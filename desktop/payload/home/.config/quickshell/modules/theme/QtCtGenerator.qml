import QtQuick
import Quickshell
import qs.config

QtObject {
    id: root

    function generate(colors: QtObject): void {
        if (!colors)
            return;
        const palette = {};
        for (const name of colors.availableColorNames)
            palette[name] = colors[name].toString();
        palette.opacity = Config.theme.srBg.opacity;
        writer.submit(["python3", Quickshell.shellPath("scripts/apply_desktop_palette.py"), JSON.stringify(palette)]);
    }

    property ThemeWriter writer: ThemeWriter {}
}
