# Description

Puny Manager is a minimal, local, CLI password manager for Linux.

It stores all passwords in a single encrypted vault file protected by a master password.
The vault is fully encrypted and unreadable without the master password.

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
