import pytest

from puny.i18n import STRINGS, get_lang, t

EN_KEYS = set(STRINGS["en"].keys())


class TestGetLang:
    def test_invalid_lang_file_must_not_crash(self, monkeypatch, tmp_path):
        lang_file = tmp_path / "lang"
        lang_file.write_text("xx")
        monkeypatch.setattr("puny.i18n.get_lang_path", lambda: lang_file)

        assert get_lang() == "en"

    def test_empty_lang_file_must_not_crash(self, monkeypatch, tmp_path):
        lang_file = tmp_path / "lang"
        lang_file.write_text("")
        monkeypatch.setattr("puny.i18n.get_lang_path", lambda: lang_file)

        assert get_lang() == "en"

    def test_valid_lang_code_returns_itself(self, monkeypatch, tmp_path):
        lang_file = tmp_path / "lang"
        lang_file.write_text("de")
        monkeypatch.setattr("puny.i18n.get_lang_path", lambda: lang_file)

        assert get_lang() == "de"


class TestTranslate:
    def test_t_with_invalid_lang_must_not_key_error(self, monkeypatch, tmp_path):
        lang_file = tmp_path / "lang"
        lang_file.write_text("xx")
        monkeypatch.setattr("puny.i18n.get_lang_path", lambda: lang_file)

        result = t("vault_missing")
        assert result == "Vault does not exist."


@pytest.mark.parametrize("lang_code", ["de", "fr", "es", "ru", "pt", "zh"])
class TestLanguageCoverage:
    def test_no_extra_keys(self, lang_code):
        extra = set(STRINGS[lang_code].keys()) - EN_KEYS
        assert extra == set(), f"{lang_code} has extra keys: {extra}"

    def test_no_missing_keys(self, lang_code):
        missing = EN_KEYS - set(STRINGS[lang_code].keys())
        assert missing == set(), f"{lang_code} is missing keys: {missing}"

    def test_all_values_are_strings(self, lang_code):
        for key, value in STRINGS[lang_code].items():
            assert isinstance(value, str), f"{lang_code}/{key} is not a string"


def test_all_english_keys_in_en():
    assert "current_language" in STRINGS["en"]
    assert "available_languages" in STRINGS["en"]
