# Design-warning cleanup and quality gate

The original Pylint design scan reported 136 findings. Structural refactoring reduced the raw count to **72**, a net reduction of **64**. All duplicate-code findings were removed. The remaining 72 observations are **explicit exceptions**, not a claim that their underlying counts have disappeared. They cover 56 named functions/classes and are recorded with reasons and numeric bounds in `desktop/quality-exceptions.json`.

## Refactoring performed

- Media requests, GitHub project actions and development commands now have separate operation handlers instead of large dispatch bodies.
- Shell and assistant share one bridge implementation with an explicit parking capability. The shell still does not advertise or accept parking. Process lifetime and pending-event behavior are preserved.
- Playback identity is an immutable PlaybackContext passed across launches and completion callbacks. Caption options, checkout snapshots, catalogue options and keybinding changes have named records.
- VLC command handling separates per-command logic, input options and subtitle preparation. Polling separates end detection, loading, subtitles, property publication and caption rendering. mpv monitoring separates connection setup and event dispatch.
- Media reconnection now has explicit connection, input, socket-read and disconnect operations. It still discards commands during an outage and handles socket EOF before subsequent input.
- Deployment now builds an InstallPlan, previews it without writes, and applies it with a DeploymentWriter. Journal entries precede mutations; rollback on failure remains tested. Linked-update work separates merge restoration, untracked file migration and checksum reconciliation.
- Rate-limit helpers separate RPC exchange, quota filtering and process cleanup. Media discovery separates chunk fetching and candidate resolution; GitHub status separates remote comparison and status presentation.
- Frame-rendering and console-close helpers remove repeated execution/result handling.
- The installed YouTube details-prefetch behavior and native 500 ms buffer were recovered into tracked source during the refactor, so deployment preserves those existing improvements.

## What the exceptions mean

A required D-Bus/HTTP callback cannot change its signature to satisfy an argument count. A one-operation state helper needs no dummy public methods. Early rejection returns help keep invalid captions and unsafe process actions explicit. Typed records, UI widgets, caches and per-session fields need descriptive names. Some bounded parsers/platform compatibility sequences exceed generic branch/local/statement counts; splitting them further purely for a threshold would obscure the validation or transaction sequence.

These judgments are deliberately visible in source and in the registry. No module-wide disable or global threshold increase was introduced. The raw scan still sees every exception.

| Exception category | Instances |
| --- | ---: |
| too-few-public-methods | 4 |
| too-many-arguments | 2 |
| too-many-branches | 12 |
| too-many-instance-attributes | 10 |
| too-many-locals | 31 |
| too-many-positional-arguments | 2 |
| too-many-return-statements | 2 |
| too-many-statements | 9 |

## Enforcement

Run `tox -e quality`, or install `pylint==4.1.3` into an isolated environment and run:

```sh
python desktop/scripts/quality.py
```

The gate performs two scans:

1. Normal design/duplication checks, including useless-suppression checks. Any active diagnostic fails.
2. A scan of temporary source copies with local disable comments removed. Every finding must match a registered function/rule. Its numeric count cannot worsen; a new or obsolete exception fails.

Thus a local directive alone cannot hide a new warning or growing complexity. The pinned Pylint version keeps the rule semantics repeatable. CI and tox run this gate alongside existing Ruff runtime checks and behavioral tests. The source copies live only under a private temporary directory and never execute repository code.

The scope remains the original scanner's Python `.py` sources under desktop/scripts and system. This is not a security certification or a QML/Bash/native-code quality proof. Those languages retain their separate runtime/build/syntax checks.

## Completion checks

The full desktop suite passed 375 tests and the media suite passed 84 tests. Native builds, shell syntax, payload verification, installed-source comparisons, the design gate and Ruff passed. A final unused-alias cleanup was followed by focused request, typing, frame and protocol regression checks; Ruff now also enables F841 to reject unused locals.

The separately developed typing-book helper acquired five new design warnings during this pass. EPUB navigation/spine parsing and library action handling were separated, eliminating those findings without adding exceptions. Existing installed direct-stream verification, details prefetch, native buffering and bounded DNS-validation caching were preserved in source. The relay's existing DNS cache required one reviewed additional state field; only that exception's bound was adjusted from 12 to 13, with its 30-second/256-host limits covered by tests.

Forty-five task-related installed Python source files match the checkout. Existing services and playback were not restarted; loaded processes use their existing code until their next normal launch. Source recovery copies are retained under the user's private rebos-desktop task-backup directory.
