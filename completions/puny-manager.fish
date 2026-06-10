# puny-manager fish completion
# Install to:
#   ~/.config/fish/completions/puny-manager.fish

complete -c puny-manager -f

# global flags
complete -c puny-manager -l version -d 'Show version'
complete -c puny-manager -l help -d 'Show help'

# top-level subcommands
set -l topcmds create list add get rm gen passwd edit lang vault

for cmd in $topcmds
    complete -c puny-manager -n "not __fish_seen_subcommand_from $topcmds" -a "$cmd"
end

# create
complete -c puny-manager -n '__fish_seen_subcommand_from create' -a create -d 'Create a new vault'
# list
complete -c puny-manager -n '__fish_seen_subcommand_from list' -a list -d 'List entries'
# add
complete -c puny-manager -n '__fish_seen_subcommand_from add' -a add -d 'Add a new entry'
# get
complete -c puny-manager -n '__fish_seen_subcommand_from get' -a get -d 'Show an entry'
complete -c puny-manager -n '__fish_seen_subcommand_from get' -l timeout -d 'Clipboard clear timeout in seconds'
# rm
complete -c puny-manager -n '__fish_seen_subcommand_from rm' -a rm -d 'Remove an entry'
# gen
complete -c puny-manager -n '__fish_seen_subcommand_from gen' -a gen -d 'Generate a secure password'
# passwd
complete -c puny-manager -n '__fish_seen_subcommand_from passwd' -a passwd -d 'Change master password'
# edit
complete -c puny-manager -n '__fish_seen_subcommand_from edit' -a edit -d 'Edit an entry'
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
