# Rebos Enclosure v1.6.1

This patch release preserves Enter-key activation for the playback next-episode
card in Quickshell.

## Changes

- Allow Enter or Return to activate the visible next-episode card. Keyboard focus
  is exclusive only while the card is offered and returns to none otherwise.

## Update

For an existing installation:

```sh
./update.sh --release v1.6.1 --files-only --dry-run
./update.sh --release v1.6.1 --files-only
```

Omit `--files-only` to also upgrade Arch and AUR packages. Review the preview
before applying the update.

## Verification

- The installed Quickshell QML was validated by the desktop update preview.
- The deployment payload checksum verification passed for 87 entries.
