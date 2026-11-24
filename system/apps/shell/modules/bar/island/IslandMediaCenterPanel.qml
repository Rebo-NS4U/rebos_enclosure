pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Window
import QtQuick.Layouts
import QtQuick.Effects
import Quickshell.Widgets
import Quickshell.Services.Mpris
import qs.modules.services
import qs.modules.theme
import qs.modules.components
import qs.modules.widgets.dashboard.controls
import qs.modules.globals
import qs.config

Item {
    id: root

    implicitWidth: Styling.spacing(620)
    readonly property bool tightLayout: Screen.height > 0 && Screen.height < Styling.spacing(720)
    implicitHeight: mainCol.implicitHeight + Styling.spacing(36)

    signal backRequested()
    signal openReaderRequested()
    property var reader: null
    readonly property bool readerActive: reader !== null && reader.speaking

    readonly property bool hasPlayer: MprisController.activePlayer !== null
    readonly property bool isPlaying: MprisController.isPlaying
    readonly property string trackTitle: MprisController.trackTitle || "No media playing"
    readonly property string trackArtist: MprisController.trackArtists || ""
    readonly property string trackArt: MprisController.activePlayer?.trackArtUrl || ""
    readonly property bool hasArtwork: root.trackArt !== ""
    readonly property string wallpaperUrl: {
        const mgr = GlobalStates.wallpaperManager;
        if (!mgr) return "";
        let path = mgr.currentWallpaper;
        let frame = (mgr.getLockscreenFramePath && path) ? mgr.getLockscreenFramePath(path) : path;
        return frame ? "file://" + frame : (path ? "file://" + path : "");
    }

    Image {
        id: bgArt
        anchors.fill: parent
        source: root.hasArtwork ? root.trackArt : root.wallpaperUrl
        fillMode: Image.PreserveAspectCrop
        asynchronous: true
        // Keep pending artwork loads out of the shared reload cache.
        cache: false

        clip: true
        layer.enabled: true
        layer.effect: MultiEffect {
            blurEnabled: root.hasArtwork || root.wallpaperUrl !== ""
            blurMax: 36
            blur: 0.8
        }
        opacity: root.hasArtwork ? 0.35 : (root.wallpaperUrl !== "" ? 0.18 : 0.0)
        Behavior on opacity { NumberAnimation { duration: Motion.feedback; easing.type: Easing.OutCubic } }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            GradientStop { position: 0.0; color: Styling.withOpacity(Colors.scrim, 0.33) }
            GradientStop { position: 0.5; color: Styling.withOpacity(Colors.scrim, 0.47) }
            GradientStop { position: 1.0; color: Styling.withOpacity(Colors.scrim, 0.67) }
        }
    }

    ColumnLayout {
        id: mainCol
        anchors.fill: parent
        anchors.margins: Styling.spacing(root.tightLayout ? 10 : 18)
        spacing: Styling.spacing(root.tightLayout ? 6 : 12)

        StyledRect {
            objectName: "typer-media-card"
            visible: root.readerActive
            Layout.fillWidth: true
            implicitHeight: readerControls.implicitHeight + 24
            radius: Styling.radius(0)
            variant: "common"
            ColumnLayout {
                id: readerControls
                anchors.fill: parent
                anchors.margins: 12
                StyledText {
                    Layout.fillWidth: true
                    text: root.readerActive ? "Typer · " + (root.reader.bookTitle || "Read aloud") : ""
                    elide: Text.ElideRight
                }
                RowLayout {
                    ThemeButton { text: "Open Typer"; onClicked: root.openReaderRequested() }
                    ThemeButton {
                        objectName: "typer-media-playback"
                        text: root.readerActive && root.reader.speechPaused ? "Resume" : "Pause"
                        onClicked: root.reader.toggleSpeechPlayback()
                    }
                    ThemeButton { objectName: "typer-media-stop"; text: "Stop"; onClicked: root.reader.stopSpeech() }
                }
            }
        }

        // ═══════════════════════════════════════════════════════════════
        // HEADER: Back button + Title + (Right) Player Switcher + Close
        // ═══════════════════════════════════════════════════════════════
        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(8)

            // Back button
            IslandBackButton {
                onClicked: root.backRequested()
            }

            Text {
                renderType: Text.NativeRendering
                font.hintingPreference: Font.PreferFullHinting
                text: "Media Center"
                font.family: Config.theme.font
                font.pixelSize: Styling.fontSize(3)
                font.bold: true
                color: Colors.overBackground
            }

            Item { Layout.fillWidth: true }

            ThemeButton {
                text: "Music library"
                onClicked: GlobalStates.openMusic()
            }

            // Single Icon Player Switcher (placed on the right before the close button)
            StyledRect {
                id: switchPlayerBtn
                implicitWidth: 28
                implicitHeight: 28
                radius: Styling.radius(0)
                variant: playerMouse.containsMouse ? "focus" : "common"
                scale: playerMouse.pressed ? 0.88 : (playerMouse.containsMouse ? 1.06 : 1.0)
                Behavior on scale { NumberAnimation { duration: Motion.feedback; easing.type: Easing.OutQuad } }

                Text {
                    id: playerIconText
                    anchors.centerIn: parent
                    renderType: Text.NativeRendering
                    font.hintingPreference: Font.PreferFullHinting
                    text: Icons.disc
                    font.family: Icons.font
                    font.pixelSize: Styling.fontSize(0)
                    color: Colors.primary

                    Behavior on rotation {
                        NumberAnimation { duration: Motion.feedback; easing.type: Motion.enterCurve }
                    }
                }

                // Dot indicator for multiple active players
                Rectangle {
                    visible: MprisController.filteredPlayers.length > 1
                    anchors.top: parent.top
                    anchors.right: parent.right
                    anchors.margins: 4
                    width: 5
                    height: 5
                    radius: 2.5
                    color: Colors.primary
                }

                MouseArea {
                    id: playerMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: MprisController.filteredPlayers.length > 1 ? Qt.PointingHandCursor : Qt.ArrowCursor
                    onClicked: {
                        playerIconText.rotation += 180;
                        if (MprisController.filteredPlayers.length > 1) {
                            MprisController.cyclePlayer(1);
                        }
                    }
                }

                StyledToolTip {
                    show: playerMouse.containsMouse
                    tooltipText: MprisController.filteredPlayers.length > 1
                        ? ("Switch player (current: " + (MprisController.activePlayer?.identity || "Player") + ")")
                        : (MprisController.activePlayer?.identity || "No other players")
                }
            }
        }

        Separator { Layout.fillWidth: true; implicitHeight: 1 }

        // ═══════════════════════════════════════════════════════════════
        // HERO: Rotating Vinyl Face Disc + Track Typography
        // ═══════════════════════════════════════════════════════════════
        RowLayout {
            Layout.fillWidth: true
            spacing: Styling.spacing(16)

            // ── ROTATING VINYL DISC CONTAINER ──
            Item {
                id: discContainer
                implicitWidth: root.tightLayout ? 64 : 96
                implicitHeight: implicitWidth
                Layout.alignment: Qt.AlignVCenter

                scale: discMouse.pressed ? 0.92 : 1.0
                Behavior on scale {
                    NumberAnimation {
                        duration: Motion.feedback
                        easing.type: Motion.enterCurve
                        easing.overshoot: 1.25
                    }
                }

                // Shadow ring for 3D depth
                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width + 4
                    height: width
                    radius: width / 2
                    color: "transparent"
                    border.color: Styling.withOpacity(Colors.scrim, 0.45)
                    border.width: Config.controlBorderWidth
                }

                // Rotating Vinyl Disc body
                Item {
                    id: vinylDisc
                    anchors.fill: parent

                    RotationAnimation on rotation {
                        id: discRotation
                        running: root.isPlaying
                        loops: Animation.Infinite
                        from: 0
                        to: 360
                        duration: 8000
                    }

                    // Vinyl base record
                    Rectangle {
                        anchors.fill: parent
                        radius: width / 2
                        color: Colors.surfaceContainerLowest
                        border.color: Colors.outlineVariant
                        border.width: Config.controlBorderWidth

                        // Concentric vinyl microgrooves
                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width * 0.88
                            height: width
                            radius: width / 2
                            color: "transparent"
                            border.color: Styling.withOpacity(Colors.outline, 0.07)
                            border.width: Config.controlBorderWidth
                        }

                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width * 0.76
                            height: width
                            radius: width / 2
                            color: "transparent"
                            border.color: Styling.withOpacity(Colors.outline, 0.06)
                            border.width: Config.controlBorderWidth
                        }

                        Rectangle {
                            anchors.centerIn: parent
                            width: parent.width * 0.64
                            height: width
                            radius: width / 2
                            color: "transparent"
                            border.color: Styling.withOpacity(Colors.outline, 0.05)
                            border.width: Config.controlBorderWidth
                        }

                        // Vinyl specular reflection cones (dual opposing highlights)
                        Canvas {
                            anchors.fill: parent
                            antialiasing: true
                            onPaint: {
                                const ctx = getContext("2d");
                                ctx.reset();
                                const cx = width / 2;
                                const cy = height / 2;
                                const r = width / 2;

                                ctx.fillStyle = "rgba(255, 255, 255, 0.05)";

                                // Cone 1
                                ctx.beginPath();
                                ctx.moveTo(cx, cy);
                                ctx.arc(cx, cy, r, -0.45, 0.45);
                                ctx.closePath();
                                ctx.fill();

                                // Cone 2
                                ctx.beginPath();
                                ctx.moveTo(cx, cy);
                                ctx.arc(cx, cy, r, Math.PI - 0.45, Math.PI + 0.45);
                                ctx.closePath();
                                ctx.fill();
                            }
                        }

                        // ── THE FACE DISC: Center Album Artwork ──
                        ClippingRectangle {
                            id: faceArtworkDisc
                            anchors.centerIn: parent
                            width: parent.width * 0.52
                            height: width
                            radius: width / 2
                            color: Colors.surfaceBright

                            Image {
                                id: coverImage
                                anchors.fill: parent
                                source: {
                                    if (root.trackArt !== "") return root.trackArt;
                                    if (root.wallpaperUrl !== "") return root.wallpaperUrl;
                                    return "";
                                }
                                fillMode: Image.PreserveAspectCrop
                                asynchronous: true
                                // Keep pending artwork loads out of the shared reload cache.
                                cache: false

                                visible: source !== ""
                            }

                            Text {
                                anchors.centerIn: parent
                                visible: !coverImage.visible
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                text: Icons.player
                                font.family: Icons.font
                                font.pixelSize: Styling.fontSize(6)
                                color: Colors.overBackground
                            }

                            // Center spindle hole
                            Rectangle {
                                anchors.centerIn: parent
                                width: 10
                                height: 10
                                radius: 5
                                color: Colors.surfaceContainerLowest
                                border.color: Colors.overSurface
                                border.width: Config.controlBorderWidth
                            }
                        }
                    }
                }

                MouseArea {
                    id: discMouse
                    anchors.fill: parent
                    cursorShape: Qt.PointingHandCursor
                    hoverEnabled: true
                    onClicked: MprisController.togglePlaying()
                }

                StyledToolTip {
                    show: discMouse.containsMouse
                    tooltipText: root.isPlaying ? "Click to Pause" : "Click to Play"
                }
            }

            // ── TRACK TYPOGRAPHY & ARTIST ──
            ColumnLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                spacing: Styling.spacing(3)

                Text {
                    renderType: Text.NativeRendering
                    font.hintingPreference: Font.PreferFullHinting
                    text: root.trackTitle
                    font.family: Config.theme.font
                    font.pixelSize: Styling.fontSize(2)
                    font.bold: true
                    color: Colors.overBackground
                    elide: Text.ElideRight
                    Layout.fillWidth: true

                    Behavior on opacity { NumberAnimation { duration: Motion.feedback } }
                }

                Text {
                    visible: root.trackArtist !== ""
                    renderType: Text.NativeRendering
                    font.hintingPreference: Font.PreferFullHinting
                    text: root.trackArtist
                    font.family: Config.theme.font
                    font.pixelSize: Styling.fontSize(0)
                    font.bold: true
                    color: Colors.primary
                    elide: Text.ElideRight
                    Layout.fillWidth: true

                    Behavior on opacity { NumberAnimation { duration: Motion.feedback } }
                }

                Text {
                    renderType: Text.NativeRendering
                    font.hintingPreference: Font.PreferFullHinting
                    text: MprisController.activePlayer?.identity || "Now Playing"
                    font.family: Config.theme.monoFont
                    font.pixelSize: Styling.fontSize(-2)
                    color: Colors.overSurfaceVariant
                    elide: Text.ElideRight
                    Layout.fillWidth: true
                }
            }
        }

        // ═══════════════════════════════════════════════════════════════
        // WAVEFORM PROGRESS BAR
        // ═══════════════════════════════════════════════════════════════
        IslandWaveformBar {
            Layout.fillWidth: true
            Layout.preferredHeight: 38
        }

        // ═══════════════════════════════════════════════════════════════
        // PLAYBACK CONTROLS ROW
        // ═══════════════════════════════════════════════════════════════
        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignHCenter
            spacing: Styling.spacing(12)

            // Shuffle button
            ThemeButton {
                id: shuffleButton
                implicitWidth: Styling.spacing(36)
                implicitHeight: implicitWidth
                padding: 0
                glyph: Icons.shuffle
                Accessible.name: "Shuffle"
                emphasized: MprisController.hasShuffle
                enabled: MprisController.shuffleSupported
                onClicked: MprisController.setShuffle(!MprisController.hasShuffle)

                StyledToolTip {
                    show: shuffleButton.hovered
                    tooltipText: shuffleButton.Accessible.name
                }
            }

            Item { Layout.fillWidth: true }

            // Previous track button
            ThemeButton {
                id: previousButton
                implicitWidth: Styling.spacing(38)
                implicitHeight: implicitWidth
                padding: 0
                glyph: Icons.previous
                Accessible.name: "Previous track"
                enabled: MprisController.canGoPrevious
                onClicked: MprisController.previous()

                StyledToolTip {
                    show: previousButton.hovered
                    tooltipText: previousButton.Accessible.name
                }
            }

            // Play / Pause HERO button
            ThemeButton {
                id: playbackButton
                implicitWidth: Styling.spacing(46)
                implicitHeight: implicitWidth
                padding: 0
                glyph: root.isPlaying ? Icons.pause : Icons.play
                Accessible.name: root.isPlaying ? "Pause" : "Play"
                emphasized: true
                glyphSize: Styling.fontSize(6)
                onClicked: MprisController.togglePlaying()

                StyledToolTip {
                    show: playbackButton.hovered
                    tooltipText: playbackButton.Accessible.name
                }
            }

            // Next track button
            ThemeButton {
                id: nextButton
                implicitWidth: Styling.spacing(38)
                implicitHeight: implicitWidth
                padding: 0
                glyph: Icons.next
                Accessible.name: "Next track"
                enabled: MprisController.canGoNext
                onClicked: MprisController.next()

                StyledToolTip {
                    show: nextButton.hovered
                    tooltipText: nextButton.Accessible.name
                }
            }

            Item { Layout.fillWidth: true }

            // Loop / Repeat button
            ThemeButton {
                id: repeatButton
                implicitWidth: Styling.spacing(36)
                implicitHeight: implicitWidth
                padding: 0
                glyph: MprisController.loopState === 2 ? Icons.repeatOnce : Icons.repeat
                Accessible.name: MprisController.loopState === 2 ? "Repeat track" : "Repeat"
                emphasized: MprisController.loopState !== 0
                enabled: MprisController.loopSupported
                onClicked: MprisController.setLoopState((MprisController.loopState + 1) % 3)

                StyledToolTip {
                    show: repeatButton.hovered
                    tooltipText: repeatButton.Accessible.name
                }
            }
        }
        MediaEqualizer { Layout.fillWidth: true }
    }
}
