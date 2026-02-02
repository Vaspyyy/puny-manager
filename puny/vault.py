from dataclasses import dataclass, field

class PunyError(Exception):
    pass

@dataclass
class Entry:
    name: str
    username: str
    password: str
    notes: str = ""
    url: str = ""
    tags: list[str] = field(default_factory=list)

@dataclass
class Vault:
    version: int = 1
    entries: list[Entry] = field(default_factory=list)

    def list(self) -> list[str]:
        return [e.name for e in self.entries]

    def get(self, name: str) -> Entry:
        for e in self.entries:
            if e.name == name:
                return e
        raise PunyError("entry_not_found")

    def add(self, entry: Entry) -> None:
        if any(e.name == entry.name for e in self.entries):
            raise PunyError("entry_exists")
        self.entries.append(entry)

    def remove(self, name: str) -> None:
        before = len(self.entries)
        self.entries = [e for e in self.entries if e.name != name]
        if len(self.entries) == before:
            raise PunyError("entry_not_found")

    def update(self, name: str, new: Entry) -> None:
        for i, e in enumerate(self.entries):
            if e.name == name:
                self.entries[i] = new
                return
        raise PunyError("entry_not_found")
