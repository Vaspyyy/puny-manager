import contextlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from .crypto import decrypt_data, derive_key, derive_key_legacy, encrypt_data, generate_salt
from .vault import Entry, PunyError, Vault

APP_NAME = "puny-manager"


def _xdg_data() -> Path:
    base = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))
    return Path(base)


def _xdg_config() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(base)


def data_dir() -> Path:
    return _xdg_data() / APP_NAME


def vault_path() -> Path:
    return data_dir() / "vault.puny"


def config_dir() -> Path:
    return _xdg_config() / APP_NAME


def lang_path() -> Path:
    return config_dir() / "lang"


def load_vault(master_password: str) -> Vault:
    path = vault_path()
    if not path.exists():
        raise PunyError("vault_missing")

    raw = path.read_bytes()
    if len(raw) < 28:
        raise PunyError("vault_corrupt")

    salt = raw[:16]
    nonce = raw[16:28]
    ciphertext = raw[28:]

    try:
        key = derive_key(master_password, salt)
        plaintext = decrypt_data(key, nonce, ciphertext)
    except Exception:
        try:
            key = derive_key_legacy(master_password, salt)
            plaintext = decrypt_data(key, nonce, ciphertext)
            data = json.loads(plaintext.decode())
            entries = [Entry(**e) for e in data["entries"]]
            vault = Vault(version=data["version"], entries=entries)
            save_vault(master_password, vault)
        except Exception:
            raise PunyError("vault_decrypt_failed") from None

    data = json.loads(plaintext.decode())
    entries = [Entry(**e) for e in data["entries"]]
    return Vault(version=data["version"], entries=entries)


def save_vault(master_password: str, vault: Vault) -> None:
    data_dir().mkdir(parents=True, exist_ok=True)

    salt = generate_salt()
    key = derive_key(master_password, salt)

    payload = {
        "version": vault.version,
        "entries": [e.__dict__ for e in vault.entries],
    }

    plaintext = json.dumps(payload).encode()
    nonce, ciphertext = encrypt_data(key, plaintext)

    blob = salt + nonce + ciphertext
    path = vault_path()
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)

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


def init_vault(master_password: str) -> None:
    path = vault_path()
    if path.exists():
        raise PunyError("vault_exists")
    save_vault(master_password, Vault())


def remove_backup() -> None:
    backup = vault_path().with_suffix(vault_path().suffix + ".bak")
    with contextlib.suppress(OSError):
        os.unlink(backup)
