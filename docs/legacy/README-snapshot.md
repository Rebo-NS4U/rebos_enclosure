# rebos_enclosure

My Arch Linux desktop configuration: Niri, a customized rebos_shell Quickshell,
Fish, Kitty, GTK/Qt themes, and desktop utilities.

This is a snapshot of the working configuration on 2026-10-10. Quickshell is
included directly, so local modifications survive cloning without submodules.
The active configuration at `~/code/dots-niri` and this snapshot use the
`rebos_shell` branding.

## Restore configuration

Install the applications you use first. The desktop needs Niri, Quickshell,
Fish, Kitty, and the dependencies listed in `install/pkg.txt`.

```bash
git clone https://github.com/Dytox2/rebos_enclosure.git "$HOME/code/rebos_enclosure"
cd "$HOME/code/rebos_enclosure"
./restore.sh --dry-run
./restore.sh
```

The restore script links the included `.config` entries and Bash files, plus
each file in `.local/bin`, `.local/share/applications`, and `.local/share/fonts`.
Existing destinations are moved to a timestamped directory under
`~/.local/state/dotfiles/backups`. It does not install packages or change system
services. Restart your shell after restoring Bash settings. Niri and Quickshell
may automatically reload when their config changes.

The configuration targets this desktop; monitor names, keybindings, fonts, and
application paths may need adjustment on another computer. Wallpapers are
included in `assets/wal`; the upstream installer copies them into
`~/.local/share/wallpapers`. `packages-explicit.txt` records explicitly installed
packages as a reference, not a command to install everything.

## Keep changes

After restoration, linked config files are edited directly in this repo.

```bash
git status
git add <files-you-changed>
git commit -m "Update desktop config"
git push
```

Account sessions, browser profiles, shell history, AI settings, weather location,
and credentials were excluded. Review new files before committing to this
repository; ignore rules cannot detect every secret.

## Credits and installer

Based on [jR4dh3y's dots-niri](https://github.com/jR4dh3y/dots-niri) and
[rebos_shell](https://github.com/Dytox2/rebos_enclosure).
Quickshell retains its AGPL-3.0 license in `.config/quickshell/LICENSE`; its bundled
source includes local modifications captured on 2026-10-10.

`UPSTREAM.md` preserves the original README for reference. The inherited
`install/` scripts perform broader Arch setup, including packages and services;
review them before running. Upstream bootstrap links in that document install
the upstream project.
