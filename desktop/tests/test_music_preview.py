"""Previewing sends only an OpenUri request; it never invokes downloads."""
from pathlib import Path
import subprocess
import sys
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'system/apps/shell/scripts'))
import music_preview


class MusicPreviewTests(unittest.TestCase):
    def test_preview_uses_spotify_uri_without_file_writes_or_downloads(self):
        uri = 'spotify:track:' + 'a'*22
        with patch.object(music_preview.subprocess, 'run') as run:
            result = music_preview.preview(uri)
        self.assertEqual(result['uri'], uri)
        args = run.call_args.args[0]
        self.assertEqual(args[-1], uri)
        self.assertIn('org.mpris.MediaPlayer2.Player.OpenUri', args)
        self.assertIn('org.mpris.MediaPlayer2.spotify', args)
        self.assertNotIn('spotdl', args)
        self.assertNotIn('yt-dlp', args)

    def test_invalid_uris_never_start_processes(self):
        for uri in (None, '', 'https://example.com/track', 'spotify:playlist:'+'a'*22, 'spotify:track:$(unsafe)'):
            with patch.object(music_preview.subprocess, 'run') as run:
                with self.assertRaises(ValueError):
                    music_preview.preview(uri)
                run.assert_not_called()

    def test_missing_player_denied_and_timeout_are_actionable(self):
        for error in (FileNotFoundError(), subprocess.CalledProcessError(1, ['gdbus']), subprocess.TimeoutExpired('gdbus', 8)):
            with patch.object(music_preview.subprocess, 'run', side_effect=error):
                with self.assertRaisesRegex(ValueError, 'Open Spotify.*No music was downloaded'):
                    music_preview.preview('spotify:track:'+'b'*22)

    def test_library_dispatch_keeps_preview_separate(self):
        import music_library
        library = object.__new__(music_library.Library)
        with patch.object(music_preview, 'preview', return_value={'uri':'fixture'}) as preview:
            self.assertEqual(library.dispatch('mixes_preview', {'uri':'fixture'}), {'uri':'fixture'})
            preview.assert_called_once_with('fixture')

    @unittest.skipUnless(shutil.which('qs'), 'Quickshell required')
    def test_undownloaded_qml_row_requests_preview_not_download(self):
        harness = r'''import QtQuick
import Quickshell
import QtTest
import qs.modules.widgets.music
ShellRoot {
 FloatingWindow { visible:true; implicitWidth:700; implicitHeight:800
  DailyMixesPane { id:pane; anchors.fill:parent
   property string streamed:""
   property int downloads:0
   property bool localPlayed:false
   onPreviewRequested: uri => streamed=uri
   onDownloadRequested: downloads++
   onPlayRequested: (list,index) => localPlayed=list.length===1 && index===0
  }
  TestCase { id:t; when:false }
  Timer { interval:400;running:true;onTriggered: {
   try {
    const uri="spotify:track:"+"a".repeat(22);
    const localUri="spotify:track:"+"b".repeat(22);
    pane.localTracks=[{path:"/fixture/local.flac",spotifyUri:localUri}];
    pane.selected={name:"Daily Mix 1",tracks:[{uri:uri,title:"Online song",artist:"Artist"},{uri:localUri,title:"Local song",artist:"Artist"}]};
    t.wait(100);
    const row=t.findChild(pane,"music-mix-track-0");
    t.verify(row!==null && row.enabled);
    row.clicked(); t.compare(pane.streamed,uri); t.compare(pane.downloads,0);
    t.findChild(pane,"music-mix-track-1").clicked(); t.verify(pane.localPlayed);
    t.findChild(pane,"music-mix-stream-preview").clicked(); t.compare(pane.streamed,uri);
    t.compare(pane.downloads,0); console.log("STREAM_PREVIEW_PASSED"); Qt.quit();
   } catch(e) {console.error(e,e.stack);Qt.exit(1);}
  } }
 }
}'''
        with tempfile.TemporaryDirectory(prefix='enclosure-music-preview-') as folder:
            root=Path(folder)
            app=ROOT/'system/apps/shell'
            for name in ('modules','config','assets'):
                (root/name).symlink_to(app/name)
            (root/'shell.qml').write_text(harness)
            (root/'runtime').mkdir(mode=0o700)
            env=dict(os.environ,HOME=folder,XDG_RUNTIME_DIR=str(root/'runtime'),QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',QT_QPA_PLATFORMTHEME='basic')
            for key in ('DISPLAY','WAYLAND_DISPLAY','DBUS_SESSION_BUS_ADDRESS'):
                env.pop(key,None)
            for key in ('XDG_CONFIG_HOME','XDG_CACHE_HOME','XDG_STATE_HOME','XDG_DATA_HOME'):
                env[key]=str(root/key)
            result=subprocess.run(['qs','-p',folder,'--no-color'],env=env,capture_output=True,text=True,timeout=15)
            output=result.stdout+result.stderr
            self.assertEqual(result.returncode,0,output)
            self.assertIn('STREAM_PREVIEW_PASSED',output)


if __name__ == '__main__':
    unittest.main()
