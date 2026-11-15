pragma ComponentBehavior: Bound
import QtQuick
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
    readonly property bool ditheredOutline: usesDitherGrid
        && enableBorder && border.width > 0 && border.color.a > 0

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

    // enableShadow is kept for API compatibility, but we intentionally do
    // NOT apply layer.effect/MultiEffect on this item. That path rasterizes
    // every child (including Text) into an FBO and makes bold bar labels
    // look soft/hazy. Widget chrome shadows live on dedicated shadow items
    // instead of on text-bearing containers.

    // Structural glass: perimeter details leave the central reading area clear.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0
            && ["bg", "popup", "pane", "surface", "surfaceContainer", "internalbg", "focus"].indexOf(root.variant) !== -1
            && ["glass-vault", "radar-station", "suspended-film"].indexOf(root.styleOverride || Styling.shellStyle) !== -1
        sourceComponent: Item {
            id: material
            readonly property string finish: root.styleOverride || Styling.shellStyle
            readonly property bool outer: root.variant === "bg" || root.variant === "popup"
            readonly property color ink: root.itemColor
            opacity: root.rectOpacity
            Canvas {
                anchors.fill: parent
                readonly property color pigment: material.ink
                readonly property string finish: material.finish
                onPigmentChanged: requestPaint()
                onFinishChanged: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx=getContext("2d"); ctx.clearRect(0,0,width,height);
                    if (width<24 || height<24) return;
                    const ink=a=>Qt.rgba(pigment.r,pigment.g,pigment.b,a);
                    ctx.lineWidth=1;
                    if (finish === "glass-vault") {
                        const step=material.outer ? 10 : 4;
                        ctx.strokeStyle=ink(0.18); ctx.strokeRect(step,step,width-step*2,height-step*2);
                        ctx.strokeStyle=ink(0.08); ctx.strokeRect(step+3,step+3,width-step*2-6,height-step*2-6);
                        // Massive corner clamps hold a continuous clear block.
                        const span=Math.min(material.outer ? 26 : 12,width/4,height/4);
                        for (const x of [3,width-3]) for (const y of [3,height-3]) {
                            const sx=x>width/2 ? -1 : 1, sy=y>height/2 ? -1 : 1;
                            ctx.strokeStyle=ink(0.32);ctx.lineWidth=material.outer?5:2;
                            ctx.beginPath();ctx.moveTo(x,y+sy*span);ctx.lineTo(x,y);ctx.lineTo(x+sx*span,y);ctx.stroke();
                            ctx.lineWidth=1;ctx.strokeStyle=ink(0.55);
                            ctx.beginPath();ctx.moveTo(x+sx*2,y+sy*span);ctx.lineTo(x+sx*2,y+sy*2);ctx.lineTo(x+sx*span,y+sy*2);ctx.stroke();
                        }
                        ctx.fillStyle=ink(0.10);ctx.fillRect(12,height-8,Math.max(0,width-24),5);
                        ctx.fillStyle=ink(0.18);ctx.fillRect(width-8,12,4,Math.max(0,height-24));
                    } else if (finish === "radar-station") {
                        // Fixed bearing scales: no sweep, motion or simulated live data.
                        ctx.strokeStyle=ink(0.12);ctx.strokeRect(8,8,width-16,height-16);
                        const radius=Math.min(54,width*0.22,height*0.28);
                        for (const corner of [0,1]) {
                            const x=corner?width-12:12,y=corner?height-12:12;
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
                            ctx.strokeStyle=ink(0.30);
                            for(let x=76;x<width-76;x+=12){ctx.beginPath();ctx.moveTo(x,5);ctx.lineTo(x,x%36===4?11:8);ctx.stroke();}
                            for(const x of [8,width-8]){ctx.beginPath();ctx.moveTo(x-4,height/2);ctx.lineTo(x+4,height/2);ctx.moveTo(x,height/2-4);ctx.lineTo(x,height/2+4);ctx.stroke();}
                            ctx.fillStyle=ink(0.25);
                            for(let i=0;i<5;i++)ctx.fillRect(width/2-19+i*8,height-7,5,2);
                        }
                    } else {
                        // Offset membranes stretch between four tension points.
                        for(let layer=0;layer<3;layer++) {
                            const d=5+layer*3;
                            ctx.strokeStyle=ink(0.22-layer*0.065);ctx.strokeRect(d,d,width-2*d,height-2*d);
                        }
                        for(const x of [7,width-7])for(const y of [7,height-7]){
                            const sx=x>width/2?-1:1,sy=y>height/2?-1:1;
                            ctx.strokeStyle=ink(0.40);ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+sx*12,y+sy*12);ctx.stroke();
                            ctx.fillStyle=ink(0.32);ctx.fillRect(x-2,y-2,4,4);
                        }
                        ctx.strokeStyle=ink(0.14);
                        for(let y=24;y<height-24;y+=5){ctx.beginPath();ctx.moveTo(3,y);ctx.lineTo(7,y+2);ctx.moveTo(width-7,y);ctx.lineTo(width-3,y+2);ctx.stroke();}
                        // A quiet diagonal fold gives the membrane tension without clutter.
                        const sheen=ctx.createLinearGradient(0,0,width,height);
                        sheen.addColorStop(0,ink(0));sheen.addColorStop(0.40,ink(0));sheen.addColorStop(0.42,ink(0.025));sheen.addColorStop(0.60,ink(0));sheen.addColorStop(1,ink(0));
                        ctx.fillStyle=sheen;ctx.fillRect(0,0,width,height);
                    }
                }
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

    // Parent directly to the root: ClippingRectangle composites its native
    // border above its contentItem, so a normal child cannot replace that line.
    // This ring is drawn above the border without capturing any text again.
    Loader {
        parent: root
        anchors.fill: parent
        z: 100
        active: root.ditheredOutline && root.visible && width > 0 && height > 0
        sourceComponent: ShaderEffect {
            objectName: "dithered-outline"
            property vector2d size: Qt.vector2d(width, height)
            property vector4d corners: Qt.vector4d(root.topLeftRadius, root.topRightRadius,
                root.bottomLeftRadius, root.bottomRightRadius)
            property real strokeWidth: Config.theme.ditherBorder === "band" ? Styling.ditherEdgeWidth
                : Config.theme.ditherBorder === "double"
                ? root.border.width : Math.max(root.border.width, root.ditherCellSize)
            property real nativeStrokeWidth: root.border.width
            property real cellSize: root.ditherCellSize
            property color edgeColor: root.border.color
            property color baseColor: root.halftoneBackgroundColor
            property color surfaceDotColor: root.gradientType === "halftone"
                ? root.halftoneDotColor : root.halftoneBackgroundColor
            vertexShader: Config.theme.ditherBorder === "band"
                ? "dither_uniform_edge.vert.qsb" : "dotted_outline.vert.qsb"
            fragmentShader: Config.theme.ditherBorder === "band" ? "dither_uniform_edge.frag.qsb"
                : Config.theme.ditherBorder === "double"
                ? "double_outline.frag.qsb" : "dotted_outline.frag.qsb"
        }
    }
}
