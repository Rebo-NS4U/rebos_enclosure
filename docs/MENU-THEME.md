# Enclosure menu theme

System Theme Playground is the reference for shell and assistant menus. They follow the active palette, font and roundness, including glass and dithered surface rendering through StyledRect.

SettingsComboBox owns settings, wallpaper and Anime Streamer dropdown styling: 48px controls, 42px menu rows, selected marks, subtle hover, visible keyboard focus and disabled opacity. Preserve textRole/valueRole and onActivated behavior when reusing it. WallpaperChoice is a compatibility wrapper.

OptionsMenu owns context menus in both applications, using popup surfaces, 40px rows, keyboard highlights and disabled actions. BarPopup owns tray and bar-attached menu surfaces. Standalone launcher, power, notes, model and backend popups use the same configured corner metric. Rich model/backend rows retain their descriptions and actions.

Run `python3 -m unittest discover -s desktop/tests -p test_menu_theme.py` to check popup opening, keyboard selection, model roles and disabled actions without touching the desktop session. Toolkit application menus are handled separately by the system theme exporter.

ReGreet uses `system/greeter/regreet.css.in` and `system/bin/regreet-sync`. The exporter reads the effective desktop palette plus shell font, size and roundness. It applies the playground components to the login card, entries, session/account dropdowns and power actions. Wallpaper and login layout are retained; the previous independent glass texture is removed. The existing sync timer picks up geometry changes within 30 seconds. Changes appear when the greeter next opens; synchronization does not restart greetd or the desktop session. Run `test_greeter_sync.py` for rendering, metric updates, font sanitization, GTK4 CSS parsing and wallpaper preservation checks.

Outer assistant and Settings surfaces use Config.roundness directly. Niri retains a 16px startup fallback; its final generated theme rule supplies the current shell radius for every window and popup. Application rules must not override corner geometry with fixed values. `test_theme_radius.py` verifies changed, square, invalid and missing theme metrics.

The login clock uses a large accent-colored time, a softly tinted date badge, and a divider above the sign-in heading. Clock styling inherits the active palette, font family and corner radius; no greeter restart is needed.

The shell has one full-width bar with the island’s context, clock, workspaces, notifications and expanding panels. Volume, brightness and battery retain the continuous bar’s circular meters; tray and audio-format indicators remain available. Volume opens the sound panel, brightness opens its slider, and battery opens the battery panel. “Keep bar visible” controls auto-hide. Legacy continuous settings migrate to this shared layout with visibility pinned; existing island visibility preferences remain intact. Run `test_merged_bar.py` for full-width geometry, meter placement and panel expansion at 1920 and 1280 pixels.
