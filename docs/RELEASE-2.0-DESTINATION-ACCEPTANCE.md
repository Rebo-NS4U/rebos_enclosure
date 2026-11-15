# 2.0 destination acceptance record

Status: **not executed**. Complete this record on disposable Arch destinations
before tagging v2.0.0. Automated temporary-home deployments verify file behavior,
not package acquisition, boot, login or hardware support.

Record the tested source commit, candidate archive SHA-256, date, Arch image,
kernel, GPU/driver, display scaling and tester for each destination. Keep account
credentials, serial numbers and private logs out of committed evidence.

| Gate | Core installation | Full installation | Evidence |
| --- | --- | --- | --- |
| Clean package acquisition and declared dependencies | Not tested | Not tested | |
| AUR build and optional application setup | Not tested | Not tested | |
| Cold boot, greeter, login, lock and unlock | Not tested | Not tested | |
| Update from v1.8.0 and repeat update | Not tested | Not tested | |
| Preferences/accounts and source links preserved | Not tested | Not tested | |
| Failed update and backup recovery | Not tested | Not tested | |
| Logout/login and suspend/resume | Not tested | Not tested | |
| Display hotplug, docking and fractional scaling | Not tested | Not tested | |
| Wi-Fi reconnect and Bluetooth pairing | Not tested | Not tested | |
| Speaker, microphone, HDMI and camera | Not tested | Not tested | |
| File dialogs, screenshots and screen sharing | Not tested | Not tested | |
| Assistant authentication and long task recovery | Not tested | Not tested | |
| Authenticated media/providers and subtitles | Not tested | Not tested | |
| Music playback, lyrics and browser authorization | Not tested | Not tested | |
| Final visual review and approved screenshots | Not tested | Not tested | |
| Sustained memory/crash observation with duration | Not tested | Not tested | |

Use the [candidate checklist](RELEASE-2.0-CHECKLIST.md) for bundle commands.
Record failures with reproduction steps and resolve them before signing off.
Mark unavailable optional hardware explicitly; do not infer GPU-family support
from software rendering or another machine.

After acceptance: select the final commit, review unpublished commits and
licenses/artwork provenance, finalize release notes and Enclosure release
metadata, rerun gates, export and verify that exact committed bundle, and obtain
explicit publishing authorization. Component version strings need not match the
Enclosure release number. No tag, push or public release is implied by this record.
