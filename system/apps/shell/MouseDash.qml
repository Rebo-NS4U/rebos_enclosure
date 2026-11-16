//@ pragma UseQApplication
//@ pragma ShellId rebos-mousedash
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtCore
import Quickshell
import qs.modules.components
import qs.modules.theme
import "MouseDashEngine.js" as Game

ShellRoot {
    FloatingWindow {
        id: window
        title: "MouseDash · Enclosure"
        visible: true
        maximized: true
        implicitWidth: 1080
        implicitHeight: 760
        minimumSize: Qt.size(700, 560)
        color: Colors.background
        onVisibleChanged: if (!visible) Qt.quit()
        property string phase: "ready"
        property int difficulty: 1
        property real elapsed: 0
        readonly property real playerRadius: Game.playerRadius(elapsed)

        property real playerX: 0.5
        property real playerY: 0.5
        property var enemies: []
        property var trail: []
        property real spawnClock: 0
        property real trailClock: 0
        property bool reducedMotion: false
        readonly property var modes: ["Easy", "Medium", "Hard"]
        readonly property real best: difficulty === 0 ? records.easy : difficulty === 1 ? records.medium : records.hard
        Settings {
            id: records
            category: "MouseDash"
            location: "file://" + Quickshell.env("HOME") + "/.config/rebos_shell/mousedash.ini"
            property real easy: 0
            property real medium: 0
            property real hard: 0
        }
        function finish() {
            phase = "over";
            if (elapsed > best) {
                if (difficulty === 0) records.easy = elapsed;
                else if (difficulty === 1) records.medium = elapsed;
                else records.hard = elapsed;
            }
        }
        function start(x, y) {
            playerX = x / arena.width; playerY = y / arena.height;
            enemies = []; trail = []; elapsed = 0; spawnClock = 0;
            enemyVisuals.clear(); trailClock = 0; phase = "playing";
            arena.forceActiveFocus();
        }
        function pause() { if (phase === "playing") phase = "paused"; }
        property bool windowActive: contentItem.Window.active
        onWindowActiveChanged: if (!windowActive) pause()
        Shortcut { sequence: "Escape"; onActivated: window.pause() }
        Shortcut { sequence: "Space"; onActivated: { if (window.phase === "paused") { window.phase = "playing"; } } }
        ListModel { id: enemyVisuals }
        FrameAnimation {
            running: window.phase === "playing"
            onTriggered: {
                const dt = Math.min(0.04, frameTime);
                window.elapsed += dt; window.spawnClock += dt;
                const gap = Game.spawnInterval(window.difficulty, window.elapsed);
                if (window.spawnClock >= gap) {
                    window.spawnClock = 0;
                    window.enemies.push(Game.spawn(arena.width, arena.height, window.playerX, window.playerY, window.difficulty, window.elapsed));
                }
                const result = Game.step(window.enemies, dt, window.playerX * arena.width, window.playerY * arena.height, arena.width, arena.height, window.playerRadius);
                window.enemies = result.enemies;
                // Keep delegates alive: update positions without rebuilding the scene.
                while (enemyVisuals.count > result.enemies.length)
                    enemyVisuals.remove(enemyVisuals.count - 1);
                for (let i = 0; i < result.enemies.length; i++) {
                    const e = result.enemies[i];
                    const row = { ex: e.x, ey: e.y, size: e.r * 2 };
                    if (i < enemyVisuals.count) enemyVisuals.set(i, row);
                    else enemyVisuals.append(row);
                }
                // Time-based sampling keeps the tail identical at 60, 120 and 144 Hz.
                window.trailClock += dt;
                if (!window.reducedMotion && window.trailClock >= 0.012) {
                    window.trailClock %= 0.012;
                    const points = window.trail.slice(-23);
                    points.push({x: window.playerX, y: window.playerY, time: window.elapsed});
                    window.trail = points;
                }
                if (result.hit) window.finish();

            }
        }
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 24; spacing: 18
            RowLayout {
                Layout.fillWidth: true; spacing: 20
                ColumnLayout {
                    spacing: 4
                    StyledText { text: "MouseDash"; font.pixelSize: 25; font.bold: true; color: Colors.primary }
                    StyledText { text: "Find your flow. Stay in motion."; opacity: 0.65 }
                }
                Item { Layout.fillWidth: true }
                ColumnLayout {
                    StyledText { text: "SURVIVAL"; opacity: 0.55; font.pixelSize: 11 }
                    StyledText { text: window.elapsed.toFixed(2) + " s"; font.pixelSize: 28; font.bold: true }
                }
                ColumnLayout {
                    StyledText { text: "PERSONAL BEST"; opacity: 0.55; font.pixelSize: 11 }
                    StyledText { text: window.best.toFixed(2) + " s"; font.pixelSize: 28; color: Colors.primary }
                }
            }
            RowLayout {
                spacing: 8
                Repeater {
                    model: window.modes
                    delegate: Button {
                        required property string modelData
                        required property int index
                        text: modelData; checkable: true; checked: window.difficulty === index
                        enabled: window.phase !== "playing" && window.phase !== "paused"
                        onClicked: { window.difficulty = index; window.phase = "ready"; window.elapsed = 0; window.enemies = []; }
                        contentItem: StyledText { text: parent.text; horizontalAlignment: Text.AlignHCenter; color: parent.checked ? Colors.background : Colors.overBackground }
                        background: Rectangle { radius: 10; implicitWidth: 92; implicitHeight: 36; color: parent.checked ? Colors.primary : Qt.alpha(Colors.primary, parent.hovered ? 0.2 : 0.08); border.width: parent.activeFocus ? 2 : 0; border.color: Colors.primary }
                    }
                }
                Item { Layout.fillWidth: true }
                CheckBox { text: "Quiet visuals"; checked: window.reducedMotion; onToggled: { window.reducedMotion = checked; window.trail = []; } }
            }
            StyledRect {
                id: arena
                variant: "common"
                Layout.fillWidth: true; Layout.fillHeight: true
                focus: true
                onWidthChanged: { window.pause(); window.enemies = []; enemyVisuals.clear(); }
                onHeightChanged: { window.pause(); window.enemies = []; enemyVisuals.clear(); }
                clip: true
                // Static scene-graph backdrop; nothing uploads a full-arena texture per frame.
                Rectangle {
                    anchors.fill: parent; radius: 16
                    gradient: Gradient {
                        GradientStop { position: 0; color: Qt.tint(Colors.background, Qt.alpha(Colors.primary, 0.13)) }
                        GradientStop { position: 1; color: Colors.background }
                    }
                    border.color: Qt.alpha(Colors.primary, 0.22)
                }
                Repeater {
                    model: Math.ceil(arena.width / 48) * Math.ceil(arena.height / 48)
                    delegate: Rectangle {
                        required property int index
                        x: (index % Math.ceil(arena.width / 48)) * 48 + 24
                        y: Math.floor(index / Math.ceil(arena.width / 48)) * 48 + 24
                        width: 2; height: 2; radius: 1
                        color: Colors.primary; opacity: 0.12
                    }
                }
                Repeater {
                    model: 24
                    delegate: Rectangle {
                        required property int index
                        readonly property var point: window.trail[index]
                        readonly property real life: point ? Math.max(0, 1 - (window.elapsed - point.time) / 0.3) : 0
                        visible: !window.reducedMotion && !!point && window.phase !== "ready"
                        x: point ? point.x * arena.width - width / 2 : 0
                        y: point ? point.y * arena.height - height / 2 : 0
                        width: 3 + life * 10; height: width; radius: width / 2
                        color: Colors.primary; opacity: life * 0.32
                    }
                }
                Repeater {
                    model: enemyVisuals
                    delegate: Rectangle {
                        required property real ex
                        required property real ey
                        required property real size
                        x: ex - size / 2; y: ey - size / 2
                        width: size; height: size; radius: size / 2
                        visible: window.phase !== "ready"
                        color: Qt.alpha(Colors.error, 0.2)
                        border.width: 1.5; border.color: Qt.alpha(Colors.error, 0.85)
                        Rectangle {
                            anchors.centerIn: parent; width: parent.width + 10; height: width; radius: width / 2
                            visible: !window.reducedMotion
                            color: "transparent"; border.width: 4; border.color: Qt.alpha(Colors.error, 0.06)
                        }
                        Rectangle {
                            anchors.centerIn: parent; width: 4; height: 4; radius: 2
                            color: Colors.error
                        }
                    }
                }
                Rectangle {
                    id: player
                    visible: window.phase !== "ready"
                    x: window.playerX * arena.width - width / 2
                    y: window.playerY * arena.height - height / 2
                    width: window.playerRadius * 2; height: width; radius: width / 2
                    color: window.phase === "over" ? Colors.error : Colors.primary
                    border.width: 2; border.color: Colors.overBackground
                    Rectangle {
                        anchors.centerIn: parent; width: parent.width + 18; height: width; radius: width / 2
                        color: Qt.alpha(player.color, 0.1)
                        border.width: 1; border.color: Qt.alpha(player.color, 0.2)
                        visible: !window.reducedMotion
                    }
                    Rectangle {
                        x: parent.width * 0.25; y: parent.height * 0.2
                        width: parent.width * 0.25; height: width; radius: width / 2
                        color: Colors.overBackground; opacity: 0.7
                    }
                }
                MouseArea {
                    anchors.fill: parent; hoverEnabled: true
                    cursorShape: window.phase === "playing" ? Qt.BlankCursor : Qt.ArrowCursor
                    onPositionChanged: mouse => {
                        if (window.phase !== "playing") return;
                        const nextX = mouse.x, nextY = mouse.y;
                        if (Game.sweptHit(window.enemies, window.playerX * width, window.playerY * height, nextX, nextY, window.playerRadius)) window.finish();
                        window.playerX = nextX / width; window.playerY = nextY / height;
                    }
                    onExited: window.pause()
                    onClicked: mouse => {
                        if (window.phase === "ready") window.start(mouse.x, mouse.y);
                        else if (window.phase === "paused") { window.phase = "playing"; }
                    }
                }
                Rectangle {
                    anchors.centerIn: parent; width: Math.min(parent.width - 48, 440); height: 190
                    visible: window.phase === "ready" || window.phase === "paused"
                    radius: 16; color: Qt.alpha(Colors.background, 0.95)
                    border.width: 1; border.color: Qt.alpha(Colors.primary, 0.3)
                    Column {
                        anchors.centerIn: parent; spacing: 14
                        StyledText { anchors.horizontalCenter: parent.horizontalCenter; text: window.phase === "ready" ? "Enter the arena" : window.phase === "paused" ? "Take a breath" : "A beautiful run."; font.pixelSize: 27; font.bold: true; color: Colors.primary }
                        StyledText { anchors.horizontalCenter: parent.horizontalCenter; text: window.phase === "ready" ? "Move your cursor. Dodge the circles." : window.phase === "paused" ? "Click to resume · Esc to pause" : "You survived " + window.elapsed.toFixed(2) + " seconds" }
                        StyledText { anchors.horizontalCenter: parent.horizontalCenter; text: window.phase === "over" ? "Click anywhere to try again →" : window.phase === "ready" ? "Click anywhere to begin →" : "Your run is waiting."; opacity: 0.6 }
                    }
                }
            }
            RowLayout {
                visible: window.phase === "over"
                Layout.fillWidth: true
                StyledText { text: "Run complete · " + window.elapsed.toFixed(2) + " s"; color: Colors.primary; font.bold: true }
                Item { Layout.fillWidth: true }
                Button {
                    text: "Play again"
                    onClicked: { window.phase = "ready"; }
                    contentItem: StyledText { text: parent.text; horizontalAlignment: Text.AlignHCenter; color: Colors.background }
                    background: Rectangle { implicitWidth: 130; implicitHeight: 36; radius: 10; color: Colors.primary; border.width: parent.activeFocus ? 2 : 0; border.color: Colors.overBackground }
                }
            }
            RowLayout {
                StyledText { text: "●  " + (window.phase === "playing" ? "IN THE FLOW" : window.phase === "paused" ? "PAUSED" : window.phase === "over" ? "RUN COMPLETE" : "READY WHEN YOU ARE"); color: Colors.primary; font.pixelSize: 11 }
                Item { Layout.fillWidth: true }
                StyledText { text: "Move to dodge   /   Esc to pause   /   Bests saved locally"; opacity: 0.5; font.pixelSize: 11 }
            }
        }
    }
}
