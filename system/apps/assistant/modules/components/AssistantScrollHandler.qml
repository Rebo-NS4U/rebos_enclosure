import QtQuick

WheelHandler {
    target: null
    acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad

    onWheel: event => scroll(event)

    function scroll(event): void {
        let view = parent;
        while (view && typeof view.cancelFlick !== "function")
            view = view.parent;
        if (!view) {
            event.accepted = false;
            return;
        }
        const delta = event.pixelDelta.y !== 0
            ? event.pixelDelta.y : event.angleDelta.y / 120 * Qt.styleHints.wheelScrollLines * 20;
        if (delta === 0) {
            event.accepted = false;
            return;
        }
        const maximum = Math.max(0, view.contentHeight - view.height);
        const next = Math.max(0, Math.min(maximum, view.contentY - delta * 6));
        event.accepted = next !== view.contentY;
        if (event.accepted) {
            view.cancelFlick();
            view.contentY = next;
            if (typeof view.followBottom === "boolean")
                view.followBottom = next >= maximum - 40;
        }
    }
}
