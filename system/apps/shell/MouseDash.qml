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
    component DashButton: Button {
        id: control
        property string caption: ""
        property bool accent: false
        implicitHeight: caption ? 66 : 36
        implicitWidth: 100
        padding: 10
        hoverEnabled: true
        opacity: enabled ? 1 : 0.38
        scale: down && !window.reducedMotion ? 0.97 : 1
        Behavior on scale { NumberAnimation { duration: 90 } }
        contentItem: Column {
            spacing: 4
            StyledText {
                width: parent.width; text: control.text; font.pixelSize: 13; font.bold: true
                horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter
                color: control.accent ? Colors.background : Colors.overBackground
            }
            StyledText {
                visible: control.caption !== ""; width: parent.width; text: control.caption
                font.pixelSize: 10; horizontalAlignment: Text.AlignHCenter
                color: control.accent ? Colors.background : Colors.overBackground; opacity: 0.65
            }
        }
        background: Rectangle {
            radius: 12
            color: control.accent ? Colors.primary : Qt.alpha(Colors.primary, control.down ? 0.24 : control.hovered ? 0.16 : 0.06)
            border.width: control.visualFocus ? 2 : 1
            border.color: control.visualFocus ? Colors.overBackground : Qt.alpha(Colors.primary, control.checked ? 0.8 : control.hovered ? 0.5 : 0.2)
            Rectangle {
                visible: control.checked && !control.accent
                anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter
                width: 28; height: 3; radius: 1.5; color: Colors.primary
            }
            Behavior on color { enabled: !window.reducedMotion; ColorAnimation { duration: 110 } }
        }
    }
    FloatingWindow {
        id: window
        title: "MouseDash · Enclosure"
        visible: true
        maximized: false
        implicitWidth: 480
        implicitHeight: 480
        minimumSize: Qt.size(480, 480)
        maximumSize: Qt.size(480, 480)
        color: Colors.background
        onVisibleChanged: if (!visible) Qt.quit()
        property string phase: "ready"
        property int difficulty: 1
        property string playMode: "survival"
        property bool victory: false
        property var death: null
        property real elapsed: 0
        readonly property real playerRadius: Game.playerRadius(elapsed)
        property real playerX: 0.5
        property real playerY: 0.5
        property var enemies: []
        property var trail: []
        property var clickTarget: null
        property real targetClock: 0
        property int targetsClicked: 0
        property real spawnClock: 0
        property real trailClock: 0
        property bool reducedMotion: false
        readonly property bool locked: phase === "playing" || phase === "paused"
        readonly property real duration: Game.roundDuration(playMode)
        readonly property var modes: [
            {key: "survival", name: "SURVIVAL", caption: "Endless · one life", hint: "Stay alive. The pressure never stops."},
            {key: "gauntlet", name: "GAUNTLET", caption: "60 seconds · six waves", hint: "Six waves. Each one faster than the last."}
        ]
        readonly property int modeIndex: playMode === "survival" ? 0 : 1
        readonly property string recordKey: playMode + difficulty
        readonly property real best: playMode === "survival" && difficulty < 3
            ? (difficulty === 0 ? records.easy : difficulty === 1 ? records.medium : records.hard)
            : Number(JSON.parse(records.challenges)[recordKey] || 0)
        Settings {
            id: records
            category: "MouseDash"
            location: "file://" + Quickshell.env("HOME") + "/.config/rebos_shell/mousedash.ini"
            property real easy: 0
            property real medium: 0
            property real hard: 0
            property string challenges: "{}"
        }
        function finish(won, collision) {
            death = collision || null;
            victory = won;
            if (won) elapsed = duration;
            phase = death ? "death" : "over";
            if (elapsed > best) {
                if (playMode === "survival" && difficulty < 3) {
                    if (difficulty === 0) records.easy = elapsed;
                    else if (difficulty === 1) records.medium = elapsed;
                    else records.hard = elapsed;
                } else {
                    const scores = JSON.parse(records.challenges);
                    scores[recordKey] = elapsed; records.challenges = JSON.stringify(scores);
                }
            }
        }
        function reset() {
            phase = "ready"; elapsed = 0; enemies = []; trail = [];
            enemyVisuals.clear(); victory = false; death = null;
            clickTarget = null; targetClock = 0; targetsClicked = 0;
        }
        function start(x, y) {
            reset(); playerX = x / arena.width; playerY = y / arena.height;
            spawnClock = 0; trailClock = 0; phase = "playing";
            arena.forceActiveFocus();
        }
        function movePlayer(x, y) {
            const hit = Game.contact(enemies, playerX * arena.width, playerY * arena.height, x, y, playerRadius);
            playerX = (hit ? hit.x : x) / arena.width;
            playerY = (hit ? hit.y : y) / arena.height;
            if (hit) finish(false, hit);
            return !hit;
        }
        function clickAt(x, y) {
            if (phase !== "playing" || !Game.targetHit(clickTarget, x, y)) return false;
            clickTarget = null; targetClock = 0; targetsClicked++;
            return true;
        }
        function updateTarget(dt) {
            if (!clickTarget) {
                targetClock += dt;
                if (targetClock >= (targetsClicked === 0 ? 4 : 6)) {
                    clickTarget = Game.spawnTarget(arena.width, arena.height, difficulty);
                    targetClock = 0;
                }
                return;
            }
            const result = Game.stepTarget(clickTarget, dt, arena.width, arena.height);
            clickTarget = result.target;
            if (result.missed) {
                const x = Math.max(clickTarget.r, Math.min(arena.width - clickTarget.r, clickTarget.x));
                const y = Math.max(clickTarget.r, Math.min(arena.height - clickTarget.r, clickTarget.y));
                finish(false, {cause:"missed", x:x, y:y, fromX:x, fromY:y,
                    enemy:{x:x,y:y,r:clickTarget.r}});
            }
        }
        function pause() { if (phase === "playing") phase = "paused"; }
        property bool windowActive: contentItem.Window.active
        onWindowActiveChanged: if (!windowActive) pause()
        Shortcut { sequence: "Escape"; onActivated: window.pause() }
        // Resuming requires the pointer inside the arena, preventing off-arena play.
        ListModel { id: enemyVisuals }
        FrameAnimation {
            running: window.phase === "playing"
            onTriggered: {
                const dt = Math.min(0.04, frameTime);
                window.elapsed += dt; window.spawnClock += dt;
                const gap = Game.spawnInterval(window.difficulty, window.elapsed, window.playMode);
                if (window.spawnClock >= gap) {
                    window.spawnClock = 0;
                    window.enemies.push(Game.spawn(arena.width, arena.height, window.playerX, window.playerY, window.difficulty, window.elapsed, window.playMode));
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
                if (result.hit) window.finish(false, result.collision);
                else {
                    window.updateTarget(dt);
                    if (window.phase === "playing" && Game.roundComplete(window.playMode, window.elapsed)) window.finish(true);
                }

            }
        }
        Item {
            id: view
            anchors.fill: parent
            HoverHandler { id: cursorPosition }
            StyledRect {
                id: arena
                anchors.fill: parent
                variant: "common"
                visible: window.locked || window.phase === "death"
                focus: visible; clip: true
                // Static scene-graph backdrop; nothing uploads a full-arena texture per frame.
                Rectangle {
                    anchors.fill: parent; radius: 16
                    gradient: Gradient {
                        GradientStop { position: 0; color: Qt.tint(Colors.background, Qt.alpha(Colors.primary, 0.13)) }
                        GradientStop { position: 1; color: Colors.background }
                    }
                    border.width: 1.5; border.color: Qt.alpha(Colors.primary, 0.5)
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
                    color: window.phase === "death" ? Colors.error : Colors.primary
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
                Rectangle {
                    id: targetCircle
                    readonly property var target: window.clickTarget
                    visible: !!target && window.phase !== "death"
                    x: target ? target.x - width / 2 : 0
                    y: target ? target.y - height / 2 : 0
                    width: target ? target.r * 2 : 0; height: width; radius: width / 2
                    color: Qt.alpha(Colors.success, 0.25)
                    border.width: 3; border.color: Colors.success
                }
                MouseArea {
                    id: pointer
                    anchors.fill: parent; hoverEnabled: true
                    cursorShape: window.phase === "playing" ? Qt.BlankCursor : Qt.PointingHandCursor
                    onPositionChanged: mouse => {
                        if (window.phase !== "playing") return;
                        window.movePlayer(mouse.x, mouse.y);
                    }
                    onExited: window.pause()
                    onClicked: mouse => {
                        if (window.phase === "playing") window.clickAt(mouse.x, mouse.y);
                        else if (window.phase === "paused") {
                            // Check the return path rather than teleporting through obstacles.
                            if (window.movePlayer(mouse.x, mouse.y)) window.phase = "playing";
                        }
                    }
                }
                // Keep the fatal field visible until the player chooses their next action.
                Item {
                    anchors.fill: parent; visible: window.phase === "death"
                    Rectangle {
                        readonly property var hit: window.death
                        x: hit ? hit.enemy.x - width / 2 : 0
                        y: hit ? hit.enemy.y - height / 2 : 0
                        width: hit ? hit.enemy.r * 2 + 10 : 0; height: width; radius: width / 2
                        color: "transparent"; border.width: 3; border.color: Colors.overBackground
                    }
                    Rectangle {
                        readonly property var hit: window.death
                        readonly property real sx: hit ? (hit.cause === "enemy" ? hit.enemyFromX : hit.fromX) : 0
                        readonly property real sy: hit ? (hit.cause === "enemy" ? hit.enemyFromY : hit.fromY) : 0
                        readonly property real ex: hit ? (hit.cause === "enemy" ? hit.enemy.x : hit.x) : 0
                        readonly property real ey: hit ? (hit.cause === "enemy" ? hit.enemy.y : hit.y) : 0
                        x: sx; y: sy - 1; height: 2; width: Math.hypot(ex - sx, ey - sy)
                        transformOrigin: Item.Left; rotation: Math.atan2(ey - sy, ex - sx) * 180 / Math.PI
                        color: Colors.overBackground
                    }
                    Rectangle {
                        x: 16; width: parent.width - 32; height: 120; radius: 12
                        y: window.death && window.death.y > parent.height / 2 ? 72 : parent.height - height - 16
                        color: Qt.alpha(Colors.background, 0.95); border.color: Qt.alpha(Colors.error, 0.5)
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 14; spacing: 6
                            StyledText { text: (window.death && window.death.cause === "missed" ? "TARGET MISSED · " : "CAUGHT · ") + window.elapsed.toFixed(2) + "s"; color: Colors.error; font.bold: true; font.pixelSize: 18 }
                            StyledText {
                                text: window.death && window.death.cause === "missed" ? "The click target escaped. Click it before it leaves." : window.death && window.death.cause === "cursor" ? "Your cursor crossed into the highlighted ring." : "The highlighted ring caught your cursor."
                                Layout.fillWidth: true; wrapMode: Text.WordWrap; font.pixelSize: 11
                            }
                            RowLayout {
                                DashButton { text: "Try again"; accent: true; onClicked: window.start(cursorPosition.point.position.x, cursorPosition.point.position.y) }
                                DashButton { text: "Setup"; onClicked: window.phase = "over" }
                            }
                        }
                    }
                }
                RowLayout {
                    anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                    anchors.margins: 16
                    StyledText {
                        text: (window.duration ? Math.max(0, window.duration - window.elapsed) : window.elapsed).toFixed(1) + "s"
                        font.pixelSize: 22; font.bold: true; color: Colors.primary
                    }
                    StyledText {
                        text: window.playMode === "gauntlet" ? "WAVE " + Math.min(6, 1 + Math.floor(window.elapsed / 10)) + "/6" : "SURVIVAL"
                        font.pixelSize: 10; opacity: 0.6
                    }
                    Item { Layout.fillWidth: true }
                    StyledText {
                        text: "○ " + window.targetsClicked
                        color: Colors.success; font.pixelSize: 11; font.bold: true
                    }
                    DashButton { text: "Pause  Ⅱ"; visible: window.phase === "playing"; onClicked: window.pause() }
                }
                Rectangle {
                    anchors.bottom: parent.bottom; height: 3
                    width: parent.width * (window.duration ? Math.min(1, window.elapsed / window.duration) : 0)
                    color: Colors.primary
                }
                Rectangle {
                    anchors.fill: parent; color: Qt.alpha(Colors.background, 0.85)
                    visible: window.phase === "paused"
                }
                Column {
                    anchors.centerIn: parent; width: parent.width - 48; spacing: 14
                    visible: window.phase === "paused"
                    StyledText {
                        width: parent.width; horizontalAlignment: Text.AlignHCenter
                        text: "TAKE A BREATH"; font.pixelSize: 24; font.bold: true; color: Colors.primary
                    }
                    StyledText {
                        width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
                        text: "Click a safe path back to your cursor to resume."
                        font.pixelSize: 12; opacity: 0.65
                    }
                    DashButton { anchors.horizontalCenter: parent.horizontalCenter; text: "End run"; onClicked: window.finish(false) }
                }
            }
            StyledRect {
                id: setup
                anchors.fill: parent; variant: "common"
                visible: !window.locked && window.phase !== "death"
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 28; spacing: 12
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            spacing: 3
                            StyledText { text: "MOUSEDASH"; font.pixelSize: 24; font.bold: true; font.letterSpacing: 2; color: Colors.primary }
                            StyledText {
                                text: window.phase === "over" ? (window.victory ? "CLEARED · " : "RUN COMPLETE · ") + window.elapsed.toFixed(2) + "s" : "Your next challenge starts here."
                                font.pixelSize: 11; opacity: 0.65
                            }
                        }
                        Item { Layout.fillWidth: true }
                    }
                    Item { Layout.fillHeight: true }
                    StyledText { text: "01 / CHOOSE YOUR RUN"; font.pixelSize: 10; opacity: 0.5 }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 8
                        Repeater {
                            model: window.modes
                            delegate: DashButton {
                                required property var modelData
                                Layout.fillWidth: true
                                text: modelData.name; caption: modelData.caption
                                checkable: true; autoExclusive: true; checked: window.playMode === modelData.key
                                onClicked: { window.playMode = modelData.key; window.reset(); }
                            }
                        }
                    }
                    StyledText {
                        Layout.fillWidth: true; text: window.modes[window.modeIndex].hint
                        font.pixelSize: 11; opacity: 0.65; wrapMode: Text.WordWrap
                    }
                    StyledText { text: "02 / SET THE PRESSURE"; font.pixelSize: 10; opacity: 0.5; Layout.topMargin: 6 }
                    RowLayout {
                        Layout.fillWidth: true; spacing: 6
                        Repeater {
                            model: ["Easy", "Normal", "Hard", "Extreme"]
                            delegate: DashButton {
                                required property string modelData
                                required property int index
                                Layout.fillWidth: true; implicitWidth: 72
                                text: modelData; checked: window.difficulty === index
                                checkable: true; autoExclusive: true; accent: checked
                                onClicked: { window.difficulty = index; window.reset(); }
                            }
                        }
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        StyledText { text: "BEST  " + window.best.toFixed(1) + "s"; font.pixelSize: 11; color: Colors.primary }
                        Item { Layout.fillWidth: true }
                        DashButton {
                            text: "Quiet FX"; checkable: true; checked: window.reducedMotion
                            onClicked: { window.reducedMotion = checked; window.trail = []; }
                        }
                    }
                    Item { Layout.fillHeight: true }
                    DashButton {
                        id: playButton
                        Layout.fillWidth: true; implicitHeight: 44
                        accent: true; text: window.phase === "over" ? "PLAY AGAIN  ↗" : "LET'S PLAY  ↗"
                        onClicked: window.start(cursorPosition.point.position.x, cursorPosition.point.position.y)
                    }
                    StyledText {
                        Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter
                        text: "Dodge rings · Click colored targets · Esc pauses"; font.pixelSize: 10; opacity: 0.45
                    }
                }
            }
        }
    }
}
