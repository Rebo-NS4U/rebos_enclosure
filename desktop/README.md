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

The default **full** profile installs the desktop and applications, then offers normal AUR package review for Zen, Spicetify, VS Code and mpvpaper (video wallpapers). Review package build files as you would for any AUR installation. `--yes` accepts the desktop plan; it does not bypass AUR review. Internet and current Arch mirrors are required; this is a configuration snapshot, not an offline package mirror. Core and `--no-aur` installs support image wallpapers; video wallpapers require mpvpaper separately.

```bash
bash install.sh --profile core       # desktop, Firefox and Neovim, without extra apps or AUR
bash install.sh --no-aur             # full official apps, skip the optional AUR apps
bash install.sh --no-login           # keep your current display manager
bash install.sh --keep-network       # retain your existing network service setup
bash install.sh --files-only         # copy settings only; dependencies must already exist
```

Reboot after installation. Select **Niri** in Ly, log in and open a terminal with **Super+Return**. A manually started session should use `niri-session` from a TTY. The packaged session exports the environment for portals and session services. See [Niri's session documentation](https://github.com/niri-wm/niri/wiki/Getting-Started). Ly uses tty2, with its corresponding getty disabled per the [Ly service setup](https://wiki.archlinux.org/title/Ly).

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
- Animated Ly login configuration, NetworkManager, Bluetooth, PipeWire/WirePlumber, power profiles, authentication agent, portals, screenshots, OCR and clipboard history.
- Full-profile apps include Discord, Spotify Launcher, OBS, Obsidian, Firefox, image viewer, developer tools, and the optional AUR apps listed above.

Base packages and optional application groups are editable in `desktop/packages/core.txt` and `desktop/packages/groups.json`. Driver packages are selected by the installer. A full system upgrade precedes package installation. The installer uses configured repositories and does not add Chaotic-AUR, replace the kernel, or copy this computer's GPU driver settings. Intel/AMD microcode and graphics userspace packages are detected from the destination. **NVIDIA:** the setup menu offers open DKMS and legacy 580 DKMS branches, matching kernel headers, hybrid offload and optional mkinitcpio early KMS. Choose the branch appropriate to the GPU; the installer does not guess NVIDIA generations or remove conflicting installed driver families automatically. Consult [Arch's NVIDIA guide](https://wiki.archlinux.org/title/NVIDIA). Existing network service enablement changes take effect on reboot so installation does not disconnect the active link. If using a custom network stack, use `--keep-network`.

The portable clipboard shortcut uses cliphist/Fuzzel. Spotify Launcher replaces the machine-local Cider shortcut. Hardware trays, Tailscale/WARP, Victus-specific fixes, Steam/game libraries, custom AI executables and paid apps are not automatically installed. The shell's assistant needs a separately installed/configured agent. Personal logins, browser profiles, messages, history, notes, weather location, AI credentials, SSH keys and local secret files are excluded. Weather defaults to Fahrenheit with an empty location.

## First login

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

## Backups and recovery

Each replaced user entry is moved to a unique directory in `~/.local/state/rebos-desktop/backups/`. Existing dotfile component symlinks are backed up as links and replaced locally, so the installer does not write through them into another repository. Linked parent folders inside `.config`, such as `environment.d` and `scripts`, are backed up and copied locally before selected files are installed. Their unrelated contents are preserved, their source directories stay unchanged, and restore reinstates the original links. Dry run lists these planned conversions without changing anything. Broken links, linked top-level containers such as `.config`, and linked parents outside `.config` are refused with a readable error.

Other files in shared folders such as `.local/bin` are preserved unless their selected entry is replaced. Selected whole directories, including Kitty, Fish, Quickshell, GTK and Neovim, are backed up and replaced together.

To restore an installation, use the exact backup path printed by the installer:

```bash
python3 desktop/scripts/deploy.py --restore "$HOME/.local/state/rebos-desktop/backups/TIMESTAMP"
```

Restoring replaces those installed entries, including edits made to them since installation. It does not uninstall packages or undo system service changes. Original Ly files and a before-install unit enablement listing are saved under `/var/backups/rebos-desktop/TIMESTAMP-PID/`. To return to TTY login, disable `ly@tty2.service` and enable `getty@tty2.service`; use the saved listing to restore your former network service choices. No service is restarted during the installer.

## Maintainer checks

```bash
python3 desktop/scripts/deploy.py --verify
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s desktop/tests -v
bash -n install.sh desktop/install.sh oneline.sh desktop/scripts/finish-apps.sh
```

`desktop/scripts/snapshot.py` is the explicit selection recipe for this source desktop. To refresh, first move the existing `desktop/payload/` aside; then run `python3 desktop/scripts/snapshot.py --home /path/to/source/home` on the source machine. Inspect the result before sharing. Snapshot checksums detect corruption and accidental edits; they do not provide publisher authentication. Preserve the bundled component licenses; wallpaper redistribution rights remain with their respective authors. This folder can be moved or deleted after installation because installed settings are copies, with no dependency on its location.
