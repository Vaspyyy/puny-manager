import argparse
import contextlib
import shutil
import subprocess
from getpass import getpass
from pathlib import Path

from . import howdy
from .config import get_config, set_config
from .crypto import KDF_ARGON2ID, LEVEL_BALANCED, LEVEL_FAST, LEVEL_PARANOID
from .export import (
    export_csv_vault,
    export_json_vault,
    import_csv_vault,
    import_json_vault,
)
from .howdy import HowdyError
from .i18n import STRINGS, get_lang, t
from .storage import (
    config_dir,
    create_vault,
    delete_vault,
    disable_howdy_vault,
    get_active_vault,
    lang_path,
    list_vaults,
    load_vault,
    load_vault_with_key,
    prepare_howdy_enrollment,
    read_vault_header,
    remove_backup,
    save_vault,
    set_active_vault,
    vault_path,
)
from .util import (
    analyze_passwords,
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


def _require_active_vault() -> str:
    name = get_active_vault()
    if name is None:
        raise PunyError("no_active_vault")
    return name


def _get_master_password(args: argparse.Namespace) -> str:
    if hasattr(args, "master_password") and args.master_password:
        return args.master_password
    return getpass(t("master_password"))


def _howdy_reason(code: str) -> str:
    try:
        return t(f"howdy_reason_{code}")
    except KeyError:
        return t("howdy_reason_helper_failed")


def _raise_howdy(error: HowdyError) -> None:
    known_codes = {
        "helper_unavailable",
        "tpm_unavailable",
        "pam_unavailable",
        "auth_failed",
        "credential_missing",
        "credential_failed",
        "invalid_request",
        "invalid_response",
        "unsafe_storage",
    }
    code = error.code if error.code in known_codes else "helper_failed"
    raise PunyError(f"howdy_reason_{code}") from None


def _unlock_vault(args: argparse.Namespace, name: str):
    if hasattr(args, "master_password") and args.master_password:
        password = args.master_password
        return load_vault(password, name=name), password

    header = read_vault_header(name)
    if header.howdy_enabled and header.vault_id is not None:
        print(t("howdy_attempting"))
        try:
            data_key = howdy.unlock(header.vault_id)
            return load_vault_with_key(data_key, name=name), None
        except HowdyError as error:
            print(t("howdy_fallback", reason=_howdy_reason(error.code)))
        except PunyError as error:
            if error.key != "vault_decrypt_failed":
                raise
            print(t("howdy_fallback", reason=t("howdy_reason_invalid_key")))

    password = getpass(t("master_password"))
    return load_vault(password, name=name), password


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


def cmd_create(args: argparse.Namespace) -> None:
    level_map = {"fast": LEVEL_FAST, "balanced": LEVEL_BALANCED, "paranoid": LEVEL_PARANOID}

    if hasattr(args, "master_password") and args.master_password:
        a = args.master_password
        err, warn = check_master_password(a)
        if err:
            raise PunyError(err)
    else:
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

    create_vault(a, args.name, level_id=level_map[args.level])
    print(t("vault_created"))


def cmd_list(args: argparse.Namespace) -> None:
    name = _require_active_vault()
    v, _m = _unlock_vault(args, name)
    entries = v.entries
    if hasattr(args, "tag") and args.tag:
        from .util import filter_by_tag

        entries = filter_by_tag(entries, args.tag)
    if not entries:
        print(t("no_entries"))
    else:
        print(t("stored_entries"))
        for e in entries:
            print(f"- {e.name}")


def _prompt_entry_interactive(password_override: str | None = None) -> Entry:
    name = input(t("entry_name")).strip()
    if not name:
        raise PunyError("entry_name_required")
    password = password_override or getpass(t("entry_password"))
    return Entry(
        name=name,
        username=input(t("entry_username")).strip(),
        password=password,
        notes=input(t("entry_notes")).strip(),
        url=input(t("entry_url")).strip(),
        tags=[tag.strip() for tag in input(t("entry_tags")).split(",") if tag.strip()],
    )


def _create_entry_from_args(args: argparse.Namespace) -> Entry:
    if not args.entry_name:
        raise PunyError("entry_name_required")
    if not args.entry_password and not args.generate:
        raise PunyError("entry_password_required")

    password = args.entry_password
    if args.generate:
        if args.length < 8:
            raise PunyError("password_length_error")
        password = generate_password(args.length)
        copy_to_clipboard(password)
        print(t("password_generated", length=args.length))

    tags = (
        [tag.strip() for tag in args.entry_tags.split(",") if tag.strip()]
        if args.entry_tags
        else []
    )
    custom_fields = {}
    if args.custom_fields:
        for pair in args.custom_fields.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                custom_fields[key.strip()] = value.strip()

    return Entry(
        name=args.entry_name,
        username=args.entry_username or "",
        password=password,
        notes=args.entry_notes or "",
        url=args.entry_url or "",
        tags=tags,
        custom_fields=custom_fields,
    )


def cmd_add(args: argparse.Namespace) -> None:
    name = _require_active_vault()
    v, m = _unlock_vault(args, name)

    if hasattr(args, "entry_name") and args.entry_name:
        e = _create_entry_from_args(args)
    else:
        password_override = None
        if args.generate:
            if args.length < 8:
                raise PunyError("password_length_error")
            password_override = generate_password(args.length)
            copy_to_clipboard(password_override)
            print(t("password_generated", length=args.length))
        e = _prompt_entry_interactive(password_override=password_override)

    v.add(e)
    save_vault(m, v)
    print(t("entry_saved", name=e.name))


def cmd_get(args: argparse.Namespace) -> None:
    name = _require_active_vault()
    v, _m = _unlock_vault(args, name)
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
    if args.show:
        print(f"Password: {e.password}")

    if not copy_to_clipboard(e.password):
        raise PunyError("clipboard_unavailable")

    schedule_clipboard_clear(args.timeout)
    print(t("password_copied"))
    if args.timeout > 0:
        print(t("clipboard_clearing", seconds=args.timeout))


def cmd_rm(args: argparse.Namespace) -> None:
    name = _require_active_vault()
    v, m = _unlock_vault(args, name)
    e = smart_find(v.entries, args.name)
    if not e:
        raise PunyError("entry_not_found", name=args.name)
    v.remove(e.name)
    save_vault(m, v)
    print(t("entry_removed", name=e.name))


def cmd_stats(args: argparse.Namespace) -> None:
    name = _require_active_vault()
    v, _m = _unlock_vault(args, name)
    path = vault_path(name)

    stat = path.stat()
    kdf_name = "Argon2id" if v.kdf_id == KDF_ARGON2ID else "PBKDF2"
    level_names = {LEVEL_FAST: "fast", LEVEL_BALANCED: "balanced", LEVEL_PARANOID: "paranoid"}
    level_name = level_names.get(v.level_id, str(v.level_id))

    from datetime import datetime, timezone

    created = datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).strftime("%Y-%m-%d")
    modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")

    print(f"\n{t('stats_vault', name=name)}")
    print(f"  {t('stats_encryption', kdf=kdf_name, level=level_name)}")
    print(f"  {t('stats_created', date=created)}")
    print(f"  {t('stats_modified', date=modified)}")

    analysis = analyze_passwords(v.entries)
    count = analysis["count"]
    print(f"\n  {t('stats_entries', count=count)}")

    url_count = sum(1 for e in v.entries if e.url)
    notes_count = sum(1 for e in v.entries if e.notes)
    tags_count = sum(1 for e in v.entries if e.tags)
    print(f"  {t('stats_with_urls', count=url_count)}")
    print(f"  {t('stats_with_notes', count=notes_count)}")
    print(f"  {t('stats_with_tags', count=tags_count)}")

    if count > 0:
        print(f"\n  {t('stats_avg_length', n=analysis['avg_length'])}")
        print(f"  {t('stats_weak', count=analysis['weak_count'])}")
        print(f"  {t('stats_unique', count=analysis['unique_count'])}")

        dupe_sets = analysis["duplicate_sets"]
        if dupe_sets:
            dupe_desc = ", ".join(f"{len(s)}×" for s in sorted(dupe_sets, key=len, reverse=True))
            print(f"  {t('stats_duplicates', sets=len(dupe_sets))} ({dupe_desc})")
        else:
            print(f"  {t('stats_duplicates', sets=0)}")

    tag_counts: dict[str, int] = {}
    for e in v.entries:
        for tag in e.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    if tag_counts:
        tags_display = "  ".join(
            f"{tag} ({n})" for tag, n in sorted(tag_counts.items(), key=lambda x: -x[1])
        )
        print(f"\n  {t('stats_tags')}:")
        print(f"  {tags_display}")


def cmd_gen(args: argparse.Namespace) -> None:
    if args.length < 8:
        raise PunyError("password_length_error")
    pw = generate_password(args.length)
    if not copy_to_clipboard(pw):
        raise PunyError("clipboard_unavailable")
    print(t("password_generated", length=args.length))


def cmd_passwd(args: argparse.Namespace) -> None:
    name = _require_active_vault()
    old = _get_master_password(args)
    v = load_vault(old, name=name)

    if hasattr(args, "new_password") and args.new_password:
        a = args.new_password
        err, warn = check_master_password(a)
        if err:
            raise PunyError(err)
    else:
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

    remove_backup(name)
    save_vault(a, v)
    print(t("vault_updated"))


def cmd_edit(args: argparse.Namespace) -> None:
    name = _require_active_vault()
    v, m = _unlock_vault(args, name)

    old = smart_find(v.entries, args.name)
    if not old:
        raise PunyError("entry_not_found", name=args.name)

    if hasattr(args, "entry_name") and args.entry_name:
        # Non-interactive mode
        password = old.password
        if args.generate:
            if args.length < 8:
                raise PunyError("password_length_error")
            password = generate_password(args.length)
            copy_to_clipboard(password)
            print(t("password_generated", length=args.length))
        elif args.entry_password:
            password = args.entry_password

        tags = (
            [tag.strip() for tag in args.entry_tags.split(",") if tag.strip()]
            if args.entry_tags
            else old.tags
        )
        custom_fields = {}
        if args.custom_fields:
            for pair in args.custom_fields.split(","):
                if "=" in pair:
                    key, value = pair.split("=", 1)
                    custom_fields[key.strip()] = value.strip()

        new = Entry(
            name=args.entry_name,
            username=args.entry_username or old.username,
            password=password,
            notes=args.entry_notes if args.entry_notes is not None else old.notes,
            url=args.entry_url if args.entry_url is not None else old.url,
            tags=tags,
            custom_fields=custom_fields or old.custom_fields,
        )
    else:
        # Interactive mode
        print(f"{t('editing_entry')} {old.name}")
        username = input(f"{t('entry_username')} [{old.username}]: ").strip()

        if args.generate:
            if args.length < 8:
                raise PunyError("password_length_error")
            password = generate_password(args.length)
            copy_to_clipboard(password)
            print(t("password_generated", length=args.length))
        else:
            password = getpass(f"{t('entry_password')} ({t('leave_empty')}): ")

        notes = input(f"{t('entry_notes')} [{old.notes}] ({t('clear_hint')}): ").strip()
        url = input(f"{t('entry_url')} [{old.url}] ({t('clear_hint')}): ").strip()
        tags_text = input(
            f"{t('entry_tags')} [{', '.join(old.tags)}] ({t('clear_hint')}): "
        ).strip()
        tags = [tag.strip() for tag in tags_text.split(",") if tag.strip()]

        new = Entry(
            name=old.name,
            username=username or old.username,
            password=password or old.password,
            notes="" if notes == "-" else notes or old.notes,
            url="" if url == "-" else url or old.url,
            tags=[] if tags_text == "-" else tags or old.tags,
            custom_fields=old.custom_fields,
        )

    v.update(old.name, new)
    save_vault(m, v)
    print(t("entry_updated", name=old.name))


def cmd_vault_list(args: argparse.Namespace) -> None:
    active = get_active_vault()
    vaults = list_vaults()
    if not vaults:
        print(t("no_vaults"))
        return
    print(t("vaults_available"))
    for vname in vaults:
        marker = " (*)" if vname == active else ""
        print(f"  {vname}{marker}")


def cmd_vault_switch(args: argparse.Namespace) -> None:
    if not vault_path(args.name).exists():
        raise PunyError("vault_not_found", name=args.name)
    set_active_vault(args.name)
    print(t("vault_switched", name=args.name))


def cmd_vault_delete(args: argparse.Namespace) -> None:
    print(t("vault_delete_warning", name=args.name))
    choice = input(t("confirm_delete", name=args.name)).strip().lower()
    if choice != "y":
        return
    header = read_vault_header(args.name)
    delete_vault(args.name)
    if header.howdy_enabled and header.vault_id is not None:
        try:
            howdy.remove(header.vault_id)
        except HowdyError:
            print(t("howdy_cleanup_warning"))
    print(t("vault_deleted", name=args.name))


def cmd_export(args: argparse.Namespace) -> None:
    name = _require_active_vault()
    vault, _password = _unlock_vault(args, name)
    export_path = Path(args.output)
    if args.csv:
        export_csv_vault(vault, export_path)
    else:
        export_json_vault(vault, export_path)
    print(t("export_success", path=str(export_path)))


def cmd_import(args: argparse.Namespace) -> None:
    name = _require_active_vault()
    vault, password = _unlock_vault(args, name)
    import_path = Path(args.input)

    if args.csv:
        import_csv_vault(vault, import_path)
    else:
        import_json_vault(vault, import_path)
    save_vault(password, vault)
    print(t("import_success"))


def cmd_howdy_enable(args: argparse.Namespace) -> None:
    name = _require_active_vault()
    try:
        helper_status = howdy.status()
    except HowdyError as error:
        _raise_howdy(error)
    if not helper_status.get("tpm"):
        raise PunyError("howdy_reason_tpm_unavailable")

    master_password = _get_master_password(args)
    header = read_vault_header(name)
    vault = prepare_howdy_enrollment(master_password, name)
    if vault.vault_id is None or vault.data_key is None:
        raise PunyError("vault_corrupt")
    try:
        howdy.enroll(vault.vault_id, vault.data_key)
    except HowdyError as error:
        _raise_howdy(error)

    if not header.howdy_enabled:
        try:
            save_vault(master_password, vault)
        except Exception:
            with contextlib.suppress(HowdyError):
                howdy.remove(vault.vault_id)
            raise
    print(t("howdy_enabled"))


def cmd_howdy_disable(args: argparse.Namespace) -> None:
    name = _require_active_vault()
    header = read_vault_header(name)
    if not header.howdy_enabled:
        raise PunyError("howdy_not_enabled")
    master_password = _get_master_password(args)
    vault_id = disable_howdy_vault(master_password, name)
    try:
        howdy.remove(vault_id)
    except HowdyError:
        print(t("howdy_cleanup_warning"))
    print(t("howdy_disabled"))


def cmd_howdy_status(args: argparse.Namespace) -> None:
    name = _require_active_vault()
    header = read_vault_header(name)
    if not header.howdy_enabled or header.vault_id is None:
        print(t("howdy_status_disabled"))
        return
    try:
        result = howdy.status(header.vault_id)
    except HowdyError as error:
        print(t("howdy_status_unavailable", reason=_howdy_reason(error.code)))
        return
    if not result.get("tpm"):
        print(t("howdy_status_unavailable", reason=t("howdy_reason_tpm_unavailable")))
    elif not result.get("enrolled"):
        print(t("howdy_status_broken"))
    else:
        print(t("howdy_status_ready"))


def cmd_howdy_test(args: argparse.Namespace) -> None:
    try:
        howdy.test()
    except HowdyError as error:
        _raise_howdy(error)
    print(t("howdy_test_success"))


def cmd_config(args: argparse.Namespace) -> None:
    if args.key and args.value:
        set_config(args.key, int(args.value))
        print(t("config_set", key=args.key, value=args.value))
    else:
        config = get_config()
        for key, value in config.items():
            print(f"{key}: {value}")


def main() -> None:
    p = argparse.ArgumentParser(prog="puny-manager")
    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {get_version()}",
    )

    sp = p.add_subparsers(dest="cmd", required=True)

    sp_create = sp.add_parser("create", help=t("cmd_create"))
    sp_create.add_argument("name", help=t("arg_vault_name"))
    sp_create.add_argument(
        "--level",
        choices=["fast", "balanced", "paranoid"],
        default="balanced",
        help=t("arg_encryption_level"),
    )
    sp_create.add_argument("--master-password", help=t("arg_master_password"))
    sp_create.set_defaults(func=cmd_create)

    sp_list = sp.add_parser("list", help=t("cmd_list"))
    sp_list.add_argument("--master-password", help=t("arg_master_password"))
    sp_list.add_argument("--tag", help=t("arg_tag"))
    sp_list.set_defaults(func=cmd_list)

    sp_add = sp.add_parser("add", help=t("cmd_add"))
    sp_add.add_argument("--generate", action="store_true", help=t("arg_generate"))
    sp_add.add_argument("--length", type=int, default=20, help=t("arg_length"))
    sp_add.add_argument("--master-password", help=t("arg_master_password"))
    sp_add.add_argument("--entry-name", help=t("arg_entry_name"))
    sp_add.add_argument("--entry-username", help=t("arg_entry_username"))
    sp_add.add_argument("--entry-password", help=t("arg_entry_password"))
    sp_add.add_argument("--entry-notes", help=t("arg_entry_notes"))
    sp_add.add_argument("--entry-url", help=t("arg_entry_url"))
    sp_add.add_argument("--entry-tags", help=t("arg_entry_tags"))
    sp_add.add_argument("--custom-fields", help=t("arg_custom_fields"))
    sp_add.set_defaults(func=cmd_add)

    sp_get = sp.add_parser("get", help=t("cmd_get"))
    sp_get.add_argument("name", help=t("arg_name"))
    sp_get.add_argument("--timeout", type=int, default=15, help=t("arg_timeout"))
    sp_get.add_argument("-s", "--show", action="store_true", help=t("arg_show"))
    sp_get.add_argument("--master-password", help=t("arg_master_password"))
    sp_get.set_defaults(func=cmd_get)

    sp_rm = sp.add_parser("rm", help=t("cmd_rm"))
    sp_rm.add_argument("name", help=t("arg_name"))
    sp_rm.add_argument("--master-password", help=t("arg_master_password"))
    sp_rm.set_defaults(func=cmd_rm)

    sp_stats = sp.add_parser("stats", help=t("cmd_stats"))
    sp_stats.add_argument("--master-password", help=t("arg_master_password"))
    sp_stats.set_defaults(func=cmd_stats)

    sp_gen = sp.add_parser("gen", help=t("cmd_gen"))
    sp_gen.add_argument("length", nargs="?", type=int, default=20)
    sp_gen.set_defaults(func=cmd_gen)

    sp_lang = sp.add_parser("lang", help=t("cmd_lang"))
    sp_lang.add_argument("lang", nargs="?", choices=["en", "de", "fr", "es", "ru", "pt", "zh"])
    sp_lang.set_defaults(func=cmd_lang)

    sp_passwd = sp.add_parser("passwd", help=t("cmd_passwd"))
    sp_passwd.add_argument("--master-password", help=t("arg_master_password"))
    sp_passwd.add_argument("--new-password", help=t("arg_new_password"))
    sp_passwd.set_defaults(func=cmd_passwd)

    sp_edit = sp.add_parser("edit", help=t("cmd_edit"))
    sp_edit.add_argument("name", help=t("arg_name"))
    sp_edit.add_argument("--generate", action="store_true", help=t("arg_generate"))
    sp_edit.add_argument("--length", type=int, default=20, help=t("arg_length"))
    sp_edit.add_argument("--master-password", help=t("arg_master_password"))
    sp_edit.add_argument("--entry-name", help=t("arg_entry_name"))
    sp_edit.add_argument("--entry-username", help=t("arg_entry_username"))
    sp_edit.add_argument("--entry-password", help=t("arg_entry_password"))
    sp_edit.add_argument("--entry-notes", help=t("arg_entry_notes"))
    sp_edit.add_argument("--entry-url", help=t("arg_entry_url"))
    sp_edit.add_argument("--entry-tags", help=t("arg_entry_tags"))
    sp_edit.add_argument("--custom-fields", help=t("arg_custom_fields"))
    sp_edit.set_defaults(func=cmd_edit)

    sp_vault = sp.add_parser("vault", help=t("cmd_vault"))
    vault_sp = sp_vault.add_subparsers(dest="vault_cmd", required=True)

    vault_list_p = vault_sp.add_parser("list", help=t("cmd_vault_list"))
    vault_list_p.set_defaults(func=cmd_vault_list)

    vault_switch_p = vault_sp.add_parser("switch", help=t("cmd_vault_switch"))
    vault_switch_p.add_argument("name", help=t("arg_vault_name"))
    vault_switch_p.set_defaults(func=cmd_vault_switch)

    vault_delete_p = vault_sp.add_parser("delete", help=t("cmd_vault_delete"))
    vault_delete_p.add_argument("name", help=t("arg_vault_name"))
    vault_delete_p.set_defaults(func=cmd_vault_delete)

    sp_export = sp.add_parser("export", help=t("cmd_export"))
    sp_export.add_argument("output", help=t("arg_export_output"))
    sp_export.add_argument("--master-password", help=t("arg_master_password"))
    sp_export.add_argument("--csv", action="store_true", help=t("arg_csv"))
    sp_export.set_defaults(func=cmd_export)

    sp_import = sp.add_parser("import", help=t("cmd_import"))
    sp_import.add_argument("input", help=t("arg_import_input"))
    sp_import.add_argument("--master-password", help=t("arg_master_password"))
    sp_import.add_argument("--csv", action="store_true", help=t("arg_csv"))
    sp_import.set_defaults(func=cmd_import)

    sp_config = sp.add_parser("config", help=t("cmd_config"))
    sp_config.add_argument("key", nargs="?", help=t("arg_config_key"))
    sp_config.add_argument("value", nargs="?", help=t("arg_config_value"))
    sp_config.set_defaults(func=cmd_config)

    sp_howdy = sp.add_parser("howdy", help=t("cmd_howdy"))
    howdy_sp = sp_howdy.add_subparsers(dest="howdy_cmd", required=True)

    howdy_enable_p = howdy_sp.add_parser("enable", help=t("cmd_howdy_enable"))
    howdy_enable_p.add_argument("--master-password", help=t("arg_master_password"))
    howdy_enable_p.set_defaults(func=cmd_howdy_enable)

    howdy_disable_p = howdy_sp.add_parser("disable", help=t("cmd_howdy_disable"))
    howdy_disable_p.add_argument("--master-password", help=t("arg_master_password"))
    howdy_disable_p.set_defaults(func=cmd_howdy_disable)

    howdy_status_p = howdy_sp.add_parser("status", help=t("cmd_howdy_status"))
    howdy_status_p.set_defaults(func=cmd_howdy_status)

    howdy_test_p = howdy_sp.add_parser("test", help=t("cmd_howdy_test"))
    howdy_test_p.set_defaults(func=cmd_howdy_test)

    args = p.parse_args()

    try:
        args.func(args)
    except PunyError as e:
        print(t("error_prefix") + t(e.key, **e.kwargs))


if __name__ == "__main__":
    main()
