# Installed source and development links

See the [filesystem guide](../docs/FILESYSTEM.md) for source, personal settings,
managed defaults, migration and recovery. Edit `config/` for shipped defaults and
`system/` for applications/services. Do not edit a personal directory to change
what the installer ships.

## Development source

| Standard application path | Source in this checkout |
| --- | --- |
| `~/.config/quickshell` | `system/apps/shell` |
| `~/code/rebos-assistant` | `system/apps/assistant` |
| `~/code/anime-streamer` | `system/apps/media` |

These links contain no second copy. Keep the checkout in place. Personal
configuration is grouped under `~/.config/enclosure/`, with accounts, histories
and generated state outside application source. Normal copied installs keep
managed files under `~/.local/share/enclosure/system/`.

```sh
python3 desktop/scripts/deploy.py --link-source --preserve-preferences --dry-run
python3 desktop/scripts/deploy.py --link-source --preserve-preferences
```

Deployment creates a recovery journal and keeps existing personal settings.
The normal updater retains development links and checks the origin. Copied
installations stay copied; updates never enable development links implicitly.
No deploy or organize command restarts active desktop, assistant or media services.

## Linked updates and recovery

`update.sh` selects the live checkout's update engine when its origin matches.
The current engine fetches the requested branch or release. Selecting an older
release pins payload features, not the engine. Very old bootstraps still need a
one-time `git pull --ff-only` refresh before acquiring this handoff behavior.

Before changing linked source, the updater previews a merge in an isolated Git
worktree. Compatible local commits, staged edits, unstaged edits and untracked
files are preserved. Conflicts stop before deployment. Layout migration relocates
reviewed untracked source alongside renamed tracked code. Hash metadata is rebuilt
from preserved source, and the live checkout is checked again for concurrent edits.

Recovery archives are private and saved under
`~/.local/state/rebos-desktop/local-source-backups/`. Tracked changes also remain
in a labeled Git stash after restoration. Nothing is pushed automatically.
Recovery archives are inactive restore points, never a second active application.

File recovery uses the journal reported by deployment or organization. It restores
paths and links, including the prior arrangement before grouping settings.
Use Git to recover source revisions; file recovery does not change Git history.

## Assistant UI recovery

The assistant keeps its open chat channels in
`~/.local/state/rebos-assistant/states.json`. Writes create the private directory
and replace the file atomically. If the registry is missing or damaged after a
UI crash, startup finds surviving bridge sockets in the current runtime session
and restores their tabs without restarting the backends. A saved empty tab list
is respected. The panel and assistant UI are separate Quickshell instances.
