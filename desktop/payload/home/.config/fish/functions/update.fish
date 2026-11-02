function update --description 'Update system/AUR packages, Flatpaks, and Rust toolchains'
    if test (count $argv) -gt 1
        printf 'Usage: update [--dry-run | --help]\n' >&2
        return 2
    end
    if set -q argv[1]
        switch $argv[1]
            case --dry-run --help -h
            case '*'
                printf 'Usage: update [--dry-run | --help]\n' >&2
                return 2
        end
    end
    bash "$HOME/.config/scripts/package-menu.sh" --update $argv
end
