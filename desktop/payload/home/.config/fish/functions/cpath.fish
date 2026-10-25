function cpath --description 'Copy the absolute path of a file or the current directory'
    if test (count $argv) -gt 1
        printf 'Usage: cpath [file-or-directory]\n' >&2
        return 2
    end
    set -l target "$PWD"
    if set -q argv[1]
        set target (path resolve -- "$argv[1]")
        or return
    end
    if command -q wl-copy; and set -q WAYLAND_DISPLAY
        printf '%s' "$target" | command wl-copy
        or return
        printf 'Copied: %s\n' "$target"
    else
        printf '%s\n' "$target"
    end
end
