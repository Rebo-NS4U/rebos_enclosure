pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Widgets
import qs.config
import qs.modules.components
import qs.modules.services
import qs.modules.theme

Item {
    id: root

    required property Item bar
    // The island embeds the switcher on its own surface, so it hides this.
    property bool showBackground: true
    readonly property int workspaceHeight: Math.round(Styling.fontSize(0) * 1.85)
    readonly property real outlineWidth: Math.max(1.5, Styling.fontSize(0) / 10)
    readonly property real outlineGap: Styling.fontSize(0) / 7
    readonly property real ringInset: Styling.fontSize(0) / 14
    readonly property real highlightInset: outlineWidth + outlineGap
    readonly property real appInset: highlightInset + outlineGap / 2
    readonly property int appSize: 2 * Math.floor((workspaceHeight - appInset * 2 - 1) / 2)
    readonly property color highlightColor: Config.resolveColor(Config.theme.srFocus.gradient?.[0]?.[0] ?? Config.theme.srFocus.color ?? "surfaceBright")

    readonly property var visibleWorkspaces: NiriService.workspacesForOutput(root.bar.screen.name)

    // Keep workspace buttons stable across window and focus updates.
    ListModel {
        id: workspaceModel
    }

    function syncWorkspaces(): void {
        const ids = root.visibleWorkspaces.map(workspace => workspace.id);
        for (let index = workspaceModel.count - 1; index >= 0; index--) {
            if (!ids.includes(workspaceModel.get(index).workspaceId))
                workspaceModel.remove(index);
        }
        for (let index = 0; index < ids.length; index++) {
            let existingIndex = index;
            while (existingIndex < workspaceModel.count && workspaceModel.get(existingIndex).workspaceId !== ids[index])
                existingIndex++;
            if (existingIndex === workspaceModel.count)
                workspaceModel.insert(index, { workspaceId: ids[index] });
            else if (existingIndex !== index)
                workspaceModel.move(existingIndex, index, 1);
        }
    }

    onVisibleWorkspacesChanged: Qt.callLater(root.syncWorkspaces)
    Component.onCompleted: syncWorkspaces()

    function iconForWindow(window) {
        const entry = DesktopEntries.heuristicLookup(window.appId);
        return entry?.icon || AppSearch.guessIcon(window.appId) || "image-missing";
    }

    implicitWidth: workspaceRow.implicitWidth + root.outlineGap * 3
    implicitHeight: root.workspaceHeight + root.outlineGap * 3

    StyledRect {
        visible: root.showBackground
        anchors.fill: parent
        variant: "bg"
        radius: Styling.radius(7)
        enableShadow: false
    }

    RowLayout {
        id: workspaceRow
        z: 2
        anchors.fill: parent
        anchors.margins: root.outlineGap * 1.5
        spacing: root.outlineGap

        Repeater {
            id: workspaceRepeater
            model: workspaceModel

            Item {
                id: workspaceButton

                required property int workspaceId
                objectName: "workspace-" + workspaceId
                readonly property var workspace: root.visibleWorkspaces.find(workspace => workspace.id === workspaceId) ?? null
                readonly property bool active: workspace?.active ?? false
                readonly property var windows: NiriService.windowsForWorkspace(workspaceId)
                readonly property bool occupied: windows.length > 0
                readonly property string displayName: workspace?.isNamed ? workspace.name : String(workspace?.idx ?? workspaceId)
                Layout.preferredWidth: occupied ? Math.max(root.workspaceHeight, appsRow.implicitWidth + root.appInset * 2) : root.workspaceHeight
                Layout.preferredHeight: root.workspaceHeight
                scale: workspaceMouse.pressed ? 0.94 : 1.0

                Behavior on scale {
                    NumberAnimation {
                        duration: workspaceMouse.pressed ? 80 : 250
                        easing.type: workspaceMouse.pressed ? Easing.OutQuad : Easing.OutBack
                        easing.overshoot: 1.5
                    }
                }

                Behavior on Layout.preferredWidth {
                    enabled: Config.animDuration > 0
                    NumberAnimation {
                        duration: Config.animDuration
                        easing.type: Easing.OutCubic
                    }
                }

                StyledRect {
                    id: workspaceHighlight
                    anchors.fill: parent
                    anchors.margins: root.highlightInset + root.ringInset
                    visible: workspaceButton.active && workspaceButton.occupied
                    variant: "focus"
                    radius: height / 2
                    animateRadius: false
                    enableShadow: false
                    enableBorder: false
                }

                StyledRect {
                    objectName: "workspace-ring-" + workspaceButton.workspaceId
                    anchors.fill: parent
                    anchors.margins: root.ringInset
                    visible: workspaceButton.occupied
                    variant: "transparent"
                    radius: height / 2
                    animateRadius: false
                    enableShadow: false
                    // Concentric pills keep the same gap at every workspace width.
                    readonly property color outlineColor: workspaceButton.workspace?.is_urgent
                        ? Colors.red
                        : (workspaceButton.active
                            ? Qt.rgba(Colors.primaryFixed.r, Colors.primaryFixed.g, Colors.primaryFixed.b, 0.5)
                            : (workspaceHighlight.color.a > 0 ? workspaceHighlight.color : root.highlightColor))
                    border.width: root.outlineWidth
                    border.color: outlineColor
                    color: "transparent"

                    Rectangle {
                        anchors.fill: parent
                        color: Styling.srItem("overprimary")
                        opacity: workspaceMouse.containsMouse && !workspaceButton.active ? 0.12 : 0
                        radius: height / 2
                    }
                }

                Rectangle {
                    objectName: "empty-workspace-dot-" + workspaceButton.workspaceId
                    anchors.centerIn: parent
                    anchors.alignWhenCentered: false
                    visible: !workspaceButton.occupied
                    width: Math.max(4, root.workspaceHeight / 5)
                    height: width
                    radius: width / 2
                    color: workspaceButton.workspace?.is_urgent ? Colors.red
                        : (workspaceButton.active ? Colors.primary : Colors.overSurfaceVariant)
                    opacity: workspaceButton.active || workspaceMouse.containsMouse ? 1 : 0.6
                }

                Row {
                    id: appsRow
                    z: 2
                    anchors.centerIn: parent
                    anchors.alignWhenCentered: false
                    visible: opacity > 0
                    opacity: workspaceButton.occupied ? 1 : 0
                    scale: workspaceButton.occupied ? 1 : 0.85
                    spacing: root.outlineGap

                    Behavior on opacity {
                        enabled: Config.animDuration > 0
                        NumberAnimation {
                            duration: Config.animDuration / 2
                            easing.type: Easing.OutQuad
                        }
                    }

                    Behavior on scale {
                        enabled: Config.animDuration > 0
                        NumberAnimation {
                            duration: Config.animDuration
                            easing.type: Easing.OutBack
                            easing.overshoot: 1.1
                        }
                    }

                    Repeater {
                        model: workspaceButton.windows

                        Item {
                            id: appButton

                            required property var modelData
                            objectName: "taskbar-window-" + windowData.id
                            readonly property var windowData: modelData
                            readonly property bool focused: NiriService.focusedClient?.id === windowData.id
                            readonly property string iconName: root.iconForWindow(windowData)

                            width: root.appSize
                            height: width
                            scale: appMouse.pressed ? 0.92 : 1.0

                            Behavior on scale {
                                NumberAnimation {
                                    duration: appMouse.pressed ? 80 : 250
                                    easing.type: appMouse.pressed ? Easing.OutQuad : Easing.OutBack
                                    easing.overshoot: 1.5
                                }
                            }

                            Rectangle {
                                objectName: "app-circle-" + appButton.windowData.id
                                anchors.fill: parent
                                radius: height / 2
                                color: appButton.focused ? Colors.primary : Styling.srItem("overprimary")
                                opacity: appButton.focused ? 1 : (appMouse.containsMouse ? 0.18 : 0)
                                border.width: appButton.focused ? 1 : 0
                                border.color: Colors.primaryFixed
                            }

                            // Keep icon artwork inside the themed app badge.
                            ClippingRectangle {
                                id: appIconClip
                                anchors.centerIn: parent
                                anchors.alignWhenCentered: false
                                width: appButton.width - 2
                                height: width
                                radius: width / 2
                                color: "transparent"
                                clip: true

                                IconImage {
                                    id: appIcon
                                    objectName: "app-icon-" + appButton.windowData.id
                                    anchors.centerIn: parent
                                    anchors.alignWhenCentered: false
                                    // Keep even dimensions inside the even-sized
                                    // badge so centerIn does not round to one side.
                                    width: 2 * Math.floor(root.appSize * (appButton.focused ? 0.7 : 0.6) / 2)
                                    height: width
                                    opacity: appButton.focused ? 1 : 0.62
                                    source: "image://icon/" + appButton.iconName
                                    // Small app icons can load without a pending async request at reload.
                                    asynchronous: false
                                    layer.enabled: true
                                    layer.effect: ShaderEffect {
                                        property Item source
                                        // Contrast with the primary-colored focused badge.
                                        property color tintColor: appButton.focused ? Colors.overPrimary : Colors.primary
                                        fragmentShader: Qt.resolvedUrl("../../components/icon_tint.frag.qsb")
                                    }

                                    Behavior on width {
                                        enabled: Config.animDuration > 0
                                        NumberAnimation {
                                            duration: Math.min(Config.animDuration, 150)
                                            easing.type: Easing.OutQuad
                                        }
                                    }

                                    Behavior on opacity {
                                        enabled: Config.animDuration > 0
                                        NumberAnimation {
                                            duration: Math.min(Config.animDuration, 150)
                                            easing.type: Easing.OutQuad
                                        }
                                    }

                                    onStatusChanged: {
                                        if (status === Image.Error && appButton.iconName !== "image-missing")
                                            source = "image://icon/image-missing";
                                    }
                                }
                            }

                            Rectangle {
                                anchors.horizontalCenter: parent.horizontalCenter
                                anchors.bottom: parent.bottom
                                anchors.bottomMargin: 1
                                width: 10
                                height: 2
                                radius: 1
                                color: Colors.primaryFixed
                                visible: appButton.focused
                            }

                            MouseArea {
                                id: appMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: mouse => {
                                    mouse.accepted = true;
                                    NiriService.focusWindow(appButton.windowData.id);
                                }
                            }

                            StyledToolTip {
                                show: appMouse.containsMouse
                                tooltipText: appButton.windowData.title || appButton.windowData.appId
                            }
                        }
                    }
                }

                MouseArea {
                    id: workspaceMouse
                    anchors.fill: parent
                    z: 1
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: NiriService.focusWorkspace(workspaceButton.workspaceId)
                }

                StyledToolTip {
                    show: workspaceMouse.containsMouse
                    tooltipText: workspaceButton.displayName + (workspaceButton.occupied ? "" : " · Empty")
                }
            }
        }
    }

    WheelHandler {
        onWheel: event => {
            if (event.angleDelta.y < 0)
                NiriService.runNiriAction(["focus-workspace-down"]);
            else if (event.angleDelta.y > 0)
                NiriService.runNiriAction(["focus-workspace-up"]);
        }
        acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
    }
}
