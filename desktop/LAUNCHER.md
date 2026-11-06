# Launcher visibility

The application launcher reads optional per-user preferences from
`$XDG_CONFIG_HOME/rebos_shell/config/launcher.json` (normally
`~/.config/rebos_shell/config/launcher.json`):

```json
{"hiddenApps": ["example-utility.desktop"]}
```

Use desktop-file names or Quickshell desktop IDs. Hidden entries are excluded
from both the full app list and search results. This does not uninstall apps,
change file associations, or remove their system desktop files. Preferences
reload automatically; use an empty `hiddenApps` array to restore all entries.
The selection is personal and is not bundled with installer defaults.

## Built-in shell applications

The launcher includes Quick Notes, File Shelf, Calendar, Weather, System Monitor,
Project Picker, Dashboard, Notifications, Sound Controls, Microphone Controls,
Network Controls, Bluetooth Controls, Battery and Power, Power Menu, and Shell
Wallpapers, and Anime Streamer, alongside the existing Settings and Assistant entries. Search by
name or keywords such as notes, wifi, volume, or cpu. These entries open tools
in the running shell through `rebos_shell run` (or the `anime-streamer` wrapper); they do not start another shell.

Desktop entries are shipped as managed files in `system/share/applications` and
registered in the payload manifest so installation and updates preserve them.
