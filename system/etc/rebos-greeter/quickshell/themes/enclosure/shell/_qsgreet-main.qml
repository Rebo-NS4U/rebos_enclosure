import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtMultimedia
import qs.config
import qs.modules.theme
import qs.modules.components
import QsGreet

FocusScope {
    id: root
    focus: true
    property string themeError: ""
    property bool entered: false
    readonly property string wallpaperVideo: Config.display.wallpaperVideo ?? ""
    readonly property string wallpaperDirectory: "file:///var/lib/rebos-greeter/theme/"
    function submit() {
        var secret = password.text;
        password.clear();
        if (Auth.promptActive) Auth.submitSecret(secret);
        else Auth.login(username.text, secret);
    }
    function reveal(control) {
        var flick = scroll.contentItem;
        var top = control.mapToItem(content, 0, 0).y;
        if (top < flick.contentY) flick.contentY = top;
        else if (top + control.height > flick.contentY + scroll.availableHeight)
            flick.contentY = Math.min(Math.max(0, content.implicitHeight - scroll.availableHeight), top + control.height - scroll.availableHeight);
    }
    Rectangle { anchors.fill: parent; color: Colors.background }
    Image {
        anchors.fill: parent
        source: root.wallpaperVideo === "" && Styling.shellStyle === "glyph"
            ? Qt.resolvedUrl("modules/components/glyph-orbits.png")
            : root.wallpaperDirectory + "background.png"
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        mipmap: true
    }
    Loader {
        anchors.fill: parent
        active: /^background-[a-f0-9]{64}\.mkv$/.test(root.wallpaperVideo)
        sourceComponent: VideoOutput {
            id: output
            fillMode: VideoOutput.PreserveAspectCrop
            visible: player.error === MediaPlayer.NoError
            MediaPlayer {
                id: player
                source: root.wallpaperDirectory + root.wallpaperVideo
                videoOutput: output
                loops: MediaPlayer.Infinite
                autoPlay: true
            }
        }
    }
    Loader {
        anchors.centerIn: parent
        width: Math.max(parent.width, parent.height * 16 / 9)
        height: width * 9 / 16
        enabled: false
        active: Config.display.orbitWallpaper === true
        Component.onCompleted: {
            const count = 3 + Math.floor(Math.random() * 3);
            const seed = Math.floor(Math.random() * 0x7fffffff);
            setSource("file:///usr/local/lib/rebos-greeter/orbit/Orbit.qml", {
                accent: Qt.binding(() => Config.palette.primary || "#d71921"),
                showLabels: false,
                // Orbit uses window IDs as seeds for the procedural terrain.
                planets: Array.from({length: count}, (_, slot) => ({
                    desk: slot + 1, slot: slot, windowId: seed + slot
                }))
            });
        }
        onLoaded: {
            // Rotate the renderer's spaced-out starting arrangement by a random phase.
            if (!item.phases)
                return;
            const offset = Math.random() * 2 * Math.PI;
            const phases = {};
            for (const body of item.planets)
                phases[body.windowId] = item.phases[body.windowId] + offset;
            item.phases = phases;
            item.place();
        }
    }
    StyledRect {
        id: panel
        variant: "bg"
        enableShadow: true
        anchors.centerIn: parent
        width: Math.min(Styling.spacing(460), parent.width - Styling.spacing(40))
        height: Math.min(content.implicitHeight + Styling.spacing(64), parent.height - Styling.spacing(32))
        radius: Styling.radius(0)
        opacity: root.entered ? 1 : 0
        transform: Translate { y: root.entered ? 0 : Motion.offset
            Behavior on y { enabled: Motion.enabled; NumberAnimation { duration: Motion.enter; easing.type: Motion.enterCurve } }
        }
        Behavior on opacity { enabled: Motion.enabled; NumberAnimation { duration: Motion.enter; easing.type: Motion.enterCurve } }
        ScrollView {
            id: scroll
            anchors.fill: parent
            anchors.margins: Styling.spacing(32)
            clip: true
            contentWidth: availableWidth
            contentHeight: content.implicitHeight
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ColumnLayout {
                id: content
                width: scroll.availableWidth
                spacing: Styling.spacing(14)
                ClockText {
                    Layout.alignment: Qt.AlignHCenter
                    clockValue: Qt.formatDateTime(clock.now, Config.display.use12hFormat ? "h:mm AP" : "HH:mm")
                    color: panel.item
                    font.family: Styling.displayFont
                    font.pixelSize: Styling.fontSize(34)
                }
                StyledText {
                    Layout.alignment: Qt.AlignHCenter
                    text: Qt.formatDateTime(clock.now, "dddd, d MMMM")
                    color: panel.item
                    font.pixelSize: Styling.fontSize(0)
                }
                StyledText { text: "Username"; color: panel.item }
                SearchInput {
                    id: username
                    Layout.fillWidth: true
                    text: Users.selectedName
                    enabled: !Auth.busy && !Auth.promptActive
                    variant: inputActiveFocus ? "focus" : "pane"
                    handleTabNavigation: true
                    onTabPressed: password.focusInput()
                    onShiftTabPressed: (powerRow.visible ? shutdown : signIn).forceActiveFocus()
                    onInputActiveFocusChanged: if (inputActiveFocus) root.reveal(this)
                    Accessible.name: "Username"
                    onAccepted: password.focusInput()
                }
                StyledText { textFormat: Text.PlainText; text: Auth.promptActive ? Auth.promptMessage : "Password"; color: panel.item; wrapMode: Text.Wrap; Layout.fillWidth: true }
                SearchInput {
                    id: password
                    Layout.fillWidth: true
                    enabled: !Auth.busy
                    focus: true
                    passwordMode: !(Auth.promptActive && Auth.promptEcho)
                    variant: Auth.errorText ? "error" : (inputActiveFocus ? "focus" : "pane")
                    handleTabNavigation: true
                    onTabPressed: (sessionButton.visible && sessionButton.enabled ? sessionButton : cancelButton).forceActiveFocus()
                    onShiftTabPressed: username.focusInput()
                    onInputActiveFocusChanged: if (inputActiveFocus) root.reveal(this)
                    Accessible.name: Auth.promptActive ? Auth.promptMessage : "Password"
                    onEscapePressed: Auth.cancel()
                    onAccepted: root.submit()
                }
                StyledText {
                    Layout.fillWidth: true
                    visible: text.length > 0
                    text: Auth.errorText || Auth.infoMessage
                    color: Auth.errorText ? Colors.error : panel.item
                    wrapMode: Text.Wrap
                    textFormat: Text.PlainText
                }
                ThemeButton {
                    onActiveFocusChanged: if (activeFocus) root.reveal(this)
                    id: sessionButton
                    Layout.fillWidth: true
                    text: Sessions.selectedName || "Session"
                    enabled: Sessions.count > 1 && !Auth.busy
                    visible: Sessions.count > 0
                    onClicked: Sessions.cycle()
                }
                RowLayout {
                    Layout.fillWidth: true
                    spacing: Styling.spacing(8)
                    ThemeButton {
                        id: cancelButton
                        onActiveFocusChanged: if (activeFocus) root.reveal(this)
                        Layout.fillWidth: true
                        text: "Cancel"
                        onClicked: { Auth.cancel(); password.clear(); password.focusInput(); }
                    }
                    ThemeButton {
                        id: signIn
                        onActiveFocusChanged: if (activeFocus) root.reveal(this)
                        Layout.fillWidth: true
                        highlighted: true
                        text: Auth.busy ? "Signing in…" : "Sign in"
                        enabled: !Auth.busy
                        onClicked: root.submit()
                    }
                }
                RowLayout {
                    id: powerRow
                    Layout.fillWidth: true
                    visible: Power.enabled
                    spacing: Styling.spacing(8)
                    ThemeButton { onActiveFocusChanged: if (activeFocus) root.reveal(this); Layout.fillWidth: true; text: "Restart"; enabled: !Auth.busy; onClicked: Power.reboot() }
                    ThemeButton { id: shutdown; onActiveFocusChanged: if (activeFocus) root.reveal(this); Layout.fillWidth: true; text: "Shut down"; enabled: !Auth.busy; onClicked: Power.poweroff() }
                }
            }
        }
    }
    Component.onCompleted: Qt.callLater(function() { root.entered = true; password.focusInput(); })
    QtObject { id: clock; property date now: new Date() }
    Timer { interval: 1000; running: true; repeat: true; onTriggered: clock.now = new Date() }
    Connections { target: Auth; function onPromptRequested(message, echo) { password.clear(); password.focusInput(); } function onFailed(message) { password.clear(); password.focusInput(); } }
}
