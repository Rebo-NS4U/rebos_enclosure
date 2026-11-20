import QtQuick
import Quickshell
import Quickshell.Io

Variants {
    id: root
    required property string sourceFile
    required property string mode
    required property real screenAspect
    readonly property string effectiveMode: {
        if (mode !== "auto")
            return mode;
        const aspect = instances[0]?.aspect ?? 0;
        const ratio = aspect / screenAspect;
        // For a centered crop this is the fraction of the source area retained.
        return Math.min(ratio, 1 / ratio) >= 0.90 ? "crop" : "fit";
    }

    model: mode === "auto" && sourceFile ? [sourceFile] : []
    Process {
        required property string modelData
        readonly property real aspect: Number(output.text)
        command: ["python3", decodeURIComponent(Qt.resolvedUrl("../../../../scripts/wallpaper_aspect.py").toString().replace("file://", "")), modelData]
        running: true
        stdout: StdioCollector { id: output }
    }
}
