# rebos_enclosure

Install my customized Niri/rebos_shell desktop on a bootable minimal **x86_64 Arch Linux** system. Clone this repo, run `install.sh`, then reboot and choose Niri at login.

The bundled desktop uses **rebos_shell 1.1.6** from
[Rebo-NS4U/rebos_shell](https://github.com/Rebo-NS4U/rebos_shell), with the redesigned
clock dashboard, edge window navigation, shortcut creation and adjustable window
corners. The snapshot also includes the separate assistant and media apps and
their user services. No account credentials or personal chat/media history are
included. Install and sign into your chosen assistant backend after installation
(the default Codex adapter also needs Node/npm from the development group);
local Whisper captions additionally need their optional model and runtime.

## Install

Boot the installed system, connect to the internet and log in as a normal user with a password and sudo access. Install the initial tools:

```bash
sudo pacman -Syu --needed git python
git clone --depth=1 https://github.com/Rebo-NS4U/rebos_enclosure.git
cd rebos_enclosure
bash install.sh --interactive --dry-run
bash install.sh
```

This repository is public. Installing it requires no GitHub login. Publishing changes requires write access through Git.

The installer upgrades the system, installs dependencies and applications, uses existing Paru/Yay or builds Paru, backs up existing settings, installs the bundled configuration, creates standard user directories and enables desktop services for the next boot. Run it without `sudo` in front; it uses sudo for system changes. AUR package review remains interactive.

This installs the desktop onto an existing Arch installation. It does not partition disks, format filesystems, create an ISO, install a bootloader or replace the kernel. For root-only Arch installations, user and sudo preparation are covered in [the detailed guide](desktop/README.md#install-on-minimal-arch).

## What's included

- Niri with current rebos_shell/Quickshell source: island bar, launcher, dashboard, settings, notifications, lockscreen, media controls and wallpaper gallery.
- Rounded windows, transparency, dark OLED styling, named workspaces and shortcuts. Applications open on the current workspace. Display modes adapt to the destination hardware.
- Matugen wallpaper colors across GTK, Qt/KDE, Kitty, Fish, Fuzzel, btop, Neovim and supported apps. Includes Zen/Spotify integration and a Vesktop theme file.
- Kitty/Fish with the custom prompt, fuzzy searching, navigation helpers and compiled wallpaper-colored bonsai greeting.
- Custom Neovim IDE configuration, plugin lockfile, bundled fonts, cursor, icons, animated Ly login screen and current wallpaper palette.
- Original rice wallpapers, 149 prepared 1920×1200 Urban/Nature wallpapers and the current background.
- NetworkManager, Bluetooth, PipeWire/WirePlumber, power profiles, desktop portals, clipboard history, screenshots and OCR tools.
- Full-profile apps: Firefox, Thunar, Discord, Spotify Launcher, OBS, Obsidian, imv, scrcpy, Flatpak, development tools and optional AUR software: Zen, VS Code, Spicetify and mpvpaper.

The shell and assets are checked into `desktop/payload/`; no submodules or separate installer archive are required. Packages download from the destination's configured repositories and AUR. Full inventory, exclusions, shortcuts and setup details are in [desktop/README.md](desktop/README.md). Edit base packages in [core.txt](desktop/packages/core.txt) and optional group definitions in [groups.json](desktop/packages/groups.json). [apps.txt](desktop/packages/apps.txt) and [aur.txt](desktop/packages/aur.txt) retain the full-profile application inventories; graphics packages are added according to the selection.

The package review and reasons for exclusions are recorded in [the package guide](desktop/packages/README.md). For the smallest supported desktop, use `--profile core`; add only the app groups you want with `--groups`. The default full profile still selects all optional groups.

## Interactive setup

`./install.sh` with no arguments opens a numbered terminal menu. To try every choice without installing anything:

```bash
./install.sh --interactive --dry-run
```

The menu covers:

- Core/full profile and optional groups: Zen, Discord, media, notes, recording, development, utilities and video wallpapers.
- AUR availability, detected CPU microcode and graphics packages: keep existing drivers, Intel, AMD, NVIDIA open DKMS, NVIDIA 580 DKMS, Nouveau or basic Mesa for virtual machines.
- NVIDIA kernel headers, optional hybrid offload launcher and optional early KMS with mkinitcpio.
- Each monitor's connector, enabled state, resolution/refresh, scale, rotation and startup focus. Choose automatic, horizontal, vertical or manual logical positioning.
- Ly versus your current login setup, NetworkManager versus current network services, Bluetooth and power profiles.

The complete plan is shown before installation. Enter `q` at a setup prompt or press Ctrl+C to cancel. `--dry-run` alone keeps the quick noninteractive preview; `--yes` uses defaults/flags and skips the final confirmation, while AUR review remains interactive.

Automatic graphics mode installs detected Intel/AMD userspace packages and leaves NVIDIA driver selection unchanged. NVIDIA branches are explicit choices based on your GPU generation; see [Arch's driver table](https://wiki.archlinux.org/title/NVIDIA). Existing conflicting NVIDIA driver families cause a clear stop, without automatic removal. DKMS selections install headers for detected installed kernels; custom kernels can use `--kernel-headers`. For hybrid NVIDIA, `rebos-prime-run <application>` offloads an app without forcing the whole desktop onto NVIDIA. Early KMS adds NVIDIA modules through a backed-up mkinitcpio drop-in; other initramfs generators are not configured by that option.

Monitor discovery uses Niri IPC when available and DRM connectors on a TTY. Missing monitors can be entered by connector name. Use known supported modes; automatic mode remains available. Horizontal/vertical offsets account for resolution, scaling and rotation. When automatic modes have no detected resolution, choose explicit modes or automatic/manual placement. Generated settings live in `~/.config/niri/monitors.kdl`; the selected plan is saved privately in `~/.local/state/rebos-desktop/installation.json`. Both participate in user-file backup/restore.

## Choices

```bash
bash install.sh --profile core    # core desktop, Firefox and Neovim; no extra apps/AUR
bash install.sh --groups notes,media --no-aur
bash install.sh --graphics keep --no-login --keep-network
bash install.sh --monitors desktop/examples/monitors.json --dry-run
bash install.sh --no-aur          # full official apps, skip optional AUR builds
bash install.sh --no-login        # keep your current display manager
bash install.sh --keep-network    # keep your current network service configuration
bash install.sh --files-only      # user settings only; dependencies must already exist
bash install.sh --yes             # accept the plan; retain AUR package review
```

The old `bash install/install.sh` entry point forwards to the same installer. `bash restore.sh` and `bash install/upgrade.sh` use the current snapshot in files-only mode (both accept `--dry-run`). They no longer link the October 10 legacy configuration into your home. `install/install-themed-apps.sh` forwards to the current post-login integration helper.

## After installation

To fetch and apply the newest commit from the GitHub repository's default branch:

```bash
./update.sh --dry-run
./update.sh
```

The updater uses a temporary checkout, leaving your repository and local edits
alone. It upgrades installed official packages with `pacman -Syu` and installed
AUR packages through Paru/Yay when available, with their normal review prompts.
Use `--no-aur` to skip AUR upgrades or `--files-only` to skip all package changes.
It does not reinstall packages from the full profile or change service selections.

Existing application configurations, shell preferences (including weather and
theme), monitor layouts, palette caches, wallpapers, and assistant configuration
are retained. Existing configuration folders keep their entire contents; new
configuration units are installed only where absent. Quickshell application
source, launchers and bundled app code are refreshed. Settings outside the payload,
including accounts, histories and the saved installation plan, are untouched.
Custom edits to application source are backed up but replaced. Close desktop
settings during an update, then log out and back in afterward.

New installations use H/J/K/L for left/down/up/right. Super selects a window,
Super+Shift repositions it on the screen, Super+Ctrl focuses a monitor, and
Super+Shift+Ctrl sends the window to another monitor. Personal shortcuts are saved
separately and retained across reinstalls and updates; see the
[shortcut defaults and personal files](desktop/README.md).

Each desktop update prints a backup path usable with the recovery command below.
If deployment is interrupted, use that backup's `journal.json` to restore with
`deploy.py --restore`. Package changes are separate and cannot be rolled back by
restoring user files. A dry run fetches and verifies the snapshot in temporary
storage without changing installed files or packages. `--repository` and
`--branch` can select a trusted fork or branch.

Reboot, choose **Niri** in Ly and log in. **Super+Return** opens Kitty; **Super+Space** opens the launcher; **Super+Shift+W** opens wallpapers. Set weather location in shell settings (Fahrenheit is the default).

Launch Zen once to create its profile. Open Spotify Launcher, sign in and close it, then run:

```bash
bash desktop/scripts/finish-apps.sh
```

Neovim plugins/language tools install through Neovim; see `:IDEHelp`. The assistant needs a separately configured agent. NVIDIA branch selection must match your hardware; driver builds and physical graphics behavior still require target-machine testing. Accounts, histories, credentials, browser profiles, machine-specific hardware fixes and game libraries are excluded.

## Updater

For an existing **rebos_shell Git checkout**, use the shell's separate
[updater](https://github.com/Rebo-NS4U/rebos_shell#updater) to get new shell
content while keeping saved preferences:

```bash
cd /path/to/rebos_shell
./update.sh --check   # Preview the changes first
./update.sh           # Apply the update
```

Run as your normal user with Git and Python 3 installed. The updater follows the
shell repository's default branch, replaces only changed source files, removes
obsolete tracked files and backs up affected existing files before changing them.
It prints the backup location, normally
`~/.local/state/rebos_shell/backups/update-*`. Saved preferences, personal data,
wallpaper choices and Niri settings remain in place. Packages and desktop services
are not changed.

**The desktop installed by this repository is a bundled snapshot without Git
metadata.** The shell updater cannot update that snapshot, the entire desktop, or
the installer repository. Its `--path` option must point to a shell Git checkout,
not `rebos_enclosure` or its `desktop/payload/` folder. The files-only installer
reapplies bundled settings with backups while retaining personal shortcuts. Use
this repository’s `./update.sh` (described above) for preference-preserving
desktop snapshot updates.

## Backups and recovery

User backups: `~/.local/state/rebos-desktop/backups/`. Use the exact timestamp printed during installation:

```bash
python3 desktop/scripts/deploy.py --restore "$HOME/.local/state/rebos-desktop/backups/TIMESTAMP"
```

Restoration replaces installed entries and reinstates their original files/links; it does not undo package/service changes. Linked parent configuration folders are copied locally with source contents preserved, and original links are restored on rollback. System Ly backups and the prior unit enablement listing are under `/var/backups/rebos-desktop/`. See [recovery details](desktop/README.md#backups-and-recovery).

## Check the installer

```bash
python3 desktop/scripts/deploy.py --verify
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s desktop/tests -v
bash install.sh --dry-run
```

[Validation record](desktop/VALIDATION.md): installation/restoration has been exercised in an isolated home and Niri/Fish checks passed. Fresh-machine boot, hardware, GUI behavior, real package changes and AUR builds still need testing on a spare machine or VM.

## Repository layout and credits

`install.sh` is the supported entry point. `desktop/` contains its implementation, portable payload, editable package lists, tests and detailed guide. `oneline.sh` is an optional authenticated clone/update helper. The root `packages-explicit.txt` is a reviewed reference inventory of core and optional packages, with hardware packages selected separately. The older root `.config/`, `.local/`, `assets/`, `install/pkg*.txt`, and archived scripts in `docs/legacy/` remain for historical reference; the new installer uses `desktop/payload/` exclusively.

Based on [jR4dh3y's dots-niri](https://github.com/jR4dh3y/dots-niri), with rebos_shell derived from Ambxst by Axenide and subsequent contributors. Current rebos_shell retains its AGPL-3.0 license in [desktop/payload/home/.config/quickshell/LICENSE](desktop/payload/home/.config/quickshell/LICENSE). cbonsai and bundled components retain their licenses. MAKC wallpaper source metadata is bundled; original collection: <https://github.com/makccr/wallpapers>. `UPSTREAM.md` retains upstream setup documentation with the current shell names.
