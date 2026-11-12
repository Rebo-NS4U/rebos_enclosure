pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import qs.modules.globals
import qs.modules.services
import qs.config
import Quickshell.Io
import "../theme/ShellStyles.js" as ShellStyles

Singleton {
    id: root

    readonly property string appId: "rebos_shell"
    readonly property string ipcRuntimeDir: Quickshell.env("XDG_RUNTIME_DIR") || "/tmp"

    // High-performance Pipe Listener (Daemon mode)
    Process {
        id: pipeListener
        command: ["bash", "-c", 'set -euo pipefail; pipe="$1/rebos_shell_ipc_$UID.pipe"; rm -f -- "$pipe"; mkfifo -m 600 -- "$pipe"; exec tail -f -- "$pipe"', "rebos-shell-ipc", root.ipcRuntimeDir]
        running: true
        
        stdout: SplitParser {
            onRead: data => {
                const cmd = data.trim();
                if (cmd !== "") {
                    root.run(cmd);
                }
            }
        }
    }

    IpcHandler {
        target: "typing"
        function toggle(): void { root.run("typing"); }
        function close(): void {
            const island = Visibilities.getIslandForActive();
            if (island?.currentMode === "typing") island.collapse();
        }
        function resume(): void {
            const island = Visibilities.getIslandForActive();
            if (island) {
                island.expand("typing");
                island.typingPractice.reopen();
            }
        }
        function upload(): void {
            const island = Visibilities.getIslandForActive();
            if (island) { island.expand("typing"); island.typingPractice.openImport(); }
        }
        function preset(index: int): void { Visibilities.getIslandForActive()?.typingPractice.loadPreset(index); }
        function start(): void { Visibilities.getIslandForActive()?.typingPractice.start(); }
        function status(): string {
            const island = Visibilities.getIslandForActive();
            const state = JSON.parse(island?.typingPractice.status() ?? "{}");
            state.opened = island?.currentMode === "typing";
            return JSON.stringify(state);
        }
    }

    IpcHandler {
        target: "lyrics"
        function timing(): string {
            return JSON.stringify({position: MprisController.position, playing: MprisController.isPlaying,
                activeLine: LyricsService.currentLine, followLine: LyricsService.followLine,
                displayLineCount: LyricsService.displayLines.length,
                clockEnabled: LyricsService.playbackClock.enabled});
        }
        function toggle(): void { root.run("lyrics"); }
        function status(): string {
            return JSON.stringify({opened: LyricsService.pinEdge !== "",
                edge: LyricsService.pinEdge, screen: LyricsService.pinScreen,
                hasLyrics: LyricsService.hasLyrics});
        }
    }

    Timer {
        id: mediaFeedbackTimer
        interval: 2000
        property var island: null
        onTriggered: {
            if (island && island.currentMode === "media")
                island.collapse();
            island = null;
        }
    }

    function toggleMedia() {
        // Explicitly opening the menu must cancel the playback-key preview timeout.
        mediaFeedbackTimer.stop();
        mediaFeedbackTimer.island = null;
        const island = Visibilities.getIslandForActive();
        if (island) {
            if (island.currentMode === "media" && !island.retractingToHidden) island.collapse();
            else island.expand("media");
        } else {
            Visibilities.getDashboardControllerForActive()?.toggleCenterMenu();
        }
    }

    function revealMediaFeedback(): bool {
        const island = Visibilities.getIslandForActive();
        if (!island) return false;
        island.expand("media");
        mediaFeedbackTimer.island = island;
        mediaFeedbackTimer.restart();
        return true;
    }

    // Playback keys select Spotify and reveal the same panel as the bar's media button.
    IpcHandler {
        target: "media"

        function toggle(): void { root.toggleMedia(); }

        function reveal(): bool {
            return root.revealMediaFeedback();
        }

        function control(action: string): bool {
            if (["PlayPause", "Pause", "Next", "Previous", "Stop"].indexOf(action) === -1)
                return false;
            const player = MprisController.filteredPlayers.find(p =>
                (p.dbusName || "").toLowerCase().includes("spotify"));
            if (!player) return false;
            MprisController.setActivePlayer(player);
            // Keep playback commands on D-Bus, including Stop which has no QML helper.
            Quickshell.execDetached(["busctl", "--user", "call", player.dbusName,
                "/org/mpris/MediaPlayer2", "org.mpris.MediaPlayer2.Player", action]);
            root.revealMediaFeedback();
            return true;
        }

        function status(): string {
            return JSON.stringify({
                mode: Visibilities.getIslandForActive()?.currentMode || "",
                player: MprisController.activePlayer?.dbusName || "",
                title: MprisController.trackTitle,
                playing: MprisController.isPlaying
            });
        }
    }

    function run(command) {
        console.log("IPC run command received:", command);
        const barAccentPrefix = "bar-accent ";
        if (command.startsWith(barAccentPrefix)) {
            const strength = Number(command.slice(barAccentPrefix.length));
            if (Config.barReady && Number.isInteger(strength) && strength >= 0 && strength <= 100)
                Config.bar.islandAccent = strength;
            else
                console.warn("Ignoring invalid bar accent strength:", command);
            return;
        }
        if (command !== "notes" && QuickNotes.visible)
            QuickNotes.close();
        switch (command) {
            case "lyrics":
                LyricsService.toggle(NiriService.focusedMonitor?.name || "");
                break;
            case "t":
            case "typing":
                const typingIsland = Visibilities.getIslandForActive();
                if (typingIsland) {
                    if (typingIsland.currentMode === "typing" && !typingIsland.retractingToHidden) typingIsland.collapse();
                    else { typingIsland.expand("typing"); typingIsland.typingPractice.reopen(); }
                }
                break;
            case "file-shelf":
            case "shelf":
                FileShelf.toggle("");
                break;
            case "notes":
                if (!QuickNotes.visible)
                    Visibilities.clearAll();
                QuickNotes.toggle();
                break;
            case "launcher": toggleLauncher(); break;
            case "projects":
            case "project-picker":
            case "projectpicker":
                toggleProjects();
                break;
            case "assistant":
            case "dashboard-assistant":
                toggleAssistant();
                break;
            case "system-monitor":
            case "stats":
            case "resources":
                Visibilities.toggleSystemMonitorForActive();
                break;
            case "wallpaper":
            case "wallpapers":
                toggleWallpapers();
                break;
            case "powermenu":
            case "power":
                Visibilities.togglePowerMenuForActive();
                break;
            case "alerts":
            case "notifications":
                toggleAlerts();
                break;
            case "dashboard": toggleDashboard(); break;
            case "sound":
            case "audio":
                Visibilities.setActiveModule("sound");
                break;
            case "mic":
            case "microphone":
                Visibilities.setActiveModule("mic");
                break;
            case "wifi":
            case "network":
                Visibilities.setActiveModule("wifi");
                break;
            case "bluetooth":
                Visibilities.setActiveModule("bluetooth");
                break;
            case "battery":
            case "powerprofile":
                Visibilities.setActiveModule("battery");
                break;
            case "weather":
                Visibilities.setActiveModule("weather");
                break;
            case "calendar":
            case "datetime":
                Visibilities.setActiveModule("calendar");
                break;
            case "lockscreen": LockscreenService.lock(); break;
            case "config":
            case "settings":
            case "dashboard-controls":
                Visibilities.closeActiveBarPopup();
                Visibilities.setActiveModule("");
                GlobalStates.settingsTargetWorkspaceId = NiriService.focusedMonitor?.activeWorkspace?.id || NiriService.focusedWorkspace?.id || 0;
                GlobalStates.settingsTargetScreenName = NiriService.focusedMonitor?.name || "";
                GlobalStates.settingsWindowVisible = true;
                for (const client of NiriService.clients.values || []) {
                    if (client.title === "rebos_shell Settings") {
                        if (GlobalStates.settingsTargetWorkspaceId)
                            NiriService.moveWindowToWorkspace(client.id, GlobalStates.settingsTargetWorkspaceId, false);
                        NiriService.focusWindow(client.id);
                        break;
                    }
                }
                break;
            case "appearance":
                if (!GlobalStates.settingsWindowVisible)
                    toggleSettings();
                GlobalStates.settingsCurrentTab = 4;
                break;
            case "new-window-rule":
                if (!GlobalStates.settingsWindowVisible)
                    toggleSettings();
                GlobalStates.settingsCurrentTab = 8;
                GlobalStates.settingsNewWindowRuleRequested = true;
                break;
            default: console.warn("Unknown IPC command:", command);
        }
    }

    property IpcHandler ipcHandler: IpcHandler {
        target: "rebos_shell"

        function run(command: string) {
            root.run(command);
        }

        function wallpaper(path: string, mode: string): bool {
            const manager = GlobalStates.wallpaperManager;
            if (!manager || !path || manager.supportedWallpaperModes.indexOf(mode) === -1)
                return false;
            manager.setWallpaperMode(mode);
            manager.setWallpaper(path);
            return true;
        }

        function themeStyle(style: string): bool {
            if (!ShellStyles.styles.some(entry => entry.id === style)) return false;
            Config.theme.shellStyle = style;
            return true;
        }

        function borderStyle(style: string): bool {
            if (["band", "dotted", "double"].indexOf(style) === -1) return false;
            Config.theme.ditherBorder = style;
            return true;
        }

        function wallpaperDitherStrength(strength: string): bool {
            if (["normal", "strong", "intense"].indexOf(strength) === -1) return false;
            Config.theme.wallpaperDitherStrength = strength;
            return true;
        }

        function themeStatus(): string {
            const manager = GlobalStates.wallpaperManager;
            return JSON.stringify({style: Config.theme.shellStyle,
                ditherPalette: Config.theme.ditherPalette,
                border: Config.theme.ditherBorder,
                wallpaperStrength: Config.theme.wallpaperDitherStrength,
                wallpaper: manager?.currentWallpaper ?? "",
                renderedWallpaper: manager?.renderedWallpaper ?? "",
                themeColorSource: manager ? manager.getColorSource(manager.currentWallpaper) : "",
                converting: DitheredWallpapers.busy,
                error: DitheredWallpapers.error});
        }
    }

    function toggleLauncher() {
        if ((Config.bar?.style ?? "default") === "island") {
            const island = Visibilities.getIslandForActive();
            if (island) {
                if (island.isExpanded && island.currentMode === "apps") {
                    island.collapse();
                } else {
                    GlobalStates.launcherMode = "apps";
                    GlobalStates.clearLauncherState();
                    island.expand("apps");
                }
                return;
            }
        }

        const isActive = Visibilities.currentActiveModule === "launcher"
            && GlobalStates.launcherMode === "apps";
        if (isActive) {
            Visibilities.setActiveModule("");
        } else {
            GlobalStates.launcherMode = "apps";
            GlobalStates.clearLauncherState();
            Visibilities.setActiveModule("launcher");
        }
    }

    function toggleProjects() {
        if ((Config.bar?.style ?? "default") === "island") {
            const island = Visibilities.getIslandForActive();
            if (island) {
                if (island.isExpanded && island.currentMode === "projects") {
                    island.collapse();
                } else {
                    GlobalStates.launcherMode = "projects";
                    GlobalStates.clearProjectPickerState();
                    island.expand("projects");
                }
                return;
            }
        }

        const isActive = Visibilities.currentActiveModule === "launcher"
            && GlobalStates.launcherMode === "projects";
        if (isActive) {
            Visibilities.setActiveModule("");
        } else {
            GlobalStates.launcherMode = "projects";
            GlobalStates.clearProjectPickerState();
            Visibilities.setActiveModule("launcher");
        }
    }

    function toggleWallpapers() {
        if ((Config.bar?.style ?? "default") === "island") {
            const island = Visibilities.getIslandForActive();
            if (island) {
                if (island.isExpanded && island.currentMode === "wallpapers") {
                    island.collapse();
                } else {
                    Visibilities.clearAll();
                    Visibilities.currentActiveModule = "wallpapers";
                    island.expand("wallpapers");
                }
                return;
            }
        }

        const controller = Visibilities.getDashboardControllerForActive();
        if (!controller) {
            console.warn("GlobalShortcuts: no dashboard controller registered for the focused monitor");
            return;
        }
        controller.toggleWallpapers();
    }

    function toggleAlerts() {
        if ((Config.bar?.style ?? "default") === "island") {
            const island = Visibilities.getIslandForActive();
            if (island) {
                if (island.isExpanded && island.currentMode === "alerts") {
                    island.collapse();
                } else {
                    Visibilities.clearAll();
                    Visibilities.currentActiveModule = "alerts";
                    island.expand("alerts");
                }
                return;
            }
        }
        Visibilities.setActiveModule("alerts");
    }

    function toggleDashboard() {
        if ((Config.bar?.style ?? "default") === "island") {
            const island = Visibilities.getIslandForActive();
            if (island) {
                if (island.isExpanded && island.currentMode === "dashboard") {
                    island.collapse();
                } else {
                    Visibilities.clearAll();
                    Visibilities.currentActiveModule = "dashboard";
                    island.expand("dashboard");
                }
                return;
            }
        }

        const controller = Visibilities.getDashboardControllerForActive();
        if (!controller) {
            console.warn("GlobalShortcuts: no dashboard controller registered for the focused monitor");
            return;
        }
        controller.toggleCenterMenu();
    }

    function toggleSettings(screenName) {
        const willOpen = !GlobalStates.settingsWindowVisible;
        if (willOpen) {
            const targetMonitor = screenName
                ? NiriService.monitorFor(screenName)
                : NiriService.focusedMonitor;
            GlobalStates.settingsTargetWorkspaceId =
                targetMonitor?.activeWorkspace?.id
                || NiriService.focusedMonitor?.activeWorkspace?.id
                || NiriService.focusedWorkspace?.id
                || 0;
            GlobalStates.settingsTargetScreenName =
                targetMonitor?.name || NiriService.focusedMonitor?.name || "";
            // Close bar popups / run menu under the settings window.
            Visibilities.closeActiveBarPopup();
            Visibilities.setActiveModule("");
        }
        GlobalStates.settingsWindowVisible = willOpen;
    }

    function toggleAssistant() {
        if (!GlobalStates.assistantAvailable) {
            GlobalStates.hideAssistant();
            return;
        }
        GlobalStates.toggleAssistant();
    }
}
