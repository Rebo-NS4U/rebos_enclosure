# Enclosure menu theme

System Theme Playground is the reference for shell and assistant menus. They follow the active palette, font and roundness, including glass and dithered surface rendering through StyledRect.

SettingsComboBox owns settings, wallpaper and Anime Streamer dropdown styling: 48px controls, 42px menu rows, selected marks, subtle hover, visible keyboard focus and disabled opacity. Preserve textRole/valueRole and onActivated behavior when reusing it. WallpaperChoice is a compatibility wrapper.

OptionsMenu owns context menus in both applications, using popup surfaces, 40px rows, keyboard highlights and disabled actions. BarPopup owns tray and bar-attached menu surfaces. Standalone launcher, power, notes, model and backend popups use the same configured corner metric. Rich model/backend rows retain their descriptions and actions.

Run `python3 -m unittest discover -s desktop/tests -p test_menu_theme.py` to check popup opening, keyboard selection, model roles and disabled actions without touching the desktop session. Toolkit application menus are handled separately by the system theme exporter.
