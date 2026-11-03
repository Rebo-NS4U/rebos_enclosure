# Validation record

## Fresh-install media dependencies — 2026-11-03

- A fresh Arch installation rejected VLC’s `--freetype-font` option because
  `vlc-plugin-freetype` was absent. Installing it fixed native MP4 playback,
  seeking and resuming through the stream relay. Both installer profiles now
  include the plugin explicitly. Existing players were not restarted.
- All 226 desktop tests passed, including the nested media checks. Payload
  checksum verification and staged whitespace checks passed.
- The destination uses AMD Radeon 890M with amdgpu/Mesa; Vulkan, OpenGL and
  VA-API diagnostics passed after installing its missing Vulkan component.
- Traced the Qt portal-registration warning to Qt6ct’s `standard_dialogs=gtk3`.
  A minimal Quickshell process reproduced it with GTK and portal dialog themes;
  `standard_dialogs=default` registered successfully using the installed Qt6ct
  theme. Updated shipped defaults, installed defaults and the personal dialog
  preference, preserving all other theme settings and making a recovery backup.
  A windowless Qt portal settings request succeeded after the change. Existing
  desktop/assistant processes were preserved; new Qt processes use the fix.

## v1.6.0 release acceptance — 2026-11-03

- All 225 desktop tests passed, including nested media checks. Assistant and panel
  QML compiled offscreen; shipped Python/Bash syntax and native Lua caption/chapter
  checks passed.
- A full files-only temporary-home install passed Niri validation, installed four
  valid 1920×1200 wallpapers and the default path, retained personal edits during
  an update, and restored both install/update journals. Repeated grouping was a no-op.
- Payload verification passed for 872 files and 85 installation groups. Focused
  developer-home/private-key/common-token scans found no matches. Local deployment
  preserved personal preferences and source links; wallpaper bytes match source.
- See [v1.6.0 release notes](../docs/RELEASE-v1.6.0.md) for scope and limits. No live
  service restart, package installation, physical hardware matrix or authenticated
  provider round trip was performed. Live interactive features remain unverified.

## Separated source and personal configuration — 2026-11-02

- Removed obsolete root dotfile/font snapshots, duplicate wallpaper assets,
  retired installers, the redundant package inventory and copied default templates.
  All removed legacy wallpaper hashes were present in the retained collection.
  Source is now grouped under `config/` and `system/`; the manifest describes
  installation destinations and update policy explicitly.
- The clean staged source passes all 225 desktop tests, including legacy payloads,
  grouping/recovery, new-default merging, preserved personal edits, external and
  internal relative links, and old-to-new linked-source updates retaining local
  tracked edits and reviewed untracked files. Media regressions now run from the
  maintainer test tree rather than installed application source.
- A full files-only install in a temporary home passed Niri validation, created
  grouped config/system/defaults storage, preserved a personal edit through an
  update, and successfully restored both recovery journals. Real Lua caption
  boundary checks, Bash/Python syntax and checksum/whitespace checks passed.
- On the development desktop, 38 installed paths were grouped without restarting
  services. Before/after checks matched file contents, inodes and link targets;
  the second migration was a no-op and local deployment preview passed.
- Three ignored, local source aliases remain for already-running applications'
  former resolved paths. They contain no duplicate source and are excluded from
  exports. Unrelated working edits and untracked development files remain separate.
- No package installation, privileged service change, GitHub push or release was
  performed. System-owned destination paths such as `/etc/greetd/` remain standard
  OS paths; their versioned templates are centralized in `system/etc/`.

## Portable hardware policy and development menu — 2026-11-02

- Hardware discovery is independent of installer/deployment policy. Fixtures cover
  portable chassis/battery detection, VM/manual overrides, mixed Intel/NVIDIA,
  custom kernels and arbitrary connected display names. Generated desktop,
  laptop and VM policies validate with real Niri.
- The staged source passes all 213 desktop tests in an isolated home. Development
  tests cover explicit staging, destination checks, single-branch non-forced push,
  dirty-pull refusal, untracked-payload refusal and exact staged-source commits.
- Installer previews for all three explicit machine profiles leave temporary homes
  empty. A real files-only VM-profile install in a temporary home includes the
  launcher and saved machine policy, validates with Niri and restores its backup.
- The interactive development menu renders and quits through a PTY. The desktop
  entry validates, the modified QML passes qmllint, and Bash syntax/whitespace and
  exported payload checksums pass. New live launcher files point to checked-in
  sources; the GitHub Settings panel already uses the linked checkout.
- No package installation, real GitHub push, active service restart or physical
  boot/suspend/docking/GPU matrix was performed. Destination hardware remains
  subject to the development guide's acceptance checklist.

## v1.4.0 — multilingual captions and assistant GitHub workflow — 2026-11-01

- All 66 desktop tests passed, including real QML checks for new and older restored
  conversations, persisted GitHub-policy delivery, failed-send retries, bridge
  restoration and Codex/Distill backend coverage.
- Four packaged subtitle regressions cover auto-detection between speech spans,
  mixed English/translated timing, worker replacement without player restart and
  missing-model reporting. Earlier live checks in this chat passed 15 caption
  tests and real English/Spanish mixed speech with leading silence.
- Two public recordings each in French, German, Japanese, Korean and Italian
  produced correct detection and valid intervals on all ten samples. Translation
  reviews found mixed French/Italian and poor German/Japanese/Korean results.
  Processing took 0.96–1.90 seconds per 3.86–6.53-second recording. This is a small
  manual sample review, not a representative accuracy benchmark.
- Payload checksums, QML lint, Bash syntax, whitespace checks and the files-only
  installer dry run passed. Installed assistant source matches the payload.
- No live desktop installation, package upgrade, downloaded model packaging or
  assistant backend restart was performed for this release.

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

- Bundles rebos_shell 1.1.6, the current portable desktop palette/Niri configuration, 149 prepared wallpapers and the separate assistant/media runtime sources, launchers and user services.
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

## Release selection — v1.3.0

- All 61 desktop installer/update tests passed, including real local Git fetches of annotated and lightweight release tags, same-name branch isolation, missing-tag refusal, argument forwarding, repeated updates and preference preservation.
- Installer and updater help expose `--release TAG`. Bash syntax checks, whitespace checks and the complete payload checksum inventory passed (108 installation entries).
- Release selection was exercised without package upgrades or changes to the active desktop. Live package upgrades, hardware and boot/login remain outside these checks.

## Fan-control removal — v1.3.1

- Removed the fan-control window, helper, launcher, desktop entry and window rules from source and payload. Snapshot filtering prevents the retired files from being copied from a source desktop again.
- All 61 desktop installer/update tests passed. Payload verification passed for 106 installation entries; shell syntax, whitespace and retired-file inventory checks passed.
- Existing desktop files and running applications were not changed. This release does not remove old launchers from existing installations or alter cooling settings.

## v1.5.0 — 2026-11-02

All 91 desktop tests passed; the four OpenRouter checks passed again after the final network-default adjustment. Payload verification passed for 113 installation entries. See [release notes](../docs/RELEASE-v1.5.0.md) for the system comparison, preserved local state and live-inference/UI/hardware verification limits.
