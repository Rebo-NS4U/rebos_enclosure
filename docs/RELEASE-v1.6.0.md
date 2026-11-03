# Rebos Enclosure v1.6.0

Personal settings and managed desktop source now have separate, documented
locations. This release includes the filesystem reorganization and completed
portable changes since v1.5.0.

## Changes

- `config/` holds shipped defaults; `system/` holds applications, commands,
  services and shared assets. Personal settings live under `~/.config/enclosure/`.
  Standard application paths remain available through links.
- Installation and updates group existing files with recovery journals, retain
  customized settings and intentional deletions, and refresh unchanged defaults.
  Development installs retain one linked source tree. Packaging exports reviewed
  Git source rather than collecting files from the live home directory.
- The updater uses the current update engine even when selecting an older payload.
  Isolated previews preserve compatible local commits and edits; conflicts stop
  before deployment. GitHub Settings exposes project status, history, connection
  repair and a separate installed-desktop update preview.
- Desktop, laptop and virtual-machine policies are independent of applications
  and GPU selection. The Enclosure Development menu provides checks, migration,
  deployment and explicit Git operations. Config Browser distinguishes personal
  settings, defaults and source.
- Four 1920×1200 wallpapers replace the older bundled collections: Aurora Lake,
  Bioluminescent Garden, Floating Islands and Neon Alley. Fresh installs use Aurora
  Lake. Existing wallpaper choices and already-installed collections are retained.
- Settings improves button access and shortcut search/replacement. Dweebo offers
  Codex, Distill and Google Gemini, with private local Gemini key setup and bounded
  retries. Restored custom chats default to dweebo-Light when no preset was saved.
- ReGreet uses GoogleDot cursors, a cursor size of 20 and 12-hour AM/PM clocks.

## Install or update

On an installed x86_64 Arch Linux system, review a preview before applying:

```sh
bash install.sh --release v1.6.0 --interactive --dry-run
bash install.sh --release v1.6.0
```

For an existing installation:

```sh
./update.sh --release v1.6.0 --files-only --dry-run
./update.sh --release v1.6.0 --files-only
```

Omit `--files-only` to include package upgrades. Log out and back in after updating
to load changed services. Very old updater launchers need the one-time checkout
refresh described in the [installation guide](../README.md#update).
See the [filesystem guide](FILESYSTEM.md) for paths and journal recovery.

## Verification and limits

- All 225 desktop regression tests passed, including nested media regressions,
  legacy-layout migration, linked updates, personal settings and recovery.
- Assistant/sidebar and settings-panel QML compiled in isolated offscreen
  Quickshell processes. Shipped Python/Bash syntax and native Lua caption/chapter
  checks passed.
- A full files-only install in a temporary home passed Niri validation, installed
  all four wallpapers and a valid default wallpaper path, preserved custom settings
  through an update, and restored both recovery journals successfully.
- All 872 payload hashes passed for 85 installation groups. Wallpaper JPEGs decode
  at 1920×1200. A focused source scan found no developer-home paths, private-key
  headers or common GitHub/OpenAI/OpenRouter token patterns; this is not an
  exhaustive secret audit.
- Local preference-preserving deployment passed; installed application links and
  wallpaper bytes match repository source. No desktop services, playback sessions
  or assistant backends were restarted.

These checks do not establish that every interactive feature works on every
machine. Live UI interaction, fresh boot/login, package/AUR installation,
Wi-Fi/Bluetooth, suspend/docking/GPU behavior, authenticated assistant inference,
provider streaming and optional Whisper translation require destination-system
or account-specific testing. No physical hardware matrix is claimed.
