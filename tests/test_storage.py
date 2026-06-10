import json
import os
from pathlib import Path

import pytest

from puny.crypto import (
    KDF_ARGON2ID,
    LEVEL_BALANCED,
    LEVEL_FAST,
    LEVEL_PARANOID,
    MAGIC,
    VERSION_1,
    derive_key,
    encrypt_data,
    generate_salt,
)
from puny.storage import (
    create_vault,
    data_dir,
    delete_vault,
    get_active_vault,
    list_vaults,
    load_vault,
    save_vault,
    set_active_vault,
    vault_path,
    vaults_dir,
)
from puny.vault import Entry, PunyError


class TestVaultPaths:
    def test_vault_path_returns_name_based_path(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        p = vault_path("test")
        assert p == tmp_path / "puny-manager" / "vaults" / "test.puny"

    def test_data_dir_respects_xdg(self, monkeypatch):
        monkeypatch.setitem(os.environ, "XDG_DATA_HOME", "/custom/data")
        assert data_dir() == Path("/custom/data/puny-manager")


class TestActiveVault:
    def test_no_active_vault_by_default(self):
        assert get_active_vault() is None

    def test_set_and_get_active_vault(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)

        vault_path("testval").parent.mkdir(parents=True, exist_ok=True)
        vault_path("testval").write_bytes(
            generate_salt() + b"\x00" * 12 + b"fake_ciphertext"
        )

        set_active_vault("testval")
        assert get_active_vault() == "testval"

    def test_active_vault_ignored_if_file_missing(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)

        set_active_vault("nonexistent")
        assert get_active_vault() is None


class TestMultiVault:
    def test_create_and_load_vault(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "myvault")
        v = load_vault("password123!", name="myvault")
        assert v.name == "myvault"
        assert v.entries == []

    def test_create_duplicate_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "dup")
        with pytest.raises(PunyError):
            create_vault("password123!", "dup")

    def test_load_default_vault_with_active_set(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "default")
        v = load_vault("password123!")
        assert v.name == "default"

    def test_load_without_active_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        with pytest.raises(PunyError):
            load_vault("any")

    def test_list_vaults_empty(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        assert list_vaults() == []

    def test_list_vaults_single(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "v1")
        assert list_vaults() == ["v1"]

    def test_list_vaults_multiple_sorted(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "zulu")
        create_vault("password123!", "alpha")
        create_vault("password123!", "mike")
        assert list_vaults() == ["alpha", "mike", "zulu"]

    def test_delete_vault_is_removed(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "temp")
        assert vault_path("temp").exists()
        set_active_vault("alpha")  # switch away
        delete_vault("temp")
        assert not vault_path("temp").exists()

    def test_cannot_delete_active_vault(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "active")
        with pytest.raises(PunyError):
            delete_vault("active")

    def test_delete_nonexistent_raises(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        with pytest.raises(PunyError):
            delete_vault("ghost")

    def test_save_and_load_preserves_entries(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        vault = create_vault("password123!", "data")
        vault.add(Entry(name="github", username="dev", password="secret"))
        save_vault("password123!", vault)

        v2 = load_vault("password123!", name="data")
        assert len(v2.entries) == 1
        assert v2.entries[0].name == "github"


class TestMigration:
    def test_legacy_vault_migrated_on_load(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        legacy_dir = data_dir()
        legacy_dir.mkdir(parents=True, exist_ok=True)
        old_path = legacy_dir / "vault.puny"

        salt = generate_salt()
        key = derive_key("legacy_pass", salt, KDF_ARGON2ID, LEVEL_BALANCED)
        payload = json.dumps({"version": 1, "entries": []}).encode()
        nonce, ciphertext = encrypt_data(key, payload)
        old_path.write_bytes(salt + nonce + ciphertext)

        with pytest.raises(PunyError):
            load_vault("wrong_pass")

        v = load_vault("legacy_pass")
        assert v.name == "default"
        assert not old_path.exists()
        assert get_active_vault() == "default"
        assert list_vaults() == ["default"]

    def test_legacy_migration_is_idempotent(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        legacy_dir = data_dir()
        legacy_dir.mkdir(parents=True, exist_ok=True)

        salt = generate_salt()
        key = derive_key("pass", salt, KDF_ARGON2ID, LEVEL_BALANCED)
        payload = json.dumps({"version": 1, "entries": []}).encode()
        nonce, ciphertext = encrypt_data(key, payload)
        (legacy_dir / "vault.puny").write_bytes(salt + nonce + ciphertext)

        load_vault("pass")
        load_vault("pass")
        load_vault("pass")

        assert list_vaults() == ["default"]


class TestEncryptionLevels:
    def test_create_fast_and_reload(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "fastvault", level_id=LEVEL_FAST)
        v = load_vault("password123!", name="fastvault")
        assert v.kdf_id == KDF_ARGON2ID
        assert v.level_id == LEVEL_FAST
        assert v.entries == []

    def test_create_balanced_and_reload(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "balvault", level_id=LEVEL_BALANCED)
        v = load_vault("password123!", name="balvault")
        assert v.kdf_id == KDF_ARGON2ID
        assert v.level_id == LEVEL_BALANCED

    def test_create_paranoid_and_reload(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "parvault", level_id=LEVEL_PARANOID)
        v = load_vault("password123!", name="parvault")
        assert v.kdf_id == KDF_ARGON2ID
        assert v.level_id == LEVEL_PARANOID

    def test_level_persists_after_save_reload(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        vault = create_vault("password123!", "persist", level_id=LEVEL_FAST)
        from puny.vault import Entry
        vault.add(Entry(name="test", username="u", password="p"))
        from puny.storage import save_vault
        save_vault("password123!", vault)

        v2 = load_vault("password123!", name="persist")
        assert v2.level_id == LEVEL_FAST
        assert v2.kdf_id == KDF_ARGON2ID
        assert len(v2.entries) == 1


class TestNewFormatHeader:
    def test_new_format_has_magic(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "magic")
        raw = vault_path("magic").read_bytes()
        assert raw[:4] == MAGIC
        assert raw[4] == VERSION_1
        assert raw[5] == KDF_ARGON2ID
        assert raw[6] == LEVEL_BALANCED
        assert raw[7] == 0

    def test_header_includes_level(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "leveled", level_id=LEVEL_PARANOID)
        raw = vault_path("leveled").read_bytes()
        assert raw[6] == LEVEL_PARANOID


class TestCorruption:
    def _write_corrupt(self, monkeypatch, tmp_path, header_bytes):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        vaults_dir().mkdir(parents=True, exist_ok=True)
        salt = generate_salt()
        key = derive_key("password123!", salt, KDF_ARGON2ID, LEVEL_BALANCED)
        nonce, ct = encrypt_data(key, json.dumps({"version": 1, "entries": []}).encode())
        vault_path("corrupt").write_bytes(header_bytes + salt + nonce + ct)

    def test_unsupported_version_raises(self, monkeypatch, tmp_path):
        header = MAGIC + bytes([255, KDF_ARGON2ID, LEVEL_BALANCED, 0])
        self._write_corrupt(monkeypatch, tmp_path, header)
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="corrupt")
        assert exc.value.key == "unsupported_version"

    def test_unsupported_kdf_raises(self, monkeypatch, tmp_path):
        header = MAGIC + bytes([VERSION_1, 255, LEVEL_BALANCED, 0])
        self._write_corrupt(monkeypatch, tmp_path, header)
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="corrupt")
        assert exc.value.key == "unsupported_kdf"

    def test_invalid_level_raises(self, monkeypatch, tmp_path):
        header = MAGIC + bytes([VERSION_1, KDF_ARGON2ID, 255, 0])
        self._write_corrupt(monkeypatch, tmp_path, header)
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="corrupt")
        assert exc.value.key == "vault_corrupt"

    def test_nonzero_flags_raises(self, monkeypatch, tmp_path):
        header = MAGIC + bytes([VERSION_1, KDF_ARGON2ID, LEVEL_BALANCED, 1])
        self._write_corrupt(monkeypatch, tmp_path, header)
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="corrupt")
        assert exc.value.key == "vault_corrupt"

    def test_truncated_header_raises(self, monkeypatch, tmp_path):
        header = MAGIC + bytes([VERSION_1, KDF_ARGON2ID])
        self._write_corrupt(monkeypatch, tmp_path, header)
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="corrupt")
        assert exc.value.key == "vault_corrupt"

    def test_wrong_password_fails(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("correct_pass!", "wpvault")
        with pytest.raises(PunyError) as exc:
            load_vault("wrong_pass!", name="wpvault")
        assert exc.value.key == "vault_decrypt_failed"
