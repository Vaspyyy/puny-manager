import os

import pytest

from puny.crypto import VERSION_1, VERSION_2
from puny.storage import (
    create_vault,
    disable_howdy_vault,
    load_vault,
    load_vault_with_key,
    prepare_howdy_enrollment,
    read_vault_header,
    save_vault,
    vault_path,
)
from puny.vault import Entry, PunyError


@pytest.fixture
def isolated_vaults(monkeypatch, tmp_path):
    monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path / "data")
    monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path / "config")


def test_enrollment_migrates_only_selected_vault(isolated_vaults):
    create_vault("password123!", "enrolled")
    create_vault("password123!", "plain")

    vault = prepare_howdy_enrollment("password123!", "enrolled")
    assert vault.format_version == VERSION_2
    assert vault.vault_id is not None and len(vault.vault_id) == 16
    assert vault.data_key is not None and len(vault.data_key) == 32
    save_vault("password123!", vault)

    assert read_vault_header("enrolled").howdy_enabled
    assert read_vault_header("plain").format_version == VERSION_1


def test_v2_unlocks_with_password_and_data_key(isolated_vaults):
    create_vault("password123!", "demo")
    vault = prepare_howdy_enrollment("password123!", "demo")
    data_key = vault.data_key
    save_vault("password123!", vault)

    password_vault = load_vault("password123!", name="demo")
    key_vault = load_vault_with_key(data_key, name="demo")
    assert password_vault.entries == key_vault.entries == []


def test_face_unlocked_save_preserves_password_recovery(isolated_vaults):
    create_vault("password123!", "demo")
    vault = prepare_howdy_enrollment("password123!", "demo")
    data_key = vault.data_key
    save_vault("password123!", vault)

    unlocked = load_vault_with_key(data_key, name="demo")
    unlocked.add(Entry(name="site", username="u", password="secret"))
    save_vault(None, unlocked)

    recovered = load_vault("password123!", name="demo")
    assert recovered.entries[0].password == "secret"


def test_wrong_face_key_fails(isolated_vaults):
    create_vault("password123!", "demo")
    vault = prepare_howdy_enrollment("password123!", "demo")
    save_vault("password123!", vault)

    with pytest.raises(PunyError) as exc:
        load_vault_with_key(os.urandom(32), name="demo")
    assert exc.value.key == "vault_decrypt_failed"


def test_password_change_rewraps_key_without_breaking_face(isolated_vaults):
    create_vault("old-password!", "demo")
    vault = prepare_howdy_enrollment("old-password!", "demo")
    data_key = vault.data_key
    save_vault("old-password!", vault)

    loaded = load_vault("old-password!", name="demo")
    save_vault("new-password!", loaded)

    with pytest.raises(PunyError):
        load_vault("old-password!", name="demo")
    assert load_vault("new-password!", name="demo").entries == []
    assert load_vault_with_key(data_key, name="demo").entries == []


def test_disable_returns_to_v1_and_keeps_data(isolated_vaults):
    create_vault("password123!", "demo")
    vault = prepare_howdy_enrollment("password123!", "demo")
    vault.add(Entry(name="site", username="u", password="secret"))
    vault_id = vault.vault_id
    save_vault("password123!", vault)

    assert disable_howdy_vault("password123!", "demo") == vault_id
    assert read_vault_header("demo").format_version == VERSION_1
    assert load_vault("password123!", name="demo").entries[0].name == "site"


def test_v2_header_tampering_is_detected(isolated_vaults):
    create_vault("password123!", "demo")
    vault = prepare_howdy_enrollment("password123!", "demo")
    save_vault("password123!", vault)
    path = vault_path("demo")
    raw = bytearray(path.read_bytes())
    raw[8] ^= 1
    path.write_bytes(raw)

    with pytest.raises(PunyError) as exc:
        load_vault("password123!", name="demo")
    assert exc.value.key == "vault_decrypt_failed"


def test_password_recovery_wrapper_tampering_breaks_face_unlock(isolated_vaults):
    create_vault("password123!", "demo")
    vault = prepare_howdy_enrollment("password123!", "demo")
    data_key = vault.data_key
    save_vault("password123!", vault)
    path = vault_path("demo")
    raw = bytearray(path.read_bytes())
    raw[60] ^= 1
    path.write_bytes(raw)

    with pytest.raises(PunyError) as exc:
        load_vault_with_key(data_key, name="demo")
    assert exc.value.key == "vault_decrypt_failed"
