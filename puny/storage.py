import json
import os
from pathlib import Path
from .crypto import generate_salt, derive_key, encrypt_data, decrypt_data
from .vault import Vault, Entry, PunyError

APP_NAME = "puny-manager"

def data_dir() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return base / APP_NAME

def vault_path() -> Path:
    return data_dir() / "vault.puny"

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
        raise PunyError("vault_decrypt_failed")

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
    path.write_bytes(blob)
    path.chmod(0o600)

def init_vault(master_password: str) -> None:
    path = vault_path()
    if path.exists():
        raise PunyError("vault_exists")
    save_vault(master_password, Vault())

def config_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME

def lang_path() -> Path:
    return config_dir() / "lang"

