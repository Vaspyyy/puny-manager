from pathlib import Path
import os

APP_NAME = "puny-manager"

def get_data_dir() -> Path:
    base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    return base / APP_NAME

def get_vault_path() -> Path:
    return get_data_dir() / "vault.puny"

def get_config_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME

def get_lang_path() -> Path:
    return get_config_dir() / "lang"
