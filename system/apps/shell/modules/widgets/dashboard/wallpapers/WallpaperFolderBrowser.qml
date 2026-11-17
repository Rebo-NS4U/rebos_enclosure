pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.components
import qs.modules.theme
import qs.config

ColumnLayout {
    id: root
    required property var folders
    property string selectedFolder: ""
    property string query: ""
    signal folderSelected(string folder)
    spacing: Styling.spacing(8)

    Button {
        visible: root.selectedFolder !== ""
        text: "‹  All folders"
        onClicked: root.folderSelected("")
        background: StyledRect {
            variant: parent.hovered || parent.visualFocus ? "focus" : "common"
            radius: Styling.radius(2)
        }
        contentItem: StyledText { text: parent.text; color: Colors.overBackground }
    }

    GridView {
        id: grid
        Layout.fillWidth: true
        Layout.fillHeight: true
        visible: root.selectedFolder === ""
        clip: true
        cellWidth: width / Math.max(1, Math.floor(width / 150))
        cellHeight: 110
        boundsBehavior: Flickable.StopAtBounds
        model: root.folders.filter(folder => folder.label.toLowerCase().includes(root.query.trim().toLowerCase()))
        delegate: Button {
            id: tile
            required property var modelData
            width: grid.cellWidth - 8
            height: grid.cellHeight - 8
            Accessible.name: modelData.display
            onClicked: root.folderSelected(modelData.id)
            background: StyledRect {
                variant: tile.hovered || tile.visualFocus ? "focus" : "common"
                radius: Styling.radius(2)
            }
            contentItem: ColumnLayout {
                spacing: Styling.spacing(4)
                Text {
                    Layout.alignment: Qt.AlignHCenter
                    text: Icons.folder
                    font.family: Icons.font
                    font.pixelSize: Styling.fontSize(18)
                    color: Colors.overBackground
                }
                StyledText {
                    Layout.fillWidth: true
                    text: tile.modelData.label
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideMiddle
                }
                StyledText {
                    Layout.alignment: Qt.AlignHCenter
                    text: tile.modelData.count + " wallpapers"
                    color: Colors.overSurfaceVariant
                }
            }
            ToolTip.visible: hovered
            ToolTip.text: modelData.id === "*" ? "All wallpapers" : modelData.id
        }
        ScrollBar.vertical: ScrollBar {}
    }
}
