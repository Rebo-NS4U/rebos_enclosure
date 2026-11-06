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
