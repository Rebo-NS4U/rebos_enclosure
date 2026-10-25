# Rebo's Neovim

The editor reads `~/.cache/rebos_shell/effective-palette.json` every two seconds.
Syntax, diagnostics, selections, terminal ANSI colors and UI accents follow the
desktop palette. Editor backgrounds stay transparent, using Kitty's existing
opacity. `:ThemeReload` refreshes immediately. A missing palette uses dark defaults.

## Getting started

Open a project with `cd /path/to/project && nvim .`.
Space is the leader key: `Space f f` means press those keys in sequence.
Press `i` to edit and Escape to return to normal mode. Ctrl-S saves.
Run `:IDEHelp` for this guide. `:checkhealth` checks the environment.

## Installation

Built-in tools work immediately without downloads: file explorer, fuzzy file
search, project search with quickfix results, terminal, run commands, Git views,
diagnostics, persistent undo, available language servers and syntax highlighting.
Lua, C, Markdown, Vim and query files use the parsers shipped with Neovim;
other languages use built-in syntax highlighting.

The first interactive launch downloads lazy.nvim and the plugins asynchronously.
Restart after `:Lazy` shows installation complete. If offline, the editor remains usable;
`:IDEInstall` retries the download. `:Lazy` shows plugin installation status.
`:Mason` manages language servers, formatters and Python debugging. Initial
downloads need internet access and can take a few minutes. The richer UI becomes
available after those installations finish. Use `:Lazy restore` to restore the
versions recorded in lazy-lock.json after an update.

Language tools are configured for Lua, Python, JavaScript/TypeScript/React, HTML,
CSS, JSON, YAML, Bash and C/C++. Rust uses rust-analyzer and rustfmt when available;
the rust-analyzer launcher exists but its toolchain component is currently missing.
Install it with `rustup component add rust-analyzer`. Additional languages and
debug adapters can be added in `lua/ide/plugins.lua`.

## Shortcuts

| Keys | Action |
| --- | --- |
| Ctrl-S / Space w | Save |
| Space e | Toggle explorer |
| Ctrl-P / Space f f | Find files |
| Space f g | Search project |
| Space f b | Open files |
| Shift-H / Shift-L | Previous / next file |
| Space b d | Close file (confirms unsaved changes) |
| Ctrl-H/J/K/L | Focus split |
| Space s v / Space s h | Vertical / horizontal split |
| Space t t | Toggle terminal |
| Escape Escape | Leave terminal input mode |
| Space r r | Run a command in the project terminal |
| gd / grr / gi | Definition / references / implementation |
| K | Documentation |
| Space c r / Space c a | Rename / code action |
| Space c s | Symbol outline |
| Space c f | Format |
| Space c d | Line diagnostics |
| Space x x | Project diagnostics |
| Space g s / Space g d | Git status / diff |
| Space ? | This guide |

With plugins installed, pausing after Space shows the shortcut menu. Completion
offers snippets, paths and language suggestions: Tab/Shift-Tab select, Enter
accepts, Ctrl-Space opens completion, Ctrl-E dismisses. Without plugins, Tab
offers buffer words and language servers provide native completion.

Additional plugin shortcuts: `Space f c` command palette, `Space f k` shortcut
search, `Space f r` recent files, `Space Space` smart file search, `Space c S`
workspace symbols, `Space u f` toggles formatting on save for the current buffer.

With plugins, formatting runs on save when a formatter is installed. Git hunk
commands are `Space g h p` preview, `Space g h s` stage, `Space g h r` reset and
`Space g h b` blame; `[h`/`]h` navigate changes.

## Debugging

Without plugins, F5 opens Neovim's built-in GDB interface (`:help termdebug`).
With plugins, Python uses Mason's debugpy; C/C++/Rust use the installed GDB DAP
adapter. Build native executables with debug symbols first. Python projects use
their virtual environment when detected by nvim-dap-python. Project-specific
launch configurations can go in `.vscode/launch.json` using matching adapter names.
Other runtimes require their own debug adapters.

| Keys (with plugins) | Action |
| --- | --- |
| F5 | Start / continue |
| F10 / F11 / F12 | Step over / into / out |
| Space d b | Toggle breakpoint |
| Space d B | Conditional breakpoint |
| Space d e | Evaluate variable or selection |
| Space d u | Toggle debugger panels |
| Space d q | Stop debugging |

No existing Neovim configuration was replaced. To revert, rename
`~/.config/nvim` to `~/.config/nvim.disabled`.
