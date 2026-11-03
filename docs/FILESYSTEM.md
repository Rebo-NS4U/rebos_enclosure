# Enclosure filesystem

There are two source locations to edit:

| Repository path | Contents |
| --- | --- |
| `config/` | Shipped configuration defaults, grouped by application. No personal settings. |
| `system/` | Managed application code, commands, services, fonts, icons, wallpapers and privileged templates. |
| `desktop/` | Installer/update tools, tests, package selection and deployment metadata. |

Within `system/`, `apps/` contains `shell`, `assistant` and `media`; `bin/` and
`scripts/` contain commands; `services/user/` contains user services; `etc/`
contains root-owned install templates; `share/` contains shared resources.
`cache-defaults/` seeds runtime caches without treating them as personal settings.
There is one shipped wallpaper/font collection. Maintainer tests live in
`desktop/tests/`, outside installed application source.

`desktop/payload/manifest.json` maps those sources to application paths and
classifies each as personal defaults, managed code or initial cache data.
`checksums.json` verifies both source trees and the manifest. Neither metadata
file contains personal settings. The tools also understand old release payloads,
so an existing installation can migrate through the normal updater.

## Installed locations

| Installed path | Purpose and update policy |
| --- | --- |
| `~/.config/enclosure/` | Personal settings, grouped by application. Updates retain customizations. |
| `~/.local/share/enclosure/defaults/` | Pristine shipped configuration defaults; refreshed by updates. |
| `~/.local/share/enclosure/system/` | Managed applications, commands, services and shared resources. |
| `~/.local/state/rebos-desktop/` | Installation records and inactive recovery backups. |
| `~/.cache/` | Generated runtime data; separate from configuration and source. |

For development installations, managed application links point directly into
this checkout's `system/` tree, so there is no second active source copy.
Personal settings remain outside the repository. Application schema files such
as `system/apps/shell/config/Config.qml` are program code; they are not the user's
persisted JSON settings.

Existing application lookup paths remain symlinks. For example:

```text
~/.config/niri           -> ~/.config/enclosure/niri
~/.config/kitty          -> ~/.config/enclosure/kitty
~/.config/rebos_shell    -> ~/.config/enclosure/shell
~/.config/quickshell     -> managed system/apps/shell
~/code/rebos-assistant   -> managed system/apps/assistant
~/code/anime-streamer    -> managed system/apps/media
```

These are aliases, not duplicate configurations. Standard Linux paths such as
`/etc/greetd/` remain where the operating system requires them; their install
sources are together in `system/etc/`. Other applications' unrelated configuration
is left alone. Accounts, histories and custom files within a moved personal
configuration directory move with it and never enter the repository.

## Migrate an existing installation

Use the development menu's **Preview grouping installed settings and system
files**, then **Group installed settings and system files**, or:

```sh
./dev.sh organize-preview
./dev.sh organize
```

The migration renames files and directories without changing their contents,
keeps standard lookup paths as links, and writes a recovery journal. It does not
restart services, playback or assistant backends. If both the old personal path
and its intended new location already exist, it stops for reconciliation instead
of choosing one. Repeating a completed migration makes no changes.

New installs and updates organize files automatically. Unchanged personal files
can receive a newer default, customized files are kept, genuinely new default
files are added, and intentional deletions stay deleted. The separate defaults
folder always shows the current shipped version. Modified managed code belongs
in the repository before updating; the updater retains its existing local-change
checks and linked-checkout recovery behavior.

Restore a reported journal using:

```sh
python3 desktop/scripts/deploy.py --restore /path/to/reported/backup
```

The journal restores files, links and their previous locations. It does not undo
package changes or Git history.

## Find and edit configuration

**Config Browser** opens personal settings, system defaults and managed source
as separate menu choices. `./dev.sh configs` opens the personal settings folder.
Edit shipped defaults in `config/` when developing; edit your settings under
`~/.config/enclosure/` for changes specific to this computer.

Review and stage explicit new source paths, then run `./dev.sh hashes` and stage
`desktop/payload/checksums.json`. `snapshot.py --verify` checks reviewed source;
`snapshot.py --output /tmp/enclosure.tar.gz` exports committed HEAD. There is no
live-home snapshot operation, so packaging cannot accidentally import personal
settings, histories, models or credentials.

During this development desktop's migration, three ignored aliases under
`desktop/payload/home/` keep already-running processes' resolved source paths
usable until their next natural launch. They contain no duplicate files, are not
shipped and are not an editing location. Installed links already point to the new
canonical source. They can be removed after the old processes have exited.
