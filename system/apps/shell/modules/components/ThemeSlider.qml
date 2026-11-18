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
    hoverEnabled: true
    opacity: enabled ? 1 : 0.45
    property bool playing: false
    readonly property real animatedPosition: pressed ? position : easedPosition
    property real easedPosition: position
    readonly property real animatedVisualPosition: (!horizontal || mirrored)
        ? 1 - animatedPosition : animatedPosition
    Behavior on easedPosition {
        enabled: !root.pressed && Motion.enabled
        NumberAnimation {
            duration: Motion.enter
            easing.type: Motion.feedbackCurve
        }
    }

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
        SliderTrack {
            anchors.centerIn: parent
            width: Math.max(0, root.horizontal
                ? parent.width - (root.handle?.width ?? 0)
                : parent.height - (root.handle?.height ?? 0))
            hovered: root.hovered
            pressed: root.pressed
            playing: root.playing
            value: root.animatedPosition
            rotation: root.horizontal ? (root.mirrored ? 180 : 0) : 270
        }
    }
    handle: SliderHandle {
        vertical: !root.horizontal
        x: root.leftPadding + (root.horizontal
            ? root.animatedVisualPosition * (root.availableWidth - width)
            : (root.availableWidth - width) / 2)
        y: root.topPadding + (root.horizontal
            ? (root.availableHeight - height) / 2
            : root.animatedVisualPosition * (root.availableHeight - height))
        focused: root.activeFocus
    }
}
