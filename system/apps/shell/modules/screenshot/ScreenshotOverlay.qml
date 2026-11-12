import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Wayland
import qs.modules.components
import qs.modules.theme

PanelWindow {
    id: root
    required property var controller
    property bool busy: false
    anchors { top: true; bottom: true; left: true; right: true }
    exclusionMode: ExclusionMode.Ignore
    WlrLayershell.layer: WlrLayer.Overlay
    WlrLayershell.namespace: "enclosure:screenshot"
    WlrLayershell.keyboardFocus: visible ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
    color: "#181818"
    property bool selectionInitialized: false
    property string tool: "crop"
    property string ink: "#ff5252"
    property var operations: []
    property var redoStack: []
    property var crop: ({x: 0, y: 0, width: 0, height: 0})
    property var draft: null
    property string hint: "Drag to select an area"
    function repaint() { drawing.requestPaint(); }
    function undo() {
        if (!operations.length) return;
        redoStack = redoStack.concat([operations[operations.length-1]]);
        operations = operations.slice(0, -1); repaint();
    }
    function redo() {
        if (!redoStack.length) return;
        operations = operations.concat([redoStack[redoStack.length-1]]);
        redoStack = redoStack.slice(0, -1); repaint();
    }
    function commit(op) { operations = operations.concat([op]); redoStack = []; repaint(); }
    function exportImage(action) {
        if (crop.width < 1 || crop.height < 1 || busy) return;
        controller.error = "";
        controller.exportImage({width: scene.width, height: scene.height, crop: crop, operations: operations}, action);
    }
    function fullImage() {
        crop = {x: 0, y: 0, width: scene.width, height: scene.height};
        tool = "arrow"; hint = "Annotate, then copy or save";
    }
    onVisibleChanged: {
        if (visible) {
            operations = []; redoStack = []; draft = null; tool = "crop";
            textEntry.visible = false; textInput.text = "";
            crop = {x: 0, y: 0, width: 0, height: 0};
            hint = "Drag to select an area";
            keyboard.forceActiveFocus();
            selectionInitialized = false;
        }
    }
    Timer {
        interval: 16
        repeat: true
        running: root.visible && !root.selectionInitialized
        onTriggered: {
            if (capture.status !== Image.Ready || scene.width < 1 || scene.height < 1) return;
            root.selectionInitialized = true;
            if (root.controller.mode !== "area" && root.controller.mode !== "edit") root.fullImage();
            root.repaint();
        }
    }
    Item {
        id: keyboard
        anchors.fill: parent
        focus: true
        Keys.onEscapePressed: root.controller.close()
        Keys.onPressed: event => {
            if (event.modifiers & Qt.ControlModifier) {
                if (event.key === Qt.Key_Z) { root.undo(); event.accepted = true; }
                if (event.key === Qt.Key_Y) { root.redo(); event.accepted = true; }
                if (event.key === Qt.Key_C) { root.exportImage("copy"); event.accepted = true; }
                if (event.key === Qt.Key_S) { root.exportImage("save"); event.accepted = true; }
            }
        }
        Image {
            id: capture
            anchors.fill: parent
            source: root.controller.imagePath ? "file://" + root.controller.imagePath : ""
            fillMode: Image.PreserveAspectFit
            cache: false
            onStatusChanged: {
                if (status === Image.Ready) {
                    root.repaint();
                }
            }
        }
        Item {
            id: scene
            anchors.centerIn: parent
            width: capture.paintedWidth
            height: capture.paintedHeight
            Canvas {
                id: drawing
                anchors.fill: parent
                onPaint: {
                    const ctx = getContext("2d");
                    ctx.clearRect(0, 0, width, height);
                    const ops = root.draft ? root.operations.concat([root.draft]) : root.operations;
                    for (const op of ops) {
                        if (!op.points.length) continue;
                        ctx.strokeStyle = op.color; ctx.fillStyle = op.color;
                        ctx.lineWidth = op.size; ctx.lineJoin = "round"; ctx.lineCap = "round";
                        const a = op.points[0]; const b = op.points[op.points.length-1];
                        ctx.beginPath();
                        if (op.tool === "pen") {
                            ctx.moveTo(a.x, a.y);
                            for (const p of op.points) ctx.lineTo(p.x, p.y);
                            ctx.stroke();
                        } else if (op.tool === "arrow") {
                            ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
                            const angle = Math.atan2(b.y-a.y, b.x-a.x);
                            ctx.beginPath(); ctx.moveTo(b.x, b.y);
                            ctx.lineTo(b.x-16*Math.cos(angle-.5), b.y-16*Math.sin(angle-.5));
                            ctx.lineTo(b.x-16*Math.cos(angle+.5), b.y-16*Math.sin(angle+.5));
                            ctx.closePath(); ctx.fill();
                        } else if (op.tool === "rectangle") {
                            ctx.strokeRect(Math.min(a.x,b.x), Math.min(a.y,b.y), Math.abs(b.x-a.x), Math.abs(b.y-a.y));
                        } else if (op.tool === "redact") {
                            ctx.fillStyle = "black";
                            ctx.fillRect(Math.min(a.x,b.x), Math.min(a.y,b.y), Math.abs(b.x-a.x), Math.abs(b.y-a.y));
                        } else if (op.tool === "text") {
                            ctx.font = "22px sans-serif"; ctx.textBaseline = "top";
                            ctx.fillText(op.text, a.x, a.y);
                        }
                    }
                    const c = root.crop;
                    ctx.fillStyle = "#88000000";
                    if (c.width < 1 || c.height < 1) ctx.fillRect(0,0,width,height);
                    else {
                        ctx.fillRect(0,0,width,c.y); ctx.fillRect(0,c.y+c.height,width,height-c.y-c.height);
                        ctx.fillRect(0,c.y,c.x,c.height); ctx.fillRect(c.x+c.width,c.y,width-c.x-c.width,c.height);
                        ctx.strokeStyle = Colors.primary; ctx.lineWidth = 2;
                        ctx.strokeRect(c.x,c.y,c.width,c.height);
                    }
                }
            }
            MouseArea {
                anchors.fill: parent
                enabled: !root.busy
                cursorShape: Qt.CrossCursor
                property point start
                function point(mouse) { return {x: Math.max(0, Math.min(width, mouse.x)), y: Math.max(0, Math.min(height, mouse.y))}; }
                onPressed: mouse => {
                    keyboard.forceActiveFocus();
                    const p = point(mouse); start = Qt.point(p.x, p.y);
                    if (root.tool === "text") {
                        textEntry.at = p; textEntry.visible = true; textInput.forceActiveFocus();
                    } else if (root.tool !== "crop") {
                        if (root.crop.width < 1) root.fullImage();
                        root.draft = {tool: root.tool, color: root.ink, size: 4, points: [p, p]};
                    }
                }
                onPositionChanged: mouse => {
                    if (!pressed) return;
                    const p = point(mouse);
                    if (root.tool === "crop") {
                        root.crop = {x: Math.min(start.x,p.x), y: Math.min(start.y,p.y), width: Math.abs(p.x-start.x), height: Math.abs(p.y-start.y)};
                    } else if (root.draft) {
                        let op = root.draft;
                        op.points = op.tool === "pen" ? op.points.concat([p]) : [op.points[0], p];
                        root.draft = op;
                    }
                    root.repaint();
                }
                onReleased: mouse => {
                    if (root.draft) { root.commit(root.draft); root.draft = null; }
                    if (root.tool === "crop" && root.crop.width >= 1 && root.crop.height >= 1) {
                        root.tool = "arrow"; root.hint = "Annotate, then copy or save";
                    }
                    root.repaint();
                }
                onCanceled: { root.draft = null; root.repaint(); }
            }
        }
        StyledRect {
            anchors.top: parent.top; anchors.topMargin: 20
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(parent.width - 40, topRow.implicitWidth + 32); height: 52
            variant: "bg"; radius: 16
            RowLayout {
                id: topRow
                anchors.centerIn: parent
                StyledText { text: "Screenshot"; font.bold: true }
                StyledText { text: root.busy ? "Exporting…" : root.controller.error || root.hint; font.pixelSize: 12 }
                Action { text: "Full image"; onClicked: { root.fullImage(); root.repaint(); } }
                Action { text: "Cancel"; onClicked: root.controller.close(); enabled: !root.busy }
            }
        }
        StyledRect {
            anchors.bottom: parent.bottom; anchors.bottomMargin: 24
            anchors.horizontalCenter: parent.horizontalCenter
            width: tools.width + 24
            height: tools.implicitHeight + 20
            variant: "bg"; radius: 16
            Flow {
                id: tools
                anchors.centerIn: parent
                width: Math.min(820, root.width - 48)
                spacing: 6
                Repeater {
                    model: [{label:"Crop",tool:"crop"},{label:"Draw",tool:"pen"},{label:"Arrow",tool:"arrow"},{label:"Box",tool:"rectangle"},{label:"Text",tool:"text"},{label:"Redact",tool:"redact"}]
                    Action {
                        required property var modelData
                        text: modelData.label
                        highlighted: root.tool === modelData.tool
                        onClicked: root.tool = modelData.tool
                    }
                }
                Repeater {
                    model: ["#ff5252", "#ffd740", "#69f0ae", "#40c4ff", "#ffffff", "#000000"]
                    Button {
                        required property string modelData
                        width: 24; height: 36
                        Accessible.name: "Ink " + modelData
                        background: Rectangle { anchors.centerIn: parent; width: 20; height: 20; radius: 10; color: parent.modelData; border.color: root.ink === parent.modelData ? Colors.primary : Colors.outline; border.width: root.ink === parent.modelData ? 3 : 1 }
                        onClicked: root.ink = modelData
                    }
                }
                Action { text: "Undo"; enabled: root.operations.length > 0; onClicked: root.undo() }
                Action { text: "Redo"; enabled: root.redoStack.length > 0; onClicked: root.redo() }
                Action { text: "Copy"; enabled: root.crop.width >= 1 && !root.busy; onClicked: root.exportImage("copy") }
                Action { text: "Save"; enabled: root.crop.width >= 1 && !root.busy; highlighted: true; onClicked: root.exportImage("save") }
            }
        }
        StyledRect {
            id: textEntry
            property var at: ({x: 0, y: 0})
            visible: false
            anchors.centerIn: parent
            width: Math.min(500, parent.width-40); height: 110
            variant: "bg"; radius: 16
            ColumnLayout {
                anchors.fill: parent; anchors.margins: 12
                StyledText { text: "Annotation text · Enter to place" }
                TextField {
                    id: textInput
                    Layout.fillWidth: true
                    color: Colors.overBackground
                    selectionColor: Colors.primary
                    background: Rectangle { color: Colors.surface; radius: 8; border.color: Colors.outline }
                    onAccepted: {
                        if (text.trim()) {
                            if (root.crop.width < 1) root.fullImage();
                            root.commit({tool:"text",color:root.ink,size:4,points:[textEntry.at],text:text});
                        }
                        text = ""; textEntry.visible = false; keyboard.forceActiveFocus();
                    }
                    Keys.onEscapePressed: { text = ""; textEntry.visible = false; keyboard.forceActiveFocus(); }
                }
            }
        }
    }
    component Action: Button {
        id: action
        implicitHeight: 36
        implicitWidth: label.implicitWidth + 20
        opacity: enabled ? 1 : .4
        contentItem: StyledText { id: label; text: action.text; color: action.highlighted ? Colors.overPrimary : Colors.overBackground; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
        background: Rectangle { radius: 10; color: action.highlighted ? Colors.primary : action.down ? Colors.surfaceContainerHighest : action.hovered ? Colors.surfaceContainerHigh : "transparent"; border.color: action.activeFocus ? Colors.primary : "transparent" }
    }
}
