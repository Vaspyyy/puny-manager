# Description

Puny Manager is a minimal, local, CLI password manager for Linux.

It stores all passwords in a single encrypted vault file protected by a master password.
The vault is fully encrypted and unreadable without the master password.

Note: To use clipboard feature you need wl-clipboard (wayland) or xclip (x11)

# Security

- Vault encryption: AES-256-GCM
- Key derivation: Argon2id (with legacy PBKDF2-HMAC-SHA256 support)
- Every command requires the master password
- No unlocked session or caching
- The vault file is binary and unreadable if opened directly
- Automatic backup on save (`vault.puny.bak`)

## Installation

Recommended method using pipx:

```bash
pipx install git+https://github.com/Vaspyyy/puny-manager.git
```

## Updating

If installed via pipx:

```bash
pipx upgrade puny-manager
```

## Usage
Change language:
```bash
puny-manager lang
```

Initialize a new vault:
```bash
puny-manager init
```
Master passwords must be at least 4 characters.

Add a new entry:
```bash
puny-manager add
```
You can store optional URL and tags for entries.

List stored entries:
```bash
puny-manager list
```
Retrieve an entry:
```bash
puny-manager get <name>
```
To copy a password and clear the clipboard after 15 seconds:
```bash
puny-manager get <name> --copy --timeout 15
```
Generate a new password:
```bash
puny-manager gen
```
Change master password:
```bash
puny-manager passwd
```
Edit an entry:
```bash
puny-manager edit <name>
```
Remove an entry:
```bash
puny-manager rm <name>
```
