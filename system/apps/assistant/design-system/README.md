# Dweebo theme

Use Dweebo as the visual standard for Enclosure and new projects: shared semantic colors, JetBrains Mono at 14px, 16px corner radius, tinted surfaces, 36px buttons and 48px inputs. Keep labels visible, provide keyboard focus, and respect reduced motion.

## Web projects

Copy this directory into the project and load `components.css`. Put `class="dweebo"` on the app root. Use semantic buttons, labels and inputs; add `dw-primary` for the main action, `dw-danger` for destructive actions, and `dw-field` for text inputs. See `preview.html` for the component gallery. The scope prevents affecting unrelated UI.

`node export.mjs` regenerates `tokens.css` from the assistant source when working in this repository. The exported CSS works independently with no runtime dependency. It uses portable Dweebo fallback colors, not personal wallpaper state. Override palette and surface CSS variables together to supply a different wallpaper palette. JetBrains Mono must be available locally or bundled by the consuming project with its license; monospace is the fallback.

## QML projects

Enclosure shell and Dweebo already use `modules/theme/Colors.qml`, `Styling.qml`, and `ShellStyles.js`. Reuse `StyledText`, `SearchInput`, `ToggleButton`, and `StyledRect` from `modules/components` within their Quickshell module context. Use `Styling.srItem()` and surface variants rather than literal colors. These components depend on `qs.config` and the theme/services modules; they are not standalone QML imports.

## Source of truth

The exporter derives font, size, radius, motion and color values from Dweebo's existing sources and computes tinted surfaces using its actual `ShellStyles.surface` function. The web adapter supplies native HTML interaction states; it is not a pixel identical Qt renderer. Regenerate tokens after changing the assistant defaults and review the gallery before adoption.
