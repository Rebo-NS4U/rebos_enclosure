# Launcher search

The app launcher keeps fuzzy application matching and adds local search providers.
Use Up/Down to select a result and Enter to activate it. Existing application
shortcut actions (right-click or Shift+Enter) apply only to application rows.
Tab still switches to Projects.

| Input | Behavior |
| --- | --- |
| `weather tomorrow` | Application matches, then a Google action |
| `g weather tomorrow` or `google weather tomorrow` | Google only |
| `2+3*4` | Calculator result first, then apps and Google |
| `= sqrt(144) + 2^3` | Calculator only; Enter copies `20` |
| `example.org/docs` or `https://example.org` | Open address first, then other matches |
| `files report` or `file report` | Local home filename search |
| `~/Documents` or `/absolute/path` | Open an existing path with its default application |

Google and web addresses open in the system default browser. Queries are not sent
anywhere while typing. Calculator results are copied with the shell's existing
`wl-copy` dependency. Python 3 provides the search helper without extra packages.
The calculator accepts arithmetic, parentheses, `%` (remainder), `^`/`**`
(powers), `pi`, `e`, `tau`, and `sqrt`, `sin`, `cos`, `tan`, `log`, `log10`,
`floor`, `ceil`, `abs`, `round`. Trigonometric angles use radians. Calculations
have size and exponent limits; arbitrary code, attributes and imports are rejected.

Filename search runs after a 120 ms typing pause in a separate process. It searches
case-insensitively, breadth first, for up to 20 matches, 25,000 entries or half a
second. This is a bounded scan, not a complete file index or content search.
Hidden directories/files and build/dependency folders are excluded; directory
symlinks are not followed. Narrow the filename if a deep file is not shown.
Stale responses never replace results for a newer query. Queries and results
are not saved by these providers.

Verification: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s desktop/tests -p test_launcher_search.py`.
