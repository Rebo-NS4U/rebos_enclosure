# 2.0 preparation and acceptance

The v2.0.0 release is selected from the reviewed committed source. Component
versions are independent of the Enclosure release number. Historical candidate
results below remain as preparation evidence; destination acceptance gaps remain
explicitly open. See the [2.0 release notes](RELEASE-v2.0.0.md).

## Repeatable local gates

- `python desktop/scripts/deploy.py --verify`
- `ruff check --no-cache desktop system`
- `python desktop/scripts/quality.py` with the pinned Pylint from tox/CI.
- `python -m unittest discover -s desktop/tests -v`
- `PYTHONPATH=system/apps/media python -m unittest discover -s desktop/tests/media -v`
- Shell and assistant Python, standalone Node and Lua regressions as listed in
  `tox.ini`, plus `bash desktop/scripts/build-check.sh`.
- `python desktop/scripts/check_wayland.py` selects both opt-in screenshot UI
  tests in a private software-rendered Niri/Xvfb session. It is now part of CI
  and tox and does not use the active desktop.
- Check installed source links and run the linked deployment preview with
  `--link-source --preserve-preferences --dry-run`.

Local run: 540 desktop tests passed with the two default opt-in skips; both
Wayland cases passed separately in the nine-test isolated runner. All 108 media,
45 shell, three assistant, Node/Lua/native/lint/design checks passed. The exported
candidate passed fresh and v1.8.0 update/recovery file acceptance. Completed run
details are in [the validation record](../desktop/VALIDATION.md).
New regressions cover connection-time public DNS enforcement, TLS identity,
compressed-document work limits, entity-expansion rejection and deterministic
committed-source exports. Failed imports preserve existing book state.

## Latest candidate refresh — 2026-11-15

The full desktop run passed 598 tests with the usual two separately exercised
Wayland skips. All 117 media, 45 shell, three assistant and Node/Lua/native,
lint and design checks passed. Subsequent shared-command recovery repair
passed 13 storage, 31 deployment and four release tests and the design gate.
The exact committed `8d97e04` r2 archive passed fresh/repeat files, v1.8.0
update, preference preservation and recovery. See the updated
[validation record](../desktop/VALIDATION.md) for its digest and limits.
Later uncommitted settings edits are excluded and need their own validation.

## Build and verify the actual bundle

From the tested, committed checkout, choose a new output path:

```sh
python desktop/scripts/snapshot.py --output /path/to/enclosure-2.0-candidate.tar.gz
python desktop/scripts/check_release.py /path/to/enclosure-2.0-candidate.tar.gz \
  --previous /path/to/v1.8.0.tar.gz --report /path/to/acceptance.json
```

Each archive requires its adjacent `<archive>.sha256` file. `snapshot.py` exports
one resolved commit, excludes uncommitted files, refuses existing archives and
checksums, and writes the exact archive digest. The previous archive can be
exported from the existing v1.8.0 tag with `git archive` and a checksum sidecar.
The acceptance command verifies both payloads and exercises fresh file install,
repeat update, preference/account preservation, cross-release file update and
journal recovery inside temporary homes with spaces in their names. It does not
run package installation or system service changes. Use only trusted source
bundles: deployment intentionally executes the packaged installer.

## Destination acceptance still required

Use the [destination acceptance record](RELEASE-2.0-DESTINATION-ACCEPTANCE.md)
to capture actual hardware and installation results. Unexecuted rows remain open.

- Fresh core and full Arch installs, real package/AUR acquisition, boot/login
  and recovery on a disposable VM or spare machine. This execution environment
  has no exposed `/dev/kvm` or QEMU/virsh tooling; temporary-home file checks
  do not substitute for this gate.
- Lock/unlock, logout/login, suspend/resume, USB-C docks, display hotplug and
  fractional scaling on the supported hardware. Record actual GPU models and
  results before claiming AMD/Intel/NVIDIA/VM support.
- Wi-Fi reconnect, Bluetooth pairing, speakers/microphone/HDMI, camera, portals
  and screen sharing; authenticated YouTube/TorBox/media/provider flows using
  the user's normal accounts, without shipping credentials.
- Longer guarded-desktop/assistant and Spotify memory/crash observation. Existing
  audit warnings are investigations, not diagnoses or automatically safe fixes.
- Final visual/screenshots review, component/release metadata decision, review
  unpublished commits, and publish only the selected verified commit.

The initial [audit](RELEASE-2.0-AUDIT.md), [UI repairs](UI-POLISH.md) and
[final four bug repairs](FINAL-BUG-FIXES.md) record prior evidence and limits.
Do not claim release readiness solely from the local green checks.
