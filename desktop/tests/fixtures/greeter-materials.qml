import QtQuick
import Quickshell
import qs.config
import qs.modules.theme
import qs.modules.components

ShellRoot {
    FloatingWindow {
        id: window
        implicitWidth: 640; implicitHeight: 700
        color: Colors.background
        Item {
            id: capture
            anchors.fill: parent
            StyledRect {
                anchors.centerIn: parent
                width: 440; height: 540
                variant: "bg"
                Column {
                    anchors { fill: parent; margins: 36 }
                    spacing: 28
                    Text { text: Styling.shellStyle; color: Colors.overBackground; font.pixelSize: 24 }
                    StyledRect { width: 368; height: 100; variant: "internalbg" }
                    StyledRect { width: 368; height: 48; variant: "focus"; controlSurface: true }
                    StyledRect { width: 368; height: 36; variant: "primary"; controlSurface: true }
                }
            }
        }
        property var styles: ["orbital", "monolith", "blueprint", "terminal-hardware", "frosted", "colorful", "clear-glass", "glass", "canopy", "metropolis", "custom"]
        property int step: -1
        property bool captured: false
        Timer {
            interval: 800; repeat: true; running: true
            onTriggered: {
                if (window.step >= 0 && !window.captured) {
                    var name = window.styles[window.step];
                    capture.grabToImage(function(result) { result.saveToFile("/tmp/rebos-material-" + name + ".png"); });
                    console.log("MATERIAL_RENDERED", name);
                    window.captured = true;
                    return;
                }
                window.captured = false;
                window.step++;
                if (window.step >= window.styles.length) { stop(); Qt.callLater(Qt.quit); return; }
                var material = Object.assign({}, Config.theme, {shellStyle: window.styles[window.step]});
                if (window.styles[window.step] === "custom") {
                    var radial = {gradient: [["primary", 0], ["background", 1]], gradientType: "radial", gradientAngle: 0, gradientCenterX: 0.5, gradientCenterY: 0.5, halftoneDotMin: 0, halftoneDotMax: 3, halftoneStart: 0, halftoneEnd: 1, halftoneDotColor: "primary", halftoneBackgroundColor: "background", itemColor: "overBackground", border: ["primary", 1], opacity: 1};
                    material.srBg = radial;
                    material.srInternalBg = Object.assign({}, radial, {gradientType: "halftone"});
                    material.srFocus = radial;
                    material.srPrimary = radial;
                }
                Config.appearance = Object.assign({}, Config.appearance, {material: material});
            }
        }
    }
}
