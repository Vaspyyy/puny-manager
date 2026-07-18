import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .storage import load_vault, save_vault
from .vault import Entry, PunyError, Vault


def export_json(master_password: str, vault_name: str, export_path: Path) -> None:
    vault = load_vault(master_password, name=vault_name)
    export_json_vault(vault, export_path)


def export_json_vault(vault: Vault, export_path: Path) -> None:

    data = {
        "version": vault.version,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "entries": [],
    }

    for entry in vault.entries:
        data["entries"].append(
            {
                "name": entry.name,
                "username": entry.username,
                "password": entry.password,
                "notes": entry.notes,
                "url": entry.url,
                "tags": entry.tags,
                "custom_fields": entry.custom_fields,
            }
        )

    export_path.write_text(json.dumps(data, indent=2))


def import_json(master_password: str, vault_name: str, import_path: Path) -> None:
    vault = load_vault(master_password, name=vault_name)
    import_json_vault(vault, import_path)
    save_vault(master_password, vault)


def import_json_vault(vault: Vault, import_path: Path) -> None:
    try:
        data = json.loads(import_path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise PunyError("invalid_export_format") from None

    if not isinstance(data, dict) or "entries" not in data:
        raise PunyError("invalid_export_format")

    if not isinstance(data["entries"], list):
        raise PunyError("invalid_export_format")

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


def export_csv(master_password: str, vault_name: str, export_path: Path) -> None:
    vault = load_vault(master_password, name=vault_name)
    export_csv_vault(vault, export_path)


def export_csv_vault(vault: Vault, export_path: Path) -> None:

    with open(export_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["name", "username", "password", "notes", "url", "tags", "custom_fields"]
        )
        writer.writeheader()
        for entry in vault.entries:
            writer.writerow(
                {
                    "name": entry.name,
                    "username": entry.username,
                    "password": entry.password,
                    "notes": entry.notes,
                    "url": entry.url,
                    "tags": ",".join(entry.tags),
                    "custom_fields": json.dumps(entry.custom_fields),
                }
            )


def import_csv(master_password: str, vault_name: str, import_path: Path) -> None:
    vault = load_vault(master_password, name=vault_name)
    import_csv_vault(vault, import_path)
    save_vault(master_password, vault)


def import_csv_vault(vault: Vault, import_path: Path) -> None:
    try:
        with open(import_path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except (csv.Error, UnicodeDecodeError):
        raise PunyError("invalid_export_format") from None

    if not rows:
        return

    for row in rows:
        try:
            tags = [t.strip() for t in row.get("tags", "").split(",") if t.strip()]
            custom_fields = (
                json.loads(row.get("custom_fields", "{}")) if row.get("custom_fields") else {}
            )

            entry = Entry(
                name=row["name"],
                username=row.get("username", ""),
                password=row["password"],
                notes=row.get("notes", ""),
                url=row.get("url", ""),
                tags=tags,
                custom_fields=custom_fields,
            )
        except (TypeError, KeyError, json.JSONDecodeError):
            raise PunyError("invalid_export_format") from None

        vault.add(entry)
