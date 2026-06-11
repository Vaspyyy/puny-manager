# Description

Puny Manager is a minimal, local, CLI password manager for Linux.

It stores all passwords in a single encrypted vault file protected by a master password.
The vault is fully encrypted and unreadable without the master password.

Note: To use clipboard feature you need wl-clipboard (wayland) or xclip (x11)

# Security

- Vault encryption: AES-256-GCM
- Key derivation: Argon2id (with legacy PBKDF2-HMAC-SHA256 support)
- Configurable encryption level: fast (32MB), balanced (64MB, default), paranoid (256MB)
- Versioned binary format with header validation
- Every command requires the master password
- No unlocked session or caching
- The vault file is binary and unreadable if opened directly
- Automatic backup on save (`vault.puny.bak`)

## Installation

Recommended method using the aur:
```bash
paru -S puny-manager
``` 
Using pipx:
```bash
pipx install git+https://github.com/Vaspyyy/puny-manager.git
```

## Updating
If installed via aur:
```bash
paru -Syu
```
If installed via pipx:

```bash
pipx upgrade puny-manager
```

## Shell completions

### Bash
```bash
cp completions/puny-manager.bash ~/.local/share/bash-completion/completions/puny-manager
```
Or source it directly:
```bash
source completions/puny-manager.bash
```

### Zsh
```bash
cp completions/_puny-manager ~/.local/share/zsh/site-functions/_puny-manager
```
Or add `completions/` to your `$fpath` in `.zshrc`:
```zsh
fpath=($(pwd)/completions $fpath)
```

### Fish
```bash
cp completions/puny-manager.fish ~/.config/fish/completions/puny-manager.fish
```

## Usage

Change language (en, de, fr, es, ru, pt, zh):
```bash
puny-manager lang        # lists available languages
puny-manager lang de     # switches to German
```

### Vault management

Create a new vault:
```bash
puny-manager create personal                   # balanced encryption
puny-manager create secrets --level paranoid   # 256MB Argon2id
puny-manager create throwaway --level fast     # 32MB, quicker unlock
```
Master passwords must be at least 4 characters.
For existing v1.x users: your vault auto-migrates on first run.

Manage vaults:
```bash
puny-manager vault list            # list all vaults (* = active)
puny-manager vault switch <name>   # change active vault
puny-manager vault delete <name>   # remove a vault
```

### Passwords & entries

Add a new entry:
```bash
puny-manager add                        # interactive prompts
puny-manager add --generate             # auto-generates password
puny-manager add --generate --length 32 # custom length
```
You can store optional URL and tags for entries.

List stored entries:
```bash
puny-manager list
```
Retrieve an entry (password is copied to clipboard):
```bash
puny-manager get <name>
```
Set clipboard clear timeout:
```bash
puny-manager get <name> --timeout 30
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
puny-manager edit <name>                # interactive
puny-manager edit <name> --generate     # regenerate password
```
Remove an entry:
```bash
puny-manager rm <name>
```

### Audit

Check vault health and password hygiene:
```bash
puny-manager stats
```
Shows entry count, weak passwords, duplicate detection, and tag breakdown
without revealing any actual passwords.

### Export/Import

Export vault to JSON:
```bash
puny-manager export vault.json
```

Export vault to CSV:
```bash
puny-manager export vault.csv --csv
```

Import vault from JSON:
```bash
puny-manager import vault.json
```

Import vault from CSV:
```bash
puny-manager import vault.csv --csv
```

### Custom Fields

Add entries with custom key-value fields:
```bash
puny-manager add
# When prompted: Custom fields (key=value, comma-separated, optional): api_key=abc123, recovery_code=xyz
```

Edit custom fields:
```bash
puny-manager edit <name>
```

### Tags Filtering

List entries filtered by tag:
```bash
puny-manager list --tag work
```

### Configuration

View current configuration:
```bash
puny-manager config
```

Set configuration values:
```bash
puny-manager config default_length 32
puny-manager config backup_count 10
puny-manager config clipboard_timeout 30
```

### Backups

Vaults are automatically backed up before each save with rotating backups (5 by default).
Backups are stored as `vault-name.puny.bak.1`, `vault-name.puny.bak.2`, etc.
