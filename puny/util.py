import secrets
import shutil
import string
import subprocess
import threading
from typing import TypeVar

from .vault import Entry

E = TypeVar("E", bound=Entry)

SYMBOLS = "!@#$%^&*()-_=+[]{};:,.<>?"
ALPHABET = string.ascii_letters + string.digits + SYMBOLS

_clipboard_timers: list[threading.Timer] = []


def generate_password(length: int) -> str:
    if length < 8:
        raise ValueError
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def check_master_password(password: str) -> tuple[str | None, str | None]:
    if len(password) < 4:
        return "master_password_too_short", None
    if len(password) < 8 or not any(c in SYMBOLS for c in password):
        return None, "weak_master_password"
    return None, None


def _clear_clipboard(clear_cmd: list[str]) -> None:
    subprocess.run(clear_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def schedule_clipboard_clear(timeout_s: int) -> None:
    if timeout_s <= 0:
        return
    if shutil.which("wl-copy"):
        clear_cmd = ["wl-copy", ""]
    elif shutil.which("xclip"):
        clear_cmd = ["xclip", "-selection", "clipboard"]
    else:
        return

    for timer in _clipboard_timers:
        timer.cancel()
    _clipboard_timers.clear()

    timer = threading.Timer(timeout_s, _clear_clipboard, args=(clear_cmd,))
    timer.daemon = True
    timer.start()
    _clipboard_timers.append(timer)


def smart_find(entries: list[E], query: str) -> E | None:
    if not query:
        return None

    exact = [e for e in entries if e.name == query]
    if exact:
        return exact[0]

    matches = [
        e
        for e in entries
        if query.lower()
        in (
            e.name + "\x00" + e.username + "\x00" + e.notes
            + "\x00" + e.url + "\x00" + " ".join(e.tags)
        ).lower()
    ]
    if not matches:
        return None
    if len(matches) == 1:
        return matches[0]

    if shutil.which("fzf"):
        p = subprocess.run(
            ["fzf"],
            input="\n".join(e.name for e in matches),
            text=True,
            capture_output=True,
        )
        if p.returncode == 0:
            for e in matches:
                if e.name == p.stdout.strip():
                    return e
        return None

    return matches[0]


def is_weak_password(password: str) -> bool:
    if len(password) < 8:
        return True
    if not any(c.isupper() for c in password):
        return True
    if not any(c.islower() for c in password):
        return True
    if not any(c.isdigit() for c in password):
        return True
    return not any(c in SYMBOLS for c in password)


def analyze_passwords(entries: list[Entry]) -> dict:
    total = len(entries)
    if total == 0:
        return {
            "count": 0, "avg_length": 0, "weak_count": 0,
            "unique_count": 0, "duplicate_sets": [],
        }

    lengths = [len(e.password) for e in entries]
    avg_length = sum(lengths) // total
    weak_count = sum(1 for e in entries if is_weak_password(e.password))

    seen: dict[str, list[str]] = {}
    for e in entries:
        seen.setdefault(e.password, []).append(e.name)

    duplicate_sets = [names for names in seen.values() if len(names) > 1]

    return {
        "count": total,
        "avg_length": avg_length,
        "weak_count": weak_count,
        "unique_count": len(seen),
        "duplicate_sets": duplicate_sets,
    }
