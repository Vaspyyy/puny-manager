# puny-manager bash completion
# Source this file or install to:
#   ~/.local/share/bash-completion/completions/puny-manager

_puny_manager() {
    local cur prev words cword
    _init_completion || return

    if ((cword == 1)); then
        COMPREPLY=($(compgen -W "init list add get rm gen passwd edit lang --version --help" -- "$cur"))
        return
    fi

    case "${words[1]}" in
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
