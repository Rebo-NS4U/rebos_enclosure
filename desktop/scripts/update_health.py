"""Validate update code in isolation before replacing the running desktop."""
import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
from layout import source as source_path, manifest

ASSISTANT_HARNESS = '''import QtQuick
import Quickshell
import qs.modules.sidebar
import qs.modules.globals
import qs.modules.services
import qs.modules.components
import qs.modules.theme
import qs.config
ShellRoot {
    Timer {
        interval: 10
        running: true
        onTriggered: {
            let sidebar = Qt.createComponent("modules/sidebar/AssistantSidebar.qml");
            if (sidebar.status !== Component.Ready) {
                console.error(sidebar.errorString());
                Qt.exit(1);
            } else {
                console.log("ASSISTANT COMPONENT READY");
                Qt.quit();
            }
        }
    }
}
'''


PANEL_HARNESS = """import QtQuick
import Quickshell
import qs.modules.widgets.config
import qs.modules.bar
ShellRoot {
    Timer {
        interval: 10
        running: true
        onTriggered: {
            for (let path of ["modules/widgets/config/SettingsWindow.qml",
                              "modules/bar/BatteryIndicator.qml"]) {
                let component = Qt.createComponent(path);
                if (component.status !== Component.Ready) {
                    console.error(component.errorString());
                    Qt.exit(1);
                    return;
                }
            }
            console.log("PANEL COMPONENT READY");
            Qt.quit();
        }
    }
}
"""


def validate(payload):
    """Do not run shipped scripts, initialize accounts, or contact desktop services."""
    home = payload / 'home'
    roots = [payload.parents[1] / name for name in ('config', 'system')] if manifest(payload).get('layout') == 2 else [home]
    for source in (p for base in roots for p in base.rglob('*.py')):
        compile(source.read_bytes(), str(source), 'exec')
    for source in (p for base in roots for p in base.rglob('*')):
        if not source.is_file():
            continue
        if source.suffix == '.sh' or source.read_bytes().startswith(b'#!/usr/bin/env bash'):
            result = subprocess.run(['bash', '-n', str(source)], capture_output=True, text=True, timeout=20)
            if result.returncode:
                raise ValueError(f'Invalid shell script {source}: {result.stderr}')
    app = source_path(payload, 'code/rebos-assistant')
    if (app / 'shell.qml').exists():
        validate_assistant(app)
    panel = source_path(payload, '.config/quickshell')
    if (panel / 'modules/widgets/config/SettingsWindow.qml').exists():
        validate_qml(panel, PANEL_HARNESS, 'Desktop panel')


def validate_assistant(app):
    session = app / 'modules/services/AiSession.qml'
    if session.is_file():
        for name in set(re.findall(r'scripts/([A-Za-z0-9_]+\.py)', session.read_text())):
            if not (app / 'scripts' / name).is_file():
                raise ValueError(f'Assistant launcher references missing script: {name}')
    if not shutil.which('qs'):
        raise ValueError('Quickshell (qs) is required to validate the assistant before updating')
    for script, dependency in [('google_agent.py', 'google_settings.json'),
                               ('openrouter_agent.py', 'openrouter_models.json')]:
        if (app / 'scripts' / script).exists() and not (app / 'scripts' / dependency).is_file():
            raise ValueError(f'Assistant backend {script} requires {dependency}')
    validate_qml(app, ASSISTANT_HARNESS, "Assistant")


def validate_qml(app, harness, label):
    if not shutil.which("qs"):
        raise ValueError("Quickshell (qs) is required to validate desktop updates")
    with tempfile.TemporaryDirectory(prefix='rebos-update-check-') as temporary:
        root = Path(temporary)
        for directory in ('modules', 'config', 'assets'):
            shutil.copytree(app / directory, root / directory)
        (root / 'shell.qml').write_text(harness)
        (root / 'runtime').mkdir(mode=0o700)
        environment = dict(os.environ, HOME=str(root), XDG_RUNTIME_DIR=str(root / 'runtime'),
                           QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                           QT_QPA_PLATFORMTHEME='basic')
        for key, directory in [('XDG_CONFIG_HOME', 'config-home'), ('XDG_CACHE_HOME', 'cache'),
                               ('XDG_DATA_HOME', 'data'), ('XDG_STATE_HOME', 'state')]:
            environment[key] = str(root / directory)
        for key in ('DISPLAY', 'WAYLAND_DISPLAY', 'DBUS_SESSION_BUS_ADDRESS'):
            environment.pop(key, None)
        result = subprocess.run(['qs', '-p', str(root), '--no-color'], env=environment,
                                capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr
        if result.returncode or 'COMPONENT READY' not in output:
            raise ValueError(label + ' update failed QML validation:\n' + output[-6000:])
    print(label + ' QML validated without starting desktop services', flush=True)
