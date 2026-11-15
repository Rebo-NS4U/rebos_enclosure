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
        implicitWidth: 1080
        implicitHeight: 760
        minimumSize: Qt.size(700, 560)
        color: Colors.background
        onVisibleChanged: if (!visible) Qt.quit()
        property string phase: "ready"
        property int difficulty: 1
        property real elapsed: 0
        property real playerX: 0.5
        property real playerY: 0.5
        property var enemies: []
        property var trail: []
        property real spawnClock: 0
        property double lastTick: 0
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
            lastTick = Date.now(); phase = "playing";
            arena.forceActiveFocus();
        }
        function pause() { if (phase === "playing") phase = "paused"; }
        property bool windowActive: contentItem.Window.active
        onWindowActiveChanged: if (!windowActive) pause()
        Shortcut { sequence: "Escape"; onActivated: window.pause() }
        Shortcut { sequence: "Space"; onActivated: { if (window.phase === "paused") { window.lastTick = Date.now(); window.phase = "playing"; } } }
        Timer {
            interval: 16; repeat: true; running: window.phase === "playing"
            onTriggered: {
                const now = Date.now(), dt = Math.min(0.04, (now - window.lastTick) / 1000);
                window.lastTick = now;
                window.elapsed += dt; window.spawnClock += dt;
                const gap = Math.max(0.16, 0.85 - window.difficulty * 0.18 - window.elapsed * 0.007);
                if (window.spawnClock >= gap) {
                    window.spawnClock = 0;
                    window.enemies.push(Game.spawn(arena.width, arena.height, window.playerX, window.playerY, window.difficulty, window.elapsed));
                }
                const result = Game.step(window.enemies, dt, window.playerX * arena.width, window.playerY * arena.height, arena.width, arena.height);
                window.enemies = result.enemies;
                if (!window.reducedMotion) {
                    window.trail.push({x: window.playerX, y: window.playerY});
                    if (window.trail.length > 22) window.trail.shift();
                }
                if (result.hit) window.finish();
                field.requestPaint();
            }
        }
        ColumnLayout {
            anchors.fill: parent; anchors.margins: 24; spacing: 18
            RowLayout {
                Layout.fillWidth: true; spacing: 20
                ColumnLayout {
                    spacing: 4
                    StyledText { text: "M O U S E D A S H"; font.pixelSize: 25; font.bold: true; color: Colors.primary }
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
                        onClicked: { window.difficulty = index; window.phase = "ready"; window.elapsed = 0; window.enemies = []; field.requestPaint(); }
                        contentItem: StyledText { text: parent.text; horizontalAlignment: Text.AlignHCenter; color: parent.checked ? Colors.background : Colors.overBackground }
                        background: Rectangle { radius: 10; implicitWidth: 92; implicitHeight: 36; color: parent.checked ? Colors.primary : Qt.alpha(Colors.primary, parent.hovered ? 0.2 : 0.08); border.width: parent.activeFocus ? 2 : 0; border.color: Colors.primary }
                    }
                }
                Item { Layout.fillWidth: true }
                CheckBox { text: "Quiet visuals"; checked: window.reducedMotion; onToggled: { window.reducedMotion = checked; window.trail = []; field.requestPaint(); } }
            }
            StyledRect {
                id: arena
                variant: "common"
                Layout.fillWidth: true; Layout.fillHeight: true
                focus: true
                onWidthChanged: { window.pause(); window.enemies = []; field.requestPaint(); }
                onHeightChanged: { window.pause(); window.enemies = []; field.requestPaint(); }
                Canvas {
                    id: field
                    anchors.fill: parent
                    onPaint: {
                        const c = getContext("2d"), w = width, h = height;
                        c.clearRect(0, 0, w, h);
                        c.strokeStyle = Qt.alpha(Colors.primary, 0.07); c.lineWidth = 1;
                        for (let x = 24; x < w; x += 32) { c.beginPath(); c.moveTo(x, 0); c.lineTo(x, h); c.stroke(); }
                        for (let y = 24; y < h; y += 32) { c.beginPath(); c.moveTo(0, y); c.lineTo(w, y); c.stroke(); }
                        if (window.phase === "ready") return;
                        if (!window.reducedMotion) for (let i = 0; i < window.trail.length; i++) {
                            const t = window.trail[i]; c.fillStyle = Qt.alpha(Colors.primary, i / window.trail.length * 0.25);
                            c.beginPath(); c.arc(t.x*w, t.y*h, 2 + i / window.trail.length * 4, 0, Math.PI*2); c.fill();
                        }
                        for (const e of window.enemies) {
                            c.fillStyle = Qt.alpha(Colors.overBackground, 0.16); c.strokeStyle = Qt.alpha(Colors.overBackground, 0.65); c.lineWidth = 1.5;
                            c.beginPath(); c.arc(e.x, e.y, e.r, 0, Math.PI*2); c.fill(); c.stroke();
                            c.fillStyle = Qt.alpha(Colors.overBackground, 0.5); c.beginPath(); c.arc(e.x, e.y, 2, 0, Math.PI*2); c.fill();
                        }
                        const px = window.playerX*w, py = window.playerY*h;
                        if (!window.reducedMotion) { c.fillStyle = Qt.alpha(Colors.primary, 0.12); c.beginPath(); c.arc(px, py, 20, 0, Math.PI*2); c.fill(); }
                        c.fillStyle = window.phase === "over" ? Colors.error : Colors.primary;
                        c.beginPath(); c.arc(px, py, 6, 0, Math.PI*2); c.fill();
                    }
                    Connections { target: Colors; function onPrimaryChanged() { field.requestPaint(); } }
                }
                MouseArea {
                    anchors.fill: parent; hoverEnabled: true
                    cursorShape: window.phase === "playing" ? Qt.BlankCursor : Qt.ArrowCursor
                    onPositionChanged: mouse => {
                        if (window.phase !== "playing") return;
                        const nextX = mouse.x, nextY = mouse.y;
                        if (Game.sweptHit(window.enemies, window.playerX * width, window.playerY * height, nextX, nextY)) window.finish();
                        window.playerX = nextX / width; window.playerY = nextY / height;
                    }
                    onExited: window.pause()
                    onClicked: mouse => {
                        if (window.phase === "ready" || window.phase === "over") window.start(mouse.x, mouse.y);
                        else if (window.phase === "paused") { window.lastTick = Date.now(); window.phase = "playing"; }
                    }
                }
                Rectangle {
                    anchors.centerIn: parent; width: Math.min(parent.width - 48, 440); height: 190
                    visible: window.phase !== "playing"
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
                StyledText { text: "●  " + (window.phase === "playing" ? "IN THE FLOW" : window.phase === "paused" ? "PAUSED" : "READY WHEN YOU ARE"); color: Colors.primary; font.pixelSize: 11 }
                Item { Layout.fillWidth: true }
                StyledText { text: "Move to dodge   /   Esc to pause   /   Bests saved locally"; opacity: 0.5; font.pixelSize: 11 }
            }
        }
    }
}
