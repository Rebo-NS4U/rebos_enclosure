#!/usr/bin/env python3
"""Run screenshot acceptance in a private software-rendered Niri/Xvfb session."""
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def isolated_environment(root):
    env = dict(os.environ, HOME=str(root), XDG_RUNTIME_DIR=str(root / 'runtime'),
               LIBGL_ALWAYS_SOFTWARE='1', GALLIUM_DRIVER='llvmpipe',
               PYTHONDONTWRITEBYTECODE='1', ENCLOSURE_SCREENSHOT_UI_TEST='1',
               QS_DISABLE_FILE_WATCHER='1', QSG_RHI_BACKEND='opengl', QT_OPENGL='software')
    for key in ('WAYLAND_DISPLAY', 'NIRI_SOCKET', 'DISPLAY', 'DBUS_SESSION_BUS_ADDRESS',
                'DBUS_STARTER_ADDRESS', 'QT_QPA_PLATFORM', 'QT_QPA_PLATFORMTHEME', 'QT_QUICK_BACKEND'):
        env.pop(key, None)
    for key, directory in (('XDG_CONFIG_HOME', 'config'), ('XDG_CACHE_HOME', 'cache'),
                           ('XDG_DATA_HOME', 'data'), ('XDG_STATE_HOME', 'state')):
        env[key] = str(root / directory)
    return env


def wait_for_niri(process, root, env):
    for _ in range(150):
        sockets = list((root / 'runtime').glob('niri.*.sock'))
        displays = [path for path in (root / 'runtime').glob('wayland-*') if path.is_socket()]
        if sockets and displays:
            env.update(NIRI_SOCKET=str(sockets[0]), WAYLAND_DISPLAY=displays[0].name)
            return
        if process.poll() is not None:
            break
        time.sleep(.1)
    raise RuntimeError('Isolated Niri did not become ready')


def run_session(root, env):
    (root / 'config.kdl').write_text('hotkey-overlay { skip-at-startup; }\n')
    with (root / 'niri.log').open('w') as log:
        process = subprocess.Popen(['niri', '-c', str(root / 'config.kdl')], env=env,
                                   stdout=log, stderr=subprocess.STDOUT)
        try:
            wait_for_niri(process, root, env)
            # Never use --session: that would replace the real session's bus environment.
            result = subprocess.run([sys.executable, '-m', 'unittest', 'discover',
                                     '-s', 'desktop/tests', '-p', 'test_screenshot_editor.py', '-v'],
                                    cwd=ROOT, env=env, timeout=60, check=False)
            if result.returncode:
                raise RuntimeError('Wayland screenshot acceptance failed')
        finally:
            stop(process)


def run(root):
    (root / 'runtime').mkdir(mode=0o700)
    env = isolated_environment(root)
    with (root / 'xvfb.log').open('w') as log:
        process = subprocess.Popen(['Xvfb', '-displayfd', '1', '-screen', '0',
                                    '1600x1000x24', '-nolisten', 'tcp'], env=env,
                                   stdout=subprocess.PIPE, stderr=log, text=True)
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                if not selector.select(timeout=15):
                    raise RuntimeError('Xvfb did not provide a display')
            display = process.stdout.readline().strip()
            if not display.isdigit():
                raise RuntimeError('Xvfb did not start')
            env['DISPLAY'] = ':' + display
            run_session(root, env)
        finally:
            process.stdout.close()
            stop(process)


def main():
    missing = [name for name in ('Xvfb', 'niri', 'qs') if not shutil.which(name)]
    if missing:
        print('Missing Wayland test dependencies: ' + ', '.join(missing), file=sys.stderr)
        return 1
    with tempfile.TemporaryDirectory(prefix='enclosure-wayland-') as directory:
        root = Path(directory)
        try:
            run(root)
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            print(error, file=sys.stderr)
            for name in ('xvfb.log', 'niri.log'):
                if (root / name).exists():
                    print((root / name).read_text()[-4000:], file=sys.stderr)
            return 1
    print('Isolated Wayland screenshot acceptance passed; real desktop was not used.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
