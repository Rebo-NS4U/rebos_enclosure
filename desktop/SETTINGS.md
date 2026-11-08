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
  restores each style's defaults. The bar follows this transparency automatically;
  app window transparency stays separate.
- Where blur applies selects Everywhere, Shell panels only, or Off independently
  of strength and transparency. Turning blur off preserves the saved strength.
- Blur strength uses one scale for Everywhere and Shell panels only. Lighter
  glass sets the slider to 22%; Full glass sets it to 50%. Other values show Custom.
  Presets preserve transparency and blur location. Choosing a preset while blur
  is off enables it Everywhere. 0% keeps a small blur; choose Off to remove it.
  The old lighter mode is converted to the shared scale when this panel loads,
  preserving approximately its previous radius.

Changes apply through normal configuration hot reload; no service restart is
required. Fonts and corners contains its own controls without duplicating the
Theme style editor.

Validation: `python3 desktop/tests/test_settings_clicks.py` exercises navigation,
slider persistence and background opacity in an isolated Quickshell window.
`python3 desktop/tests/test_desktop_blur.py` validates generated Niri configuration
at minimum, middle and maximum strength for each mode.

Bar opacity follows the active theme background and shell transparency override.
Bar borders and clock accents use the theme's border and highlight colors, so
palette and style changes update them automatically. The separate bar opacity
and accent sliders have been removed; older saved values are retained for
compatibility but no longer override the theme.

Shadows now render as a separate shape behind surfaces that explicitly enable
shadows, leaving text crisp. The Shadows page provides a live preview and saves
opacity, softness, color and signed offsets without overwriting saved values on
load. App window shadows remain compositor settings.

Shell sliders share round 16px handles, themed 4px tracks, keyboard focus and
disabled styling. Settings, palette opacity and reading controls use the same
appearance. Arrow keys adjust values; Home and End reach their limits. Existing
media controls retain their release-to-seek behavior and animated waveform.
