# Interactive completions and search; keep scripts and batch commands quiet.
if not status is-interactive
    return
end

set -g fish_autosuggestion_enabled 1

function __rebos_shell_refresh_palette --on-event fish_prompt
    set -l palette "$HOME/.cache/rebos_shell/fish.fish"
    if test -r "$palette"
        source "$palette"
    end
end
__rebos_shell_refresh_palette

if command -q fzf
    set -gx FZF_DEFAULT_OPTS_FILE "$HOME/.cache/rebos_shell/fzf.conf"
    if command -q fd
        set -gx FZF_CTRL_T_COMMAND 'fd --type f --type d --hidden --exclude .git --exclude node_modules --exclude .cache'
        set -gx FZF_ALT_C_COMMAND 'fd --type d --hidden --exclude .git --exclude node_modules --exclude .cache'
    end
    # Official bindings: Ctrl+R history, Ctrl+T paths, Alt+C directories,
    # and Shift+Tab fuzzy completion. Normal Tab retains fish completion.
    fzf --fish | source
end

bind ctrl-space accept-autosuggestion
bind -M insert ctrl-space accept-autosuggestion
