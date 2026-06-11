import json
import os
from pathlib import Path

import pytest

from puny.export import export_json, import_json
from puny.storage import create_vault, load_vault, save_vault, vault_path
from puny.vault import Entry, PunyError


class TestExportJson:
    def test_export_empty_vault(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "export_test")
        export_path = tmp_path / "export.json"

        export_json("password123!", "export_test", export_path)

        assert export_path.exists()
        data = json.loads(export_path.read_text())
        assert data["version"] == 1
        assert data["entries"] == []
        assert "exported_at" in data

    def test_export_vault_with_entries(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        create_vault("password123!", "export_test")
        vault = load_vault("password123!", name="export_test")
        vault.add(Entry(
            name="github",
            username="dev",
            password="secret",
            notes="work account",
            url="https://github.com",
            tags=["work", "git"],
            custom_fields={"api_key": "abc123"},
        ))
        save_vault("password123!", vault)

        export_path = tmp_path / "export.json"
        export_json("password123!", "export_test", export_path)

        data = json.loads(export_path.read_text())
        assert len(data["entries"]) == 1
        entry = data["entries"][0]
        assert entry["name"] == "github"
        assert entry["username"] == "dev"
        assert entry["password"] == "secret"
        assert entry["notes"] == "work account"
        assert entry["url"] == "https://github.com"
        assert entry["tags"] == ["work", "git"]
        assert entry["custom_fields"] == {"api_key": "abc123"}


class TestImportJson:
    def test_import_empty_vault(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        export_path = tmp_path / "export.json"
        export_path.write_text(json.dumps({
            "version": 1,
            "exported_at": "2026-06-11T14:30:00Z",
            "entries": [],
        }))

        create_vault("password123!", "import_test")
        import_json("password123!", "import_test", export_path)

        vault = load_vault("password123!", name="import_test")
        assert len(vault.entries) == 0

    def test_import_vault_with_entries(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        export_path = tmp_path / "export.json"
        export_path.write_text(json.dumps({
            "version": 1,
            "exported_at": "2026-06-11T14:30:00Z",
            "entries": [
                {
                    "name": "github",
                    "username": "dev",
                    "password": "secret",
                    "notes": "work account",
                    "url": "https://github.com",
                    "tags": ["work", "git"],
                    "custom_fields": {"api_key": "abc123"},
                }
            ],
        }))

        create_vault("password123!", "import_test")
        import_json("password123!", "import_test", export_path)

        vault = load_vault("password123!", name="import_test")
        assert len(vault.entries) == 1
        entry = vault.entries[0]
        assert entry.name == "github"
        assert entry.username == "dev"
        assert entry.password == "secret"
        assert entry.notes == "work account"
        assert entry.url == "https://github.com"
        assert entry.tags == ["work", "git"]
        assert entry.custom_fields == {"api_key": "abc123"}

    def test_import_invalid_json_raises_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        export_path = tmp_path / "export.json"
        export_path.write_text("not json")

        create_vault("password123!", "import_test")
        with pytest.raises(PunyError) as exc:
            import_json("password123!", "import_test", export_path)
        assert exc.value.key == "invalid_export_format"

    def test_import_missing_entries_key_raises_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path)
        monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path)

        export_path = tmp_path / "export.json"
        export_path.write_text(json.dumps({"version": 1}))

        create_vault("password123!", "import_test")
        with pytest.raises(PunyError) as exc:
            import_json("password123!", "import_test", export_path)
        assert exc.value.key == "invalid_export_format"