# Description

Puny Manager is a minimal, local, CLI password manager for Linux.

It stores all passwords in a single encrypted vault file protected by a master password.
The vault is fully encrypted and unreadable without the master password.

Note: To use clipboard feature you need wl-clipboard (wayland) or xclip (x11)

# Security

- Vault encryption: AES-256-GCM
- Key derivation: PBKDF2-HMAC-SHA256
- Every command requires the master password
- No unlocked session or caching
- The vault file is binary and unreadable if opened directly

## Installation

Recommended method using pipx:

```bash
pipx install git+https://github.com/Vaspyyy/puny-manager.git
```
## Usage

Initialize a new vault:
```bash
puny-manager init
```

Add a new entry:
```bash
puny-manager add
```

List stored entries:
```bash
puny-manager list
```
Retrieve an entry:
```bash
puny-manager get <name>
```
Generate a new password:
```bash
puny-manager gen
```

