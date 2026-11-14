# Shell theme

Frosted Glass is the default for new installations, with 16px corners and shared typography. Existing preferences are preserved during updates. Instrument remains selectable with its layered graphite surfaces, precise typography and restrained status accents. It retains Dweebo's semantic colors and shared QML components. Select **Instrument** in Theme settings; the other surface styles remain available.

## Visual decisions

- Depth, rather than bright outlines everywhere, separates the panel, raised cards and inset controls. The palette follows the wallpaper; the depth hierarchy uses foreground luminance so it survives changes of accent color.
- JetBrains Mono at 14px keeps names and values readable. Secondary labels are smaller and muted. The dashboard clock anchors the overview; a spaced section heading groups controls beneath connection status.
- Connection cards use neutral surfaces. Active icons and connection values carry the accent, leaving saturated fills for deliberate actions. Hover uses a raised surface and accent outline.
- A 440px dashboard, 18px outer padding and 14px group gaps give dense controls breathing room. Shared 4px corners preserve the technical character. Circular gauges retain their shape.
- Press feedback is a small movement rather than a large bounce. Shared motion settings still control duration and reduced motion.

`system/apps/shell/config/defaults/theme.js`, the shell preset and `config/shell/config/theme.json` ship matching defaults. Personal settings live under `~/.config/enclosure/shell/config/theme.json`. Font size, corner radius, animation and surface style remain adjustable.

## Extending the design

Use `StyledRect` semantic variants rather than fixed fills. `Styling.fontSize()` supplies relative typography; `Styling.spacing()` scales layout gaps against the 14px reference. Use dedicated icon fonts, shared semantic colors and `Styling.radius()` for panel corners. Add information hierarchy before adding decoration. Maintain visible labels and keyboard focus.

The Instrument surface hierarchy is exported through `ShellStyles.appPalette()` to native theme integrations. Tests cover distinct depth levels, 4.5:1 foreground contrast in dark and light palettes, transparent roles and matching application exports.

This pass establishes the shared surfaces and dashboard composition. Launcher row composition, settings navigation, notifications and other individual views can be refined further against the same direction. QML and personal settings hot reload; no service restart is required.

## Bar

Instrument mode gives the island bar the same 4px corners, opaque background and subtle frame as its dashboard. A 40px height leaves room around the clock and status controls. The clock uses a raised card surface; hover controls use matching corners and restrained press feedback. Active workspace outlines and charging indicators use the primary accent, low battery uses the error role, and muted audio recedes. Other bar appearances retain their existing shape and behavior.

## Frosted Glass

Choose **Frosted Glass** in Settings → Appearance → Theme style for the OCR
menu’s glass treatment throughout the shell. Shared menus, panels, bar surfaces
and controls use a three-stop highlight, translucent tinted surfaces, fine
foreground borders and corners controlled by Appearance → Fonts and corners.
The corner radius setting applies to Frosted Glass just as it does to the other
styles, including zero for square corners. Text and semantic action colors
remain solid; switching styles does not overwrite the personal corner preference.

Selecting this style uses 32% background transparency and enables shell blur if
blur was off. Existing blur strength and enabled scope are preserved; both can
be adjusted under Transparency and blur. The compositor provides live backdrop
blur rather than taking screen captures. Theme transparency overrides still work.
Native app integrations receive the matching surface palette where supported.
`qs ipc -p ~/.config/quickshell call theme status` reports the active style,
opacity, corner radius and blur settings. Selecting an installed theme changes
the appearance live without restarting the panel or active apps.

Kitty exports use six-digit RGB colors. Translucent palette colors (including
Frosted Glass borders) are composited against the terminal background; terminal
transparency remains in Kitty’s separate `background_opacity` setting.

## Shared sizing and terminal styling

Frosted bar corners follow the saved radius while collapsed and expanded, including zero. Bar height and meter symbols scale with the Appearance font size. Fish uses neutral text, readable muted details and semantic status accents from the effective palette; it reloads colors at each prompt. New Fish sessions load the updated prompt layout. Kitty follows the monospace font and size (converted from pixels to points), alongside its exported theme colors and app opacity. Adjust these in Appearance → Fonts and corners; shell transparency and blur remain under Transparency and blur.

## Bar menus

Bar menus share a 36px back action with keyboard focus, an accessible name and a tooltip. Clearer titles, inset gutters and a fine header divider distinguish navigation from menu content. Menu widths and gutters follow the configured type size; Wi-Fi, Bluetooth and Alerts leave more room for scrollable lists. Sound and Microphone use 44px device rows with neutral labels, accented selection outlines and check marks rather than solid accent fills. All surfaces, focus outlines, fonts and corners continue to use the active theme settings.

The terminal bonsai derives its foliage colors from the terminal palette, with seed-specific wood colors and leaf-colored ceramic patterns, with no background fill or visible frame. Whitespace centers the tree; reserved blank rows keep greeting animation and prompt placement stable. New greetings follow Kitty theme changes.

Wood palettes repeat for the same seed and leaf palette throughout growth. The wallpaper primary accent guides the choice: green crowns always use brown wood and red crowns always use dark red wood; cool crowns use birch or violet ash, while pink crowns use rosewood. The wood follows the wallpaper primary hue, just like the visible leaves. A subtle reflected leaf tint unifies the wood, with dark bark, wood and restrained highlights. Semantic ANSI colors such as terminal green never determine the wallpaper hue.

The crown is the visual focus: the wallpaper primary and any distinct secondary hue use the highest saturation and brightness. Ceramic patterns repeat the vibrant crown colors on a muted pot body. Seeded wood, blossoms and shoots use quieter supporting tones below the foliage’s brightness. Neutral terminal palettes retain neutral foliage. All materials use foreground colors without a background fill.

Trunks use broad, seed-stable grain bands in related dark wood tones. The narrow scar uses a blend of bark and heartwood instead of an extra-dark slit; its existing shape and growth remain intact.

## Wallpaper leaf accents

Wallpaper-driven Matugen palettes use the terminal bonsai crown’s chroma and
neighboring leaf hues for dark-mode primary, secondary and tertiary accents.
Each wallpaper is extracted afresh; neutral themes remain neutral. When Matugen
finds a distinct, colorful second source (35–180° apart), including blue/green
pairs, it becomes the secondary accent with
its containers and fixed colors in both modes. Near-neutral, dark and similar
candidates are ignored; single-hue images keep the neighboring leaf shades.
This is a deterministic color-harmony heuristic, not a subjective aesthetic judgment. Matugen still
generates surfaces and light-mode colors. Accent text uses black or white for
contrast. Static color presets bypass wallpaper generation; select a Matugen
scheme to resume automatic updates. Wallust remains the fallback when Matugen
is unavailable.

The terminal bonsai reads the current effective accents on every render. When
primary and secondary are distinct, its foliage uses both hues and the ceramic
inlay repeats the secondary. Existing printed terminal output stays as drawn;
new greetings and animation frames use the current palette.

Paired bonsai foliage blends both accents in linear RGB light across every
leaf cluster, with intermediate shades and restrained saturation. The main
foliage groups retain 85% of their original accent, with a softer midpoint shade. This softens
color boundaries while retaining leaf highlights and the current wallpaper hues.

Mature foliage uses pointed leaf faces around fuller interior clusters, with
sparse small tips on the rim. Seed-stable dapple places highlights on the upper
shoulder and shadows beneath each spray without changing canopy geometry.

The finished specimen shares upper-left lighting across the foliage, wood and
ceramics. Deeper leaf undersides reveal spray depth; slower grain highlights
the left wood face. A glazed pot rim, shaded sides and foot, and restrained
inlay glints keep the crown dominant. Growth positions, framing and pot motifs
remain stable throughout animation.
