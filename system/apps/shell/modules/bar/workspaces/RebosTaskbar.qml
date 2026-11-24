pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import qs.config
import qs.modules.bar
import qs.modules.components
import qs.modules.services
import qs.modules.theme

Item {
    id: root
    required property Item bar
    readonly property bool orbital: Styling.shellStyle === "orbital"
    property bool showBackground: true
    // Even indicator dimensions share a pixel center at every workspace width.
    readonly property int workspaceHeight: 2 * Math.round(Styling.fontSize(0) * 1.85 / 2)
    readonly property int workspaceGap: Math.max(1, Math.round(Styling.fontSize(0) / 7))
    readonly property var visibleWorkspaces: NiriService.workspacesForOutput(root.bar.screen.name)

    // Keep workspace buttons stable across window and focus updates.
    ListModel {
        id: workspaceModel
    }

    function reconcileIds(model: ListModel, ids: list<int>, role: string): void {
        for (let index = model.count - 1; index >= 0; index--) {
            if (!ids.includes(model.get(index)[role]))
                model.remove(index);
        }
        for (let index = 0; index < ids.length; index++) {
            let existingIndex = index;
            while (existingIndex < model.count && model.get(existingIndex)[role] !== ids[index])
                existingIndex++;
            if (existingIndex === model.count) {
                const entry = {};
                entry[role] = ids[index];
                model.insert(index, entry);
            } else if (existingIndex !== index) {
                model.move(existingIndex, index, 1);
            }
        }
    }

    function syncWorkspaces(): void {
        reconcileIds(workspaceModel, root.visibleWorkspaces.map(workspace => workspace.id), "workspaceId");
    }

    // Timers are destroyed with the delegate during native hot reload;
    // queued Qt.callLater callbacks can otherwise outlive their QML context.
    Timer {
        id: workspaceSync
        interval: 0
        onTriggered: root.syncWorkspaces()
    }
    onVisibleWorkspacesChanged: workspaceSync.restart()
    Component.onCompleted: syncWorkspaces()

    implicitWidth: workspaceRow.implicitWidth + root.workspaceGap * 3
    implicitHeight: root.workspaceHeight + root.workspaceGap * 3

    StyledRect {
        visible: root.showBackground && !root.orbital
        anchors.fill: parent
        variant: "bg"
        radius: Styling.radius(7)
        enableShadow: false
    }

    Rectangle {
        visible: root.orbital && workspaceModel.count > 1
        anchors.centerIn: workspaceRow
        width: Math.max(0, workspaceRow.width - root.workspaceHeight)
        height: 1
        color: Qt.alpha(BarAppearance.foregroundColor, 0.36)
    }

    RowLayout {
        id: workspaceRow
        anchors.centerIn: parent
        spacing: root.workspaceGap

        Repeater {
            model: workspaceModel

            Item {
                id: workspaceButton
                required property int workspaceId
                objectName: "workspace-" + workspaceId
                readonly property var workspace: root.visibleWorkspaces.find(workspace => workspace.id === workspaceId) ?? null
                readonly property bool active: workspace?.active ?? false
                readonly property var windows: NiriService.windowsForWorkspace(workspaceId)
                readonly property bool occupied: windows.length > 0
                readonly property int dotSize: Math.max(4, 2 * Math.round(root.workspaceHeight / 10))
                readonly property bool orbitLayout: root.orbital && windows.length <= 8
                ListModel { id: windowModel }
                Timer {
                    id: windowSync
                    interval: 0
                    onTriggered: root.reconcileIds(windowModel, workspaceButton.windows.map(window => window.id), "windowId")
                }
                onWindowsChanged: windowSync.restart()
                Component.onCompleted: windowSync.restart()
                readonly property string displayName: workspace?.isNamed ? workspace.name : String(workspace?.idx ?? workspaceId)
                Layout.preferredWidth: orbitLayout ? root.workspaceHeight * 2 : Math.max(root.workspaceHeight, windowDots.implicitWidth + root.workspaceGap * 6)
                Layout.preferredHeight: root.workspaceHeight
                Layout.alignment: Qt.AlignVCenter

                Rectangle {
                    objectName: "workspace-highlight-" + workspaceButton.workspaceId
                    anchors.fill: parent
                    radius: root.orbital ? height / 2 : Styling.radius(-4)
                    border.width: root.orbital ? 1 : 0
                    border.color: workspaceButton.active ? Colors.primary : Qt.alpha(Colors.overBackground, 0.36)
                    color: root.orbital ? (workspaceMouse.containsMouse ? Styling.getStyledRectConfig("focus").gradient[0][0] : Colors.background) : BarAppearance.workspaceTint(workspaceButton.active, workspaceMouse.containsMouse)
                    Behavior on color {
                        enabled: Config.animDuration > 0
                        ColorAnimation { duration: Math.min(Config.animDuration, 150) }
                    }
                }

                Rectangle {
                    objectName: "workspace-dot-" + workspaceButton.workspaceId
                    anchors.centerIn: parent
                    anchors.alignWhenCentered: false
                    visible: !workspaceButton.occupied && !workspaceButton.orbitLayout
                    width: workspaceButton.dotSize
                    height: width
                    radius: width / 2
                    // Shape distinguishes empty spaces without dimming their centerline.
                    color: "transparent"
                    border.color: workspaceButton.active ? BarAppearance.activeWorkspaceOutline : BarAppearance.foregroundColor
                    border.width: Math.max(1, Math.round(width / 6))
                }

                Text {
                    anchors.centerIn: parent
                    visible: workspaceButton.orbitLayout
                    text: workspaceButton.workspace?.idx ?? workspaceButton.workspaceId
                    color: workspaceButton.active ? Colors.primary : BarAppearance.foregroundColor
                    font.family: "Departure Mono"
                    font.pixelSize: Styling.fontSize(-3)
                }

                Item {
                    id: windowDots
                    anchors.centerIn: parent
                    anchors.alignWhenCentered: false
                    readonly property int gap: root.workspaceGap * 2
                    implicitWidth: windowModel.count * workspaceButton.dotSize + Math.max(0, windowModel.count - 1) * gap
                    width: workspaceButton.orbitLayout ? workspaceButton.width : implicitWidth
                    height: workspaceButton.height

                    Repeater {
                        model: windowModel
                        Rectangle {
                            id: windowDot
                            required property int index
                            required property int windowId
                            objectName: "window-dot-" + windowId
                            readonly property real angle: 2 * Math.PI * index / Math.max(1, windowModel.count)
                            width: workspaceButton.dotSize
                            height: width
                            radius: width / 2
                            x: workspaceButton.orbitLayout
                                ? (windowDots.width - width) / 2 + Math.cos(angle) * (windowDots.width / 2 - width)
                                : index * (width + windowDots.gap)
                            y: (windowDots.height - height) / 2 * (workspaceButton.orbitLayout ? 1 + Math.sin(angle) : 1)
                            color: root.orbital && NiriService.focusedClient?.id === windowId ? Colors.primary : BarAppearance.foregroundColor
                            Behavior on x { enabled: root.orbital && Config.animDuration > 0; NumberAnimation { duration: Config.animDuration } }
                            Behavior on y { enabled: root.orbital && Config.animDuration > 0; NumberAnimation { duration: Config.animDuration } }
                            property bool entered: false
                            Timer {
                                running: true
                                interval: 0
                                onTriggered: windowDot.entered = true
                            }
                            opacity: entered ? 1 : 0
                            Behavior on opacity {
                                enabled: Config.animDuration > 0
                                NumberAnimation { duration: Math.min(Config.animDuration, 150) }
                            }
                        }
                    }
                }

                Rectangle {
                    objectName: "workspace-underline-" + workspaceButton.workspaceId
                    anchors.horizontalCenter: parent.horizontalCenter
                    anchors.alignWhenCentered: false
                    anchors.bottom: parent.bottom
                    anchors.bottomMargin: root.workspaceGap
                    width: 2 * Math.round(root.workspaceHeight / 5)
                    height: Math.max(2, Math.round(Styling.fontSize(0) / 7))
                    radius: height / 2
                    color: BarAppearance.activeWorkspaceOutline
                    opacity: workspaceButton.active && !root.orbital ? 1 : 0
                    Behavior on opacity {
                        enabled: Config.animDuration > 0
                        NumberAnimation { duration: Math.min(Config.animDuration, 150) }
                    }
                }

                MouseArea {
                    id: workspaceMouse
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: NiriService.focusWorkspace(workspaceButton.workspaceId)
                }

                StyledToolTip {
                    show: workspaceMouse.containsMouse
                    tooltipText: workspaceButton.displayName + " · " + (workspaceButton.occupied
                        ? workspaceButton.windows.length + (workspaceButton.windows.length === 1 ? " window" : " windows") : "Empty")
                }
            }
        }
    }

    ScrollStepHandler {
        onStepped: steps => {
            NiriService.runNiriAction([steps < 0 ? "focus-workspace-down" : "focus-workspace-up"]);
        }
    }
}
