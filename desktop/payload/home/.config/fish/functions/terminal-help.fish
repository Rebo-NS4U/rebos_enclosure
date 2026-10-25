function terminal-help --description 'Show your terminal shortcuts and everyday commands'
    set -l heading (set_color --bold)
    set -l reset (set_color normal)
    printf '\n%sFind commands and files%s\n' "$heading" "$reset"
    printf '  Tab             Complete commands and paths; press again for choices\n'
    printf '  Right / Ctrl+Space  Accept the gray suggestion at the end of the line\n'
    printf '  Ctrl+R          Search command history; Enter selects, then Enter runs\n'
    printf '  Ctrl+T          Search and insert a file or directory path\n'
    printf '  Alt+C           Search for a directory and enter it\n'
    printf '  Esc             Cancel a search; Ctrl+C cancels a command\n'
    printf '\n%sMove around%s\n' "$heading" "$reset"
    printf '  z project       Jump to a previously visited directory by name\n'
    printf '  zi              Choose from previously visited directories\n'
    printf '  Alt+Left/Right  Directory back/forward on an empty line; otherwise move by word\n'
    printf '  cd -            Return to your previous directory\n'
    printf '  up / up 2       Go up one / two directories\n'
    printf '  mkcd "new dir"  Create a directory and enter it\n'
    printf '\n%sFiles and Git%s\n' "$heading" "$reset"
    printf '  ls / la / ll    Compact listing / hidden files included / details and sizes\n'
    printf '  lt / l.         Directory tree (recursive listing without tree) / hidden files\n'
    printf '  x <path>        Open a file or folder in its desktop app\n'
    printf '  copy <src> <dst>  Copy a file or directory\n'
    printf '  backup <path>   Make a .bak copy; ask before replacing an existing backup\n'
    printf '  cpath [path]    Copy an absolute path on Wayland; otherwise print it\n'
    printf '  gs / gd / gl    Expand to Git status / diff / recent commits when you press Space\n'
    printf '  Git prompt      clean, staged, edited, new; ahead/behind your remote\n'
    printf '  exit N          The last command failed with status N\n'
    printf '\n%sKitty window shortcuts%s\n' "$heading" "$reset"
    printf '  Ctrl+Shift+C/V  Copy / paste\n'
    printf '  Ctrl+Shift+F    Search terminal output\n'
    printf '  Ctrl+Shift+G    View the last command output\n'
    printf '  Ctrl+Shift+Up/Down  Jump between command prompts\n'
    printf '  Ctrl+Shift+U    Select and open a link using keyboard hints\n'
    printf '  Ctrl+Shift+N    New window in the current directory\n'
    printf '  Ctrl+Shift+plus/minus/0  Larger / smaller / reset text size\n'
    printf '\nRun terminal-help anytime. New windows load these settings automatically.\n\n'
end
