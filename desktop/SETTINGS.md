# Shell settings

The sidebar combines settings into five categories. Related pages appear as tabs
above the content, so switching pages keeps the category selected:

| Category | Pages |
| --- | --- |
| Personalization | Appearance, Shell |
| Desktop | Display, Keyboard shortcuts, Window rules |
| Connections & sound | Network, Bluetooth, Sound |
| System | System information, weather and effects |
| Apps & integrations | Assistant, GitHub |

Search opens individual settings and subsections directly. Clearing search keeps
the current page selected in its category. Section IDs remain stable for saved
selections and links from elsewhere in the shell.

Personalization → Appearance → Transparency and blur contains two saved sliders:

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
