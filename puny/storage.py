import contextlib
import json
import os
import re
import shutil
import tempfile
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from cryptography.exceptions import InvalidTag

from .crypto import (
    KDF_ARGON2ID,
    KDF_PBKDF2,
    LEVEL_BALANCED,
    MAGIC,
    PRESETS,
    SUPPORTED_KDFS,
    VERSION_1,
    VERSION_2,
    decrypt_data,
    derive_key,
    encrypt_data,
    generate_key,
    generate_salt,
)
from .vault import Entry, PunyError, Vault

APP_NAME = "puny-manager"
FLAG_HOWDY = 0x01
V2_HEADER_SIZE = 112


@dataclass(frozen=True)
class VaultHeader:
    format_version: int
    howdy_enabled: bool
    vault_id: bytes | None = None


def _xdg_data() -> Path:
    base = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))
    return Path(base)


def _xdg_config() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(base)


def data_dir() -> Path:
    return _xdg_data() / APP_NAME


def vaults_dir() -> Path:
    return data_dir() / "vaults"


_VAULT_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


def validate_vault_name(name: str) -> None:
    if not _VAULT_NAME_RE.match(name):
        raise PunyError("invalid_vault_name", name=name)


def vault_path(name: str) -> Path:
    validate_vault_name(name)
    return vaults_dir() / f"{name}.puny"


def config_dir() -> Path:
    return _xdg_config() / APP_NAME


def lang_path() -> Path:
    return config_dir() / "lang"


def _active_path() -> Path:
    return config_dir() / "active"


def get_active_vault() -> str | None:
    try:
        name = _active_path().read_text().strip()
        if name and vault_path(name).exists():
            return name
    except FileNotFoundError:
        pass
    return None


def set_active_vault(name: str) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    _active_path().write_text(name)


def list_vaults() -> list[str]:
    vaults_dir().mkdir(parents=True, exist_ok=True)
    names = []
    for p in sorted(vaults_dir().glob("*.puny")):
        stem = p.stem
        if _VAULT_NAME_RE.match(stem):
            names.append(stem)
    return names


def _migrate_legacy_vault() -> bool:
    old_path = data_dir() / "vault.puny"
    if not old_path.exists():
        return False

    vaults_dir().mkdir(parents=True, exist_ok=True)
    os.chmod(vaults_dir(), 0o700)

    new_path = vault_path("default")
    if new_path.exists():
        return False

    shutil.move(str(old_path), str(new_path))

    old_backup = data_dir() / "vault.puny.bak"
    if old_backup.exists():
        new_backup = new_path.with_suffix(new_path.suffix + ".bak")
        shutil.move(str(old_backup), str(new_backup))

    set_active_vault("default")
    return True


def _parse_vault_raw(plaintext: bytes, name: str | None, kdf_id: int, level_id: int) -> Vault:
    try:
        data = json.loads(plaintext.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise PunyError("vault_corrupt") from None

    if not isinstance(data, dict) or "entries" not in data or "version" not in data:
        raise PunyError("vault_corrupt")

    if not isinstance(data["entries"], list):
        raise PunyError("vault_corrupt")

    entries: list[Entry] = []
    for e in data["entries"]:
        if not isinstance(e, dict):
            raise PunyError("vault_corrupt")
        try:
            entries.append(Entry(**e))
        except (TypeError, ValueError, PunyError):
            raise PunyError("vault_corrupt") from None

    return Vault(
        version=data["version"],
        entries=entries,
        name=name,
        kdf_id=kdf_id,
        level_id=level_id,
    )


def _load_new_format(raw: bytes, password: str, name: str | None) -> Vault:
    fmt_version = raw[4]
    kdf_id = raw[5]
    level_id = raw[6]
    flags = raw[7]

    if fmt_version != VERSION_1:
        raise PunyError("unsupported_version", version=fmt_version)
    if kdf_id not in SUPPORTED_KDFS:
        raise PunyError("unsupported_kdf", kdf=kdf_id)
    if kdf_id == KDF_ARGON2ID and level_id not in PRESETS:
        raise PunyError("vault_corrupt")
    if flags != 0:
        raise PunyError("vault_corrupt")

    salt = raw[8:24]
    nonce = raw[24:36]
    ciphertext = raw[36:]

    key = derive_key(password, salt, kdf_id, level_id)
    try:
        plaintext = decrypt_data(key, nonce, ciphertext)
    except InvalidTag:
        raise PunyError("vault_decrypt_failed") from None
    return _parse_vault_raw(plaintext, name, kdf_id, level_id)


def _parse_v2_header(raw: bytes) -> tuple[int, int, bytes, bytes, bytes, bytes, bytes]:
    if len(raw) < V2_HEADER_SIZE + 16:
        raise PunyError("vault_corrupt")

    kdf_id = raw[5]
    level_id = raw[6]
    flags = raw[7]
    if kdf_id not in SUPPORTED_KDFS:
        raise PunyError("unsupported_kdf", kdf=kdf_id)
    if kdf_id == KDF_ARGON2ID and level_id not in PRESETS:
        raise PunyError("vault_corrupt")
    if flags != FLAG_HOWDY:
        raise PunyError("vault_corrupt")

    vault_id = raw[8:24]
    if len(vault_id) != 16 or vault_id == bytes(16):
        raise PunyError("vault_corrupt")
    return (
        kdf_id,
        level_id,
        vault_id,
        raw[24:40],
        raw[40:52],
        raw[52:100],
        raw[100:112],
    )


def _load_v2_with_key(raw: bytes, data_key: bytes, name: str | None) -> Vault:
    if len(data_key) != 32:
        raise PunyError("vault_decrypt_failed")
    kdf_id, level_id, vault_id, salt, wrap_nonce, wrapped_key, data_nonce = _parse_v2_header(raw)
    try:
        plaintext = decrypt_data(data_key, data_nonce, raw[V2_HEADER_SIZE:], raw[:100])
    except InvalidTag:
        raise PunyError("vault_decrypt_failed") from None
    vault = _parse_vault_raw(plaintext, name, kdf_id, level_id)
    vault.format_version = VERSION_2
    vault.vault_id = vault_id
    vault.data_key = data_key
    vault.wrap_salt = salt
    vault.wrap_nonce = wrap_nonce
    vault.wrapped_key = wrapped_key
    return vault


def _load_v2_with_password(raw: bytes, password: str, name: str | None) -> Vault:
    kdf_id, level_id, _vault_id, salt, wrap_nonce, wrapped_key, _data_nonce = _parse_v2_header(raw)
    wrapping_key = derive_key(password, salt, kdf_id, level_id)
    try:
        data_key = decrypt_data(wrapping_key, wrap_nonce, wrapped_key, raw[:40])
    except InvalidTag:
        raise PunyError("vault_decrypt_failed") from None
    return _load_v2_with_key(raw, data_key, name)


def _load_legacy_format(raw: bytes, password: str, name: str | None) -> Vault:
    if len(raw) < 28:
        raise PunyError("vault_corrupt")

    salt = raw[:16]
    nonce = raw[16:28]
    ciphertext = raw[28:]

    key = derive_key(password, salt, KDF_ARGON2ID, LEVEL_BALANCED)
    try:
        plaintext = decrypt_data(key, nonce, ciphertext)
        return _parse_vault_raw(plaintext, name, KDF_ARGON2ID, LEVEL_BALANCED)
    except InvalidTag:
        pass

    key = derive_key(password, salt, KDF_PBKDF2, 0)
    try:
        plaintext = decrypt_data(key, nonce, ciphertext)
        vault = _parse_vault_raw(plaintext, name, KDF_PBKDF2, LEVEL_BALANCED)
        save_vault(password, vault)
        return vault
    except InvalidTag:
        raise PunyError("vault_decrypt_failed") from None


def load_vault(master_password: str, name: str | None = None) -> Vault:
    _migrate_legacy_vault()

    if name is None:
        name = get_active_vault()
        if name is None:
            raise PunyError("no_active_vault")

    path = vault_path(name)
    if not path.exists():
        raise PunyError("vault_missing")

    raw = path.read_bytes()
    if len(raw) < 28:
        raise PunyError("vault_corrupt")

    if raw[:4] == MAGIC:
        if len(raw) < 8:
            raise PunyError("vault_corrupt")
        if raw[4] == VERSION_1:
            return _load_new_format(raw, master_password, name)
        if raw[4] == VERSION_2:
            return _load_v2_with_password(raw, master_password, name)
        raise PunyError("unsupported_version", version=raw[4])
    return _load_legacy_format(raw, master_password, name)


def load_vault_with_key(data_key: bytes, name: str | None = None) -> Vault:
    if name is None:
        name = get_active_vault()
        if name is None:
            raise PunyError("no_active_vault")
    raw = vault_path(name).read_bytes()
    if len(raw) < 8 or raw[:4] != MAGIC or raw[4] != VERSION_2:
        raise PunyError("vault_decrypt_failed")
    return _load_v2_with_key(raw, data_key, name)


def read_vault_header(name: str) -> VaultHeader:
    raw = vault_path(name).read_bytes()
    if raw[:4] != MAGIC:
        return VaultHeader(format_version=0, howdy_enabled=False)
    if len(raw) < 8:
        raise PunyError("vault_corrupt")
    if raw[4] == VERSION_1:
        return VaultHeader(format_version=VERSION_1, howdy_enabled=False)
    if raw[4] == VERSION_2:
        _kdf, _level, vault_id, *_rest = _parse_v2_header(raw)
        return VaultHeader(
            format_version=VERSION_2,
            howdy_enabled=True,
            vault_id=vault_id,
        )
    raise PunyError("unsupported_version", version=raw[4])


def rotate_backups(vault_path: Path, max_backups: int = 5) -> None:
    vault_dir = vault_path.parent
    vault_name = vault_path.stem
    vault_ext = vault_path.suffix

    for i in range(max_backups - 1, 0, -1):
        old_backup = vault_dir / f"{vault_name}{vault_ext}.bak.{i}"
        new_backup = vault_dir / f"{vault_name}{vault_ext}.bak.{i + 1}"
        if old_backup.exists():
            shutil.move(str(old_backup), str(new_backup))

    if vault_path.exists():
        backup_path = vault_dir / f"{vault_name}{vault_ext}.bak.1"
        shutil.copy2(str(vault_path), str(backup_path))


def _vault_payload(vault: Vault) -> bytes:
    return json.dumps(
        {
            "version": vault.version,
            "entries": [asdict(e) for e in vault.entries],
        }
    ).encode()


def _write_vault_blob(path: Path, blob: bytes) -> None:
    rotate_backups(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(blob)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)


def _build_v1_blob(master_password: str, vault: Vault) -> bytes:
    salt = generate_salt()
    key = derive_key(master_password, salt, vault.kdf_id, vault.level_id)
    nonce, ciphertext = encrypt_data(key, _vault_payload(vault))
    header = MAGIC + bytes([VERSION_1, vault.kdf_id, vault.level_id, 0])
    return header + salt + nonce + ciphertext


def _build_v2_blob(master_password: str | None, vault: Vault) -> bytes:
    if vault.vault_id is None or len(vault.vault_id) != 16:
        raise PunyError("vault_corrupt")
    if vault.data_key is None or len(vault.data_key) != 32:
        raise PunyError("vault_decrypt_failed")

    prefix = MAGIC + bytes([VERSION_2, vault.kdf_id, vault.level_id, FLAG_HOWDY]) + vault.vault_id
    if master_password is not None:
        salt = generate_salt()
        wrapping_key = derive_key(master_password, salt, vault.kdf_id, vault.level_id)
        wrap_nonce, wrapped_key = encrypt_data(wrapping_key, vault.data_key, prefix + salt)
        vault.wrap_salt = salt
        vault.wrap_nonce = wrap_nonce
        vault.wrapped_key = wrapped_key

    if (
        vault.wrap_salt is None
        or len(vault.wrap_salt) != 16
        or vault.wrap_nonce is None
        or len(vault.wrap_nonce) != 12
        or vault.wrapped_key is None
        or len(vault.wrapped_key) != 48
    ):
        raise PunyError("vault_corrupt")

    authenticated_header = prefix + vault.wrap_salt + vault.wrap_nonce + vault.wrapped_key
    data_nonce, ciphertext = encrypt_data(
        vault.data_key, _vault_payload(vault), authenticated_header
    )
    return authenticated_header + data_nonce + ciphertext


def save_vault(master_password: str | None, vault: Vault) -> None:
    vaults_dir().mkdir(parents=True, exist_ok=True)
    os.chmod(vaults_dir(), 0o700)

    if vault.name is None:
        raise PunyError("vault_no_name")

    path = vault_path(vault.name)
    if vault.format_version == VERSION_2:
        blob = _build_v2_blob(master_password, vault)
    else:
        if master_password is None:
            raise PunyError("master_password_required")
        blob = _build_v1_blob(master_password, vault)
    _write_vault_blob(path, blob)


def prepare_howdy_enrollment(master_password: str, name: str) -> Vault:
    vault = load_vault(master_password, name=name)
    if vault.format_version == VERSION_2:
        return vault
    vault.format_version = VERSION_2
    vault.vault_id = uuid.uuid4().bytes
    vault.data_key = generate_key()
    vault.wrap_salt = None
    vault.wrap_nonce = None
    vault.wrapped_key = None
    # Build once in memory so invalid KDF metadata is rejected before authentication.
    _build_v2_blob(master_password, vault)
    return vault


def disable_howdy_vault(master_password: str, name: str) -> bytes:
    vault = load_vault(master_password, name=name)
    if vault.format_version != VERSION_2 or vault.vault_id is None:
        raise PunyError("howdy_not_enabled")
    old_vault_id = vault.vault_id
    vault.format_version = VERSION_1
    vault.vault_id = None
    vault.data_key = None
    vault.wrap_salt = None
    vault.wrap_nonce = None
    vault.wrapped_key = None
    _write_vault_blob(vault_path(name), _build_v1_blob(master_password, vault))
    return old_vault_id


def create_vault(master_password: str, name: str, level_id: int = LEVEL_BALANCED) -> Vault:
    _migrate_legacy_vault()

    path = vault_path(name)
    if path.exists():
        raise PunyError("vault_exists")

    vault = Vault(name=name, level_id=level_id)
    save_vault(master_password, vault)
    set_active_vault(name)
    return vault


def delete_vault(name: str) -> None:
    path = vault_path(name)
    if not path.exists():
        raise PunyError("vault_missing")

    active = get_active_vault()
    if active == name:
        raise PunyError("vault_delete_active")

    with contextlib.suppress(OSError):
        os.unlink(path)
    with contextlib.suppress(OSError):
        os.unlink(path.with_suffix(path.suffix + ".bak"))


def remove_backup(name: str) -> None:
    backup = vault_path(name).with_suffix(vault_path(name).suffix + ".bak")
    with contextlib.suppress(OSError):
        os.unlink(backup)
