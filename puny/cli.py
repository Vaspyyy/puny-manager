import argparse
import shutil
import subprocess
from getpass import getpass

from .i18n import get_lang, t
from .storage import config_dir, init_vault, lang_path, load_vault, save_vault
from .util import (
    check_master_password,
    generate_password,
    schedule_clipboard_clear,
    smart_find,
)
from .vault import Entry, PunyError
from .version import get_version

def copy_to_clipboard(text: str) -> bool:
    if shutil.which("wl-copy"):
        subprocess.run(
            ["wl-copy"],
            input=text,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True

    if shutil.which("xclip"):
        subprocess.run(
            ["xclip", "-selection", "clipboard"],
            input=text,
            text=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True

    return False


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
    g.add_argument("--timeout", type=int, default=15, help=t("arg_timeout"))

    r = sp.add_parser("rm", help=t("cmd_rm"))
    r.add_argument("name", help=t("arg_name"))

    gen = sp.add_parser("gen", help=t("cmd_gen"))
    gen.add_argument("length", nargs="?", type=int, default=20)

    lang = sp.add_parser("lang", help=t("cmd_lang"))
    lang.add_argument("lang", nargs="?", choices=["en", "de", "ru"])

    e = sp.add_parser("edit", help=t("cmd_edit"))
    e.add_argument("name", help=t("arg_name"))

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
            err, warn = check_master_password(a)
            if err:
                raise PunyError(err)

            if warn:
                choice = input(t(warn)).strip().lower()
                if choice != "y":
                    return

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
                input(t("entry_url")).strip(),
                [t.strip() for t in input(t("entry_tags")).split(",") if t.strip()],
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
            if e.url:
                print(f"URL: {e.url}")
            if e.tags:
                print(f"Tags: {', '.join(e.tags)}")
            if args.copy:
                if not copy_to_clipboard(e.password):
                    raise PunyError("clipboard_unavailable")

                schedule_clipboard_clear(args.timeout)
                print(t("password_copied"))
                if args.timeout > 0:
                    print(t("clipboard_clearing", seconds=args.timeout))
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
            err, warn = check_master_password(a)
            if err:
                raise PunyError(err)

            if warn:
                choice = input(t(warn)).strip().lower()
                if choice != "y":
                    return

            save_vault(a, v)
            print(t("vault_updated"))


        elif args.cmd == "edit":
            m = getpass(t("master_password"))
            v = load_vault(m)

            old = smart_find(v.entries, args.name)
            if not old:
                raise PunyError("entry_not_found")

            print(f"{t('editing_entry')} {old.name}")

            username = input(f"{t('entry_username')} [{old.username}]: ").strip()
            password = getpass(f"{t('entry_password')} ({t('leave_empty')}): ")
            notes = input(f"{t('entry_notes')} [{old.notes}]: ").strip()
            url = input(f"{t('entry_url')} [{old.url}]: ").strip()
            tags_text = input(f"{t('entry_tags')} [{', '.join(old.tags)}]: ").strip()
            tags = [t.strip() for t in tags_text.split(",") if t.strip()]

            new = Entry(
                name=old.name,
                username=username or old.username,
                password=password or old.password,
                notes=notes or old.notes,
                url=url or old.url,
                tags=tags or old.tags,
            )
            v.update(old.name, new)
            save_vault(m, v)
            print(t("entry_updated", name=old.name))

    except PunyError as e:
        print(t("error_prefix") + t(str(e)))
    except Exception as e:
        print(t("error_prefix") + str(e))


if __name__ == "__main__":
    main()
