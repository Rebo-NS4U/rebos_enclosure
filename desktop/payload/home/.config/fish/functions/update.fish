function update --description 'Update system/AUR packages, Flatpaks, and Rust toolchains'
    set -l dry_run 0
    if test (count $argv) -gt 1
        printf 'Usage: update [--dry-run | --help]\n' >&2
        return 2
    end
    if set -q argv[1]
        switch $argv[1]
            case --dry-run
                set dry_run 1
            case -h --help
                printf '%s\n' 'Usage: update [--dry-run | --help]' \
                    'Updates Arch repositories and AUR (including development packages),' \
                    'system/user Flatpaks, and installed Rust toolchains.' \
                    'Keeps normal package-manager prompts; reports any failed stages.' \
                    'Pacman-managed npm packages and rustup itself update with Arch packages.'
                return 0
            case '*'
                printf 'Unknown option: %s\nUsage: update [--dry-run | --help]\n' "$argv[1]" >&2
                return 2
        end
    end

    set -l failed
    for stage in packages flatpak-system flatpak-user rust
        set -l cmd
        switch $stage
            case packages
                if command -q paru
                    set cmd paru -Syu --devel
                else if command -q yay
                    set cmd yay -Syu --devel
                else
                    set cmd sudo pacman -Syu
                    printf 'No AUR helper found; only repository packages will update.\n' >&2
                end
            case flatpak-system
                command -q flatpak; or continue
                set cmd flatpak update --system
            case flatpak-user
                command -q flatpak; or continue
                set cmd flatpak update --user
            case rust
                command -q rustup; or continue
                # rustup itself belongs to Pacman; only update its toolchains here.
                set cmd rustup update --no-self-update
        end

        printf '\n==> %s\n' "$stage"
        if test $dry_run -eq 1
            string join ' ' -- (string escape -- $cmd)
            continue
        end
        command $cmd
        set -l result $status
        if contains -- $result 130 143
            return $result
        else if test $result -ne 0
            set -a failed "$stage (exit $result)"
        end
    end

    if set -q failed[1]
        printf '\nUpdates failed: %s\n' (string join ', ' -- $failed) >&2
        return 1
    end
    if test $dry_run -eq 0
        printf '\nAll update stages completed successfully.\n'
    end
end
