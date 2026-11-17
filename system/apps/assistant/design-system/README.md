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

In the shell, use `ContentText` for animated lyrics and typing glyphs. It follows the selected system/theme font with scalable Qt rendering and unhinted metrics; keep `StyledText` for static labels. Typing pagination preserves fractional glyph advances and clears cached widths after font metrics change, so proportional and monospace fonts use the same measurements as the renderer.

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
Monolith uses clean continuous slabs with a fine neutral rim, a short primary-colored upper accent and a smaller secondary-colored lower accent. Its center stays plain; inset surfaces omit colored marks.
Blueprint uses square corners, wire controls, major and minor drafting grids, perimeter measurement ticks, registration targets and inset frames.
Terminal Hardware uses double machined bezels, cooling vents, slotted screws, recessed display scanlines and raised mechanical controls.
Their fonts are Noto Sans, JetBrains Mono and DejaVu Sans Mono respectively.
Botanical Archive has been removed. Saved selections of removed styles fall back through normal configuration validation.

## Terminal rendering

Kitty follows the exported surface palette and opacity as well as the selected style's native controls. Monolith uses broad padding, borderless slabs and solid cursors; Blueprint uses fine borders, underlined cursors and ruled tab separators; Terminal Hardware uses heavier borders, inset margins, solid cursors and powerline tabs. Frosted Glass uses fine edges and fading tabs; Tinted uses slanted tabs. Switching styles explicitly resets all managed geometry and cursor settings. The dedicated monospace font and size remain user configurable. Niri continues to supply background blur according to the desktop blur settings. Kitty receives a configuration reload without closing terminal sessions.

## Translucent materials

Glass Vault uses thick stepped blocks, bold corner clamps and deep inset controls. Radar Station uses static bearing scales, partial range arcs, crosshair junctions and segmented controls. Suspended Film uses floating glass sheets, offset edges and quiet contact shadows. All three keep translucent centers, the selected semantic colors and matching native terminal profiles. Selecting one enables shell blur if off and resets the manual transparency override; existing blur location and strength preferences are preserved.

Saved Smoked Acrylic selections migrate to Glass Vault, Glass Console to Radar Station, and Circuit Glass to Suspended Film. Older predecessors migrate directly to the corresponding current theme.

Clear Glass is the final theme-picker entry: restrained translucent panels, fine outer borders, borderless inner layers, gentle top highlights and soft corners. It preserves the selected colors, uses compositor blur and includes a minimal Kitty profile. Focused controls gain definition while semantic action buttons remain opaque.

Frosted Glass uses etched double rims, broken highlights, fine perimeter grain and soft corner bloom, with rounded outer and inner surfaces. Tinted uses offset accent planes, open-corner frames, layered color bands and cut accent tabs. Both keep translucent layers, readable semantic action colors and their native terminal profiles; selecting either enables shell blur if it was off. All decorative details are static and concentrated at the perimeter.

Glass Vault follows the corner-radius setting: clamps, inset seams and the lower glass lip use concentric rounded paths and repaint as the actual surface radius changes. Square and oversized radii are clamped to the available surface dimensions.

Every theme now follows the shared corner-radius setting. Inset frame lines use concentric radii; canvas decorations repaint during changes, and corner brackets and attachment points follow the actual clipped surface geometry.

Terminal Hardware uses concentric bezel grooves and recessed cooling louvers. These details stay at the perimeter, adapt to the shared corner radius and remain static.

Architectural refinement: Suspended Film now uses floating offset glass sheets and contact-shadow edges, replacing tension cables and bindings. Monolith uses quiet continuous surfaces and restrained palette-colored edge accents. Both preserve selected colors and radius behavior; Terminal Hardware remains unchanged.

## Material themes

Canopy, Orbital and Metropolis are the first three theme-picker entries, in that order.
Canopy uses an architectural fabric roof with scalloped catenary spans, soft palette-tinted shading and a quiet lower shadow. Bar surfaces simplify this to one shallow fabric sweep and faint shading without a lower seam. The assistant toolbar uses a more sculpted fabric canopy: a highlighted draped hem, a soft accent glow confined to the header. Each opening randomly chooses one of six silhouettes with one to five fabric spans, including an asymmetric three-span arrangement; repainting and resizing preserve the current choice. It retains consistent 36px controls and filled selected menu/pin states. It uses DejaVu Sans Mono.
Orbital uses elliptical orbit tracks and satellite points around recessed glass, with a deterministic star field distributed across the full panel. Star brightness and size vary subtly; stars remain static behind content. It uses JetBrains Mono.
Metropolis uses overlapping setback facades, sparse illuminated windows, slender mullions and a soft reflected-sky band with two fading cloud banks along the upper edge. Glass and facade fills follow the selected background, architectural lighting uses primary, and windows use tertiary. No blue, amber or other fixed theme colors override the selected palette. The former full-panel drafting grid and neon sign bands are removed. Architectural decoration stays around the perimeter; static windows vary by floor and building.
Canopy, Orbital and Metropolis use 62%, 68% and 64% opacity for outer panels, respectively, with lighter inset and nested surfaces. Focused surfaces retain stronger fills, while text and semantic action buttons keep their existing opacity. The same surface values apply across the shell, assistant, media app and native application palette exports.
All three use static technical details, semantic palette colors and visible surface hierarchy. Marks are decorative, with no invented telemetry.
All three preserve selected semantic action colors, readable centers, compositor blur, native Kitty profiles and the shared corner radius. Material layers clip to rounded surfaces; Clear Glass remains last.

## Material detail refinement

The remaining nine themes share the same level of material detail as Canopy, Orbital and Metropolis. Glass Vault adds refractive grazing bands behind its rounded clamps. Radar Station adds soft scope illumination and radial divisions to its etched bearing scales. Suspended Film separates floating sheets with curved grazing reflections. Monolith keeps a clean face with small palette-derived edge accents. Blueprint includes a small architectural truss drawing within its ruled sheet. Terminal Hardware adds brushed upper-bezel lines and recessed panel seams. Frosted Glass grows branching crystals from the upper rim. Tinted layers fading colored-glass planes at its upper edge. Clear Glass keeps restrained grazing reflections and a lower meniscus.

Details use selected semantic palette colors and static geometry. Glass layers clip to the shared rounded frame; inset surfaces retain simpler decoration. Clear Glass remains the final entry. No theme imposes a new palette, and native application export colors remain derived from the selected palette.

## Metropolis bar

The collapsed bar uses a dedicated shallow city cornice: a miniature skyline and sparse lit windows in the bottom eight pixels, a softly illuminated roofline and stepped end caps. It follows the selected background, primary and tertiary colors. Expanded panels retain the full facade and cloud treatment. The finish is static, clips to the bar corners and repaints when the bar expands or collapses.

## Settings navigation

Shell settings use wrapping category tabs at the top, plus page shortcuts above the full-width scrolling controls. Search remains available across categories and shows guidance when there are no matches. Theme previews choose their column count from the available grid width; labels wrap and cards grow to keep longer names visible in narrow windows.

Theme & appearance has a second row of tabs: Style, Colors, Typography, Effects, and Panels & widgets. Each tab shows its own controls directly under visible headings, without accordion headers. Search and legacy links select the matching tab and scroll to the requested controls. The full-width content area scrolls independently beneath the tabs; theme previews appear only in Style. Standalone panels used for indexing keep all sections available.

The terminal bonsai lifts wood and ceramic shading as exported surface opacity falls, keeping the trunk grain and bowl visible over wallpaper. Opaque surfaces retain their subdued materials; foliage and enamel accents keep their theme colors.

The bonsai sits in a glass terrarium with a subdued rounded line frame softly tinted by the theme primary color, aligned to the fill and a few reflections in the empty side panes. The panel uses a uniform backing tinted twelve percent darker than the exported theme background to separate the artwork from transparent terminal wallpapers, with no colored sky tint. Celestial placement and lighting follow local civil time. A large shaded sun disc or solid shaded crescent sits inset in an upper glass corner with sparse night stars and broken mist strokes, confined to empty cells. The sun occupies the left corner from 06:00–12:00 and the right from 12:00–18:00; the moon occupies the left from 18:00–00:00 and the right from 00:00–06:00. The solid crescent opens toward the tree from either side, with cool-blue to pearl-silver shading across its opaque body. The sun and moon share the same thirteen-column, seven-row solid half-block silhouette and curved edges. The sun keeps the full disc with an ivory-to-amber radial gradient; it warms toward copper near sunrise and sunset. Where the tree eclipses the sky, a narrow dark contour separates solid celestial shapes from fine foliage and branches; restrained warm daylight or cool moonlight lifts the overlapping tree material without changing its glyphs or theme hue. After growth, the panel samples local time every 30 seconds, so corner placement and sky lighting follow the clock while the first prompt is idle. Fish stops the worker before executing a command or exiting, and resizing stops it as well; the final frame then stays in scrollback. The cycle uses fixed 06:00–18:00 daylight hours and does not require location access. In Kitty, a single rounded PNG mask draws the darker theme background with the exported theme opacity and a crisp primary rim behind the text. The translucent center lets the terminal’s existing compositor blur show through; the rim stays crisp. Opaque themes retain an opaque backing. Its transparent exterior follows the curve exactly, including the top edge, without full-cell background spill or interior seams. Glass decoration stays character based: a staggered cluster of `╱` glyphs and two broken horizontal `─` glints. The diagonal cluster uses a longer diagonal glint, a variable parallel echo and an optional short fragment. Each new terminal selects one of three fixed anchors—upper shoulder, middle side or lower corner—then independently varies streak length, echo length, horizontal spacing, vertical stagger and fragment presence within that anchor’s safe bounds; the seeded layout stays stable between redraws, and the diagonal cluster chooses either side independently of the sun or moon, subject to artwork clearance. If growing artwork blocks its current anchor, it yields to another safe anchor. Horizontal glints choose among six fixed edge anchors, with varied lengths and gaps. Each composition randomly uses two or three groups: two split one per pane, while three split two on one pane and one on the other. The streak side and optional third group’s side vary independently with the seed. A layout that cannot fit safely on both sides is omitted as a whole. Every complete group is checked against the artwork and other groups with a one-cell clearance; blocked groups try another anchor or are omitted rather than clipped or overlapped. The central backing stays plain theme background. Narrow cool reflection ribbons and twin laminated seams shade the outer side panes without crossing the artwork. In Kitty, the charcoal base projects one and a half character cells beyond each glass wall when the terminal is at least 61 columns wide. Its backing image gains one column on each side while the glass and artwork retain their position and size; narrower terminals keep the compact half-cell overhang. The charcoal base has three visible steps: a narrow upper ledge, a wider middle tier with a restrained upper highlight, and the widest dark bottom foot, stepping outward toward the floor. The upper tier starts flush with the glass walls and chamfers inward into its narrower neck, with a short rim reflection carrying into the metal seat. Each tier has its own rounded outline and a pronounced setback of roughly half a character cell. All tier faces share one deep charcoal color beneath a single subdued upper highlight; the silhouette defines the steps, with clearance below the base inside the existing frame height. The ceramic pot has no solid body fill; its outline and decorative enamel sit over the shared terrarium background. The ceramic bowl closes with a slightly heavier rounded baseline that joins its tapered sides, with downward joints connecting two short solid feet that flare gently outward into flat soles with softly rounded corners. Kitty draws the feet directly in the backing image, using the ceramic foot color and a restrained side highlight; text terminals use solid wedge glyphs. Its floor meets the ceramic foot baseline with a soft contact shadow, seating the pot on the bottom surface. Details stay near the edge; the neutral center remains clear behind the tree and celestial bodies. The graphic scrolls with the terminal content; text rendering uses the existing 59-column, 26-row footprint, with the wider Kitty base using a 61-column image when space permits. Other terminals retain a rounded text frame and darker theme background cell backing; text cells cannot express per-cell alpha. It is restored after foreground changes and reset outside the frame and before the prompt. Plain output stays uncolored; the case preserves the 59-column, 26-row animation footprint.

Zen browser chrome uses primary containers for selected tabs, URL focus and menu highlights, secondary containers for tab and toolbar hover states, and tertiary accents for workspace/new-tab controls and download progress. These exports preserve the selected glass opacity and apply on the next browser launch.

Celestial design references: [wttr.in’s compact weather drawings](https://github.com/chubin/wttr.in#usage), [ASCII Art Archive sun gallery](https://www.asciiart.eu/nature/sun), and [crescent gallery](https://www.asciiart.eu/space/moons). The bonsai drawings are original compositions using crescent silhouettes and negative space from these references; no external artwork is bundled.

The bonsai glass enclosure is flat and front-facing, with a low charcoal base directly beneath the pot foot and no roof or perspective lines. The animation uses 59 columns and 26 rows.

Glass Vault shell refinement uses a fine polished bevel, fading upper reflections and slimmer rounded clasps on outer panels. Inner controls retain a single quiet rim; the lower meniscus follows the shared radius. Selected palette colors and translucent centers are preserved.

Glass Vault bar surfaces use a shallow continuous rim and a narrow upper sheen, leaving the compact center clear. Expanded island panels retain the full vault treatment; switching between them repaints the material.

Monolith, Blueprint and Terminal Hardware carry their material treatments into bars as well as panels. Monolith has a plain face, a fine rim and restrained primary and secondary edge accents. Blueprint's major and minor rules fade beneath the content and strengthen toward the sheet edges. Terminal Hardware adds a brushed upper shoulder inside its clipped housing. These finishes remain static, preserve semantic colors and share the same treatment in shell, assistant and media surfaces.

Monolith keeps its surfaces free of grain, mineral seams and carved facets. Terminal Hardware uses recessed rack mounting slots, cooling louvers, diagonal grip cuts and a segmented lower retention rail. Their surface geometry remains distinct at compact bar sizes; decorations stay at the perimeter and follow the selected palette and rounded clipping frame.

Canopy keeps uninterrupted fabric hems: upper support ribs and the randomized assistant header’s short vertical attachment marks are removed. Fabric silhouettes, soft shading and the stable variation per opening are preserved.

Glass Vault corner clasps sit on the inset bevel with matching concentric radii, short tangent arms, rounded ends and a soft translucent seat beneath a fine highlight. Their reach is limited at compact and pill-shaped sizes. The lower reflection is centered between the mounts instead of climbing one side of the frame.
