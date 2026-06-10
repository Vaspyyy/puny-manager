import pytest

from puny.vault import Entry, PunyError, Vault


class TestEntry:
    def test_entry_creation(self):
        e = Entry(name="test", username="user", password="pass")
        assert e.name == "test"
        assert e.username == "user"
        assert e.password == "pass"
        assert e.notes == ""
        assert e.url == ""
        assert e.tags == []

    def test_entry_with_all_fields(self):
        e = Entry(
            name="github",
            username="dev",
            password="secret",
            notes="work account",
            url="https://github.com",
            tags=["work", "git"],
        )
        assert e.name == "github"
        assert e.tags == ["work", "git"]

    def test_empty_name_raises_puny_error(self):
        with pytest.raises(PunyError) as exc:
            Entry(name="", username="u", password="p")
        assert exc.value.key == "entry_name_required"

    def test_whitespace_only_name_raises_puny_error(self):
        with pytest.raises(PunyError) as exc:
            Entry(name="   ", username="u", password="p")
        assert exc.value.key == "entry_name_required"


class TestVault:
    def test_empty_vault(self):
        v = Vault()
        assert v.version == 1
        assert v.entries == []
        assert v.list() == []

    def test_add_entry(self):
        v = Vault()
        e = Entry(name="test", username="u", password="p")
        v.add(e)
        assert len(v.entries) == 1
        assert v.list() == ["test"]

    def test_add_duplicate_raises(self):
        v = Vault()
        v.add(Entry(name="test", username="u", password="p"))
        with pytest.raises(PunyError):
            v.add(Entry(name="test", username="u2", password="p2"))

    def test_get_entry(self):
        v = Vault()
        e = Entry(name="test", username="u", password="p")
        v.add(e)
        assert v.get("test") == e

    def test_get_missing_raises(self):
        v = Vault()
        with pytest.raises(PunyError):
            v.get("nonexistent")

    def test_remove_entry(self):
        v = Vault()
        v.add(Entry(name="test", username="u", password="p"))
        v.remove("test")
        assert len(v.entries) == 0

    def test_remove_missing_raises(self):
        v = Vault()
        with pytest.raises(PunyError):
            v.remove("nonexistent")

    def test_update_entry(self):
        v = Vault()
        v.add(Entry(name="test", username="old", password="p"))
        v.update("test", Entry(name="test", username="new", password="p"))
        assert v.get("test").username == "new"

    def test_update_missing_raises(self):
        v = Vault()
        with pytest.raises(PunyError):
            v.update("test", Entry(name="test", username="u", password="p"))

    def test_update_with_different_name(self):
        v = Vault()
        v.add(Entry(name="old", username="u", password="p"))
        v.update("old", Entry(name="renamed", username="u", password="p"))
        with pytest.raises(PunyError):
            v.get("old")
        assert v.get("renamed").name == "renamed"

    def test_update_to_existing_name_must_raise(self):
        v = Vault()
        v.add(Entry(name="a", username="u", password="p"))
        v.add(Entry(name="b", username="u", password="p"))
        with pytest.raises(PunyError):
            v.update("a", Entry(name="b", username="u", password="p"))
        assert v.get("a").name == "a"
