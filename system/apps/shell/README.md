# <img src="./assets/rebos_shell/rebos_shell-logo-color.svg" alt="" width="40" height="40"> rebos_shell

**rebos_shell** is a Niri-first Wayland desktop shell built with
[Quickshell](https://quickshell.org).

## Hard fork

This project is a **hard fork** of
[Ambxst](https://github.com/Axenide/Ambxst) by
[Axenide](https://github.com/Axenide).

It is not Ambxst, does not track Ambxst as an upstream merge target for
day-to-day work, and ships under its own name, branding, config paths, and
release process. The fork keeps a lean runtime focus:

- wallpaper
- one unified bar
- floating run menu
- lockscreen
- reactive JSON configuration

Multi-monitor support uses Quickshell `Variants` on `Quickshell.screens`.

## Features

Version **1.1.6** adds the redesigned clock dashboard, edge window navigation,
desktop shortcut creation and adjustable window corners. It also updates shell
outlines, media handling, blur and idle network resource use.

Published source and the complete Arch desktop are maintained in the
[rebos_enclosure installer](https://github.com/Rebo-NS4U/rebos_enclosure).

- Runs directly on [Niri](https://github.com/YaLTeR/niri) via its JSON event stream
- Normalized monitor, workspace, and window state for multi-monitor setups
- Unified bar with workspaces/taskbar, clock, system status, and systray
- Floating run menu and power menu
- Wallpaper picker and secure `WlSessionLock` session lock
- Isolated `rebos_shell` config, state, cache, data, and IPC paths
- [Persistent assistant](scripts/ai_bridge.md) that keeps working across shell reloads

## Direct commands

The shell exposes lightweight commands through its IPC runner. For example,
`rebos_shell run wallpapers` opens the wallpaper picker on the focused monitor
and toggles it closed when invoked again. This can be bound from Niri with:

```kdl
Mod+Shift+W hotkey-overlay-title="Open Wallpapers" { spawn "rebos_shell" "run" "wallpapers"; }
```

## Run the development tree

Install Quickshell and the runtime tools needed by the shell. Install fonts once,
then run from a checkout:

```bash
./scripts/install-fonts.sh
qs -p /path/to/rebos_shell
```

Or use the CLI wrapper:

```bash
./cli.sh
```

## Updater

Use the [rebos_enclosure updater](https://github.com/Rebo-NS4U/rebos_enclosure/blob/main/update.sh)
from your enclosure checkout to update the bundled desktop while keeping saved
preferences:

```bash
cd /path/to/rebos_enclosure
./update.sh --dry-run     # Fetch and verify without changing installed files
./update.sh --files-only  # Apply desktop files without upgrading packages
```

The updater fetches the remote default branch, verifies the payload, and creates
a recovery backup under `~/.local/state/rebos-desktop/backups`. Git and Python 3
are required; run it as your normal user. Standard XDG paths under HOME are required.
Existing preferences and wallpapers are retained. Without `--files-only`, the
updater also upgrades installed packages. Log out and back in after applying an
update to load the updated desktop.

The installer and Nix package are still inherited scaffolding and may need
adjustment for this fork.

## Attribution and license

rebos_shell is a customized desktop shell derived from Ambxst by Axenide and contributions by jR4dh3y. Full copyright and
contributor history from that lineage is preserved in this repository’s Git
history.

This project is licensed under the GNU Affero General Public License v3.0 or
later. See [LICENSE](./LICENSE).

### Continuous typing dropdown

Open the island bar's control panel and choose **Typing practice →**. Typing
replaces the expanded bar contents, using the same input and dismissal behavior
as its other panels. The compact typing surface uses a faint glass fill, soft blur and a subtle rim;
controls are text only. Practice shows about 90 characters at a time, with only
Edit and Back in the header. Setup controls stay hidden while typing. Panel
resizing, passage reveals and typed characters animate smoothly, respecting the
Appearance motion setting (zero disables animations). Upcoming characters are faint, and typed characters become opaque
(errors use the error color). Type directly over the passage. Backspace to correct.
Paste text or import documents, then select **Start practice**. Completed passages
advance and the document loops forever, without a timer or failure state. **Back**
or Escape returns to the control panel. Clicking outside collapses the bar.
Text stays in this shell session and is not uploaded or saved. PDF import uses
Poppler's `pdftotext`; scanned PDFs require OCR before import. Legacy DOC and RTF
are not supported. IPC: `qs -p ~/.config/quickshell/shell.qml ipc call typing toggle`.

The **Practice texts** selector includes six original CC0 passages: a lowercase
warmup, two short stories, a reflective passage, dialogue and punctuation, and
numbers and everyday details. Select one, then choose **Start practice**. These
passages may be copied, changed and shared freely. Choosing a passage replaces
the text in the editor; pasting and document import remain available.
