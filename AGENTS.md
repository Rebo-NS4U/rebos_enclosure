# Enclosure development

The repository-first, tested automatic local-commit workflow applies to every GitHub project handled by this assistant, not only Enclosure. The assistant sends this policy to new and restored backend conversations; these instructions add the Enclosure-specific mapping below. Create releases when requested.

Work in this repository first and apply the task's changes to installed files for verification. If a live edit is necessary first, bring its focused diff into the repository during the same task. Preserve unrelated changes and portable installer substitutions; do not refresh the entire desktop snapshot for a small edit.

This development desktop links its installed application sources to the payload
in this checkout. Check `readlink -f` before editing or deploying: both paths may
already refer to the same file. Preserve these links; do not recreate duplicate
installed source trees. See `desktop/SOURCE-LINKS.md` for deployment and updates.

Installed paths map to these tracked sources:

| Installed path (relative to the user's home) | Repository source |
| --- | --- |
| `.config/quickshell/` | `system/apps/shell/` |
| `code/rebos-assistant/` | `system/apps/assistant/` |
| `code/anime-streamer/` | `system/apps/media/` |
| Personal settings | `~/.config/enclosure/` locally; portable defaults under `config/` |
| Other shipped files | Explicit source mappings in `desktop/payload/manifest.json` |

Use `desktop/payload/manifest.json` to map `config/` defaults and `system/` source when adding shipped files. `snapshot.py` verifies source or exports committed HEAD; never snapshot a live home. Update required package declarations, services, installer behavior, documentation and tests within the same task. Refresh changed entries in `desktop/payload/checksums.json` and verify the payload with `desktop/scripts/deploy.py` before committing. Put maintainer tests in `desktop/tests/` when they should not be installed; direct Python bytecode caches outside the checksummed payload.

Ship portable source and defaults only. Exclude credentials, account files, personal settings/history, caches, downloaded models and build artifacts. Preserve explicit `@HOME@` substitutions and existing privacy filtering.

Verify both repository behavior and applicable installed behavior. The user authorizes committing tested task changes locally automatically; do not push unless explicitly requested by the user or initiated with the Push button in GitHub Settings; use explicit paths/hunks, respect branch policy and never force-push. If the remote advanced, reconcile without overwriting others' work. Report the local commit, whether it remains unpushed, and any verification limits. Do not restart active desktop services without applicable user authorization.
