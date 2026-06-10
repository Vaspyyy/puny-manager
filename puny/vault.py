from dataclasses import dataclass, field

from .crypto import KDF_ARGON2ID, LEVEL_BALANCED

SUPPORTED_VERSIONS = {1}


class PunyError(Exception):
    def __init__(self, key: str, **kwargs: object) -> None:
        self.key = key
        self.kwargs = kwargs
        super().__init__(key)


@dataclass
class Entry:
    name: str
    username: str
    password: str
    notes: str = ""
    url: str = ""
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("Entry name must not be empty.")


@dataclass
class Vault:
    version: int = 1
    entries: list[Entry] = field(default_factory=list)
    name: str | None = field(default=None, repr=False)
    kdf_id: int = field(default=KDF_ARGON2ID, repr=False)
    level_id: int = field(default=LEVEL_BALANCED, repr=False)

    def __post_init__(self) -> None:
        if self.version not in SUPPORTED_VERSIONS:
            raise PunyError("unsupported_version", version=self.version)

    def list(self) -> list[str]:
        return [e.name for e in self.entries]

    def get(self, name: str) -> Entry:
        for e in self.entries:
            if e.name == name:
                return e
        raise PunyError("entry_not_found", name=name)

    def add(self, entry: Entry) -> None:
        if any(e.name == entry.name for e in self.entries):
            raise PunyError("entry_exists", name=entry.name)
        self.entries.append(entry)

    def remove(self, name: str) -> None:
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.name != name]
        if len(self.entries) == before:
            raise PunyError("entry_not_found", name=name)

    def update(self, name: str, new: Entry) -> None:
        if new.name != name and any(e.name == new.name for e in self.entries):
            raise PunyError("entry_exists", name=new.name)
        for i, e in enumerate(self.entries):
            if e.name == name:
                self.entries[i] = new
                return
        raise PunyError("entry_not_found", name=name)
