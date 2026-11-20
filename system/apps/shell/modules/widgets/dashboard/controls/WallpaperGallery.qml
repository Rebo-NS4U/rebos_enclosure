pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import qs.modules.components
import qs.modules.theme

GridView {
    id: gallery
    required property var manager
    required property string screenName
    readonly property string screenWallpaper: manager?.perScreenWallpapers?.[screenName] ?? ""
    readonly property string selectedPath: screenWallpaper || manager?.currentWallpaper || ""
    readonly property int columns: Math.max(1, Math.floor((width - 12) / 248))

    objectName: "wallpaper-gallery"
    Accessible.name: "Wallpaper gallery"
    clip: true
    reuseItems: true
    activeFocusOnTab: true
    keyNavigationEnabled: true
    boundsBehavior: Flickable.StopAtBounds
    cellWidth: Math.max(1, Math.floor((width - 12) / columns))
    cellHeight: Math.round(cellWidth * 9 / 16) + 44
    model: visible ? manager?.wallpaperPaths ?? [] : []
    ScrollBar.vertical: ScrollBar {}

    function choose(index) {
        const path = model[index];
        if (!path || path === selectedPath) return;
        manager.setWallpaper(path, screenWallpaper ? screenName : null);
    }

    onModelChanged: {
        currentIndex = Math.max(0, model.indexOf(selectedPath));
        Qt.callLater(() => positionViewAtIndex(currentIndex, GridView.Contain));
    }
    Keys.onReturnPressed: choose(currentIndex)
    Keys.onEnterPressed: choose(currentIndex)
    Keys.onSpacePressed: choose(currentIndex)

    delegate: SettingsButton {
        id: tile
        required property int index
        required property string modelData
        readonly property bool selected: modelData === gallery.selectedPath
        readonly property bool useThumbnail: gallery.manager?.getFileType(modelData) !== "image"

        width: gallery.cellWidth - 8
        height: gallery.cellHeight - 8
        padding: 5
        focusPolicy: Qt.NoFocus
        text: modelData.split("/").pop()
        Accessible.description: selected ? "Current wallpaper" : ""
        highlighted: selected
        emphasized: gallery.activeFocus && GridView.isCurrentItem
        onClicked: {
            gallery.currentIndex = index;
            gallery.forceActiveFocus();
            gallery.choose(index);
        }
        contentItem: ColumnLayout {
            spacing: 3
            Image {
                objectName: "wallpaper-preview"
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.minimumHeight: 0
                asynchronous: true
                autoTransform: true
                fillMode: Image.PreserveAspectCrop
                clip: true
                sourceSize: Qt.size(Math.max(1, tile.width), Math.max(1, tile.height))
                source: {
                    const path = tile.useThumbnail ? gallery.manager?.getThumbnailPath(tile.modelData) : tile.modelData;
                    if (!path) return "";
                    const url = "file://" + path.split("/").map(encodeURIComponent).join("/");
                    return tile.useThumbnail ? url + "?v=" + gallery.manager.thumbnailsVersion : url;
                }
            }
            StyledText {
                Layout.fillWidth: true
                textFormat: Text.PlainText
                text: (tile.selected ? "✓  " : "") + tile.text
                color: tile.background.itemColor
                font: tile.font
                elide: Text.ElideMiddle
            }
        }
    }
}
