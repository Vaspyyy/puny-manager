import pytest
from cryptography.exceptions import InvalidTag

from puny.crypto import decrypt_data, derive_key, derive_key_legacy, encrypt_data, generate_salt


class TestSalt:
    def test_generate_salt_default_length(self):
        salt = generate_salt()
        assert len(salt) == 16

    def test_generate_salt_custom_length(self):
        salt = generate_salt(32)
        assert len(salt) == 32

    def test_generate_salt_is_random(self):
        a = generate_salt()
        b = generate_salt()
        assert a != b


class TestKeyDerivation:
    def test_derive_key_consistent(self):
        salt = generate_salt()
        k1 = derive_key("password", salt)
        k2 = derive_key("password", salt)
        assert k1 == k2

    def test_derive_key_different_password(self):
        salt = generate_salt()
        k1 = derive_key("password1", salt)
        k2 = derive_key("password2", salt)
        assert k1 != k2

    def test_derive_key_different_salt(self):
        k1 = derive_key("password", generate_salt())
        k2 = derive_key("password", generate_salt())
        assert k1 != k2

    def test_derive_key_output_length(self):
        key = derive_key("password", generate_salt())
        assert len(key) == 32


class TestEncryptionRoundTrip:
    def test_encrypt_decrypt(self):
        key = derive_key("password", generate_salt())
        plaintext = b"secret message"
        nonce, ciphertext = encrypt_data(key, plaintext)
        result = decrypt_data(key, nonce, ciphertext)
        assert result == plaintext

    def test_encrypt_tampered_data(self):
        key = derive_key("password", generate_salt())
        plaintext = b"secret"
        nonce, ciphertext = encrypt_data(key, plaintext)
        tampered = ciphertext[:-1] + bytes([ciphertext[-1] ^ 1])
        with pytest.raises(InvalidTag):
            decrypt_data(key, nonce, tampered)

    def test_encrypt_wrong_key(self):
        plaintext = b"secret"
        nonce, ciphertext = encrypt_data(
            derive_key("password", generate_salt()), plaintext
        )
        wrong_key = derive_key("different", generate_salt())
        with pytest.raises(InvalidTag):
            decrypt_data(wrong_key, nonce, ciphertext)

    def test_encrypt_empty(self):
        key = derive_key("password", generate_salt())
        nonce, ciphertext = encrypt_data(key, b"")
        assert decrypt_data(key, nonce, ciphertext) == b""


class TestLegacyKeyDerivation:
    def test_derive_key_legacy_consistent(self):
        salt = generate_salt()
        k1 = derive_key_legacy("password", salt)
        k2 = derive_key_legacy("password", salt)
        assert k1 == k2

    def test_derive_key_legacy_different_password(self):
        salt = generate_salt()
        k1 = derive_key_legacy("password1", salt)
        k2 = derive_key_legacy("password2", salt)
        assert k1 != k2

    def test_derive_key_legacy_different_salt(self):
        k1 = derive_key_legacy("password", generate_salt())
        k2 = derive_key_legacy("password", generate_salt())
        assert k1 != k2

    def test_derive_key_legacy_output_length(self):
        key = derive_key_legacy("password", generate_salt())
        assert len(key) == 32

    def test_derive_key_legacy_roundtrip(self):
        key = derive_key_legacy("password", generate_salt())
        nonce, ciphertext = encrypt_data(key, b"secret")
        assert decrypt_data(key, nonce, ciphertext) == b"secret"
