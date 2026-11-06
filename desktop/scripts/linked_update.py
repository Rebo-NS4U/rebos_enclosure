"""Preview linked updates with local edits before touching the live checkout."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

from deploy import verify


def git(root, *args, input=None, check=True, raw=False):
    result = subprocess.run(['git', '-C', str(root), *args], input=input,
                            capture_output=True, text=True)
    if check and result.returncode:
        raise ValueError((result.stderr or result.stdout).strip())
    return (result.stdout if raw else result.stdout.rstrip('\n')) if check else result


def changed_state(root):
    return git(root, 'status', '--porcelain=v1', '-z', '--untracked-files=all')


def working_state(root):
    names = set(filter(None, git(root, 'ls-files', '--modified', '--others', '--exclude-standard', '-z').split('\0')))
    names.update(filter(None, git(root, 'diff', '--cached', '--name-only', '-z').split('\0')))
    files = {}
    for name in sorted(names):
        path = root / name
        if path.is_symlink():
            files[name] = ['link', os.readlink(path)]
        elif path.is_file():
            files[name] = [path.stat().st_mode, hashlib.sha256(path.read_bytes()).hexdigest()]
        else:
            files[name] = ['deleted']
    return json.dumps([changed_state(root), files,
                       git(root, 'diff', '--cached', '--binary', 'HEAD', raw=True)], sort_keys=True)


def save_backup(root, home):
    parent = home / '.local/state/rebos-desktop/local-source-backups'
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    backup = Path(tempfile.mkdtemp(prefix='before-update-', dir=parent))
    backup.chmod(0o700)
    names = git(root, 'ls-files', '--modified', '--others', '--exclude-standard', '-z').split('\0')
    with tarfile.open(backup / 'local-files.tar.gz', 'w:gz') as archive:
        for name in dict.fromkeys(filter(None, names)):
            path = root / name
            if path.exists() or path.is_symlink():
                archive.add(path, arcname=name, recursive=False)
    for name, args in [('working.patch', ['diff', '--binary', 'HEAD']),
                       ('index.patch', ['diff', '--binary', '--cached'])]:
        (backup / name).write_text(git(root, *args, raw=True))
    (backup / 'head.txt').write_text(git(root, 'rev-parse', 'HEAD') + '\n')
    for path in backup.iterdir():
        path.chmod(0o600)
    return backup


class PreparedUpdate:
    def __init__(self, checkout, plan, home, head, status, *, untracked_moves=()):
        self.checkout, self.plan, self.home = checkout, plan, home
        self.head, self.status = head, status
        self.untracked_moves = untracked_moves

    def apply(self):
        root, plan = self.checkout, self.plan
        if git(root, 'rev-parse', 'HEAD') != self.head or working_state(root) != self.status:
            raise ValueError('Local source changed during the preview. Run the update again.')
        target = git(plan, 'rev-parse', 'HEAD')
        # Already-current source needs no stash or checkout operation.
        if target == self.head:
            metadata = root / 'desktop/payload/checksums.json'
            planned = (plan / 'desktop/payload/checksums.json').read_bytes()
            if metadata.read_bytes() != planned:
                backup = save_backup(root, self.home)
                with tempfile.NamedTemporaryFile(dir=metadata.parent, delete=False) as temporary:
                    temporary.write(planned)
                os.chmod(temporary.name, metadata.stat().st_mode)
                os.replace(temporary.name, metadata)
                print(f'Updated local source hashes; recovery backup: {backup}', flush=True)
            verify(root / 'desktop/payload')
            return
        backup = save_backup(root, self.home)
        print(f'Local source recovery backup: {backup}', flush=True)
        index_patch = git(plan, 'diff', '--cached', '--binary', 'HEAD', raw=True)
        working_patch = git(plan, 'diff', '--binary', raw=True)
        saved_stash = ''
        had_tracked_changes = bool(git(root, 'diff', '--name-only', 'HEAD'))
        if had_tracked_changes:
            git(root, 'stash', 'push', '-m', 'Enclosure update recovery; retained after update')
            saved_stash = git(root, 'rev-parse', 'refs/stash')
            (backup / 'stash.txt').write_text(saved_stash + '\n')
        try:
            git(root, 'merge', '--ff-only', target)
            if index_patch:
                git(root, 'apply', '--index', '--binary', '-', input=index_patch)
            if working_patch:
                git(root, 'apply', '--binary', '-', input=working_patch)
            from deploy import check_parent
            for old_name, new_name in self.untracked_moves:
                check_parent(root, old_name)
                check_parent(root, new_name)
                old, new = root / old_name, root / new_name
                if new.exists() or new.is_symlink():
                    raise ValueError('Untracked migration destination now exists: ' + new_name)
                new.parent.mkdir(parents=True, exist_ok=True)
                old.rename(new)
        except BaseException as error:
            if saved_stash and git(root, 'rev-parse', 'HEAD') == self.head:
                git(root, 'stash', 'apply', '--index', saved_stash)
            # Never auto-reset or discard source on failure. The exact tracked
            # snapshot remains in refs/stash and the private recovery archive.
            raise ValueError(f'Update interrupted; recover local files from {backup}: {error}') from error
        print('Local edits restored. Recovery archive and Git stash retained.', flush=True)


@contextmanager
def prepare(checkout, snapshot, home):
    checkout = Path(checkout)
    if git(checkout, 'diff', '--name-only', '--diff-filter=U'):
        raise ValueError('Resolve the existing Git conflicts before updating.')
    head, before = git(checkout, 'rev-parse', 'HEAD'), working_state(checkout)
    incoming = git(snapshot, 'rev-parse', 'HEAD')
    git(checkout, 'fetch', '--', str(snapshot), 'HEAD')
    saved = git(checkout, 'stash', 'create', 'Enclosure read-only update preview')
    original_index = git(checkout, 'diff', '--cached', '--binary', 'HEAD', raw=True)
    with tempfile.TemporaryDirectory(prefix='rebos-linked-preview-') as temporary:
        plan = Path(temporary) / 'source'
        git(checkout, 'worktree', 'add', '--detach', str(plan), head)
        try:
            merged = git(plan, '-c', 'commit.gpgsign=false', 'merge', '--no-edit', incoming, check=False)
            if merged.returncode:
                conflicts = git(plan, 'diff', '--name-only', '--diff-filter=U')
                raise ValueError('Incoming commits conflict with local commits; live files are unchanged: '
                                 + (conflicts or merged.stderr.strip()))
            if saved:
                applied = git(plan, 'stash', 'apply', saved, check=False)
                conflicts = git(plan, 'diff', '--name-only', '--diff-filter=U').splitlines()
                other = [p for p in conflicts if p != 'desktop/payload/checksums.json']
                if other or (applied.returncode and not conflicts):
                    raise ValueError('Local edits conflict with the update; live files are unchanged: '
                                     + (', '.join(other) or applied.stderr.strip()))
            # Restore the original staged/unstaged boundary in the isolated index.
            git(plan, 'restore', '--staged', '--source=HEAD', '--', '.')
            if original_index:
                git(plan, 'apply', '--cached', '--3way', '--binary', '-', input=original_index)
            untracked_moves = []
            for name in filter(None, git(checkout, 'ls-files', '--others', '--exclude-standard', '-z').split('\0')):
                destination = plan / name
                if name.startswith('desktop/payload/home/'):
                    from layout import manifest, source as source_path
                    payload = plan / 'desktop/payload'
                    if manifest(payload).get('layout') == 2:
                        destination = source_path(payload, name.removeprefix('desktop/payload/home/'))
                        untracked_moves.append((name, str(destination.relative_to(plan))))
                if destination.exists() or destination.is_symlink():
                    raise ValueError(f'Untracked file conflicts with incoming source; live files unchanged: {name}')
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(checkout / name, destination, follow_symlinks=False)
            payload = plan / 'desktop/payload'
            # Hash metadata is generated, so reconcile it from the preserved
            # sources instead of exposing merge markers to the live desktop.
            current = json.loads((checkout / 'desktop/payload/checksums.json').read_text())
            incoming_hashes = json.loads(git(plan, 'show', 'HEAD:desktop/payload/checksums.json'))
            names = set(current) | set(incoming_hashes)
            from deploy import check_parent
            from layout import checksum_path, manifest, source as source_path
            if manifest(payload).get('layout') == 2:
                translated = set()
                for name in names:
                    if name.startswith('home/'):
                        path = source_path(payload, name.removeprefix('home/'))
                        if path.is_relative_to(plan) and path.is_file():
                            translated.add(str(path.relative_to(plan)))
                    elif name.startswith('system/') and not (plan / name).exists() and (plan / 'system/etc' / name.removeprefix('system/')).exists():
                        translated.add('system/etc/' + name.removeprefix('system/'))
                    else:
                        translated.add(name)
                names = translated
            for name in names:
                path = checksum_path(payload, name)
                check_parent(plan if path.is_relative_to(plan) else payload, str(path.relative_to(plan if path.is_relative_to(plan) else payload)))
                if path.is_symlink():
                    raise ValueError('Payload checksum path cannot be a symlink: ' + name)
            hashes = {name: hashlib.sha256(checksum_path(payload, name).read_bytes()).hexdigest()
                      for name in sorted(names) if checksum_path(payload, name).is_file()}
            (payload / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')
            verify(payload)
            yield PreparedUpdate(checkout, plan, home, head, before, untracked_moves=untracked_moves)
        finally:
            git(checkout, 'worktree', 'remove', '--force', str(plan))
