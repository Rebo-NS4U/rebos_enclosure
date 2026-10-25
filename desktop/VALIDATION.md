# Validation record

2026-10-24 local time, on the source Arch desktop:

- Seven deployment tests passed: checksum failure before writes, unexpected payload files, traversal refusal, parent symlink refusal, read-only dry runs, repeat installs/restores, and preserving original symlink targets/unrelated files.
- Follow-up fix: all nine tests passed after adding linked `.config` parent handling, including preserving source contents, unrelated files, relative link restoration and refusing broken links. The actual `bash install.sh --dry-run` now passes against the source desktop's linked `environment.d` and `scripts` folders, with no desktop changes. Expected deployment errors now print a concise message instead of a Python traceback.
- Repository integration: all twelve tests passed, including real local-Git clone/fast-forward bootstrap behavior, argument forwarding and preservation of dirty/non-repository destinations. All 928 payload files (including checksums) are present in the Git index. A clean export from the staged Git tree passed previews through the root, former installer, restore and upgrade entry points, followed by an actual files-only install/build, Niri validation, Fish startup and restoration under a temporary username. Linked `environment.d` and `scripts` source contents remained unchanged. Shell syntax checks passed for supported entry points. No source-home installation was run.
- A real `--files-only --yes` install passed in a temporary home under a different username, followed by restoring its backup.
- cbonsai compiled from the bundled source against ncurses and panelw.
- Installed Niri configuration validated with Niri 26.04; all installed Fish files and generated Bash wrappers passed syntax checks, and Fish startup found the greeting and compiled binary.
- Confirmed destination PATH and Qt palette paths use the new home. Confirmed all 307 prepared wallpapers were present.
- All core/apps package names were found in the configured Arch official repository databases. mpvpaper was only present in the source machine's third-party repository and was moved to the optional AUR list.
- Payload checksums passed for 927 selected files. No payload symlinks, hardcoded `/home/rebo` strings, or matches for the scanned private-key and common API credential patterns were found. The snapshot uses an explicit selection list, with no account/history/AI configuration copied.

Not exercised: real pacman installation or upgrade, AUR downloads/builds, system service changes, boot/login, live shell UI, lock/unlock, screen sharing, Spotify patching and target GPU behavior. Those need a fresh Arch VM or spare computer. No active desktop config, installed package or system service on the source computer was changed by these checks.
