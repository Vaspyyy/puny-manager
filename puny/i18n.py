from pathlib import Path
import os

APP_NAME = "puny-manager"

def get_lang_path() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME / "lang"

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
        "entry_url": "URL (optional): ",
        "entry_tags": "Tags (comma-separated, optional): ",

        # init
        "password_mismatch": "Passwords do not match.",
        "master_password_too_short": "Master password must be at least 4 characters.",
#        "master_password_requirements": "Master password must include upper, lower, digit, and symbol.",
        "vault_created": "Vault created successfully.",
        "vault_exists": "Vault already exists.",

        # list
        "no_entries": "No entries found.",
        "stored_entries": "Stored entries:",

        # add
        "entry_saved": "Entry '{name}' saved.",
        "entry_notes": "Notes (optional): ",

        # get
        "entry_not_found": "Entry '{name}' not found.",
        "password_copied": "Password copied to clipboard.",
        "clipboard_clearing": "Clipboard will be cleared in {seconds} seconds.",

        # remove
        "entry_removed": "Entry '{name}' removed.",

        # generator
        "password_length_error": "Password length must be at least 8.",

        # vault / storage errors
        "vault_missing": "Vault does not exist.",
        "vault_corrupt": "Vault file is corrupted.",
        "vault_decrypt_failed": "Vault could not be decrypted.",
        "entry_exists": "Entry '{name}' already exists.",


        # edits
        "vault_updated": "Master password updated.",
        "cmd_edit": "Edit an entry",
        "editing_entry": "Editing entry:",
        "entry_updated": "Entry '{name}' updated.",
        "leave_empty": "leave empty to keep",

        # argparse / help
        "cmd_init": "Initialize a new vault",
        "cmd_list": "List entries",
        "cmd_add": "Add a new entry",
        "cmd_get": "Show an entry",
        "cmd_gen": "Generate a secure password",
        "cmd_rm": "Remove an entry",
        "cmd_lang": "Set language",
        "cmd_passwd": "Change master password",

        "arg_name": "Entry name",
        "arg_length": "Password length (default: 20)",
        "arg_copy": "Copy password to clipboard",
        "arg_timeout": "Clipboard clear timeout in seconds (default: 15)",

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
        "entry_url": "URL (optional): ",
        "entry_tags": "Tags (kommagetrennt, optional): ",

        # init
        "password_mismatch": "Passwörter stimmen nicht überein.",
        "master_password_too_short": "Master-Passwort muss mindestens 4 Zeichen haben.",
#        "master_password_requirements": "Master-Passwort braucht Groß-/Kleinbuchstaben, Zahl und Symbol.",
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
        "clipboard_clearing": "Zwischenablage wird in {seconds} Sekunden geleert.",
        "entry_notes": "Notizen (optional): ",

        # remove
        "entry_removed": "Eintrag '{name}' entfernt.",

        # generator
        "password_length_error": "Passwortlänge muss mindestens 8 sein.",

        # vault / storage errors
        "vault_missing": "Vault existiert nicht.",
        "vault_corrupt": "Vault-Datei ist beschädigt.",
        "vault_decrypt_failed": "Vault konnte nicht entschlüsselt werden.",

        # edits
        "vault_updated": "Master-Passwort aktualisiert.",
        "cmd_edit": "Eintrag bearbeiten",
        "editing_entry": "Bearbeite Eintrag:",
        "entry_updated": "Eintrag '{name}' aktualisiert.",
        "leave_empty": "leer lassen zum Behalten",



        # argparse / help
        "cmd_init": "Neue Vault erstellen",
        "cmd_list": "Einträge auflisten",
        "cmd_add": "Eintrag hinzufügen",
        "cmd_get": "Eintrag anzeigen",
        "cmd_gen": "Sicheres Passwort generieren",
        "cmd_rm": "Eintrag entfernen",
        "cmd_lang": "Sprache setzen",
        "cmd_passwd": "Master Passwort ändern",

        "arg_name": "Name des Eintrags",
        "arg_length": "Passwortlänge (Standard: 20)",
        "arg_copy": "Passwort in die Zwischenablage kopieren",
        "arg_timeout": "Zwischenablage nach Sekunden leeren (Standard: 15)",

        # lang
        "lang_set": "Sprache gesetzt auf {lang}",
    },

    "ru": {
        # generic
        "error_prefix": "✗ Ошибка: ",
        "success_prefix": "✓ ",

        # prompts
        "master_password": "Мастер-пароль: ",
        "set_master_password": "Установить мастер-пароль: ",
        "repeat_master_password": "Повторите мастер-пароль: ",
        "entry_name": "Имя: ",
        "entry_username": "Имя пользователя / Email: ",
        "entry_password": "Пароль: ",
        "entry_url": "URL (необязательно): ",
        "entry_tags": "Теги (через запятую, необязательно): ",

        # init
        "password_mismatch": "Пароли не совпадают.",
        "master_password_too_short": "Мастер-пароль должен быть не менее 4 символов.",
#        "master_password_requirements": "Мастер-пароль должен содержать регистр, цифру и символ.",
        "vault_created": "Хранилище успешно создано.",
        "vault_exists": "Хранилище уже существует.",

        # list
        "no_entries": "Записи не найдены.",
        "stored_entries": "Сохранённые записи:",

        # add
        "entry_saved": "Запись '{name}' сохранена.",
        "entry_notes": "Заметки (необязательно): ",

        # get
        "entry_not_found": "Запись '{name}' не найдена.",
        "password_copied": "Пароль скопирован в буфер обмена.",
        "clipboard_clearing": "Буфер обмена будет очищен через {seconds} секунд.",

        # remove
        "entry_removed": "Запись '{name}' удалена.",

        # generator
        "password_length_error": "Длина пароля должна быть не менее 8.",

        # vault / storage errors
        "vault_missing": "Хранилище не существует.",
        "vault_corrupt": "Файл хранилища повреждён.",
        "vault_decrypt_failed": "Не удалось расшифровать хранилище.",

        # edits
        "vault_updated": "Мастер-пароль обновлён.",
        "cmd_edit": "Редактировать запись",
        "editing_entry": "Редактирование записи:",
        "entry_updated": "Запись '{name}' обновлена.",
        "leave_empty": "оставьте пустым, чтобы сохранить",


        # argparse / help
        "cmd_init": "Создать новое хранилище",
        "cmd_list": "Показать список записей",
        "cmd_add": "Добавить новую запись",
        "cmd_get": "Показать запись",
        "cmd_gen": "Сгенерировать безопасный пароль",
        "cmd_rm": "Удалить запись",
        "cmd_lang": "Установить язык",
        "cmd_passwd": "Изменить мастер-пароль",

        "arg_name": "Имя записи",
        "arg_length": "Длина пароля (по умолчанию: 20)",
        "arg_copy": "Скопировать пароль в буфер обмена",
        "arg_timeout": "Очистить буфер обмена через N секунд (по умолчанию: 15)",

        # lang
        "lang_set": "Язык установлен на {lang}",
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
