pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import qs.modules.globals
import qs.modules.services
import qs.modules.components

SettingsGroup {
    id: root
    title: "Wallpaper"
    property string settingsAnchor: "wallpaper"
    readonly property var manager: GlobalStates.wallpaperManager

    SettingsButton {
        text: "Choose wallpaper"
        enabled: !!root.manager
        onClicked: {
            GlobalStates.settingsWindowVisible = false;
            GlobalShortcuts.toggleWallpapers();
        }
    }
    StyledText { text: "Wallpaper folder" }
    SettingsTextField {
        objectName: "wallpaper-folder"
        Layout.fillWidth: true
        Accessible.name: "Wallpaper folder"
        enabled: !!root.manager
        text: root.manager?.wallpaperDir ?? ""
        placeholderText: "Default wallpaper folder"
        onEditingFinished: root.manager?.setWallpaperDirectory(text)
    }
    StyledText { text: "Display mode" }
    SettingsComboBox {
        Layout.fillWidth: true
        Accessible.name: "Wallpaper display mode"
        enabled: !!root.manager
        model: root.manager?.wallpaperModes ?? []
        textRole: "label"
        valueRole: "id"
        currentIndex: model.findIndex(entry => entry.id === root.manager?.wallpaperMode)
        onActivated: root.manager.setWallpaperMode(currentValue)
    }
    StyledText {
        Layout.fillWidth: true
        wrapMode: Text.WordWrap
        text: "Auto fit fills each screen when cropping removes at most 10% of the picture. Otherwise it shows the whole picture."
    }
}
