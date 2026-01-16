
import argparse
from getpass import getpass

from .vault import init_vault
from .listing import list_entries
from .adding import add_entry
from .getting import get_entry
from .generator import generate_password

def ask_master_password() -> str:
    return getpass("Master-Passwort: ")


def main():
    parser = argparse.ArgumentParser(
        prog="puny",
        description="Puny Manager – minimaler Passwortmanager"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init", help="Erstellt eine neue Vault")
    subparsers.add_parser("list", help="Listet Einträge")
    subparsers.add_parser("add", help="Fügt einen Eintrag hinzu")

    get_parser = subparsers.add_parser("get", help="Zeigt einen Eintrag")
    get_parser.add_argument("name", help="Name des Eintrags")


    gen_parser = subparsers.add_parser("gen", help="Generiert ein sicheres Passwort")
    gen_parser.add_argument(
            "length",
            nargs="?",
            type=int,
            default=20,
            help="Passwordlänge (STandard: 20)"
    )

    args = parser.parse_args()

    if args.command == "init":
        pw1 = getpass("Master-Passwort festlegen: ")
        pw2 = getpass("Master-Passwort wiederholen: ")

        if pw1 != pw2:
            print("✗ Passwörter stimmen nicht überein.")
            return

        try:
            init_vault(pw1)
            print("✓ Vault erfolgreich erstellt.")
        except FileExistsError as e:
            print(f"✗ Fehler: {e}")

    elif args.command == "list":
        master = ask_master_password()
        try:
            entries = list_entries(master)
            if not entries:
                print("Keine Einträge vorhanden.")
            else:
                print("Gespeicherte Einträge:")
                for name in entries:
                    print(f"- {name}")
        except Exception as e:
            print(f"✗ Fehler: {e}")

    elif args.command == "add":
        master = ask_master_password()
        name = input("Name: ").strip()
        username = input("Username / Email: ").strip()
        password = getpass("Passwort: ")

        try:
            add_entry(master, name, username, password)
            print(f"✓ Eintrag '{name}' gespeichert.")
        except Exception as e:
            print(f"✗ Fehler: {e}")

    elif args.command == "get":
        master = ask_master_password()
        try:
            entry = get_entry(master, args.name)
            print(f"Name: {entry['name']}")
            print(f"Username: {entry['username']}")
            print(f"Passwort: {entry['password']}")
        except Exception as e:
            print(f"✗ Fehler: {e}")

    elif args.command == "gen":
        try:
            password = generate_password(args.length)
            print(password)
        except ValueError as e:
            print(f"✗ Fehler: {e}")


if __name__ == "__main__":
    main()

