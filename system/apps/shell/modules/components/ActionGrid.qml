import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.modules.theme
import qs.modules.components
import qs.config

FocusScope {
    id: root

    property alias actions: repeater.model
    property string layout: "row" // "row" or "grid"
    property int buttonSize: 48
    property int iconSize: 20
    property int spacing: Styling.spacing(4)
    property int columns: 3 // para layout grid
    property int textSpacing: 8
    property bool labeledTiles: false

    signal actionTriggered(var action)

    property int currentIndex: 0

    function getNextValidIndex(current, step) {
        let next = current;
        let limit = actions.length;
        for (let i = 0; i < limit; i++) {
            next = (next + step + limit) % limit;
            let action = actions[next];
            let isEnabled = (action.enabled !== undefined ? action.enabled : true);
            if ((!action.type || action.type !== "separator") && isEnabled)
                return next;
        }
        return current;
    }

    implicitWidth: container.implicitWidth
    implicitHeight: container.implicitHeight

    Component.onCompleted: {
        root.forceActiveFocus();
        if (repeater.count > 0) {
            repeater.itemAt(0).forceActiveFocus();
        }
    }

    onActiveFocusChanged: {
        if (activeFocus && repeater.count > 0) {
            Qt.callLater(() => {
                let item = repeater.itemAt(currentIndex);
                if (item)
                    item.forceActiveFocus();
            });
        }
    }

    Keys.onPressed: event => {
        let nextIndex = currentIndex;

        if (layout === "row") {
            if (event.key === Qt.Key_Right || event.key === Qt.Key_Down) {
                nextIndex = getNextValidIndex(currentIndex, 1);
            } else if (event.key === Qt.Key_Left || event.key === Qt.Key_Up) {
                nextIndex = getNextValidIndex(currentIndex, -1);
            }
        } else {
            // grid layout
            if (event.key === Qt.Key_Right) {
                nextIndex = Math.min(currentIndex + 1, actions.length - 1);
            } else if (event.key === Qt.Key_Left) {
                nextIndex = Math.max(currentIndex - 1, 0);
            } else if (event.key === Qt.Key_Down) {
                nextIndex = Math.min(currentIndex + columns, actions.length - 1);
            } else if (event.key === Qt.Key_Up) {
                nextIndex = Math.max(currentIndex - columns, 0);
            }
        }

        if (event.key === Qt.Key_Return || event.key === Qt.Key_Space) {
            if (repeater.itemAt(currentIndex)) {
                repeater.itemAt(currentIndex).triggerAction();
            }
            event.accepted = true;
        } else if (nextIndex !== currentIndex) {
            currentIndex = nextIndex;
            let item = repeater.itemAt(currentIndex);
            if (item)
                item.forceActiveFocus();
            event.accepted = true;
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"

        // Highlight que se desplaza entre botones
        StyledRect {
            id: highlight
            variant: (repeater.count > 0 && repeater.itemAt(root.currentIndex) && repeater.itemAt(root.currentIndex).actionModel.variant) ? repeater.itemAt(root.currentIndex).actionModel.variant : "primary"
            radius: Styling.radius(4)
            z: 0 // Por debajo de los botones
            visible: !root.labeledTiles && repeater.count > 0

            property Item targetItem: repeater.count > 0 ? repeater.itemAt(root.currentIndex) : null

            // Target values (geometry relative to container)
            property real tx: targetItem ? targetItem.x : 0
            property real ty: targetItem ? targetItem.y : 0
            property real tw: targetItem ? targetItem.width : 0
            property real th: targetItem ? targetItem.height : 0

            // Tracker 1 (Fast / Lead)
            property real t1x: tx
            property real t1y: ty
            property real t1w: tw
            property real t1h: th

            Behavior on t1x {
                enabled: Config.animDuration > 0
                NumberAnimation {
                    duration: Config.animDuration / 3
                    easing.type: Easing.OutSine
                }
            }
            Behavior on t1y {
                enabled: Config.animDuration > 0
                NumberAnimation {
                    duration: Config.animDuration / 3
                    easing.type: Easing.OutSine
                }
            }
            Behavior on t1w {
                enabled: Config.animDuration > 0
                NumberAnimation {
                    duration: Config.animDuration / 3
                    easing.type: Easing.OutSine
                }
            }
            Behavior on t1h {
                enabled: Config.animDuration > 0
                NumberAnimation {
                    duration: Config.animDuration / 3
                    easing.type: Easing.OutSine
                }
            }

            // Tracker 2 (Slow / Follow)
            property real t2x: tx
            property real t2y: ty
            property real t2w: tw
            property real t2h: th

            Behavior on t2x {
                enabled: Config.animDuration > 0
                NumberAnimation {
                    duration: Config.animDuration
                    easing.type: Easing.OutSine
                }
            }
            Behavior on t2y {
                enabled: Config.animDuration > 0
                NumberAnimation {
                    duration: Config.animDuration
                    easing.type: Easing.OutSine
                }
            }
            Behavior on t2w {
                enabled: Config.animDuration > 0
                NumberAnimation {
                    duration: Config.animDuration
                    easing.type: Easing.OutSine
                }
            }
            Behavior on t2h {
                enabled: Config.animDuration > 0
                NumberAnimation {
                    duration: Config.animDuration
                    easing.type: Easing.OutSine
                }
            }

            // Final geometry combining both trackers to create elastic effect
            x: Math.min(t1x, t2x) + container.x
            y: Math.min(t1y, t2y) + container.y
            width: Math.max(t1x + t1w, t2x + t2w) - Math.min(t1x, t2x)
            height: Math.max(t1y + t1h, t2y + t2h) - Math.min(t1y, t2y)
        }

        Grid {
            id: container
            anchors.centerIn: parent
            columns: root.layout === "row" ? root.actions.length : root.columns
            rows: root.layout === "row" ? 1 : Math.ceil(root.actions.length / root.columns)
            columnSpacing: root.spacing
            rowSpacing: root.spacing

            Repeater {
                id: repeater

                delegate: Item {
                    id: delegateWrapper
                    readonly property bool isSeparator: (modelData.type === "separator")
                    property var actionModel: modelData

                    implicitWidth: {
                        if (isSeparator)
                            return root.layout === "row" ? 2 : root.buttonSize;
                        if (root.labeledTiles)
                            return Math.max(Styling.spacing(72), Math.ceil(textMetrics.width) + Styling.spacing(16));
                        return root.buttonSize + (hasText ? textMetrics.width + root.textSpacing : 0);
                    }
                    implicitHeight: isSeparator ? (root.layout === "row" ? root.buttonSize : 2) : root.buttonSize
                    z: 1

                    readonly property bool hasText: {
                        if (!modelData)
                            return false;
                        if (typeof modelData.text === "string")
                            return modelData.text.length > 0;
                        return false;
                    }

                    TextMetrics {
                        id: textMetrics
                        text: delegateWrapper.hasText ? modelData.text : ""
                        font.family: Config.defaultFont
                        font.pixelSize: root.labeledTiles ? Styling.fontSize(-2) : root.iconSize * 0.7
                        font.weight: Font.DemiBold
                    }

                    function triggerAction() {
                        if (!isSeparator)
                            actionButton.triggerAction();
                    }

                    Button {
                        id: actionButton
                        anchors.fill: parent
                        visible: !delegateWrapper.isSeparator
                        enabled: !delegateWrapper.isSeparator && (modelData.enabled !== undefined ? modelData.enabled : true)
                        opacity: enabled ? 1.0 : 0.5
                        hoverEnabled: true
                        Accessible.name: modelData.tooltip || modelData.text || ""
                        readonly property bool selected: index === root.currentIndex
                        readonly property color foreground: root.labeledTiles ? tileSurface.itemColor
                            : pressed ? Styling.srItem("overprimary")
                            : selected ? (highlight.targetItem ? highlight.item : Styling.srItem("primary"))
                            : Colors.overBackground
                        scale: actionButton.pressed ? 0.93 : 1.0

                        Behavior on scale {
                            enabled: (Config.animDuration ?? 0) > 0
                            NumberAnimation {
                                duration: actionButton.pressed ? Motion.press : Motion.feedback
                                easing.type: Motion.feedbackCurve
                            }
                        }

                        Process {
                            id: commandProcess
                            command: ["bash", "-c", delegateWrapper.actionModel.command || ""]
                            running: false
                        }

                        function triggerAction() {
                            if (!enabled) return;
                            root.actionTriggered(delegateWrapper.actionModel);
                            if (delegateWrapper.actionModel.command) {
                                commandProcess.running = true;
                            }
                        }

                        background: StyledRect {
                            id: tileSurface
                            visible: root.labeledTiles
                            radius: Styling.radius(-4)
                            controlSurface: Styling.shellStyle === "terminal-hardware"
                            controlPressed: actionButton.down
                            variant: actionButton.selected ? (modelData.variant || "primary") : "common"
                            border.width: actionButton.selected ? 2 : 1
                            border.color: actionButton.selected ? itemColor : Qt.alpha(Colors.outline, 0.3)
                        }

                        contentItem: Item {
                            anchors.fill: parent

                            Text {
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                width: root.labeledTiles ? parent.width : root.buttonSize
                                height: root.labeledTiles ? parent.height - label.implicitHeight - Styling.spacing(8) : parent.height
                                anchors.left: parent.left
                                text: modelData.icon || ""
                                textFormat: Text.RichText
                                font.family: Icons.font
                                font.pixelSize: root.iconSize
                                color: root.labeledTiles && !actionButton.selected && modelData.variant === "error"
                                    ? Colors.error : actionButton.foreground
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter

                                Behavior on color {
                                    enabled: Config.animDuration > 0
                                    ColorAnimation {
                                        duration: Motion.feedback
                                        easing.type: Motion.feedbackCurve
                                    }
                                }
                            }

                            Text {
                                id: label
                                renderType: Text.NativeRendering
                                font.hintingPreference: Font.PreferFullHinting
                                visible: delegateWrapper.hasText
                                text: visible ? modelData.text : ""
                                anchors.left: root.labeledTiles ? undefined : parent.left
                                anchors.leftMargin: root.buttonSize
                                anchors.horizontalCenter: root.labeledTiles ? parent.horizontalCenter : undefined
                                anchors.verticalCenter: root.labeledTiles ? undefined : parent.verticalCenter
                                anchors.bottom: root.labeledTiles ? parent.bottom : undefined
                                anchors.bottomMargin: Styling.spacing(8)

                                font.family: textMetrics.font.family
                                font.pixelSize: textMetrics.font.pixelSize
                                font.weight: textMetrics.font.weight
                                color: actionButton.foreground
                                verticalAlignment: Text.AlignVCenter

                                Behavior on color {
                                    enabled: Config.animDuration > 0
                                    ColorAnimation {
                                        duration: Motion.feedback
                                        easing.type: Motion.feedbackCurve
                                    }
                                }
                            }
                        }

                        onClicked: triggerAction()

                        onHoveredChanged: {
                            if (hovered && actionButton.enabled) {
                                root.currentIndex = index;
                            }
                        }

                        onActiveFocusChanged: {
                            if (activeFocus) {
                                root.currentIndex = index;
                            }
                        }

                        StyledToolTip {
                            show: parent.hovered
                            tooltipText: modelData.tooltip || ""
                            delay: 500
                        }
                    }

                    Item {
                        anchors.fill: parent
                        visible: delegateWrapper.isSeparator
                        Separator {
                            anchors.centerIn: parent
                            vert: root.layout === "row"
                        }
                    }
                }
            }
        }
    }
}
