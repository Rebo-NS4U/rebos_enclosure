# One application source tree

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
before removing an old installation. The initial consolidation on this desktop
stores those extras in `~/.local/share/rebos-desktop/local-extras/`.

The normal updater recognizes these links, checks that the checkout is clean and
has the requested origin, and fast-forwards it before redeploying with links.
Commit local changes before updating. A divergent or older release cannot be
fast-forwarded; select its revision manually in the checkout if intended.
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
edits are checked before downloading a snapshot or upgrading packages; preserve
or commit those edits first. The updater never silently discards them.
