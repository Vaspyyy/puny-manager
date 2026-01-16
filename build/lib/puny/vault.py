
from .paths import get_data_dir, get_vault_path
from .storage import save_vault
from .i18n import t

INITIAL_VAULT = {
    "version": 1,
    "entries": []
}

def init_vault(master_password: str) -> None:
    data_dir = get_data_dir()
    vault_path = get_vault_path()

    if vault_path.exists():
        raise FileExistsError(t("vault_exists"))

    data_dir.mkdir(parents=True, exist_ok=True)
    save_vault(master_password, INITIAL_VAULT)

