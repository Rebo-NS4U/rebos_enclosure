import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Services.Polkit
import qs.modules.components
import qs.modules.theme
import qs.modules.services

Item {
    id: root
    property var request: null
    property var choices: []
    readonly property var flow: agentLoader.item?.flow ?? null
    readonly property bool authenticating: agentLoader.item?.isActive ?? false

    function finish(selection) {
        broker.write(JSON.stringify({selection: selection}) + "\n");
        request = null;
        choices = [];
        search.clear();
    }
    function filter() {
        const query = search.text.toLocaleLowerCase();
        choices = (request?.lines ?? []).filter(line => String(line).toLocaleLowerCase().includes(query));
        list.currentIndex = choices.length ? 0 : -1;
    }
    function submit() {
        if (authenticating) {
            if (flow?.isResponseRequired) {
                flow.submit(search.text);
                search.clear();
            }
        } else if (list.currentIndex >= 0) finish(choices[list.currentIndex]);
    }
    function cancel() {
        search.clear();
        if (authenticating) flow?.cancelAuthenticationRequest();
        else if (request) finish(null);
    }
    Process {
        id: broker
        command: ["python3", Qt.resolvedUrl("scripts/menu_broker.py").toString().replace(/^file:\/\//, "")]
        stdinEnabled: true
        running: true
        stdout: SplitParser {
            onRead: data => {
                try {
                    root.request = JSON.parse(data);
                    if (root.authenticating) { root.finish(null); return; }
                    search.clear();
                    root.filter();
                    Qt.callLater(() => search.focusInput());
                } catch (_) { root.request = null; }
            }
        }
        onExited: { root.request = null; retry.restart(); }
    }
    Timer { id: retry; interval: 2000; onTriggered: broker.running = true }
    Loader {
        id: agentLoader
        sourceComponent: PolkitAgent { path: "/org/rebos/Shell/PolkitAgent" }
    }
    // Retry registration after polkit restarts or a former agent releases ownership.
    Timer {
        interval: 10000
        repeat: true
        running: true
        onTriggered: {
            if (!agentLoader.item?.isRegistered && !root.authenticating) {
                agentLoader.active = false;
                agentLoader.active = true;
            }
        }
    }
    Connections {
        target: root.flow
        function onIsResponseRequiredChanged() {
            search.clear();
            if (root.flow?.isResponseRequired) Qt.callLater(() => search.focusInput());
        }
        function onIsCompletedChanged() { search.clear(); }
    }
    onAuthenticatingChanged: {
        search.clear();
        if (authenticating && request) finish(null);
        if (authenticating) Qt.callLater(() => search.focusInput());
    }
    IpcHandler {
        target: "desktopDialogs"
        function status(): string {
            return JSON.stringify({polkitRegistered: agentLoader.item?.isRegistered ?? false,
                authenticating: root.authenticating, selectionOpen: root.request !== null});
        }
        function cancel(): void { root.cancel(); }
        function select(index: int): bool {
            if (root.authenticating || index < 0 || index >= root.choices.length) return false;
            root.finish(root.choices[index]);
            return true;
        }
    }
    PanelWindow {
        id: window
        visible: root.authenticating || root.request !== null
        screen: Quickshell.screens.find(s => s.name === NiriService.focusedMonitor?.name) ?? Quickshell.screens[0]
        color: "transparent"
        implicitWidth: Math.min(620, (screen?.width ?? 640) - 24)
        implicitHeight: Math.min(content.implicitHeight + Styling.spacing(32), (screen?.height ?? 600) - 48)
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "rebos_shell:dialogs"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: visible ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
        onVisibleChanged: if (visible) Qt.callLater(() => search.focusInput())
        StyledRect {
            anchors.fill: parent
            variant: "bg"
            radius: Styling.radius(0)
            enableShadow: true
            Flickable {
                anchors.fill: parent
                anchors.margins: Styling.spacing(16)
                contentHeight: content.implicitHeight
                clip: true
                ColumnLayout {
                    id: content
                    width: parent.width
                    spacing: Styling.spacing(12)
                    focus: true
                    Keys.onEscapePressed: root.cancel()
                    StyledText {
                        Layout.fillWidth: true
                        text: root.authenticating ? "Authentication required" : root.request?.title ?? "Select"
                        font.bold: true
                        wrapMode: Text.Wrap
                    }
                    StyledText {
                        Layout.fillWidth: true
                        visible: root.authenticating
                        text: root.flow?.message ?? ""
                        wrapMode: Text.Wrap
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: Styling.spacing(8)
                        visible: root.authenticating && (root.flow?.identities.length ?? 0) > 1
                        Repeater {
                            model: root.flow?.identities ?? []
                            ThemeButton {
                                required property var modelData
                                text: modelData.displayName || modelData.name || "User"
                                checked: root.flow?.selectedIdentity === modelData
                                onClicked: { search.clear(); root.flow.selectedIdentity = modelData; }
                            }
                        }
                    }
                    StyledText {
                        Layout.fillWidth: true
                        visible: root.authenticating && text.length > 0
                        text: root.flow?.supplementaryMessage || (root.flow?.failed ? "Authentication failed. Try again or cancel." : "")
                        color: root.flow?.supplementaryIsError || root.flow?.failed ? Colors.error : Colors.overSurface
                        wrapMode: Text.Wrap
                    }
                    StyledText {
                        Layout.fillWidth: true
                        visible: root.authenticating
                        text: root.flow?.inputPrompt || "Waiting for authentication…"
                        wrapMode: Text.Wrap
                    }
                    SearchInput {
                        id: search
                        Layout.fillWidth: true
                        enabled: !root.authenticating || (root.flow?.isResponseRequired ?? false)
                        passwordMode: root.authenticating && !root.flow?.responseVisible
                        placeholderText: root.authenticating ? "Authentication response" : root.request?.placeholder ?? "Search…"
                        clearOnEscape: false
                        onSearchTextChanged: if (!root.authenticating) root.filter()
                        onAccepted: root.submit()
                        onEscapePressed: root.cancel()
                        onDownPressed: list.currentIndex = Math.min(root.choices.length - 1, list.currentIndex + 1)
                        onUpPressed: list.currentIndex = Math.max(0, list.currentIndex - 1)
                    }
                    ListView {
                        id: list
                        visible: !root.authenticating
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(320, contentHeight)
                        clip: true
                        model: root.choices
                        currentIndex: -1
                        onCurrentIndexChanged: positionViewAtIndex(currentIndex, ListView.Contain)
                        delegate: ThemeButton {
                            required property string modelData
                            required property int index
                            width: list.width
                            text: modelData
                            highlighted: list.currentIndex === index
                            onClicked: root.finish(modelData)
                        }
                    }
                    StyledText {
                        visible: !root.authenticating && root.choices.length === 0
                        text: "No matching entries"
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        ThemeButton { text: "Cancel"; onClicked: root.cancel() }
                        Item { Layout.fillWidth: true }
                        ThemeButton {
                            text: root.authenticating ? "Authenticate" : "Select"
                            highlighted: true
                            enabled: root.authenticating ? root.flow?.isResponseRequired ?? false : list.currentIndex >= 0
                            onClicked: root.submit()
                        }
                    }
                }
            }
        }
    }
}
