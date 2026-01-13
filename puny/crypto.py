
import os
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def generate_salt(length: int = 16) -> bytes:
    return os.urandom(length)

def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=200_000,
            backend=default_backend(),

    )
    return kdf.derive(password.encode("utf-8"))

def generate_nonce(length: int = 12) -> bytes:
    return os.urandom(length)

def encrypt_data(key: bytes, plaintext: bytes) -> tuple[bytes, bytes]:
    nonce = generate_nonce()
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)
    return nonce, ciphertext

def decrypt_data(key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None)
