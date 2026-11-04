# Dweebo theme

Use Dweebo as the visual standard for Enclosure and new projects: shared semantic colors, JetBrains Mono at 14px, 16px corner radius, tinted surfaces, 36px buttons and 48px inputs. Keep labels visible, provide keyboard focus, and respect reduced motion.

## Web projects

Copy this directory into the project and load `components.css`. Put `class="dweebo"` on the app root. Use semantic buttons, labels and inputs; add `dw-primary` for the main action, `dw-danger` for destructive actions, and `dw-field` for text inputs. See `preview.html` for the component gallery. The scope prevents affecting unrelated UI.

`node export.mjs` regenerates `tokens.css` from the assistant source when working in this repository. The exported CSS works independently with no runtime dependency. It uses portable Dweebo fallback colors, not personal wallpaper state. Override palette and surface CSS variables together to supply a different wallpaper palette. JetBrains Mono must be available locally or bundled by the consuming project with its license; monospace is the fallback.

## QML projects

Enclosure shell and Dweebo already use `modules/theme/Colors.qml`, `Styling.qml`, and `ShellStyles.js`. Reuse `StyledText`, `SearchInput`, `ToggleButton`, and `StyledRect` from `modules/components` within their Quickshell module context. Use `Styling.srItem()` and surface variants rather than literal colors. These components depend on `qs.config` and the theme/services modules; they are not standalone QML imports.

## Source of truth

The exporter derives font, size, radius, motion and color values from Dweebo's existing sources and computes tinted surfaces using its actual `ShellStyles.surface` function. The web adapter supplies native HTML interaction states; it is not a pixel identical Qt renderer. Regenerate tokens after changing the assistant defaults and review the gallery before adoption.

## Color and surface variants

Set `data-theme="black"` or `data-theme="white"` on the `.dweebo` root for neutral dark or light styling, including monochrome buttons, fields, text and error states. Omit it for the original color palette. These portable monochrome adapters use neutral semantic roles; they are not exports of a personal wallpaper or Matugen scheme.

Set `data-style="colorful"`, `glass`, `quiet`, or `dithered` for Tinted, Transparent, Opaque, or Dithered surfaces. All twelve combinations are generated using Dweebo's surface function, including surface opacity. The CSS dither is an approximation of the Qt shader. The preview selectors apply variants to every component together. Custom styling can override CSS variables; no fixed custom preset is exported because Dweebo's custom mode depends on saved user settings.

Example: `<body class="dweebo" data-theme="white" data-style="quiet">`.

## Dropdowns

Single-choice selects inherit themed borders, spacing, arrows, hover and keyboard focus. Browsers supporting `appearance: base-select` also receive a rounded menu with padded rows, a selected checkmark and themed selection. Other browsers retain their native option popup. Disabled, invalid and forced color states remain available. Use a visible `<label for="…">` for every select; existing change events work without a JavaScript adapter. The preview includes enabled and disabled dropdowns.

Implementation reference: [Chrome customizable select documentation](https://developer.chrome.com/blog/a-customizable-select).

For consistently themed open menus in Zen/Firefox as well, load `<script src="dropdowns.js" defer></script>`. The adapter enhances existing single-choice selects with a labeled combobox, keyboard navigation, typeahead, selection marks and Escape/outside-click dismissal, preserving native select values and change events. Load it after the markup or with `defer`. Menus are positioned within the component; avoid overflow clipping on ancestors. Reinitialize or extend the adapter when dynamically replacing options.
