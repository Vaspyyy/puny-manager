
import json
from pathlib import Path

from .paths import get_vault_path
from .crypto import (
        generate_salt,
        derive_key,
        encrypt_data,
        decrypt_data,
)


def load_vault(master_password: str) -> dict:
    vault_path = get_vault_path()

    if not vault_path.exists():
        raise FileNotFoundError("Vault existiert nicht!")

    raw = vault_path.read_bytes()

    if len(raw) < 28:
        raise ValueError("Vault-Datei ist beschädigt.")

    salt = raw[:16]
    nonce = raw[16:28]
    ciphertext = raw[28:]

    key = derive_key(master_password, salt)

    try:
        plaintext = decrypt_data(key, nonce, ciphertext)
    except Exception:
        raise ValueError("Vault konnte nicht entschlüsselt werden")

    return json.loads(plaintext.decode("utf-8"))

def save_vault(master_password: str, data: dict) -> None:
    vault_path = get_vault_path()

    salt = generate_salt()
    key = derive_key(master_password, salt)

    plaintext = json.dumps(data).encode("utf-8")
    nonce, ciphertext = encrypt_data(key, plaintext)

    blob = salt + nonce + ciphertext
    vault_path.write_bytes(blob)
    vault_path.chmod(0o600)
