pragma Singleton
import QtQuick
import Quickshell
import qs.config
import qs.modules.services
Singleton {
    property Item wallpaperManager: null
    readonly property bool assistantAvailable: Config.aiReady
        && (Config.ai.enabled ?? true)
        && (Config.ai.sidebarEnabled ?? true)
    property bool assistantVisible: false
    property bool assistantPinned: Config.ai.sidebarPinnedOnStartup ?? false
    property int assistantWidth: Config.ai.sidebarWidth ?? 400
    property string assistantPosition: Config.ai.sidebarPosition ?? "right"
    property string assistantScreenName: ""

    signal assistantFocusRequested(bool wasAlreadyOpen)

    function toggleAssistant() {
        if (!assistantAvailable) {
            assistantVisible = false;
            return;
        }
        if (assistantVisible) {
            hideAssistant();
        } else {
            if (NiriService.focusedMonitor && NiriService.focusedMonitor.name) {
                assistantScreenName = NiriService.focusedMonitor.name;
            } else if (Quickshell.screens.length > 0) {
                assistantScreenName = Quickshell.screens[0].name;
            }
            assistantVisible = true;
            assistantFocusRequested(false);
        }
    }

    function hideAssistant() {
        assistantVisible = false;
    }

    onAssistantAvailableChanged: {
        if (!assistantAvailable)
            hideAssistant();
    }

}
