# Memory audit

## Bounded music artwork

Music library covers decode within 512 × 512 pixels and the dashboard player
background within 1024 × 1024 pixels, including its wallpaper fallback. This
avoids keeping full-resolution originals for these small surfaces. Fixed bounds
also avoid decoding again during layout animations. Existing asynchronous loading
and playback lifetimes are preserved. Savings depend on the source images; no
desktop-wide before/after reduction has been established for this change.

## 2026-11-14 measurements

The assistant was already running a newer process when this audit began. Its RSS
was 342.9 MiB, rather than the roughly 2 GiB observed in the earlier process.
That difference is not a controlled before/after result and cannot all be
attributed to the UI changes.

Three hide/show cycles measured the following live assistant process memory:

| Cycle | Hidden RSS | Visible RSS | Hidden PSS | Visible PSS |
| --- | ---: | ---: | ---: | ---: |
| 1 | 305.5 MiB | 339.0 MiB | 205.0 MiB | 236.8 MiB |
| 2 | 304.8 MiB | 338.5 MiB | 204.3 MiB | 236.2 MiB |
| 3 | 306.3 MiB | 336.3 MiB | 205.8 MiB | 234.1 MiB |

This short test showed no monotonic growth. It does not rule out longer-term
leaks. Active assistant work continued during the test.

The shell eagerly instantiated twelve island menus while collapsed. Those menus
now load when selected and unload after their closing fade. Typing, notifications,
the bar itself, and other persistent services retain their existing lifetimes.
Power-menu keyboard navigation forwards through the loaded menu.

An isolated offscreen comparison ran the expanded merged-bar regression scenario
against the committed eager-loading version and the new lazy-loading version.
Both passed. Peak child-process RSS (Linux `RUSAGE_CHILDREN.ru_maxrss`) fell from
233.3 MiB to 208.7 MiB, a reduction of 24.6 MiB. This is a single comparison with
software rendering and synthetic state, not a desktop-wide idle measurement.

Regression coverage opens all twelve menus, checks their geometry, and verifies
that each creates its controls on opening and destroys them after closing when
animations are disabled. Separate menu tests exercise keyboard back actions.

The live system used about 8.2 GiB at the time of the audit, with an active browser,
video playback, and an AI task. This is not an idle baseline. Process PSS totals
were about 4.5 GiB; kernel and graphics memory, shared memory, and reclaimable
caches require separate accounting. Summed RSS double-counts shared pages.

Allocation profiling with Valgrind Massif was attempted on the isolated Settings
regression scenario. It exceeded both the normal 25-second timeout and an
extended 180-second timeout, producing no usable allocation report. No allocation
call-stack attribution or leak diagnosis is claimed. Native regression tests
passed independently of this instrumented run.

## Remaining validation

- Measure after a normal fresh login with no browser, playback, or active AI work.
  Do not restart active services simply to obtain this baseline.
- Repeat browsing and hide/show cycles over a longer period, including long chats
  and attachments, and track PSS as well as RSS.
- The current chat view initially renders 40 messages and loads older messages in
  batches. Full viewport virtualization remains a separate improvement; loading
  all earlier batches can still construct many message widgets.
- Validate the complete desktop on an actual 8 GiB system or VM. The under-3-GiB
  idle target has not been established by these measurements.
