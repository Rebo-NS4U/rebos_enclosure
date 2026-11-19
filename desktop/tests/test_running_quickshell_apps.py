#!/usr/bin/env python3
"""Exercise the merged application list and registry close targeting in isolation."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

SOURCE = Path(__file__).resolve().parents[2] / 'system/apps/shell'
QS = shutil.which('qs')

with tempfile.TemporaryDirectory(prefix='quickshell-close-test-') as directory:
    root = Path(directory)
    for name in ('modules', 'config', 'scripts'):
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
import qs.modules.services
import qs.modules.widgets.dashboard.metrics
ShellRoot {
    id: shell
    MetricsTab { id: monitor; width: implicitWidth }
    IslandStatsPanel { id: island; width: implicitWidth; height: implicitHeight }
    function applicationsSection(item) {
        if (typeof item.applicationRows === "function") return item;
        for (const child of item.children) {
            const section = applicationsSection(child);
            if (section) return section;
        }
        return null;
    }
    readonly property var apps: applicationsSection(monitor)
    readonly property var islandApps: applicationsSection(island)
    Component.onCompleted: NiriService.rawWindows = [
        { id: 1, pid: 12345, app_id: "fixture-shell", title: "Duplicate window" },
        { id: 2, pid: 23456, app_id: "fixture-editor", title: "First document" },
        { id: 3, pid: 23457, app_id: "fixture-editor", title: "Second document", is_focused: true }
    ]
    Timer {
        readonly property var apps: shell.apps
        property int phase: 0
        property int attempts: 0
        interval: 100; running: true; repeat: true
        onTriggered: {
            if (++attempts > 60) { console.error("CLOSE_TEST_TIMEOUT", apps.status, apps.actionMessage); Qt.exit(1); }
            if (phase === 0 && shell.apps.instances.length === 1 && shell.islandApps.instances.length === 1) {
                const rows = apps.applications;
                if (rows.length !== 2 || shell.islandApps.applications.length !== 2
                    || rows[0].instance?.id !== "fixture-instance"
                    || rows[1].windowId !== 3 || rows[1].detail !== "2 windows") {
                    console.error("APPLICATION_TEST_FAILED", JSON.stringify(rows));
                    Qt.exit(1);
                    return;
                }
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
           'NIRI_SOCKET':str(root/'niri.sock'),
           'PATH':str(root/'bin')+os.pathsep+os.environ['PATH'], 'QS_TEST_STATE':str(root/'closed')}
    result = subprocess.run([QS, '-p', str(root)], env=env, capture_output=True, text=True, timeout=15)
    log = result.stdout + result.stderr
    assert result.returncode == 0 and 'CLOSE_TEST_OK' in log, log
    assert (root/'closed').read_text() == 'closed fixture-instance'
    assert not any(message in log for message in ('TypeError:', 'ReferenceError:', 'Binding loop')), log
    print('PASS: merged app rows, window grouping, specific-instance close, refresh, and failure feedback')
