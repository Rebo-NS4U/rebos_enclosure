//@ pragma UseQApplication
//@ pragma ShellId rebos_shell
//@ pragma DataDir $BASE/rebos_shell
//@ pragma StateDir $BASE/rebos_shell

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Wayland
import qs.modules.services
import qs.modules.lockscreen
import qs.modules.globals
import qs.modules.shell
import qs.modules.shell.osd
import qs.modules.widgets.dashboard.wallpapers
import qs.modules.widgets.config
import qs.config
import qs.modules.components

ShellRoot {
    id: root


    DesktopDialogs {}

    // Keep the inherited wallpaper owner: it also provides the wallpaper
    // manager used by the lockscreen.
    Variants {
        model: Quickshell.screens

        Loader {
            id: wallpaperLoader
            active: true
            required property ShellScreen modelData
            sourceComponent: Wallpaper {
                screen: wallpaperLoader.modelData
            }
        }
    }

    // The shell owns one panel per configured screen. Transient UI such as the
    // run menu is rendered inside this same panel instead of separate windows.
    Variants {
        model: Quickshell.screens

        Item {
            id: screenShellContainer
            required property ShellScreen modelData

            UnifiedShellPanel {
                id: unifiedPanel
                targetScreen: screenShellContainer.modelData
            }

            // Exclusive zone reservations
            ReservationWindows {
                screen: screenShellContainer.modelData

                // Keep exclusive zone even during niri overview so tiled
                // windows do not reflow. Bar is only hidden visually.
                barEnabled: unifiedPanel.barEnabled
                barSize: unifiedPanel.barTargetHeight
                barOuterMargin: unifiedPanel.barOuterMargin
                barPosition: Config.bar?.position ?? "top"

            }

            // Volume / mic / brightness OSD for keyboard media keys (standard bar only; island bar embeds its own OSD)
            LockKeyOSD {
                targetScreen: screenShellContainer.modelData
            }

            Loader {
                active: Config.barReady ? (Config.bar?.style ?? "default") !== "island" : false
                sourceComponent: OSD {
                    targetScreen: screenShellContainer.modelData
                }
            }
        }
    }

    // Secure WlSessionLock lockscreen
    WlSessionLock {
        id: sessionLock
        locked: GlobalStates.lockscreenVisible

        // Surface auto-created per screen. Defer animation until the protocol
        // confirms niri has locked every output.
        LockScreen {
            lockSecure: sessionLock.secure
        }
    }

    // Toasts are hosted inside UnifiedShellPanel (NotificationToastStack) so
    // they receive clicks. NotificationServer still loads via service init.

    // Keep the window object alive so IPC can toggle its visible property.
    SettingsWindow {}

    // Niri runs the selected action. Hold logind's lid-switch inhibitor so
    // the system lid policy cannot run a second action for the same event.
    FileView {
        id: lidConfig
        property bool hasOverride: false
        path: (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config") + "/niri/config.kdl"
        preload: true
        watchChanges: true
        printErrors: false
        onFileChanged: reload()
        onLoaded: hasOverride = /^include optional=true .+ \/\/ Enclosure lid (action|suspend)$/m.test(text())
        onLoadFailed: hasOverride = false
    }

    Process {
        running: lidConfig.hasOverride
        stdinEnabled: true
        command: ["systemd-inhibit", "--what=handle-lid-switch", "--who=Enclosure",
            "--why=The desktop is handling the lid switch", "--mode=block", "cat"]
        onExited: code => {
            if (code !== 0 && lidConfig.hasOverride)
                console.warn("Could not take over the system lid switch.");
        }
    }

    // Initialize only the services needed by the bar, run menu, and lockscreen.
    QtObject {
        id: serviceInitializer

        Component.onCompleted: {
            Qt.callLater(() => {
                let _ = GlobalShortcuts.appId;
                _ = LockscreenService.prepActive;
                // Keep compositor + OSD services hot for overview hide and media keys.
                _ = NiriService.overviewOpen;
                _ = DesktopBlur.appliedMode;
                _ = Audio.value;
                _ = AudioEqualizer.initialized;
                _ = AudioFormat.connected;
                _ = Brightness.monitors;
                // Own org.freedesktop.Notifications and load history early.
                _ = Notifications.appNameList;
                _ = StateService.initialized;
                // Assistant sessions belong to the separate assistant application.
            });
        }

    }
}
