from .paths import get_lang_path

STRINGS = {
    "en": {
        # generic
        "error_prefix": "✗ Error: ",
        "success_prefix": "✓ ",

        # prompts
        "master_password": "Master password: ",
        "set_master_password": "Set master password: ",
        "repeat_master_password": "Repeat master password: ",
        "entry_name": "Name: ",
        "entry_username": "Username / Email: ",
        "entry_password": "Password: ",

        # init
        "password_mismatch": "Passwords do not match.",
        "vault_created": "Vault created successfully.",
        "vault_exists": "Vault already exists.",

        # list
        "no_entries": "No entries found.",
        "stored_entries": "Stored entries:",

        # add
        "entry_saved": "Entry '{name}' saved.",

        # get
        "entry_not_found": "Entry '{name}' not found.",
        "password_copied": "Password copied to clipboard.",

        # remove
        "entry_removed": "Entry '{name}' removed.",

        # generator
        "password_length_error": "Password length must be at least 8.",

        # vault / storage errors
        "vault_missing": "Vault does not exist.",
        "vault_corrupt": "Vault file is corrupted.",
        "vault_decrypt_failed": "Vault could not be decrypted.",

        # argparse / help
        "cmd_init": "Initialize a new vault",
        "cmd_list": "List entries",
        "cmd_add": "Add a new entry",
        "cmd_get": "Show an entry",
        "cmd_gen": "Generate a secure password",
        "cmd_rm": "Remove an entry",
        "cmd_lang": "Set language",

        "arg_name": "Entry name",
        "arg_length": "Password length (default: 20)",
        "arg_copy": "Copy password to clipboard",

        # lang
        "lang_set": "Language set to {lang}",
    },

    "de": {
        # generic
        "error_prefix": "✗ Fehler: ",
        "success_prefix": "✓ ",

        # prompts
        "master_password": "Master-Passwort: ",
        "set_master_password": "Master-Passwort festlegen: ",
        "repeat_master_password": "Master-Passwort wiederholen: ",
        "entry_name": "Name: ",
        "entry_username": "Benutzername / E-Mail: ",
        "entry_password": "Passwort: ",

        # init
        "password_mismatch": "Passwörter stimmen nicht überein.",
        "vault_created": "Vault erfolgreich erstellt.",
        "vault_exists": "Vault existiert bereits.",

        # list
        "no_entries": "Keine Einträge vorhanden.",
        "stored_entries": "Gespeicherte Einträge:",

        # add
        "entry_saved": "Eintrag '{name}' gespeichert.",

        # get
        "entry_not_found": "Eintrag '{name}' nicht gefunden.",
        "password_copied": "Passwort wurde in die Zwischenablage kopiert.",

        # remove
        "entry_removed": "Eintrag '{name}' entfernt.",

        # generator
        "password_length_error": "Passwortlänge muss mindestens 8 sein.",

        # vault / storage errors
        "vault_missing": "Vault existiert nicht.",
        "vault_corrupt": "Vault-Datei ist beschädigt.",
        "vault_decrypt_failed": "Vault konnte nicht entschlüsselt werden.",

        # argparse / help
        "cmd_init": "Neue Vault erstellen",
        "cmd_list": "Einträge auflisten",
        "cmd_add": "Eintrag hinzufügen",
        "cmd_get": "Eintrag anzeigen",
        "cmd_gen": "Sicheres Passwort generieren",
        "cmd_rm": "Eintrag entfernen",
        "cmd_lang": "Sprache setzen",

        "arg_name": "Name des Eintrags",
        "arg_length": "Passwortlänge (Standard: 20)",
        "arg_copy": "Passwort in die Zwischenablage kopieren",

        # lang
        "lang_set": "Sprache gesetzt auf {lang}",
    },
}

def get_lang() -> str:
    try:
        return get_lang_path().read_text().strip()
    except FileNotFoundError:
        return "en"

def t(key: str, **kwargs) -> str:
    lang = get_lang()
    if key not in STRINGS.get(lang, {}):
        raise KeyError(f"Missing i18n key: {key}")
    return STRINGS[lang][key].format(**kwargs)
