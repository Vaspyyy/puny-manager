
import secrets
import string

DEFAULT_LENGTH = 20

ALPHABET = (
        string.ascii_lowercase +
        string.ascii_uppercase +
        string.digits +
        string.punctuation
)

def generate_password(length: int = DEFAULT_LENGTH) -> str:
    if length < 8:
        raise ValuError("Passwort länge muss mindestens 8 sein")

    return "".join(secrets.choice(ALPHABET) for _ in range(length))
