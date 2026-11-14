import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import unittest

SCRIPTS = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts'
spec = importlib.util.spec_from_file_location('lyrics_bridge', SCRIPTS / 'lyrics_plus_bridge.py')
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class Bridge(unittest.TestCase):
    def test_validate_and_strip_unexpected_fields(self):
        row = bridge.normalize({'uri': 'spotify:track:' + '1' * 22, 'synced': True,
                                'provider': 'Spotify', 'accessToken': 'must not be forwarded',
                                'lines': [{'time': 2, 'text': 'second'}, {'time': 1, 'text': 'first'}]})
        self.assertEqual(row['lines'][0]['time'], 1)
        self.assertNotIn('accessToken', row)
        self.assertEqual(row['provider'], 'Lyrics Plus · Spotify')
        for data in ({}, {'uri': 'spotify:track:' + '1' * 22, 'lines': [{'text': 'bad', 'time': float('nan')}], 'synced': True}):
            with self.assertRaises(ValueError): bridge.normalize(data)

    def test_http_origin_and_json_contract(self):
        import threading
        from urllib.request import Request, urlopen
        from urllib.error import HTTPError
        server = bridge.HTTPServer(('127.0.0.1', 0), bridge.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        url = 'http://127.0.0.1:%s/lyrics' % server.server_port
        data = json.dumps({'uri': 'spotify:track:' + '1' * 22, 'lines': [{'text': 'test'}]}).encode()
        try:
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(url, data=data, headers={'Origin': 'https://example.com'}))
            self.assertEqual(error.exception.code, 403)
            with contextlib.redirect_stdout(io.StringIO()) as output:
                with urlopen(Request(url, data=data, headers={'Origin': bridge.ORIGIN})) as result:
                    self.assertEqual(result.status, 204)
            self.assertEqual(json.loads(output.getvalue())['lines'], [{'text': 'test'}])
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_adapter_timestamp_conversion_and_plain_fallback(self):
        source = (SCRIPTS / 'lyrics_plus_extension.js').read_text()
        script = '''const vm = require('vm'); const assert = require('assert');
const context = vm.createContext({setTimeout: () => {}});
vm.runInContext(SOURCE, context);
const timed = vm.runInContext("payload({uri:'track'}, {provider:'Spotify',synced:[{startTime:'1250',text:'Test'}]})", context);
assert.equal(timed.lines[0].time, 1.25); assert.equal(timed.synced, true);
const plain = vm.runInContext("payload({uri:'track'}, {provider:'Spotify',unsynced:[{text:'Test'}]})", context);
assert.equal(plain.synced, false); assert.equal(plain.lines[0].text, 'Test');
'''.replace('SOURCE', json.dumps(source))
        subprocess.run(['node', '-e', script], check=True, capture_output=True, text=True)
