#!/usr/bin/env python3
"""Connect GitHub and configure Git without replacing existing author settings."""
from console_helpers import close_console
import argparse
import json
import re
import subprocess

from github_projects import checkout, git, run


def account():
    try:
        return json.loads(run('gh', 'api', '--hostname', 'github.com', 'user', timeout=30))
    except ValueError as error:
        message = str(error).lower()
        if any(marker in message for marker in (
                'could not resolve', 'error connecting', 'network is unreachable',
                'connection refused', 'timed out', 'tls handshake')):
            raise ValueError('Cannot reach GitHub from this process. Check network access; '
                             'your saved login has not been changed.') from error
        raise


def connect(path, login=False):
    root, _ = checkout(path)
    try:
        user = account()
    except ValueError as error:
        message = str(error).lower()
        needs_login = any(marker in message for marker in (
            'http 401', 'bad credentials', 'gh auth login', 'not logged into'))
        if not login or not needs_login:
            raise
        # Only a verified authentication failure may start interactive login.
        subprocess.run(['gh', 'auth', 'login', '--web', '--hostname', 'github.com',
                        '--git-protocol', 'https'], check=True)
        user = account()
    username = user.get('login', '')
    identity = user.get('id')
    if not re.fullmatch(r'[A-Za-z0-9-]+', username) or type(identity) is not int or identity <= 0:
        raise ValueError('GitHub returned an incomplete account identity.')
    # Configure the standard helper; gh keeps tokens in its own storage/keyring.
    run('gh', 'auth', 'setup-git', '--hostname', 'github.com')
    for key, value in (('user.name', user.get('name') or username),
                       ('user.email', f'{identity}+{username}@users.noreply.github.com')):
        result = subprocess.run(['git', '-C', str(root), 'config', '--get', key],
                                capture_output=True, text=True, check=False)
        if result.returncode not in (0, 1):
            raise ValueError('Could not read Git author settings.')
        if not result.stdout.strip():
            git(root, 'config', '--local', key, value)
    print(f'Connected to GitHub as {username}. Git credentials and commit identity are ready.', flush=True)
    print('Login and Git settings are personal files outside the desktop payload; reinstalling preserves them.')
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', required=True)
    parser.add_argument('--login', action='store_true')
    args = parser.parse_args()
    code = 0
    try:
        connect(args.path, login=args.login)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'GitHub setup stopped: {error}', flush=True)
        code = 1
    return close_console(code)


if __name__ == '__main__':
    raise SystemExit(main())
