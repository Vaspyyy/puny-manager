# puny-manager fish completion
# Install to:
#   ~/.config/fish/completions/puny-manager.fish

complete -c puny-manager -f

# global flags
complete -c puny-manager -l version -d 'Show version'
complete -c puny-manager -l help -d 'Show help'

# subcommands
set -l subcmds init list add get rm gen passwd edit lang

for cmd in $subcmds
    complete -c puny-manager -n "not __fish_seen_subcommand_from $subcmds" -a "$cmd"
end

# init
complete -c puny-manager -n '__fish_seen_subcommand_from init' -a init -d 'Initialize a new vault'
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
