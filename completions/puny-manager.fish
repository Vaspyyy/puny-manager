# puny-manager fish completion
# Install to:
#   ~/.config/fish/completions/puny-manager.fish

complete -c puny-manager -f

# global flags
complete -c puny-manager -l version -d 'Show version'
complete -c puny-manager -l help -d 'Show help'

# top-level subcommands
set -l topcmds create list add get rm stats gen passwd edit lang vault howdy

for cmd in $topcmds
    complete -c puny-manager -n "not __fish_seen_subcommand_from $topcmds" -a "$cmd"
end

# create
complete -c puny-manager -n '__fish_seen_subcommand_from create' -a create -d 'Create a new vault'
complete -c puny-manager -n '__fish_seen_subcommand_from create' -l level -d 'Encryption level (fast, balanced, paranoid)' -r -a 'fast balanced paranoid'
# list
complete -c puny-manager -n '__fish_seen_subcommand_from list' -a list -d 'List entries'
# add
complete -c puny-manager -n '__fish_seen_subcommand_from add' -a add -d 'Add a new entry'
complete -c puny-manager -n '__fish_seen_subcommand_from add' -l generate -d 'Auto-generate password'
complete -c puny-manager -n '__fish_seen_subcommand_from add' -l length -d 'Password length'
# edit
complete -c puny-manager -n '__fish_seen_subcommand_from edit' -a edit -d 'Edit an entry'
complete -c puny-manager -n '__fish_seen_subcommand_from edit' -l generate -d 'Auto-generate password'
complete -c puny-manager -n '__fish_seen_subcommand_from edit' -l length -d 'Password length'
# stats
complete -c puny-manager -n '__fish_seen_subcommand_from stats' -a stats -d 'Audit vault'
# lang
complete -c puny-manager -n '__fish_seen_subcommand_from lang' -a lang -d 'Set language'
complete -c puny-manager -n '__fish_seen_subcommand_from lang' -a 'en de fr es ru pt zh'
# vault
complete -c puny-manager -n '__fish_seen_subcommand_from vault' -a vault -d 'Manage vaults'
set -l vaultcmds list switch delete
for cmd in $vaultcmds
    complete -c puny-manager -n "__fish_seen_subcommand_from vault; and not __fish_seen_subcommand_from $vaultcmds" -a "$cmd"
end
complete -c puny-manager -n '__fish_seen_subcommand_from vault; and __fish_seen_subcommand_from list' -a list -d 'List vaults'
complete -c puny-manager -n '__fish_seen_subcommand_from vault; and __fish_seen_subcommand_from switch' -a switch -d 'Switch active vault'
complete -c puny-manager -n '__fish_seen_subcommand_from vault; and __fish_seen_subcommand_from delete' -a delete -d 'Delete a vault'
# howdy
complete -c puny-manager -n '__fish_seen_subcommand_from howdy' -a howdy -d 'Manage facial unlock'
set -l howdycmds enable disable status test
for cmd in $howdycmds
    complete -c puny-manager -n "__fish_seen_subcommand_from howdy; and not __fish_seen_subcommand_from $howdycmds" -a "$cmd"
end
complete -c puny-manager -n '__fish_seen_subcommand_from howdy; and __fish_seen_subcommand_from enable disable' -l master-password -d 'Master password (non-interactive)' -r
