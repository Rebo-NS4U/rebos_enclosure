//@ pragma UseQApplication
//@ pragma ShellId enclosure_screen_text
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.modules.components
import qs.modules.globals
import qs.modules.theme

ShellRoot {
    id: root
    property var images: ({})
    property var overlays: ({})
    property string selectedScreen: ""
    property string phase: "loading"
    property string resultText: ""
    property string message: ""
    readonly property color accent: Colors.primary
    function finish() {
        worker.stdinEnabled = false;
        Qt.quit();
    }
    function select(screenName, x, y, width, height, vw, vh) {
        if (phase !== "selecting" || width < 8 || height < 8) return;
        selectedScreen = screenName;
        phase = "reading";
        worker.write(JSON.stringify({screen: screenName, x: x, y: y, width: width,
            height: height, viewWidth: vw, viewHeight: vh}) + "\n");
    }
    Connections {
        target: GlobalStates
        function onLockscreenVisibleChanged() { if (GlobalStates.lockscreenVisible) root.finish(); }
    }
    IpcHandler {
        target: "screenText"
        function status(): string { return JSON.stringify({phase: root.phase, screen: root.selectedScreen}); }
        function close(): void { root.finish(); }
        function select(screenName: string, x: int, y: int, width: int, height: int): bool {
            const overlay = root.overlays[screenName];
            if (!overlay || root.phase !== "selecting" || x < 0 || y < 0 || width < 8 || height < 8 || x + width > overlay.width || y + height > overlay.height) return false;
            overlay.selection = Qt.rect(x, y, width, height);
            root.select(screenName, x, y, width, height, overlay.width, overlay.height);
            return true;
        }
    }
    Process {
        id: worker
        command: ["python3", Qt.resolvedUrl("scripts/screen_text.py").toString().replace("file://", "")]
        running: true
        stdinEnabled: true
        stdout: SplitParser {
            onRead: data => {
                try {
                    const result = JSON.parse(data);
                    if (result.screens) {
                        root.images = result.screens;
                        root.phase = "selecting";
                    } else {
                        root.resultText = result.text || "";
                        root.message = result.error || "";
                        if (!root.selectedScreen) {
                            Quickshell.execDetached(["notify-send", "Screen text", root.message]);
                            root.finish();
                        } else root.phase = "result";
                    }
                } catch (e) {
                    root.message = "Could not read screen text.";
                    root.phase = "result";
                }
            }
        }
        onExited: (code, status) => {
            if (root.phase === "loading") {
                Quickshell.execDetached(["notify-send", "Screen text", "Screen capture could not start."]);
                root.finish();
            } else if (root.phase === "reading") {
                root.message = "Recognition stopped. Please try again.";
                root.phase = "result";
            }
        }
    }
    Process {
        id: copy
        command: ["wl-copy", "--type", "text/plain;charset=utf-8", "--", root.resultText]
        onExited: (code, status) => {
            if (code === 0) root.finish();
            else root.message = "Copy failed. Please try again.";
        }
    }
    Variants {
        model: Quickshell.screens
        PanelWindow {
            id: window
            required property ShellScreen modelData
            screen: modelData
            Component.onCompleted: root.overlays[modelData.name] = window
            visible: root.phase !== "loading" && !!root.images[modelData.name]
            anchors { top: true; bottom: true; left: true; right: true }
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: visible ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
            WlrLayershell.namespace: "enclosure:screen-text"
            color: "transparent"
            property bool chosen: root.selectedScreen === modelData.name
            property bool collapsed: chosen && root.phase !== "selecting"
            property rect selection: Qt.rect(0, 0, 0, 0)
            property bool dragging: false
            property point start
            Image {
                id: desktop
                anchors.fill: parent
                source: root.images[window.modelData.name] ? "file://" + root.images[window.modelData.name] : ""
                fillMode: Image.Stretch
                visible: false
            }
            MultiEffect {
                anchors.fill: parent
                source: desktop
                blurEnabled: true
                blurMax: 32
                blur: window.collapsed ? 0.72 : 0.24
                brightness: window.collapsed ? -0.12 : -0.04
                Behavior on blur { NumberAnimation { duration: 500; easing.type: Easing.OutCubic } }
                Behavior on brightness { NumberAnimation { duration: 500 } }
            }
            Rectangle { id: glassMask; width: glass.width; height: glass.height; radius: glass.radius; color: "white"; visible: false; layer.enabled: true }
            // A single glass surface changes geometry: full screen -> exact selection.
            Rectangle {
                id: glass
                layer.enabled: true
                layer.effect: MultiEffect { maskEnabled: true; maskSource: glassMask }
                x: window.collapsed ? window.selection.x : 14
                y: window.collapsed ? window.selection.y : 14
                width: window.collapsed ? window.selection.width : window.width - 28
                height: window.collapsed ? window.selection.height : window.height - 28
                radius: window.collapsed ? Math.min(16, height / 5) : 28
                color: Qt.alpha(Colors.surface, window.collapsed ? 0.10 : 0.22)
                border.width: 1
                border.color: Qt.alpha(window.collapsed ? root.accent : "white", 0.65)
                clip: true
                Behavior on x { NumberAnimation { duration: 480; easing.type: Easing.InOutCubic } }
                Behavior on y { NumberAnimation { duration: 480; easing.type: Easing.InOutCubic } }
                Behavior on width { NumberAnimation { duration: 480; easing.type: Easing.InOutCubic } }
                Behavior on height { NumberAnimation { duration: 480; easing.type: Easing.InOutCubic } }
                Behavior on radius { NumberAnimation { duration: 480 } }
                Image {
                    x: -glass.x; y: -glass.y
                    width: window.width; height: window.height
                    source: desktop.source
                    fillMode: Image.Stretch
                    opacity: window.collapsed ? 1 : 0
                    Behavior on opacity { NumberAnimation { duration: 480 } }
                }
                Rectangle {
                    anchors.fill: parent
                    gradient: Gradient {
                        GradientStop { position: 0; color: "#18ffffff" }
                        GradientStop { position: 0.45; color: "#02ffffff" }
                        GradientStop { position: 1; color: "#10000000" }
                    }
                }
                Rectangle {
                    anchors.fill: parent; anchors.margins: 1
                    radius: Math.max(0, glass.radius - 1)
                    color: "transparent"
                    border.color: "#25ffffff"
                }
            }
            MouseArea {
                anchors.fill: parent
                enabled: root.phase === "selecting"
                cursorShape: Qt.CrossCursor
                onPressed: mouse => {
                    window.start = Qt.point(mouse.x, mouse.y);
                    window.selection = Qt.rect(mouse.x, mouse.y, 0, 0);
                    window.dragging = true;
                }
                onPositionChanged: mouse => {
                    if (!pressed) return;
                    const px = Math.max(0, Math.min(width, mouse.x));
                    const py = Math.max(0, Math.min(height, mouse.y));
                    window.selection = Qt.rect(Math.min(window.start.x, px), Math.min(window.start.y, py),
                        Math.abs(px - window.start.x), Math.abs(py - window.start.y));
                }
                onReleased: {
                    window.dragging = false;
                    const s = window.selection;
                    root.select(window.modelData.name, s.x, s.y, s.width, s.height, width, height);
                }
                onCanceled: window.dragging = false
            }
            Rectangle {
                x: window.selection.x; y: window.selection.y
                width: window.selection.width; height: window.selection.height
                visible: window.dragging
                radius: 8
                color: Qt.alpha(root.accent, 0.08)
                border.width: 2
                border.color: root.accent
                Rectangle {
                    anchors.bottom: parent.top; anchors.bottomMargin: 8
                    width: dimensions.implicitWidth + 20; height: 28; radius: 14
                    color: Qt.alpha(Colors.background, 0.9)
                    StyledText {
                        id: dimensions; anchors.centerIn: parent
                        text: Math.round(window.selection.width) + " × " + Math.round(window.selection.height)
                        font.pixelSize: 11
                    }
                }
            }
            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: parent.bottom; anchors.bottomMargin: 36
                width: hint.implicitWidth + 36; height: 40; radius: 20
                color: Qt.alpha(Colors.background, 0.7)
                border.color: "#22ffffff"
                visible: root.phase === "selecting"
                StyledText { id: hint; anchors.centerIn: parent; text: "Drag to select    ·    Esc to dismiss"; font.pixelSize: 12 }
            }
            Rectangle {
                id: resultCard
                width: Math.min(580, window.width - 48)
                height: Math.min(320, window.height - 48)
                x: Math.max(24, Math.min(window.width - width - 24, window.selection.x + window.selection.width / 2 - width / 2))
                y: {
                    const below = window.selection.y + window.selection.height + 20;
                    return below + height < window.height - 24 ? below : Math.max(24, window.selection.y - height - 20);
                }
                opacity: window.collapsed && reveal.running === false ? 1 : 0
                visible: opacity > 0
                scale: opacity > 0 ? 1 : 0.96
                color: "transparent"
                radius: 24
                border.color: "#40ffffff"
                Behavior on opacity { NumberAnimation { duration: 280; easing.type: Easing.OutCubic } }
                Behavior on scale { NumberAnimation { duration: 320; easing.type: Easing.OutCubic } }
                Timer { id: reveal; interval: 500; running: window.collapsed; repeat: false }
                Rectangle { id: cardMask; anchors.fill: parent; radius: 24; color: "white"; visible: false; layer.enabled: true }
                Item {
                    anchors.fill: parent
                    layer.enabled: true
                    layer.effect: MultiEffect { maskEnabled: true; maskSource: cardMask }
                    MultiEffect {
                        x: -resultCard.x; y: -resultCard.y
                        width: window.width; height: window.height
                        source: desktop; blurEnabled: true; blurMax: 48; blur: 1
                    }
                    Rectangle { anchors.fill: parent; color: Qt.alpha(Colors.surfaceContainer, 0.68); radius: 24 }
                    Rectangle {
                        anchors.fill: parent; radius: 24
                        gradient: Gradient {
                            GradientStop { position: 0; color: "#18ffffff" }
                            GradientStop { position: 1; color: "#04000000" }
                        }
                        border.color: "#40ffffff"
                    }
                }
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 22; spacing: 12
                    RowLayout {
                        StyledText { text: root.phase === "reading" ? "Reading…" : "Text"; font.pixelSize: 20; font.bold: true }
                        Item { Layout.fillWidth: true }
                    }
                    ScrollView {
                        Layout.fillWidth: true; Layout.fillHeight: true
                        TextArea {
                            id: editor
                            text: root.resultText
                            onTextChanged: if (activeFocus) root.resultText = text
                            readOnly: root.phase !== "result"
                            textFormat: TextEdit.PlainText
                            wrapMode: TextEdit.Wrap
                            selectByMouse: true
                            color: Colors.overBackground
                            selectionColor: root.accent
                            font.family: "JetBrains Mono"; font.pixelSize: 14
                            padding: 12
                            background: Rectangle { radius: 12; color: "#24000000"; border.color: "#15ffffff" }
                        }
                    }
                    StyledText { visible: root.phase === "result" && root.message.length > 0; text: root.message; font.pixelSize: 11; opacity: 0.7; Layout.fillWidth: true; wrapMode: Text.Wrap }
                    RowLayout {
                        ThemeButton { text: "Close"; onClicked: root.finish() }
                        Item { Layout.fillWidth: true }
                        ThemeButton {
                            text: "Web Search ↗"; enabled: root.phase === "result" && root.resultText.trim().length > 0
                            onClicked: { Qt.openUrlExternally("https://www.google.com/search?q=" + encodeURIComponent(root.resultText.trim())); root.finish(); }
                        }
                        ThemeButton { text: "Copy text"; highlighted: true; enabled: root.phase === "result" && root.resultText.trim().length > 0 && !copy.running; onClicked: copy.running = true }
                    }
                }
            }
            Shortcut { sequence: "Escape"; context: Qt.ApplicationShortcut; enabled: window.modelData === Quickshell.screens[0]; onActivated: root.finish() }
            Shortcut { sequence: "Ctrl+Return"; enabled: window.chosen && root.phase === "result" && !!root.resultText.trim(); onActivated: copy.running = true }
        }
    }
}
