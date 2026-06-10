import pytest

from puny.util import (
    analyze_passwords,
    check_master_password,
    generate_password,
    is_weak_password,
    smart_find,
)
from puny.vault import Entry


class TestGeneratePassword:
    def test_default_length(self):
        pw = generate_password(20)
        assert len(pw) == 20

    def test_minimum_length(self):
        pw = generate_password(8)
        assert len(pw) == 8

    def test_too_short_raises(self):
        with pytest.raises(ValueError):
            generate_password(7)

    def test_zero_raises(self):
        with pytest.raises(ValueError):
            generate_password(0)

    def test_only_printable(self):
        pw = generate_password(64)
        assert all(c.isprintable() for c in pw)

    def test_randomness(self):
        a = generate_password(20)
        b = generate_password(20)
        assert a != b


class TestCheckMasterPassword:
    def test_too_short(self):
        err, warn = check_master_password("abc")
        assert err == "master_password_too_short"
        assert warn is None

    def test_weak_short_length(self):
        err, warn = check_master_password("abcde!")
        assert err is None
        assert warn == "weak_master_password"

    def test_weak_no_symbol(self):
        err, warn = check_master_password("abcdefgh")
        assert err is None
        assert warn == "weak_master_password"

    def test_weak_short_and_no_symbol(self):
        err, warn = check_master_password("abcde")
        assert err is None
        assert warn == "weak_master_password"

    def test_strong_password(self):
        err, warn = check_master_password("correcthorsebatterystaple!")
        assert err is None
        assert warn is None

    def test_minimum_strong(self):
        err, warn = check_master_password("pass!word")
        assert err is None
        assert warn is None


class TestSmartFind:
    def test_exact_match(self):
        entries = [Entry(name="github", username="u", password="p")]
        result = smart_find(entries, "github")
        assert result is not None
        assert result.name == "github"

    def test_no_match(self):
        entries = [Entry(name="github", username="u", password="p")]
        result = smart_find(entries, "reddit")
        assert result is None

    def test_substring_match(self):
        entries = [Entry(name="github", username="u", password="p")]
        result = smart_find(entries, "hub")
        assert result is not None
        assert result.name == "github"

    def test_case_insensitive(self):
        entries = [Entry(name="GitHub", username="u", password="p")]
        result = smart_find(entries, "github")
        assert result is not None
        assert result.name == "GitHub"

    def test_search_in_username(self):
        entries = [Entry(name="site", username="alice@example.com", password="p")]
        result = smart_find(entries, "alice")
        assert result is not None

    def test_search_in_notes(self):
        entries = [Entry(name="site", username="u", password="p", notes="backup key")]
        result = smart_find(entries, "backup")
        assert result is not None

    def test_search_in_tags(self):
        entries = [Entry(name="site", username="u", password="p", tags=["bank", "finance"])]
        result = smart_find(entries, "bank")
        assert result is not None

    def test_search_in_url(self):
        entries = [Entry(name="site", username="u", password="p", url="https://reddit.com")]
        result = smart_find(entries, "reddit")
        assert result is not None

    def test_returns_first_when_multiple(self, monkeypatch):
        monkeypatch.setattr("puny.util.shutil.which", lambda x: None)
        entries = [
            Entry(name="hub-one", username="u", password="p"),
            Entry(name="something-hub", username="u", password="p"),
        ]
        result = smart_find(entries, "hub")
        assert result.name == "hub-one"

    def test_empty_query_must_return_none(self):
        entries = [Entry(name="github", username="u", password="p")]
        result = smart_find(entries, "")
        assert result is None

    def test_fzf_nonzero_exit_must_not_return_first(self, monkeypatch):
        monkeypatch.setattr("puny.util.shutil.which", lambda x: "mock-fzf" if x == "fzf" else None)
        monkeypatch.setattr(
            "puny.util.subprocess.run",
            lambda *args, **kwargs: type("P", (), {"returncode": 1})(),
        )
        entries = [
            Entry(name="debug-foo", username="u", password="p"),
            Entry(name="debug-bar", username="u", password="p"),
            Entry(name="debug-baz", username="u", password="p"),
        ]
        result = smart_find(entries, "debug")
        assert result is None


class TestGeneratePasswordBoundaries:
    def test_negative_length_raises(self):
        with pytest.raises(ValueError):
            generate_password(-1)

    def test_exactly_eight_is_valid(self):
        pw = generate_password(8)
        assert len(pw) == 8


class TestCheckMasterPasswordBoundaries:
    def test_exactly_four_with_symbol_is_weak_not_error(self):
        err, warn = check_master_password("a!bc")
        assert err is None
        assert warn == "weak_master_password"

    def test_exactly_four_no_symbol_is_weak_not_error(self):
        err, warn = check_master_password("abcd")
        assert err is None
        assert warn == "weak_master_password"

    def test_exactly_eight_with_symbol_is_strong(self):
        err, warn = check_master_password("abcdefg!")
        assert err is None
        assert warn is None

    def test_exactly_eight_no_symbol_is_weak(self):
        err, warn = check_master_password("abcdefgh")
        assert err is None
        assert warn == "weak_master_password"


class TestIsWeakPassword:
    def test_short_password_is_weak(self):
        assert is_weak_password("Abc1!")

    def test_no_upper_is_weak(self):
        assert is_weak_password("abc123!@")

    def test_no_lower_is_weak(self):
        assert is_weak_password("ABC123!@")

    def test_no_digit_is_weak(self):
        assert is_weak_password("Abcdef!@")

    def test_no_symbol_is_weak(self):
        assert is_weak_password("Abcdef123")

    def test_strong_password_is_not_weak(self):
        assert not is_weak_password("CorrectHorseBatteryStaple1!")

    def test_minimum_strong_is_not_weak(self):
        assert not is_weak_password("aA1!bcde")


class TestAnalyzePasswords:
    def test_empty_entries(self):
        result = analyze_passwords([])
        assert result["count"] == 0
        assert result["weak_count"] == 0
        assert result["unique_count"] == 0
        assert result["duplicate_sets"] == []

    def test_single_entry(self):
        from puny.vault import Entry
        entries = [Entry(name="x", username="u", password="Str0ng!Pass")]
        result = analyze_passwords(entries)
        assert result["count"] == 1
        assert result["weak_count"] == 0
        assert result["unique_count"] == 1
        assert result["duplicate_sets"] == []

    def test_weak_password_counted(self):
        from puny.vault import Entry
        entries = [
            Entry(name="a", username="u", password="weak"),
            Entry(name="b", username="u", password="Str0ng!1"),
        ]
        result = analyze_passwords(entries)
        assert result["weak_count"] == 1

    def test_duplicate_passwords_detected(self):
        from puny.vault import Entry
        entries = [
            Entry(name="a", username="u", password="same"),
            Entry(name="b", username="u", password="same"),
            Entry(name="c", username="u", password="diff"),
        ]
        result = analyze_passwords(entries)
        assert result["unique_count"] == 2
        assert len(result["duplicate_sets"]) == 1
        assert sorted(result["duplicate_sets"][0]) == ["a", "b"]

    def test_avg_length_rounded_down(self):
        from puny.vault import Entry
        entries = [
            Entry(name="a", username="u", password="12345678"),
            Entry(name="b", username="u", password="123456"),
        ]
        result = analyze_passwords(entries)
        assert result["avg_length"] == 7  # (8+6)//2

    def test_multiple_duplicate_sets(self):
        from puny.vault import Entry
        entries = [
            Entry(name="a1", username="u", password="dup1"),
            Entry(name="a2", username="u", password="dup1"),
            Entry(name="b1", username="u", password="dup2"),
            Entry(name="b2", username="u", password="dup2"),
            Entry(name="b3", username="u", password="dup2"),
        ]
        result = analyze_passwords(entries)
        assert result["unique_count"] == 2
        assert len(result["duplicate_sets"]) == 2
