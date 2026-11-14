import QtQuick

// Samples the displayed image, excluding the letterbox around its fitted bounds.
Item {
    id: root
    property url source
    property string hoverColor: ""
    readonly property bool ready: canvas.drawn
    readonly property bool failed: imageInfo.status === Image.Error || canvas.isImageError(source)
    signal picked(string color)
    activeFocusOnTab: true

    function sampleAt(x, y) {
        const r = canvas.imageRect;
        if (!ready || x < r.x || y < r.y || x >= r.x + r.width || y >= r.y + r.height)
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
            function onSourceChanged() { canvas.loadSource(); }
        }
        onPaint: {
            const ctx = getContext("2d");
            ctx.clearRect(0, 0, width, height);
            if (!isImageLoaded(root.source) || imageInfo.status !== Image.Ready)
                return;
            const size = imageInfo.sourceSize;
            const scale = Math.min(width / size.width, height / size.height);
            const w = size.width * scale, h = size.height * scale;
            imageRect = Qt.rect((width - w) / 2, (height - h) / 2, w, h);
            ctx.drawImage(root.source, imageRect.x, imageRect.y, w, h);
            drawn = true;
        }
    }
    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.ready ? Qt.CrossCursor : Qt.ArrowCursor
        onPositionChanged: mouse => root.hoverColor = root.sampleAt(mouse.x, mouse.y)
        onExited: root.hoverColor = ""
        onClicked: mouse => {
            root.forceActiveFocus();
            const color = root.sampleAt(mouse.x, mouse.y);
            if (color) root.picked(color);
        }
    }
    property real cursorX: width / 2
    property real cursorY: height / 2
    Keys.onPressed: event => {
        const step = event.modifiers & Qt.ShiftModifier ? 10 : 1;
        if (event.key === Qt.Key_Left) cursorX -= step;
        else if (event.key === Qt.Key_Right) cursorX += step;
        else if (event.key === Qt.Key_Up) cursorY -= step;
        else if (event.key === Qt.Key_Down) cursorY += step;
        else if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
            const color = sampleAt(cursorX, cursorY);
            if (color) picked(color);
        } else return;
        cursorX = Math.max(canvas.imageRect.x, Math.min(canvas.imageRect.x + canvas.imageRect.width - 1, cursorX));
        cursorY = Math.max(canvas.imageRect.y, Math.min(canvas.imageRect.y + canvas.imageRect.height - 1, cursorY));
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
