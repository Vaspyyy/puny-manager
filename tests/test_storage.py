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
    validate_vault_name,
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


class TestVaultNameValidation:
    def test_valid_names_accepted(self):
        for name in ["test", "my-vault", "vault_2", "A", "a1b2c3"]:
            validate_vault_name(name)

    def test_path_traversal_rejected(self):
        with pytest.raises(PunyError) as exc:
            validate_vault_name("../../etc/passwd")
        assert exc.value.key == "invalid_vault_name"

    def test_slash_rejected(self):
        with pytest.raises(PunyError) as exc:
            validate_vault_name("foo/bar")
        assert exc.value.key == "invalid_vault_name"

    def test_backslash_rejected(self):
        with pytest.raises(PunyError):
            validate_vault_name("foo\\bar")

    def test_leading_dot_rejected(self):
        with pytest.raises(PunyError):
            validate_vault_name(".hidden")

    def test_dot_dot_rejected(self):
        with pytest.raises(PunyError):
            validate_vault_name("..")

    def test_empty_name_rejected(self):
        with pytest.raises(PunyError):
            validate_vault_name("")

    def test_space_rejected(self):
        with pytest.raises(PunyError):
            validate_vault_name("has space")

    def test_null_byte_rejected(self):
        with pytest.raises(PunyError):
            validate_vault_name("test\x00evil")

    def test_too_long_rejected(self):
        with pytest.raises(PunyError):
            validate_vault_name("a" * 65)

    def test_max_length_accepted(self):
        validate_vault_name("a" * 64)

    def test_vault_path_rejects_traversal(self):
        with pytest.raises(PunyError):
            vault_path("../escape")


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


class TestDeserialization:
    def _write_vault_payload(self, monkeypatch, tmp_path, payload_bytes: bytes):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        vaults_dir().mkdir(parents=True, exist_ok=True)
        salt = generate_salt()
        key = derive_key("password123!", salt, KDF_ARGON2ID, LEVEL_BALANCED)
        nonce, ct = encrypt_data(key, payload_bytes)
        header = MAGIC + bytes([VERSION_1, KDF_ARGON2ID, LEVEL_BALANCED, 0])
        vault_path("badformat").write_bytes(header + salt + nonce + ct)

    def test_malformed_json_raises_corrupt(self, monkeypatch, tmp_path):
        self._write_vault_payload(monkeypatch, tmp_path, b"not json {{{")
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="badformat")
        assert exc.value.key == "vault_corrupt"

    def test_json_array_raises_corrupt(self, monkeypatch, tmp_path):
        self._write_vault_payload(monkeypatch, tmp_path, b'[1, 2, 3]')
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="badformat")
        assert exc.value.key == "vault_corrupt"

    def test_missing_entries_key_raises_corrupt(self, monkeypatch, tmp_path):
        self._write_vault_payload(monkeypatch, tmp_path, json.dumps({"version": 1}).encode())
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="badformat")
        assert exc.value.key == "vault_corrupt"

    def test_missing_version_key_raises_corrupt(self, monkeypatch, tmp_path):
        self._write_vault_payload(monkeypatch, tmp_path, json.dumps({"entries": []}).encode())
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="badformat")
        assert exc.value.key == "vault_corrupt"

    def test_entries_not_a_list_raises_corrupt(self, monkeypatch, tmp_path):
        self._write_vault_payload(
            monkeypatch, tmp_path, json.dumps({"version": 1, "entries": "bad"}).encode()
        )
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="badformat")
        assert exc.value.key == "vault_corrupt"

    def test_entry_not_a_dict_raises_corrupt(self, monkeypatch, tmp_path):
        self._write_vault_payload(
            monkeypatch, tmp_path, json.dumps({"version": 1, "entries": ["string"]}).encode()
        )
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="badformat")
        assert exc.value.key == "vault_corrupt"

    def test_entry_missing_required_field_raises_corrupt(self, monkeypatch, tmp_path):
        self._write_vault_payload(
            monkeypatch,
            tmp_path,
            json.dumps({"version": 1, "entries": [{"name": "x", "username": "u"}]}).encode(),
        )
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="badformat")
        assert exc.value.key == "vault_corrupt"

    def test_entry_extra_keys_raises_corrupt(self, monkeypatch, tmp_path):
        self._write_vault_payload(
            monkeypatch,
            tmp_path,
            json.dumps({
                "version": 1,
                "entries": [{"name": "x", "username": "u", "password": "p", "evil": True}],
            }).encode(),
        )
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="badformat")
        assert exc.value.key == "vault_corrupt"

    def test_entry_empty_name_raises_corrupt(self, monkeypatch, tmp_path):
        self._write_vault_payload(
            monkeypatch,
            tmp_path,
            json.dumps({
                "version": 1,
                "entries": [{"name": "", "username": "u", "password": "p"}],
            }).encode(),
        )
        with pytest.raises(PunyError) as exc:
            load_vault("password123!", name="badformat")
        assert exc.value.key == "vault_corrupt"


class TestRotatingBackups:
    def test_backup_created_on_save(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "backup_test")
        vault = load_vault("password123!", name="backup_test")
        vault.add(Entry(name="test", username="u", password="p"))
        save_vault("password123!", vault)

        backup_path = vault_path("backup_test").with_suffix(".puny.bak.1")
        assert backup_path.exists()

    def test_rotating_backups_created(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "rotate_test")
        
        for i in range(7):
            vault = load_vault("password123!", name="rotate_test")
            vault.add(Entry(name=f"entry_{i}", username="u", password="p"))
            save_vault("password123!", vault)

        vault_dir = vault_path("rotate_test").parent
        backups = sorted(vault_dir.glob("rotate_test.puny.bak.*"))
        assert len(backups) == 5
        assert backups[0].name == "rotate_test.puny.bak.1"
        assert backups[4].name == "rotate_test.puny.bak.5"

    def test_backup_rotation_preserves_order(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "order_test")
        
        for i in range(3):
            vault = load_vault("password123!", name="order_test")
            vault.add(Entry(name=f"entry_{i}", username="u", password="p"))
            save_vault("password123!", vault)

        vault_dir = vault_path("order_test").parent
        backups = sorted(vault_dir.glob("order_test.puny.bak.*"))
        assert len(backups) == 3
        assert backups[0].name == "order_test.puny.bak.1"
        assert backups[1].name == "order_test.puny.bak.2"
        assert backups[2].name == "order_test.puny.bak.3"
