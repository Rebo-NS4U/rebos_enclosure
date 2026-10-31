//@ pragma UseQApplication
//@ pragma ShellId rebos-assistant-ui
//@ pragma DataDir $BASE/rebos_shell
//@ pragma StateDir $BASE/rebos-assistant
import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import Quickshell.Wayland._BackgroundEffect
import qs.config
import qs.modules.services
import qs.modules.globals
import qs.modules.sidebar
import qs.modules.components
ShellRoot {
    // The launcher starts this UI on demand. Keep it while any task needs it;
    // parked bridges retain drafts/history while the hidden UI releases RAM.
    Timer {
        interval: 60000
        running: Ai.sessionsReady && !GlobalStates.assistantVisible
            && Ai.sessions.every(session => session.agentParked || !session.sessionEnabled)
        onTriggered: {
            for (let session of Ai.sessions) session.checkpointBridge();
            idleExit.start();
        }
    }
    Timer { id: idleExit; interval: 250; onTriggered: {
        if (!GlobalStates.assistantVisible
            && Ai.sessions.every(session => session.agentParked || !session.sessionEnabled)) Qt.quit();
    } }
    IpcHandler {
        target: "assistant"
        function toggle(): void { GlobalStates.toggleAssistant(); }
        function dismiss(): void { GlobalStates.hideAssistant(); }
        function reveal(): void {
            if (!GlobalStates.assistantVisible) GlobalStates.toggleAssistant();
        }
        function status(): string {
            return JSON.stringify({visible: GlobalStates.assistantVisible, sessions: Ai.sessions.length, parked: Ai.sessions.filter(session => session.agentParked).length, busySessions: Ai.sessions.filter(session => session.isBusy).length, ready: Ai.sessionsReady, channel: Ai.activeSession.channelId, agent: Ai.activeSession.currentAgentId, busy: Ai.activeSession.isBusy, activityStatus: Ai.activeSession.activityStatus, screen: GlobalStates.assistantScreenName, available: GlobalStates.assistantAvailable, pinned: GlobalStates.assistantPinned, width: GlobalStates.assistantWidth});
        }
        function releaseIdle(): string {
            let released = 0;
            for (let session of Ai.sessions) {
                if (session.releaseIdleAgent()) released++;
            }
            return JSON.stringify({released: released});
        }
    }
    Component.onCompleted: { let ready = Ai.models; }
    Variants {
        model: Quickshell.screens
        PanelWindow {
            id: panel
            required property ShellScreen modelData
            screen: modelData
            // Keep the surface until the closing motion ends. Animation progress
            // is independent of child visibility, avoiding a mapping feedback loop.
            visible: !GlobalStates.assistantPinned && sidebar.presented
            anchors { top: true; bottom: true; left: true; right: true }
            color: "transparent"
            exclusionMode: ExclusionMode.Ignore
            WlrLayershell.namespace: "rebos-assistant"
            WlrLayershell.layer: WlrLayer.Overlay
            WlrLayershell.keyboardFocus: sidebar.active && sidebar.wantsFocus && !GlobalStates.assistantPinned ? WlrKeyboardFocus.Exclusive : WlrKeyboardFocus.None
            mask: Region {
                regions: [
                    Region { item: !GlobalStates.assistantPinned && (sidebar.active || sidebar.hitbox.visible) ? sidebar.hitbox : null },
                    Region { item: !GlobalStates.assistantPinned && sidebar.active ? sidebar.resizeHitbox : null }
                ]
            }
            BackgroundEffect.blurRegion: Region {
                regions: [
                    // A nonempty off-screen region prevents an empty blur mask
                    // from being interpreted as full-screen blur at either endpoint.
                    Region { x: -2; y: -2; width: 1; height: 1 },
                    BlurRegion { target: GlobalStates.assistantPinned ? null : sidebar.blurTarget }
                ]
            }
            AssistantWindow { id: tiledWindow; targetScreen: panel.modelData }
            AssistantSidebar {
                id: sidebar
                targetScreen: panel.modelData
                tiled: GlobalStates.assistantPinned
                windowFocused: !tiled || tiledWindow.compositorFocused
                parent: tiled ? tiledWindow.contentItem : panel.contentItem
                anchors.topMargin: !tiled && Config.bar.position === "top" ? (Config.bar.style === "island" ? 36 : 52) : 0
                anchors.bottomMargin: !tiled && Config.bar.position === "bottom" ? (Config.bar.style === "island" ? 36 : 52) : 0
            }
        }
    }
}
