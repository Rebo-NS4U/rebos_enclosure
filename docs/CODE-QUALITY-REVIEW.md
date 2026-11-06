# Code quality review — 2026-11-06

Radon 6.0.1 and Pylint 4.1.3 were run locally against `desktop/scripts` and `system`. Radon reads Python, including recognized extensionless Python helpers. Pylint was run with its design and duplicate-code checkers enabled; formatting and naming rules were not enabled. These are static maintainability signals, not proof of defects. QML is outside their coverage.

## Results

- Radon: 710 unique functions/methods; grades A: 430, B: 127, C: 111, D: 25, E: 6, F: 11.
- Pylint: 153 design findings. Its nonzero status reflects those findings, rather than a tool crash.

| Complexity | Grade | Function |
| --- | --- | --- |
| 97 | F | `desktop/scripts/deploy.py:149` — `install` |
| 68 | F | `system/bin/bonsai-grow:848` — `specimen` |
| 64 | F | `system/bin/bonsai-grow:674` — `natural_specimen` |
| 59 | F | `desktop/scripts/setup.py:23` — `normalize_monitors` |
| 52 | F | `system/apps/media/menu_backend.py:380` — `Engine.player_event` |
| 49 | F | `system/apps/media/vlc_session.py:366` — `VlcSession.poll` |
| 48 | F | `system/bin/bonsai-grow:1390` — `render` |
| 45 | F | `system/apps/media/menu_requests.py:63` — `dispatch` |
| 45 | F | `system/apps/media/discovery_catalogue.py:122` — `_page` |
| 44 | F | `system/apps/shell/scripts/github_projects.py:231` — `action` |

The largest runtime hotspot is the installer deployment function. Other review targets include monitor normalization, player event handling, VLC polling and media request dispatch. Large dispatchers and generated drawing logic can legitimately have high complexity, so each needs behavioral tests and contextual review before refactoring. No broad behavior-changing refactor was made just to improve grades.

## Fixes made in this review

The emoji picker now uses the already-installed Fuzzel in dmenu mode, keeps its catalog in a quoted here-document, and copies only a selected emoji. It no longer invokes missing /usr/bin/dmenu or reads an unquoted script path. Canceled and empty selections do not write to the clipboard. Four focused regression tests passed against both tracked source and installed helper. ShellCheck, Bash syntax, Ruff and payload verification passed.

## Reproduce

Install `radon==6.0.1` and `pylint==4.1.3` in an isolated development virtual environment, then run from the repository root:

```sh
radon cc --json --show-complexity desktop/scripts system > complexity.json
radon mi --json desktop/scripts system > maintainability.json
pylint --recursive=y --disable=all --enable=design,duplicate-code --reports=n --score=n --output-format=json desktop/scripts system > design.json
```

Radon cyclomatic complexity counts decision paths. Its Maintainability Index is heuristic and should not be treated as a whole-repository quality score. Pylint points to specific branch-heavy functions, large methods/classes and duplicate blocks. Existing Ruff, behavioral tests and payload/build checks remain complementary.

References: [Radon](https://radon.readthedocs.io/en/stable/commandline.html), [Pylint design checker](https://github.com/pylint-dev/pylint/blob/main/pylint/checkers/design_analysis.py).

## Follow-up investigation

The original 153 findings were design heuristics, not failed behavioral tests. Branch/local/statement counts account for most findings. Argument and instance-attribute counts are common in the existing UI, playback and callback interfaces. The short validation returns in provided_cues_usable and process_monitor are guard clauses; merging them just to reduce return counts would make review harder. Small worker/configuration classes need no artificial public methods.

The nine duplication findings include parallel shell/assistant helpers, shared bridge protocol handling, small window-close wrappers and similar subprocess error handling. Pylint attaches its end-of-run similarity reports to window_rules.py; that does not mean the copied code is in window_rules.py. Removing parallel application helpers requires an explicit shared-module deployment design, rather than deleting one application's copy. These reports remain visible.

### Changes verified

- Deployment now separates preference-preserving selection and source-link planning from installation, backup journaling and file mutation. The main install function's cyclomatic complexity fell from 97 to 48. The extracted responsibilities still have their own reviewable decision paths; no conditions were deleted to improve a score.
- Monitor configuration now separates per-connector validation and logical rotated/scaled dimensions from multi-monitor placement. normalize_monitors complexity fell from 59 to 32. The same size helper is used for automatic placement and overlap checks.
- Reviewing scale validation revealed an actual bug: math.isfinite on an enormous integer raised OverflowError. Bounds are now checked before conversion, so invalid input raises the normal explanatory ValueError. Regression checks cover that case, fractional-scale rotation, adjacent manual boundaries, one-pixel overlap and preservation of the caller's configuration.

Pylint now reports 155 design warnings, up from 153 because the extracted preference-selection helper independently crosses local-variable/branch thresholds. This is reported rather than suppressed: smaller responsibilities and corrected behavior are the outcome, not a claim of a clean lint baseline. Large deployment helpers, monitor validation, artwork generation and playback dispatch still merit incremental work with behavior checks. No broad rewrite of live playback or independently deployed assistant modules was attempted.

These changes affect the checkout's installer/updater tooling. No active desktop or assistant service was restarted, and no personal monitor configuration was applied. The deployment payload itself is unchanged and its existing checksum inventory still verifies.

Validation after the follow-up: 343 desktop tests and 84 media tests passed, Ruff runtime checks passed, payload verification passed, and preference-preserving deployment preview against the actual installation passed without applying files. Raw follow-up metrics and test logs are retained with the local review artifacts.

## Second cleanup pass

Pylint design warnings fell from **155 to 150**, with no suppressions or threshold changes. Preference selection no longer exceeds the branch, statement or local-variable thresholds; monitor normalization no longer exceeds the branch/local thresholds.

Default-file fingerprinting and replacement decisions, recovery of legacy defaults from Git, and loading recorded baselines now have separate functions. The selection loop retains the same symlink safeguards and preserves unknown personal files and intentional deletions. Its cyclomatic complexity is now 13 (previously 32 before this pass).

Monitor normalization now delegates automatic placement and manual overlap checking to distinct helpers. Its complexity fell from 32 to 17; the placement and overlap functions score 9 and 8. Validation and placement errors retain their existing messages and behavior. These splits make the permission to replace a preference file and the geometry rules independently reviewable.

Validation: **88 tests passed** across deployment (31), monitor/setup (16), updater/health/handoff (18), source layout (12) and linked-update recovery (11). Ruff and payload verification passed, and preference-preserving deployment preview against the installed desktop passed. Changes remain in installer/updater tooling; no desktop services or personal configuration were changed.

## Argument and duplication audit

See the [detailed argument, duplication and branch review](CODE-QUALITY-DETAILS.md) for the decisions on every argument warning, the actual bridge differences, the consolidated helpers and the remaining branch inventory. The latest scanner reports 137 warnings (previously 150), including 7 duplicate-code, 35 branch and 6 positional-argument warnings. Total-argument warnings remain visible.

## Remaining warning usefulness

The [remaining warning review](REMAINING-WARNINGS.md) classifies all 136 current observations by usefulness and records the bounded GPU-query fix. Low-value structural warnings remain visible; no suppressions were added.
