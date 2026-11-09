import QtQuick
import QtQuick.Window
import Quickshell
ShellRoot {
    Window {
        id: window
        visible: true
        width: 640; height: 600
        TypingMenu { id: menu; anchors.fill: parent }
    }
    function find(item, name) {
        if (item.objectName === name) return item;
        for (const child of item.children || []) { const result = find(child, name); if (result) return result; }
        return null;
    }
    Timer {
        running: true; repeat: true; interval: 350
        property int phase: 0
        property int hold: 0
        property var sizes: [[360, 640], [640, 480], [1280, 720], [1920, 1080], [2560, 1440], [3840, 2160]]
        onTriggered: {
            try {
                if (phase === 0) {
                    menu.practicing = true;
                    menu.bookLength = 100000;
                    menu.chapters = [{title: 'Resolution test', position: 0}];
                    menu.pageSource = 'A passage that reflows while keeping the bookmark and input intact. '.repeat(150);
                }
                if (phase >= sizes.length * 2) {
                    console.log('PASS: compact and fullscreen layouts fit six resolutions without moving the bookmark');
                    Qt.quit(); return;
                }
                const size = sizes[Math.floor(phase / 2)];
                if (hold === 0) {
                    window.width = size[0]; window.height = size[1];
                    menu.fullscreen = phase % 2 === 1;
                    menu.fitPage(); hold++; return;
                }
                const state = JSON.parse(menu.status());
                const layout = find(menu, 'typing-responsive-layout');
                if (layout.width > window.width || layout.height + layout.y > window.height + 1) throw Error('Layout exceeds viewport at ' + size);
                if (state.position !== 0) throw Error('Resize moved bookmark');
                if (state.passageHeight <= 0 || state.passageHeight > window.height) throw Error('Invalid passage height at ' + size);
                if (menu.readingFont.pixelSize < 16 || menu.readingFont.pixelSize > 30) throw Error('Invalid font scale');
                phase++; hold = 0;
            } catch (error) { console.error('FAIL:', error); Qt.exit(1); }
        }
    }
}
