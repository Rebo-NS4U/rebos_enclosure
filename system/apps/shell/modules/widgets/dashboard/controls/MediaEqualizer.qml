import QtQuick
import QtQuick.Window
import QtQuick.Controls
import qs.modules.theme

Item {
    id: root
    objectName: "media-equalizer"
    implicitWidth: Styling.spacing(400)
    // Reserve the former lyrics area, with room for playback controls above it.
    readonly property real maximumHeight: Math.max(100, Math.min(Styling.spacing(300),
        (Screen.height > 0 ? Screen.height : 1000) - Styling.spacing(420)))
    implicitHeight: Math.min(equalizer.implicitHeight, maximumHeight)
    readonly property Item focusedControl: Window.window?.activeFocusItem ?? null
    onFocusedControlChanged: {
        let ancestor = focusedControl;
        while (ancestor && ancestor !== equalizer) ancestor = ancestor.parent;
        if (!ancestor) return;
        const top = focusedControl.mapToItem(equalizer, 0, 0).y;
        const bottom = top + focusedControl.height;
        if (top < scroll.contentY) scroll.contentY = Math.max(0, top);
        else if (bottom > scroll.contentY + scroll.height)
            scroll.contentY = Math.min(Math.max(0, scroll.contentHeight - scroll.height), bottom - scroll.height);
    }
    Flickable {
        id: scroll
        objectName: "media-equalizer-scroll"
        anchors.fill: parent
        contentWidth: width
        contentHeight: equalizer.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        clip: true
        ScrollBar.vertical: ScrollBar {}
        AudioEqualizerPanel {
            id: equalizer
            width: scroll.width
            compact: true
        }
    }
}
