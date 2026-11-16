//@ pragma UseQApplication
//@ pragma ShellId rebos-mousedash
import QtQuick
import QtQuick.Window
import QtQuick.Controls
import QtQuick.Layouts
import QtCore
import Quickshell
import Quickshell.Widgets
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
            radius: Styling.radius(0)
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
    component Cosmos: Item {
        Repeater {
            model: 70
            delegate: Rectangle {
                required property int index
                x: (index * 137.508) % Math.max(1, parent.width)
                y: (index * 83.71) % Math.max(1, parent.height)
                width: index % 9 === 0 ? 3 : 1; height: width; radius: width / 2
                color: Colors.overBackground; opacity: 0.12 + (index % 4) * 0.1
            }
        }
        Rectangle {
            x: parent.width * 0.7 - width / 2; y: parent.height * 0.44 - height / 2
            width: parent.width * 0.34; height: width; radius: width / 2
            gradient: Gradient {
                GradientStop { position: 0; color: Qt.tint(Colors.background, Qt.alpha(Colors.tertiary, 0.35)) }
                GradientStop { position: 1; color: Colors.background }
            }
            border.color: Qt.alpha(Colors.tertiary, 0.28)
            Rectangle {
                anchors.centerIn: parent; width: parent.width * 1.65; height: parent.height * 0.4
                radius: width / 2; rotation: -25; color: "transparent"
                border.width: 3; border.color: Qt.alpha(Colors.primary, 0.2)
            }
        }
        Repeater {
            model: 3
            delegate: Rectangle {
                required property int index
                x: parent.width * 0.7 - width / 2; y: parent.height * 0.44 - height / 2
                width: parent.width * (0.5 + index * 0.25); height: width; radius: width / 2
                color: "transparent"; border.color: Qt.alpha(Colors.primary, 0.07)
            }
        }
    }
    FloatingWindow {
        id: window
        title: "Starwake · Enclosure"
        visible: true
        maximized: false
        implicitWidth: 480
        implicitHeight: 480
        minimumSize: Qt.size(480, 480)
        maximumSize: Qt.size(480, 480)
        color: "transparent"
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
        property var pickupTarget: null
        property real targetClock: 0
        property real targetBorn: 0
        property var collection: null
        property int targetsCollected: 0
        property int score: 0
        property int combo: 0
        property int nearMisses: 0
        property bool hangarOpen: false
        property string objectiveNotice: ""
        property real objectiveNoticeUntil: 0
        readonly property var careerBadges: JSON.parse(records.badges)
        readonly property string flightStyle: Game.styleAvailable(records.selectedStyle, careerBadges) ? records.selectedStyle : "scout"
        readonly property var loadout: Game.loadout(flightStyle)
        readonly property real pickupRadius: playerRadius + loadout.pickupBonus
        readonly property var flightObjectives: Game.objectives(elapsed, targetsCollected, nearMisses)
        readonly property var pendingObjectives: flightObjectives.filter(o => !careerBadges[o.id])
        function selectStyle(id) {
            if (locked || phase === "death" || !Game.styleAvailable(id, careerBadges)) return false;
            records.selectedStyle = id; reset(); return true;
        }
        function updateObjectives() {
            if (phase !== "playing") return;
            const badges = JSON.parse(records.badges);
            const earned = flightObjectives.filter(o => o.progress >= o.goal && !badges[o.id]);
            if (!earned.length) return;
            for (const objective of earned) badges[objective.id] = true;
            records.badges = JSON.stringify(badges);
            objectiveNotice = earned.map(o => o.name + " · " + o.reward).join(" / ");
            objectiveNoticeUntil = elapsed + 3;
        }
        property real comboUntil: 0
        property real overdriveUntil: 0
        property int milestone: 0
        property string notice: ""
        property real noticeUntil: 0
        readonly property bool overdrive: elapsed < overdriveUntil
        readonly property int bestScore: Number(JSON.parse(records.scoreRecords)[recordKey] || 0)
        function awardPoints(points, label) {
            const reward = Game.award(score, points, elapsed, overdriveUntil, milestone);
            const gained = reward.score - score;
            score = reward.score; milestone = reward.milestone; overdriveUntil = reward.overdriveUntil;
            notice = reward.activated ? "OVERDRIVE · DOUBLE SCORE FOR 6s" : label + " +" + gained;
            noticeUntil = elapsed + 1.6;
        }
        function awardGrazes(count) {
            if (!count) return;
            nearMisses += count;
            if (combo > 0) comboUntil = Math.min(elapsed + 8, comboUntil + count);
            awardPoints(count * loadout.grazePoints, "NEAR MISS");
            updateObjectives();
        }
        property int pulseCharges: 1
        property real pulseTime: -10
        property real pulseX: 0
        property real pulseY: 0
        function pulse() {
            if (phase !== "playing" || pulseCharges < 1) return;
            pulseCharges--; pulseTime = elapsed;
            pulseX = playerX * arena.width; pulseY = playerY * arena.height;
            const cleared = Game.pulse(enemies, pulseX, pulseY, loadout.pulseRadius);
            enemies = cleared.enemies;
            if (cleared.count) awardPoints(cleared.count * 25, "PULSE");
        }
        property real spawnClock: 0
        property real trailClock: 0
        property bool reducedMotion: false
        readonly property bool locked: phase === "playing" || phase === "paused"
        readonly property real duration: Game.roundDuration(playMode)
        readonly property var modes: [
            {key: "survival", name: "DEEP SPACE", caption: "Endless expedition", hint: "Skim debris for +" + loadout.grazePoints + ". Chain stars. Open Hangar for objectives."},
            {key: "gauntlet", name: "WARP RUN", caption: "60s · six sectors", hint: "Score big through six sectors. Every 1,000 points: 6s double score."}
        ]
        readonly property int modeIndex: playMode === "survival" ? 0 : 1
        readonly property string recordKey: Game.scoreKey(playMode, difficulty, flightStyle)
        readonly property real best: playMode === "survival" && difficulty < 3 && flightStyle === "scout"
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
            property string scoreRecords: "{}"
            property string badges: "{}"
            property string selectedStyle: "scout"
        }
        function finish(won, collision) {
            death = collision || null;
            victory = won;
            if (won) elapsed = duration;
            phase = death ? "death" : "over";
            if (score > bestScore) {
                const scores = JSON.parse(records.scoreRecords);
                scores[recordKey] = score; records.scoreRecords = JSON.stringify(scores);
            }
            if (elapsed > best) {
                if (playMode === "survival" && difficulty < 3 && flightStyle === "scout") {
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
            pickupTarget = null; targetClock = 0; targetsCollected = 0; collection = null;
            score = 0; combo = 0; pulseCharges = 1; pulseTime = -10;
            objectiveNotice = ""; objectiveNoticeUntil = 0;
            nearMisses = 0; comboUntil = 0; overdriveUntil = 0; milestone = 0; notice = ""; noticeUntil = 0;
        }
        function start(x, y) {
            reset(); hangarOpen = false; playerX = x / arena.width; playerY = y / arena.height;
            spawnClock = 0; trailClock = 0; phase = "playing";
            arena.forceActiveFocus();
        }
        function movePlayer(x, y) {
            const fromX = playerX * arena.width, fromY = playerY * arena.height;
            const hit = Game.contact(enemies, fromX, fromY, x, y, playerRadius);
            const pickup = pickupTarget && Game.sweptHit([pickupTarget], fromX, fromY, x, y, pickupRadius);
            playerX = (hit ? hit.x : x) / arena.width;
            playerY = (hit ? hit.y : y) / arena.height;
            if (hit) finish(false, hit);
            else {
                awardGrazes(Game.graze(enemies, fromX, fromY, x, y, playerRadius));
                if (pickup) collectTarget();
            }
            return !hit;
        }
        function collectTarget() {
            if (phase !== "playing" || !pickupTarget) return false;
            if (elapsed >= comboUntil) combo = 0;
            const reward = Game.starReward(combo, elapsed - targetBorn);
            combo = reward.combo; comboUntil = elapsed + 8;
            const before = score;
            awardPoints(reward.points, reward.quick ? "QUICK STAR" : "STAR");
            collection = {x: pickupTarget.x, y: pickupTarget.y, time: elapsed, points: score - before};
            pickupTarget = null; targetClock = 0; targetsCollected++;
            if (targetsCollected % 3 === 0) pulseCharges = Math.min(2, pulseCharges + 1);
            updateObjectives();
            return true;
        }
        function updateTarget(dt) {
            if (!pickupTarget) {
                targetClock += dt;
                if (targetClock >= (targetsCollected === 0 ? 1.5 : 0.85)) {
                    pickupTarget = Game.spawnTarget(arena.width, arena.height, difficulty);
                    targetBorn = elapsed;
                    targetClock = 0;
                }
                return;
            }
            const result = Game.stepTarget(pickupTarget, dt, arena.width, arena.height, playerX * arena.width, playerY * arena.height, pickupRadius);
            pickupTarget = result.target;
            if (result.collected) { collectTarget(); return; }
            if (result.missed) {
                pickupTarget = null; targetClock = 0; combo = 0; comboUntil = 0;
                notice = "STAR LOST · CHAIN RESET"; noticeUntil = elapsed + 1.6;
            }
        }
        function pause() { if (phase === "playing") phase = "paused"; }
        property bool windowActive: contentItem.Window.active
        onWindowActiveChanged: if (!windowActive) pause()
        Shortcut { sequence: "Space"; onActivated: window.pulse() }
        Shortcut { sequence: "Escape"; onActivated: window.pause() }
        // Resuming requires the pointer inside the arena, preventing off-arena play.
        ListModel { id: enemyVisuals }
        FrameAnimation {
            running: window.phase === "playing"
            onTriggered: {
                const dt = Math.min(0.04, frameTime);
                window.elapsed += dt; window.spawnClock += dt;
                if (window.combo > 0 && window.elapsed >= window.comboUntil) window.combo = 0;
                const gap = Game.spawnInterval(window.difficulty, window.elapsed, window.playMode);
                if (window.spawnClock >= gap) {
                    window.spawnClock = 0;
                    const spawned = Game.spawn(arena.width, arena.height, window.playerX, window.playerY, window.difficulty, window.elapsed, window.playMode);
                    spawned.born = window.elapsed;
                    window.enemies.push(spawned);
                }
                Game.steerDebris(window.enemies, dt);
                const result = Game.step(window.enemies, dt, window.playerX * arena.width, window.playerY * arena.height, arena.width, arena.height, window.playerRadius);
                window.enemies = result.enemies;
                if (!result.hit) window.awardGrazes(result.grazes);
                // Keep delegates alive: update positions without rebuilding the scene.
                while (enemyVisuals.count > result.enemies.length)
                    enemyVisuals.remove(enemyVisuals.count - 1);
                for (let i = 0; i < result.enemies.length; i++) {
                    const e = result.enemies[i];
                    const row = { ex: e.x, ey: e.y, size: e.r * 2, age: window.elapsed - e.born, orbiting: !!e.orbiting, heading: Math.atan2(e.vy, e.vx) * 180 / Math.PI };
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
                    window.updateObjectives();
                    if (window.phase === "playing" && Game.roundComplete(window.playMode, window.elapsed)) window.finish(true);
                }

            }
        }
        ClippingRectangle {
            id: view
            anchors.fill: parent
            radius: Styling.radius(0)
            color: Colors.background
            HoverHandler { id: cursorPosition }
            StyledRect {
                id: arena
                anchors.fill: parent
                variant: "common"
                radius: Styling.radius(0)
                visible: window.locked || window.phase === "death"
                focus: visible; clip: true
                // Static scene-graph backdrop; nothing uploads a full-arena texture per frame.
                Rectangle {
                    anchors.fill: parent; radius: arena.radius
                    gradient: Gradient {
                        GradientStop { position: 0; color: Qt.tint(Colors.background, Qt.alpha(Colors.primary, 0.13)) }
                        GradientStop { position: 1; color: Colors.background }
                    }
                    border.width: 1.5; border.color: Qt.alpha(Colors.primary, 0.5)
                }
                Cosmos { anchors.fill: parent; opacity: 0.6 }
                Repeater {
                    model: 95
                    delegate: Rectangle {
                        required property int index
                        x: ((index * 137.508) % arena.width)
                        y: ((index * 83.71) % arena.height)
                        width: index % 7 === 0 ? 3 : 1.5; height: width; radius: width / 2
                        color: Colors.overBackground; opacity: 0.15 + (index % 5) * 0.1
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
                        required property real age
                        required property bool orbiting
                        required property real heading
                        readonly property real arrival: window.reducedMotion ? 1 : Math.min(1, age / 0.65)
                        // The rim keeps the exact collision size while its halo blooms.
                        opacity: 0.65 + arrival * 0.35
                        x: ex - size / 2; y: ey - size / 2
                        width: size; height: size; radius: size / 2
                        visible: window.phase !== "ready"
                        color: Qt.alpha(orbiting ? Colors.tertiary : Colors.error, 0.3)
                        border.width: 1.5; border.color: Qt.alpha(Colors.error, 0.85)
                        Rectangle {
                            anchors.centerIn: parent; width: parent.width + 10 + (1 - parent.arrival) * 44; height: width; radius: width / 2
                            visible: !window.reducedMotion
                            color: "transparent"; border.width: 1 + (1 - parent.arrival) * 2
                            border.color: Qt.alpha(Colors.error, 0.06 + (1 - parent.arrival) * 0.55)
                        }
                        rotation: heading
                        Rectangle {
                            anchors.right: parent.left; anchors.verticalCenter: parent.verticalCenter
                            width: parent.size * 1.6; height: parent.size * 0.5; radius: height / 2
                            gradient: Gradient {
                                orientation: Gradient.Horizontal
                                GradientStop { position: 0; color: "transparent" }
                                GradientStop { position: 1; color: Qt.alpha(Colors.error, 0.35) }
                            }
                            visible: !window.reducedMotion && !parent.orbiting
                        }
                        Rectangle {
                            anchors.centerIn: parent; width: parent.width * 0.45; height: width; radius: width * 0.25
                            rotation: 45; color: parent.orbiting ? Colors.tertiary : Colors.error
                        }
                    }
                }
                Rectangle {
                    id: player
                    visible: window.phase !== "ready"
                    x: window.playerX * arena.width - width / 2
                    y: window.playerY * arena.height - height / 2
                    width: window.playerRadius * 2; height: width
                    rotation: 45
                    radius: 4
                    color: window.phase === "death" ? Colors.error : window.flightStyle === "collector" ? Colors.success : window.flightStyle === "surfer" ? Colors.tertiary : Colors.primary
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
                    readonly property real arrival: window.reducedMotion ? 1 : Math.max(0, Math.min(1, (window.elapsed - window.targetBorn) / 0.55))
                    readonly property var target: window.pickupTarget
                    visible: !!target && window.phase !== "death"
                    x: target ? target.x - width / 2 : 0
                    y: target ? target.y - height / 2 : 0
                    width: target ? target.r * 2 : 0; height: width; radius: width / 2
                    color: Qt.alpha(Colors.success, 0.25)
                    border.width: 3; border.color: Colors.success
                    Rectangle {
                        anchors.centerIn: parent; width: parent.width + window.loadout.pickupBonus * 2; height: width
                        radius: width / 2; color: "transparent"; border.width: 1; border.color: Qt.alpha(Colors.success, 0.45)
                        visible: window.loadout.pickupBonus > 0
                    }
                    StyledText {
                        anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.top; anchors.bottomMargin: 7
                        text: "+50%"; visible: window.elapsed - window.targetBorn <= 2
                        font.pixelSize: 10; font.bold: true; color: Colors.success
                    }
                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width + 12 + (1 - targetCircle.arrival) * 50
                        height: width; radius: width / 2; color: "transparent"
                        border.width: 2; border.color: Colors.success
                        opacity: window.reducedMotion ? 0 : 0.15 + (1 - targetCircle.arrival) * 0.65
                    }
                    Rectangle {
                        anchors.centerIn: parent; width: 17; height: width; radius: 3
                        rotation: 45; color: Colors.success
                        Rectangle { anchors.centerIn: parent; width: 7; height: 7; radius: 2; color: Colors.overBackground }
                    }
                }
                Item {
                    id: collectFX
                    readonly property var burst: window.collection
                    readonly property real progress: burst ? Math.max(0, Math.min(1, (window.elapsed - burst.time) / 0.65)) : 1
                    visible: !!burst && progress < 1
                    x: burst ? burst.x : 0; y: burst ? burst.y : 0
                    Rectangle {
                        anchors.centerIn: parent
                        width: window.reducedMotion ? 52 : 44 + collectFX.progress * 100
                        height: width; radius: width / 2
                        color: Qt.alpha(Colors.success, (1 - collectFX.progress) * 0.18)
                        border.width: 3 * (1 - collectFX.progress); border.color: Colors.success
                        opacity: 1 - collectFX.progress
                    }
                    Repeater {
                        model: window.reducedMotion ? 0 : 10
                        delegate: Rectangle {
                            required property int index
                            readonly property real angle: index * Math.PI / 5
                            readonly property real distance: 20 + 60 * (1 - Math.pow(1 - collectFX.progress, 3))
                            x: Math.cos(angle) * distance - width / 2
                            y: Math.sin(angle) * distance - height / 2
                            width: 5 * (1 - collectFX.progress) + 2; height: width; radius: width / 2
                            color: Colors.success; opacity: 1 - collectFX.progress
                        }
                    }
                    StyledText {
                        x: -40; width: 80; y: -30 - (window.reducedMotion ? 0 : collectFX.progress * 28)
                        text: "+" + (collectFX.burst ? collectFX.burst.points : 0); font.pixelSize: 20; font.bold: true
                        color: Colors.success; horizontalAlignment: Text.AlignHCenter
                        opacity: 1 - collectFX.progress
                    }
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
                        if (window.phase === "paused") {
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
                        x: 16; width: parent.width - 32; height: 120; radius: Styling.radius(0)
                        y: window.death && window.death.y > parent.height / 2 ? 72 : parent.height - height - 16
                        color: Qt.alpha(Colors.background, 0.95); border.color: Qt.alpha(Colors.error, 0.5)
                        ColumnLayout {
                            anchors.fill: parent; anchors.margins: 14; spacing: 6
                            StyledText { text: (window.death && window.death.cause === "missed" ? "TARGET MISSED · " : "CAUGHT · ") + window.elapsed.toFixed(2) + "s · " + Game.medal(window.score); color: Colors.error; font.bold: true; font.pixelSize: 18 }
                            StyledText {
                                text: window.death && window.death.cause === "missed" ? "The target escaped. Touch it before it leaves." : window.death && window.death.cause === "cursor" ? "Flight path crossed debris. Score " + window.score + " · Best " + window.bestScore : "Debris intercepted your ship. Score " + window.score + " · Best " + window.bestScore
                                Layout.fillWidth: true; wrapMode: Text.WordWrap; font.pixelSize: 11
                            }
                            RowLayout {
                                DashButton { text: "Try again"; accent: true; onClicked: window.start(cursorPosition.point.position.x, cursorPosition.point.position.y) }
                                DashButton { text: "Flight plan"; onClicked: window.phase = "over" }
                            }
                        }
                    }
                }
                Rectangle {
                    readonly property real progress: Math.max(0, Math.min(1, (window.elapsed - window.pulseTime) / 0.5))
                    visible: progress < 1
                    x: window.pulseX - width / 2; y: window.pulseY - height / 2
                    width: window.loadout.pulseRadius * 2 * (window.reducedMotion ? 1 : progress); height: width; radius: width / 2
                    color: Qt.alpha(Colors.primary, 0.08); border.color: Colors.primary; border.width: 3
                    opacity: 1 - progress
                }
                Column {
                    anchors.top: parent.top; anchors.topMargin: 63
                    anchors.horizontalCenter: parent.horizontalCenter; spacing: 5
                    width: parent.width - 32
                    visible: window.phase === "playing"
                    StyledText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        text: window.overdrive ? "OVERDRIVE ×2 · " + Math.ceil(window.overdriveUntil - window.elapsed) + "s" : "CHAIN ×" + window.combo + " · " + Math.max(0, window.comboUntil - window.elapsed).toFixed(1) + "s"
                        color: window.overdrive ? Colors.tertiary : Colors.primary; font.pixelSize: 10
                    }
                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: 140; height: 3; radius: 1.5; color: Qt.alpha(Colors.primary, 0.15)
                        Rectangle { width: parent.width * Math.max(0, Math.min(1, window.overdrive ? (window.overdriveUntil - window.elapsed) / 6 : (window.comboUntil - window.elapsed) / 8)); height: parent.height; radius: 1.5; color: window.overdrive ? Colors.tertiary : Colors.primary; visible: window.overdrive || window.combo > 0 }
                    }
                    StyledText {
                        anchors.horizontalCenter: parent.horizontalCenter
                        width: parent.width; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap
                        text: window.elapsed < window.objectiveNoticeUntil ? window.objectiveNotice : window.notice
                        visible: window.elapsed < window.noticeUntil || window.elapsed < window.objectiveNoticeUntil
                        color: Colors.success; font.pixelSize: 10; font.bold: true
                    }
                }
                RowLayout {
                    anchors.bottom: parent.bottom; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottomMargin: 16
                    StyledText { text: "✦ " + window.targetsCollected + " STARS"; font.pixelSize: 10; color: Colors.success }
                    DashButton { implicitWidth: 170; text: "PULSE [Space]  " + window.pulseCharges; enabled: window.pulseCharges > 0 && window.phase === "playing"; onClicked: window.pulse() }
                }
                RowLayout {
                    anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right
                    anchors.margins: 16
                    StyledText {
                        text: (window.duration ? Math.max(0, window.duration - window.elapsed) : window.elapsed).toFixed(1) + "s"
                        font.pixelSize: 22; font.bold: true; color: Colors.primary
                    }
                    StyledText {
                        text: window.playMode === "gauntlet" ? "SECTOR " + Math.min(6, 1 + Math.floor(window.elapsed / 10)) + "/6" : "DEEP SPACE"
                        font.pixelSize: 10; opacity: 0.6
                    }
                    Item { Layout.fillWidth: true }
                    StyledText {
                        text: "✦ " + window.score + "  ×" + window.combo
                        color: Colors.success; font.pixelSize: 11; font.bold: true
                    }
                    DashButton { text: "Pause  Ⅱ"; visible: window.phase === "playing"; onClicked: window.pause() }
                }
                StyledText {
                    anchors.bottom: parent.bottom; anchors.bottomMargin: 62
                    anchors.horizontalCenter: parent.horizontalCenter
                    visible: window.phase === "playing"
                    text: window.pendingObjectives.length
                        ? window.pendingObjectives[0].name + " " + window.pendingObjectives[0].progress + "/" + window.pendingObjectives[0].goal
                        : Game.nextMedal(window.score) ? "NEXT MEDAL · " + window.score + "/" + Game.nextMedal(window.score) : "GOLD FLIGHT · ALL BADGES EARNED"
                    font.pixelSize: 10; color: Colors.tertiary
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
                        text: "HOLDING ORBIT"; font.pixelSize: 24; font.bold: true; color: Colors.primary
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
                radius: Styling.radius(0)
                visible: !window.locked && window.phase !== "death" && !window.hangarOpen
                Cosmos { anchors.fill: parent; opacity: 0.7 }
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 24; spacing: 8
                    RowLayout {
                        Layout.fillWidth: true
                        ColumnLayout {
                            spacing: 3
                            StyledText { text: "STARWAKE"; font.pixelSize: 24; font.bold: true; font.letterSpacing: 2; color: Colors.primary }
                            StyledText {
                                text: window.phase === "over" ? (window.victory ? "JUMP COMPLETE · " : "FLIGHT LOG · ") + window.elapsed.toFixed(2) + "s" : "A small ship. An infinite sky."
                                font.pixelSize: 11; opacity: 0.65
                            }
                        }
                        Item { Layout.fillWidth: true }
                        DashButton { text: "Hangar"; implicitWidth: 82; onClicked: window.hangarOpen = true }
                    }
                    Item {
                        Layout.fillHeight: true; Layout.minimumHeight: 36; Layout.fillWidth: true
                        StyledText {
                            anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter
                            text: window.phase === "over" ? Game.medal(window.score) + " · " + window.nearMisses + " NEAR MISSES" : window.loadout.name + " · " + Game.medal(window.bestScore); color: Colors.tertiary
                            font.pixelSize: 11; font.letterSpacing: 1
                        }
                    }
                    StyledText { text: "01 / FLIGHT PLAN"; font.pixelSize: 10; opacity: 0.5 }
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
                    StyledText { text: "02 / HAZARD DENSITY"; font.pixelSize: 10; opacity: 0.5; Layout.topMargin: 6 }
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
                        StyledText { text: window.phase === "over" ? "SCORE " + window.score + " · BEST " + window.bestScore : "BEST " + window.bestScore + " · " + window.best.toFixed(1) + "s"; font.pixelSize: 11; color: Colors.primary }
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
                        accent: true; text: window.phase === "over" ? "LAUNCH AGAIN  ↗" : "LAUNCH EXPEDITION  ↗"
                        onClicked: window.start(cursorPosition.point.position.x, cursorPosition.point.position.y)
                    }
                    StyledText {
                        Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter
                        text: "Stars within 2s = +50% · 3 stars = pulse · Space fires"; font.pixelSize: 10; opacity: 0.45
                    }
                }
            }
            StyledRect {
                anchors.fill: parent; variant: "common"; radius: Styling.radius(0)
                visible: !window.locked && window.phase !== "death" && window.hangarOpen
                Cosmos { anchors.fill: parent; opacity: 0.5 }
                ColumnLayout {
                    anchors.fill: parent; anchors.margins: 24; spacing: 9
                    RowLayout {
                        StyledText { text: "HANGAR"; font.pixelSize: 24; font.bold: true; color: Colors.primary }
                        Item { Layout.fillWidth: true }
                        DashButton { text: "Back"; onClicked: window.hangarOpen = false }
                    }
                    StyledText { text: "Complete objectives in one flight to unlock styles."; font.pixelSize: 10 }
                    Repeater {
                        model: Game.styles()
                        delegate: DashButton {
                            required property var modelData
                            readonly property bool available: Game.styleAvailable(modelData.id, window.careerBadges)
                            Layout.fillWidth: true; implicitHeight: 58
                            text: modelData.name + (available ? (window.flightStyle === modelData.id ? " · EQUIPPED" : "") : " · LOCKED")
                            caption: available ? modelData.caption : modelData.id === "collector" ? "Collect 5 stars in one flight" : "Earn 8 near misses in one flight"
                            enabled: available; accent: window.flightStyle === modelData.id
                            onClicked: window.selectStyle(modelData.id)
                        }
                    }
                    StyledText { text: "CAREER OBJECTIVES"; font.pixelSize: 10; color: Colors.tertiary }
                    Repeater {
                        model: window.flightObjectives
                        delegate: StyledText {
                            required property var modelData
                            text: (window.careerBadges[modelData.id] ? "✓ " : "○ ") + modelData.name + " · " + (modelData.id === "collector" ? "5 stars" : modelData.id === "surfer" ? "8 near misses" : "Survive 30s")
                            color: window.careerBadges[modelData.id] ? Colors.success : Colors.overBackground
                            font.pixelSize: 11
                        }
                    }
                    Item { Layout.fillHeight: true }
                    StyledText {
                        Layout.fillWidth: true; wrapMode: Text.WordWrap; font.pixelSize: 10
                        text: "MEDALS  Bronze 1,000 · Silver 3,000 · Gold 6,000\n" + window.loadout.name + " best: " + window.bestScore + " · " + Game.medal(window.bestScore) + "\nRecords are separate for each style, mode and difficulty."
                        color: Colors.primary
                    }
                }
            }
        }
    }
}
