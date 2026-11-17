import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import Quickshell
import qs.modules.components
import qs.modules.globals
import qs.modules.theme
import qs.config

RowLayout {
    id: root
    spacing: Styling.spacing(8)
    readonly property string directory: GlobalStates.wallpaperManager?.wallpaperDir ?? ""

    Button {
        text: "Choose folder…"
        Accessible.name: "Choose wallpaper folder"
        enabled: GlobalStates.wallpaperManager !== null
        implicitHeight: 36
        onClicked: folderDialog.open()
        background: StyledRect {
            variant: parent.down || parent.hovered || parent.visualFocus ? "focus" : "common"
            radius: Styling.radius(2)
        }
        contentItem: Text {
            text: parent.text
            color: Colors.overBackground
            font.family: Config.theme.font
            font.pixelSize: Styling.fontSize(-1)
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
    }

    Text {
        Layout.fillWidth: true
        text: root.directory || "Choose a folder to browse wallpapers"
        elide: Text.ElideMiddle
        color: Colors.overSurfaceVariant
        font.family: Config.theme.font
        font.pixelSize: Styling.fontSize(-2)
        ToolTip.visible: folderHover.hovered
        ToolTip.text: text
        HoverHandler { id: folderHover }
    }

    FolderDialog {
        id: folderDialog
        title: "Choose wallpaper folder"
        currentFolder: "file://" + (root.directory || Quickshell.env("HOME"))
        onAccepted: {
            const url = selectedFolder.toString();
            if (url.startsWith("file://"))
                GlobalStates.wallpaperManager?.setWallpaperDirectory(decodeURIComponent(url.substring(7)));
        }
    }
}
