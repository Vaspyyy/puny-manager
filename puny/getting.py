
from .storage import load_vault

def get_entry(master_password: str, name: str) -> dict:
    vault = load_vault(master_password)

    for entry in vault["entries"]:
        if entry["name"] == name:
            return entry

    raise KeyError(f"Eintrag '{name}' nicht gefunden!")

