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
    // Color samples need their exact fill, without a surface shader over it.
    property color fillColor: "transparent"
    readonly property bool hasFillColor: fillColor.a > 0

    property string gradientOrientation: "vertical"
    property bool enableShadow: false
    property bool enableBorder: true
    property bool animateRadius: true
    property real backgroundOpacity: -1  // -1 means use config value

    readonly property var variantConfig: Styling.styleConfig(styleOverride || Styling.shellStyle, variant) || {}

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

    // Passive material details: loaded only on the relevant visible surfaces.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0
            && ["bg", "popup", "pane", "surface", "internalbg"].indexOf(root.variant) !== -1
            && ["smoked-acrylic", "liquid-glass", "prism-glass"].indexOf(root.styleOverride || Styling.shellStyle) !== -1
        sourceComponent: Item {
            id: material
            readonly property string style: root.styleOverride || Styling.shellStyle
            readonly property bool outer: root.variant === "bg" || root.variant === "popup"
            readonly property bool acrylic: style === "smoked-acrylic"
            readonly property bool liquid: style === "liquid-glass"
            readonly property bool prism: style === "prism-glass"
            readonly property color ink: root.itemColor
            opacity: root.rectOpacity
            // Material optics stay static and subtle across the reading area.
            Canvas {
                anchors.fill: parent
                readonly property color pigment: material.ink
                readonly property string finish: material.style
                onPigmentChanged: requestPaint()
                onFinishChanged: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx = getContext("2d");
                    ctx.clearRect(0, 0, width, height);
                    if (width < 24 || height < 24) return;
                    const ink = alpha => Qt.rgba(pigment.r, pigment.g, pigment.b, alpha);
                    ctx.lineWidth = 1;
                    if (material.acrylic) {
                        // Broad diagonal reflection, split into a fine polished glint.
                        const sheen = ctx.createLinearGradient(0, 0, width, height * 0.5);
                        sheen.addColorStop(0, ink(0));
                        sheen.addColorStop(0.24, ink(0.015));
                        sheen.addColorStop(0.30, ink(0.075));
                        sheen.addColorStop(0.32, ink(0.015));
                        sheen.addColorStop(0.50, ink(0));
                        sheen.addColorStop(1, ink(0));
                        ctx.fillStyle = sheen;
                        ctx.fillRect(0, 0, width, height);
                        // Laminated edge: offset hairlines form an apparent glass thickness.
                        for (let i = 0; i < 3; i++) {
                            ctx.strokeStyle = ink(0.19 - i * 0.045);
                            ctx.beginPath();
                            ctx.moveTo(width - 5 - i * 2, 18);
                            ctx.lineTo(width - 5 - i * 2, height - 16 + i * 2);
                            ctx.lineTo(18, height - 16 + i * 2);
                            ctx.stroke();
                        }
                    } else if (material.prism) {
                        // Cut crystal facets alternate broad planes with razor edge highlights.
                        const bevel = Math.min(18, width / 7, height / 7);
                        const facets = [
                            [[0,0],[width,0],[width-bevel,bevel],[bevel,bevel]],
                            [[width,0],[width,height],[width-bevel,height-bevel],[width-bevel,bevel]],
                            [[width,height],[0,height],[bevel,height-bevel],[width-bevel,height-bevel]],
                            [[0,height],[0,0],[bevel,bevel],[bevel,height-bevel]]
                        ];
                        facets.forEach((points, index) => {
                            ctx.fillStyle = ink([0.12,0.035,0.065,0.02][index]);
                            ctx.beginPath(); ctx.moveTo(points[0][0], points[0][1]);
                            points.slice(1).forEach(p => ctx.lineTo(p[0],p[1])); ctx.closePath(); ctx.fill();
                        });
                        ctx.strokeStyle = ink(0.28);
                        ctx.strokeRect(bevel,bevel,width-bevel*2,height-bevel*2);
                        ctx.strokeStyle = ink(0.12);
                        for (const x of [0,width]) for (const y of [0,height]) {
                            ctx.beginPath(); ctx.moveTo(x,y);
                            ctx.lineTo(x ? width-bevel : bevel,y ? height-bevel : bevel); ctx.stroke();
                        }
                        // A pair of fractured reflections stays on the perimeter.
                        ctx.strokeStyle = ink(0.38); ctx.beginPath();
                        ctx.moveTo(bevel+12,bevel); ctx.lineTo(width*0.42,bevel);
                        ctx.moveTo(width-bevel,height*0.62); ctx.lineTo(width-bevel,height-bevel-12); ctx.stroke();
                    } else if (material.liquid) {
                        // Curved meniscus bands suggest a thick, smoothly poured lens.
                        const rim = Math.min(24, width / 5, height / 5);
                        ctx.lineCap = "round";
                        for (let layer=0; layer<3; layer++) {
                            const d = 4 + layer*3;
                            ctx.strokeStyle = ink([0.26,0.10,0.045][layer]);
                            ctx.lineWidth = [2,3,4][layer];
                            ctx.beginPath(); ctx.moveTo(rim,d);
                            ctx.bezierCurveTo(width*0.36,d+6,width*0.65,d-1,width-rim,d);
                            ctx.quadraticCurveTo(width-d,d,width-d,rim); ctx.stroke();
                            ctx.strokeStyle = ink([0.13,0.08,0.035][layer]);
                            ctx.beginPath(); ctx.moveTo(d,height-rim);
                            ctx.quadraticCurveTo(d,height-d,rim,height-d);
                            ctx.bezierCurveTo(width*0.40,height-d-5,width*0.70,height-d+1,width-rim,height-d); ctx.stroke();
                        }
                        const shine = ctx.createRadialGradient(width*0.20,0,1,width*0.20,0,Math.min(width,height)*0.7);
                        shine.addColorStop(0,ink(0.075)); shine.addColorStop(1,ink(0));
                        ctx.fillStyle=shine; ctx.fillRect(0,0,width,height);
                    }
                }
            }
            Rectangle {
                anchors.fill: parent; anchors.margins: material.prism ? 3 : 2
                radius: Math.max(0, root.radius - (material.prism ? 3 : 2))
                color: "transparent"
                border.width: material.liquid ? 2 : 1
                border.color: Qt.alpha(material.ink, material.prism ? 0.18 : material.liquid ? 0.08 : 0.14)
            }
            Rectangle {
                visible: material.acrylic
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                anchors.topMargin: 3; anchors.leftMargin: 12; anchors.rightMargin: 12
                height: 1; color: material.ink; opacity: 0.30
            }
            Rectangle {
                visible: material.acrylic && material.outer
                anchors.right: parent.right; anchors.top: parent.top; anchors.bottom: parent.bottom
                anchors.margins: 4; width: 2
                color: material.ink; opacity: 0.09
            }
        }
    }

    // Monolith: a carved perimeter and a recessed channel along the slab.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0 && (root.styleOverride || Styling.shellStyle) === "monolith"
            && ["bg", "popup", "pane", "surface", "surfaceContainer", "internalbg", "focus"].indexOf(root.variant) !== -1
        sourceComponent: Item {
            id: slab
            readonly property bool outer: root.variant === "bg" || root.variant === "popup"
            readonly property bool inset: root.variant === "internalbg"
            readonly property color ink: root.itemColor
            opacity: root.rectOpacity
            // Staggered cuts and a deep inner seam give the slab a silhouette.
            Rectangle {
                visible: slab.outer
                anchors.fill: parent; anchors.margins: 6
                radius: 0; color: "transparent"
                border.width: 1; border.color: Qt.alpha(slab.ink, 0.10)
            }
            Repeater {
                model: slab.outer && slab.height > 80 ? 3 : 0
                Rectangle {
                    required property int index
                    x: 1; y: 20 + index * 8
                    width: 7 + index * 3; height: 3
                    color: slab.ink; opacity: 0.26 - index * 0.045
                }
            }
            Rectangle {
                visible: slab.outer
                anchors.right: parent.right; anchors.top: parent.top
                width: 7; height: Math.max(0, slab.height * 0.32)
                color: slab.ink; opacity: 0.14
            }
            Repeater {
                model: slab.outer && slab.width > 100 ? 5 : 0
                Rectangle {
                    required property int index
                    x: slab.width - 54 + index * 7; y: slab.height - 9
                    width: 2; height: 5; rotation: 35
                    color: slab.ink; opacity: 0.26
                }
            }
            Rectangle {
                visible: slab.inset
                anchors.left: parent.left; anchors.right: parent.right; anchors.top: parent.top
                height: 3; color: slab.ink; opacity: 0.12
            }
            Rectangle {
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                anchors.margins: slab.outer ? 1 : 0
                height: 1
                color: slab.ink; opacity: slab.inset ? 0.04 : 0.16
            }
            Rectangle {
                anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
                width: slab.outer ? 5 : 2
                color: slab.ink; opacity: slab.inset ? 0.16 : 0.08
            }
            Rectangle {
                visible: slab.outer
                x: 8; y: 14; width: 2; height: Math.max(0, slab.height - 28)
                color: slab.ink; opacity: 0.16
            }
            Rectangle {
                anchors.bottom: parent.bottom; anchors.left: parent.left; anchors.right: parent.right
                height: slab.outer ? 5 : 2
                color: slab.ink; opacity: slab.inset ? 0.025 : 0.08
            }
            Rectangle {
                visible: slab.outer
                anchors.right: parent.right; anchors.bottom: parent.bottom
                anchors.rightMargin: 14; anchors.bottomMargin: 10
                width: 28; height: 2
                color: slab.ink; opacity: 0.30
            }
        }
    }

    // Hardware housings and recessed displays have their own physical details.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0 && (root.styleOverride || Styling.shellStyle) === "terminal-hardware"
            && ["bg", "popup", "pane", "surface", "surfaceContainer", "internalbg", "focus"].indexOf(root.variant) !== -1
        sourceComponent: Item {
            id: chassis
            readonly property bool outer: root.variant === "bg" || root.variant === "popup"
            readonly property bool screen: root.variant === "internalbg"
            readonly property color ink: root.itemColor
            opacity: root.rectOpacity
            Rectangle {
                anchors.fill: parent; anchors.margins: chassis.outer ? 4 : 2
                radius: chassis.outer ? 3 : 1
                color: "transparent"; border.width: 1
                border.color: Qt.alpha(chassis.ink, chassis.screen ? 0.20 : 0.15)
            }
            Rectangle {
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                anchors.margins: chassis.outer ? 3 : 1
                height: chassis.outer ? 2 : 1
                color: chassis.ink; opacity: chassis.screen ? 0.045 : 0.20
            }
            Rectangle {
                anchors.left: parent.left; anchors.top: parent.top; anchors.bottom: parent.bottom
                anchors.margins: chassis.outer ? 3 : 1
                width: 1; color: chassis.ink; opacity: chassis.screen ? 0.07 : 0.16
            }
            Repeater {
                model: chassis.outer && chassis.height > 90 ? 6 : 0
                Rectangle {
                    required property int index
                    x: chassis.width - 11; y: 24 + index * 5
                    width: 5; height: 2; radius: 1
                    color: chassis.ink; opacity: 0.30
                }
            }
            // Passive display texture, with no animation or invented status lights.
            Repeater {
                model: chassis.screen ? Math.min(160, Math.floor(chassis.height / 4)) : 0
                Rectangle {
                    required property int index
                    x: 3; y: 3 + index * 4
                    width: Math.max(0, chassis.width - 6); height: 1
                    color: chassis.ink; opacity: 0.035
                }
            }
            Repeater {
                model: chassis.outer && chassis.width > 100 ? 3 : 0
                Rectangle {
                    required property int index
                    x: 20 + index * 13; y: chassis.height - 8
                    width: 9; height: 2
                    color: chassis.ink; opacity: 0.24
                }
            }
        }
    }

    // Non-interactive drafting marks and case fasteners, behind content.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0 && (root.variant === "bg" || root.variant === "popup")
            && ["blueprint", "terminal-hardware"].indexOf(root.styleOverride || Styling.shellStyle) !== -1
        sourceComponent: Item {
            id: engraving
            readonly property bool drafting: (root.styleOverride || Styling.shellStyle) === "blueprint"
            readonly property color ink: root.itemColor
            opacity: root.rectOpacity
            Repeater {
                model: engraving.drafting ? Math.floor(engraving.width / 20) : 0
                Rectangle {
                    required property int index
                    x: (index + 1) * 20
                    width: 1; height: engraving.height
                    color: engraving.ink; opacity: (index + 1) % 4 === 0 ? 0.14 : 0.055
                }
            }
            Repeater {
                model: engraving.drafting ? Math.floor(engraving.height / 20) : 0
                Rectangle {
                    required property int index
                    y: (index + 1) * 20
                    height: 1; width: engraving.width
                    color: engraving.ink; opacity: (index + 1) % 4 === 0 ? 0.14 : 0.055
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
            Repeater {
                model: 4
                Item {
                    required property int index
                    x: index % 2 ? engraving.width - 15 : 6
                    y: index >= 2 ? engraving.height - 15 : 6
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

    border.color: Config.resolveColor(borderData?.[0] ?? "transparent")
    border.width: root.enableBorder ? (borderData?.[1] ?? 0) : 0

}
