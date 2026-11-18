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
        function open(): void { music.navigate("Playlists"); GlobalStates.musicWindowVisible = true; music.requestActivate(); }
        function showDownloadedMixes(): void { music.navigate("Playlists"); GlobalStates.musicWindowVisible = true; music.requestActivate(); }
        function showPlaylist(id: string): void {
            if (music.playlists.some(p => p.id === id)) music.navigate("Playlist", id);
        }
        function refreshSuggestions(): void { music.refreshSuggestions(); }
        function hide(): void { GlobalStates.musicWindowVisible = false; }
        function status(): string {
            return JSON.stringify({visible: music.visible, busy: music.busy, tracks: music.tracks.length,
                page: music.page, playlists: music.playlists.length, detail: music.detail,
                suggestions: {pending: music.spotifySuggestions.pending, status: music.spotifySuggestions.status,
                    received: (music.spotifySuggestions.tracks || []).length}, suggestedCount: music.suggestedTracks.length,
                playing: music.playing, title: music.current?.title || "", error: music.notice});
        }
    }
}
