#!/usr/bin/env python3
"""Launch Google's native Gemini ACP agent with private, local credentials."""
import getpass
import os
from pathlib import Path
import sys

GEMINI_PACKAGE = '@google/gemini-cli@0.66.0'
GOOGLE_MODEL = 'gemini-3.5-flash-lite'
KEY_NAMES = ('GEMINI_API_KEY', 'GOOGLE_API_KEY', 'GOOGLE_AI_API_KEY')


def launch_environment(environment=None):
    env = dict(os.environ if environment is None else environment)
    config = Path(env.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    path = config / 'dweebo/google-api-key'
    key = ''
    # A replacement saved through Dweebo takes precedence over stale service env.
    if path.is_file():
        if path.stat().st_mode & 0o077:
            raise ValueError('Set permissions to 600 on ' + str(path))
        key = path.read_text().strip()
    if not key:
        key = next((env[name].strip() for name in KEY_NAMES if env.get(name, '').strip()), '')
    if not key:
        raise ValueError('Save your Google API key in ~/.config/dweebo/google-api-key (permissions 600), or export GEMINI_API_KEY to the launching service.')
    env['GEMINI_API_KEY'] = key
    # Keep Dweebo authentication separate from an existing Gemini CLI login.
    data = Path(env.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
    env['GEMINI_CLI_HOME'] = str(data / 'dweebo/google')
    env['GEMINI_TELEMETRY_ENABLED'] = 'false'
    env['GEMINI_CLI_SYSTEM_SETTINGS_PATH'] = str(Path(__file__).with_name('google_settings.json'))
    return env


def command():
    return ['npx', '-y', GEMINI_PACKAGE, '--acp', '--model', GOOGLE_MODEL, '--approval-mode', 'default']


def save_key(environment=None, prompt=getpass.getpass):
    env = os.environ if environment is None else environment
    key = next((env[name].strip() for name in KEY_NAMES if env.get(name, '').strip()), '')
    if not key:
        key = prompt('Google API key (hidden): ').strip()
    if not key:
        raise ValueError('No key provided; the saved key was not changed.')
    config = Path(env.get('XDG_CONFIG_HOME', str(Path.home() / '.config')))
    path = (config / 'dweebo/google-api-key').resolve()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, 'w') as output:
        os.fchmod(output.fileno(), 0o600)
        output.write(key + '\n')
    return path


def main():
    try:
        if sys.argv[1:] == ['--save-key']:
            save_key()
            print('Google key saved privately. Choose Backend → Google Gemini in Dweebo.')
            return 0
        if sys.argv[1:]:
            raise ValueError('Usage: google_agent.py [--save-key]')
        env = launch_environment()
    except (OSError, ValueError) as error:
        print('Dweebo Google: ' + str(error), file=sys.stderr)
        return 1
    args = command()
    os.execvpe(args[0], args, env)


if __name__ == '__main__':
    raise SystemExit(main())
