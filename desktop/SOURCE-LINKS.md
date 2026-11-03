# Installed files and optional development links

The normal layout is one active installed copy at `~/.config/quickshell`,
`~/code/rebos-assistant` and `~/code/anime-streamer`, plus the separate Enclosure
repository. Launchers and service definitions use those installed paths. Updating
replaces that copy in place. Temporary fetched snapshots are cleaned up after
success or failure; recovery backups are inactive and are not application paths.
Copied installations stay copied. Updates never enable development links by
accident or install another active copy under a versioned directory.

The updater fetches the default branch's current update engine before applying
the selected payload. Selecting an older release pins features, not the engine.
A bootstrap from before this handoff needs one `git pull --ff-only` refresh;
unchanged old scripts cannot acquire new logic remotely. GitHub Settings uses the
same `update.sh` entrypoint as the terminal. Legacy fetched sources without the
handoff protocol use the current local engine; unknown protocols fail safely.

## Optional development layout

On a development desktop, the installed application paths can be symlinks to
`desktop/payload/home/` in a persistent Enclosure checkout:

| Installed path | Source under `desktop/payload/home/` |
| --- | --- |
| `~/.config/quickshell` | `.config/quickshell` |
| `~/code/rebos-assistant` | `code/rebos-assistant` |
| `~/code/anime-streamer` | `code/anime-streamer` |

The aliases contain no second copy. Existing commands and services keep using
their installed paths. Edit either path to change the same files. Keep this
checkout in place while using the desktop. Personal settings, accounts and chat
history stay in their existing XDG directories, outside the application source.

To deploy from this checkout while retaining preferences:

```sh
python3 desktop/scripts/deploy.py --link-source --preserve-preferences --dry-run
python3 desktop/scripts/deploy.py --link-source --preserve-preferences
```

Deployment saves replaced paths in a recovery backup and reports its location.
Use `deploy.py --restore BACKUP` to restore those paths. Recovery backups can
contain old source versions; they are not active application installations.
Local files absent from the portable payload must be preserved separately
before removing an old installation. Keep recovery archives separate from the active application paths.

The normal updater recognizes these links and checks the requested origin.
It previews incoming commits and local edits in an isolated Git worktree before
changing the installed checkout. Compatible local commits are retained in a
local merge; staged edits, unstaged edits and untracked files are preserved.
Conflicting source edits stop the preview with the live checkout untouched.
Generated payload hashes are rebuilt from the preserved source files.

Before applying, it saves a private recovery archive under
`~/.local/state/rebos-desktop/local-source-backups/`. Tracked edits also remain
in a labeled Git stash after successful restoration. Nothing is pushed.
The live checkout is checked again for edits made during the preview. Linked
updates reuse its existing Git objects rather than downloading the whole payload
again. An older release remains a merge target; revision switching/downgrading
requires an explicit manual checkout.
File recovery restores installed paths, not Git history; use Git to recover a
previous source revision. Changes load through the existing application reload
or restart behavior; deployment does not restart active conversations.

Portable installations from temporary release snapshots still copy source into
their installed paths. The deployer refuses to replace an existing linked
installation with a second copy. Python bytecode caches are ignored during
payload verification, while checksummed source files must still match.

`update.sh` resolves the installed source checkout before choosing its updater.
When invoked from an older checkout, it uses the live checkout's updater only
when both origins match. This prevents old deployment code from treating the
assistant or media source symlinks as ordinary destination directories. Local
edits are previewed and preserved before deployment. The updater never silently
discards them.

Updates fetch the remote default branch unless a branch or release is explicitly
selected. Personal accounts, history, generated palettes and wallpaper choices
remain local. Configuration directories are updated file by file: new shipped
files are added, and files still matching their previous shipped default receive
new defaults. Customized files and configuration symlinks are retained. On the
first update without a defaults record, the updater uses the recorded installed
revision to recover old defaults from local Git history when available. Otherwise
existing files are conservatively kept. Each update records the shipped defaults
for subsequent comparisons. Intentionally deleted known preferences stay deleted.
Files removed upstream are retained to avoid deleting personal includes. A customized
file that also changed upstream is reported as kept and requires manual merging.
The defaults record is backed up and restored with the deployment. The default
GitHub status shows the installed desktop revision; selecting a project shows
that checkout's independent Git status.
