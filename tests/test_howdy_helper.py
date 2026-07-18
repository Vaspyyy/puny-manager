import base64
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from puny import howdy_helper
from puny.howdy_helper import HelperError

VAULT_ID = "12345678123456781234567812345678"
PAM_POLICY = Path(__file__).parents[1] / "packaging/arch/puny-manager-howdy.pam"


def test_rejects_invalid_vault_id():
    for value in (None, "../escape", "0" * 32, "z" * 32):
        with pytest.raises(HelperError):
            howdy_helper._validate_vault_id(value)


def test_pam_policy_allows_account_after_howdy_authentication():
    policy = PAM_POLICY.read_text()
    assert "auth required pam_howdy.so" in policy
    assert "account required pam_permit.so" in policy
    assert "pam_unix.so" not in policy


def test_authentication_skips_unsupported_credential_reset(monkeypatch):
    calls = []

    class Authenticator:
        def authenticate(self, *args, **kwargs):
            calls.append((args, kwargs))
            return True

    pam_module = SimpleNamespace(pam=Authenticator)
    monkeypatch.setattr(howdy_helper.importlib, "import_module", lambda _name: pam_module)
    monkeypatch.setattr(
        howdy_helper.pwd, "getpwuid", lambda _uid: SimpleNamespace(pw_name="ransom")
    )

    howdy_helper._authenticate(1000)
    assert calls[0][0] == ("ransom", "")
    assert calls[0][1] == {
        "service": "puny-manager-howdy",
        "resetcreds": False,
    }


def test_enroll_authenticates_before_sealing(monkeypatch):
    calls = []
    key = b"k" * 32
    monkeypatch.setattr(howdy_helper, "_authenticate", lambda uid: calls.append(("auth", uid)))
    monkeypatch.setattr(
        howdy_helper,
        "_seal_key",
        lambda uid, vault_id, data_key: calls.append(("seal", uid, vault_id, data_key)),
    )

    result = howdy_helper.handle_request(
        1000,
        {
            "version": 1,
            "op": "enroll",
            "vault_id": VAULT_ID,
            "key": base64.b64encode(key).decode(),
        },
    )
    assert result == {"ok": True}
    assert calls == [("auth", 1000), ("seal", 1000, VAULT_ID, key)]


def test_unlock_authenticates_and_returns_only_key(monkeypatch):
    calls = []
    key = b"k" * 32
    monkeypatch.setattr(howdy_helper, "_authenticate", lambda uid: calls.append(uid))
    monkeypatch.setattr(howdy_helper, "_unseal_key", lambda uid, vault_id: key)

    result = howdy_helper.handle_request(
        1000,
        {
            "version": 1,
            "op": "unlock",
            "vault_id": VAULT_ID,
        },
    )
    assert calls == [1000]
    assert base64.b64decode(result["key"]) == key


def test_unknown_protocol_and_operation_are_rejected():
    with pytest.raises(HelperError):
        howdy_helper.handle_request(1000, {"version": 2, "op": "test"})
    with pytest.raises(HelperError):
        howdy_helper.handle_request(
            1000,
            {
                "version": 1,
                "op": "unknown",
                "vault_id": VAULT_ID,
            },
        )


def test_sealing_requires_tpm_and_host_key(monkeypatch, tmp_path):
    target = tmp_path / "credential"
    commands = []
    monkeypatch.setattr(howdy_helper, "_has_tpm2", lambda: True)
    monkeypatch.setattr(howdy_helper, "_credential_path", lambda _uid, _id: target)

    def run(command, **kwargs):
        commands.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout=b"sealed")

    monkeypatch.setattr(howdy_helper.subprocess, "run", run)
    howdy_helper._seal_key(1000, VAULT_ID, b"k" * 32)

    assert "--with-key=host+tpm2" in commands[0][0]
    assert commands[0][1]["input"] == b"k" * 32
    assert target.read_bytes() == b"sealed"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_unsealing_refuses_null_credentials(monkeypatch, tmp_path):
    target = tmp_path / "credential"
    target.write_bytes(b"sealed")
    commands = []
    monkeypatch.setattr(howdy_helper, "_has_tpm2", lambda: True)
    monkeypatch.setattr(howdy_helper, "_credential_path", lambda _uid, _id: target)
    monkeypatch.setattr(howdy_helper, "_credential_exists", lambda _uid, _id: True)

    def run(command, **kwargs):
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout=b"k" * 32)

    monkeypatch.setattr(howdy_helper.subprocess, "run", run)
    assert howdy_helper._unseal_key(1000, VAULT_ID) == b"k" * 32
    assert "--refuse-null" in commands[0]
