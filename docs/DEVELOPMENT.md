# Developing Enclosure across Arch machines

Enclosure supports an installed x86_64 Arch Linux system with Niri and Quickshell.
Hardware policy, application selection, portable source and personal state are
separate. A new machine does not need the original developer's home, monitor
names, GPU environment variables, fan controller or account files.

## Repository controls in GitHub Settings

Open **Settings → GitHub** and select or add a local GitHub repository. Repository
review checks merge conflicts, staged and unstaged whitespace, local changes and
free storage. It never runs repository code, fetches, or claims project tests passed.
Changed files, local history, pending commits, branches, staging, commits, pushes
and pull requests apply to the selected repository. Pending commits use the last
fetched Git state; use **Fetch origin** to refresh it. No check pushes changes.

The standalone graphical development app has been removed. Its old desktop entry
is shipped as hidden so updates retire an already-installed launcher. Desktop
installation and update controls remain Enclosure-specific; use **Update installed
desktop** in GitHub Settings for updates.

## Terminal maintenance

From the Enclosure checkout, run `./dev.sh` for the terminal menu. Use
`./dev.sh check` for project tests and payload verification, or `./dev.sh health`
and `./dev.sh outgoing` for read-only reports.

The menu offers personal configuration access, grouping previews/migration, status/diffs, a hardware plan, tests, explicit file staging,
payload checksum regeneration, local deployment previews, deployment, local
commits, push, fast-forward source pulls, and installed desktop updates.
Every action also works as a command; `./dev.sh --help` lists options.

The launcher finds a linked checkout or `~/code/rebos_enclosure`. For another
location, set `ENCLOSURE_SOURCE=/path/to/checkout`. Both fetch and push origins
must point to the official Enclosure repository. Detached HEAD checkouts must
switch to a development branch first. Git branch policy still applies.

Typical edit cycle:

```sh
./dev.sh status
# Edit config/ defaults or system/ source in this checkout.
./dev.sh diff
./dev.sh stage path/to/changed-file path/to/new-file
./dev.sh hashes
./dev.sh stage desktop/payload/checksums.json
./dev.sh check
./dev.sh preview
./dev.sh deploy
./dev.sh commit -m 'Describe the resulting behavior'
# Explicitly publish only when ready:
./dev.sh push
```

Staging requires explicit file paths. No menu operation runs `git add .`, resets
source, force-pushes or automatically pushes after a commit. Commit verification
exports and tests the **staged** source, so unrelated working edits cannot mask
missing staged files. Tests use the dependencies of the development Arch machine;
install the `development` application group. Niri, Qt/Quickshell, Fish, a C
compiler, ncurses and GTK development files are needed by the existing full suite.

Checksum regeneration reads tracked/staged payload paths only. Review and stage
new source before hashing; untracked payload files stop regeneration rather than
silently shipping personal files. New top-level shipped files also need entries
in `desktop/payload/manifest.json` and the snapshot recipe. Launcher source is in `system/bin/` and `system/share/applications/`; there is no duplicate template tree.

Local deployment uses `--preserve-preferences`, makes recovery backups and retains
existing source links to this checkout. `./dev.sh deploy --link-source` explicitly
enables source links on a copied installation. Keep a linked checkout in place.
The menu does not restart desktop services or active assistant/media backends.
Source-linked QML changes follow the desktop's existing reload behavior.

Pull updates the repository with `--ff-only` and refuses a dirty checkout.
Update runs the existing `update.sh --files-only` pipeline, including its preview,
preference preservation and linked-source reconciliation. Neither action installs
packages. Use the installer/updater directly when package changes are needed.

See the [filesystem guide](FILESYSTEM.md) for the grouped source and personal settings layout. Packaging exports reviewed committed source; live-home snapshotting has been removed.

## Machine profiles

```sh
./install.sh --local-snapshot --machine auto --profile core --dry-run
./install.sh --machine laptop --profile core
./dev.sh hardware --machine virtual
```

| Profile | Selection and behavior |
| --- | --- |
| `auto` | Detect VM first, then battery/portable chassis, otherwise desktop. |
| `desktop` | Enable keyboard Num Lock at startup. |
| `laptop` | Keep normal keyboard defaults; shared touchpad settings apply when present. |
| `virtual` | Keep normal keyboard defaults and disable Niri animations. |

The plan reports battery, Bluetooth, backlight and virtualization capabilities.
Detection is read-only; missing detection tools or sysfs data have conservative
fallbacks. An explicit profile overrides detection. GPU choice and core/full app
selection remain independent; a laptop profile does not imply NVIDIA, and a
desktop profile does not disable Bluetooth or power controls.

`desktop/scripts/hardware.py` owns detection and policy. `setup.py` combines that
policy with GPU/package/service choices and renders local `hardware.kdl` and
`monitors.kdl`. `deploy.py` installs verified source and retains personal state.
`develop.py` orchestrates those existing tools and Git without duplicating their
deployment/update logic. Machine identity stays in the destination's installation
record and generated Niri includes; it does not become a shipped personal profile.
Old version-1 installation plans without a machine field remain accepted.

Display modes and placement remain automatic unless explicitly configured with
`--monitors`. No profile embeds connector names, resolutions, firmware workarounds,
fan policies, CPU governors, forced render GPUs or a particular laptop vendor.
Existing installations keep customized settings during updates; use installer
setup to choose a new machine policy deliberately.

## Compatibility and verification limits

| Hardware | Installer support |
| --- | --- |
| Intel/AMD desktop or laptop | CPU microcode and Mesa/Vulkan selected from detected vendors. |
| Mixed integrated + NVIDIA | Keep existing driver by default; explicitly select an NVIDIA family and optional offload. |
| NVIDIA-only | Explicit driver family and kernel headers; conflicts stop before replacement. |
| Virtual machine | Generic Mesa option, automatic outputs and reduced animations. |
| Docked/multiple displays | Automatic layout, or explicit scaled/rotated monitor JSON. |

This is not support for every GPU or firmware combination. Proprietary driver
generation selection stays explicit. ARM, non-Arch distributions and Windows/macOS
are outside this redesign's target. Real boot/login, suspend/resume, docking,
Wi-Fi/Bluetooth and GPU acceleration must be exercised on destination hardware.
Unit tests and Niri validation cannot establish those physical behaviors.

For each supported hardware family, validate a core install in a spare system or
VM, boot into Niri, check output scaling/input/audio/network, suspend and resume
where supported, and preview/apply an update retaining personal settings before
declaring that hardware tested. No release should imply a machine matrix was
physically tested when only synthetic fixtures were used.

## Symphony assistant profile

Choose **dweebo-Symphony** in the Codex profile picker. It uses the same Sol
model and medium reasoning as dweebo-Do, with issue execution guidance adapted
from [Symphony SPEC.md](https://github.com/openai/symphony/blob/main/SPEC.md).
It reads repository instructions and WORKFLOW.md when available, checks issue
eligibility, uses isolated issue worktrees, validates changes, bounds transient
retries and reports a review handoff. Existing permissions and publication rules
still apply. Selection and guidance use the existing per-chat persistence and
mode-switching path; the default profile stays dweebo-Do.

This is an interactive profile, not an implementation of the Symphony service:
there is no background tracker polling, concurrent scheduler, automatic cleanup
or restart recovery. Workflow runtime settings require a separate service.
Tracker actions require available authenticated tools and user authorization.
