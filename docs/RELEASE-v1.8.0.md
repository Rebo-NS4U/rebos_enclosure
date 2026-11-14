# Rebos Enclosure v1.8.0

This release brings the desktop, reader and media improvements made since v1.7.1.

## Changes

- Selectable Frosted Glass styling, shared corner radii, themed menus and a compact
  island bar; wallpaper palettes support manual accent selection and zoomable previews.
- A themed screenshot editor and frozen-screen OCR selection with editable text,
  copy and web search. The launcher adds web search, calculations, URLs and local files.
- Synced lyrics with playback timing, animated scrolling and desktop pins. An optional
  Spicetify Lyrics Plus adapter forwards lyrics through a local bridge; setup remains
  opt-in. See [Lyrics setup](LYRICS.md) for provider and activation requirements.
- Reader narration gains phoneme-aligned word highlighting, buffered audio and voice
  choices. Book import supports MOBI through Calibre; chapter completion persists.
- Faster video startup, connected YouTube feeds and queues, improved subtitle
  selection and switching, and VLC playback/control fixes.
- Procedural terminal bonsai with varied connected crowns, staged growth, blossoms
  and wallpaper-driven foliage and ceramic colors.
- Assistant session recovery, execution profiles and provider quota/status improvements;
  corrected battery indicators and additional installer, update and CI checks.
- Release cleanup extracts focused helpers for OCR, screenshot drawing, speech timing
  and palette validation, and groups optional book-save fields without changing the
  external book request format.

## Install or update

```sh
bash install.sh --release v1.8.0 --interactive --dry-run
bash install.sh --release v1.8.0

./update.sh --release v1.8.0 --files-only --dry-run
./update.sh --release v1.8.0 --files-only
```

Omit `--files-only` to include package upgrades. Personal preferences are preserved.
The release includes the committed source bundle and a SHA-256 checksum file.

## Verification

- The full desktop run executed 518 tests with two environment-dependent skips.
  Its remaining OCR validation-order error was corrected; all five OCR tests
  passed on a focused rerun. Lyrics and wallpaper regression tests passed.
- All 88 standalone media tests passed, including sustained VLC control/playback.
- Python runtime lint and the design gate passed; all 71 documented design
  exceptions stayed within their ceilings.
- Installer shell syntax and both native helper builds passed (GTK deprecation
  warnings remain). Payload checksums passed for all 101 installation entries,
  including an export of the staged source. All 11 task-related installed source
  files match the checkout.

No active desktop services or playback sessions were restarted. Fresh-machine,
authenticated-provider and hardware matrix coverage are not implied by local tests.
