# Shell theme

The compact technical default uses JetBrains Mono at 13px, opaque semantic surfaces, 4px corners and 160ms animations. Change fonts, size, corners and surfaces in the existing Theme settings; typography and layout spacing follow those settings together. Icon fonts remain dedicated icon fonts. Circular controls and illustration geometry retain their shape.

`system/apps/shell/config/defaults/theme.js`, the shell preset and `config/shell/config/theme.json` ship the same defaults. Personal settings remain under `~/.config/enclosure/shell/config/theme.json`. `Styling.fontSize()` supplies relative typography and `Styling.spacing()` scales layout gaps against a 14px reference. Use these helpers for new shell widgets, shared semantic colors for surfaces and `Styling.radius()` for panel corners.

Shell QML and personal theme settings hot reload; no service restart is required.
