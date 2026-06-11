import json
from pathlib import Path

from .storage import config_dir
from .vault import PunyError

DEFAULTS = {
    "default_length": 20,
    "backup_count": 5,
    "clipboard_timeout": 15,
}

VALID_KEYS = set(DEFAULTS.keys())


def _config_path() -> Path:
    return config_dir() / "config.json"


def get_config() -> dict:
    path = _config_path()
    if not path.exists():
        return DEFAULTS.copy()
    try:
        data = json.loads(path.read_text())
        config = DEFAULTS.copy()
        config.update(data)
        return config
    except (json.JSONDecodeError, UnicodeDecodeError):
        return DEFAULTS.copy()


def set_config(key: str, value: int) -> None:
    if key not in VALID_KEYS:
        raise PunyError("invalid_config_key", config_key=key)

    if not isinstance(value, int) or value < 0:
        raise PunyError("invalid_config_value", config_key=key)

    config = get_config()
    config[key] = value

    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(config, indent=2))
