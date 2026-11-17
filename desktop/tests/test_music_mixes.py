"""Daily Mix version replacement, immutable snapshots and input validation."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('music_mixes', ROOT/'system/apps/shell/scripts/music_mixes.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class MixTests(unittest.TestCase):
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

    def test_reject_incomplete_or_untrusted_metadata(self):
        for value in [{}, {'mixes': [{}]}, {'mixes': [dict(uri='spotify:playlist:'+'a'*22, name='Daily Mix 1', tracks=[])]}]:
            with self.assertRaises(ValueError): module.normalize(value)

if __name__ == '__main__': unittest.main()
