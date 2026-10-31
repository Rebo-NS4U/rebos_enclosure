# Validation record

## Enclosure v1.0.0 launch — 2026-10-31

- Fresh installs seed bar, theme, performance, lockscreen and system settings from
  the bundled default preset. Weather location is empty and its unit is Celsius.
  Existing preferences remain in place during desktop updates.
- All 40 installer/updater tests passed. Payload verification checked all 95
  installation units and 992 files. Two consecutive files-only dry runs passed,
  with payload verification still passing afterward.
- The shortcut reader now loads source without creating Python cache files inside
  the checksummed payload. Bash syntax and whitespace checks passed.
- Real package upgrades, AUR builds, boot/login and target hardware still require
  validation on an installed Arch system.

## Preference-preserving updater — 2026-10-30

- All 30 installer/updater tests passed. The updater integration test fetches a local Git repository, previews without deploying, applies twice in a temporary home and retains personal settings.
- Deployment tests cover refreshed application source, retained configuration contents, relative and broken preference links, repeat backups and restoration after a simulated interrupted copy. Existing preferences remain in place; even an update with no changed units creates a recoverable journal.
- The bundled payload passed checksum verification for all 95 installation units. The update entry point passed Bash syntax checking and the working changes passed whitespace checking.
- No live desktop update, network fetch from GitHub, real package upgrade or AUR build was performed. Package-manager execution remains unverified here.

2026-10-24 local time, on the source Arch desktop:

- Seven deployment tests passed: checksum failure before writes, unexpected payload files, traversal refusal, parent symlink refusal, read-only dry runs, repeat installs/restores, and preserving original symlink targets/unrelated files.
- Follow-up fix: all nine tests passed after adding linked `.config` parent handling, including preserving source contents, unrelated files, relative link restoration and refusing broken links. The actual `bash install.sh --dry-run` now passes against the source desktop's linked `environment.d` and `scripts` folders, with no desktop changes. Expected deployment errors now print a concise message instead of a Python traceback.
- Repository integration: all twelve tests passed, including real local-Git clone/fast-forward bootstrap behavior, argument forwarding and preservation of dirty/non-repository destinations. All 928 payload files (including checksums) are present in the Git index. A clean export from the staged Git tree passed previews through the root, former installer, restore and upgrade entry points, followed by an actual files-only install/build, Niri validation, Fish startup and restoration under a temporary username. Linked `environment.d` and `scripts` source contents remained unchanged. Shell syntax checks passed for supported entry points. No source-home installation was run.
- Interactive setup addition: all 26 tests passed, covering application group filtering, service/microcode choices, NVIDIA branches and header requirements, driver conflicts, monitor validation, scale/rotation-aware positioning and real Niri KDL parsing. A real PTY walkthrough selected notes-only, Mesa, two monitors with scaling/rotation, startup focus and preserved login/network configuration; dry run left its temporary HOME empty. The no-argument entry opened the menu automatically and q cancelled without changes. An actual files-only install with customized monitors compiled cbonsai, passed Niri/Fish checks, saved its selected plan and restored successfully.
- A recorded-command integration test exercised the full NVIDIA open DKMS/early KMS/hybrid path and selected service exclusions. Actual user-file installation and restoration ran in a temporary home; sudo, pacman, systemctl, mkinitcpio and desktop-default commands were recording stubs. Assertions checked the requested driver/header packages, generated module/drop-in contents, initramfs rebuild command, service exclusions and offload launcher. This verifies installer wiring, not driver execution or hardware behavior.
- A real `--files-only --yes` install passed in a temporary home under a different username, followed by restoring its backup.
- cbonsai compiled from the bundled source against ncurses and panelw.
- Installed Niri configuration validated with Niri 26.04; all installed Fish files and generated Bash wrappers passed syntax checks, and Fish startup found the greeting and compiled binary.
- Confirmed destination PATH and Qt palette paths use the new home. Confirmed all 307 prepared wallpapers were present.
- All core/apps package names were found in the configured Arch official repository databases. mpvpaper was only present in the source machine's third-party repository and was moved to the optional AUR list.
- Payload checksums passed for 927 selected files. No payload symlinks, hardcoded `/home/rebo` strings, or matches for the scanned private-key and common API credential patterns were found. The snapshot uses an explicit selection list, with no account/history/AI configuration copied.

Not exercised: real pacman installation or upgrade, AUR downloads/builds, system service changes, boot/login, live shell UI, lock/unlock, screen sharing, Spotify patching and target GPU behavior. Those need a fresh Arch VM or spare computer. No active desktop config, installed package or system service on the source computer was changed by these checks.

## 1.1.6 snapshot refresh — 2026-10-30

- Bundles rebos_shell 1.1.6 from Rebo-NS4U/rebos_shell at b78ac15d, the current portable desktop palette/Niri configuration, 149 prepared wallpapers and the separate assistant/media runtime sources, launchers and user services.
- All 26 installer tests passed, including real temporary-home deployment, Niri validation, compilation, customized monitor setup and restoration. System/package actions in the installation-flow test use recording stubs.
- The installation-flow test also verifies the shell version, assistant/media files, resolver, expanded service paths and removal of new runtime files on restore.
- All 988 checksum entries passed. Selected packaged release files match the shell source after home-path normalization. Source-home/private-key/common credential-pattern scanning found no matches. A core dry run succeeded and left its temporary home empty. Added packages resolve in the local official package databases.
- Shell release checks: 31 backend tests and 10 isolated real-QML integration tests passed. Qt 6 lint found no syntax/fatal errors in 16 changed QML files; virtual qs import warnings remain.
- Fresh-machine package installation, AUR builds, boot/login, assistant authentication, provider-dependent playback, optional Whisper models and the optional VLC pause-click plugin were not exercised. Node/npm remain in the optional development group for the default assistant adapter. No live desktop reinstall or service restart was performed.

## Current local payload refresh — 2026-10-31

- Refreshed 39 bundled QuickShell and assistant source files from their local source trees and regenerated all 992 payload checksums. Generated Python cache files were excluded.
- All 40 installer/updater tests passed. The core installer dry run verified 992 payload files and planned deployment of 96 installation entries without changing the current desktop.
- GitHub remote verification and push could not run because this environment cannot resolve `github.com`.

## Panel stability and blur repair — 2026-10-31

- Panel discovery now uses the exact QuickShell configuration path, including home paths with spaces. The independent assistant cannot suppress panel startup. Shell IPC defaults explicitly select the panel configuration.
- Added an independent supervised panel service with QML file watching disabled. The media menu retains its surface and releases keyboard/input capture when closed. Niri loads the appearance blur override and explicitly prevents the transparent media surface from blurring the desktop.
- A Qt 6.12.0 guard builds from source on the destination when development tools/private headers are available. Other Qt versions skip it; library hashes prevent loading an obsolete build. The build replaces libraries atomically and is optional for service startup. No compiled library, source-machine hashes or personal settings are in the payload.
- All 43 installer tests passed, including another-home installation/restoration, personal shortcut preservation, independent panel/assistant detection, spaces in home paths, and skipping unsupported Qt versions. The payload checksum inventory and Bash syntax checks passed.
- Built the packaged guard into a temporary data directory, verified its library/source hashes, and ran its native Wayland regression test with stale, null, live and empty output lists. The user service passed systemd verification.
- Earlier live desktop verification passed menu open/close and launcher checks after repair, and a desktop screenshot confirmed the blur was cleared. Installer verification did not restart the current desktop or assistant. Fresh-machine boot, package downloads and other hardware/Qt versions remain untested.
