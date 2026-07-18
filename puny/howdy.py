import base64
import json
import socket
from pathlib import Path

SOCKET_PATH = Path("/run/puny-manager/howdy.sock")
PROTOCOL_VERSION = 1
MAX_MESSAGE_SIZE = 8192


class HowdyError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def _vault_id_text(vault_id: bytes) -> str:
    if len(vault_id) != 16:
        raise HowdyError("invalid_request")
    return vault_id.hex()


def _request(op: str, **payload: object) -> dict[str, object]:
    message = {"version": PROTOCOL_VERSION, "op": op, **payload}
    encoded = json.dumps(message, separators=(",", ":")).encode() + b"\n"
    if len(encoded) > MAX_MESSAGE_SIZE:
        raise HowdyError("invalid_request")

    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(20)
    try:
        client.connect(str(SOCKET_PATH))
        client.sendall(encoded)
        response = bytearray()
        while len(response) <= MAX_MESSAGE_SIZE:
            chunk = client.recv(4096)
            if not chunk:
                break
            response.extend(chunk)
            if b"\n" in chunk:
                break
    except OSError:
        raise HowdyError("helper_unavailable") from None
    finally:
        client.close()

    if len(response) > MAX_MESSAGE_SIZE:
        raise HowdyError("invalid_response")
    try:
        result = json.loads(bytes(response).split(b"\n", 1)[0])
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HowdyError("invalid_response") from None
    if not isinstance(result, dict) or not isinstance(result.get("ok"), bool):
        raise HowdyError("invalid_response")
    if not result["ok"]:
        code = result.get("code")
        raise HowdyError(code if isinstance(code, str) else "helper_failed")
    return result


def status(vault_id: bytes | None = None) -> dict[str, object]:
    payload = {}
    if vault_id is not None:
        payload["vault_id"] = _vault_id_text(vault_id)
    return _request("status", **payload)


def test() -> None:
    _request("test")


def enroll(vault_id: bytes, data_key: bytes) -> None:
    if len(data_key) != 32:
        raise HowdyError("invalid_request")
    _request(
        "enroll",
        vault_id=_vault_id_text(vault_id),
        key=base64.b64encode(data_key).decode("ascii"),
    )


def unlock(vault_id: bytes) -> bytes:
    result = _request("unlock", vault_id=_vault_id_text(vault_id))
    value = result.get("key")
    if not isinstance(value, str):
        raise HowdyError("invalid_response")
    try:
        data_key = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        raise HowdyError("invalid_response") from None
    if len(data_key) != 32:
        raise HowdyError("invalid_response")
    return data_key


def remove(vault_id: bytes) -> None:
    _request("remove", vault_id=_vault_id_text(vault_id))
