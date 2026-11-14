import QtQuick

// Samples the displayed image, excluding the letterbox around its fitted bounds.
Item {
    id: root
    property url source
    property string hoverColor: ""
    property real zoom: 1
    property real panX: 0
    property real panY: 0
    clip: true
    readonly property bool ready: canvas.drawn
    readonly property bool failed: imageInfo.status === Image.Error || canvas.isImageError(source)
    signal picked(string color)
    activeFocusOnTab: true

    function imageBounds() {
        const size = imageInfo.sourceSize;
        if (size.width <= 0 || size.height <= 0) return Qt.rect(0, 0, 0, 0);
        const scale = Math.min(width / size.width, height / size.height) * zoom;
        const w = size.width * scale, h = size.height * scale;
        return Qt.rect((width - w) / 2 + panX, (height - h) / 2 + panY, w, h);
    }
    function invalidate() { canvas.drawn = false; hoverColor = ""; canvas.requestPaint(); }
    function clampPan() {
        const r = imageBounds();
        const dx = Math.max(0, (r.width - width) / 2), dy = Math.max(0, (r.height - height) / 2);
        panX = Math.max(-dx, Math.min(dx, panX));
        panY = Math.max(-dy, Math.min(dy, panY));
    }
    function zoomAt(factor, x, y) {
        const r = imageBounds(), next = Math.max(1, Math.min(8, zoom * factor));
        if (!r.width || next === zoom) return;
        const ratio = next / zoom;
        zoom = next;
        panX = x - (x - r.x) * ratio - (width - r.width * ratio) / 2;
        panY = y - (y - r.y) * ratio - (height - r.height * ratio) / 2;
        clampPan();
        invalidate();
    }
    function resetView() { zoom = 1; panX = 0; panY = 0; invalidate(); }
    onWidthChanged: { clampPan(); invalidate(); }
    onHeightChanged: { clampPan(); invalidate(); }

    function sampleAt(x, y) {
        const r = canvas.imageRect;
        if (!ready || x < 0 || y < 0 || x >= width || y >= height ||
                x < r.x || y < r.y || x >= r.x + r.width || y >= r.y + r.height)
            return "";
        const pixel = canvas.getContext("2d").getImageData(Math.floor(x), Math.floor(y), 1, 1).data;
        if (pixel[3] === 0)
            return "";
        return "#" + [pixel[0], pixel[1], pixel[2]].map(v => Math.round(v).toString(16).padStart(2, "0")).join("");
    }

    Image {
        id: imageInfo
        source: root.source
        visible: false
        asynchronous: true
        onStatusChanged: canvas.requestPaint()
    }
    Canvas {
        id: canvas
        anchors.fill: parent
        property bool drawn: false
        property rect imageRect: Qt.rect(0, 0, 0, 0)
        property url loadedSource
        renderTarget: Canvas.Image
        function loadSource() {
            drawn = false;
            root.hoverColor = "";
            if (loadedSource.toString())
                unloadImage(loadedSource);
            loadedSource = root.source;
            if (available && loadedSource.toString())
                loadImage(loadedSource);
            requestPaint();
        }
        onAvailableChanged: if (available) loadSource()
        onImageLoaded: requestPaint()
        onWidthChanged: { drawn = false; requestPaint(); }
        onHeightChanged: { drawn = false; requestPaint(); }
        Connections {
            target: root
            function onSourceChanged() { root.resetView(); canvas.loadSource(); }
        }
        onPaint: {
            const ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);
            if (!isImageLoaded(root.source) || imageInfo.status !== Image.Ready)
                return;
            imageRect = root.imageBounds();
            ctx.drawImage(root.source, imageRect.x, imageRect.y, imageRect.width, imageRect.height);
            drawn = true;
        }
    }
    MouseArea {
        id: pointer
        anchors.fill: parent
        hoverEnabled: true
        preventStealing: root.zoom > 1
        property point pressedAt
        property point panAtPress
        property bool panning: false
        cursorShape: panning ? Qt.ClosedHandCursor : root.ready ? Qt.CrossCursor : Qt.ArrowCursor
        onPressed: mouse => {
            pressedAt = Qt.point(mouse.x, mouse.y);
            panAtPress = Qt.point(root.panX, root.panY);
            panning = false;
        }
        onPositionChanged: mouse => {
            const dx = mouse.x - pressedAt.x, dy = mouse.y - pressedAt.y;
            if (pressed && root.zoom > 1 && (panning || Math.hypot(dx, dy) > 6)) {
                panning = true;
                root.panX = panAtPress.x + dx;
                root.panY = panAtPress.y + dy;
                root.clampPan();
                root.invalidate();
            } else root.hoverColor = root.sampleAt(mouse.x, mouse.y);
        }
        onWheel: wheel => {
            if (!root.ready) { wheel.accepted = false; return; }
            root.zoomAt(Math.pow(1.25, wheel.angleDelta.y / 120), wheel.x, wheel.y);
            wheel.accepted = true;
        }
        onExited: root.hoverColor = ""
        onClicked: mouse => {
            root.forceActiveFocus();
            if (panning) { panning = false; return; }
            const color = root.sampleAt(mouse.x, mouse.y);
            if (color) root.picked(color);
        }
    }
    property real cursorX: width / 2
    property real cursorY: height / 2
    Keys.onPressed: event => {
        const step = event.modifiers & Qt.ShiftModifier ? 10 : 1;
        if (event.key === Qt.Key_Plus || event.key === Qt.Key_Equal) zoomAt(1.25, cursorX, cursorY);
        else if (event.key === Qt.Key_Minus) zoomAt(0.8, cursorX, cursorY);
        else if (event.key === Qt.Key_0) resetView();
        else if (event.key === Qt.Key_Left) cursorX -= step;
        else if (event.key === Qt.Key_Right) cursorX += step;
        else if (event.key === Qt.Key_Up) cursorY -= step;
        else if (event.key === Qt.Key_Down) cursorY += step;
        else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
            const color = sampleAt(cursorX, cursorY);
            if (color) picked(color);
        } else return;
        cursorX = Math.max(0, canvas.imageRect.x, Math.min(width - 1, canvas.imageRect.x + canvas.imageRect.width - 1, cursorX));
        cursorY = Math.max(0, canvas.imageRect.y, Math.min(height - 1, canvas.imageRect.y + canvas.imageRect.height - 1, cursorY));
        hoverColor = sampleAt(cursorX, cursorY);
        event.accepted = true;
    }
    Rectangle {
        visible: root.activeFocus && root.ready
        x: root.cursorX - 5
        y: root.cursorY - 5
        width: 10
        height: 10
        radius: 5
        color: "transparent"
        border.color: "white"
        border.width: 2
        Rectangle { anchors.fill: parent; anchors.margins: 2; radius: 3; color: "transparent"; border.color: "black" }
    }
}
