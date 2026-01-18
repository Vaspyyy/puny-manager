import argparse
import pyperclip
from getpass import getpass
from .storage import load_vault, save_vault, init_vault, lang_path, config_dir
from .vault import Entry, PunyError
from .util import generate_password, smart_find
from .i18n import t, get_lang
from .version import get_version

def main():
    p = argparse.ArgumentParser(prog="puny-manager")
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
    )

    sp = p.add_subparsers(dest="cmd", required=True)

    sp.add_parser("init", help=t("cmd_init"))
    sp.add_parser("list", help=t("cmd_list"))
    sp.add_parser("add", help=t("cmd_add"))
    sp.add_parser("passwd", help=t("cmd_passwd"))

    g = sp.add_parser("get", help=t("cmd_get"))
    g.add_argument("name", help=t("arg_name"))
    g.add_argument("--copy", action="store_true")

    r = sp.add_parser("rm", help=t("cmd_rm"))
    r.add_argument("name", help=t("arg_name"))

    gen = sp.add_parser("gen", help=t("cmd_gen"))
    gen.add_argument("length", nargs="?", type=int, default=20)

    lang = sp.add_parser("lang", help=t("cmd_lang"))
    lang.add_argument("lang", nargs="?", choices=["en", "de", "ru"])

    args = p.parse_args()

    try:
        if args.cmd == "lang":
            if args.lang is None:
                print(get_lang())
                return
            config_dir().mkdir(parents=True, exist_ok=True)
            lang_path().write_text(args.lang)
            print(t("lang_set", lang=args.lang))

        elif args.cmd == "init":
            a = getpass(t("set_master_password"))
            b = getpass(t("repeat_master_password"))
            if a != b:
                raise PunyError("password_mismatch")
            init_vault(a)
            print(t("vault_created"))

        elif args.cmd == "list":
            v = load_vault(getpass(t("master_password")))
            if not v.entries:
                print(t("no_entries"))
            else:
                print(t("stored_entries"))
                for n in v.list():
                    print(f"- {n}")

        elif args.cmd == "add":
            m = getpass(t("master_password"))
            v = load_vault(m)
            e = Entry(
                input(t("entry_name")).strip(),
                input(t("entry_username")).strip(),
                getpass(t("entry_password")),
                input(t("entry_notes")).strip(),
            )
            v.add(e)
            save_vault(m, v)
            print(t("entry_saved", name=e.name))

        elif args.cmd == "get":
            m = getpass(t("master_password"))
            v = load_vault(m)
            e = smart_find(v.entries, args.name)
            if not e:
                raise PunyError("entry_not_found")
            print(f"Name: {e.name}")
            print(f"Username: {e.username}")
            if e.notes:
                print(f"Notes: {e.notes}")
            if args.copy:
                pyperclip.copy(e.password)
                print(t("password_copied"))
            else:
                print(f"Password: {e.password}")

        elif args.cmd == "rm":
            m = getpass(t("master_password"))
            v = load_vault(m)
            v.remove(args.name)
            save_vault(m, v)
            print(t("entry_removed", name=args.name))

        elif args.cmd == "gen":
            print(generate_password(args.length))

        elif args.cmd == "passwd":
            old = getpass(t("master_password"))
            v = load_vault(old)
            a = getpass(t("set_master_password"))
            b = getpass(t("repeat_master_password"))
            if a != b:
                raise PunyError("password_mismatch")
            save_vault(a, v)
            print(t("vault_updated"))

    except PunyError as e:
        print(t("error_prefix") + t(str(e)))
    except Exception:
        print(t("error_prefix") + t("vault_decrypt_failed"))

if __name__ == "__main__":
    main()
