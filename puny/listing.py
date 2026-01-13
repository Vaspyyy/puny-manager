
from .storage import load_vault

def list_entries(master_password: str) -> list[str]:
    vault = load_vault(master_password)
    return [entry["name"] for entry in vault["entries"]]

