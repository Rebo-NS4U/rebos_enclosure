# Instrument shell theme

The shell uses an instrument-panel direction: layered graphite surfaces, precise typography and restrained status accents. It retains Dweebo's semantic colors and shared QML components. Select **Instrument** in Theme settings; the other surface styles remain available.

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
