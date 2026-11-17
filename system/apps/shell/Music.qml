//@ pragma UseQApplication
//@ pragma ShellId enclosure-music
import QtQuick
import Quickshell
import Quickshell.Io
import qs.modules.widgets.music
import qs.modules.globals

ShellRoot {
    MusicWindow { id: music }
    Component.onCompleted: GlobalStates.musicWindowVisible = true
    IpcHandler {
        target: "music"
        function open(): void { GlobalStates.musicWindowVisible = true; music.requestActivate(); }
        function showDownloadedMixes(): void { music.navigate("Downloaded Mixes"); GlobalStates.musicWindowVisible = true; music.requestActivate(); }
        function hide(): void { GlobalStates.musicWindowVisible = false; }
        function status(): string {
            return JSON.stringify({visible: music.visible, busy: music.busy, tracks: music.tracks.length,
                page: music.page, downloadedMixes: music.downloadedMixes.map(p => p.name),
                playing: music.playing, title: music.current?.title || "", error: music.notice});
        }
    }
}
