# puny-manager bash completion
# Source this file or install to:
#   ~/.local/share/bash-completion/completions/puny-manager

_puny_manager() {
    local cur prev words cword
    _init_completion || return

    if ((cword == 1)); then
        COMPREPLY=($(compgen -W "create list add get rm stats gen passwd edit lang vault howdy --version --help" -- "$cur"))
        return
    fi

    case "${words[1]}" in
        vault)
            if ((cword == 2)); then
                COMPREPLY=($(compgen -W "list switch delete" -- "$cur"))
            fi
            ;;
        howdy)
            if ((cword == 2)); then
                COMPREPLY=($(compgen -W "enable disable status test" -- "$cur"))
            elif [[ "${words[2]}" == "enable" || "${words[2]}" == "disable" ]]; then
                COMPREPLY=($(compgen -W "--master-password --help" -- "$cur"))
            fi
            ;;
        create)
            COMPREPLY=($(compgen -W "--level" -- "$cur"))
            ;;
        add|edit)
            COMPREPLY=($(compgen -W "--generate --length --help" -- "$cur"))
            ;;
        get)
            case "$prev" in
                --timeout)
                    COMPREPLY=()
                    ;;
                *)
                    COMPREPLY=($(compgen -W "--timeout --help" -- "$cur"))
                    ;;
            esac
            ;;
        lang)
            COMPREPLY=($(compgen -W "en de fr es ru pt zh" -- "$cur"))
            ;;
        *)
            COMPREPLY=()
            ;;
    esac
} && complete -F _puny_manager puny-manager
complete -F _puny_manager pt
