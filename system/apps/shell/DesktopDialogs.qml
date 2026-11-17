import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Wayland._BackgroundEffect
import qs.config
import Quickshell.Services.Polkit
import qs.modules.components
import qs.modules.theme
import qs.modules.services

Item {
    id: root
    readonly property real shadowMargin: Math.ceil(Math.max(Math.abs(Config.theme.shadowXOffset), Math.abs(Config.theme.shadowYOffset)) + Config.theme.shadowBlur * 16)
    property var request: null
    property var choices: []
    readonly property var flow: agentLoader.item?.flow ?? null
    readonly property bool authenticating: agentLoader.item?.isActive ?? false

    function finish(selection) {
        broker.write(JSON.stringify({selection: selection}) + "\n");
        request = null;
        choices = [];
        card.searchInput.clear();
    }
    function filter() {
        const query = card.searchInput.text.toLocaleLowerCase();
        choices = (request?.lines ?? []).filter(line => String(line).toLocaleLowerCase().includes(query));
        card.choiceList.currentIndex = choices.length ? 0 : -1;
    }
    function submit() {
        if (authenticating) {
            if (flow?.isResponseRequired) {
                flow.submit(card.searchInput.text);
                card.searchInput.clear();
            }
        } else if (card.choiceList.currentIndex >= 0) finish(choices[card.choiceList.currentIndex]);
    }
    function cancel() {
        card.searchInput.clear();
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
                    card.searchInput.clear();
                    root.filter();
                    Qt.callLater(() => card.searchInput.focusInput());
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
            card.searchInput.clear();
            if (root.flow?.isResponseRequired) Qt.callLater(() => card.searchInput.focusInput());
        }
        function onIsCompletedChanged() { card.searchInput.clear(); }
    }
    onAuthenticatingChanged: {
        card.searchInput.clear();
        if (authenticating && request) finish(null);
        if (authenticating) Qt.callLater(() => card.searchInput.focusInput());
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
        implicitWidth: Math.max(1, Math.min(Styling.spacing(620) + root.shadowMargin * 2, (screen?.width ?? 640) - 24))
        implicitHeight: Math.max(1, Math.min(card.contentImplicitHeight + root.shadowMargin * 2, (screen?.height ?? 600) - 48))
        exclusionMode: ExclusionMode.Ignore
        WlrLayershell.namespace: "rebos_shell:dialogs"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: visible ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
        onVisibleChanged: if (visible) Qt.callLater(() => card.searchInput.focusInput())
        BackgroundEffect.blurRegion: BlurRegion { target: card }
        DesktopDialogSurface {
            id: card
            anchors.fill: parent
            anchors.margins: root.shadowMargin
            controller: root
        }
    }
}
