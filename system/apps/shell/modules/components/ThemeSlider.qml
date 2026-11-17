import QtQuick
import QtQuick.Controls
import qs.modules.theme
Slider {
    id: root
    implicitHeight: horizontal ? 32 : 140
    implicitWidth: horizontal ? 100 : 32
    padding: 8
    focusPolicy: Qt.StrongFocus
    wheelEnabled: false
    opacity: enabled ? 1 : 0.45
    // A small pointer detent at each quarter; programmatic updates stay exact.
    function snapQuarter(ratio: real): real {
        const quarter = Math.round(ratio * 4) / 4;
        return quarter > 0 && quarter < 1 && Math.abs(ratio - quarter) <= 0.030000001
            ? quarter : ratio;
    }

    onMoved: {
        if (pressed && to !== from) {
            const ratio = (value - from) / (to - from);
            const snapped = snapQuarter(ratio);
            if (snapped !== ratio) value = from + snapped * (to - from);
        }
    }
    background: Item {
        x: root.leftPadding
        y: root.topPadding
        width: root.availableWidth
        height: root.availableHeight
        StandardProgressBar {
            anchors.centerIn: parent
            width: root.horizontal ? parent.width : parent.height
            height: 2
            value: root.position
            rotation: root.horizontal ? (root.mirrored ? 180 : 0) : 270
        }
    }
    handle: SliderHandle {
        x: root.leftPadding + (root.horizontal ? root.visualPosition * (root.availableWidth - width) : (root.availableWidth - width) / 2)
        y: root.topPadding + (root.horizontal ? (root.availableHeight - height) / 2 : root.visualPosition * (root.availableHeight - height))
        focused: root.activeFocus
    }
}
