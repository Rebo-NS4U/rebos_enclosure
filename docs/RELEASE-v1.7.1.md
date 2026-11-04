# Rebos Enclosure v1.7.1

Repository tools now live in **Settings → GitHub**. The standalone graphical
Enclosure Development app and its Settings launch panel have been removed.

## Changes

- Select or add a local GitHub repository in Settings to review changed files,
  recent commits, branches, and commits waiting to push.
- **Check local repository** reports merge conflicts, staged and unstaged
  whitespace problems, changed-file counts, and free storage. It works offline,
  preserves staged and unstaged work, and does not run project tests or push.
- Pending commits are shown in their own expandable section, with a reminder
  that comparisons use the last fetched Git state. Fetch origin refreshes it.
- Check results appear near the repository controls, highlight issues, and clear
  when another repository is selected.
- Enclosure desktop updates remain specific to Enclosure. Terminal maintenance
  commands remain available through `./dev.sh` and `enclosure-dev`.
- Existing installations receive a hidden retirement entry for the old launcher,
  so the removed development app no longer appears in application menus.

## Update

Preview before applying:

```sh
./update.sh --release v1.7.1 --files-only --dry-run
./update.sh --release v1.7.1 --files-only
```

Omit `--files-only` to include package upgrades. Personal preferences are retained.
For installation instructions, see the [installation guide](../README.md).

## Verification

All 235 desktop tests passed, including repository checks against temporary
checkouts, preservation of staged changes, merge conflicts, detached and unborn
branches, and QML action routing and feedback. Payload verification passed for
all 87 installation entries. Installed changes match source; the installed
repository check passed and the retired launcher is verified hidden.

No active desktop services, playback sessions, or assistant backends were
restarted. These checks do not establish fresh-machine or authenticated-provider
coverage. The release includes a source bundle and SHA-256 checksum file.
