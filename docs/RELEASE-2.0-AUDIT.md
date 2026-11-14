# Enclosure 2.0 readiness audit — 2026-11-14

The baseline was clean checkout `1cb4f9e` at
`https://github.com/Rebo-NS4U/rebos_enclosure.git`, 23 commits ahead of the
remote main verified with `git ls-remote`. The latest remote tag was v1.8.0.
The audit inspected source, installer mappings, dependency declarations,
CI/tox/development checks, installed source links, services, journals,
crash records, package/database integrity, storage, memory and listeners.
It ran the available automated suites and isolated reproductions.
This is a bounded release review, not an assertion that every possible defect
or hardware failure has been found.

## Baseline evidence

| Check | Result before repairs |
| --- | --- |
| Desktop unittest discovery | 525 run: 522 passed, 1 failed, 2 skipped; 282.646 seconds |
| Media suite | 88 passed; includes VLC HLS decoding and 807 control requests over 20 seconds |
| Shell Python suite | 45 passed |
| Assistant environment suite | 3 passed |
| Standalone Node regression files | 2 passed, connectivity file failed |
| Ruff configured runtime rules | Passed |
| Expanded Pyflakes rules | 24 unused imports and 2 unnecessary f-string prefixes |
| Pylint 4.1.3 design gate | Failed: dither convert had 14 branches, limit 12 |
| Native greeter build/tests | Passed, with two deprecated GTK API warnings |
| Payload integrity | All 101 install entries verified |
| Tracked Python/Bash syntax | 191 Python files parsed; 29 Bash files passed |
| Relative Markdown file targets | No missing targets found; anchors/remote links not certified |
| Portable-source privacy patterns | No developer-home, private-key or scanned token-pattern matches |
| Linked deployment preview | Passed with explicit --link-source --preserve-preferences |
| Niri installed config | Valid |
| System/user failed units | None after approved live bus access |
| Pacman database consistency | Passed; every declared core package was installed |
| Selected desktop package file inventories | No missing files in Niri, Quickshell, Qt base, PipeWire, WirePlumber, greetd or Cage |

Media tests also run inside desktop discovery; these counts must not be added
as if all were unique tests. Pacman inventory checks verify presence, not all
file bytes or package authenticity. Privacy patterns are a focused scan,
not a complete secret detector.

## Confirmed findings and repairs

1. **Release test failure: stale island-bar expectation.** The bar deliberately
   changed brightness to microphone, but `test_merged_bar.py` still required
   `bar-brightness`. Expect `bar-mic` and exercise its expansion alongside
   sound/battery. Restoring brightness would reverse the intended UI change.
2. **Release design-gate failure.** Ordered RGB dithering pushed `convert`
   over the branch limit. Extract the ordered RGB transform; preserve output,
   cache keys and source images. Remove its obsolete statement waiver rather
   than increasing ceilings.
3. **Connectivity fixture failure.** The standalone JavaScript context omitted
   `wifiConnectTarget`, which exists in real QML. Initialize the fixture and
   retain its connection, ordering and password regression assertions.
4. **CI coverage gap.** CI and tox omitted separately located shell/assistant
   tests and standalone connectivity/Lua regressions. Include them explicitly
   so a green CI run covers the previously failing connectivity fixture.
5. **Playback-service backpressure hang.** An isolated Unix-socket reproduction
   showed `sendall` to a nonreading UI holding the shared server lock until
   the peer closed. Queue output through bounded per-client writers, with
   a two-second per-frame write deadline. Limit client count, outgoing queue
   size and incoming/outgoing frames. A slow UI must not block other clients
   or playback state updates. No running player was used in the reproduction.
6. **Unbounded relay metadata.** Registering 2,000 distinct sources retained
   2,000 source entries and 2,000 reverse routes. Cap retained routes and
   remove associated errors/preloads when retiring a route. Prevent late
   failed requests from recreating retired error entries. Random route tokens
   also replace predictable sequential paths. This is local service hardening;
   the audit did not establish a remote compromise.
7. **Missing real-time audio scheduling dependency.** `rtkit` was absent both
   locally and from core declarations. The boot journal repeatedly reported
   unavailable RealtimeKit and fallback scheduling values. Declare it in core;
   installing it locally requires the administrator approval helper. Existing
   audio processes must not be restarted merely to apply this change.
8. **Subtitle asset integrity gap.** Setup accepted any existing nonempty file
   and downloaded mutable model URLs without digest verification. Pin model
   revisions, verify source/model SHA-256 values, use unique temporary files
   and bounded socket waits, and replace cached files only after verification.
   Mismatch/network-failure tests must preserve the previous destination.
9. **Incomplete adapter provenance package.** `moviebox_source.py` referred
   to `vendor/moviebox-tui/SOURCE.md` and `LICENSE-MIT`; both were absent.
   Restore the upstream notice and record the exact revision used to obtain it.
   Do not invent the historical adaptation revision. Notice source:
   [MovieBox-Tui](https://github.com/mesamirh/MovieBox-Tui).
10. **Assistant crash-guard coverage gap.** The desktop panel used the
    hash-checked Qt 6.12.0 screen guard, while the assistant UI launched plain
    `qs`. Use the existing guard wrapper and optional build hook for the
    assistant as well; retain unmodified-Qt fallback on other versions.
    This closes a launch-path inconsistency, not a proof that every historical
    Quickshell crash is fixed.
11. **Native GTK deprecation warnings.** The greeter draw function queried a
    deprecated style context color and never used the result. Remove the unused
    query. Preserve the actual Cairo paint and verify the native build.
12. **Unused-source cleanup and prevention.** Remove the 26 expanded Pyflakes
    findings and enforce the full F rule family. Review import removal for
    intentional re-exports or side effects; validate behavior with the suites.
13. **Test resource warning.** Close the intentionally received HTTPError in
    the lyrics bridge origin test.
14. **Stale quality documentation.** The registry had 71 exceptions although
    the older quality document described 72. The dither extraction removes
    another waiver. Record the current 70 separately from historical results.

## System investigations and release acceptance still needed

These observations do not yet establish a defect with a safe automatic fix.

| Area | Evidence | Next acceptance step |
| --- | --- | --- |
| Quickshell crashes | Seven non-/tmp Quickshell command lines and eight test-harness crashes in seven-day records; several non-test traces include QPlatformScreen/Wayland screen selection | Reproduce output hotplug, scaling and suspend/resume with the guarded release; record crash-free duration and remaining stacks |
| Spotify | 65 crash records for its launcher-managed binary in seven days | Separate renderer/main-process failures; compare vanilla app, Spicetify and graphics acceleration independently; preserve account state |
| Cage | All four reviewed Cage records were test/probe command lines, including `cage -- /usr/bin/true` | Do not call these four login failures; test a real cold boot/login on a spare destination |
| Python | The recent inspected Python crash was a separate Locus render check | Track with its owning project; do not attribute it to Enclosure |
| Audio | ALSA ACP device creation and Mic ACP LED warnings; actual speaker/microphone are currently present | Exercise recording, playback, HDMI and Bluetooth; identify the affected card before changing profiles |
| Camera | Optional libcamera plugin warning; V4L2 camera sources are present | Verify camera and portal capture; add libcamera support only if the hardware/feature needs it |
| Power | Startup UPower owner warning, but UPower and power-profiles-daemon are running | Test battery changes, profile switching and suspend; avoid treating a startup race as a permanent outage |
| Keyring | Greeter-session warning followed by successful user login-keyring unlock | Verify account secret retrieval; do not reset credentials based on the warning |
| Portals | UI app-ID registration warning | Exercise file dialogs, screen sharing and screenshots; isolate the duplicate-registration caller |
| Night Light | One gamma property timeout | Exercise enable/disable and temperature changes; diagnose backend responsiveness before changing startup |
| Firmware | AMD-Vi ACPI UID and USB-C UCSI_GET_PDOS errors | Test actual USB-C/dock behavior; check vendor firmware support before choosing a remedy |
| Hot reload | Panel unit explicitly sets QS_DISABLE_FILE_WATCHER=1 | Reconcile intended reload policy with crash mitigation in a separate live test; no restart was used for this audit |
| UI memory | One sample: panel about 873 MiB, assistant UI about 631 MiB, media backend about 113 MiB | Measure idle baseline and growth across repeated open/close cycles; a single sample does not establish a leak |

The machine had about 794 GiB free on the main filesystem, about 26 GiB
available RAM of 30 GiB, no swap use, negligible pressure and kernel taint 0.
The only observed TCP listener was a loopback Python lyrics bridge on port
19837. That bridge checks the Spotify Origin and caps input size. This does
not establish an exhaustive security assessment of every installed application.

## Security scan triage

Bandit results are leads, not vulnerability counts. Most were subprocess calls
expected in desktop integration. Specifically:

- MovieBox's public protocol MD5/HMAC conventions are not user secrets and
  cannot be replaced arbitrarily without breaking the provider protocol.
- The reported book-deletion SQL table names come from a fixed internal tuple;
  the user-supplied book ID is parameterized. No SQL-injection proof resulted.
- `personal_bindings.py` executes a local packaged helper, not document text;
  replacing this requires an interface decision, not merely removing `exec`.
- XML/ZIP importers already have member/text bounds, but hostile-document
  expansion and converter resource limits deserve dedicated adversarial tests.
  No exploitable XML issue was demonstrated in this audit.
- Relay DNS checks and redirects reject private answers, but the connection's
  DNS resolution is not pinned to the validated address. A dedicated rebinding
  test and connection-level design review remain advisable; checking DNS twice
  would not by itself close that race.
- Runtime socket fallback to a predictable `/tmp` path deserves a separate
  ownership/symlink review. Normal runtime sockets are user-local and mode 0600.

## 2.0 release gates

Repair verification completed: 528 desktop tests ran with 526 passing and the
two explicit Wayland screenshot skips; all 91 media, 45 shell and 3 assistant
Python tests passed, as did all three standalone Node regression files and the
Lua checks. Ruff, the 70-exception design gate, warning-free greeter builds,
the native Qt screen-guard regression on this Wayland session, payload checks
and the linked-install preview passed. The exact staged payload/lint/design
checks also passed from an isolated Git-index export.

RealtimeKit 0.14-2 was installed through the administrator approval helper;
its D-Bus MaxRealtimePriority property returned 20. User unit definitions were
reloaded, and the assistant unit now selects the existing guard wrapper.
Panel, assistant UI and media service restart counters remained zero. Python
backend changes take effect on their next normal launch. Existing greeter
libraries and running audio/desktop processes were preserved; the greeter's
compile-warning cleanup applies when its helper is next rebuilt.

Subtitle model digests/revisions were checked against the primary
[Whisper model metadata](https://huggingface.co/api/models/ggerganov/whisper.cpp?blobs=true)
and [VAD metadata](https://huggingface.co/api/models/ggml-org/whisper-vad?blobs=true).
The [Whisper v1.9.5 archive](https://codeload.github.com/ggml-org/whisper.cpp/tar.gz/refs/tags/v1.9.5)
was downloaded and hashed during the repair. Tests exercise corruption,
cache reuse and interrupted downloads without fetching models.

1. Finish all local checks on the final source and verify the exact payload.
2. Test fresh core/full installs, update and recovery on a disposable Arch VM.
   Unit fixtures and temporary-home deployments do not establish package-manager,
   boot/login, AUR or real rollback behavior on destination hardware.
3. Run the two opt-in screenshot Wayland tests in a selected test session;
   they were explicitly skipped in the baseline. Do not disrupt active work.
4. Exercise lock/unlock, logout/login, suspend/resume, docking, fractional
   scaling, Wi-Fi reconnect, Bluetooth pairing, audio, microphone, camera,
   screen sharing and authenticated media/provider flows on supported hardware.
5. Record AMD/Intel/NVIDIA/VM support only for hardware actually exercised.
6. Review the 23 unpublished baseline commits plus these fixes, choose the
   intended 2.0 scope, and update release notes/screenshots/version metadata.
7. Produce a committed-source bundle with checksums and verify install/update
   from that exact bundle. No release, tag or push is implied by this audit.

Raw audit logs are local under `/tmp/enclosure-2-audit/`, mode 0700, and may
contain private machine/session information. Do not package them into a release.
Final repair verification is recorded in `desktop/VALIDATION.md`.


## Follow-up status — local candidate preparation

The baseline counts and findings above remain historical evidence. Subsequent
repairs fixed the relay lifetime, settings acknowledgement, chat interaction
identity and socket replacement bugs; see [the repair notes](FINAL-BUG-FIXES.md).
Connection-time numeric public-address checks now close the relay's independent
DNS-validation/connection race, retaining normal hostname TLS verification and
bypassing environment proxies for that transport. EPUB reads now share a
cumulative decompression budget; XML amplification/external-entity rejection
and failed-import preservation have dedicated tests. General converter resource
sandboxing is still not claimed.

The previously skipped screenshot acceptance cases now pass inside an isolated
software-rendered Niri/Xvfb session, and that runner is included in CI/tox.
Committed-source archive/checksum and temporary-home install/update/recovery
acceptance is repeatable, including the actual v1.8.0 source archive. Current
results are 540 desktop tests (the two ordinary-discovery skips pass separately),
108 media, 45 shell, three assistant and all Node/Lua/native/lint/design gates.
The [2.0 checklist](RELEASE-2.0-CHECKLIST.md) replaces the old suggested repair
order with current local checks and remaining destination acceptance work.

A later approved MemoryCurrent sample showed roughly 3.65 GiB for the active
assistant UI service. This service-level sample is not comparable to a controlled
idle/retained-heap benchmark and does not prove a leak. Memory/crash observation
remains open; the active UI/backend was preserved. No release, tag or push was
performed, and stable component version metadata was not relabeled as released.
