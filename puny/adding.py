
from .storage import load_vault, save_vault

def add_entry(master_password: str, name: str, username: str, password: str) -> None:
    vault = load_vault(master_password)

    for entry in vault["entries"]:
        if entry["name"] == name:
            raise ValueError(f"Eintrag '{name}' existiert bereits")

    vault["entries"].append({
        "name": name,
        "username": username,
        "password": password
    })

    save_vault(master_password, vault)

