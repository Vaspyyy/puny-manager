
import argparse
import pyperclip

from getpass import getpass

from .vault import init_vault
from .listing import list_entries
from .adding import add_entry
from .getting import get_entry
from .generator import generate_password
from .removing import remove_entry
from .i18n import t
from .passwd import change_master_password
from .version import get_version

def ask_master_password() -> str:
    return getpass(t("master_password"))


def main():
    parser = argparse.ArgumentParser(
        prog="puny",
        description="Puny Manager – a minimal password manager"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help=t("cmd_init"))
    subparsers.add_parser("list", help=t("cmd_list"))
    subparsers.add_parser("add", help=t("cmd_add"))
    subparsers.add_parser("passwd", help=t("cmd_passwd"))

    get_parser = subparsers.add_parser("get", help=t("cmd_get"))
    get_parser.add_argument("name", help=t("arg_name"))
    get_parser.add_argument(
            "--copy",
            action="store_true",
            help="Kopiert das Password in die Zwischenablage"
    )


    gen_parser = subparsers.add_parser("gen", help=t("cmd_gen"))
    gen_parser.add_argument(
            "length",
            nargs="?", 
            type=int,
            default=20,
            help=t("arg_length")
    )

    rm_parser = subparsers.add_parser(
            "rm",
            help="Entfernt einen Eintrag"
    )
    rm_parser.add_argument(
            "name",
            help="Name des Eintrags"
    )

    lang_parser = subparsers.add_parser("lang", help="Set language")
    lang_parser.add_argument("lang", choices=["en", "de", "ru"])

    args = parser.parse_args()

    if args.command == "init":
        pw1 = getpass(t("set_master_password"))
        pw2 = getpass(t("repeat_master_password"))


        if pw1 != pw2:
            print(t("password_mismatch"))
            return

        try:
            init_vault(pw1)
            print(t("vault_created"))
        except FileExistsError as e:
            print(f"✗ Fehler: {e}")

    elif args.command == "list":
        master = ask_master_password()
        try:
            entries = list_entries(master)
            if not entries:
                print(t("no_entries"))
            else:
                print(t("stored_entries"))
                for name in entries:
                    print(f"- {name}")
        except Exception as e:
            print(f"✗ Fehler: {e}")

    elif args.command == "add":
        master = ask_master_password()

        name = input(t("entry_name")).strip()
        username = input(t("entry_username")).strip()
        password = getpass(t("entry_password"))
        notes = input(t("entry_notes")).strip()

        try:
            add_entry(master, name, username, password, notes)
            print(t("entry_saved", name=name))
        except Exception as e:
            print(f"{t('error_prefix')}{e}")


    elif args.command == "get":
        master = ask_master_password()
        try:
            entry = get_entry(master, args.name)
            print(f"Name: {entry['name']}")
            print(f"Username: {entry['username']}")

            if entry.get("notes"):                ###############
                print(f"Notes: {entry['notes']}") ###############

            if args.copy:
                pyperclip.copy(entry["password"])
                print(t("password_copied"))
            else:
                print(f"Passwort: {entry['password']}")
        except Exception as e:
            print(f"✗ Fehler: {e}")

    elif args.command == "gen":
        try:
            password = generate_password(args.length)
            print(password)
        except ValueError as e:
            print(f"✗ Fehler: {e}")

    elif args.command == "rm":
        master = ask_master_password()
        try:
            remove_entry(master, args.name)
            print(t("entry_removed", name=args.name))
        except Exception as e:
            print(f"✗ Fehler: {e}")

    elif args.command == "lang":
        from .paths import get_config_dir, get_lang_path

        cfg = get_config_dir()
        cfg.mkdir(parents=True, exist_ok=True)
        get_lang_path().write_text(args.lang)
        print(t("lang_set", lang=args.lang))

    elif args.command == "passwd":
        try:
            change_master_password()
            print(t("vault_updated"))
        except Exception as e:
            print(f"{t('error_prefix')}{e}")



if __name__ == "__main__":
    main()

