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
bash install.sh --release v1.6.0 --interactive --dry-run
bash install.sh --release v1.6.0
```

The selector works through both installer entry points. A missing tag stops before
installation; a branch with the same name is never used in its place. `--release`
cannot be combined with `BRANCH` or `--local-snapshot`.
For intentional offline previews or testing local edits,
use `bash install.sh --local-snapshot --dry-run`; `--local-snapshot` deliberately
bypasses the freshness check. Help is available without network access.

The default **full** profile installs the desktop and applications, then offers normal AUR package review for Zen, Spicetify, VS Code and mpvpaper (video wallpapers). Review package build files as you would for any AUR installation. `--yes` accepts the desktop plan; it does not bypass AUR review. Internet and current Arch mirrors are required; this is a configuration snapshot, not an offline package mirror. Core and `--no-aur` installs support image wallpapers; video wallpapers require mpvpaper separately.

```bash
bash install.sh --profile core       # desktop and Neovim, without extra apps or AUR
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
- Locus Linux opens in a full-width tiled column, preserving Niri's border and outer gaps.
- Dark OLED theme with wallpaper-driven GTK, Qt, KDE, Kitty, Fish, Fuzzel, btop, Neovim and supported app palettes; a current palette snapshot is provided for the first login.
- Kitty/Fish prompt and shortcuts, procedural wallpaper-colored bonsai greeting that grows from a seedling into a unique Unicode tree with layered foliage and a ceramic pot, bundled terminal/shell fonts, GoogleDot cursor and Papirus icons.
- Custom Neovim IDE configuration and plugin lockfile. Plugins and language servers download separately through Neovim on first use; open `:IDEHelp` for instructions.
- Four 1920×1200 wallpapers in `New-1920x1200`: Aurora Lake, Bioluminescent Garden, Floating Islands and Neon Alley. Fresh installs select Aurora Lake; existing wallpaper preferences are preserved.
- Themed ReGreet login configuration, background, layout extension and GoogleDot cursor, NetworkManager, Bluetooth, PipeWire/WirePlumber, power profiles, authentication agent, portals, screenshots, OCR and clipboard history.
- Full-profile apps include Discord, Spotify Launcher, OBS, Obsidian, Zen, image viewer, developer tools, and the optional AUR apps listed above.

Anime Streamer captions can automatically detect each speech span's language and
produce English subtitles. English retains word timing; translations retain speech
timing. Settings → **Auto-detect language and translate to English** selects the
multilingual `ggml-base.bin` model; turning it off uses `ggml-base.en.bin` for English
only. Whisper binaries, Silero VAD and models are not bundled. Run
`python desktop/scripts/setup-subtitles.py` from the checkout to build Whisper
1.9.5 and download both base models and Silero VAD into
`~/.local/share/anime-streamer`. Setup requires CMake, a C++ compiler and ffmpeg;
it runs as the current user and does not restart playback or desktop services.
After setup, toggle captions off/on to retry an existing playback.
Short-clip checks found correct detection but mixed French/Italian
translation and poor German/Japanese/Korean translation with the base model;
do not treat detection success as evidence of translation accuracy.

Series playback queues continue across released seasons, keep specials separate,
and enforce the selected resolution limit. Next-episode preparation buffers a
bounded startup prefix 30 seconds before the next-episode prompt, which appears
at a named credits chapter or falls back to the final three minutes (the final
fifth for short clips). VLC receives chapter names for credits detection and
uses MP4 demuxing and network buffering options for network playback.

The package shortcuts share one menu for official/AUR installation, removal,
and updates. Fish `update --dry-run` previews the Arch/AUR, Flatpak and Rust
update commands. Administrator operations use `assistant-sudo`; package-manager
prompts are accepted automatically for installs and updates, including AUR review
menus. Removals still ask for confirmation. Signing-key trust failures refresh
`archlinux-keyring` and retry once; other failures stop that stage and remain
visible. Locks and file conflicts require manual resolution. Configuration Browser is also included
as a launcher entry for opening desktop configuration folders.

The assistant's GitHub workflow applies across projects and backends: edit in the
owning repository, keep applicable installed and installer files synchronized,
then commit tested task changes locally. Push only when explicitly requested or
initiated with the Push button in GitHub Settings. It preserves unrelated work and normal
approval boundaries. The policy is delivered once to each backend conversation,
including older restored chats, and persists across reconnects. Releases are
created when requested.

Password login through ReGreet starts and unlocks the login keyring using optional
GNOME Keyring PAM hooks in `/etc/pam.d/greetd`. The installer backs up the previous
PAM file. The keyring password must match the login password; automatic login
cannot supply a password to unlock it. Existing sessions need no restart.

Login packages are `greetd`, `greetd-regreet` and `cage`. The tracked greetd and
ReGreet configuration lives in `system/etc/greetd/`; the matching
layout, cursor extension and theme assets live in `system/etc/rebos-greeter/`.
The former `install/ly/` configuration and patches have been removed.

Base packages and optional application groups are editable in `desktop/packages/core.txt` and `desktop/packages/groups.json`. Driver packages are selected by the installer. A full system upgrade precedes package installation. The installer uses configured repositories and does not add Chaotic-AUR, replace the kernel, or copy this computer's GPU driver settings. Intel/AMD microcode and graphics userspace packages are detected from the destination. **NVIDIA:** the setup menu offers open DKMS and legacy 580 DKMS branches, matching kernel headers, hybrid offload and optional mkinitcpio early KMS. Choose the branch appropriate to the GPU; the installer does not guess NVIDIA generations or remove conflicting installed driver families automatically. Consult [Arch's NVIDIA guide](https://wiki.archlinux.org/title/NVIDIA). Existing network service enablement changes take effect on reboot so installation does not disconnect the active link. If using a custom network stack, use `--keep-network`.

The portable clipboard shortcut uses cliphist/Fuzzel. Spotify Launcher replaces the machine-local Cider shortcut. Hardware trays, Tailscale/WARP, Victus-specific fixes, Steam/game libraries, custom AI executables and paid apps are not automatically installed. The shell's assistant needs a separately installed/configured agent. Personal logins, browser profiles, messages, history, notes, weather location, AI credentials, SSH keys and local secret files are excluded. Weather defaults to Celsius with an empty location.

## First login

Fresh installs use the pinned classic island bar (80% opacity, 55% accent), a 12-hour clock, browser media integration, and the Transparent theme. Bar and theme defaults live in `config/shell/config/` and also seed the reset preset; updates preserve existing preferences.

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

Versioned defaults under `config/niri/` and `config/kitty/` are the source for future installs;
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
| Super+Alt+S | Sleep / suspend; press a key to resume when keyboard wake is supported |
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

The current updater fetches the latest default-branch update engine before it
applies any payload, even for `--release` or `--branch`. The selected release/branch
still determines the features installed. An older fetched source without the
handoff protocol uses the current local engine for compatibility. Unknown future
protocol versions fail safely and request a launcher refresh. The updater lock
remains held across handoff; temporary fetched source is removed on success or
failure. A failed fetch never runs a stale local installer.

For checkouts predating this handoff, run `git pull --ff-only` once before updating.
If local changes prevent that, preserve/reconcile them first. Old scripts already
on another machine cannot be upgraded until their launcher is refreshed.

Normal installations keep one active copy at the usual installed paths, with the
repository separate. Updates do not create a second active application tree or
switch copied installations into repository links. Recovery backups are inactive.
Existing optional development links remain supported and are not duplicated.

Updates replace managed scripts and user service definitions, including the
package menu and Fish `update` command. Personal Fish configuration, other
functions, desktop preferences and shortcuts stay in place. Configuration files
that match their previous shipped defaults receive upstream changes. Customized
files, symlinks and intentionally deleted known preferences stay personal; new
shipped files are added. Overlapping edits in a customized file require manual
merging and are reported. The first update uses an older defaults record or
available installed-revision Git history; unknown existing files are kept. The file backup
also restores the previous managed commands and service definitions.

Select a specific release with its exact tag from
[GitHub releases](https://github.com/Rebo-NS4U/rebos_enclosure/releases):

```bash
./update.sh --release v1.6.0 --dry-run
./update.sh --release v1.6.0
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

GitHub Actions runs payload verification, installer Bash syntax checks, the
desktop suite and the separate media suite on pushes and pull requests. The
runner uses an Arch Linux container with Python, Pillow, GTK, Quickshell, Niri,
Lua and VLC/FFmpeg dependencies. Tests run as an unprivileged user so installer
and updater checks exercise the normal user path. See
[the Blueprint review](../docs/BLUEPRINT-REVIEW.md) and the
[code quality review](../docs/CODE-QUALITY-REVIEW.md) for Radon/Pylint analysis.

For repeatable local runs, install tox in a development environment and use
`tox -e lint,quality,checks` from the repository root. The checks environment uses system
Python packages for GTK/Pillow and needs the same native tools as CI. The [design quality gate](../docs/QUALITY-GATE.md) also checks bounded, documented exceptions. The Ruff
rules check syntax, invalid control flow, undefined names and unbound locals;
they do not enforce a new formatting style.

```bash
python3 desktop/scripts/deploy.py --verify
ruff check --no-cache desktop system
bash desktop/scripts/build-check.sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s desktop/tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=system/apps/media python3 -m unittest discover -s desktop/tests/media -v
for script in install.sh desktop/install.sh oneline.sh desktop/scripts/finish-apps.sh \
              docs/restore-windows-vm-passthrough.sh docs/windows-vm-passthrough/*.sh; do
    bash -n "$script" || break
done
```

The native build check compiles both greeter extensions in a
temporary directory, then removes its output. It never installs or loads them.

Media settings requests validate a candidate settings object and save it before
updating the playback engine. Invalid values or failed saves leave the previous
settings in place. Regression tests cover rejected caption timing, save failures
and successful requests retaining their client/request identifiers.

`desktop/scripts/snapshot.py --verify` verifies reviewed `config/` and `system/` source. Use `--output /path/to/new.tar.gz` to export committed HEAD. Live-home snapshotting has been removed. Preserve component licenses; artwork rights remain with their authors. See the [filesystem guide](../docs/FILESYSTEM.md) for personal settings, managed defaults, grouping and recovery.

ReGreet follows the current desktop wallpaper and effective color palette through
`regreet-sync.path`, with a timer to retry failures and detect edits to the image.
Installation and `update.sh` enable the sync for an existing Enclosure greeter and
refresh its theme immediately; the next login displays the result. The first
update may request administrator approval to grant the desktop user ownership of
`/var/lib/rebos-greeter/theme` only. It does not restart greetd or the desktop.
The CSS template and sync units are managed code refreshed by updates; wallpaper
and color preferences remain preserved. Animated wallpapers use a still frame.
Setup disables the legacy `rebos-greeter-sync.path` watcher and stops its service
before enabling the replacement, so both exporters cannot compete.

ThinkPad Fan Control is available from the app launcher. It shows live fan mode and RPM, with Stop fans and Automatic controls; changes require administrator approval.

TV details open on the first regular season unless a saved season exists. Season 0 is labeled Specials; the catalogue cache badge checks S1 E1, not specials or every episode.

Player subtitles and live caption OSD use bundled OpenDyslexic (SIL OFL). The font is installed offline with the desktop; VLC applies it on the next new player session. Existing playback is preserved. Font source: https://github.com/antijingoist/opendyslexic (compiled OTF files and OFL.txt).

The playback menu reconnects automatically after service interruptions, clears its connection warning on readiness, and does not replay playback commands. Closing the menu transport never stops playback.

Both transparent media surfaces (the browser and next-episode overlay) are excluded from compositor blur, including while hidden, so they cannot blur the video or desktop underneath.

Playback settings include Subtitle font: OpenDyslexic, Noto Sans, Noto Serif or DejaVu Sans. The preference is saved and used by new VLC/mpv sessions; changing it does not restart active playback. Live caption recognition publishes each completed speech span and uses shorter chunks to reduce the wait for captions. Readiness reflects the current scene, rather than the presence of an older transcript.

Caption refreshes reuse their VLC channel without clearing between heartbeats, and use a long OSD lifetime refreshed before fading. Cue ends still clear immediately. Caption generation fills the nearest missing chunk in order, without jumping over dialogue to meet a moving lookahead target. No mouse or keyboard activity is required.

New Dweebo Codex chats default to **dweebo-Do** (Sol, medium reasoning). Saved chats retain their selected preset. Choose **dweebo-Deep** for complex coding and research with Sol at high reasoning.

### Free models in Dweebo

Choose **Free Code (OpenRouter)** or **Free Nemotron (OpenRouter)** in Dweebo's
agent picker. They use the existing Codex ACP backend, workspace permissions
and shared configuration with provider overrides scoped to that Dweebo agent.
Create an OpenRouter API key at https://openrouter.ai/keys and save it to
`~/.config/dweebo/openrouter-api-key` with mode `600`. Alternatively supply
`OPENROUTER_API_KEY` in the assistant backend service's environment.
Keys are private local state and must never be included in the installer.
No service restart is needed for source updates; choose the agent in a new chat.
The live model catalog listed Cohere North Mini Code and NVIDIA Nemotron Ultra
with zero token cost and tool support on 2026-11-02. Availability and rate limits
can change; no free DeepSeek endpoint was listed. Inference needs an API key.

Provider routing follows the [Codex provider configuration](https://learn.chatgpt.com/docs/config-file/config-advanced) and [OpenRouter Responses API](https://openrouter.ai/docs/api_reference/responses/overview).
The launcher preserves existing workspace/network and approval settings.

### Dweebo backends

The backend selector offers Codex, Distill, and Google Gemini. Each backend
manages its own authentication and usage limits.

### Google Gemini backend

Choose Backend → Google Gemini for the pinned native Gemini CLI ACP adapter.
It starts `gemini-3.5-flash-lite` with `--approval-mode default`, opens a dedicated chat,
and uses the normal permission prompts. Node.js and npm/npx are already part of
the assistant package requirements. The native CLI package is
`@google/gemini-cli@0.66.0` and is downloaded by npx on first launch.

Save the key in `~/.config/dweebo/google-api-key` with mode `600`. Alternatively,
the launcher accepts `GEMINI_API_KEY`, `GOOGLE_API_KEY`, or `GOOGLE_AI_API_KEY`
from its own environment. A variable in an existing fish terminal is not
necessarily inherited by a systemd user service. To copy an exported key safely
from that terminal, run the following command. It uses a recognized exported
variable, or asks for the key with input hidden if none is exported:

```fish
python3 ~/code/rebos-assistant/scripts/google_agent.py --save-key
```

No key is written to repository files or sent in the ACP handshake. Dweebo's
Gemini CLI login state is isolated under `~/.local/share/dweebo/google`.
Google API quotas and billing depend on the key's project; this integration
does not enable billing or change the project settings.

Dweebo's Google launcher makes one attempt per request and disables automatic
plan-model routing. Provider overload and quota errors should surface instead of
being hidden behind Gemini CLI's default ten-attempt retry loop. The lighter
default model avoids depending on the moving `flash` alias; other available
models can still be chosen through the model selector.

### Update validation and local fixes

`./update.sh --dry-run` fetches the selected snapshot, verifies its checksums,
checks Python and Bash syntax, and compiles the assistant sidebar and panel settings using an
isolated offscreen Quickshell process. It does not start agents or desktop
services. Normal updates run these checks before package upgrades and repeat
the code check after upgrading Qt, before replacing desktop files. Missing
backend support files or incompatible QML stop the update.

Deployments record hashes of the managed code they install. Later updates
stop if those files were edited or deleted locally, so a working local fix
cannot silently disappear. Commit and publish the fix first; use
`--allow-local-changes` only when intentionally replacing those edits with the
fetched snapshot. Earlier installations without recorded hashes acquire this
protection after their next deployment. Personal preferences and credentials
are excluded from these fingerprints.

A failed file copy automatically restores the deployment journal. Package
upgrades remain installed. The recovery backup is retained, and successful
updates still require logging out and back in to load desktop services.

### Updates from GitHub Settings

The default Enclosure project resolves its verified local checkout for branch,
commit and push controls, including when the installed shell is a separate copy.
Initial checkout selection waits for the catalogue and status requests to finish.
With no local checkout available, the page can still compare the installed
revision, but Git editing controls stay disabled. After updating these controls,
use **Check for updates** once to refresh an already-open GitHub page.

In Settings → GitHub, select Enclosure and use **Preview & update installed
desktop…**. The update window shows a dry run and requires typing `UPDATE` before
applying. Desktop files only is the default; select the package checkbox to also
upgrade system and AUR packages. Errors remain visible until the window is closed.
Locally edited managed files block updates rather than being silently replaced.
The official checkout must be at `~/rebos_enclosure` or `~/code/rebos_enclosure`
(or linked to the installed shell). Pull current branch updates only the checkout.
Personal preferences and the updater's recovery backups are retained. Log out
and back in after success.

### Settings navigation and shortcut search

Keyboard shortcuts has Search and Clear buttons beside its live filter. Enter
applies the search and Ctrl+F focuses it. Match counts show how many shortcuts
remain. The page scrolls when adding or editing shortcuts on smaller windows.
Appearance keeps its style form behind a Theme style card so section buttons
remain easy to reach. Shared Settings buttons, section cards and titlebar actions
support keyboard focus and expose names to accessibility tools. Hardware-dependent
and input-dependent actions retain their normal availability checks.

### GitHub connection and reinstalling

In Settings → GitHub, use **Connect / repair GitHub…** for the selected checkout.
The connection window verifies the signed-in account, configures Git to use the
GitHub CLI credential helper, and fills missing commit author fields in that
checkout using the account name and GitHub noreply address. Existing author
settings are preserved. Signing in alone does not configure a Git author.

Desktop installation, updates and recovery preserve `~/.config/gh/`, your login
keyring, Git settings and Codex configuration. These personal files are outside
the portable payload; a new machine or erased home still requires its own login.
Network failures leave credentials untouched and do not trigger reauthentication.
An assistant session restricted by its host can still be unable to reach GitHub;
repairing login does not change that session's network permissions.

`bonsai-grow` is the sole shipped bonsai renderer. The Fish greeting reserves space for the tree, then runs `bonsai-grow --background` (2 seconds by default) while the prompt accepts input. Submitting a command stops painting before command output starts. Each terminal gets a fresh specimen and one of 16 ceramic pots with intricate two-row panels of woven ribbons, latticework, scrolls, waves and medallions. Only the decorative inlays blend the wallpaper primary and secondary colors in linear light; the body, rim and foot stay dark and subtly tinted. Small terminals and `REDUCE_MOTION=1` show a still greeting.

Growth begins as a tiny single stem with two seed leaves; bark and girth develop later. Growing branches carry a leaf at their current tip until the final foliage opens, including when typing a command interrupts the greeting. Outer forks finish as shorter, finer twigs within the crown rather than long protruding spurs. Each tree has five to nine main limbs, combining its trunk habit with one of six crown forms: rounded, spreading, tiered, umbrella, open vase, or columnar. Unequal scaffold limbs divide into staggered, tapered secondary branches and fine twigs. Broadleaf crowns form irregular overlapping fans; junipers have lower, spreading foliage tiers. Smaller leaf clusters on finer twigs leave visible gaps beneath the crown, with fine dots at their edges. The trunk has solid exposed outlines with spaced bark shading, fine dots, and occasional knots inside. Leaf highlights are warm, shadows are cool, and stable patches add color variation using the current wallpaper palette. Existing branches remain visible through natural foliage gaps.

Use `bonsai-grow --animate --duration 10` for a slower foreground preview, or `bonsai-grow --preview 30 --seed 42` for a reproducible mature specimen. Saved growth for non-animation use lives privately under `${XDG_STATE_HOME:-~/.local/state}/bonsai-grow/` and is never shipped.

The older terminal-bonsai, cbonsai, and experimental rainforest renderers are retired. Installing this version archives their commands and assets in the desktop recovery backup instead of reinstalling them. The approved renderer and Fish greeting remain the only bonsai implementation.

Video startup avoids extra YouTube format probes and uses a 1.5-second network buffer for all VLC sources. Slow connections may buffer again during playback. These changes apply when the media backend next starts; active playback is preserved.

Single-video YouTube quick-play uses the existing feed card instead of fetching full details a second time. Playlist enumeration is preserved. Provider subtitle downloads and conversion run after video loading starts; late results are scoped to the current video and preserve explicit subtitle choices.

The shared stream relay forwards available network bytes immediately, including after a preloaded prefix, rather than waiting for a full 64 KB chunk. VLC pause-click capability detection is cached for the media backend lifetime to avoid an extra VLC process on repeat launches.

The book reader offers **Read aloud**, **Notes**, and **Settings** in a compact toolbar. Heart is the default speech voice, at natural pitch and a faster default pace of 105%. Reader settings has a speed slider (75–150%), chapter/time stopping limits, mode/fullscreen controls, and library/import actions. Settings opens on its own surface so it stays usable with a compact reader. Voice setup and repair share one button.

Download voices once from **Settings → Download voices**, or run `python3 ~/.config/quickshell/scripts/reader_speech.py --setup`. Setup installs `kokoro-onnx==0.4.7` and `onnx==1.20.1` into an isolated user environment and downloads about 354 MB of model/voice data with pinned SHA-256 verification. Runtime and assets stay in `$XDG_DATA_HOME/enclosure/reader-speech` (normally `~/.local/share/enclosure/reader-speech`), outside the payload. Playback thereafter is offline, uses `pw-play`, and does not save reading text or audio. See [Kokoro ONNX](https://github.com/thewh1teagle/kokoro-onnx).

Whole-page narration advances across pages and chapters, stopping at the book's end. Selected text plays once. Stop works between pages; manual navigation, speed changes, mode changes, and playback/load errors cancel narration. Closing or hiding Typer keeps active narration playing across pages. The media menu shows a Typer card with Open Typer, Pause/Resume, and Stop while a narration session is active; it disappears when playback ends or is stopped. Closing Typer without active narration leaves no media card. CLI speed can be set with `--speed 1.05`; `--wav /tmp/reader.wav` renders a sample without playback.

On wide fullscreen layouts, book notes form a floating right-side writing panel in the unused margin beside the reading column, with a taller editor and a 24 px outer inset. Word lookup uses the left margin. Escape closes either panel, preserving unsaved note drafts for reopening. Narrow fullscreen layouts retain a top-centered popup. Compact notes retain their position below the reader. They use the shared popup surface, theme-controlled outlines, rounded fields, and focus/hover surfaces. The editor and Save/Cancel controls remain accessible. Create a titled note from Notes, select a category, and save; search and category filters apply to saved notes. The context excerpt/action is removed; optional dictionary definitions remain in word lookup.

Reader settings offers Heart and Bella (female) plus Michael and Puck (male), all American English Kokoro voices; Heart is the default. Choose a voice and use **Preview** to compare the same sample at your chosen speed. Preview is bounded and never advances the book; voice changes stop current playback. These voices share the installed model and voice pack, so existing Kokoro installations need no additional downloads. All retain natural pitch, the speed slider, and continuous book reading.

During book narration, a tinted highlight follows each spoken word without changing text selection or page layout. Timing uses the Kokoro model’s phoneme durations mapped to the source words, including leading silence and pauses, and follows the playback buffer. The first narration creates a local timed copy of the pinned ONNX model (about 311 MB of additional disk space); existing installations can use Repair voice to install the ONNX dependency. Physical output latency depends on the selected audio device. Highlights reset on Stop, errors, page changes, and voice/speed changes. Selected-text narration highlights only its source range; Preview does not highlight the book.

Narration keeps connected sentences together so the model handles punctuation, abbreviations, and decimal numbers in context. Real paragraph boundaries receive a brief 120 ms pause, scaled by reading speed; there is no fixed silence after every sentence or at the end of a page. Synthesis uses chunks of at most 180 characters, with sentence boundaries preferred. Soft line wraps are sent to the voice as spaces. Before live playback, the reader prepares at least six seconds of audio (or the complete short selection, with a 12-chunk cap), then keeps a six-chunk lookahead queue. This prevents a brief heading from starting before the following paragraph is ready. Initial preparation may take several seconds on the CPU; narration then streams while later chunks are generated. Continuous reading also fetches and synthesizes the next measured page during current playback without moving the bookmark. A private runtime cache keeps at most three prepared pages with their word cues, matched by timing format, text, voice, speed, and paragraph boundaries. Old estimated-timing cache entries are not reused. Cached playback skips model loading and synthesis. Stop or manual navigation cancels background preparation; bounded selections and chapter/page stopping limits avoid preloading beyond their boundary. Very short pages or a resize can still require normal synthesis if the next page is not ready or its layout changed.

**Settings → Stop after** offers Until stopped, Current page, Next chapter, Chapter count (1–100, including the current chapter), and Time limit (1–240 minutes). Chapter limits stop before speaking the next chapter and leave it ready on screen. The timer starts with Read aloud, includes loading time, and stops playback at expiry; selected-text reading and voice previews stay bounded to their own text. Changing a limit stops the current session. The selected voice and current speed are preserved.

Reader settings stays open when changing voice, speed, stopping limits, reading/typing mode, or fullscreen size. Use Done or click outside to dismiss it; library/import navigation still closes the panel.

Reader preferences (reading/typing mode, fullscreen size, voice, speed, stopping limits, and notes category filter) are saved to the existing local book database, with a short debounce and an immediate save when closing. Reopening the typing menu restores the last book/page and typed progress, or the library if that was the last view. A fresh Quickshell instance loads preferences before opening the saved book. Playback, countdowns, highlights, and popups are not restarted automatically. No personal state is included in the installer payload.

The notes popup requests native keyboard focus for its title/search field and editor. Background reader refreshes do not steal focus while Notes or Settings is open. If an outside click dismisses a note with an unsaved draft, reopening Notes returns to that draft.

Reading requests buffer enough text for the full 36-line reading budget before fullscreen geometry settles (still capped at 4096 characters and chapter boundaries). Opening or expanding fullscreen therefore fills its first page without needing to turn a page first; the renderer fits that buffer to the available height.

In reading mode, **Space** starts narration or pauses/resumes the current audio without restarting its page. Page navigation remains on arrows, Page Up/Down, h/l, and Shift+Space for previous. **Ctrl+Space** looks up the active highlighted word, including the word being narrated. **Ctrl+H/L** moves the highlight left/right by word; **Ctrl+J/K** moves down/up by displayed line while preserving the horizontal column. These word movements stay within the current page. Narration continues to update the highlight while playing. While paused, moving the word highlight sets the point where narration resumes; it reads from that word through the remainder of the page, retaining continuous reading and the remaining timer. A pause with no word movement resumes the original audio in place. Explicit mouse selections remain available for lookup when there is no active narrated word. The main playback button mirrors Pause/Resume; Stop remains separate. Pausing freezes highlight timing and suspends the session countdown; resuming preserves the remaining time. Spaces in note/settings text fields are unaffected, and holding Space does not repeatedly toggle playback.

Typing **Backspace** deletes the preceding Unicode character without advancing the reading window. At an empty page it returns to the previous page; during a page handoff it removes queued input or applies the correction when the next window arrives.
