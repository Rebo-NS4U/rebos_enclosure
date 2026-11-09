# Reviewed package selection

Reviewed on 2026-10-31 against the bundled Niri, Quickshell, terminal,
assistant and media application source. `core.txt` is the required desktop
selection; `groups.json` holds optional applications. `apps.txt` and `aur.txt`
mirror the union of those groups. The redundant root package inventory has been removed; these files are the installer selection.

Use `./install.sh --profile core` for the core desktop with Thunar,
Kitty/Fish and Neovim. Add groups explicitly, for example
`./install.sh --profile core --groups notes,communication`.
The default full profile selects every optional group. Core does not install a browser;
select the browser group for Zen. Firefox is not installed or used as a fallback. Package changes here
affect future installations; they do not uninstall anything from this computer.

## Night Light

The shell needs `wl-gammarelay-rs` from the AUR for Night Light. Both profiles
select it unless `--no-aur` is used. The session starts it on demand through
D-Bus and supervises it with a user service; no compositor restart is needed.
With `--no-aur`, install this backend separately to enable Night Light.

## Removed from core

| Package | Reason |
| --- | --- |
| archlinux-xdg-menu | No bundled command or configuration uses its menu generator. |
| playerctl | The shell controls media through Quickshell MPRIS. No bundled command uses playerctl. |
| wtype | No bundled command uses keyboard-event injection. |
| python-numpy | No bundled Python source imports NumPy. |
| python-rich | No bundled Python source imports Rich. |
| libadwaita | The GTK apps import GTK4 directly; none imports Adwaita. |
| qt5-graphicaleffects | No bundled QML imports the Qt5 effects module. |
| qt6-shadertools | The payload includes compiled shader files and never runs qsb; rebuilding shaders is development work. |

Pacman may still install a removed entry if another selected package requires it.
This review removes unnecessary explicit requirements, not dependencies required
by the package manager.

## Dependencies deliberately retained

- VLC, its FFmpeg, DVB, FreeType and Lua plugins, and Lua Socket support the bundled media
  browser's VLC session and local control interface. Arch documents Lua Socket
  as the HTTP-interface optional dependency of
  [vlc-plugin-lua](https://archlinux.org/packages/extra/x86_64/vlc-plugin-lua/).
  FreeType supplies the subtitle-font options passed at player startup; without
  it VLC rejects those options and exits before playback.
  The DVB package supplies the MPEG transport-stream demuxer used by HLS anime
  segments; without it VLC can open the playlist but fails before decoding video.
  MPV remains the bundled ani-cli default player.
- Python GObject/GTK4 support the media app and administrator dialog; Pillow
  supports wallpaper processing. FFmpeg supports video thumbnails and wallpapers.
- Fuzzel and cliphist implement clipboard history and project selection.
  Blueman and pavucontrol are opened by the shell's Bluetooth and audio controls.
- Qt5/Qt6 theme and Wayland support, Breeze, image formats, Qt multimedia and
  syntax highlighting support the shipped application settings and QML imports.
- Terminal helpers and fonts match the supplied terminal/editor configuration.
  Base-devel builds the native greeter helpers and optional AUR apps.
  The bonsai greeting uses Python’s standard library.

Optional groups retain Zen, Discord, Spotify/Spicetify/imv, Obsidian,
OBS/scrcpy, development tools, Fastfetch/Flatpak and video wallpapers.
Select only the groups you want; assistant backends still require separate setup.
The default Codex backend uses Node/npm from the development group.

Fresh installs use the shell's bundled default bar, theme, performance,
lockscreen and system settings, with an empty weather location. The snapshot
recipe does not copy those preferences from the source user's live desktop.
The desktop updater preserves preferences already present in the destination
home; it does not reset them to these fresh-install defaults.

## Old machine snapshot

The root inventory no longer reproduces the original machine's installed package
snapshot. It excludes unrelated gaming/overlay tools, printer services, disk and
boot administration tools, debug packages, WARP, Victus-specific software,
duplicate bars/notification daemons/wallpaper utilities, extra fonts and
machine-specific kernel/driver choices. The installer selects GPU drivers and
CPU microcode for the destination; it keeps its existing kernel and bootloader.
The obsolete hardware-specific installer and package snapshots have been removed.

## Qt dialogs and portal registration

Qt6ct uses its default Qt dialogs while retaining the desktop palette, Breeze
style and Papirus icons. Loading GTK dialogs as an additional platform theme
causes duplicate portal registration with Qt 6.12 and Quickshell. Use
`Appearance → Standard dialogs → Default` in Qt6ct if an older personal config
still selects GTK dialogs. This takes effect for newly launched Qt applications;
portal access stays enabled.

The emoji picker uses the core Fuzzel launcher in dmenu mode and wl-clipboard. It does not require the X11 dmenu package. Canceling the menu leaves the clipboard unchanged.

- Calibre supplies `ebook-convert` for the typer’s local MOBI import.
