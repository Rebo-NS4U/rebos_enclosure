#!/usr/bin/env python3
"""Exercise registry close targeting and failures without stopping desktop apps."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[2] / 'system/apps/shell'
QS = shutil.which('qs')

with tempfile.TemporaryDirectory(prefix='quickshell-close-test-') as directory:
    root = Path(directory)
    for name in ('modules', 'config'):
        (root/name).symlink_to(SOURCE/name)
    (root/'version').write_text('test')
    (root/'bin').mkdir()
    (root/'runtime').mkdir(mode=0o700)
    mock = root/'bin/qs'
    mock.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
state = Path(os.environ['QS_TEST_STATE'])
if sys.argv[1:] == ['list', '--all', '--json']:
    print('[]' if state.exists() else json.dumps([{'id':'fixture-instance', 'pid':12345, 'shell_id':'fixture', 'config_path':'/fixture.qml'}]))
elif sys.argv[1:] == ['kill', '--id', 'fixture-instance']:
    state.write_text('closed fixture-instance')
elif sys.argv[1:] == ['kill', '--id', 'failure-instance']:
    sys.exit(1)
else:
    sys.exit(2)
''')
    mock.chmod(0o755)
    (root/'shell.qml').write_text('''import QtQuick
import Quickshell
import qs.modules.bar.island
ShellRoot {
    RunningQuickshellApps { id: apps; width: 420 }
    Timer {
        property int phase: 0
        property int attempts: 0
        interval: 100; running: true; repeat: true
        onTriggered: {
            if (++attempts > 60) { console.error("CLOSE_TEST_TIMEOUT", apps.status, apps.actionMessage); Qt.exit(1); }
            if (phase === 0 && apps.instances.length === 1) {
                apps.closeApp(apps.instances[0]); phase = 1;
            } else if (phase === 1 && apps.instances.length === 0 && apps.actionMessage === "Close requested.") {
                apps.closeApp({id:"failure-instance"}); phase = 2;
            } else if (phase === 2 && apps.actionMessage.indexOf("Could not close") === 0 && apps.closingId === "") {
                console.log("CLOSE_TEST_OK"); Qt.quit();
            }
        }
    }
}
''')
    env = {**os.environ, 'HOME':str(root), 'XDG_CONFIG_HOME':str(root/'user-config'),
           'XDG_CACHE_HOME':str(root/'cache'), 'XDG_DATA_HOME':str(root/'data'),
           'XDG_RUNTIME_DIR':str(root/'runtime'), 'QT_QPA_PLATFORM':'offscreen',
           'PATH':str(root/'bin')+os.pathsep+os.environ['PATH'], 'QS_TEST_STATE':str(root/'closed')}
    result = subprocess.run([QS, '-p', str(root)], env=env, capture_output=True, text=True, timeout=15)
    log = result.stdout + result.stderr
    assert result.returncode == 0 and 'CLOSE_TEST_OK' in log, log
    assert (root/'closed').read_text() == 'closed fixture-instance'
    assert not any(message in log for message in ('TypeError:', 'ReferenceError:', 'Binding loop')), log
    print('PASS: specific-instance close, list refresh, and close failure feedback')
