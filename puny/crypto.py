import os

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC = b"PUNY"
VERSION_1 = 1

KDF_ARGON2ID = 1
KDF_PBKDF2 = 2
SUPPORTED_KDFS = {KDF_ARGON2ID, KDF_PBKDF2}

LEVEL_FAST = 1
LEVEL_BALANCED = 2
LEVEL_PARANOID = 3

PRESETS = {
    LEVEL_FAST: {"time": 2, "mem": 32 * 1024, "par": 2},
    LEVEL_BALANCED: {"time": 5, "mem": 64 * 1024, "par": 4},
    LEVEL_PARANOID: {"time": 10, "mem": 256 * 1024, "par": 8},
}

PBKDF2_ITERATIONS = 200_000


def generate_salt(length: int = 16) -> bytes:
    return os.urandom(length)


def derive_key(password: str, salt: bytes, kdf_id: int, level_id: int) -> bytes:
    if kdf_id == KDF_ARGON2ID:
        params = PRESETS[level_id]
        kdf = Argon2id(
            salt=salt,
            length=32,
            iterations=params["time"],
            memory_cost=params["mem"],
            lanes=params["par"],
        )
        return kdf.derive(password.encode())

    if kdf_id == KDF_PBKDF2:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=PBKDF2_ITERATIONS,
            backend=default_backend(),
        )
        return kdf.derive(password.encode())

    raise ValueError(f"Unsupported KDF: {kdf_id}")


def derive_key_legacy(password: str, salt: bytes) -> bytes:
    return derive_key(password, salt, KDF_PBKDF2, 0)


def encrypt_data(key: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
    nonce = os.urandom(12)
    aes = AESGCM(key)
    return nonce, aes.encrypt(nonce, plaintext, None)


def decrypt_data(key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    aes = AESGCM(key)
    return aes.decrypt(nonce, ciphertext, None)
