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
puny-manager edit <name>
```
Remove an entry:
```bash
puny-manager rm <name>
```
