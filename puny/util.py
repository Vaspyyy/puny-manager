import secrets
import string
import shutil
import subprocess

ALPHABET = string.ascii_letters + string.digits + string.punctuation

def generate_password(length: int) -> str:
    if length < 8:
        raise ValueError
    return "".join(secrets.choice(ALPHABET) for _ in range(length))

def smart_find(entries, query):
    exact = [e for e in entries if e.name == query]
    if exact:
        return exact[0]

    matches = [e for e in entries if query.lower() in (e.name + e.notes).lower()]
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
