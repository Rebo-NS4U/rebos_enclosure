# rebos desktop installer

Recreates the current rebos Niri/Quickshell desktop on an **already installed, bootable x86_64 Arch Linux system**. This is a desktop installer, with no partitioning, formatting, bootloader installation, or ISO creation. Snapshot date: 2026-10-27 (local time).

## Install on minimal Arch

Boot into your installed system and connect it to the internet. Use a normal user with a password and sudo access. If you have only root, prepare the user first, replacing `yourname`:

```bash
pacman -Syu sudo python
useradd -m -G wheel -s /bin/bash yourname   # only if this user does not exist
passwd yourname
EDITOR=nano visudo                       # uncomment: %wheel ALL=(ALL:ALL) ALL
```

Use an editor installed on your machine in place of `nano` if needed. Log out of root and log in as that user, then clone the repository. Authenticate Git first: this repository is private.

```bash
sudo pacman -Syu --needed git python
git clone --depth=1 https://github.com/Rebo-NS4U/rebos_enclosure.git
cd rebos_enclosure
bash install.sh --interactive --dry-run
bash install.sh
```

Commands below are run from the repository root. The implementation and payload live in `desktop/`. No separate installer archive or submodules are needed. Existing Paru or Yay is reused; otherwise the installer builds Paru. Standard XDG user folders are initialized during full/core installation.

Both `install.sh` and `desktop/install.sh` fetch a fresh temporary snapshot of the
official repository's default branch before planning or installing, and print the
exact commit being used. A fetch failure stops installation; it never silently
uses an old checkout. Your checkout and local edits remain untouched. `--dry-run`
also fetches, but does not change installed files or packages. Git authentication
must be available for private sources. `REPO_URL` and `BRANCH` explicitly override
the source and branch. Use `--release TAG` to fetch an exact release tag instead:

```bash
bash install.sh --release v1.3.1 --interactive --dry-run
bash install.sh --release v1.3.1
```

The selector works through both installer entry points. A missing tag stops before
installation; a branch with the same name is never used in its place. `--release`
cannot be combined with `BRANCH` or `--local-snapshot`.
For intentional offline previews or testing local edits,
use `bash install.sh --local-snapshot --dry-run`; `--local-snapshot` deliberately
bypasses the freshness check. Help is available without network access.

The default **full** profile installs the desktop and applications, then offers normal AUR package review for Zen, Spicetify, VS Code and mpvpaper (video wallpapers). Review package build files as you would for any AUR installation. `--yes` accepts the desktop plan; it does not bypass AUR review. Internet and current Arch mirrors are required; this is a configuration snapshot, not an offline package mirror. Core and `--no-aur` installs support image wallpapers; video wallpapers require mpvpaper separately.

```bash
bash install.sh --profile core       # desktop, Firefox and Neovim, without extra apps or AUR
bash install.sh --no-aur             # full official apps, skip the optional AUR apps
bash install.sh --no-login           # keep your current display manager
bash install.sh --keep-network       # retain your existing network service setup
bash install.sh --files-only         # copy settings only; dependencies must already exist
```

Reboot after installation. Select **Niri** in ReGreet, log in and open a terminal with **Super+Return**. A manually started session should use `niri-session` from a TTY. The packaged session exports the environment for portals and session services. See [Niri's session documentation](https://github.com/niri-wm/niri/wiki/Getting-Started). ReGreet runs under Cage through greetd on tty1, with its corresponding getty disabled. Enabled Ly units are disabled for the next boot; no running session is stopped.

## Interactive configuration

Run `./install.sh` without options in a terminal to open setup, or `./install.sh --interactive --dry-run` for a read-only walkthrough. The [root guide](../README.md#interactive-setup) describes each menu choice. `--dry-run` by itself uses defaults/flags without opening the menu.

Applications are selectable by group. CLI alternatives include `--groups notes,media`, `--graphics keep`, `--no-bluetooth`, `--no-power`, `--hybrid`, `--early-kms`, and `--monitors FILE`. Run `./install.sh --help` for all values. The final package list and monitor configuration are shown before confirmation. AUR driver packages still require AUR review.

For a reusable monitor specification, copy [examples/monitors.json](examples/monitors.json) and replace connector names/modes with your hardware. `layout` accepts `auto`, `horizontal`, `vertical` or `manual`. Each output accepts `name`, `enabled`, `mode` (`auto` or `WIDTHxHEIGHT@REFRESH`), `scale`, `transform`, `primary`, and optional `position: {"x": 0, "y": 0}` for manual layout. At least one monitor must remain enabled. Automatic row/column layouts need known dimensions; manual coordinates are logical pixels after scaling and rotation. See [Niri's output configuration](https://github.com/niri-wm/niri/blob/main/resources/default-config.kdl).

Monitor choices are generated into `~/.config/niri/monitors.kdl` with an include in the installed Niri config. The chosen plan is saved as `~/.local/state/rebos-desktop/installation.json` with mode 600. A selected hybrid NVIDIA setup adds `~/.local/bin/rebos-prime-run`. All of these user files restore with the installation backup. Driver module/early KMS files are system settings: their originals, when present, are saved with the system backup, but the user-file restore does not revert them or remove driver packages.

Early KMS is optional and currently supports mkinitcpio. It adds an additive NVIDIA `MODULES` drop-in, preserves existing module lists and rebuilds initramfs. Selected NVIDIA drivers also receive DRM modesetting parameters. The current [Arch NVIDIA table](https://wiki.archlinux.org/title/NVIDIA) documents GPU branch support, and [PRIME documentation](https://wiki.archlinux.org/title/PRIME#PRIME_render_offload) describes the offload environment used by the launcher. The installer does not rewrite the bootloader or force the desktop onto the discrete GPU.

## Included

- Live rebos_shell QML and scripts: island bar, launcher, dashboard, lockscreen, notifications, settings and wallpaper color/sort controls. No clone of an older upstream shell is needed.
- Portable Niri keybindings, named workspaces, rounded windows, transparency and blur. Applications open on the current workspace. Monitor modes are selected by the destination computer.
- Dark OLED theme with wallpaper-driven GTK, Qt, KDE, Kitty, Fish, Fuzzel, btop, Neovim and supported app palettes; a current palette snapshot is provided for the first login.
- Kitty/Fish prompt and shortcuts, wallpaper-colored bonsai greeting, cbonsai source and license, bundled terminal/shell fonts, GoogleDot cursor and Papirus icons.
- Custom Neovim IDE configuration and plugin lockfile. Plugins and language servers download separately through Neovim on first use; open `:IDEHelp` for instructions.
- Original rice wallpapers, 149 prepared 1920×1200 Urban/Nature wallpapers, and the current background. Source metadata is retained in the wallpaper folders; the collection is from <https://github.com/dharmx/walls>.
- Themed ReGreet login configuration, background, layout extension and GoogleDot cursor, NetworkManager, Bluetooth, PipeWire/WirePlumber, power profiles, authentication agent, portals, screenshots, OCR and clipboard history.
- Full-profile apps include Discord, Spotify Launcher, OBS, Obsidian, Firefox, image viewer, developer tools, and the optional AUR apps listed above.

Anime Streamer captions can automatically detect each speech span's language and
produce English subtitles. English retains word timing; translations retain speech
timing. Settings → **Auto-detect language and translate to English** selects the
multilingual `ggml-base.bin` model; turning it off uses `ggml-base.en.bin` for English
only. Whisper binaries, Silero VAD and models require separate local setup and are
not bundled. Short-clip checks found correct detection but mixed French/Italian
translation and poor German/Japanese/Korean translation with the base model;
do not treat detection success as evidence of translation accuracy.

Series playback queues continue across released seasons, keep specials separate,
and enforce the selected resolution limit. Next-episode preparation buffers a
bounded startup prefix; VLC receives chapter names for credits detection and
uses MP4 demuxing and network buffering options for network playback.

The package shortcuts share one menu for official/AUR installation, removal,
and updates. Fish `update --dry-run` previews the Arch/AUR, Flatpak and Rust
update commands. Administrator operations use `assistant-sudo`; package-manager
review and confirmation remain enabled. Configuration Browser is also included
as a launcher entry for opening desktop configuration folders.

The assistant's GitHub workflow applies across projects and backends: edit in the
owning repository, keep applicable installed and installer files synchronized,
then commit and push tested task changes. It preserves unrelated work and normal
approval boundaries. The policy is delivered once to each backend conversation,
including older restored chats, and persists across reconnects. Releases are
created when requested.

Login packages are `greetd`, `greetd-regreet` and `cage`. The tracked greetd and
ReGreet configuration lives in `desktop/payload/system/greetd/`; the matching
layout, cursor extension and theme assets live in `desktop/payload/system/rebos-greeter/`.
The former `install/ly/` configuration and patches have been removed.

Base packages and optional application groups are editable in `desktop/packages/core.txt` and `desktop/packages/groups.json`. Driver packages are selected by the installer. A full system upgrade precedes package installation. The installer uses configured repositories and does not add Chaotic-AUR, replace the kernel, or copy this computer's GPU driver settings. Intel/AMD microcode and graphics userspace packages are detected from the destination. **NVIDIA:** the setup menu offers open DKMS and legacy 580 DKMS branches, matching kernel headers, hybrid offload and optional mkinitcpio early KMS. Choose the branch appropriate to the GPU; the installer does not guess NVIDIA generations or remove conflicting installed driver families automatically. Consult [Arch's NVIDIA guide](https://wiki.archlinux.org/title/NVIDIA). Existing network service enablement changes take effect on reboot so installation does not disconnect the active link. If using a custom network stack, use `--keep-network`.

The portable clipboard shortcut uses cliphist/Fuzzel. Spotify Launcher replaces the machine-local Cider shortcut. Hardware trays, Tailscale/WARP, Victus-specific fixes, Steam/game libraries, custom AI executables and paid apps are not automatically installed. The shell's assistant needs a separately installed/configured agent. Personal logins, browser profiles, messages, history, notes, weather location, AI credentials, SSH keys and local secret files are excluded. Weather defaults to Celsius with an empty location.

## First login

Fresh installs use the pinned classic island bar (80% opacity, 55% accent), a 12-hour clock, Firefox media integration, and the Transparent theme. Bar and theme defaults live in `desktop/defaults/` and also seed the reset preset; updates preserve existing preferences.

New installs use H/J/K/L for **left/down/up/right**:

| Modifier with H/J/K/L | Action |
| --- | --- |
| Super | Select the active window on this screen |
| Super+Shift | Reposition the current window within this screen |
| Super+Ctrl | Focus the monitor in that direction |
| Super+Shift+Ctrl | Move the current window to the monitor in that direction |

The defaults are in `~/.config/niri/keybindings-defaults.kdl`. Personal changes go in
`~/.config/niri/keybindings-personal.kdl`, which loads last. Settings saves added
shortcuts and remaps there. Kitty uses the equivalent `keybindings-defaults.conf`
and `keybindings-personal.conf` in `~/.config/kitty/`.

A reinstall saves existing shortcuts, including included profiles and terminal
mappings, into these personal files before replacing the configuration folders.
If a user directly edits the default Niri file, the installer detects the change
and saves those bindings too. Updates keep the installed configuration folders
in place. Both paths retain personal keys; the deployment backup also keeps the
original files for restoration. A fresh install starts with empty personal files.

Versioned defaults in `desktop/defaults/` are the source for future snapshots;
the snapshot builder does not copy the maintainer's personal shortcut files into
new installer defaults. Niri loads later bindings as overrides, as described in
its [include documentation](https://niri-wm.github.io/niri/Configuration%3A-Include.html).

| Shortcut | Action |
| --- | --- |
| Super+Return | Kitty/Fish with bonsai |
| Super+Space | Application launcher |
| Super+N | Dashboard |
| Super+V | Clipboard history |
| Super+Shift+W | Wallpaper gallery |
| Super+Alt+Left / Right / W | Previous / next / random prepared wallpaper |
| Super+Alt+L | Lock screen |
| Super+W / E | Browser / file manager |
| Super+Shift+/ | Keybinding help |

Open Settings from the launcher to adjust weather location, displays and theme. Choose any wallpaper to generate a fresh palette. Open Zen once to create its profile and Spotify Launcher once to install its client and sign in. Close Spotify, then run:

```bash
bash desktop/scripts/finish-apps.sh
```

App profile initialization and Spotify authentication cannot be copied from this computer. First-session GUI, lock/unlock, hardware compatibility, screen sharing, AUR builds and app downloads still need validation on the target machine.

## Update

The panel runs as `rebos-panel.service`, independently of the assistant. It recovers
from failures and does not automatically reload QML source files, avoiding a Qt
screen-lifecycle crash. After editing panel code, apply it with
`systemctl --user restart rebos-panel.service`. Niri still reloads its configuration
automatically. The media menu stays mapped with no blur or input capture when closed;
the appearance blur setting is loaded through `niri-blur.kdl`.

On Qt 6.12.0, the service builds a small local screen-pointer guard from the bundled
source when a compiler and private headers are available. No prebuilt library or
machine-specific hashes are shipped. Other Qt versions skip the build; a Qt library
change disables the old guard. Build failure is logged and does not prevent startup.
The guard is a workaround for the observed Qt crash, not a general Qt fix.

Already installed and just want the latest version? Use this to update your system and desktop while keeping your personal settings.

Run these commands from the installer folder you cloned or extracted:

```bash
./update.sh --dry-run
./update.sh
```

The first command previews the update. Log out and back in after applying the update.

Updates replace managed scripts and user service definitions, including the
package menu and Fish `update` command. Personal Fish configuration, other
functions, desktop preferences and shortcuts stay in place. The file backup
also restores the previous managed commands and service definitions.

Select a specific release with its exact tag from
[GitHub releases](https://github.com/Rebo-NS4U/rebos_enclosure/releases):

```bash
./update.sh --release v1.3.1 --dry-run
./update.sh --release v1.3.1
```

Omitting `--release` uses the default branch. `--release` and `--branch` are
mutually exclusive; `--repository URL` can still select another source. A missing
tag stops before changes. Personal settings are retained when selecting a release.
Release selection pins desktop files, while package upgrades use current Arch/AUR
repositories. Add `--files-only` to skip package upgrades. Selecting an older
desktop release does not downgrade packages or reverse system service changes.

## Backups and recovery

Each replaced user entry is moved to a unique directory in `~/.local/state/rebos-desktop/backups/`. Existing dotfile component symlinks are backed up as links and replaced locally, so the installer does not write through them into another repository. Linked parent folders inside `.config`, such as `environment.d` and `scripts`, are backed up and copied locally before selected files are installed. Their unrelated contents are preserved, their source directories stay unchanged, and restore reinstates the original links. Dry run lists these planned conversions without changing anything. Broken links, linked top-level containers such as `.config`, and linked parents outside `.config` are refused with a readable error.

Other files in shared folders such as `.local/bin` are preserved unless their selected entry is replaced. Selected whole directories, including Kitty, Fish, Quickshell, GTK and Neovim, are backed up and replaced together.

To restore an installation, use the exact backup path printed by the installer:

```bash
python3 desktop/scripts/deploy.py --restore "$HOME/.local/state/rebos-desktop/backups/TIMESTAMP"
```

Restoring replaces those installed entries, including edits made to them since installation. It does not uninstall packages or undo system service changes. Original greetd configuration, greeter assets, system cursor theme and a before-install unit enablement listing are saved under `/var/backups/rebos-desktop/TIMESTAMP-PID/`. To return to TTY login, disable `greetd.service` and enable `getty@tty1.service`; use the saved listing to restore your former network service choices. The bundled GTK layout and Cage cursor extensions are compiled locally; their sources and theme assets are installed with system-readable permissions. No service is restarted during the installer.

## Maintainer checks

```bash
python3 desktop/scripts/deploy.py --verify
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s desktop/tests -v
bash -n install.sh desktop/install.sh oneline.sh desktop/scripts/finish-apps.sh
```

`desktop/scripts/snapshot.py` is the explicit selection recipe for this source desktop. To refresh, first move the existing `desktop/payload/` aside; then run `python3 desktop/scripts/snapshot.py --home /path/to/source/home` on the source machine. Inspect the result before sharing. Snapshot checksums detect corruption and accidental edits; they do not provide publisher authentication. Preserve the bundled component licenses; wallpaper redistribution rights remain with their respective authors. This folder can be moved or deleted after installation because installed settings are copies, with no dependency on its location.

ReGreet follows the current desktop wallpaper and effective color palette through
`regreet-sync.path`, with a timer to retry failures and detect edits to the image.
Installation and `update.sh` enable the sync for an existing Enclosure greeter and
refresh its theme immediately; the next login displays the result. The first
update may request administrator approval to grant the desktop user ownership of
`/var/lib/rebos-greeter/theme` only. It does not restart greetd or the desktop.
The CSS template and sync units are managed code refreshed by updates; wallpaper
and color preferences remain preserved. Animated wallpapers use a still frame.
