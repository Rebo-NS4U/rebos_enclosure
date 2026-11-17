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
    property bool barSurface: false
    property int canopyVariation: 0
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

    readonly property real effectiveCornerRadius: Math.max(0, Math.min(radius, width / 2, height / 2))

    function themeInsetRadius(inset) {
        return Math.max(0, Math.min(effectiveCornerRadius - inset, (width - 2 * inset) / 2, (height - 2 * inset) / 2));
    }

    function traceThemeFrame(ctx, inset) {
        if (width <= 2 * inset || height <= 2 * inset) return false;
        const r = themeInsetRadius(inset), right = width - inset, bottom = height - inset;
        ctx.beginPath();ctx.moveTo(inset+r,inset);ctx.lineTo(right-r,inset);
        ctx.quadraticCurveTo(right,inset,right,inset+r);ctx.lineTo(right,bottom-r);
        ctx.quadraticCurveTo(right,bottom,right-r,bottom);ctx.lineTo(inset+r,bottom);
        ctx.quadraticCurveTo(inset,bottom,inset,bottom-r);ctx.lineTo(inset,inset+r);
        ctx.quadraticCurveTo(inset,inset,inset+r,inset);
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

    // enableShadow is kept for API compatibility, but we intentionally do
    // NOT apply layer.effect/MultiEffect on this item. That path rasterizes
    // every child (including Text) into an FBO and makes bold bar labels
    // look soft/hazy. Widget chrome shadows live on dedicated shadow items
    // instead of on text-bearing containers.

    // Frosted and Tinted have distinct perimeter construction, not a palette swap.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0
            && ["bg", "popup", "pane", "surface", "surfaceContainer", "internalbg", "focus"].indexOf(root.variant) !== -1
            && ["frosted", "colorful"].indexOf(root.styleOverride || Styling.shellStyle) !== -1
        sourceComponent: Item {
            id: classic
            readonly property bool ice: (root.styleOverride || Styling.shellStyle) === "frosted"
            readonly property bool outer: root.variant === "bg" || root.variant === "popup"
            readonly property color ink: root.itemColor
            readonly property color accent: Colors.primary
            opacity: root.rectOpacity
            Canvas {
                anchors.fill: parent
                readonly property color pigment: classic.ink
                readonly property bool outer: classic.outer
                onOuterChanged: requestPaint()
                readonly property color accent: classic.accent
                readonly property bool ice: classic.ice
                objectName: "classic-glass-canvas"
                readonly property int frostSeed: Math.floor(Math.random()*65536)
                readonly property real cornerRadius: root.effectiveCornerRadius
                onCornerRadiusChanged: requestPaint()
                onPigmentChanged: requestPaint()
                onAccentChanged: requestPaint()
                onIceChanged: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx=getContext("2d");ctx.clearRect(0,0,width,height);
                    if(width<24 || height<24)return;
                    const ink=a=>Qt.rgba(pigment.r,pigment.g,pigment.b,a);
                    const tint=a=>Qt.rgba(accent.r,accent.g,accent.b,a);
                    ctx.save();if(root.traceThemeFrame(ctx,0))ctx.clip();
                    ctx.lineWidth=1;
                    if(ice){
                        // Two soft inset rims and a broken highlight suggest etched ice.
                        for(let layer=0;layer<2;layer++){
                            const d=3+layer*3,r=root.themeInsetRadius(d);
                            ctx.strokeStyle=ink(layer?0.07:0.18);
                            ctx.beginPath();ctx.moveTo(d+r,d);ctx.lineTo(width-d-r,d);
                            ctx.quadraticCurveTo(width-d,d,width-d,d+r);ctx.lineTo(width-d,height-d-r);
                            ctx.quadraticCurveTo(width-d,height-d,width-d-r,height-d);ctx.lineTo(d+r,height-d);
                            ctx.quadraticCurveTo(d,height-d,d,height-d-r);ctx.lineTo(d,d+r);
                            ctx.quadraticCurveTo(d,d,d+r,d);ctx.stroke();
                        }
                        ctx.strokeStyle=ink(0.32);ctx.beginPath();ctx.moveTo(Math.max(18,cornerRadius),3);ctx.lineTo(Math.max(18,cornerRadius,width*0.38),3);ctx.stroke();
                        if(classic.outer){
                            // Fixed fine grain at the perimeter; no texture over text.
                            ctx.fillStyle=ink(0.14);
                            for(let i=0;i<Math.min(200,Math.floor((width+height)/4));i++){
                                const x=8+((i*47)%Math.max(1,width-16));
                                const y=i%2?height-5-(i%5):4+(i%5);
                                ctx.fillRect(x,y,1,1);
                            }
                            // Stable per-surface randomness breaks the repeated crack motif.
                            // Repainting or resizing keeps existing crystals in place.
                            const random=i=>{
                                const value=Math.sin((i+1)*127.1+frostSeed*311.7)*43758.5453;
                                return value-Math.floor(value);
                            };
                            const edge=Math.max(22,cornerRadius+8);
                            let x=edge+random(0)*38;
                            for(let crystal=0;x<width-edge;crystal++){
                                const key=crystal*13;
                                const length=Math.min(height-9,9+random(key+2)*15);
                                const lean=(random(key+3)-0.5)*14;
                                ctx.strokeStyle=ink(0.08+random(key+4)*0.07);ctx.lineWidth=0.7;
                                ctx.beginPath();ctx.moveTo(x,3);ctx.lineTo(x+lean,length);
                                const twigs=1+Math.floor(random(key+5)*3);
                                for(let twig=0;twig<twigs;twig++){
                                    const t=(twig+1)/(twigs+1);
                                    const y=3+t*(length-3),stem=x+t*lean;
                                    const reach=2+random(key+6+twig)*4;
                                    ctx.moveTo(stem,y);ctx.lineTo(stem-reach,y+reach*0.55);
                                    if(random(key+9+twig)>0.35){
                                        ctx.moveTo(stem,y);ctx.lineTo(stem+reach*0.8,y-reach*0.45);
                                    }
                                }
                                ctx.stroke();
                                x+=30+random(key+1)*76;
                            }
                            const bloom=ctx.createRadialGradient(width,0,0,width,0,Math.min(100,width/3,height/2));
                            bloom.addColorStop(0,ink(0.075));bloom.addColorStop(1,ink(0));
                            ctx.fillStyle=bloom;ctx.fillRect(0,0,width,height);
                        }
                    }else{
                        // Offset accent planes, quiet inner keylines and open frame corners.
                        const band=classic.outer?7:3;
                        ctx.fillStyle=tint(0.22);ctx.fillRect(0,12,band,Math.max(0,height-24));
                        ctx.fillStyle=tint(0.12);ctx.fillRect(band+2,22,2,Math.max(0,height-44));
                        ctx.strokeStyle=tint(0.30);ctx.beginPath();
                        const r=root.themeInsetRadius(5);
                        ctx.moveTo(Math.max(18,5+r),5);ctx.lineTo(width-5-r,5);
                        ctx.quadraticCurveTo(width-5,5,width-5,5+r);
                        ctx.lineTo(width-5,Math.max(5+r,height*0.32));ctx.stroke();
                        ctx.strokeStyle=ink(0.09);ctx.beginPath();ctx.moveTo(Math.max(16,11+root.themeInsetRadius(11)),11);ctx.lineTo(width-Math.max(22,11+root.themeInsetRadius(11)),11);ctx.stroke();
                        ctx.fillStyle=tint(0.23);ctx.beginPath();
                        ctx.moveTo(width-34,height-5);ctx.lineTo(width-5,height-5);ctx.lineTo(width-5,height-16);ctx.lineTo(width-23,height-16);ctx.closePath();ctx.fill();
                        if(classic.outer){
                            // Layered colored glass planes recede into the upper and lower margins.
                            for(let plane=0;plane<3;plane++){
                                const depth=12+plane*8;
                                const wash=ctx.createLinearGradient(0,0,0,depth+10);
                                wash.addColorStop(0,tint(0.10-plane*0.02));wash.addColorStop(1,tint(0));
                                ctx.fillStyle=wash;ctx.beginPath();ctx.moveTo(width*0.36+plane*18,0);
                                ctx.lineTo(width,0);ctx.lineTo(width,depth);
                                ctx.lineTo(width*0.51+plane*14,depth);ctx.closePath();ctx.fill();
                            }
                            ctx.fillStyle=tint(0.35);
                            for(let i=0;i<3;i++)ctx.fillRect(18+i*9,height-7,5,2);
                        }
                    }
                    ctx.restore();
                }
            }
        }
    }

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
                readonly property bool outer: material.outer
                onOuterChanged: requestPaint()
                readonly property string finish: material.finish
                objectName: "structural-glass-canvas"
                readonly property real cornerRadius: Math.max(0, Math.min(root.radius, width / 2, height / 2))
                onCornerRadiusChanged: requestPaint()
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
                        const radiusAt = inset => Math.max(0, Math.min(cornerRadius-inset, (width-inset*2)/2, (height-inset*2)/2));
                        const frame = inset => {
                            if (width <= inset*2 || height <= inset*2) return;
                            const r=radiusAt(inset),right=width-inset,bottom=height-inset;
                            ctx.beginPath();ctx.moveTo(inset+r,inset);ctx.lineTo(right-r,inset);
                            ctx.quadraticCurveTo(right,inset,right,inset+r);ctx.lineTo(right,bottom-r);
                            ctx.quadraticCurveTo(right,bottom,right-r,bottom);ctx.lineTo(inset+r,bottom);
                            ctx.quadraticCurveTo(inset,bottom,inset,bottom-r);ctx.lineTo(inset,inset+r);
                            ctx.quadraticCurveTo(inset,inset,inset+r,inset);ctx.stroke();
                        };
                        const step=material.outer ? 10 : 4;
                        ctx.strokeStyle=ink(0.18);frame(step);
                        ctx.strokeStyle=ink(0.08);frame(step+3);
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
                        if(material.outer){
                            // Thick glass splits grazing light into narrow refractive bands.
                            for(let band=0;band<3;band++){
                                const d=12+band*3;
                                const refraction=ctx.createLinearGradient(0,0,width,0);
                                refraction.addColorStop(0,ink(0));refraction.addColorStop(0.28,ink(0.08-band*0.02));
                                refraction.addColorStop(0.64,ink(0.025));refraction.addColorStop(1,ink(0));
                                ctx.strokeStyle=refraction;ctx.lineWidth=2;
                                ctx.beginPath();ctx.moveTo(Math.max(24,cornerRadius),d);
                                ctx.bezierCurveTo(width*0.30,d+5,width*0.70,d-3,width-24,d+2);ctx.stroke();
                            }
                        }
                            // A centered lower reflection fades before the corner mounts.
                            const lip=step;
                            const reflection=ctx.createLinearGradient(0,0,width,0);
                            reflection.addColorStop(0,ink(0));reflection.addColorStop(0.35,ink(0.12));
                            reflection.addColorStop(0.65,ink(0.12));reflection.addColorStop(1,ink(0));
                            ctx.lineWidth=1;ctx.strokeStyle=reflection;
                            const end=lip+reach;
                            if(width>end*2){
                                ctx.beginPath();ctx.moveTo(end,height-lip);
                                ctx.lineTo(width-end,height-lip);ctx.stroke();
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
                            const glow=ctx.createRadialGradient(pad,pad,0,pad,pad,scopeRadius);
                            glow.addColorStop(0,ink(0.015));glow.addColorStop(0.72,ink(0.055));glow.addColorStop(1,ink(0));
                            ctx.fillStyle=glow;ctx.fillRect(0,0,scopeRadius+pad,scopeRadius+pad);
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
                    } else {
                        // Floating sheets have offset edges and a narrow contact shadow.
                        const sheet=(x,y,w,h,inset)=>{
                            if(w<=0||h<=0)return;
                            const r=Math.max(0,Math.min(cornerRadius-inset,w/2,h/2));
                            ctx.beginPath();ctx.moveTo(x+r,y);ctx.lineTo(x+w-r,y);
                            ctx.quadraticCurveTo(x+w,y,x+w,y+r);ctx.lineTo(x+w,y+h-r);
                            ctx.quadraticCurveTo(x+w,y+h,x+w-r,y+h);ctx.lineTo(x+r,y+h);
                            ctx.quadraticCurveTo(x,y+h,x,y+h-r);ctx.lineTo(x,y+r);
                            ctx.quadraticCurveTo(x,y,x+r,y);ctx.closePath();
                        };
                        const gap=material.outer?8:4;
                        sheet(gap,3,width-gap-4,height-gap-3,3);
                        ctx.fillStyle=ink(0.018);ctx.fill();ctx.strokeStyle=ink(0.20);ctx.stroke();
                        sheet(3,gap,width-gap-4,height-gap-3,gap);
                        ctx.strokeStyle=ink(0.08);ctx.stroke();
                        // Layered lower edge supplies a visible sense of separation.
                        ctx.lineWidth=2;ctx.strokeStyle=ink(0.09);
                        const safe=Math.max(16,cornerRadius+gap);
                        ctx.beginPath();ctx.moveTo(safe,height-gap-2);
                        ctx.lineTo(Math.max(safe,width-safe),height-gap-2);ctx.stroke();
                        ctx.lineWidth=1;ctx.strokeStyle=ink(0.23);
                        ctx.beginPath();ctx.moveTo(safe,3);ctx.lineTo(Math.max(safe,width*0.58),3);ctx.stroke();
                        if(material.outer){
                            // Curved grazing reflections separate the suspended sheets.
                            for(let layer=0;layer<3;layer++){
                                ctx.strokeStyle=ink(0.09-layer*0.02);ctx.lineWidth=1;
                                ctx.beginPath();ctx.moveTo(width*0.24,5+layer*4);
                                ctx.bezierCurveTo(width*0.46,18+layer*4,width*0.73,2+layer*3,width-12,18+layer*5);ctx.stroke();
                            }
                        }
                        const sheen=ctx.createLinearGradient(0,0,width,height);
                        sheen.addColorStop(0,ink(0.035));sheen.addColorStop(0.38,ink(0.01));sheen.addColorStop(1,ink(0));
                        ctx.fillStyle=sheen;ctx.fillRect(0,0,width,height);
                    }
                    ctx.restore();
                }
            }
        }
    }

    // Wallpaper architecture, using the selected semantic colors throughout.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0
            && ["bg", "popup", "pane", "surface", "surfaceContainer", "internalbg", "focus"].indexOf(root.variant) !== -1
            && ["canopy", "orbital", "metropolis"].indexOf(root.styleOverride || Styling.shellStyle) !== -1
        sourceComponent: Canvas {
            anchors.fill: parent
            objectName: "wallpaper-theme-canvas"
            readonly property bool barSurface: root.barSurface
            onBarSurfaceChanged: requestPaint()
            readonly property int canopyVariation: root.canopyVariation
            onCanopyVariationChanged: requestPaint()
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
            onPigmentChanged: requestPaint()
            onFinishChanged: requestPaint()
            onOuterChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                const ctx=getContext("2d");ctx.clearRect(0,0,width,height);
                if(width<24||height<24)return;
                const ink=a=>Qt.rgba(pigment.r,pigment.g,pigment.b,a);
                ctx.lineWidth=1;
                const safe=Math.max(18,cornerRadius+6);
                // Clip every material layer to the shared rounded surface.
                ctx.save();
                if(root.traceThemeFrame(ctx,0))ctx.clip();
                if(finish === "canopy"){
                    // Translucent fabric drapes use the selected palette.
                    const fabric=a=>Qt.rgba(accent.r*0.65+secondaryAccent.r*0.35,accent.g*0.65+secondaryAccent.g*0.35,accent.b*0.65+secondaryAccent.b*0.35,a);
                    // Taut diagonal fabric sails with folded tips, grazing light and soft shadows.
                    function drapedCanopy(depth, shape) {
                        const split=0.39+(shape%4)*0.055;
                        const glow=ctx.createLinearGradient(0,0,width,depth);
                        glow.addColorStop(0,Qt.rgba(secondaryAccent.r,secondaryAccent.g,secondaryAccent.b,0.08));
                        glow.addColorStop(0.55,fabric(0.025));
                        glow.addColorStop(1,Qt.rgba(accent.r,accent.g,accent.b,0.12));
                        ctx.fillStyle=glow;ctx.fillRect(0,0,width,depth);
                        for(let layer=0;layer<3;layer++){
                            const reach=depth*(1-layer*0.24);
                            const pinch=split+(layer-1)*0.11;
                            const edge=reach*(0.12+layer*0.04);
                            function drape(offset) {
                                ctx.beginPath();ctx.moveTo(0,0);ctx.lineTo(width,0);
                                ctx.lineTo(width,edge+offset);
                                // Long diagonal hems meet at a crisp folded tip, without scallops.
                                ctx.lineTo(width*(pinch+0.16),reach*0.58+offset);
                                ctx.lineTo(width*pinch,reach*0.88+offset);
                                ctx.lineTo(width*(pinch+0.055),reach*0.55+offset);
                                ctx.bezierCurveTo(width*(pinch-0.10),reach*0.54+offset,
                                    width*0.12,reach*0.32+offset,0,edge+offset);
                                ctx.closePath();
                            }
                            // Broad, fading contact shadow separates the suspended sheets.
                            const shadow=ctx.createLinearGradient(0,reach*0.25,0,reach+8);
                            shadow.addColorStop(0,Qt.rgba(backdrop.r,backdrop.g,backdrop.b,0));
                            shadow.addColorStop(0.7,Qt.rgba(backdrop.r,backdrop.g,backdrop.b,0.13));
                            shadow.addColorStop(1,Qt.rgba(backdrop.r,backdrop.g,backdrop.b,0));
                            ctx.fillStyle=shadow;drape(Math.min(6,depth*0.09));ctx.fill();
                            const cloth=ctx.createLinearGradient(0,0,width,reach);
                            cloth.addColorStop(0,fabric(0.12+layer*0.035));
                            cloth.addColorStop(0.23,fabric(0.32));
                            cloth.addColorStop(0.43,fabric(0.11));
                            cloth.addColorStop(0.67,Qt.rgba(secondaryAccent.r,secondaryAccent.g,secondaryAccent.b,0.22));
                            cloth.addColorStop(0.86,fabric(0.38));
                            cloth.addColorStop(1,fabric(0.16));
                            ctx.fillStyle=cloth;drape(0);ctx.fill();
                        }
                    }

                    if(barSurface){
                        // Broad drapes stay confined to the header.
                        // Different span counts and proportions, stable until the next opening.
                        const profiles=[
                            [1], [0.46,0.54], [0.28,0.44,0.28],
                            [0.22,0.28,0.28,0.22], [0.16,0.19,0.30,0.19,0.16],
                            [0.52,0.30,0.18]
                        ];
                        const v=((canopyVariation % profiles.length)+profiles.length)%profiles.length;
                        const spans=profiles[v];
                        const roof=Math.min([72,76,68,60,52,78][v],height*0.22);
                        drapedCanopy(roof,spans.length+3);
                    }else if(outer){
                        const drop=Math.min(70,height*0.22);
                        drapedCanopy(drop,5);
                        // Ground-level shade echoes the roof without framing the content.
                        const ground=ctx.createLinearGradient(0,height-24,0,height);
                        ground.addColorStop(0,fabric(0));ground.addColorStop(1,fabric(0.12));
                        ctx.fillStyle=ground;ctx.fillRect(0,height-24,width,24);

                    }
                }else if(finish === "orbital"){
                    // Elliptical orbital tracks wrap a quiet, recessed space capsule.
                    ctx.strokeStyle=ink(0.20);ctx.lineWidth=1;
                    if(root.traceThemeFrame(ctx,outer?6:3))ctx.stroke();
                    if(inset){
                        ctx.strokeStyle=ink(0.08);
                        if(root.traceThemeFrame(ctx,6))ctx.stroke();
                    }
                    // Deterministic jitter spreads a stable star field over the entire surface.
                    // Low opacity keeps stars behind content, with occasional brighter points.
                    for(let row=0;row<Math.ceil(height/46);row++){
                        for(let col=0;col<Math.ceil(width/54);col++){
                            const seed=Math.abs(Math.sin((col+1)*127.1+(row+1)*311.7)*43758.5453);
                            const fraction=seed-Math.floor(seed);
                            const x=col*54+7+fraction*38;
                            const y=row*46+6+((fraction*7.31)%1)*32;
                            const bright=fraction>0.88;
                            ctx.fillStyle=ink(bright?0.40:0.14+fraction*0.12);
                            ctx.beginPath();ctx.arc(x,y,bright?1.15:0.55,0,Math.PI*2);ctx.fill();
                            if(bright){
                                ctx.strokeStyle=ink(0.16);ctx.lineWidth=0.7;
                                ctx.beginPath();ctx.moveTo(x-3,y);ctx.lineTo(x+3,y);
                                ctx.moveTo(x,y-3);ctx.lineTo(x,y+3);ctx.stroke();
                            }
                        }
                    }
                    if(outer){
                        for(const bottom of [false,true]){
                            ctx.save();
                            ctx.translate(bottom?width-safe:safe,bottom?height-8:8);
                            ctx.rotate(bottom?-0.24:0.24);
                            ctx.scale(1,0.32);
                            for(let ring=0;ring<3;ring++){
                                ctx.strokeStyle=Qt.rgba(accent.r,accent.g,accent.b,0.34-ring*0.07);
                                ctx.beginPath();ctx.arc(0,0,24+ring*15,0,Math.PI*2);ctx.stroke();
                            }
                            ctx.restore();
                        }
                        // Satellites remain attached to the perimeter orbit tracks.
                        ctx.fillStyle=Qt.rgba(accent.r,accent.g,accent.b,0.8);
                        for(const point of [[safe+35,14],[width-safe-35,height-14]]){
                            ctx.beginPath();ctx.arc(point[0],point[1],2.5,0,Math.PI*2);ctx.fill();
                        }

                    }
                }else{
                    // City architecture follows the selected palette for glass, frames and windows.
                    const frame=a=>Qt.rgba(accent.r,accent.g,accent.b,a);
                    const windowLight=a=>Qt.rgba(secondaryAccent.r,secondaryAccent.g,secondaryAccent.b,a);
                    const facade=a=>Qt.rgba(backdrop.r,backdrop.g,backdrop.b,a);
                    ctx.lineWidth=1;ctx.strokeStyle=frame(outer?0.24:0.12);
                    if(root.traceThemeFrame(ctx,outer?5:3))ctx.stroke();
                    // A narrow reflected sky band gives depth without tinting all content.
                    const sky=ctx.createLinearGradient(0,0,0,Math.min(height,85));
                    sky.addColorStop(0,frame(outer?0.12:0.045));
                    sky.addColorStop(0.5,frame(0.025));sky.addColorStop(1,frame(0));
                    ctx.fillStyle=sky;ctx.fillRect(0,0,width,Math.min(height,85));
                    if(outer && barSurface){
                        // A city cornice designed for the bar's shallow proportions.
                        // Architecture occupies only the bottom eight pixels; controls stay clear.
                        const margin=Math.max(16,cornerRadius+4),base=height-2;
                        ctx.strokeStyle=frame(0.30);ctx.lineWidth=0.8;
                        ctx.beginPath();ctx.moveTo(margin,base);ctx.lineTo(width-margin,base);ctx.stroke();
                        let building=0;
                        for(let x=margin+5;x<width-margin-8;x+=22,building++){
                            const roof=base-[4,7,5,8,3,6][building%6];
                            const right=Math.min(width-margin,x+16);
                            ctx.fillStyle=facade(0.30);ctx.fillRect(x,roof,right-x,base-roof);
                            ctx.strokeStyle=frame(building%3===0?0.38:0.20);
                            ctx.beginPath();ctx.moveTo(x,base);ctx.lineTo(x,roof);
                            ctx.lineTo(right,roof);ctx.lineTo(right,base);ctx.stroke();
                            ctx.fillStyle=windowLight(building%3===0?0.58:0.30);
                            for(let column=0;column<3;column++){
                                if((building+column)%3!==0 && x+3+column*4<right-1)
                                    ctx.fillRect(x+3+column*4,base-3,1.5,1.5);
                            }
                        }
                        // A luminous roofline and stepped end caps frame the skyline.
                        const crown=ctx.createLinearGradient(0,0,width,0);
                        crown.addColorStop(0,frame(0));crown.addColorStop(0.25,frame(0.22));
                        crown.addColorStop(0.50,frame(0.38));crown.addColorStop(0.75,frame(0.22));crown.addColorStop(1,frame(0));
                        ctx.strokeStyle=crown;ctx.lineWidth=1;
                        ctx.beginPath();ctx.moveTo(margin,3);ctx.lineTo(width-margin,3);ctx.stroke();
                        for(const side of [0,1]){
                            ctx.save();if(side){ctx.translate(width,0);ctx.scale(-1,1);}
                            ctx.strokeStyle=frame(0.36);ctx.lineWidth=1;
                            ctx.beginPath();ctx.moveTo(5,height*0.66);ctx.lineTo(5,height*0.40);
                            ctx.lineTo(8,height*0.40);ctx.lineTo(8,height*0.25);
                            ctx.lineTo(12,height*0.25);ctx.stroke();ctx.restore();
                        }
                    }else if(outer){
                        // Soft cloud banks hang from the upper edge, fading before the content.
                        const cloudDepth=Math.min(52,height*0.18);
                        for(let layer=0;layer<2;layer++){
                            const mist=ctx.createLinearGradient(0,0,0,cloudDepth);
                            mist.addColorStop(0,layer===0?ink(0.07):frame(0.10));
                            mist.addColorStop(0.48,layer===0?ink(0.045):frame(0.055));
                            mist.addColorStop(1,frame(0));
                            ctx.fillStyle=mist;ctx.beginPath();ctx.moveTo(-48,0);
                            ctx.lineTo(-48,cloudDepth*0.40);
                            const span=layer===0?126:94;
                            for(let x=-48;x<width+span;x+=span){
                                const rise=cloudDepth*(0.55+0.18*Math.sin(x*0.023+layer*2));
                                const base=cloudDepth*(layer===0?0.30:0.18);
                                ctx.bezierCurveTo(x+span*0.18,rise,x+span*0.40,rise,x+span*0.52,base+cloudDepth*0.12);
                                ctx.bezierCurveTo(x+span*0.68,base+cloudDepth*0.40,x+span*0.86,base+cloudDepth*0.30,x+span,base);
                            }
                            ctx.lineTo(width+span*2,0);ctx.closePath();ctx.fill();
                        }
                        // Overlapping facades vary in width, setback and roof height.
                        // Their silhouettes remain in the lower margin, below the reading area.
                        const base=height-5;
                        let index=0;
                        for(let x=safe-8;x<width-safe-12;index++){
                            const towerWidth=[29,41,24,35,31][index%5];
                            const towerHeight=Math.min(height*0.18,[36,54,29,66,43,48,32][index%7]);
                            const right=Math.min(width-safe,x+towerWidth);
                            const roof=base-towerHeight;
                            const setback=Math.min(7,(right-x)*0.20);
                            ctx.fillStyle=facade(0.42);ctx.beginPath();ctx.moveTo(x,base);
                            ctx.lineTo(x,roof+7);ctx.lineTo(x+setback,roof+7);
                            ctx.lineTo(x+setback,roof);ctx.lineTo(right-setback,roof);
                            ctx.lineTo(right-setback,roof+5);ctx.lineTo(right,roof+5);
                            ctx.lineTo(right,base);ctx.closePath();ctx.fill();
                            ctx.strokeStyle=frame(index%3===0?0.32:0.17);ctx.lineWidth=1;ctx.stroke();
                            // Lit rooms are sparse and irregular, rather than a repeated checkerboard.
                            for(let floor=0;floor<Math.floor((towerHeight-12)/7);floor++){
                                for(let column=0;column<Math.floor((right-x-8)/7);column++){
                                    const room=(index*13+floor*7+column*11)%9;
                                    if(room<4)continue;
                                    ctx.fillStyle=room===8?frame(0.36):windowLight(room===7?0.58:0.30);
                                    ctx.fillRect(x+5+column*7,roof+12+floor*7,2,3);
                                }
                            }
                            x+=towerWidth+4;
                        }
                        // Slender vertical mullions and palette-colored lobby light frame the city glass.
                        for(const x of [8,width-9]){
                            ctx.strokeStyle=frame(0.22);ctx.beginPath();
                            ctx.moveTo(x,safe);ctx.lineTo(x,height-safe);ctx.stroke();
                            ctx.strokeStyle=frame(0.07);ctx.beginPath();
                            ctx.moveTo(x+3,safe+12);ctx.lineTo(x+3,height-safe-12);ctx.stroke();
                        }
                        const lobby=ctx.createLinearGradient(0,height-18,0,height);
                        lobby.addColorStop(0,windowLight(0));lobby.addColorStop(1,windowLight(0.09));
                        ctx.fillStyle=lobby;ctx.fillRect(0,height-18,width,18);
                    }
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
            onPigmentChanged: requestPaint()
            onOuterChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                const ctx=getContext("2d");ctx.clearRect(0,0,width,height);
                if(width<24||height<24)return;
                const ink=a=>Qt.rgba(pigment.r,pigment.g,pigment.b,a);
                ctx.save();if(root.traceThemeFrame(ctx,0))ctx.clip();
                const reflection=ctx.createLinearGradient(0,0,0,Math.min(height,outer?32:12));
                reflection.addColorStop(0,ink(outer?0.07:0.025));reflection.addColorStop(1,ink(0));
                ctx.fillStyle=reflection;ctx.fillRect(0,0,width,Math.min(height,outer?32:12));
                if(outer){
                    const safe=Math.max(18,cornerRadius+5);
                    ctx.strokeStyle=ink(0.20);ctx.lineWidth=0.8;
                    ctx.beginPath();ctx.moveTo(safe,3);ctx.lineTo(Math.max(safe,width*0.44),3);ctx.stroke();
                    ctx.strokeStyle=ink(0.08);
                    ctx.beginPath();ctx.moveTo(width*0.56,height-4);ctx.lineTo(Math.max(width*0.56,width-safe),height-4);ctx.stroke();
                }
                ctx.restore();
            }
        }
    }

    // Monolith: angular incisions engraved into a mineral-grained stone slab.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0 && (root.styleOverride || Styling.shellStyle) === "monolith"
            && ["bg", "popup", "bar", "pane", "surface", "surfaceContainer", "internalbg", "focus", "surfaceVariant"].indexOf(root.variant) !== -1
        sourceComponent: Canvas {
            anchors.fill: parent
            objectName: "surface-edge-canvas"
            readonly property real cornerRadius: root.effectiveCornerRadius
            readonly property color pigment: root.itemColor
            readonly property color shadowInk: Qt.darker(Colors.background, 1.8)
            readonly property color accent: Colors.primary
            readonly property color secondaryAccent: Colors.secondary
            readonly property bool outer: root.variant === "bg" || root.variant === "popup" || root.variant === "bar" || root.barSurface
            readonly property bool inset: root.variant === "internalbg"
            opacity: root.rectOpacity
            onCornerRadiusChanged: requestPaint()
            onPigmentChanged: requestPaint()
            onShadowInkChanged: requestPaint()
            onAccentChanged: requestPaint()
            onSecondaryAccentChanged: requestPaint()
            onOuterChanged: requestPaint()
            onInsetChanged: requestPaint()
            onWidthChanged: requestPaint()
            onHeightChanged: requestPaint()
            onPaint: {
                const ctx=getContext("2d");ctx.clearRect(0,0,width,height);
                if(width<24||height<24)return;
                ctx.save();if(root.traceThemeFrame(ctx,0))ctx.clip();
                // Deterministic mineral stipple and tiny diagonal tool marks.
                // Bound the sample count on large panels; no animation or random repaint noise.
                const grainStep=Math.max(6,Math.ceil(Math.sqrt(width*height/10000)));
                for(let gy=0;gy<height;gy+=grainStep){
                    for(let gx=0;gx<width;gx+=grainStep){
                        let hash=((gx+11)*374761393+(gy+7)*668265263)|0;
                        hash=((hash^(hash>>>13))*1274126177)|0;
                        const seed=(hash^(hash>>>16))>>>0;
                        const x=gx+(seed&255)/256*grainStep;
                        const y=gy+((seed>>>8)&255)/256*grainStep;
                        const strength=inset?0.025:outer?0.065:0.045;
                        ctx.fillStyle=Qt.alpha(pigment,strength*(0.55+((seed>>>16)&15)/20));
                        const size=(seed&3)===0?1.2:0.7;
                        ctx.fillRect(x,y,size,size);
                        if(!inset && seed%19===0){
                            ctx.strokeStyle=Qt.alpha(pigment,strength*0.7);ctx.lineWidth=0.6;
                            const cut=2+((seed>>>20)&3);
                            ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x+cut,y-cut);ctx.stroke();
                        }
                    }
                }
                // A lit upper shoulder and shaded lower lip give the slab thickness.
                const rim=ctx.createLinearGradient(0,0,width*0.25,height);
                rim.addColorStop(0,Qt.alpha(pigment,inset?0.06:0.26));
                rim.addColorStop(0.40,Qt.alpha(pigment,0.025));
                rim.addColorStop(0.75,Qt.alpha(shadowInk,0.08));
                rim.addColorStop(1,Qt.alpha(shadowInk,inset?0.16:0.48));
                ctx.strokeStyle=rim;ctx.lineWidth=outer?3:2;
                if(root.traceThemeFrame(ctx,1.5))ctx.stroke();
                // A fine rim follows the selected rounded frame.
                ctx.lineWidth=0.8;ctx.strokeStyle=Qt.alpha(pigment,inset?0.045:0.085);
                if(root.traceThemeFrame(ctx,0.8))ctx.stroke();
                if(!inset){
                    // Incised channels: shadowed upper-left walls and a lit lower-right lip.
                    // All shading stays inside the groove; no floating cast shadow.
                    function engrave(points){
                        function edge(dx,dy,color,lineWidth){
                            ctx.strokeStyle=color;ctx.lineWidth=lineWidth;ctx.beginPath();
                            ctx.moveTo(points[0][0]+dx,points[0][1]+dy);
                            for(let j=1;j<points.length;j++)ctx.lineTo(points[j][0]+dx,points[j][1]+dy);
                            ctx.stroke();
                        }
                        // Broad dark channel, dark upper wall, then a thin catching edge.
                        edge(0,0,Qt.alpha(shadowInk,outer?0.52:0.36),outer?3:2);
                        edge(-0.65,-0.65,Qt.alpha(shadowInk,0.72),1.2);
                        edge(0.9,0.9,Qt.alpha(pigment,outer?0.25:0.16),0.8);
                    }
                    // Shallow recessed planes outlined by straight 45-degree carvings.
                    const depth=Math.min(outer?64:28,height*0.36,width*0.30);
                    const reach=Math.min(width*0.48,outer?240:108);
                    for(let i=0;i<3;i++){
                        const d=depth*(1-i*0.27);
                        const run=reach-i*depth*0.46;
                        ctx.fillStyle=Qt.alpha(shadowInk,outer?0.055:0.035);
                        ctx.beginPath();ctx.moveTo(width-run,0);ctx.lineTo(width,0);
                        ctx.lineTo(width,d);ctx.lineTo(width-run+d,d);
                        ctx.closePath();ctx.fill();
                        engrave([[width-run,0],[width-run+d,d],[width,d]]);
                        ctx.fillStyle=Qt.alpha(shadowInk,outer?0.045:0.025);
                        ctx.beginPath();ctx.moveTo(0,height);ctx.lineTo(run,height);
                        ctx.lineTo(run-d,height-d);ctx.lineTo(0,height-d);
                        ctx.closePath();ctx.fill();
                        engrave([[run,height],[run-d,height-d],[0,height-d]]);
                    }
                    // Narrow side facets repeat the corner geometry without filling the face.
                    if(height>100){
                        const side=Math.min(outer?18:8,width*0.08,height*0.08);
                        const top=height*0.30,bottom=height*0.70;
                        for(let i=0;i<3;i++){
                            const d=side*(1-i*0.27);
                            const a=top+i*side*0.46,b=bottom-i*side*0.46;
                            ctx.fillStyle=Qt.alpha(shadowInk,outer?0.055:0.035);
                            ctx.beginPath();ctx.moveTo(0,a);ctx.lineTo(d,a+d);
                            ctx.lineTo(d,b-d);ctx.lineTo(0,b);ctx.closePath();ctx.fill();
                            engrave([[0,a],[d,a+d],[d,b-d],[0,b]]);
                            ctx.fillStyle=Qt.alpha(shadowInk,outer?0.045:0.025);
                            ctx.beginPath();ctx.moveTo(width,a);ctx.lineTo(width-d,a+d);
                            ctx.lineTo(width-d,b-d);ctx.lineTo(width,b);ctx.closePath();ctx.fill();
                            engrave([[width,a],[width-d,a+d],[width-d,b-d],[width,b]]);
                        }
                    }
                }
                ctx.restore();
            }
        }
    }

    // Hardware housings and recessed displays have their own physical details.
    Loader {
        anchors.fill: parent
        active: !root.hasFillColor && root.rectOpacity > 0 && (root.styleOverride || Styling.shellStyle) === "terminal-hardware"
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
                color: "transparent"; border.width: 1
                border.color: Qt.alpha(chassis.ink, chassis.outer ? 0.15 : 0.07)
            }
            Canvas {
                anchors.fill: parent
                objectName: "surface-edge-canvas"
                readonly property real cornerRadius: root.effectiveCornerRadius
                readonly property color pigment: chassis.ink
                readonly property bool outer: chassis.outer
                readonly property bool screen: chassis.screen
                onOuterChanged: requestPaint()
                onScreenChanged: requestPaint()
                onCornerRadiusChanged: requestPaint()
                onPigmentChanged: requestPaint()
                onWidthChanged: requestPaint()
                onHeightChanged: requestPaint()
                onPaint: {
                    const ctx=getContext("2d");ctx.clearRect(0,0,width,height);
                    if(width<24||height<24)return;
                    ctx.save();if(root.traceThemeFrame(ctx,0))ctx.clip();
                    const brushed=ctx.createLinearGradient(0,0,0,chassis.outer?20:8);
                    brushed.addColorStop(0,Qt.alpha(pigment,0.14));
                    brushed.addColorStop(0.35,Qt.alpha(pigment,0.035));brushed.addColorStop(1,Qt.alpha(pigment,0));
                    ctx.fillStyle=brushed;ctx.fillRect(0,0,width,chassis.outer?20:8);
                    // One inset bezel and a small vent bank keep the housing legible.
                    if(chassis.outer){
                        const safe=Math.max(20,cornerRadius+8);
                        if(width>safe*2+40 && height>safe*2+24){
                            for(let i=0;i<4;i++){
                                const y=safe+i*6;
                                ctx.fillStyle=Qt.alpha(pigment,0.16);
                                ctx.fillRect(width-12,y,5,1);
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
                    // Ruled vellum: crisp near its edges, quiet beneath content.
                    for(let axis=0;axis<2;axis++){
                        const extent=axis?height:width;
                        for(let n=20;n<extent;n+=20){
                            const major=n%80===0;
                            const wash=ctx.createLinearGradient(axis?0:n,axis?n:0,axis?width:n,axis?n:height);
                            const alpha=major?0.13:0.055;
                            wash.addColorStop(0,Qt.alpha(pigment,alpha));
                            wash.addColorStop(0.22,Qt.alpha(pigment,alpha*0.22));
                            wash.addColorStop(0.78,Qt.alpha(pigment,alpha*0.22));
                            wash.addColorStop(1,Qt.alpha(pigment,alpha));
                            ctx.strokeStyle=wash;ctx.lineWidth=major?0.8:0.5;
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
