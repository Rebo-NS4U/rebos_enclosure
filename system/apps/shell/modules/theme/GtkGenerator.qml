import QtQuick
import Quickshell
import qs.config

QtObject {
    function generate(colors) {
        if (!colors) return;
        const value = colors.background.toString().slice(-6);
        const luma = parseInt(value.slice(0,2),16) * .299 + parseInt(value.slice(2,4),16) * .587 + parseInt(value.slice(4,6),16) * .114;
        const dark = luma < 128;
        // CSS and geometry are serialized by apply_desktop_palette.py.
        // Notify GTK clients without clearing the theme or restarting applications.
        writerProcess.submit(["sh", "-c", "gsettings set org.gnome.desktop.interface color-scheme " + (dark ? "prefer-dark" : "prefer-light") + "; gsettings set org.gnome.desktop.interface gtk-theme " + (dark ? "adw-gtk3-dark" : "adw-gtk3")]);
    }
    property ThemeWriter writerProcess: ThemeWriter {}
}
