# Enclosure development

The repository-first, tested automatic commit/push workflow applies to every GitHub project handled by this assistant, not only Enclosure. The assistant sends this policy to new and restored backend conversations; these instructions add the Enclosure-specific mapping below. Create releases when requested.

Work in this repository first and apply the task's changes to installed files for verification. If a live edit is necessary first, bring its focused diff into the repository during the same task. Preserve unrelated changes and portable installer substitutions; do not refresh the entire desktop snapshot for a small edit.

Installed paths map to these tracked sources:

| Installed path (relative to the user's home) | Repository source |
| --- | --- |
| `.config/quickshell/` | `desktop/payload/home/.config/quickshell/` |
| `code/rebos-assistant/` | `desktop/payload/home/code/rebos-assistant/` |
| `code/anime-streamer/` | `desktop/payload/home/code/anime-streamer/` |
| Other shipped home files | Matching paths under `desktop/payload/home/` |

Check `desktop/scripts/snapshot.py` and `desktop/payload/manifest.json` when adding shipped files. Update required package declarations, services, installer behavior, documentation and tests within the same task. Refresh changed entries in `desktop/payload/checksums.json` and verify the payload with `desktop/scripts/deploy.py` before committing. Put maintainer tests in `desktop/tests/` when they should not be installed; direct Python bytecode caches outside the checksummed payload.

Ship portable source and defaults only. Exclude credentials, account files, personal settings/history, caches, downloaded models and build artifacts. Preserve explicit `@HOME@` substitutions and existing privacy filtering.

Verify both repository behavior and applicable installed behavior. The user authorizes committing and pushing tested task changes automatically to the verified existing remote; use explicit paths/hunks, respect branch policy and never force-push. If the remote advanced, reconcile without overwriting others' work. Report the pushed commit and any verification limits. Do not restart active desktop services without applicable user authorization.
