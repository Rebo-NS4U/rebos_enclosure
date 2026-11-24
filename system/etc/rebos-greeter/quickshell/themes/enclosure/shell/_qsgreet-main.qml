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
        if (!Auth.promptActive && !username.text.trim()) {
            username.focusInput();
            return;
        }
        var secret = password.text;
        password.clear();
        if (Auth.promptActive) Auth.submitSecret(secret);
        else Auth.login(username.text, secret);
    }
    readonly property real edgeMargin: Styling.spacing(20)

    function cancel() {
        Auth.cancel();
        password.clear();
        password.focusInput();
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
            const seed = Math.floor(Math.random() * 0xffffffff);
            setSource("file:///usr/local/lib/rebos-greeter/orbit/Orbit.qml", {
                accent: Qt.binding(() => Config.palette.primary || "#d71921"),
                showLabels: false,
                planets: Array.from({length: count}, (_, slot) => ({
                    desk: slot + 1,
                    slot: slot,
                    windowId: slot + 1,
                    // Spread the seeds across the range and skip the zero state.
                    planetSeed: 1 + (seed + slot * 2654435761) % 0xffffffff
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
    ColumnLayout {
        anchors.top: parent.top
        anchors.topMargin: Math.max(root.edgeMargin, parent.height / 8)
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: Styling.spacing(4)

        ClockText {
            Layout.alignment: Qt.AlignHCenter
            clockValue: Qt.formatDateTime(clock.now, Config.display.use12hFormat ? "h:mm AP" : "HH:mm")
            color: Colors.overBackground
            font.family: Styling.displayFont
            font.pixelSize: Styling.fontSize(52)
        }
        StyledText {
            Layout.alignment: Qt.AlignHCenter
            text: Qt.formatDateTime(clock.now, "dddd, d MMMM")
            color: Colors.overBackground
        }
    }
    StyledRect {
        id: panel
        variant: "bg"
        enableShadow: true
        anchors.centerIn: parent
        width: Math.min(Styling.spacing(320), parent.width - 2 * root.edgeMargin)
        height: Math.min(content.implicitHeight + Styling.spacing(24), parent.height / 3)
        radius: Styling.radius(0)
        opacity: root.entered ? 1 : 0
        transform: Translate { y: root.entered ? 0 : Motion.offset
            Behavior on y { enabled: Motion.enabled; NumberAnimation { duration: Motion.enter; easing.type: Motion.enterCurve } }
        }
        Behavior on opacity { enabled: Motion.enabled; NumberAnimation { duration: Motion.enter; easing.type: Motion.enterCurve } }
        ScrollView {
            id: scroll
            anchors.fill: parent
            anchors.margins: Styling.spacing(12)
            clip: true
            contentWidth: availableWidth
            contentHeight: content.implicitHeight
            ScrollBar.horizontal.policy: ScrollBar.AlwaysOff
            ColumnLayout {
                id: content
                width: scroll.availableWidth
                spacing: Styling.spacing(14)
                StyledText {
                    Layout.fillWidth: true
                    visible: Auth.promptActive || Auth.busy
                    text: Auth.promptActive ? Auth.promptMessage : "Signing in…"
                    color: panel.item
                    wrapMode: Text.Wrap
                    textFormat: Text.PlainText
                }
                SearchInput {
                    id: password
                    Layout.fillWidth: true
                    enabled: !Auth.busy
                    placeholderText: Auth.promptActive ? "" : "Password"
                    passwordMode: !(Auth.promptActive && Auth.promptEcho)
                    variant: Auth.errorText ? "error" : (inputActiveFocus ? "focus" : "pane")
                    onInputActiveFocusChanged: if (inputActiveFocus) root.reveal(this)
                    Accessible.name: Auth.promptActive ? Auth.promptMessage : "Password"
                    onEscapePressed: root.cancel()
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
            }
        }
    }
    RowLayout {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: root.edgeMargin
        width: Math.min(implicitWidth, parent.width / 2 - root.edgeMargin * 1.5)
        spacing: Styling.spacing(8)

        SearchInput {
            id: username
            Layout.preferredWidth: Styling.spacing(132)
            Layout.fillWidth: true
            text: Users.selectedName
            placeholderText: "Username"
            enabled: !Auth.busy && !Auth.promptActive && !GreeterConfig.lockUser
            variant: inputActiveFocus ? "focus" : "pane"
            Accessible.name: "Username"
            onAccepted: password.focusInput()
        }
        ThemeButton {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            text: Sessions.selectedName || "Session"
            enabled: Sessions.count > 1 && !Auth.busy
            visible: Sessions.count > 0
            onClicked: Sessions.cycle()
        }
        ThemeButton {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            text: "Sign in"
            highlighted: true
            enabled: !Auth.busy
            onClicked: root.submit()
        }
    }
    RowLayout {
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: root.edgeMargin
        width: Math.min(implicitWidth, parent.width / 2 - root.edgeMargin * 1.5)
        spacing: Styling.spacing(8)

        ThemeButton {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            text: "Cancel"
            onClicked: root.cancel()
        }
        ThemeButton {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            text: "Restart"
            visible: Power.enabled
            enabled: !Auth.busy
            onClicked: Power.reboot()
        }
        ThemeButton {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            text: "Shut down"
            visible: Power.enabled
            enabled: !Auth.busy
            onClicked: Power.poweroff()
        }
    }
    Component.onCompleted: Qt.callLater(function() { root.entered = true; password.focusInput(); })
    QtObject { id: clock; property date now: new Date() }
    Timer { interval: 1000; running: true; repeat: true; onTriggered: clock.now = new Date() }
    Connections { target: Auth; function onPromptRequested(message, echo) { password.clear(); password.focusInput(); } function onFailed(message) { password.clear(); password.focusInput(); } }
}
