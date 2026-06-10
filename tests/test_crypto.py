import pytest
from cryptography.exceptions import InvalidTag

from puny.crypto import (
    KDF_ARGON2ID,
    KDF_PBKDF2,
    LEVEL_BALANCED,
    LEVEL_FAST,
    LEVEL_PARANOID,
    PRESETS,
    decrypt_data,
    derive_key,
    derive_key_legacy,
    encrypt_data,
    generate_salt,
)


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
        k1 = derive_key("password", salt, KDF_ARGON2ID, LEVEL_BALANCED)
        k2 = derive_key("password", salt, KDF_ARGON2ID, LEVEL_BALANCED)
        assert k1 == k2

    def test_derive_key_different_password(self):
        salt = generate_salt()
        k1 = derive_key("password1", salt, KDF_ARGON2ID, LEVEL_BALANCED)
        k2 = derive_key("password2", salt, KDF_ARGON2ID, LEVEL_BALANCED)
        assert k1 != k2

    def test_derive_key_different_salt(self):
        k1 = derive_key("password", generate_salt(), KDF_ARGON2ID, LEVEL_BALANCED)
        k2 = derive_key("password", generate_salt(), KDF_ARGON2ID, LEVEL_BALANCED)
        assert k1 != k2

    def test_derive_key_output_length(self):
        key = derive_key("password", generate_salt(), KDF_ARGON2ID, LEVEL_BALANCED)
        assert len(key) == 32


class TestKeyDerivationPresets:
    def test_fast_produces_key(self):
        key = derive_key("password", generate_salt(), KDF_ARGON2ID, LEVEL_FAST)
        assert len(key) == 32

    def test_balanced_produces_key(self):
        key = derive_key("password", generate_salt(), KDF_ARGON2ID, LEVEL_BALANCED)
        assert len(key) == 32

    def test_paranoid_produces_key(self):
        key = derive_key("password", generate_salt(), KDF_ARGON2ID, LEVEL_PARANOID)
        assert len(key) == 32

    def test_presets_are_deterministic(self):
        salt = generate_salt()
        for level_id in PRESETS:
            k1 = derive_key("password", salt, KDF_ARGON2ID, level_id)
            k2 = derive_key("password", salt, KDF_ARGON2ID, level_id)
            assert k1 == k2, f"preset {level_id} not deterministic"

    def test_different_levels_produce_different_keys(self):
        salt = generate_salt()
        k1 = derive_key("password", salt, KDF_ARGON2ID, LEVEL_FAST)
        k2 = derive_key("password", salt, KDF_ARGON2ID, LEVEL_BALANCED)
        k3 = derive_key("password", salt, KDF_ARGON2ID, LEVEL_PARANOID)
        assert k1 != k2
        assert k2 != k3
        assert k1 != k3

    def test_pbkdf2_kdf_id_still_works(self):
        key = derive_key("password", generate_salt(), KDF_PBKDF2, 0)
        assert len(key) == 32

    def test_unsupported_kdf_raises(self):
        with pytest.raises(ValueError):
            derive_key("password", generate_salt(), 99, LEVEL_BALANCED)


class TestEncryptionRoundTrip:
    def test_encrypt_decrypt(self):
        key = derive_key("password", generate_salt(), KDF_ARGON2ID, LEVEL_BALANCED)
        plaintext = b"secret message"
        nonce, ciphertext = encrypt_data(key, plaintext)
        result = decrypt_data(key, nonce, ciphertext)
        assert result == plaintext

    def test_encrypt_tampered_data(self):
        key = derive_key("password", generate_salt(), KDF_ARGON2ID, LEVEL_BALANCED)
        plaintext = b"secret"
        nonce, ciphertext = encrypt_data(key, plaintext)
        tampered = ciphertext[:-1] + bytes([ciphertext[-1] ^ 1])
        with pytest.raises(InvalidTag):
            decrypt_data(key, nonce, tampered)

    def test_encrypt_wrong_key(self):
        plaintext = b"secret"
        nonce, ciphertext = encrypt_data(
            derive_key("password", generate_salt(), KDF_ARGON2ID, LEVEL_BALANCED), plaintext
        )
        wrong_key = derive_key("different", generate_salt(), KDF_ARGON2ID, LEVEL_BALANCED)
        with pytest.raises(InvalidTag):
            decrypt_data(wrong_key, nonce, ciphertext)

    def test_encrypt_empty(self):
        key = derive_key("password", generate_salt(), KDF_ARGON2ID, LEVEL_BALANCED)
        nonce, ciphertext = encrypt_data(key, b"")
        assert decrypt_data(key, nonce, ciphertext) == b""


class TestEncryptionRoundTripWithPresets:
    def test_roundtrip_with_fast(self):
        for _ in range(3):
            key = derive_key("password", generate_salt(), KDF_ARGON2ID, LEVEL_FAST)
            nonce, ct = encrypt_data(key, b"data")
            assert decrypt_data(key, nonce, ct) == b"data"

    def test_roundtrip_with_paranoid(self):
        key = derive_key("password", generate_salt(), KDF_ARGON2ID, LEVEL_PARANOID)
        nonce, ct = encrypt_data(key, b"data")
        assert decrypt_data(key, nonce, ct) == b"data"


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
