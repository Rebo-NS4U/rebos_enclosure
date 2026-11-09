import QtQuick
import Quickshell
import qs.modules.bar.island
ShellRoot {
    PanelWindow {
        implicitWidth: 640; implicitHeight: 600
        TypingMenu { id: menu; anchors.fill: parent }
        IslandMediaCenterPanel { id: media; width: 420; reader: menu; visible: !menu.visible }
    }
    Timer {
        interval: 100; running: true; repeat: true
        property int phase: 0
        property int ticks: 0
        property int hold: 0
        property int initialPosition: 0
        onTriggered: {
            try {
                if (++ticks > 250) throw Error("Media lifecycle timed out at " + phase);
                if (phase === 0) {
                    menu.readingMode = true;
                    menu.send({action: "add", title: "Background reading", text: "The story continues with the reader closed. ".repeat(200)});
                    phase++; return;
                }
                if (phase === 1) {
                    if (menu.busy || !menu.bookId || ++hold < 6) return;
                    menu.toggleSpeech();
                    initialPosition = menu.position;
                    menu.visible = false;
                    if (!menu.speaking || !media.readerActive) throw Error("Hiding reader stopped speech or removed media card");
                    phase++; return;
                }
                if (phase === 2) {
                    if (menu.position === initialPosition || menu.speechAdvancing || menu.busy) return;
                    if (!menu.speaking || !media.readerActive) throw Error("Hidden reader failed to continue to next page");
                    menu.toggleSpeechPlayback();
                    if (!menu.speechPaused) throw Error("Media pause failed");
                    menu.toggleSpeechPlayback();
                    if (menu.speechPaused) throw Error("Media resume failed");
                    menu.stopSpeech(); hold = 0; phase++; return;
                }
                if (phase === 3) {
                    if (++hold < 5) return;
                    if (media.readerActive) throw Error("Stopped reader remained in media");
                    menu.visible = true; menu.visible = false;
                    if (media.readerActive) throw Error("Silent reader appeared in media after exit");
                    console.log("PASS: hidden reader continues playback, media pause/resume and silent dismissal");
                    Qt.quit();
                }
            } catch (error) { console.error(error); Qt.exit(1); }
        }
    }
}
