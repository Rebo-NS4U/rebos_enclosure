"""Daily Mix version replacement, immutable snapshots and input validation."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('music_mixes', ROOT/'system/apps/shell/scripts/music_mixes.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class MixTests(unittest.TestCase):
    def test_playlist_write_validation_result_and_timeout(self):
        store = module.Mixes(Path('/unused'), lambda *a: a[1], lambda *a: None)
        uri = 'spotify:playlist:' + 'a'*22
        with self.assertRaises(ValueError):
            store.replace_playlist(uri, ['file:///song'])
        tracks = ['spotify:track:' + 'b'*22, 'spotify:track:' + 'c'*22]
        self.assertTrue(store.replace_playlist(uri, tracks)['pending'])
        self.assertEqual(store.playlist_write['tracks'], tracks)
        with self.assertRaises(ValueError):
            store.replace_playlist(uri, [])
        store.update(dict(playlist_write_id='stale', error='failed'))
        self.assertTrue(store.playlist_write_status()['pending'])
        store.update(dict(playlist_write_id=store.playlist_write['id']))
        self.assertFalse(store.playlist_write_status()['pending'])
        store.replace_playlist(uri, [])
        store.update(dict(playlist_write_id=store.playlist_write['id'], error='No edit permission'))
        self.assertEqual(store.playlist_write_status()['status'], 'No edit permission')
        store.replace_playlist(uri, tracks)
        store.playlist_write['started'] -= 121
        self.assertFalse(store.playlist_write_status()['pending'])
        self.assertIn('could not be confirmed', store.playlist_write_status()['status'])

    def test_load_any_playlist_and_report_access_failure(self):
        store = module.Mixes(Path('/unused'), lambda *a: a[1], lambda *a: None)
        uri = 'spotify:playlist:' + 'c'*22
        result = store.dispatch('mixes_load', {'link': 'https://open.spotify.com/playlist/' + 'c'*22 + '?si=shared'})
        self.assertTrue(result['refreshPending'])
        self.assertEqual(store.refresh_uri, uri)
        with self.assertRaises(ValueError):
            store.dispatch('mixes_refresh', {})
        mix = dict(uri=uri, name='My favorites / 2026', tracks=[dict(uri='spotify:track:'+'b'*22, title='One')])
        store.update(dict(mixes=[mix], refresh_id=store.refresh_id))
        current = store.dispatch('mixes_get', {})['current'][0]
        self.assertEqual(current['name'], mix['name'])
        store.dispatch('mixes_save', dict(uri=uri, version=current['version']))
        self.assertEqual(len(store.data['saved']), 1)
        store.dispatch('mixes_load', {'link': uri})
        store.update(dict(mixes=[], refresh_id=store.refresh_id, error='Playlist unavailable'))
        self.assertEqual(store.dispatch('mixes_get', {})['refreshStatus'], 'Playlist unavailable')
        self.assertEqual(len(store.data['current']), 1)

    def test_playlist_links_are_validated(self):
        uri = 'spotify:playlist:' + 'a'*22
        self.assertEqual(module.playlist_uri(uri), uri)
        self.assertEqual(module.playlist_uri('https://open.spotify.com/intl-en/playlist/'+'a'*22), uri)
        for link in ('https://evil.test/playlist/'+'a'*22, 'file:///etc/passwd',
                     'https://open.spotify.com/track/'+'a'*22, 'spotify:playlist:$(bad)', ''):
            with self.assertRaises(ValueError):
                module.playlist_uri(link)

    def test_refresh_and_save(self):
        with tempfile.TemporaryDirectory() as directory:
            writes = []
            store = module.Mixes(Path(directory)/'mixes.json', lambda *a: a[1], lambda p, data: writes.append(copy.deepcopy(data)))
            mix = dict(uri='spotify:playlist:'+'a'*22, name='Daily Mix 1', tracks=[dict(uri='spotify:track:'+'b'*22, title='One')])
            store.update(dict(mixes=[mix]))
            current = store.dispatch('mixes_get', {})['current'][0]
            store.dispatch('mixes_save', dict(uri=mix['uri'], version=current['version']))
            store.dispatch('mixes_save', dict(uri=mix['uri'], version=current['version']))
            mix['tracks'][0]['title'] = 'Two'
            store.update(dict(mixes=[mix]))
            result = store.dispatch('mixes_get', {})
            self.assertEqual(len(result['saved']), 1)
            self.assertEqual(result['saved'][0]['tracks'][0]['title'], 'One')
            self.assertEqual(result['current'][0]['tracks'][0]['title'], 'Two')
            with self.assertRaises(ValueError):
                store.dispatch('mixes_save', dict(uri=mix['uri'], version=current['version']))
            store.update(dict(mixes=[]))
            self.assertEqual(len(store.dispatch('mixes_get', {})['current']), 1)
            result['saved'].clear()
            self.assertEqual(len(store.dispatch('mixes_get', {})['saved']), 1)
            self.assertTrue(writes)

    def test_manual_refresh_completion_and_timeout(self):
        store = module.Mixes(Path('/unused'), lambda *a: a[1], lambda *a: None)
        self.assertTrue(store.dispatch('mixes_refresh', {})['refreshPending'])
        request_id = store.refresh_id
        # Heartbeats from the previous collection must not complete this request.
        store.update(dict(mixes=[]))
        self.assertTrue(store.dispatch('mixes_get', {})['refreshPending'])
        store.update(dict(mixes=[], refresh_id=request_id))
        result = store.dispatch('mixes_get', {})
        self.assertFalse(result['refreshPending'])
        self.assertIn('No mixes received', result['refreshStatus'])
        store.dispatch('mixes_refresh', {})
        with patch.object(module.time, 'monotonic', return_value=store.refresh_started + 91):
            result = store.dispatch('mixes_get', {})
        self.assertFalse(result['refreshPending'])
        self.assertIn('did not respond', result['refreshStatus'])

    def test_reject_incomplete_or_untrusted_metadata(self):
        for value in [{}, {'mixes': [{}]}, {'mixes': [dict(uri='spotify:playlist:'+'a'*22, name='Daily Mix 1', tracks=[])]}]:
            with self.assertRaises(ValueError): module.normalize(value)

if __name__ == '__main__': unittest.main()
