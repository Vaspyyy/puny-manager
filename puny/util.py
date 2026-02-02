import secrets
import string
import shutil
import subprocess
import sys

ALPHABET = string.ascii_letters + string.digits + string.punctuation

def generate_password(length: int) -> str:
    if length < 8:
        raise ValueError
    return "".join(secrets.choice(ALPHABET) for _ in range(length))

def check_master_password(password: str) -> str | None:
    if len(password) < 4:
        return "master_password_too_short"
#    if not any(c.islower() for c in password):
#        return "master_password_requirements"
#    if not any(c.isupper() for c in password):
#        return "master_password_requirements"
#    if not any(c.isdigit() for c in password):
#        return "master_password_requirements"
#    if not any(c in string.punctuation for c in password):
#        return "master_password_requirements"
    return None

def schedule_clipboard_clear(timeout_s: int) -> None:
    if timeout_s <= 0:
        return
    script = (
        "import time, pyperclip;"
        f"time.sleep({timeout_s});"
        "pyperclip.copy('')"
    )
    subprocess.Popen(
        [sys.executable, "-c", script],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def smart_find(entries, query):
    exact = [e for e in entries if e.name == query]
    if exact:
        return exact[0]

    matches = [
        e
        for e in entries
        if query.lower() in (e.name + e.notes + e.username + e.url + " ".join(e.tags)).lower()
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

    return matches[0]
