# Assistant presets

Do remains the default for implementing and verifying application changes.
The other presets use distinct task methods; selecting a role does not silently
change it to another role or authorize delegation.

| Preset | Specialty | Completion evidence |
| --- | --- | --- |
| Do | Focused implementation and debugging | Relevant behavior checks |
| Deep | Root-cause investigation, architecture and complex research | Tested hypotheses, regression checks or cited findings; explicit uncertainty |
| Symphony | Bounded issue execution | Acceptance criteria mapped to validation and a review handoff |
| Light | Linux configs, desktop troubleshooting and small scripts | Minimal reversible fix plus parser or behavior validation |
| Quick | Direct answers, commands, rewrites and calculations | Answer first; targeted verification when needed |
| Know | Sourced explanations, teaching and comparisons | Clear reasoning, concrete examples and evidence beside claims |

Model and reasoning settings are unchanged. Role guidance is delivered when a
conversation first uses it, when its text changes, or when the user changes roles.
Existing conversations receive revised guidance on their next prompt. QML changes
hot-reload; no desktop service restart is required.

## Tools and role skills

Each specialist preset supplies a resolved path to its bundled `skills/*/SKILL.md`.
The assistant reads the matching skill when the task needs that specialty; ordinary
chat does not require loading it. This is instruction-based tool routing, not
per-preset tool isolation. Shared connected tools remain available. Do is unchanged.

- Light: `light-linux`, with a read-only platform/tool inventory helper.
- Quick: `quick-answer`, with a restricted decimal arithmetic helper (28 significant digits).
- Know: `know-evidence`, with source freshness, version matching and claim attribution.
- Deep: `deep-investigation`, with discriminating hypotheses and regression evidence.
- Symphony: `symphony-acceptance`, with an acceptance ledger and tracker-aware handoff.

The helpers use only the Python standard library and run through normal execution
approvals. The environment helper reads no session credentials, logs or service state.
It cannot establish desktop connectivity. No helper bypasses execution permissions.

Context7 is an optional documentation integration for technical tasks. It must be
installed and connected separately; the skills discover it before use and fall back
to official documentation when unavailable. No account tokens or plugin connection
state are shipped, and no connection or global permission is changed by these presets.

Skills ship within the existing assistant installer source mapping, so installed
copies receive the same skills and helpers as development symlinks. They are loaded
by the preset's explicit file reference rather than requiring a global skill install
or a backend restart.

## Tab shortcuts

While the assistant is focused, press Ctrl+H for the previous conversation tab
and Ctrl+L for the next. Navigation wraps at either end and focuses the composer.
