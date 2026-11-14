#!/usr/bin/env python3
"""Verify checksummed release archives with temporary-home deployment and recovery."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile


BACKUPS = Path('.local/state/rebos-desktop/backups')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def unpack(archive, destination):
    with archive.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    checksum = archive.with_name(archive.name + '.sha256').read_text().strip()
    require(checksum == digest + '  ' + archive.name, 'Archive checksum does not match: ' + str(archive))
    with tarfile.open(archive) as bundle:
        revision = bundle.pax_headers.get('comment')
        bundle.extractall(destination, filter='data')
    require((destination / 'desktop/scripts/deploy.py').is_file(), 'Archive has no Enclosure deployment entry point')
    return digest, revision


def deploy(source, *arguments):
    result = subprocess.run([sys.executable, str(source / 'desktop/scripts/deploy.py'), *map(str, arguments)],
                            env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                            capture_output=True, text=True, timeout=120, check=False)
    require(result.returncode == 0, result.stdout[-2500:] + result.stderr[-2500:])


def fingerprint(home):
    found = {}
    for path in sorted(home.rglob('*')):
        relative = path.relative_to(home)
        if relative == BACKUPS or BACKUPS in relative.parents:
            continue  # Recovery journals are intentionally retained after restore.
        if path.is_symlink():
            found[str(relative)] = ('link', os.readlink(path))
        elif path.is_file():
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            found[str(relative)] = (path.stat().st_mode & 0o777, digest)
    return found


def install(source, home):
    before = fingerprint(home)
    deploy(source, '--home', home, '--preserve-preferences', '--dry-run')
    require(fingerprint(home) == before, 'Dry run changed the temporary home')
    journals = set(home.glob(str(BACKUPS / '*/journal.json')))
    deploy(source, '--home', home, '--preserve-preferences')
    added = set(home.glob(str(BACKUPS / '*/journal.json'))) - journals
    require(len(added) == 1, 'Deployment did not create one recovery journal')
    return added.pop().parent


def seed_preferences(home):
    theme = home / '.config/rebos_shell/config/theme.json'
    value = json.loads(theme.read_text())
    value['releaseAcceptanceSentinel'] = 'preserve this custom preference'
    theme.write_text(json.dumps(value))
    credential = home / '.config/gh/hosts.yml'
    credential.parent.mkdir(parents=True, exist_ok=True)
    credential.write_text('example.invalid: synthetic release-test account\n')
    return {path: path.read_bytes() for path in (theme, credential)}


def exercise(source, home):
    before = fingerprint(home)
    backup = install(source, home)
    after = fingerprint(home)
    require(after != before, 'Fresh deployment produced no files')
    sentinels = seed_preferences(home)
    customized = fingerprint(home)
    update = install(source, home)
    require(all(path.read_bytes() == data for path, data in sentinels.items()), 'Update replaced personal settings')
    deploy(source, '--restore', update)
    require(fingerprint(home) == customized, 'Update recovery did not restore the prior files and links')
    deploy(source, '--restore', backup)
    # The synthetic account was not part of the install and must survive recovery.
    credential = home / '.config/gh/hosts.yml'
    require(credential.read_bytes() == sentinels[credential], 'Recovery deleted an unrelated account file')
    expected = before | {'.config/gh/hosts.yml': customized['.config/gh/hosts.yml']}
    require(fingerprint(home) == expected, 'Fresh recovery left changed files or links behind')


def upgrade(previous, source, home):
    install(previous, home)
    sentinels = seed_preferences(home)
    before = fingerprint(home)
    backup = install(source, home)
    require(all(path.read_bytes() == data for path, data in sentinels.items()), 'Cross-release update replaced preferences')
    deploy(source, '--restore', backup)
    require(fingerprint(home) == before, 'Cross-release recovery did not restore the prior release')


def check(archive, previous=None):
    with tempfile.TemporaryDirectory(prefix='enclosure-bundle-acceptance-') as directory:
        root = Path(directory)
        source = root / 'candidate'
        digest, revision = unpack(archive, source)
        deploy(source, '--verify')
        home = root / 'fresh user'
        home.mkdir()
        exercise(source, home)
        if previous:
            old = root / 'previous'
            unpack(previous, old)
            deploy(old, '--verify')
            home = root / 'upgrade user'
            home.mkdir()
            upgrade(old, source, home)
    return dict(archive=archive.name, sha256=digest, source_revision=revision, payload=True, fresh_files=True,
                repeat_update=True, preferences=True, file_recovery=True,
                previous_archive=previous.name if previous else None,
                package_boot_hardware_tested=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('--previous', type=Path, help='Checksummed previous release for upgrade/recovery acceptance')
    parser.add_argument('--report', type=Path, help='Write the acceptance result as JSON')
    args = parser.parse_args()
    try:
        result = check(args.archive.resolve(), args.previous.resolve() if args.previous else None)
        if args.report:
            with args.report.open('x') as stream:
                json.dump(result, stream, indent=2)
                stream.write('\n')
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, tarfile.TarError, subprocess.SubprocessError) as error:
        parser.exit(1, 'Release acceptance failed: ' + str(error) + '\n')


if __name__ == '__main__':
    main()
