import json
import os
from pathlib import Path

import pytest

from puny.crypto import derive_key, encrypt_data, generate_salt
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
        key = derive_key("legacy_pass", salt)
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
        key = derive_key("pass", salt)
        payload = json.dumps({"version": 1, "entries": []}).encode()
        nonce, ciphertext = encrypt_data(key, payload)
        (legacy_dir / "vault.puny").write_bytes(salt + nonce + ciphertext)

        load_vault("pass")
        load_vault("pass")
        load_vault("pass")

        assert list_vaults() == ["default"]
