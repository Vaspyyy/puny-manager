
from .storage import load_vault
from .i18n import t

def get_entry(master_password: str, name: str) -> dict:
    vault = load_vault(master_password)

    for entry in vault["entries"]:
        if entry["name"] == name:
            return entry

    raise KeyError(t("entry_not_found", name=name))

