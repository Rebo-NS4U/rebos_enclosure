import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.config
import qs.modules.theme
import qs.modules.components
import QsGreet

FocusScope {
    id: root
    focus: true
    property string themeError: ""
    readonly property var appearance: Config.appearance
    readonly property var p: appearance.palette || ({background: "#111111", foreground: "#eeeeee", primary: "#b9a1ff", overPrimary: "#111111"})
    readonly property var metrics: appearance.metrics || ({})
    readonly property string family: metrics.font || "JetBrains Mono"
    readonly property int size: metrics.fontSize || 14
    readonly property int corners: metrics.radius === undefined ? 16 : metrics.radius
    function submit() {
        var secret = password.text;
        password.clear();
        if (Auth.promptActive) Auth.submitSecret(secret);
        else Auth.login(username.text, secret);
    }
    Rectangle { anchors.fill: parent; color: root.p.background }
    Image {
        anchors.fill: parent
        source: "file:///var/lib/rebos-greeter/theme/background.png"
        fillMode: Image.PreserveAspectCrop
    }
    Rectangle { anchors.fill: parent; color: "#65000000" }
    StyledRect {
        variant: "bg"
        enableShadow: true
        anchors.centerIn: parent
        width: Math.min(460, parent.width - 40)
        height: content.implicitHeight + 64
        radius: root.corners
        ColumnLayout {
            id: content
            anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; margins: 32 }
            spacing: 14
            Label {
                Layout.alignment: Qt.AlignHCenter
                text: Qt.formatDateTime(clock.now, "hh:mm AP")
                color: root.p.foreground
                font { family: root.family; pixelSize: 48 }
            }
            Label {
                Layout.alignment: Qt.AlignHCenter
                text: Qt.formatDateTime(clock.now, "dddd, d MMMM")
                color: root.p.foreground
                font { family: root.family; pixelSize: root.size }
            }
            Label { text: "Welcome back"; color: root.p.foreground; font { family: root.family; pixelSize: 22 } }
            Label { text: "Username"; color: root.p.foreground; font.family: root.family }
            TextField {
                id: username
                Layout.fillWidth: true
                text: Users.selectedName
                enabled: !Auth.busy && !Auth.promptActive
                font { family: root.family; pixelSize: root.size }
                color: root.p.foreground
                background: StyledRect { implicitHeight: 48; variant: username.activeFocus ? "focus" : "internalbg"; controlSurface: true; radius: Math.max(0, root.corners - 6) }
                onAccepted: password.forceActiveFocus()
            }
            Label { text: Auth.promptActive ? Auth.promptMessage : "Password"; color: root.p.foreground; wrapMode: Text.Wrap; Layout.fillWidth: true; font.family: root.family }
            TextField {
                id: password
                Layout.fillWidth: true
                enabled: !Auth.busy
                focus: true
                echoMode: Auth.promptActive && Auth.promptEcho ? TextInput.Normal : TextInput.Password
                font { family: root.family; pixelSize: root.size }
                color: root.p.foreground
                background: StyledRect { implicitHeight: 48; variant: password.activeFocus ? "focus" : "internalbg"; controlSurface: true; radius: Math.max(0, root.corners - 6) }
                onAccepted: root.submit()
            }
            Label {
                Layout.fillWidth: true
                visible: text.length > 0
                text: Auth.errorText || Auth.infoMessage
                color: Auth.errorText ? (root.p.error || "#ff8888") : root.p.foreground
                wrapMode: Text.Wrap
                font.family: root.family
            }
            Repeater {
                model: [Sessions.selectedName || "Session", Auth.busy ? "Signing in…" : "Sign in", "Cancel", "Restart", "Shut down"]
                Button {
                    required property int index
                    required property string modelData
                    Layout.fillWidth: true
                    enabled: index === 2 || (!Auth.busy && (index !== 0 || Sessions.count > 1))
                    visible: index < 3 || Power.enabled
                    text: modelData
                    contentItem: Text { text: parent.text; color: index === 1 ? (root.p.overPrimary || root.p.background) : root.p.foreground; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter; font { family: root.family; pixelSize: root.size } }
                    background: StyledRect { implicitHeight: 36; variant: index === 1 ? "primary" : (parent.activeFocus || parent.hovered ? "focus" : "common"); controlSurface: true; controlPressed: parent.down; radius: Math.max(0, root.corners - 6) }
                    onClicked: {
                        if (index === 0) Sessions.cycle();
                        else if (index === 1) root.submit();
                        else if (index === 2) { Auth.cancel(); password.clear(); password.forceActiveFocus(); }
                        else if (index === 3) Power.reboot();
                        else Power.poweroff();
                    }
                }
            }
        }
    }
    QtObject { id: clock; property date now: new Date() }
    Timer { interval: 1000; running: true; repeat: true; onTriggered: clock.now = new Date() }
    Connections { target: Auth; function onPromptRequested(message, echo) { password.clear(); password.forceActiveFocus(); } function onFailed(message) { password.clear(); password.forceActiveFocus(); } }
}
