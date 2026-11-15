# Rebos Enclosure 2.0.0

Enclosure 2.0 brings a unified themed desktop, local Music, expanded reading and
narration, persistent Dweebo sessions, and simpler desktop updates.

## What's new

- **Twelve material themes:** Canopy, Orbital, Metropolis, Glass Vault, Radar
  Station, Suspended Film, Monolith, Blueprint, Terminal Hardware, Frosted Glass,
  Tinted and Clear Glass. Palettes, corners, fonts and Kitty styling follow the
  selected appearance. Font previews and custom font names are supported.
- **Settings and wallpapers:** category navigation, top tabs, searchable settings,
  exclusive vertical accordions and larger choosers. Wallpaper/color presets,
  artist sorting and dominant-color classification accompany the Seventeenth,
  Cycle Circle and shared-album collections. Artist/source credits are retained.
- **Desktop controls:** microphone control in the unified bar, guarded input
  toggles, clearer power/brightness/audio controls, process trees, and improved
  OCR, screenshots and annotation. The greeter uses OLED black surfaces.
- **Music:** local library, folder playlists, favorites, shuffle/repeat, bounded
  queues, spotDL downloads, cached LRCLIB lyrics, current/next bar lyrics,
  estimated-line alignment and an output-monitor spectrum visualizer.
- **Books and typing:** continuous/fullscreen typing, saved reading progress,
  categorized notes, word lookup and optional offline Kokoro narration with four
  voices, speed controls, selected-text reading and spoken-word highlighting.
- **Dweebo:** independent persistent sessions, continuity through long silent
  tasks and UI reloads, compact conversation controls and collapsible completed
  tool details. Hidden views unload while active work is preserved.
- **Video:** themed Anime/Movie/TV/YouTube browsing, automatic catalogue fill,
  early-opening VLC playback, stream recovery, continuing episodes/playlists,
  browser-connected YouTube recommendations and explicit subtitle selection.
  Provider captions are checked before use; optional local Whisper/Silero assets
  use pinned revisions, verified digests and atomic replacement.
- **Two update buttons:** GitHub Settings can apply current main-branch desktop
  files. A highlighted top-bar alert appears only for a newer stable release and
  applies that exact tag. Both show terminal progress and retain preference,
  backup and local-change protections. Package upgrades remain a terminal option.
- **Reliability:** bounded playback queues and relay routes, public-address
  enforcement at connection time with hostname TLS checks, safer runtime socket
  handling, cumulative EPUB decompression limits, and state reconciliation after
  rejected saves/disconnects. Shared-command aliases now recover correctly.
- **Installer validation:** frozen updater handoff, payload checksums, isolated
  QML preflight including the release alert, expanded CI checks, deterministic
  source exports and temporary-home install/update/recovery acceptance.

## Install or update

Run as your normal user on an existing x86_64 Arch installation. This installs a
desktop; it does not partition disks or install a bootloader.

```sh
bash install.sh --release v2.0.0 --interactive --dry-run
bash install.sh --release v2.0.0
```

From an existing checkout, preview and apply the release's desktop files:

```sh
./update.sh --release v2.0.0 --files-only --dry-run
./update.sh --release v2.0.0 --files-only
```

The graphical release button applies immediately with progress. The regular
Settings button follows main rather than pinning this release. Keep local fixes
committed before updating. Log out and back in when ready after a successful
update. File recovery uses the deployment journal; it does not downgrade
packages, undo system-service changes or reverse Git history.

Optional caption/narration models and account credentials are not bundled.
See the [installation guide](../desktop/README.md), [README credits](../README.md#credits)
and [source-link/recovery guide](../desktop/SOURCE-LINKS.md).

## Verification and known limits

Payload, lint/design, native builds, automated desktop/media/assistant checks,
software-rendered Wayland screenshots and temporary-home file deployment/update/
recovery are covered by the [validation record](../desktop/VALIDATION.md).
These results do not certify clean Arch package/AUR acquisition, boot/login,
every GPU, suspend/docking, lock/unlock, screen sharing or authenticated provider
flows. Destination hardware acceptance and sustained memory/crash observation
remain open in the [acceptance record](RELEASE-2.0-DESTINATION-ACCEPTANCE.md).

The Qt screen guard is a mitigation, not a blanket crash fix. Subtitle checks
cannot certify translation accuracy. Relay route capacity remains bounded;
indefinitely growing live streams need a separate retirement design. General
PDF/Calibre process sandboxing is not claimed. Existing crash/audio/portal and
hardware investigations remain documented in the [audit](RELEASE-2.0-AUDIT.md).
