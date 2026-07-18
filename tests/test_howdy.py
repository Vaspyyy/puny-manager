from argparse import Namespace

import pytest

from puny import cli, howdy
from puny.howdy import HowdyError
from puny.storage import (
    create_vault,
    prepare_howdy_enrollment,
    read_vault_header,
    save_vault,
)


@pytest.fixture
def enrolled_vault(monkeypatch, tmp_path):
    monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path / "data")
    monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path / "config")
    create_vault("password123!", "demo")
    vault = prepare_howdy_enrollment("password123!", "demo")
    save_vault("password123!", vault)
    return vault


def test_unlock_uses_howdy_without_prompt(monkeypatch, enrolled_vault):
    monkeypatch.setattr(howdy, "unlock", lambda _vault_id: enrolled_vault.data_key)
    monkeypatch.setattr(cli, "getpass", lambda _prompt: pytest.fail("unexpected prompt"))

    vault, password = cli._unlock_vault(Namespace(master_password=None), "demo")
    assert vault.name == "demo"
    assert password is None


def test_unlock_falls_back_to_master_password(monkeypatch, enrolled_vault, capsys):
    def fail(_vault_id):
        raise HowdyError("auth_failed")

    monkeypatch.setattr(howdy, "unlock", fail)
    monkeypatch.setattr(cli, "getpass", lambda _prompt: "password123!")

    vault, password = cli._unlock_vault(Namespace(master_password=None), "demo")
    assert vault.name == "demo"
    assert password == "password123!"
    assert "using the master password" in capsys.readouterr().out


def test_explicit_password_bypasses_howdy(monkeypatch, enrolled_vault):
    monkeypatch.setattr(howdy, "unlock", lambda _vault_id: pytest.fail("Howdy should be bypassed"))
    vault, password = cli._unlock_vault(Namespace(master_password="password123!"), "demo")
    assert vault.name == "demo"
    assert password == "password123!"


def test_client_validates_returned_key(monkeypatch):
    monkeypatch.setattr(howdy, "_request", lambda *_args, **_kwargs: {"ok": True, "key": "eA=="})
    with pytest.raises(HowdyError) as exc:
        howdy.unlock(bytes.fromhex("11" * 16))
    assert exc.value.code == "invalid_response"


def test_enable_enrolls_then_migrates(monkeypatch, tmp_path):
    monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path / "data")
    monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path / "config")
    create_vault("password123!", "demo")
    calls = []
    monkeypatch.setattr(howdy, "status", lambda *_args: {"ok": True, "tpm": True})
    monkeypatch.setattr(
        howdy,
        "enroll",
        lambda vault_id, data_key: calls.append((vault_id, data_key)),
    )

    cli.cmd_howdy_enable(Namespace(master_password="password123!"))

    header = read_vault_header("demo")
    assert header.howdy_enabled
    assert calls and calls[0][0] == header.vault_id
    assert len(calls[0][1]) == 32


def test_failed_enrollment_keeps_v1_vault(monkeypatch, tmp_path):
    monkeypatch.setattr("puny.storage._xdg_data", lambda: tmp_path / "data")
    monkeypatch.setattr("puny.storage._xdg_config", lambda: tmp_path / "config")
    create_vault("password123!", "demo")
    monkeypatch.setattr(howdy, "status", lambda *_args: {"ok": True, "tpm": True})

    def fail(_vault_id, _data_key):
        raise HowdyError("auth_failed")

    monkeypatch.setattr(howdy, "enroll", fail)
    with pytest.raises(cli.PunyError):
        cli.cmd_howdy_enable(Namespace(master_password="password123!"))
    assert not read_vault_header("demo").howdy_enabled


def test_disable_requires_master_and_removes_credential(monkeypatch, enrolled_vault):
    removed = []
    monkeypatch.setattr(howdy, "remove", lambda vault_id: removed.append(vault_id))
    cli.cmd_howdy_disable(Namespace(master_password="password123!"))
    assert removed == [enrolled_vault.vault_id]
    assert not read_vault_header("demo").howdy_enabled


def test_each_unlock_calls_howdy_again(monkeypatch, enrolled_vault):
    calls = []

    def unlock(vault_id):
        calls.append(vault_id)
        return enrolled_vault.data_key

    monkeypatch.setattr(howdy, "unlock", unlock)
    args = Namespace(master_password=None)
    cli._unlock_vault(args, "demo")
    cli._unlock_vault(args, "demo")
    assert calls == [enrolled_vault.vault_id, enrolled_vault.vault_id]
