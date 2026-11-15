# Dweebo theme

Use Dweebo as the visual standard for Enclosure and new projects: shared semantic colors, JetBrains Mono at 14px, 16px corner radius, tinted surfaces, 36px buttons and 48px inputs. Keep labels visible, provide keyboard focus, and respect reduced motion.

## Web projects

Copy this directory into the project and load `components.css`. Put `class="dweebo"` on the app root. Use semantic buttons, labels and inputs; add `dw-primary` for the main action, `dw-danger` for destructive actions, and `dw-field` for text inputs. See `preview.html` for the component gallery. The scope prevents affecting unrelated UI.

`node export.mjs` regenerates `tokens.css` from the assistant source when working in this repository. The exported CSS works independently with no runtime dependency. It uses portable Dweebo fallback colors, not personal wallpaper state. Override palette and surface CSS variables together to supply a different wallpaper palette. JetBrains Mono must be available locally or bundled by the consuming project with its license; monospace is the fallback.

## Theme typography

The theme picker offers Monolith (Noto Sans), Blueprint (JetBrains Mono),
Terminal Hardware and Frosted Glass (DejaVu Sans Mono), and Tinted (DejaVu Sans).
Selecting a style applies its typeface; the font field still allows manual changes.
Legacy styles remain readable for saved configurations but are no longer offered.
These families are supplied by the existing desktop font packages.

## QML projects

Enclosure shell and Dweebo already use `modules/theme/Colors.qml`, `Styling.qml`, and `ShellStyles.js`. Reuse `StyledText`, `SearchInput`, `ToggleButton`, and `StyledRect` from `modules/components` within their Quickshell module context. Use `Styling.srItem()` and surface variants rather than literal colors. These components depend on `qs.config` and the theme/services modules; they are not standalone QML imports.

## Source of truth

The exporter derives font, size, radius, motion and color values from Dweebo's existing sources and computes tinted surfaces using its actual `ShellStyles.surface` function. The web adapter supplies native HTML interaction states; it is not a pixel identical Qt renderer. Regenerate tokens after changing the assistant defaults and review the gallery before adoption.

## Color and surface variants

Set `data-theme="black"` or `data-theme="white"` on the `.dweebo` root for neutral dark or light styling, including monochrome buttons, fields, text and error states. Omit it for the original color palette. These portable monochrome adapters use neutral semantic roles; they are not exports of a personal wallpaper or Matugen scheme.

Set `data-style="colorful"`, `glass`, `quiet`, or `dithered` for Tinted, Transparent, Opaque, or Dithered surfaces. All twelve combinations are generated using Dweebo's surface function, including surface opacity. The Qt dither uses an ordered screen with fixed one-pixel grain and strength-controlled contrast; buttons and borders stay solid. Wallpapers in Original mode use ordered RGB quantization to preserve the full range of hues instead of a reduced dominant-color palette; Normal, Strong and Intense use 2px, 4px and 8px ordered cells with 8, 5 and 4 levels per RGB channel respectively, increasing texture contrast while preserving the overall colors. The CSS dither is an approximation of the Qt shader. The preview selectors apply variants to every component together. Custom styling can override CSS variables; no fixed custom preset is exported because Dweebo's custom mode depends on saved user settings.

Example: `<body class="dweebo" data-theme="white" data-style="quiet">`.

## Dropdowns

Single-choice selects inherit themed borders, spacing, arrows, hover and keyboard focus. Browsers supporting `appearance: base-select` also receive a rounded menu with padded rows, a selected checkmark and themed selection. Other browsers retain their native option popup. Disabled, invalid and forced color states remain available. Use a visible `<label for="…">` for every select; existing change events work without a JavaScript adapter. The preview includes enabled and disabled dropdowns.

Implementation reference: [Chrome customizable select documentation](https://developer.chrome.com/blog/a-customizable-select).

For consistently themed open menus in Zen/Firefox as well, load `<script src="dropdowns.js" defer></script>`. The adapter enhances existing single-choice selects with a labeled combobox, keyboard navigation, typeahead, selection marks and Escape/outside-click dismissal, preserving native select values and change events. Load it after the markup or with `defer`. Menus are positioned within the component; avoid overflow clipping on ancestors. Reinitialize or extend the adapter when dynamically replacing options.

## Progress rails

Use `StandardProgressBar` for linear progress in QML. Its normalized `value` is clamped to 0–1; `activeColor` and `foregroundColor` use semantic theme defaults. The lyrics-style 2px rail includes a gradient, soft bloom, bright leading edge and quarter markers. Slider wrappers retain their existing input and accessibility behavior. Shell, assistant and media package identical copies so each app installs independently; keep these copies synchronized. Vertical sliders rotate the same rail. Shell sliders gently snap pointer drags within three percentage points of the 25%, 50% and 75% positions. Keyboard, wheel and external value updates remain exact so small adjustments can leave those positions.

## Rendered desktop themes

All styles use the selected wallpaper or color preset, including application exports.
Monolith uses sculpted slabs, staggered edge cuts, deep inset seams, diagonal engraving and stepped lower edges.
Blueprint uses square corners, wire controls, major and minor drafting grids, perimeter measurement ticks, registration targets and inset frames.
Terminal Hardware uses double machined bezels, cooling vents, slotted screws, recessed display scanlines and raised mechanical controls.
Their fonts are Noto Sans, JetBrains Mono and DejaVu Sans Mono respectively.
Botanical Archive has been removed. Saved selections of removed styles fall back through normal configuration validation.

## Terminal rendering

Kitty follows the exported surface palette and opacity as well as the selected style's native controls. Monolith uses broad padding, borderless slabs and solid cursors; Blueprint uses fine borders, underlined cursors and ruled tab separators; Terminal Hardware uses heavier borders, inset margins, solid cursors and powerline tabs. Frosted Glass uses fine edges and fading tabs; Tinted uses slanted tabs. Switching styles explicitly resets all managed geometry and cursor settings. The dedicated monospace font and size remain user configurable. Niri continues to supply background blur according to the desktop blur settings. Kitty receives a configuration reload without closing terminal sessions.

## Translucent materials

Smoked Acrylic uses diagonal reflection bands, laminated edge hairlines, translucent sheets and recessed wells. Glass Console uses segmented chassis rails, vented housings, slotted fasteners and translucent inset display wells. Circuit Glass uses printed circuit routes, junction pads, connector teeth and a subtle dot lattice on blurred glass. Each keeps the selected palette and has a matching native Kitty profile. Selecting one resets the manual transparency override to its material default and enables shell blur if blur was off. Existing desktop blur location and strength choices are preserved; Niri supplies the actual background blur. The global transparency slider remains available after selection.

Condensation and Liquid Glass selections migrate to Glass Console; Optical Instrument and Prism Glass selections migrate to Circuit Glass.

Clear Glass is the final theme-picker entry: restrained translucent panels, fine outer borders, borderless inner layers, gentle top highlights and soft corners. It preserves the selected colors, uses compositor blur and includes a minimal Kitty profile. Focused controls gain definition while semantic action buttons remain opaque.
