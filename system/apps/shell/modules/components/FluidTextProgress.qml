pragma ComponentBehavior: Bound

import QtQuick
import qs.config
import qs.modules.theme

Item {
    id: root

    property string text: ""
    property string fontFamily: Config.theme.font
    property int pixelSize: Styling.fontSize(-1)
    property bool bold: true
    property int elide: Text.ElideRight
    property int verticalAlignment: Text.AlignVCenter
    property real progress: 0.0
    property bool isPlaying: false
    property color baseColor: Colors.overBackground
    property color fillColor: Colors.primary

    readonly property bool showFluidBar: root.isPlaying && root.progress > 0.0

    implicitWidth: Math.min(baseText.implicitWidth, 200)
    implicitHeight: Math.max(inkBounds.height + (root.showFluidBar ? 6 : 0), 20)

    FontMetrics {
        id: textMetrics
        font: baseText.font
    }
    readonly property rect inkBounds: textMetrics.tightBoundingRect(
        textMetrics.elidedText(root.text, root.elide, Math.max(0, root.width)))

    property real phase: 0.0

    FrameAnimation {
        running: root.isPlaying && root.visible && root.width > 0
        onTriggered: {
            const dt = (frameTime > 0 && frameTime < 0.1) ? frameTime : 0.016;
            root.phase = (root.phase + 2.5 * dt) % (Math.PI * 2);
            if (root.showFluidBar) {
                wavyCanvas.requestPaint();
            }
        }
    }

    Text {
        id: baseText
        anchors.left: parent.left
        anchors.right: parent.right
        height: implicitHeight
        // Center the visible text and optional waveform as one group.
        y: (root.height - root.inkBounds.height - (root.showFluidBar ? 6 : 0)) / 2
            - root.inkBounds.y - baselineOffset
        text: root.text
        font.family: root.fontFamily
        font.pixelSize: root.pixelSize
        font.bold: root.bold
        color: root.baseColor
        elide: root.elide
        verticalAlignment: Text.AlignTop
        renderType: Text.NativeRendering
        font.hintingPreference: Font.PreferFullHinting
    }

    Canvas {
        id: wavyCanvas
        y: (root.height + root.inkBounds.height - height + 1) / 2
        anchors.left: parent.left
        anchors.right: parent.right
        height: 5
        visible: root.showFluidBar
        antialiasing: true

        onPaint: {
            const ctx = getContext("2d");
            ctx.reset();
            const w = width;
            const h = height;
            if (w <= 0 || h <= 0) return;

            const centerY = h / 2;
            const playedX = Math.max(0.0, Math.min(w, w * root.progress));

            // Unplayed track line (subtle background line)
            if (playedX < w) {
                ctx.beginPath();
                ctx.strokeStyle = Qt.rgba(root.baseColor.r, root.baseColor.g, root.baseColor.b, 0.25);
                ctx.lineWidth = 1.5;
                ctx.lineCap = "round";
                ctx.moveTo(playedX + 2, centerY);
                ctx.lineTo(w, centerY);
                ctx.stroke();
            }

            // Played fluid wavy sine line
            if (playedX > 0) {
                ctx.beginPath();
                ctx.strokeStyle = root.fillColor;
                ctx.lineWidth = 2.0;
                ctx.lineCap = "round";
                ctx.lineJoin = "round";

                const wavelength = 12.0;
                const k = (2 * Math.PI) / wavelength;
                const amp = 1.6;
                const taperLen = Math.min(10.0, playedX * 0.4);

                for (let x = 0; x <= playedX; x += 1.0) {
                    let envelope = 1.0;
                    if (taperLen > 0.001) {
                        const distStart = x;
                        const distEnd = playedX - x;
                        if (distStart < taperLen) {
                            envelope = Math.min(envelope, 0.5 * (1.0 - Math.cos(Math.PI * distStart / taperLen)));
                        }
                        if (distEnd < taperLen) {
                            envelope = Math.min(envelope, 0.5 * (1.0 - Math.cos(Math.PI * distEnd / taperLen)));
                        }
                    }

                    const waveY = centerY + amp * envelope * Math.sin(x * k - root.phase * 2.0);
                    if (x === 0) ctx.moveTo(x, waveY);
                    else ctx.lineTo(x, waveY);
                }
                ctx.lineTo(playedX, centerY);
                ctx.stroke();

                // Live playhead bead stays stationary at centerY
                ctx.beginPath();
                ctx.fillStyle = root.baseColor;
                ctx.arc(playedX, centerY, 2.0, 0, Math.PI * 2);
                ctx.fill();
            }
        }
    }
}
