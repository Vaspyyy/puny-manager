import json
from datetime import datetime, timezone
from pathlib import Path

from .storage import load_vault, save_vault
from .vault import Entry, PunyError


def export_json(master_password: str, vault_name: str, export_path: Path) -> None:
    vault = load_vault(master_password, name=vault_name)

    data = {
        "version": vault.version,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "entries": [],
    }

    for entry in vault.entries:
        data["entries"].append({
            "name": entry.name,
            "username": entry.username,
            "password": entry.password,
            "notes": entry.notes,
            "url": entry.url,
            "tags": entry.tags,
            "custom_fields": entry.custom_fields,
        })

    export_path.write_text(json.dumps(data, indent=2))


def import_json(master_password: str, vault_name: str, import_path: Path) -> None:
    try:
        data = json.loads(import_path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise PunyError("invalid_export_format") from None

    if not isinstance(data, dict) or "entries" not in data:
        raise PunyError("invalid_export_format")

    if not isinstance(data["entries"], list):
        raise PunyError("invalid_export_format")

    vault = load_vault(master_password, name=vault_name)

    for entry_data in data["entries"]:
        if not isinstance(entry_data, dict):
            raise PunyError("invalid_export_format")

        try:
            entry = Entry(
                name=entry_data["name"],
                username=entry_data["username"],
                password=entry_data["password"],
                notes=entry_data.get("notes", ""),
                url=entry_data.get("url", ""),
                tags=entry_data.get("tags", []),
                custom_fields=entry_data.get("custom_fields", {}),
            )
        except (TypeError, KeyError):
            raise PunyError("invalid_export_format") from None

        vault.add(entry)

    save_vault(master_password, vault)
