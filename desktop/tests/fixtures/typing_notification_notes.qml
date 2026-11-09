import QtQuick
import Quickshell
import qs.modules.bar.layouts
import qs.modules.services
ShellRoot {
    PanelWindow {
        id: panel
        implicitWidth: 1280; implicitHeight: 1000
        IslandBar { id: bar; screen: panel.screen }
    }
    Timer {
        interval: 400; repeat: true; running: true
        property int phase: 0
        onTriggered: {
            try {
                const reader = bar.typingPractice;
                if (phase === 0) { bar.expand('typing'); reader.send({action: 'add', title: 'Notification test', text: 'A book for testing notes and notifications. '.repeat(50)}); phase++; return; }
                if (phase === 1) { if (reader.busy || !reader.bookId) return; reader.pinRequested(); phase++; return; }
                if (phase === 2) { reader.openNotebook(); phase++; return; }
                if (phase === 3) {
                    if (!JSON.parse(reader.status()).wordToolsOpen) throw Error('Notes did not open');
                    bar.expand('notification'); phase++; return;
                }
                if (phase === 4) {
                    if (!JSON.parse(reader.status()).wordToolsOpen || !FocusGrabManager.hasActiveGrab) throw Error('Notification dismissed notes');
                    bar.collapse(); phase++; return;
                }
                if (phase === 5) {
                    if (!JSON.parse(reader.status()).wordToolsOpen || !FocusGrabManager.hasActiveGrab) throw Error('Notification dismissal closed notes');
                    FocusGrabManager.clearTopGrab(); phase++; return;
                }
                if (phase === 6) {
                    if (JSON.parse(reader.status()).wordToolsOpen) throw Error('Explicit dismissal stopped working');
                    reader.openNotebook(); phase++; return;
                }
                if (phase === 7) { bar.expand('dashboard'); phase++; return; }
                if (JSON.parse(reader.status()).wordToolsOpen) throw Error('Panel switch did not dismiss notes');
                console.log('PASS: pinned notes survive notification arrival and dismissal; outside clicks and panel switches still dismiss');
                Qt.quit();
            } catch (error) { console.error('FAIL:', error); Qt.exit(1); }
        }
    }
}
