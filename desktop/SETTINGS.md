# Shell settings

The sidebar puts Appearance and Shell first, followed by Display, Keyboard
shortcuts, Window rules, Network, Bluetooth, Sound, System, Assistant and GitHub.
Section IDs remain stable for saved selections and search links.

Appearance → Transparency and blur contains two saved sliders:

- Shell background transparency adjusts menu and panel backgrounds from opaque
  (0%) to transparent (100%) while preserving text opacity. Use theme transparency
  restores each style's defaults. This override does not change app windows or the
  bar's separate appearance settings.
- Blur strength adjusts Niri blur where the selected blur mode permits it. The
  lowest setting keeps a small blur; choose Blur off to remove it. Lighter glass
  uses fewer passes. The default strength preserves the previous preset radius.

Changes apply through normal configuration hot reload; no service restart is
required. Fonts and corners contains its own controls without duplicating the
Theme style editor.

Validation: `python3 desktop/tests/test_settings_clicks.py` exercises navigation,
slider persistence and background opacity in an isolated Quickshell window.
`python3 desktop/tests/test_desktop_blur.py` validates generated Niri configuration
at minimum, middle and maximum strength for each mode.
