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
