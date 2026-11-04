# Shared system theme

The approved System Theme Playground defines the component style: active wallpaper colors, JetBrains Mono at 14px, 16px corners, compact toolbar buttons, 40px menu rows, padded fields, subtle hover surfaces, and visible keyboard focus. The personal playground remains outside this repository.

`system/apps/shell/scripts/standard_theme.py` applies the component geometry alongside the effective palette exporter. It reads the existing shell font, size and radius. Menus, menu items, tabs, tooltips, fields and buttons use the same radius without inset offsets; circular radio buttons, switches and track ends retain their shape. Shell and assistant radius helpers and the portable web kit use that same corner metric. These changes regenerate when the palette or theme metrics change. Personal CSS, extra Qt stylesheets, comments and unrelated settings are retained. GTK CSS is written by this exporter only; GtkGenerator sends session preference notifications.

| Menus / applications | Adapter | Application |
| --- | --- | --- |
| Enclosure context menus and tray menus | Shared QML menu primitives | Quickshell hot reload |
| GTK3 apps: Thunar, pavucontrol, Bluetooth tools, archive manager, prompts | GTK3 CSS and settings | Live where supported; otherwise next app launch |
| GTK4 apps: Nautilus and GTK portals | GTK4 CSS and settings | Some apps require reopening |
| Qt5/Qt6 widgets: VLC, OBS, Qt settings and dialogs | qtct palettes, font and shared QSS | Toolkit notification or next app launch |
| Fuzzel application/dmenu menus | Generated palette, font and rounded border | Next menu opening |
| Zen browser menus | Existing chrome export plus menu geometry | User reopens browser; web page content is untouched |
| VS Code menus | Workbench menu and selection colors | Settings update; UI geometry remains application controlled |
| Spotify | Existing Spicetify theme plus menu geometry | Existing no-restart refresh, when configured |
| Vesktop | Existing Discord theme generator | Theme reload, when enabled |
| Locus Linux | Shared system stylesheet adapter in its owning repository | Existing two-second theme watcher |
| Niri window/popup blur | Existing compositor rules and alpha-aware backgrounds | Niri hot reload; no compositor restart |

Theme refresh never restarts browsers or music players. Apps without a live theme reload apply changes when reopened by the user. Media launch changes apply on next playback launch and never interrupt active playback.

This coverage is not a claim that every installed interface is converted. GTK application CSS and Qt application stylesheets can override theme rules. Qt Quick applications, Electron clients without theme APIs, Steam, games, browser content and proprietary custom interfaces require app-specific work or do not expose full theming. Flatpak applications may require explicit access to a theme. Root-owned login and authentication surfaces require a separately approved administrator update; this task does not write them.

Use `~/.cache/rebos_shell/theme-standard-status.json` for installed adapter/metric status. Run `desktop/tests/test_standard_theme.py` for preservation and repeatability checks. Validate generated GTK3/GTK4 CSS with each toolkit and Qt QSS with representative widgets before changing the component rules.

References: [Qt stylesheet controls](https://doc.qt.io/qt-6/stylesheet-reference.html), [GTK CSS properties](https://docs.gtk.org/gtk4/css-properties.html).
