import contextlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from .crypto import decrypt_data, derive_key, derive_key_legacy, encrypt_data, generate_salt
from .vault import Entry, PunyError, Vault

APP_NAME = "puny-manager"


def _xdg_data() -> Path:
    base = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))
    return Path(base)


def _xdg_config() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(base)


def data_dir() -> Path:
    return _xdg_data() / APP_NAME


def vaults_dir() -> Path:
    return data_dir() / "vaults"


def vault_path(name: str) -> Path:
    return vaults_dir() / f"{name}.puny"


def config_dir() -> Path:
    return _xdg_config() / APP_NAME


def lang_path() -> Path:
    return config_dir() / "lang"


def _active_path() -> Path:
    return config_dir() / "active"


def get_active_vault() -> str | None:
    try:
        name = _active_path().read_text().strip()
        if name and vault_path(name).exists():
            return name
    except FileNotFoundError:
        pass
    return None


def set_active_vault(name: str) -> None:
    config_dir().mkdir(parents=True, exist_ok=True)
    _active_path().write_text(name)


def list_vaults() -> list[str]:
    vaults_dir().mkdir(parents=True, exist_ok=True)
    names = []
    for p in sorted(vaults_dir().glob("*.puny")):
        names.append(p.stem)
    return names


def _migrate_legacy_vault() -> bool:
    old_path = data_dir() / "vault.puny"
    if not old_path.exists():
        return False

    vaults_dir().mkdir(parents=True, exist_ok=True)
    os.chmod(vaults_dir(), 0o700)

    new_path = vault_path("default")
    if new_path.exists():
        return False

    shutil.move(str(old_path), str(new_path))

    old_backup = data_dir() / "vault.puny.bak"
    if old_backup.exists():
        new_backup = new_path.with_suffix(new_path.suffix + ".bak")
        shutil.move(str(old_backup), str(new_backup))

    set_active_vault("default")
    return True


def load_vault(master_password: str, name: str | None = None) -> Vault:
    _migrate_legacy_vault()

    if name is None:
        name = get_active_vault()
        if name is None:
            raise PunyError("no_active_vault")

    path = vault_path(name)
    if not path.exists():
        raise PunyError("vault_missing")

    raw = path.read_bytes()
    if len(raw) < 28:
        raise PunyError("vault_corrupt")

    salt = raw[:16]
    nonce = raw[16:28]
    ciphertext = raw[28:]

    try:
        key = derive_key(master_password, salt)
        plaintext = decrypt_data(key, nonce, ciphertext)
    except Exception:
        try:
            key = derive_key_legacy(master_password, salt)
            plaintext = decrypt_data(key, nonce, ciphertext)
            data = json.loads(plaintext.decode())
            entries = [Entry(**e) for e in data["entries"]]
            vault = Vault(version=data["version"], entries=entries, name=name)
            save_vault(master_password, vault)
        except Exception:
            raise PunyError("vault_decrypt_failed") from None

    data = json.loads(plaintext.decode())
    entries = [Entry(**e) for e in data["entries"]]
    return Vault(version=data["version"], entries=entries, name=name)


def save_vault(master_password: str, vault: Vault) -> None:
    vaults_dir().mkdir(parents=True, exist_ok=True)
    os.chmod(vaults_dir(), 0o700)

    if vault.name is None:
        raise PunyError("vault_no_name")

    salt = generate_salt()
    key = derive_key(master_password, salt)

    payload = {
        "version": vault.version,
        "entries": [e.__dict__ for e in vault.entries],
    }

    plaintext = json.dumps(payload).encode()
    nonce, ciphertext = encrypt_data(key, plaintext)

    blob = salt + nonce + ciphertext
    path = vault_path(vault.name)
    if path.exists():
        backup = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup)

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(blob)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_path, 0o600)
        os.replace(tmp_path, path)
    finally:
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)


def create_vault(master_password: str, name: str) -> Vault:
    _migrate_legacy_vault()

    path = vault_path(name)
    if path.exists():
        raise PunyError("vault_exists")

    vault = Vault(name=name)
    save_vault(master_password, vault)
    set_active_vault(name)
    return vault


def delete_vault(name: str) -> None:
    path = vault_path(name)
    if not path.exists():
        raise PunyError("vault_missing")

    active = get_active_vault()
    if active == name:
        raise PunyError("vault_delete_active")

    with contextlib.suppress(OSError):
        os.unlink(path)
    with contextlib.suppress(OSError):
        os.unlink(path.with_suffix(path.suffix + ".bak"))


def remove_backup(name: str) -> None:
    backup = vault_path(name).with_suffix(vault_path(name).suffix + ".bak")
    with contextlib.suppress(OSError):
        os.unlink(backup)
