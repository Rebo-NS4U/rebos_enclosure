//@ pragma UseQApplication
//@ pragma ShellId enclosure_screen_text
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.modules.components
import qs.modules.theme

ShellRoot {
    id: root
    component Action: Button {
        id: action
        implicitHeight: 36
        implicitWidth: label.implicitWidth + 28
        background: StyledRect { variant: action.hovered ? "focus" : "bg"; radius: Styling.radius(0) }
        contentItem: StyledText { id: label; text: action.text; opacity: action.enabled ? 1 : 0.45; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
    }
    property bool ready: false
    property string message: ""
    Process {
        id: capture
        command: ["python3", Qt.resolvedUrl("scripts/screen_text.py").toString().replace("file://", "")]
        running: true
        stdout: StdioCollector {
            onStreamFinished: {
                try {
                    const result = JSON.parse(text);
                    if (result.cancelled) { Qt.quit(); return; }
                    editor.text = result.text || "";
                    root.message = result.error || "Review or edit the text, then copy or search.";
                } catch (e) { root.message = "Could not read screen text."; }
                root.ready = true;
            }
        }
    }
    Process {
        id: copy
        command: ["wl-copy", "--type", "text/plain;charset=utf-8", "--", editor.text]
        onExited: (code, status) => {
            if (code === 0) Qt.quit();
            else root.message = "Copy failed. Please try again.";
        }
    }
    PanelWindow {
        visible: root.ready
        onVisibleChanged: if (visible) editor.forceActiveFocus()
        implicitWidth: 680
        implicitHeight: 420
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: visible ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
        WlrLayershell.namespace: "enclosure:screen-text"
        color: "transparent"
        StyledRect {
            anchors.fill: parent
            variant: "bg"
            radius: Styling.radius(0)
            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 20
                spacing: 12
                StyledText { text: "Screen text"; font.bold: true }
                StyledText { text: root.message; Layout.fillWidth: true; wrapMode: Text.Wrap }
                ScrollView {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    TextArea {
                        id: editor
                        textFormat: TextEdit.PlainText
                        wrapMode: TextEdit.Wrap
                        selectByMouse: true
                        color: Colors.overBackground
                        font.family: "JetBrains Mono"
                        font.pixelSize: 14
                        background: Rectangle { color: Colors.background; radius: 12 }
                    }
                }
                RowLayout {
                    Action { text: "Cancel"; onClicked: Qt.quit() }
                    Item { Layout.fillWidth: true }
                    Action {
                        text: "Web Search"
                        enabled: editor.text.trim().length > 0
                        onClicked: {
                            Qt.openUrlExternally("https://www.google.com/search?q=" + encodeURIComponent(editor.text.trim()));
                            Qt.quit();
                        }
                    }
                    Action {
                        text: "Copy"
                        enabled: editor.text.trim().length > 0 && !copy.running
                        onClicked: copy.running = true
                    }
                }
            }
            Shortcut { sequence: "Escape"; onActivated: Qt.quit() }
            Shortcut { sequence: "Ctrl+Return"; onActivated: { if (editor.text.trim()) copy.running = true; } }
        }
    }
}
