.pragma library

var styles = [
    {id: "canopy", label: "Canopy", font: "DejaVu Sans Mono", description: "Overlapping tree boughs with two-tone leaf sprays across the window."},
    {id: "orbital", label: "Orbital", font: "JetBrains Mono", description: "Orbital space: elliptical tracks, satellite points, fixed stars and recessed glass."},
    {id: "metropolis", label: "Metropolis", font: "DejaVu Sans", description: "Stepped towers and lit windows rise behind an elevated highway."},
    {id: "glass-vault", label: "Glass Vault", font: "Noto Sans", description: "Thick glass blocks, rounded clamps, refractive light bands and deep inset controls."},
    {id: "radar-station", label: "Radar Station", font: "DejaVu Sans", description: "Etched bearing scales, radial divisions and softly illuminated scope glass."},
    {id: "suspended-film", label: "Suspended Film", font: "DejaVu Sans Mono", description: "A thin translucent membrane bows between two pin mounts."},
    {id: "monolith", label: "Monolith", font: "Noto Sans", description: "Layered slate with a diagonal fault, tapered mineral seams and exposed edges."},
    {id: "blueprint", label: "Blueprint", font: "JetBrains Mono", description: "Architectural drafting sheets, truss details, ruled scales and wire controls."},
    {id: "terminal-hardware", label: "Terminal Hardware", font: "DejaVu Sans Mono", description: "Flat machined panels, inset bezels and sparse cooling vents."},
    {id: "frosted", label: "Frosted Glass", description: "Satin glass with a sandblasted margin and a fine polished rim."},
    {id: "colorful", label: "Tinted", description: "Layered colored glass planes, offset frames and fading accent reflections."},
    {id: "clear-glass", label: "Clear Glass", font: "Noto Sans", description: "Clear glazing with grazing reflections, fine highlights and a subtle lower meniscus."}
];

function mix(a, b, amount) {
    function rgb(hex) {
        var value = hex.replace("#", "");
        if (value.length === 8) value = value.slice(2);
        return [parseInt(value.slice(0,2),16), parseInt(value.slice(2,4),16), parseInt(value.slice(4,6),16)];
    }
    var x = rgb(a), y = rgb(b);
    return "#" + x.map(function(channel, i) {
        return Math.round(channel * (1 - amount) + y[i] * amount).toString(16).padStart(2, "0");
    }).join("");
}

function contrast(a, b) {
    function luminance(hex) {
        var channels = hex.slice(-6).match(/../g).map(function(c) {
            var v = parseInt(c, 16) / 255;
            return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
        });
        return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
    }
    var x = luminance(a), y = luminance(b);
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

function dotColor(fill, text, amount) {
    // Texture must stay readable even on bright accent buttons and light themes.
    for (var i = 0; i < 12; i++) {
        var color = mix(fill, text, amount);
        if (contrast(color, text) >= 4.5) return color;
        amount *= 0.75;
    }
    return fill;
}

// Every surface uses one hierarchy, with the wallpaper palette supplying all color.
function ditherCellSize(strength) {
    // Fixed logical-pixel grain avoids chunky patterns and fractional cell sizes.
    return 1;
}

function surface(style, variant, p, ditherStrength) {
    var strength = Number.isFinite(ditherStrength) ? Math.max(0, Math.min(100, ditherStrength)) : 20;
    var colorful = style === "colorful", dithered = style === "dithered", quiet = style === "quiet" || dithered;
    var tint = colorful ? 0.10 : (quiet ? 0.015 : 0.035);
    var base = mix(p.background, p.foreground, dithered ? 0.025 : 0.035);
    var fill = mix(base, p.primary, tint), item = p.foreground;
    // One glass opacity for menus, panels and their popup surfaces.
    var glassOpacity = 0.78;
    var opacity = quiet ? 1 : 0.92;
    var border = [mix(base, p.primary, dithered ? 0.24 : (colorful ? 0.32 : 0.18)), 0];
    switch (variant) {
    case "transparent": opacity = 0; break;
    case "barbg": opacity = dithered && strength > 0 ? 1 : 0; break;
    case "bg":
        opacity = quiet ? 1 : glassOpacity;
        border[1] = 1; break;
    case "popup":
        opacity = quiet ? 1 : glassOpacity;
        border[1] = 1; break;
    case "bar": case "pane": case "surface": case "surfaceContainer":
        fill = mix(base, p.primary, tint + (dithered ? 0.045 : 0.02));
        opacity = quiet ? 1 : glassOpacity; break;
    case "internalbg":
        fill = mix(p.background, p.primary, tint * 0.6);
        opacity = quiet ? 1 : 0.72; break;
    case "focus": case "surfaceVariant":
        fill = mix(base, p.primary, colorful ? 0.28 : (dithered ? 0.14 : (quiet ? 0.10 : 0.16)));
        border[1] = 1; break;
    case "primary": case "primaryfocus":
        fill = variant === "primaryfocus" ? mix(p.primary, p.foreground, 0.12) : p.primary;
        item = p.onPrimary; opacity = 1; break;
    case "overprimary": fill = base; item = p.primary; break;
    case "secondary": case "secondaryfocus": fill = p.secondary; item = p.onSecondary; opacity = 1; break;
    case "oversecondary": item = p.secondary; break;
    case "tertiary": case "tertiaryfocus": fill = p.tertiary; item = p.onTertiary; opacity = 1; break;
    case "overtertiary": item = p.tertiary; break;
    case "error": case "errorfocus": fill = p.error; item = p.onError; opacity = 1; break;
    case "overerror": item = p.error; break;
    }
    // Instrument panels separate depth with neutral luminance, reserving
    // saturated fills for deliberate actions and semantic status indicators.
    if (style === "instrument") {
        var depth = 0.075;
        if (["internalbg", "barbg"].indexOf(variant) !== -1) depth = 0.035;
        if (["pane", "bar", "surface", "surfaceContainer", "common"].indexOf(variant) !== -1) depth = 0.12;
        if (["focus", "surfaceVariant"].indexOf(variant) !== -1) depth = 0.19;
        if (["bg", "popup", "internalbg", "barbg", "pane", "bar", "surface", "surfaceContainer", "common", "focus", "surfaceVariant", "transparent"].indexOf(variant) !== -1) {
            fill = mix(mix(p.background, p.foreground, depth), p.primary, 0.025);
            item = p.foreground;
            opacity = variant === "transparent" || variant === "barbg" ? 0 : 1;
            border = [mix(fill, p.foreground, 0.12), ["bg", "popup", "focus", "surfaceVariant"].indexOf(variant) !== -1 ? 1 : 0];
            if (variant === "focus" || variant === "surfaceVariant") border[0] = mix(fill, p.primary, 0.48);
        }
    }
    if (style === "frosted") {
        var outer = ["bg", "popup", "bar", "pane", "surface", "surfaceContainer"].indexOf(variant) !== -1;
        var inner = ["common", "internalbg"].indexOf(variant) !== -1;
        var focused = ["focus", "surfaceVariant"].indexOf(variant) !== -1;
        if (outer || inner || focused) {
            fill = mix(mix(p.background, p.foreground, outer ? 0.12 : 0.065), p.primary, focused ? 0.14 : 0.055);
            opacity = outer ? 0.68 : focused ? 0.84 : 0.48;
            border = [focused ? p.primary : "#40" + p.foreground.slice(-6), 1];
        }
    }
    // Render treatments use semantic palette roles without choosing a color scheme.
    var monolith = style === "monolith", blueprint = style === "blueprint", hardware = style === "terminal-hardware";
    var rendered = monolith || blueprint || hardware;
    var outer = variant === "bg" || variant === "popup";
    var inset = variant === "internalbg";
    var focused = variant === "focus" || variant === "surfaceVariant";
    var neutral = ["bg", "popup", "bar", "pane", "surface", "surfaceContainer", "common", "internalbg", "focus", "surfaceVariant"].indexOf(variant) !== -1;
    var outlineRole = variant.indexOf("over") === 0;
    if (rendered) {
        opacity = variant === "transparent" || variant === "barbg" ? 0 : 1;
        if (neutral || outlineRole) {
            var depth = monolith ? (inset ? 0 : focused ? 0.12 : outer ? 0.035 : 0.075)
                : blueprint ? (inset ? 0.015 : focused ? 0.065 : 0.025)
                : (inset ? 0 : focused ? 0.12 : outer ? 0.085 : 0.045);
            fill = mix(p.background, p.foreground, depth);
            if (!outlineRole) item = p.foreground;
        }
        if (monolith) {
            border = [mix(fill, p.foreground, 0.18), focused ? 2 : inset ? 1 : 0];
            if (focused) border[0] = p.primary;
        } else if (blueprint) {
            // Wire controls retain the selected accent as their ink color.
            if (!neutral && !outlineRole && opacity > 0) {
                item = fill;
                fill = p.background;
            }
            border = [focused ? p.primary : neutral ? mix(p.background, p.foreground, 0.35) : item, focused ? 2 : 1];
        } else {
            border = [mix(fill, p.foreground, inset ? 0.26 : 0.38), focused || outer ? 2 : 1];
            if (focused) border[0] = p.primary;
        }
    }
    // Three distinct structural treatments with translucent centers.
    var vault=style === "glass-vault", radar=style === "radar-station", film=style === "suspended-film";
    if ((vault || radar) && neutral) {
        fill=mix(p.background,p.foreground,inset?0.012:focused?0.07:0.03);
        item=p.foreground;
        opacity=vault?(inset?0.82:focused?0.94:0.70):(inset?0.76:focused?0.92:0.64);
        border=[focused?p.primary:mix(fill,p.foreground,vault?0.36:0.34),vault?2:1];
    }
    if (film && neutral) {
        fill = mix(p.background, p.primary, focused ? 0.14 : inset ? 0.025 : 0.06);
        opacity = focused ? 0.86 : inset ? 0.44 : outer ? 0.58 : 0.50;
        border = [focused ? p.primary : mix(fill, p.foreground, 0.22), outer || focused ? 1 : 0];
    }
    var clearGlass = style === "clear-glass";
    if (clearGlass && neutral) {
        fill = mix(p.background, p.foreground, inset ? 0.01 : 0.025);
        item = p.foreground;
        opacity = focused ? 0.78 : inset ? 0.38 : outer ? 0.52 : 0.32;
        border = [focused ? p.primary : mix(fill, p.foreground, outer ? 0.22 : 0.12), outer || focused || inset ? 1 : 0];
    }
    if (colorful && neutral) {
        fill=mix(mix(p.background,p.foreground,0.025),p.primary,focused?0.14:inset?0.035:0.07);
        item=p.foreground;
        opacity=focused?0.86:inset?0.50:outer?0.74:0.62;
        border=[focused?p.primary:mix(fill,p.primary,outer?0.38:0.20),outer||focused?1:0];
    }
    var canopy=style === "canopy", orbital=style === "orbital", metro=style === "metropolis";
    if (orbital && neutral) {
        fill=mix(p.background,p.foreground,inset?0.005:focused?0.10:outer?0.075:0.045);
        item=p.foreground;
        opacity=focused?0.84:inset?0.48:outer?0.68:0.48;
        border=[focused?p.primary:mix(fill,p.foreground,inset?0.28:0.40),focused||outer?2:1];
    }
    if (metro && neutral) {
        // Material depth uses only the selected palette; no imposed city colors.
        fill=mix(p.background,p.foreground,inset?0.005:focused?0.045:0.012);
        item=p.foreground;
        opacity=focused?0.82:inset?0.42:outer?0.64:0.44;
        border=[focused?p.primary:mix(fill,p.primary,outer?0.32:0.20),focused||outer?1:0];
    }
    if (canopy && neutral) {
        // Carry a little foliage color into the surrounding surface.
        var foliage=mix(p.primary,p.secondary,0.35);
        fill=mix(mix(p.background,p.foreground,inset?0.015:0.035),foliage,inset?0.025:0.055);
        item=p.foreground;
        opacity=focused?0.80:inset?0.40:outer?0.62:0.42;
        border=[focused?p.primary:mix(fill,foliage,outer?0.27:0.16),focused||outer?1:0];
    }
    var containers = ["bg", "popup", "pane", "surface", "surfaceContainer", "common", "internalbg", "focus", "surfaceVariant", "bar", "barbg"];
    var dotted = dithered && strength > 0 && containers.indexOf(variant) !== -1;
    // Strength changes contrast only. Buttons and edges stay clean at every level.
    var dotMax = ditherCellSize(strength);
    // Inner dividers recede; outer edges and focused controls retain definition.
    if (dithered && ["pane", "surface", "surfaceContainer", "common", "internalbg"].indexOf(variant) !== -1)
        border[0] = mix(fill, p.primary, 0.12);
    return {
        gradient: [[fill, 0]], gradientType: dotted ? "halftone" : "linear", gradientAngle: 0,
        gradientCenterX: 0.5, gradientCenterY: 0.5,
        halftoneDotMin: dotted ? dotMax : 0, halftoneDotMax: dotted ? dotMax : 0, halftoneStart: 0, halftoneEnd: 1,
        halftoneDotColor: dotted ? dotColor(fill, item, strength * 0.001) : fill, halftoneBackgroundColor: fill,
        border: border, itemColor: item, opacity: opacity
    };
}

// Export the same surface hierarchy to native and themed applications.
function appPalette(style, palette, customOpacity) {
    var result = Object.assign({}, palette);
    result.style = style;
    result.opacity = customOpacity;
    if (style === "custom") return result;
    var roles = {background: palette.background.toString(), foreground: palette.overBackground.toString(),
        primary: palette.primary.toString(), onPrimary: palette.overPrimary.toString(),
        secondary: palette.secondary.toString(), onSecondary: palette.overSecondary.toString(),
        tertiary: palette.tertiary.toString(), onTertiary: palette.overTertiary.toString(),
        error: palette.error.toString(), onError: palette.overError.toString()};
    result.background = surface(style, "bg", roles).gradient[0][0];
    result.surface = result.surfaceContainer = surface(style, "pane", roles).gradient[0][0];
    result.surfaceContainerHigh = surface(style, "focus", roles).gradient[0][0];
    result.surfaceContainerLowest = surface(style, "internalbg", roles).gradient[0][0];
    result.surfaceContainerLow = result.surfaceContainer;
    result.surfaceContainerHighest = result.surfaceContainerHigh;
    result.surfaceVariant = result.surfaceContainerHigh;
    result.surfaceDim = result.surfaceContainerLowest;
    result.surfaceBright = result.surfaceContainerHigh;
    result.outlineVariant = surface(style, "bg", roles).border[0];
    result.opacity = surface(style, "bg", roles).opacity;
    return result;
}


// Styles affect rendering only; colors come from the selected palette.
// Retained for existing palette consumers and preview cards.
function themePalette(style) {
    return null;
}
