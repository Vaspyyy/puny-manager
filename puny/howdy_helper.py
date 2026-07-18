import base64
import binascii
import contextlib
import importlib
import json
import os
import pwd
import socket
import stat
import struct
import subprocess
import tempfile
import uuid
from pathlib import Path

PROTOCOL_VERSION = 1
MAX_MESSAGE_SIZE = 8192
STORE_ROOT = Path("/var/lib/puny-manager/howdy")
PAM_SERVICE = "puny-manager-howdy"


class HelperError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _validate_vault_id(value: object) -> str:
    if not isinstance(value, str) or len(value) != 32:
        raise HelperError("invalid_request")
    try:
        parsed = uuid.UUID(hex=value)
    except ValueError:
        raise HelperError("invalid_request") from None
    if parsed.hex != value.lower() or parsed.int == 0:
        raise HelperError("invalid_request")
    return parsed.hex


def _credential_name(uid: int, vault_id: str) -> str:
    return f"puny-manager-{uid}-{vault_id}"


def _user_dir(uid: int) -> Path:
    if uid < 0:
        raise HelperError("invalid_request")
    STORE_ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    root_stat = STORE_ROOT.lstat()
    if stat.S_ISLNK(root_stat.st_mode) or root_stat.st_uid != 0:
        raise HelperError("unsafe_storage")
    os.chmod(STORE_ROOT, 0o700)

    path = STORE_ROOT / str(uid)
    if path.exists():
        path_stat = path.lstat()
        if stat.S_ISLNK(path_stat.st_mode) or not stat.S_ISDIR(path_stat.st_mode):
            raise HelperError("unsafe_storage")
        if path_stat.st_uid != 0:
            raise HelperError("unsafe_storage")
    else:
        path.mkdir(mode=0o700)
    os.chmod(path, 0o700)
    return path


def _credential_path(uid: int, vault_id: str) -> Path:
    return _user_dir(uid) / f"{vault_id}.cred"


def _credential_exists(uid: int, vault_id: str) -> bool:
    target = _credential_path(uid, vault_id)
    try:
        target_stat = target.lstat()
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(target_stat.st_mode) or not stat.S_ISREG(target_stat.st_mode):
        raise HelperError("unsafe_storage")
    if target_stat.st_uid != 0 or stat.S_IMODE(target_stat.st_mode) != 0o600:
        raise HelperError("unsafe_storage")
    return True


def _has_tpm2() -> bool:
    try:
        result = subprocess.run(
            ["systemd-creds", "has-tpm2"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and result.stdout.splitlines()[:1] == [b"yes"]


def _authenticate(uid: int) -> None:
    try:
        pam_module = importlib.import_module("pam")
    except ImportError:
        raise HelperError("pam_unavailable") from None
    try:
        username = pwd.getpwuid(uid).pw_name
    except KeyError:
        raise HelperError("invalid_request") from None
    authenticator = pam_module.pam()
    if not authenticator.authenticate(username, "", service=PAM_SERVICE, resetcreds=False):
        raise HelperError("auth_failed")


def _seal_key(uid: int, vault_id: str, data_key: bytes) -> None:
    if not _has_tpm2():
        raise HelperError("tpm_unavailable")
    name = _credential_name(uid, vault_id)
    try:
        result = subprocess.run(
            [
                "systemd-creds",
                "--quiet",
                "--newline=no",
                "--with-key=host+tpm2",
                "--tpm2-device=auto",
                f"--name={name}",
                "encrypt",
                "-",
                "-",
            ],
            input=data_key,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        raise HelperError("credential_failed") from None
    if result.returncode != 0 or not result.stdout:
        raise HelperError("credential_failed")

    target = _credential_path(uid, vault_id)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{vault_id}.", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(result.stdout)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, target)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp_name)


def _unseal_key(uid: int, vault_id: str) -> bytes:
    if not _has_tpm2():
        raise HelperError("tpm_unavailable")
    target = _credential_path(uid, vault_id)
    if not _credential_exists(uid, vault_id):
        raise HelperError("credential_missing") from None

    try:
        result = subprocess.run(
            [
                "systemd-creds",
                "--quiet",
                "--newline=no",
                "--refuse-null",
                f"--name={_credential_name(uid, vault_id)}",
                "decrypt",
                str(target),
                "-",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        raise HelperError("credential_failed") from None
    if result.returncode != 0 or len(result.stdout) != 32:
        raise HelperError("credential_failed")
    return result.stdout


def handle_request(uid: int, request: object) -> dict[str, object]:
    if not isinstance(request, dict) or request.get("version") != PROTOCOL_VERSION:
        raise HelperError("invalid_request")
    op = request.get("op")

    if op == "status":
        vault_id_value = request.get("vault_id")
        enrolled = False
        if vault_id_value is not None:
            vault_id = _validate_vault_id(vault_id_value)
            enrolled = _credential_exists(uid, vault_id)
        return {"ok": True, "tpm": _has_tpm2(), "enrolled": enrolled}

    if op == "test":
        if not _has_tpm2():
            raise HelperError("tpm_unavailable")
        _authenticate(uid)
        return {"ok": True}

    vault_id = _validate_vault_id(request.get("vault_id"))
    if op == "enroll":
        value = request.get("key")
        if not isinstance(value, str):
            raise HelperError("invalid_request")
        try:
            data_key = base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error):
            raise HelperError("invalid_request") from None
        if len(data_key) != 32:
            raise HelperError("invalid_request")
        _authenticate(uid)
        _seal_key(uid, vault_id, data_key)
        return {"ok": True}

    if op == "unlock":
        _authenticate(uid)
        data_key = _unseal_key(uid, vault_id)
        return {"ok": True, "key": base64.b64encode(data_key).decode("ascii")}

    if op == "remove":
        target = _credential_path(uid, vault_id)
        if not _credential_exists(uid, vault_id):
            return {"ok": True}
        target.unlink()
        return {"ok": True}

    raise HelperError("invalid_request")


def _read_request(connection: socket.socket) -> object:
    payload = bytearray()
    while len(payload) <= MAX_MESSAGE_SIZE:
        chunk = connection.recv(4096)
        if not chunk:
            break
        payload.extend(chunk)
        if b"\n" in chunk:
            break
    if not payload or len(payload) > MAX_MESSAGE_SIZE or b"\n" not in payload:
        raise HelperError("invalid_request")
    try:
        return json.loads(bytes(payload).split(b"\n", 1)[0])
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HelperError("invalid_request") from None


def main() -> None:
    connection = socket.socket(fileno=0)
    _pid, uid, _gid = struct.unpack(
        "3i", connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12)
    )
    try:
        response = handle_request(uid, _read_request(connection))
    except HelperError as error:
        response = {"ok": False, "code": error.code}
    encoded = json.dumps(response, separators=(",", ":")).encode() + b"\n"
    connection.sendall(encoded)


if __name__ == "__main__":
    main()
