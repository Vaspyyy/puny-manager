import json
from pathlib import Path

import pytest

from puny.config import get_config, set_config
from puny.vault import PunyError


class TestConfig:
    def test_get_default_config(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.config._config_path", lambda: tmp_path / "config.json")
        config = get_config()
        assert config["default_length"] == 20
        assert config["backup_count"] == 5
        assert config["clipboard_timeout"] == 15

    def test_set_config(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.config._config_path", lambda: tmp_path / "config.json")
        set_config("default_length", 32)
        config = get_config()
        assert config["default_length"] == 32

    def test_set_config_persists(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.config._config_path", lambda: tmp_path / "config.json")
        set_config("default_length", 32)
        
        from puny.config import _config_path
        config_file = _config_path()
        assert config_file.exists()
        data = json.loads(config_file.read_text())
        assert data["default_length"] == 32

    def test_set_invalid_key_raises_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.config._config_path", lambda: tmp_path / "config.json")
        with pytest.raises(PunyError) as exc:
            set_config("invalid_key", "value")
        assert exc.value.key == "invalid_config_key"

    def test_set_invalid_value_raises_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.config._config_path", lambda: tmp_path / "config.json")
        with pytest.raises(PunyError) as exc:
            set_config("default_length", "not_a_number")
        assert exc.value.key == "invalid_config_value"

    def test_set_negative_value_raises_error(self, monkeypatch, tmp_path):
        monkeypatch.setattr("puny.config._config_path", lambda: tmp_path / "config.json")
        with pytest.raises(PunyError) as exc:
            set_config("default_length", -1)
        assert exc.value.key == "invalid_config_value"
