# Enclosure development

The repository-first, tested automatic local-commit workflow applies to every GitHub project handled by this assistant, not only Enclosure. The assistant sends this policy to new and restored backend conversations; these instructions add the Enclosure-specific mapping below. Create releases when requested.

Work in this repository first and apply the task's changes to installed files for verification. If a live edit is necessary first, bring its focused diff into the repository during the same task. Preserve unrelated changes and portable installer substitutions; do not refresh the entire desktop snapshot for a small edit.

Locate the checkout before editing: check `~/rebos_enclosure`, then
`~/code/rebos_enclosure` and resolved installed symlink targets. Verify with
`git rev-parse --show-toplevel` and `git remote -v`. A copied installation under
`~/.local/share/enclosure` has no `.git`; this does not establish that no checkout
exists. Before finishing, compare the task-related installed files with their
tracked mappings and recover any missed focused changes.

Development installations can link application sources to the payload
in this checkout; copied installations have separate managed files. Check `readlink -f` before editing or deploying: both paths may
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

## Shared visual theme

For UI work in Enclosure and projects derived from it, use Dweebo’s visual theme. See `system/apps/assistant/design-system/README.md` for the portable CSS kit and existing QML components. Reuse its buttons, text, fields, semantic palette and interaction states; regenerate tokens when changing the source theme.

## Standing user preferences

These preferences apply when relevant to the current request; they do not authorize unrelated repository work or desktop checks. Respond normally to greetings.

- When the user says “the repo” or “the repository” without naming another project, they mean Rebos Enclosure, not `rebos-assistant`.
- Make focused changes, inspect only relevant context, and run checks that verify the requested behavior. Keep explanations concise. Do not delegate unless requested.
- Start with one task sentence and give brief, useful progress during multi-step work. Activity titles should state the action and purpose, with commands and output in details.
- For consequential preferences or missing details, discover `assistant_questions.ask_user_question`, offer two or three choices, and wait before dependent edits. Ask in chat only if that tool is unavailable. Continue independent authorized work.
- Use only relevant skills; read their entrypoint and required references, skipping generic explanations. Do not automatically read or write persistent memory, including Obsidian notes; use saved notes only on explicit request. Keep Token Optimizer enabled.
- Use `~/.local/bin/rtk` for supported noisy searches, git, tests and logs when available; check `rtk <command> --help` for syntax. Use raw commands for exact source, patches, structured output or details omitted by compression. Compression never replaces verification.

### Desktop access and playback

Empty `ps` or `pgrep` results in a restricted command session do not prove desktop applications are stopped. Check the user service and session connection using available tools: `systemctl --user`, D-Bus, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR` and `NIRI_SOCKET`. If access is restricted, request the tool's supported approval for the specific check or action and retry after approval. Never bypass isolation or a denied approval. If approval is unavailable, state the exact limitation. Never claim a restart succeeded without checking it.

Quickshell QML and Niri configuration hot-reload automatically; do not kill or restart them for configuration edits. Anime Streamer mpv launch changes apply on the next playback launch and do not require restarting VLC or Quickshell. Preserve active playback and assistant backends unless the user requests a restart.

For requested panel changes, inspect the assistant source at `~/code/rebos-assistant` and shell configuration at `~/.config/quickshell`, following the repository mappings above. Establish access with tools and request supported approval if blocked. Report unavailable or rejected approval and the exact blocked action. Use `~/.local/bin/assistant-sudo --reason 'reason' -- command` for each administrator action. Preserve unrelated work and active backends.

### GitHub network access

Dweebo enables network access in Codex workspace mode while retaining workspace file protections and tool approvals. Try the normal `git` or `gh` command first. Host or administrator restrictions can still block access. For GitHub DNS failures, blocked connections, or a sandboxed `gh auth status` failure, request the execution tool's supported network approval for the exact command and retry after approval. With Codex `exec_command`, use `sandbox_permissions=require_escalated` and a specific justification when available. Task authorization to push does not replace tool approval.

If approval is unavailable or rejected, report the exact blocker and provide the command for the user to run. A sandboxed authentication failure does not establish an invalid credential. Never log out, delete credentials or start reauthentication based on that failure; verify authentication only after network access succeeds. Ask only when a new repository's destination or visibility is unclear. Never include secrets or personal state, force-push or bypass sandbox approvals.

### Task outcome reporting

End the final reply with exactly one outcome line. Use `Task outcome: Positive — <verification>` only if the whole request succeeded; otherwise use `Task outcome: Negative — <remaining work or blocker>`.
