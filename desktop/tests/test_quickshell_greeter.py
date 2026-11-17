"""Exercise the real Quickshell greetd client against a local protocol server."""
import json
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / 'system/etc/rebos-greeter/quickshell/core'


class AuthenticationTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('quickshell'), 'requires Quickshell')
    def test_failure_retry_and_additional_prompt(self):
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory)
            runtime = tmp / 'runtime'
            runtime.mkdir(mode=0o700)
            entry = tmp / 'shell.qml'
            entry.write_text('''import QtQuick
import Quickshell
import QsGreet
ShellRoot {
    Component.onCompleted: Auth.login("example", "first")
    Timer { id: retry; interval: 100; onTriggered: Auth.login("example", "second") }
    Connections {
        target: Auth
        function onFailed(message) { retry.start(); }
        function onPromptRequested(message, echo) { Auth.submitSecret("factor"); }
    }
}''')
            server = socket.socket(socket.AF_UNIX)
            server.bind(str(tmp / 'greetd.sock'))
            server.listen(1)
            server.settimeout(10)
            env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen',
                   'XDG_RUNTIME_DIR': str(runtime), 'QML_IMPORT_PATH': str(CORE),
                   'GREETD_SOCK': str(tmp / 'greetd.sock'),
                   'QSGREET_DEFAULT_COMMAND': '["niri-session"]'}
            process = subprocess.Popen(['quickshell', '-p', str(entry)], env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            try:
                try:
                    connection, _ = server.accept()
                except TimeoutError:
                    process.terminate()
                    output, _ = process.communicate(timeout=5)
                    self.fail(output)
                connection.settimeout(10)
                def receive():
                    def exact(length):
                        data = b''
                        while len(data) < length:
                            chunk = connection.recv(length - len(data))
                            if not chunk:
                                raise AssertionError('greeter disconnected')
                            data += chunk
                        return data
                    return json.loads(exact(struct.unpack('<I', exact(4))[0]))
                def send(message):
                    data = json.dumps(message).encode()
                    connection.sendall(struct.pack('<I', len(data)) + data)
                with connection:
                    self.assertEqual(receive(), {'type': 'create_session', 'username': 'example'})
                    send({'type': 'auth_message', 'auth_message_type': 'secret', 'auth_message': 'Password:'})
                    self.assertEqual(receive()['response'], 'first')
                    send({'type': 'error', 'error_type': 'auth_error', 'description': 'Try again'})
                    # Quickshell cancels failed sessions before signalling failure.
                    request = receive()
                    if request['type'] == 'cancel_session':
                        send({'type': 'success'})
                        request = receive()
                    self.assertEqual(request['type'], 'create_session')
                    send({'type': 'auth_message', 'auth_message_type': 'secret', 'auth_message': 'Password:'})
                    self.assertEqual(receive(), {'type': 'post_auth_message_response', 'response': 'second'})
                    send({'type': 'auth_message', 'auth_message_type': 'secret', 'auth_message': 'Second factor:'})
                    self.assertEqual(receive()['response'], 'factor')
                    send({'type': 'success'})
                    request = receive()
                    self.assertEqual(request['type'], 'start_session')
                    self.assertEqual(request['cmd'], ['niri-session'])
                    send({'type': 'success'})
                process.wait(timeout=10)
                self.assertEqual(process.returncode, 0, process.stdout.read())
            finally:
                server.close()
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=5)
                process.stdout.close()


if __name__ == '__main__':
    unittest.main()
