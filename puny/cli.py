import argparse
import shutil
import subprocess
from getpass import getpass

from .i18n import STRINGS, get_lang, t
from .storage import config_dir, init_vault, lang_path, load_vault, remove_backup, save_vault
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


def cmd_lang(args: argparse.Namespace) -> None:
    if args.lang is None:
        current = get_lang()
        print(f"{t('current_language')}: {current}")
        codes = list(STRINGS.keys())
        print(f"{t('available_languages')}: {' | '.join(codes)}")
        return
    config_dir().mkdir(parents=True, exist_ok=True)
    lang_path().write_text(args.lang)
    print(t("lang_set", lang=args.lang))


def cmd_init(args: argparse.Namespace) -> None:
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


def cmd_list(args: argparse.Namespace) -> None:
    v = load_vault(getpass(t("master_password")))
    if not v.entries:
        print(t("no_entries"))
    else:
        print(t("stored_entries"))
        for n in v.list():
            print(f"- {n}")


def _prompt_entry_interactive() -> Entry:
    name = input(t("entry_name")).strip()
    if not name:
        raise PunyError("entry_name_required")
    return Entry(
        name=name,
        username=input(t("entry_username")).strip(),
        password=getpass(t("entry_password")),
        notes=input(t("entry_notes")).strip(),
        url=input(t("entry_url")).strip(),
        tags=[tag.strip() for tag in input(t("entry_tags")).split(",") if tag.strip()],
    )


def cmd_add(args: argparse.Namespace) -> None:
    m = getpass(t("master_password"))
    v = load_vault(m)
    e = _prompt_entry_interactive()
    v.add(e)
    save_vault(m, v)
    print(t("entry_saved", name=e.name))


def cmd_get(args: argparse.Namespace) -> None:
    m = getpass(t("master_password"))
    v = load_vault(m)
    e = smart_find(v.entries, args.name)
    if not e:
        raise PunyError("entry_not_found", name=args.name)
    print(f"Name: {e.name}")
    print(f"Username: {e.username}")
    if e.notes:
        print(f"Notes: {e.notes}")
    if e.url:
        print(f"URL: {e.url}")
    if e.tags:
        print(f"Tags: {', '.join(e.tags)}")
    if not copy_to_clipboard(e.password):
        raise PunyError("clipboard_unavailable")

    schedule_clipboard_clear(args.timeout)
    print(t("password_copied"))
    if args.timeout > 0:
        print(t("clipboard_clearing", seconds=args.timeout))


def cmd_rm(args: argparse.Namespace) -> None:
    m = getpass(t("master_password"))
    v = load_vault(m)
    e = smart_find(v.entries, args.name)
    if not e:
        raise PunyError("entry_not_found", name=args.name)
    v.remove(e.name)
    save_vault(m, v)
    print(t("entry_removed", name=e.name))


def cmd_gen(args: argparse.Namespace) -> None:
    if args.length < 8:
        raise PunyError("password_length_error")
    print(generate_password(args.length))


def cmd_passwd(args: argparse.Namespace) -> None:
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

    remove_backup()
    save_vault(a, v)
    print(t("vault_updated"))


def cmd_edit(args: argparse.Namespace) -> None:
    m = getpass(t("master_password"))
    v = load_vault(m)

    old = smart_find(v.entries, args.name)
    if not old:
        raise PunyError("entry_not_found", name=args.name)

    print(f"{t('editing_entry')} {old.name}")

    username = input(f"{t('entry_username')} [{old.username}]: ").strip()
    password = getpass(f"{t('entry_password')} ({t('leave_empty')}): ")
    notes = input(f"{t('entry_notes')} [{old.notes}]: ").strip()
    url = input(f"{t('entry_url')} [{old.url}]: ").strip()
    tags_text = input(f"{t('entry_tags')} [{', '.join(old.tags)}]: ").strip()
    tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

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


def main() -> None:
    p = argparse.ArgumentParser(prog="puny-manager")
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
    )

    sp = p.add_subparsers(dest="cmd", required=True)

    sp_init = sp.add_parser("init", help=t("cmd_init"))
    sp_init.set_defaults(func=cmd_init)

    sp_list = sp.add_parser("list", help=t("cmd_list"))
    sp_list.set_defaults(func=cmd_list)

    sp_add = sp.add_parser("add", help=t("cmd_add"))
    sp_add.set_defaults(func=cmd_add)

    sp_get = sp.add_parser("get", help=t("cmd_get"))
    sp_get.add_argument("name", help=t("arg_name"))
    sp_get.add_argument("--timeout", type=int, default=15, help=t("arg_timeout"))
    sp_get.set_defaults(func=cmd_get)

    sp_rm = sp.add_parser("rm", help=t("cmd_rm"))
    sp_rm.add_argument("name", help=t("arg_name"))
    sp_rm.set_defaults(func=cmd_rm)

    sp_gen = sp.add_parser("gen", help=t("cmd_gen"))
    sp_gen.add_argument("length", nargs="?", type=int, default=20)
    sp_gen.set_defaults(func=cmd_gen)

    sp_lang = sp.add_parser("lang", help=t("cmd_lang"))
    sp_lang.add_argument("lang", nargs="?", choices=["en", "de", "fr", "es", "ru", "pt", "zh"])
    sp_lang.set_defaults(func=cmd_lang)

    sp_passwd = sp.add_parser("passwd", help=t("cmd_passwd"))
    sp_passwd.set_defaults(func=cmd_passwd)

    sp_edit = sp.add_parser("edit", help=t("cmd_edit"))
    sp_edit.add_argument("name", help=t("arg_name"))
    sp_edit.set_defaults(func=cmd_edit)

    args = p.parse_args()

    try:
        args.func(args)
    except PunyError as e:
        print(t("error_prefix") + t(e.key, **e.kwargs))
    except Exception as e:
        print(t("error_prefix") + str(e))


if __name__ == "__main__":
    main()
