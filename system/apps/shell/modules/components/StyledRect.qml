pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Effects
import Quickshell.Widgets
import qs.config
import qs.modules.theme

ClippingRectangle {
    id: root

    clip: true
    antialiasing: true
    contentUnderBorder: true

    required property string variant
    property string styleOverride: ""
    property bool materialPreview: false
    property bool barSurface: false
    property bool buttonSurface: false
    property bool inputSurface: false
    readonly property bool controlSurface: buttonSurface && (styleOverride || Styling.shellStyle) === "terminal-hardware"
    property bool controlPressed: false
    // Color samples need their exact fill, without a surface shader over it.
    property color fillColor: "transparent"
    readonly property bool hasFillColor: fillColor.a > 0

    property string gradientOrientation: "vertical"
    property bool enableShadow: false
    property bool enableBorder: true
    property bool animateRadius: true
    property real backgroundOpacity: -1  // -1 means use config value

    readonly property var variantConfig: Styling.styleConfig(styleOverride || Styling.shellStyle, variant, buttonSurface, inputSurface) || {}

    readonly property var gradientStops: variantConfig.gradient

    readonly property string gradientType: variantConfig.gradientType

    readonly property real gradientAngle: variantConfig.gradientAngle

    readonly property real gradientCenterX: variantConfig.gradientCenterX

    readonly property real gradientCenterY: variantConfig.gradientCenterY

    readonly property real halftoneDotMin: variantConfig.halftoneDotMin

    readonly property real halftoneDotMax: variantConfig.halftoneDotMax

    readonly property real halftoneStart: variantConfig.halftoneStart

    readonly property real halftoneEnd: variantConfig.halftoneEnd

    readonly property color halftoneDotColor: Config.resolveColor(variantConfig.halftoneDotColor)

    readonly property color halftoneBackgroundColor: Config.resolveColor(variantConfig.halftoneBackgroundColor)

    readonly property var borderData: variantConfig.border

    readonly property color solidColor: Config.resolveColor(variantConfig.color)
    readonly property bool hasSolidColor: variantConfig.color !== undefined && variantConfig.color !== ""

    readonly property color itemColor: Config.resolveColor(variantConfig.itemColor)
    property color item: itemColor

    readonly property real rectOpacity: backgroundOpacity >= 0 ? backgroundOpacity : variantConfig.opacity
    readonly property bool usesDitherGrid: false
    readonly property real ditherCellSize: Styling.ditherCellSize


    // Check if gradient is actually a single color (optimization: treat as solid)
    readonly property bool isSingleColorGradient: gradientStops && gradientStops.length === 1
    readonly property color singleGradientColor: isSingleColorGradient ? Config.resolveColor(gradientStops[0][0]) : "transparent"

    // Whether we need a multi-stop gradient shader
    readonly property bool needsGradientShader: (gradientType === "linear" || gradientType === "radial") && !isSingleColorGradient && gradientStops && gradientStops.length >= 2

    // Number of active stops (clamped to max 8)
    readonly property int numGradientStops: gradientStops ? Math.min(gradientStops.length, 8) : 0

    // Resolve gradient stops into vec4 color array for shader uniforms
    function resolveStopColor(index) {
        if (!gradientStops || index >= gradientStops.length) return Qt.vector4d(0,0,0,0);
        const resolved = Config.resolveColor(gradientStops[index][0]);
        // Qt.color() ensures hex strings become proper color objects with .r/.g/.b/.a
        const c = Qt.color(resolved);
        return Qt.vector4d(c.r, c.g, c.b, c.a);
    }

    // Pack stop positions into two vec4s (positions 0-3 in first, 4-7 in second)
    readonly property vector4d stopPositionsPack0: Qt.vector4d(
        gradientStops && gradientStops.length > 0 ? gradientStops[0][1] : 0,
        gradientStops && gradientStops.length > 1 ? gradientStops[1][1] : 0,
        gradientStops && gradientStops.length > 2 ? gradientStops[2][1] : 0,
        gradientStops && gradientStops.length > 3 ? gradientStops[3][1] : 0
    )
    readonly property vector4d stopPositionsPack1: Qt.vector4d(
        gradientStops && gradientStops.length > 4 ? gradientStops[4][1] : 0,
        gradientStops && gradientStops.length > 5 ? gradientStops[5][1] : 0,
        gradientStops && gradientStops.length > 6 ? gradientStops[6][1] : 0,
        gradientStops && gradientStops.length > 7 ? gradientStops[7][1] : 0
    )

    radius: variantConfig.radius !== undefined ? variantConfig.radius : Styling.radius(0)

    readonly property real effectiveCornerRadius: Math.max(0, Math.min(radius, width / 2, height / 2))

    function themeInsetRadius(inset) {
        return Math.max(0, Math.min(effectiveCornerRadius - inset, (width - 2 * inset) / 2, (height - 2 * inset) / 2));
    }

    function themeCornerRadius(value, inset) {
        const corner = value < 0 ? radius : value;
        return Math.max(0, Math.min(corner - inset, (width - 2 * inset) / 2, (height - 2 * inset) / 2));
    }

    function traceThemeFrame(ctx, inset) {
        if (width <= 2 * inset || height <= 2 * inset) return false;
        const tl = themeCornerRadius(topLeftRadius, inset);
        const tr = themeCornerRadius(topRightRadius, inset);
        const bl = themeCornerRadius(bottomLeftRadius, inset);
        const br = themeCornerRadius(bottomRightRadius, inset);
        const right = width - inset, bottom = height - inset;
        ctx.beginPath();ctx.moveTo(inset+tl,inset);ctx.lineTo(right-tr,inset);
        ctx.quadraticCurveTo(right,inset,right,inset+tr);ctx.lineTo(right,bottom-br);
        ctx.quadraticCurveTo(right,bottom,right-br,bottom);ctx.lineTo(inset+bl,bottom);
        ctx.quadraticCurveTo(inset,bottom,inset,bottom-bl);ctx.lineTo(inset,inset+tl);
        ctx.quadraticCurveTo(inset,inset,inset+tl,inset);
        return true;
    }

    // Helper to apply opacity to a color via alpha channel
    function applyOpacity(baseColor, opacityValue) {
        return Qt.rgba(baseColor.r, baseColor.g, baseColor.b, baseColor.a * opacityValue);
    }

    // Color priority: single-color gradient > explicit solid color > transparent (for real gradients)
    // Apply rectOpacity via alpha channel to avoid affecting children
    color: {
        if (hasFillColor) return applyOpacity(fillColor, rectOpacity);
        if (isSingleColorGradient && (gradientType === "linear" || gradientType === "radial")) {
            return applyOpacity(singleGradientColor, rectOpacity);
        }
        if (hasSolidColor && gradientType !== "linear" && gradientType !== "radial" && gradientType !== "halftone") {
            return applyOpacity(solidColor, rectOpacity);
        }
        return "transparent";
    }

    Behavior on radius {
        enabled: root.animateRadius && Config.animDuration > 0
        NumberAnimation {
            duration: Motion.press
        }
    }

    // Linear gradient - procedural (no texture)
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.gradientType === "linear" && root.needsGradientShader

        sourceComponent: ShaderEffect {
            opacity: root.rectOpacity

            property real angle: root.gradientAngle
            property real canvasWidth: width
            property real canvasHeight: height
            property int numStops: root.numGradientStops

            property vector4d stopColor0: root.resolveStopColor(0)
            property vector4d stopColor1: root.resolveStopColor(1)
            property vector4d stopColor2: root.resolveStopColor(2)
            property vector4d stopColor3: root.resolveStopColor(3)
            property vector4d stopColor4: root.resolveStopColor(4)
            property vector4d stopColor5: root.resolveStopColor(5)
            property vector4d stopColor6: root.resolveStopColor(6)
            property vector4d stopColor7: root.resolveStopColor(7)

            property vector4d stopPositionsPack0: root.stopPositionsPack0
            property vector4d stopPositionsPack1: root.stopPositionsPack1

            vertexShader: "linear_gradient.vert.qsb"
            fragmentShader: "linear_gradient.frag.qsb"
        }
    }

    // Radial gradient - procedural (no texture)
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.gradientType === "radial" && root.needsGradientShader

        sourceComponent: ShaderEffect {
            opacity: root.rectOpacity

            property real centerX: root.gradientCenterX
            property real centerY: root.gradientCenterY
            property real canvasWidth: width
            property real canvasHeight: height
            property int numStops: root.numGradientStops

            property vector4d stopColor0: root.resolveStopColor(0)
            property vector4d stopColor1: root.resolveStopColor(1)
            property vector4d stopColor2: root.resolveStopColor(2)
            property vector4d stopColor3: root.resolveStopColor(3)
            property vector4d stopColor4: root.resolveStopColor(4)
            property vector4d stopColor5: root.resolveStopColor(5)
            property vector4d stopColor6: root.resolveStopColor(6)
            property vector4d stopColor7: root.resolveStopColor(7)

            property vector4d stopPositionsPack0: root.stopPositionsPack0
            property vector4d stopPositionsPack1: root.stopPositionsPack1

            vertexShader: "radial_gradient.vert.qsb"
            fragmentShader: "radial_gradient.frag.qsb"
        }
    }

    // Halftone gradient - no texture needed, purely procedural
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.gradientType === "halftone" && !root.usesDitherGrid

        sourceComponent: ShaderEffect {
            opacity: root.rectOpacity

            property real angle: root.gradientAngle
            property real dotMinSize: root.halftoneDotMin
            property real dotMaxSize: root.halftoneDotMax
            property real gradientStart: root.halftoneStart
            property real gradientEnd: root.halftoneEnd
            property vector4d dotColor: {
                const c = root.halftoneDotColor || Colors.surface;
                return Qt.vector4d(c.r, c.g, c.b, c.a);
            }
            property vector4d backgroundColor: {
                const c = root.halftoneBackgroundColor || Colors.background;
                return Qt.vector4d(c.r, c.g, c.b, c.a);
            }
            property real canvasWidth: width
            property real canvasHeight: height

            vertexShader: "halftone.vert.qsb"
            fragmentShader: "halftone.frag.qsb"
        }
    }

    // The preset shares one fixed-pixel grid with the outline shader. Custom
    // halftone gradients retain their independent renderer and saved settings.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.gradientType === "halftone" && root.usesDitherGrid
        sourceComponent: ShaderEffect {
            objectName: "dithered-fill"
            opacity: root.rectOpacity
            property vector2d size: Qt.vector2d(width, height)
            property real cellSize: root.ditherCellSize
            property color dotColor: root.halftoneDotColor
            property color baseColor: root.halftoneBackgroundColor
            vertexShader: "dither_fill.vert.qsb"
            fragmentShader: "dither_fill.frag.qsb"
        }
    }

    // Render a separate shape behind the surface; never capture its text.
    RectangularShadow {
        objectName: root.objectName + "-shadow"
        opacity: root.opacity
        parent: root.parent
        x: root.x + Config.theme.shadowXOffset
        y: root.y + Config.theme.shadowYOffset
        width: root.width
        height: root.height
        z: root.z - 0.01
        visible: root.visible && root.enableShadow && Config.theme.shadowOpacity > 0
        color: Qt.alpha(Config.resolveColor(Config.theme.shadowColor), Config.theme.shadowOpacity)
        blur: Config.theme.shadowBlur * 16
        radius: root.radius
    }

    Loader {
        anchors.fill: parent
        active: Config.theme.backgroundFinish !== "default" && !root.buttonSurface
            && !root.hasFillColor && root.rectOpacity > 0
            && (root.barSurface || ["bg", "popup", "bar"].includes(root.variant))
        sourceComponent: Rectangle {
            objectName: "background-finish"
            opacity: root.rectOpacity
            gradient: Gradient {
                orientation: Config.theme.backgroundFinish === "two-tone" ? Gradient.Horizontal : Gradient.Vertical
                GradientStop { position: 0; color: Qt.alpha(Colors.primary, 0.26) }
                GradientStop { position: 0.55; color: Qt.alpha(Colors.primary, 0) }
                GradientStop { position: 1; color: Qt.alpha(Colors.tertiary, Config.theme.backgroundFinish === "two-tone" ? 0.26 : 0) }
            }
        }
    }

    // Structural glass: perimeter details leave the central reading area clear.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0
            && ["bg", "popup", "pane", "surface", "surfaceContainer", "internalbg", "focus"].indexOf(root.variant) !== -1
            && ["glass-vault", "radar-station"].indexOf(root.styleOverride || Styling.shellStyle) !== -1
        sourceComponent: Item {
            id: material
            readonly property string finish: root.styleOverride || Styling.shellStyle
            readonly property bool outer: root.variant === "bg" || root.variant === "popup"
            readonly property color ink: root.itemColor
            opacity: root.rectOpacity
            Canvas {
                anchors.fill: parent
                readonly property color pigment: material.ink
                readonly property bool outer: material.outer
                onOuterChanged: requestPaint()
                readonly property string finish: material.finish
                objectName: "structural-glass-canvas"
                readonly property real cornerRadius: Math.max(0, Math.min(root.radius, width / 2, height / 2))
                readonly property bool barSurface: root.barSurface
                onBarSurfaceChanged: requestPaint()
                onCornerRadiusChanged: requestPaint()
                readonly property var frameCorners: [root.topLeftRadius, root.topRightRadius, root.bottomLeftRadius, root.bottomRightRadius]
                onFrameCornersChanged: requestPaint()
                onPigmentChanged: requestPaint()
                onFinishChanged: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx=getContext("2d"); ctx.clearRect(0,0,width,height);
                    if (width<24 || height<24) return;
                    const ink=a=>Qt.rgba(pigment.r,pigment.g,pigment.b,a);
                    ctx.save();if(root.traceThemeFrame(ctx,0))ctx.clip();
                    ctx.lineWidth=1;
                    if (finish === "glass-vault") {
                        const radiusAt = inset => root.themeInsetRadius(inset);
                        const frame = inset => {
                            if(root.traceThemeFrame(ctx,inset))ctx.stroke();
                        };
                        if(barSurface){
                            ctx.strokeStyle = ink(0.17);
                            frame(1.5);
                        }else{
                        // A polished bevel defines the block without boxing in its content.
                        const step=material.outer ? 6 : 2;
                        ctx.strokeStyle = ink(0.18);
                        frame(step);
                        if(material.outer){
                            ctx.lineWidth = 3;
                            ctx.strokeStyle = ink(0.09);
                            frame(step + 2);
                            ctx.lineWidth = 1;
                            ctx.strokeStyle = ink(0.18);
                            frame(step + 4);
                            // Clasps share the bevel's inset and radius, with short tangent arms.
                            // Clamp their reach to half the surface so pill corners never overlap.
                            const mount=step,r=radiusAt(mount);
                            const reach=Math.min(r+12,(width-mount*2)/2,(height-mount*2)/2);
                            ctx.save();ctx.lineCap="round";ctx.lineJoin="round";
                            for(const right of [false,true])for(const bottom of [false,true]){
                                ctx.save();
                                ctx.translate(right?width:0,bottom?height:0);
                                ctx.scale(right?-1:1,bottom?-1:1);
                                const corner=()=>{
                                    ctx.beginPath();ctx.moveTo(mount,mount+reach);
                                    ctx.lineTo(mount,mount+r);
                                    ctx.quadraticCurveTo(mount,mount,mount+r,mount);
                                    ctx.lineTo(mount+reach,mount);
                                };
                                // A broad translucent seat and a fine glint read as one clasp.
                                corner();ctx.lineWidth=4;ctx.strokeStyle=ink(bottom?0.07:0.11);ctx.stroke();
                                corner();ctx.lineWidth=1.2;ctx.strokeStyle=ink(bottom?0.19:0.36);ctx.stroke();
                                ctx.restore();
                            }
                            ctx.restore();
                            const lip = step;
                            ctx.lineWidth = 1;
                            ctx.strokeStyle = ink(0.13);
                            const end=lip+reach;
                            if(width>end*2){
                                ctx.beginPath();ctx.moveTo(end,height-lip);
                                ctx.lineTo(width-end,height-lip);ctx.stroke();
                            }
                        }
                        }
                    } else if (finish === "radar-station") {
                        // Fixed bearing scales: no sweep, motion or simulated live data.
                        ctx.strokeStyle=ink(0.12);if(root.traceThemeFrame(ctx,8))ctx.stroke();
                        const radius=Math.min(54,width*0.22,height*0.28);
                        for (const corner of [0,1]) {
                            const pad=Math.max(12,cornerRadius*0.30+8);
                            const x=corner?width-pad:pad,y=corner?height-pad:pad;
                            ctx.strokeStyle=ink(0.19);
                            for (const r of [radius*0.55,radius*0.78,radius]) {
                                ctx.beginPath();ctx.arc(x,y,r,corner?Math.PI:0,corner?Math.PI*1.5:Math.PI*0.5);ctx.stroke();
                            }
                            for (let tick=0;tick<=12;tick++) {
                                const a=(corner?Math.PI:0)+tick*Math.PI/24;
                                const r=radius+(tick%3===0?5:2);
                                ctx.beginPath();ctx.moveTo(x+radius*Math.cos(a),y+radius*Math.sin(a));ctx.lineTo(x+r*Math.cos(a),y+r*Math.sin(a));ctx.stroke();
                            }
                        }
                        if(material.outer) {
                            // Static scope phosphor and radial divisions enrich the bearing plate.
                            const scopeRadius=Math.min(78,width*0.26,height*0.32);
                            const pad=Math.max(14,cornerRadius*0.30+8);
                            const bearing = Math.PI / 6;
                            ctx.fillStyle = ink(0.13);
                            ctx.beginPath();
                            ctx.moveTo(pad, pad);
                            ctx.arc(pad, pad, radius, bearing, bearing + Math.PI / 8);
                            ctx.closePath();
                            ctx.fill();
                            ctx.strokeStyle=ink(0.08);
                            for(const angle of [Math.PI/8,Math.PI/4,Math.PI*3/8]){
                                ctx.beginPath();ctx.moveTo(pad+12*Math.cos(angle),pad+12*Math.sin(angle));
                                ctx.lineTo(pad+scopeRadius*Math.cos(angle),pad+scopeRadius*Math.sin(angle));ctx.stroke();
                            }
                            ctx.strokeStyle=ink(0.30);
                            for(let x=76;x<width-76;x+=12){ctx.beginPath();ctx.moveTo(x,5);ctx.lineTo(x,x%36===4?11:8);ctx.stroke();}
                            for(const x of [8,width-8]){ctx.beginPath();ctx.moveTo(x-4,height/2);ctx.lineTo(x+4,height/2);ctx.moveTo(x,height/2-4);ctx.lineTo(x,height/2+4);ctx.stroke();}
                            ctx.fillStyle=ink(0.25);
                            for(let i=0;i<5;i++)ctx.fillRect(width/2-19+i*8,height-7,5,2);
                        }
                    }
                    ctx.restore();
                }
            }
        }
    }

    Loader {
        anchors.fill: parent
        active: (root.styleOverride || Styling.shellStyle) === "glyph" && !root.hasFillColor
            && !root.controlSurface && root.rectOpacity > 0
            && (root.materialPreview || (width >= 160 && height >= 80))
            && ["bg", "popup", "pane", "surface", "surfaceContainer"].includes(root.variant)
        sourceComponent: Image {
            objectName: "glyph-orbit-background"
            source: Qt.resolvedUrl("glyph-orbits.png")
            fillMode: Image.PreserveAspectCrop
            horizontalAlignment: Image.AlignRight
            opacity: root.rectOpacity
        }
    }

    // Wallpaper architecture, using the selected semantic colors throughout.
    Loader {
        anchors.fill: parent
        readonly property string material: root.styleOverride || Styling.shellStyle
        active: !root.hasFillColor && root.rectOpacity > 0 && (["canopy", "metropolis"].includes(material)
            ? !root.controlSurface && ["bg", "popup", "pane", "surface", "surfaceContainer", "bar"].includes(root.variant)
            : material === "orbital"
                && ["bg", "popup", "pane", "surface", "surfaceContainer", "internalbg", "focus", "bar"].includes(root.variant))
        sourceComponent: Canvas {
            anchors.fill: parent
            id: materialCanvas
            objectName: "wallpaper-theme-canvas"
            readonly property bool barSurface: root.barSurface
            onBarSurfaceChanged: requestPaint()
            readonly property string finish: root.styleOverride || Styling.shellStyle
            readonly property real cornerRadius: root.effectiveCornerRadius
            readonly property color backdrop: Colors.background
            onBackdropChanged: requestPaint()
            readonly property color accent: Colors.primary
            readonly property color secondaryAccent: Colors.tertiary
            onAccentChanged: requestPaint()
            onSecondaryAccentChanged: requestPaint()
            readonly property color pigment: root.itemColor
            readonly property bool inset: root.variant === "internalbg"
            onInsetChanged: requestPaint()
            readonly property bool outer: root.variant === "bg" || root.variant === "popup"
            opacity: root.rectOpacity
            onCornerRadiusChanged: requestPaint()
            readonly property var frameCorners: [root.topLeftRadius, root.topRightRadius, root.bottomLeftRadius, root.bottomRightRadius]
            onFrameCornersChanged: requestPaint()
            onPigmentChanged: requestPaint()
            onFinishChanged: requestPaint()
            onOuterChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            readonly property bool broad: root.materialPreview || (width >= 160 && height >= 80 && root.variant !== "bar")
            readonly property bool nested: !outer && !barSurface && root.variant !== "bar"
            onBroadChanged: requestPaint()
            onNestedChanged: requestPaint()

            HoverHandler {
                id: orbitHover
                enabled: materialCanvas.finish === "orbital" && Config.animDuration > 0
                blocking: false
            }
            property real orbitPhase: 0
            Timer {
                interval: 50
                repeat: true
                running: materialCanvas.visible && orbitHover.enabled && orbitHover.hovered
                onTriggered: {
                    materialCanvas.orbitPhase = (materialCanvas.orbitPhase + 0.025) % (2 * Math.PI)
                    materialCanvas.requestPaint()
                }
            }

            function paintGravityWell(ctx) {
                const radius = Math.min(width * 0.20, height * 0.45, 55)
                if (radius < 7) return
                ctx.save()
                ctx.translate(width - radius - 8, height * 0.46)
                ctx.strokeStyle = Qt.alpha(pigment, 0.30)
                ctx.lineWidth = 0.8
                for (const scale of [1, 0.72, 0.49, 0.30, 0.15]) {
                    const r = radius * scale
                    const dip = radius * 0.40 * Math.pow(1 - scale, 2)
                    const wave = Math.sin(orbitPhase * 2 - scale * 6) * radius * 0.035
                    ctx.beginPath()
                    ctx.ellipse(-r, dip + wave - r * 0.32, r * 2, r * 0.64)
                    ctx.stroke()
                }
                ctx.fillStyle = Qt.alpha(accent, 0.78)
                ctx.beginPath()
                ctx.arc(Math.cos(orbitPhase) * radius, Math.sin(orbitPhase) * radius * 0.32,
                    Math.max(1.4, radius * 0.05), 0, 2 * Math.PI)
                ctx.fill()
                ctx.restore()
            }

            function paintCanopy(ctx) {
                const leafSize = broad ? Math.min(28, width * 0.047, height * 0.105) : Math.min(12, height * 0.23, width * 0.035)

                function leaf(x, y, angle, size, breadth, foliage) {
                    ctx.save()
                    ctx.translate(x, y)
                    ctx.rotate(angle)
                    ctx.scale(size, size * breadth)
                    ctx.beginPath()
                    ctx.moveTo(0, 0)
                    ctx.bezierCurveTo(0.27, -0.42, 0.65, -0.25, 1, -0.10)
                    ctx.bezierCurveTo(0.73, 0.02, 0.38, 0.42, 0, 0)
                    ctx.fillStyle = foliage
                    ctx.fill()
                    ctx.beginPath()
                    ctx.moveTo(0, 0)
                    ctx.bezierCurveTo(0.27, -0.42, 0.65, -0.25, 1, -0.10)
                    ctx.quadraticCurveTo(0.49, -0.02, 0, 0)
                    ctx.fillStyle = Qt.alpha(pigment, 0.27)
                    ctx.fill()
                    ctx.restore()
                }

                // Sample each curved bough so shoots grow from the wood and
                // paired leaves follow their shoot, even on tall windows.
                function limb(x0, y0, cx, cy, x1, y1, size, count, foliage) {
                    const bark = Qt.tint(foliage, Qt.alpha(backdrop, 0.48))
                    ctx.fillStyle = bark
                    ctx.beginPath()
                    ctx.moveTo(x0, y0 - size * 0.30)
                    ctx.quadraticCurveTo(cx, cy - size * 0.13, x1, y1)
                    ctx.quadraticCurveTo(cx, cy + size * 0.14, x0, y0 + size * 0.30)
                    ctx.closePath()
                    ctx.fill()
                    for (let i = 0; i < count; ++i) {
                        const t = (i + 0.52) / count, u = 1 - t
                        const x = u*u*x0 + 2*u*t*cx + t*t*x1
                        const y = u*u*y0 + 2*u*t*cy + t*t*y1
                        const heading = Math.atan2(u*(cy-y0) + t*(y1-cy), u*(cx-x0) + t*(x1-cx))
                        const side = i % 2 ? -1 : 1
                        const shoot = size * (2.4 - t * 0.85 + (i % 3) * 0.32)
                        ctx.save()
                        ctx.translate(x, y)
                        ctx.rotate(heading + side * (0.47 + (i % 3) * 0.16))
                        const bend = side * shoot * 0.29
                        // Two curves meet at a fine tip; leaves attach along their centerline.
                        const stem = Math.max(0.55, size * 0.055)
                        ctx.fillStyle = bark
                        ctx.beginPath()
                        ctx.moveTo(0, -stem)
                        ctx.quadraticCurveTo(shoot * 0.5, -stem * 0.35, shoot, bend)
                        ctx.quadraticCurveTo(shoot * 0.5, stem * 0.35, 0, stem)
                        ctx.closePath()
                        ctx.fill()

                        const leaves = 3 + i % 3
                        for (let j = 1; j <= leaves; ++j) {
                            const s = j / (leaves + 1)
                            const tangent = Math.atan2(2 * bend * s, shoot)
                            const spread = (j % 2 ? 1 : -1) * (1.05 - 0.48 * s)
                            const breadth = 0.76 + 0.12 * ((i + j) % 4)
                            leaf(shoot * s, bend * s*s, tangent + spread,
                                 size * (1.13 - s * 0.47), breadth, foliage)
                        }
                        leaf(shoot, bend, Math.atan2(2 * bend, shoot), size * 0.66, 0.74, foliage)
                        ctx.restore()
                    }
                }

                if (broad) {
                    // A distant crown crosses the reading area in silhouette.
                    // The closer limbs overlap it at opposite edges.
                    ctx.globalAlpha = nested ? 0.15 : 0.26
                    limb(width * 1.03, height * 0.12, width * 0.67, height * 0.20,
                         width * 0.21, height * 0.68, leafSize, nested ? 5 : 9, secondaryAccent)
                    ctx.globalAlpha = nested ? 0.24 : 0.48
                    limb(-leafSize, height * 0.98, width * 0.12, height * 0.79,
                         width * 0.42, height * 0.78, leafSize * 0.76, 5, accent)
                }
                if (!nested) {
                    // Limit the reach on a wide bar so the clock stays clear.
                    const reach = Math.min(width * 0.29, leafSize * 9)
                    const crownSize = leafSize * (broad ? 0.60 : 0.78)
                    ctx.globalAlpha = broad ? 0.55 : 0.70
                    limb(-leafSize, crownSize * 1.75, reach * 0.35, crownSize * 0.35,
                         reach, -crownSize * 0.24, crownSize, 5, accent)
                    if (!broad) {
                        ctx.globalAlpha = 0.60
                        limb(width + leafSize, leafSize * 1.6, width - reach * 0.44, leafSize * 0.9,
                             width - reach * 0.82, 0, leafSize * 0.62, 4, secondaryAccent)
                    }
                }
            }

            function paintMetropolis(ctx) {
                const base = height
                const compact = !broad
                const rise = Math.min(height * (nested ? 0.44 : 0.64), width * 0.42)
                const color = (ink, strength) => Qt.tint(backdrop, Qt.alpha(ink, strength))
                ctx.globalAlpha = nested ? 0.62 : 1

                // Setbacks, a recessed side face and continuous vertical fins give
                // each tower a readable silhouette even when its windows disappear.
                function tower(x, span, tall, steps, seed) {
                    const roof = base - tall
                    const setback = span * 0.11
                    const tier = tall * 0.085
                    const facade = ctx.createLinearGradient(0, roof, 0, base)
                    facade.addColorStop(0, color(accent, 0.38))
                    facade.addColorStop(1, color(accent, 0.10))
                    ctx.fillStyle = facade
                    ctx.beginPath()
                    ctx.moveTo(x, base)
                    for (let i = 0; i <= steps; ++i) {
                        const level = roof + (steps - i) * tier
                        ctx.lineTo(x + i * setback, level)
                        ctx.lineTo(x + (i + 1) * setback, level)
                    }
                    for (let i = steps; i >= 0; --i) {
                        const level = roof + (steps - i) * tier
                        ctx.lineTo(x + span - i * setback, level)
                        ctx.lineTo(x + span - i * setback, level + tier)
                    }
                    ctx.lineTo(x + span, base)
                    ctx.closePath()
                    ctx.fill()

                    const shoulder = roof + steps * tier
                    ctx.fillStyle = Qt.alpha(backdrop, 0.53)
                    ctx.fillRect(x + span * 0.77, shoulder, span * 0.23, base - shoulder)
                    if (steps === 2) {
                        ctx.fillStyle = color(secondaryAccent, 0.56)
                        ctx.fillRect(x + span * 0.48, roof - tall * 0.09, 1, tall * 0.09)
                    }
                    if (tall < 14 || span < 10) return
                    const bays = Math.min(9, Math.max(2, Math.floor(span / 5)))
                    const pitch = span * 0.68 / bays
                    const floorHeight = Math.max(4, (base - shoulder) / 22)
                    for (let bay = 0; bay < bays; ++bay) {
                        const left = x + span * 0.05 + bay * pitch
                        const start = roof + (steps - Math.min(steps, Math.floor((left - x) / setback))) * tier + 2
                        ctx.fillStyle = Qt.alpha(backdrop, 0.46)
                        ctx.fillRect(left, start, pitch * 0.56, base - start)
                        for (let floor = 1; shoulder + floor * floorHeight < base; ++floor) {
                            const light = (floor * 7 + bay * 11 + seed * 3 + Math.floor(floor / 3) * bay) % 19
                            if (light > 6) continue
                            ctx.fillStyle = Qt.alpha(light < 3 ? secondaryAccent : pigment, light < 3 ? 0.88 : 0.36)
                            ctx.fillRect(left, shoulder + floor * floorHeight, pitch * 0.56, Math.min(2, floorHeight * 0.39))
                        }
                    }
                }

                if (compact) {
                    const reach = Math.min(width * 0.26, 85)
                    const roof = Math.min(height * 0.42, 19)
                    tower(0, reach * 0.36, roof * 0.54, 0, 1)
                    tower(reach * 0.32, reach * 0.23, roof, 2, 2)
                    tower(reach * 0.53, reach * 0.38, roof * 0.42, 1, 3)
                    tower(width - reach * 0.78, reach * 0.28, roof * 0.72, 1, 4)
                    tower(width - reach * 0.52, reach * 0.54, roof * 0.48, 0, 5)
                    return
                }

                // Smaller, softer blocks across the horizon connect the two districts.
                ctx.fillStyle = Qt.alpha(secondaryAccent, 0.16)
                const roofs = [0.36, 0.54, 0.42, 0.61, 0.27, 0.31, 0.18, 0.22, 0.13,
                              0.17, 0.12, 0.23, 0.16, 0.28, 0.41, 0.30, 0.55, 0.39, 0.48]
                for (let i = 0; i < roofs.length; ++i) {
                    const tall = roofs[i] * rise
                    ctx.fillRect(i * width / roofs.length, base - tall, width / roofs.length, tall)
                }
                tower(-0.028 * width, 0.11 * width, rise * 0.58, 1, 3)
                tower(0.07 * width, 0.075 * width, rise, 2, 2)
                tower(0.15 * width, 0.05 * width, rise * 0.50, 0, 6)
                tower(0.20 * width, 0.087 * width, rise * 0.34, 1, 1)
                tower(0.67 * width, 0.085 * width, rise * 0.30, 0, 1)
                tower(0.755 * width, 0.085 * width, rise * 0.72, 2, 7)
                tower(0.845 * width, 0.055 * width, rise * 0.44, 0, 5)
                tower(0.91 * width, 0.115 * width, rise * 0.53, 1, 4)
            }

            onPaint: {
                const ctx=getContext("2d");ctx.clearRect(0,0,width,height);
                if(width<24||height<24)return;
                const ink=a=>Qt.rgba(pigment.r,pigment.g,pigment.b,a);
                ctx.lineWidth=1;
                // Clip every material layer to the shared rounded surface.
                ctx.save();
                if(root.traceThemeFrame(ctx,0))ctx.clip();
                if (finish === "canopy") {
                    paintCanopy(ctx)

                } else if (finish === "orbital") {
                    paintGravityWell(ctx)
                    const rim = outer || inset ? 6 : 3;
                    // Deterministic jitter spreads a stable star field over the entire surface.
                    // Check star centers against an inset that allows for the full cross and stroke.
                    const stars = [];
                    if (root.traceThemeFrame(ctx, rim + 4)) {
                        for (let row = 0; row < Math.ceil(height / 46); row++) {
                            for (let col = 0; col < Math.ceil(width / 54); col++) {
                                const seed = Math.abs(Math.sin((col + 1) * 127.1 + (row + 1) * 311.7) * 43758.5453);
                                const fraction = seed - Math.floor(seed);
                                const x = col * 54 + 7 + fraction * 38;
                                const y = row * 46 + 6 + (fraction * 7.31 % 1) * 32;
                                if (ctx.isPointInPath(x, y)) stars.push({x, y, fraction});
                            }
                        }
                    }
                    for (const {x, y, fraction} of stars) {
                        const bright = fraction > 0.88;
                        ctx.fillStyle = ink(bright ? 0.95 : 0.31 + fraction * 0.34);
                        ctx.beginPath();
                        ctx.arc(x, y, bright ? 1.55 : 0.82, 0, Math.PI * 2);
                        ctx.fill();
                        if (bright) {
                            ctx.strokeStyle = ink(0.54);
                            ctx.lineWidth = 0.9;
                            ctx.beginPath();
                            ctx.moveTo(x - 3, y);
                            ctx.lineTo(x + 3, y);
                            ctx.moveTo(x, y - 3);
                            ctx.lineTo(x, y + 3);
                            ctx.stroke();
                        }
                    }
                } else {
                    paintMetropolis(ctx)
                }
                ctx.restore();
            }
        }
    }

    // Clear Glass keeps only grazing reflections and a tiny lower meniscus.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0
            && (root.styleOverride || Styling.shellStyle) === "clear-glass"
            && ["bg","popup","pane","surface","internalbg","focus"].indexOf(root.variant) !== -1
        sourceComponent: Canvas {
            anchors.fill: parent
            objectName: "clear-glass-canvas"
            readonly property real cornerRadius: root.effectiveCornerRadius
            readonly property color pigment: root.itemColor
            readonly property bool outer: root.variant === "bg" || root.variant === "popup"
            opacity: root.rectOpacity
            onCornerRadiusChanged: requestPaint()
            readonly property var frameCorners: [root.topLeftRadius, root.topRightRadius, root.bottomLeftRadius, root.bottomRightRadius]
            onFrameCornersChanged: requestPaint()
            onPigmentChanged: requestPaint()
            onOuterChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                const ctx=getContext("2d");ctx.clearRect(0,0,width,height);
                if(width<24||height<24)return;
                const ink=a=>Qt.rgba(pigment.r,pigment.g,pigment.b,a);
                ctx.save();if(root.traceThemeFrame(ctx,0))ctx.clip();
                if(outer){
                    const safe=Math.max(18,cornerRadius+5);
                    ctx.strokeStyle = ink(0.14);
                    ctx.lineWidth = 1;
                    if (root.traceThemeFrame(ctx, 1.5)) ctx.stroke();
                    ctx.strokeStyle=ink(0.08);
                    ctx.beginPath();ctx.moveTo(width*0.56,height-4);ctx.lineTo(Math.max(width*0.56,width-safe),height-4);ctx.stroke();
                }
                ctx.restore();
            }
        }
    }

    Loader {
        anchors.fill: parent
        readonly property string finish: root.styleOverride || Styling.shellStyle
        readonly property bool panel: ["bg", "popup", "pane", "surface", "surfaceContainer", "internalbg", "focus", "surfaceVariant"].includes(root.variant)
        active: !root.hasFillColor && root.rectOpacity > 0 && (finish === "monolith"
            ? panel || root.controlSurface || ["common", "primary", "primaryfocus", "secondary", "secondaryfocus", "tertiary", "tertiaryfocus", "error", "errorfocus"].includes(root.variant)
            : finish === "guilloche" && !root.buttonSurface && (root.barSurface || ["bg", "popup", "bar"].includes(root.variant)))
        sourceComponent: Canvas {
            objectName: "surface-edge-canvas"
            anchors.fill: parent
            opacity: root.rectOpacity
            readonly property string finish: root.styleOverride || Styling.shellStyle
            readonly property color pigment: root.itemColor
            readonly property color accent: Colors.primary
            readonly property real cornerRadius: root.effectiveCornerRadius
            readonly property var frameCorners: [root.topLeftRadius, root.topRightRadius, root.bottomLeftRadius, root.bottomRightRadius]
            readonly property bool outer: root.barSurface || ["bg", "popup", "bar"].includes(root.variant)
            onFinishChanged: requestPaint()
            onPigmentChanged: requestPaint()
            onAccentChanged: requestPaint()
            onCornerRadiusChanged: requestPaint()
            onFrameCornersChanged: requestPaint()
            onOuterChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()

            function paintSlateFace(ctx) {
                // Positions follow the slab as it resizes. The third coordinate
                // is the local thickness of each exposed mineral bed.
                const strength = outer ? 1 : 0.65
                const thickness = Math.min(32, Math.max(2.5, height * 0.065))
                function bed(points, dye, alpha) {
                    ctx.beginPath()
                    ctx.moveTo(points[0][0] * width, points[0][1] * height)
                    for (const [x, y] of points) ctx.lineTo(x * width, y * height)
                    for (let i = points.length - 1; i >= 0; --i) {
                        const [x, y, weight] = points[i]
                        ctx.lineTo(x * width, y * height + weight * thickness)
                    }
                    ctx.closePath()
                    ctx.fillStyle = Qt.alpha(dye, alpha * strength)
                    ctx.fill()
                }

                // A diagonal cleavage plane breaks into parallel seams and
                // tapers into narrow, brighter inclusions near the edges.
                const fault = [[0,.78,.95],[.14,.66,.65],[.22,.65,.38],[.35,.53,.55],
                               [.47,.51,.14],[.61,.40,.34],[.69,.40,.16],[.88,.21,.85],[1,.17,.48]]
                bed(fault, pigment, 0.085)
                bed([[0,.77,.21],[.14,.66,.17],[.22,.65,.04],[.35,.53,0]], accent, 0.34)
                bed([[.47,.51,0],[.59,.45,.21],[.64,.45,.11],[.78,.32,0]], pigment, 0.16)
                bed([[.69,.40,0],[.80,.275,.13],[.88,.21,.37],[1,.17,.12]], accent, 0.27)

                bed([[.16,.62,0],[.205,.62,.08],[.28,.575,.18],[.35,.53,0]], pigment, 0.22)
                bed([[.78,.31,0],[.84,.225,.12],[.90,.195,0]], pigment, 0.26)

                // Offset beds give the slab a second plane on either side of
                // the main seam. Their widths vary independently.
                bed([[.29,-.045,.30],[.42,.006,.72],[.54,.026,.62],[.65,.018,.38],[.72,-.04,0]], pigment, 0.13)
                bed([[.56,1,0],[.68,.90,.86],[.76,.895,.52],[.86,.78,.38],[1,.70,1.3]], accent, 0.14)
                bed([[.76,.895,0],[.83,.795,.10],[.86,.78,.19],[.95,.729,0]], pigment, 0.26)
            }

            readonly property bool ribbonBar: root.barSurface || root.variant === "bar"
            onRibbonBarChanged: requestPaint()

            function paintGuilloche(ctx) {
                const vertical = ribbonBar && height > width
                const length = vertical ? height : width
                const breadth = vertical ? width : height
                const compact = ribbonBar || breadth < 70
                const strands = ribbonBar ? 3 : compact ? 5 : 13
                const steps = Math.min(240, Math.max(48, Math.ceil(length / 5)))
                const amplitude = ribbonBar ? Math.min(3, breadth * 0.08) : breadth * 0.21
                const ink = ctx.createLinearGradient(0, 0, vertical ? 0 : length, vertical ? length : 0)
                ink.addColorStop(0, Qt.alpha(accent, 0.32))
                ink.addColorStop(0.43, Qt.alpha(pigment, 0.12))
                ink.addColorStop(0.65, Qt.alpha(accent, 0.19))
                ink.addColorStop(1, Qt.alpha(accent, 0.32))
                ctx.strokeStyle = ink
                ctx.lineWidth = 1
                // Parallel cuts fan open, twist through one another, then
                // spread again along a shallow S-shaped sweep.
                for (let strand = 0; strand < strands; ++strand) {
                    const offset = strand / (strands - 1) - 0.5
                    ctx.beginPath()
                    for (let step = 0; step <= steps; ++step) {
                        const t = step / steps
                        const sweep = Math.sin(2 * Math.PI * (t - 0.12))
                        const axis = ribbonBar ? breadth * 0.85 : breadth * (0.50 + 0.22 * sweep)
                        const twist = 2 * Math.PI * (1.45 * t + 0.10 * sweep)
                        const cross = axis + amplitude * Math.sin(twist + offset * 2.8)
                        const x = vertical ? cross : t * length
                        const y = vertical ? t * length : cross
                        if (step === 0) ctx.moveTo(x, y)
                        else ctx.lineTo(x, y)
                    }
                    ctx.stroke()
                }
            }

            onPaint: {
                const ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                if (width < 24 || height < 16) return
                ctx.save()
                if (root.traceThemeFrame(ctx, 0)) ctx.clip()
                if (finish === "monolith") paintSlateFace(ctx)
                else paintGuilloche(ctx)
                ctx.restore()
            }
        }
    }

    // Flat keycaps: concentric rims and short edge notches, clear of labels.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0
            && (root.styleOverride || Styling.shellStyle) === "terminal-hardware"
            && (root.controlSurface || ["primary", "primaryfocus", "secondary", "secondaryfocus", "tertiary", "tertiaryfocus", "error", "errorfocus"].indexOf(root.variant) !== -1)
        sourceComponent: Canvas {
            readonly property color pigment: root.itemColor
            readonly property real cornerRadius: root.effectiveCornerRadius
            readonly property bool depressed: root.controlPressed
            onPigmentChanged: requestPaint()
            onCornerRadiusChanged: requestPaint()
            onDepressedChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                const ctx=getContext("2d");ctx.clearRect(0,0,width,height);
                if(width<18||height<18)return;
                ctx.save();if(root.traceThemeFrame(ctx,0))ctx.clip();
                ctx.lineWidth=1;
                ctx.strokeStyle=Qt.alpha(pigment,depressed?0.28:0.16);
                if(root.traceThemeFrame(ctx,depressed?2:3))ctx.stroke();
                const mid=height/2;
                ctx.fillStyle=Qt.alpha(pigment,depressed?0.35:0.26);
                for(const x of [5,width-6])ctx.fillRect(x,mid-2,1,4);
                ctx.restore();
            }
        }
    }

    // Hardware housings and recessed displays have their own physical details.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0 && (root.styleOverride || Styling.shellStyle) === "terminal-hardware"
            && !root.controlSurface
            && ["bg", "popup", "bar", "pane", "surface", "surfaceContainer", "internalbg", "focus", "surfaceVariant"].indexOf(root.variant) !== -1
        sourceComponent: Item {
            id: chassis
            readonly property bool outer: root.variant === "bg" || root.variant === "popup" || root.variant === "bar" || root.barSurface
            readonly property bool screen: root.variant === "internalbg"
            readonly property color ink: root.itemColor
            opacity: root.rectOpacity
            Rectangle {
                anchors.fill: parent; anchors.margins: chassis.outer ? 4 : 2
                radius: root.themeInsetRadius(chassis.outer ? 4 : 2)
                topLeftRadius: root.themeCornerRadius(root.topLeftRadius, chassis.outer ? 4 : 2)
                topRightRadius: root.themeCornerRadius(root.topRightRadius, chassis.outer ? 4 : 2)
                bottomLeftRadius: root.themeCornerRadius(root.bottomLeftRadius, chassis.outer ? 4 : 2)
                bottomRightRadius: root.themeCornerRadius(root.bottomRightRadius, chassis.outer ? 4 : 2)
                color: "transparent"; border.width: 1
                border.color: Qt.alpha(chassis.ink, chassis.outer ? 0.15 : 0.07)
            }
            Canvas {
                anchors.fill: parent
                objectName: "surface-edge-canvas"
                readonly property real cornerRadius: root.effectiveCornerRadius
                readonly property color pigment: chassis.ink
                readonly property color slotColor: Colors.background
                onSlotColorChanged: requestPaint()
                readonly property bool outer: chassis.outer
                readonly property bool screen: chassis.screen
                onOuterChanged: requestPaint()
                onScreenChanged: requestPaint()
                onCornerRadiusChanged: requestPaint()
                readonly property var frameCorners: [root.topLeftRadius, root.topRightRadius, root.bottomLeftRadius, root.bottomRightRadius]
                onFrameCornersChanged: requestPaint()
                onPigmentChanged: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx=getContext("2d");ctx.clearRect(0,0,width,height);
                    if(width<24||height<24)return;
                    ctx.save();if(root.traceThemeFrame(ctx,0))ctx.clip();
                    // One inset bezel and a small vent bank keep the housing legible.
                    if(chassis.outer){
                        const safe=Math.max(20,cornerRadius+8);
                        // Split top seams and three inset slots suggest a machined cover.
                        if(width>safe*2+80){
                            const center=width/2;
                            ctx.strokeStyle=Qt.alpha(pigment,0.18);ctx.lineWidth=1;
                            for(const span of [[safe,center-24],[center+24,width-safe]]){
                                ctx.beginPath();ctx.moveTo(span[0],9);
                                ctx.lineTo(span[1],9);ctx.stroke();
                            }
                            ctx.fillStyle=Qt.alpha(pigment,0.22);
                            for(let i=-1;i<=1;i++)ctx.fillRect(center+i*10-3,7,6,2);
                        }
                        // A short rail on each side, with end caps and a center notch.
                        // Keep details inside the bezel and away from rounded corners.
                        if(height>safe*2+64){
                            const mid=height/2;
                            const half=Math.min(28,(height-safe*2)/4);
                            ctx.strokeStyle=Qt.alpha(pigment,0.18);ctx.lineWidth=1;
                            for(const x of [8,width-8]){
                                const inward=x<width/2?1:-1;
                                ctx.beginPath();ctx.moveTo(x+3*inward,mid-half);
                                ctx.lineTo(x,mid-half);ctx.lineTo(x,mid+half);
                                ctx.lineTo(x+3*inward,mid+half);ctx.stroke();
                                ctx.fillStyle=Qt.alpha(pigment,0.24);
                                ctx.fillRect(x-1,mid-3,2,6);
                            }
                        }
                        if(width>safe*2+40 && height>safe*2+24){
                            // Recessed louvers catch light on the lower lip of each cutout.
                            for (let slot = 0; slot < 6; slot++) {
                                const x = width - safe - 42 + slot * 7;
                                ctx.fillStyle = Qt.alpha(slotColor, 0.84);
                                ctx.fillRect(x, height - 15, 4, 7);
                                ctx.fillStyle = Qt.alpha(pigment, 0.30);
                                ctx.fillRect(x, height - 8, 4, 1);
                            }
                        }
                    }
                    ctx.restore();
                }
            }
        }
    }

    // Non-interactive drafting marks and case fasteners, behind content.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0 && (root.variant === "bg" || root.variant === "popup" || root.variant === "bar" || root.barSurface)
            && !root.controlSurface
            && ["blueprint", "terminal-hardware"].indexOf(root.styleOverride || Styling.shellStyle) !== -1
        sourceComponent: Item {
            id: engraving
            readonly property bool drafting: (root.styleOverride || Styling.shellStyle) === "blueprint"
            readonly property color ink: root.itemColor
            opacity: root.rectOpacity
            Canvas {
                anchors.fill: parent
                visible: engraving.drafting
                readonly property color pigment: engraving.ink
                onPigmentChanged: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx=getContext("2d");ctx.clearRect(0,0,width,height);
                    ctx.save();if(root.traceThemeFrame(ctx,0))ctx.clip();
                    // Major and minor rules use two uniform ink weights.
                    for(let axis=0;axis<2;axis++){
                        const extent=axis?height:width;
                        for(let n=20;n<extent;n+=20){
                            const major=n%80===0;
                            ctx.strokeStyle = Qt.alpha(pigment, major ? 0.085 : 0.035);
                            ctx.lineWidth = major ? 0.8 : 0.5;
                            ctx.beginPath();ctx.moveTo(axis?0:n,axis?n:0);
                            ctx.lineTo(axis?width:n,axis?n:height);ctx.stroke();
                        }
                    }
                    ctx.restore();
                }
            }
            // Measurement teeth stay at the perimeter, away from text.
            Repeater {
                model: engraving.drafting ? Math.floor(engraving.width / 10) : 0
                Item {
                    required property int index
                    x: (index + 1) * 10
                    width: 1; height: engraving.height
                    Rectangle { width: 1; height: (parent.index + 1) % 4 === 0 ? 7 : 3; color: engraving.ink; opacity: 0.30 }
                    Rectangle { anchors.bottom: parent.bottom; width: 1; height: (parent.index + 1) % 4 === 0 ? 7 : 3; color: engraving.ink; opacity: 0.30 }
                }
            }
            Repeater {
                model: engraving.drafting ? Math.floor(engraving.height / 10) : 0
                Item {
                    required property int index
                    y: (index + 1) * 10
                    height: 1; width: engraving.width
                    Rectangle { height: 1; width: (parent.index + 1) % 4 === 0 ? 7 : 3; color: engraving.ink; opacity: 0.30 }
                    Rectangle { anchors.right: parent.right; height: 1; width: (parent.index + 1) % 4 === 0 ? 7 : 3; color: engraving.ink; opacity: 0.30 }
                }
            }
            Rectangle {
                visible: engraving.drafting
                anchors.fill: parent
                anchors.margins: 10
                radius: root.themeInsetRadius(10)
                topLeftRadius: root.themeCornerRadius(root.topLeftRadius, 10)
                topRightRadius: root.themeCornerRadius(root.topRightRadius, 10)
                bottomLeftRadius: root.themeCornerRadius(root.bottomLeftRadius, 10)
                bottomRightRadius: root.themeCornerRadius(root.bottomRightRadius, 10)
                color: "transparent"
                border.width: 1
                border.color: Qt.alpha(engraving.ink, 0.15)
            }
            Repeater {
                model: engraving.drafting ? 2 : 0
                Item {
                    required property int index
                    x: index ? engraving.width - 30 : 30
                    y: index ? engraving.height - 10 : 10
                    Rectangle { x: -4; width: 9; height: 1; color: engraving.ink; opacity: 0.5 }
                    Rectangle { y: -4; height: 9; width: 1; color: engraving.ink; opacity: 0.5 }
                    Rectangle { x: -3; y: -3; width: 7; height: 7; radius: 3.5; color: "transparent"; border.width: 1; border.color: Qt.alpha(engraving.ink, 0.3) }
                }
            }
            Canvas {
                anchors.fill: parent
                visible: engraving.drafting
                objectName: "drafting-corner-canvas"
                readonly property real cornerRadius: root.effectiveCornerRadius
                readonly property color pigment: engraving.ink
                onCornerRadiusChanged: requestPaint()
                readonly property var frameCorners: [root.topLeftRadius, root.topRightRadius, root.bottomLeftRadius, root.bottomRightRadius]
                onFrameCornersChanged: requestPaint()
                onPigmentChanged: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx=getContext("2d");ctx.clearRect(0,0,width,height);
                    const r=root.themeInsetRadius(6);
                    const span=Math.min(Math.max(9,r+6),(width-12)/2,(height-12)/2);
                    // A small drafted truss detail gives the sheet architectural purpose.
                    ctx.save();if(root.traceThemeFrame(ctx,0))ctx.clip();
                    const safe=Math.max(24,cornerRadius+10);
                    if(width>safe*2+64){
                        const left=safe,right=Math.min(width-safe,left+160),bottom=28;
                        ctx.strokeStyle=Qt.alpha(pigment,0.16);ctx.lineWidth=0.8;
                        ctx.beginPath();ctx.moveTo(left,bottom);ctx.lineTo(right,bottom);
                        ctx.moveTo(left,bottom);ctx.quadraticCurveTo((left+right)/2,0,right,bottom);ctx.stroke();
                        if (height > 90) {
                            const baseline = bottom + 7;
                            ctx.strokeStyle = Qt.alpha(pigment, 0.38);
                            ctx.beginPath();
                            ctx.moveTo(left, baseline);
                            ctx.lineTo(right, baseline);
                            for (const x of [left, right]) {
                                ctx.moveTo(x, bottom + 2);
                                ctx.lineTo(x, baseline + 4);
                                ctx.moveTo(x - 3, baseline + 3);
                                ctx.lineTo(x + 3, baseline - 3);
                            }
                            ctx.stroke();
                            ctx.strokeStyle = Qt.alpha(pigment, 0.16);
                        }
                        for(let x=left+12;x<right;x+=16){
                            const t=(x-left)/(right-left),top=bottom-56*t*(1-t);
                            ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,bottom);
                            ctx.lineTo(Math.min(right,x+16),bottom-56*Math.min(1,t+16/(right-left))*(1-Math.min(1,t+16/(right-left))));ctx.stroke();
                        }
                    }
                    ctx.restore();
                    ctx.strokeStyle=Qt.alpha(pigment,0.28);ctx.lineWidth=1;
                    for(const x of [6,width-6])for(const y of [6,height-6]){
                        const sx=x>width/2?-1:1,sy=y>height/2?-1:1;
                        ctx.beginPath();ctx.moveTo(x,y+sy*span);ctx.lineTo(x,y+sy*r);
                        ctx.quadraticCurveTo(x,y,x+sx*r,y);ctx.lineTo(x+sx*span,y);ctx.stroke();
                    }
                }
            }
            Repeater {
                model: engraving.drafting ? 0 : 4
                Item {
                    required property int index
                    readonly property real pad: Math.max(6,root.effectiveCornerRadius*(1-Math.SQRT1_2)+4)
                    x: index % 2 ? engraving.width - pad - 9 : pad
                    y: index >= 2 ? engraving.height - pad - 9 : pad
                    width: 9; height: 9
                    rotation: engraving.drafting ? (index === 1 ? 90 : index === 2 ? 270 : index === 3 ? 180 : 0) : 0
                    Rectangle {
                        width: engraving.drafting ? 9 : 5
                        height: engraving.drafting ? 1 : 5
                        radius: engraving.drafting ? 0 : 2.5
                        color: engraving.ink; opacity: 0.28
                    }
                    Rectangle {
                        visible: !engraving.drafting
                        x: 1; y: 2; width: 3; height: 1; rotation: -35
                        color: Config.resolveColor(root.gradientStops?.[1]?.[0] ?? Colors.background); opacity: 0.9
                    }
                    Rectangle {
                        visible: engraving.drafting
                        width: 1; height: 9
                        color: engraving.ink; opacity: 0.28
                    }
                }
            }
        }
    }

    Loader {
        anchors.fill: parent
        active: root.buttonSurface && Config.theme.buttonFinish !== "default"
            && !root.hasFillColor && root.rectOpacity > 0
        sourceComponent: Item {
            objectName: "button-finish"
            readonly property bool inset: Config.theme.buttonFinish === "inset"
            readonly property real margin: root.controlPressed ? 2 : 3
            opacity: root.rectOpacity
            Rectangle {
                visible: parent.inset
                anchors.fill: parent
                anchors.margins: parent.margin
                color: "transparent"
                border.width: 1
                border.color: Qt.alpha(root.itemColor, 0.48)
                topLeftRadius: root.themeCornerRadius(root.topLeftRadius, parent.margin)
                topRightRadius: root.themeCornerRadius(root.topRightRadius, parent.margin)
                bottomLeftRadius: root.themeCornerRadius(root.bottomLeftRadius, parent.margin)
                bottomRightRadius: root.themeCornerRadius(root.bottomRightRadius, parent.margin)
            }
            Rectangle {
                visible: !parent.inset
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom
                anchors.bottomMargin: parent.margin
                width: Math.min(parent.width * 0.48, 48)
                height: 2
                radius: 1
                color: Qt.alpha(root.itemColor, 0.72)
            }
        }
    }

    border.color: Config.resolveColor(borderData?.[0] ?? "transparent")
    border.width: root.enableBorder ? (borderData?.[1] ?? 0) : 0

    Loader {
        active: root.buttonSurface && (root.styleOverride || Styling.shellStyle) === "glyph"
            && root.width >= 28 && root.height >= 20 && root.rectOpacity > 0
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 4
        opacity: root.rectOpacity
        sourceComponent: Grid {
            objectName: "glyph-button-corner"
            columns: 3
            spacing: 2
            Repeater {
                model: 9
                delegate: Rectangle {
                    required property int index
                    readonly property bool cornerPixel: index < 3 || index % 3 === 2
                    width: 2
                    height: 2
                    color: root.controlPressed || root.variant === "primary" || root.variant === "primaryfocus"
                        ? Colors.primary : root.itemColor
                    opacity: cornerPixel ? (index === 2 ? 0.9 : 0.48) : 0
                }
            }
        }
    }

}
