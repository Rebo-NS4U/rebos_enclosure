import QtQuick
import QtQuick.Controls
import qs.modules.theme
Slider {
    id: root
    implicitHeight: 32
    implicitWidth: 100
    padding: 8
    focusPolicy: Qt.StrongFocus
    wheelEnabled: false
    opacity: enabled ? 1 : 0.45
    // A small pointer detent at each quarter; programmatic updates stay exact.
    function snapQuarter(ratio: real): real {
        const quarter = Math.round(ratio * 4) / 4;
        return quarter > 0 && quarter < 1 && Math.abs(ratio - quarter) <= 0.050000001
            ? quarter : ratio;
    }

    onMoved: {
        if (pressed && to !== from) {
            const ratio = (value - from) / (to - from);
            const snapped = snapQuarter(ratio);
            if (snapped !== ratio) value = from + snapped * (to - from);
        }
    }
    background: StandardProgressBar {
        x: root.leftPadding
        y: root.topPadding + (root.availableHeight - height) / 2
        width: root.availableWidth
        height: 2
        value: root.position
        rotation: root.mirrored ? 180 : 0
    }
    handle: SliderHandle {
        x: root.leftPadding + root.visualPosition * (root.availableWidth - width)
        y: root.topPadding + (root.availableHeight - height) / 2
        focused: root.activeFocus
    }
}
