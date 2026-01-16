
import secrets
import string
from .i18n import t

DEFAULT_LENGTH = 20

ALPHABET = (
        string.ascii_lowercase +
        string.ascii_uppercase +
        string.digits +
        string.punctuation
)

def generate_password(length: int = DEFAULT_LENGTH) -> str:
    if length < 8:
        raise ValueError(t("password_length_error"))

    return "".join(secrets.choice(ALPHABET) for _ in range(length))
