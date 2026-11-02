"""Exercise project writes in temporary checkouts; never mutate user repositories."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'payload/home/.config/quickshell/scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('github_projects', SCRIPTS / 'github_projects.py')
projects = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projects)


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / 'project'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('remote', 'add', 'origin', 'https://github.com/example/project.git')
        for name in ('one.txt', 'two.txt'):
            (self.repo / name).write_text('original\n')
        self.git('add', '--', 'one.txt', 'two.txt')
        self.git('commit', '-qm', 'Initial')

    def git(self, *args):
        return projects.git(self.repo, *args)

    def act(self, kind, **kwargs):
        return projects.action({'action': kind, 'path': str(self.repo), **kwargs})

    def test_repository_validation_and_root(self):
        for value in ('example/project', 'https://github.com/example/project.git', 'git@github.com:example/project.git'):
            self.assertEqual(projects.repo_name(value), 'example/project')
        for value in ('file:///tmp/repo', 'https://evil.example/repo', '../project', '--arg/project', 'example/a/b'):
            with self.subTest(value=value), self.assertRaises(ValueError):
                projects.repo_name(value)
        (self.repo / 'subdir').mkdir()
        with self.assertRaisesRegex(ValueError, 'repository root'):
            projects.checkout(self.repo / 'subdir')
        self.git('remote', 'set-url', 'origin', '/tmp/other')
        with self.assertRaises(ValueError):
            self.act('fetch')

    def test_commit_preserves_unrelated_staged_changes(self):
        (self.repo / 'one.txt').write_text('one changed\n')
        (self.repo / 'two.txt').write_text('two changed\n')
        self.act('stage', files=['one.txt', 'two.txt'])
        self.act('commit', files=['one.txt'], message='Only selected file')
        self.assertEqual(self.git('show', 'HEAD:one.txt'), 'one changed')
        self.assertEqual(self.git('show', 'HEAD:two.txt'), 'original')
        self.assertEqual(self.git('diff', '--cached', '--name-only'), 'two.txt')

    def test_rename_commit_requires_both_paths(self):
        self.git('mv', 'one.txt', 'renamed.txt')
        with self.assertRaisesRegex(ValueError, 'both the old and new'):
            self.act('commit', files=['renamed.txt'], message='Rename')
        self.act('commit', files=['one.txt', 'renamed.txt'], message='Rename')
        self.assertEqual(self.git('ls-tree', '--name-only', 'HEAD'), 'renamed.txt\ntwo.txt')

    def prepare_remote(self):
        remote = self.root / 'remote.git'
        projects.run('git', 'init', '--bare', '-q', '-b', 'main', str(remote))
        self.git('remote', 'set-url', 'origin', str(remote))
        self.git('push', '-u', 'origin', 'main')
        peer = self.root / 'peer'
        projects.run('git', 'clone', '-q', str(remote), str(peer))
        projects.git(peer, 'config', 'user.name', 'Test')
        projects.git(peer, 'config', 'user.email', 'test@example.invalid')
        (peer / 'incoming.txt').write_text('incoming')
        projects.git(peer, 'add', 'incoming.txt')
        projects.git(peer, 'commit', '-qm', 'Incoming')
        projects.git(peer, 'push', 'origin', 'main')

    def test_pull_fast_forwards_current_branch(self):
        self.prepare_remote()
        with patch.object(projects, 'checkout', return_value=(self.repo, 'example/project')):
            self.act('pull')
        self.assertEqual((self.repo / 'incoming.txt').read_text(), 'incoming')

    def test_divergent_pull_preserves_local_commits(self):
        self.prepare_remote()
        (self.repo / 'local.txt').write_text('local')
        self.git('add', 'local.txt')
        self.git('commit', '-qm', 'Local')
        sha = self.git('rev-parse', 'HEAD')
        with patch.object(projects, 'checkout', return_value=(self.repo, 'example/project')):
            with self.assertRaises(ValueError):
                self.act('pull')
        self.assertEqual(self.git('rev-parse', 'HEAD'), sha)
        self.assertEqual((self.repo / 'local.txt').read_text(), 'local')

    def test_newer_unstaged_edits_block_commit(self):
        (self.repo / 'one.txt').write_text('first\n')
        self.act('stage', files=['one.txt'])
        (self.repo / 'one.txt').write_text('newer\n')
        with self.assertRaisesRegex(ValueError, 'newer unstaged'):
            self.act('commit', files=['one.txt'], message='No')
        self.assertEqual(self.git('log', '-1', '--format=%s'), 'Initial')

    def test_literal_file_paths_and_unstage(self):
        (self.repo / '[one].txt').write_text('literal')
        (self.repo / 'o.txt').write_text('other')
        self.act('stage', files=['[one].txt'])
        self.assertEqual(self.git('diff', '--cached', '--name-only'), '[one].txt')
        self.act('unstage', files=['[one].txt'])
        self.assertEqual(self.git('diff', '--cached', '--name-only'), '')
        self.assertEqual((self.repo / '[one].txt').read_text(), 'literal')

    def test_diff_is_read_only_and_explains_untracked_files(self):
        (self.repo / 'one.txt').write_text('changed')
        (self.repo / 'new.txt').write_text('new')
        before = self.git('status', '--porcelain')
        result = self.act('diff', files=['one.txt', 'new.txt'])
        self.assertIn('+changed', result['output'])
        self.assertIn('Untracked files', result['output'])
        self.assertFalse(result['refresh'])
        self.assertEqual(self.git('status', '--porcelain'), before)

    def test_selected_paths_cannot_escape_or_stage_unselected_directories(self):
        for files in ([], ['../outside'], ['/tmp/outside'], ['missing.txt'], ['.']):
            with self.subTest(files=files), self.assertRaises(ValueError):
                self.act('stage', files=files)

    def test_switch_and_create_require_clean_worktree(self):
        self.act('branch', branch='feature/test')
        self.assertEqual(self.git('branch', '--show-current'), 'feature/test')
        self.act('switch', branch='main')
        (self.repo / 'one.txt').write_text('keep me')
        with self.assertRaisesRegex(ValueError, 'local changes'):
            self.act('switch', branch='feature/test')
        with self.assertRaisesRegex(ValueError, 'local changes'):
            self.act('pull')
        self.assertEqual((self.repo / 'one.txt').read_text(), 'keep me')

    def test_push_refuses_other_push_destination(self):
        self.git('remote', 'set-url', '--push', 'origin', 'https://github.com/other/repository.git')
        with self.assertRaisesRegex(ValueError, 'push destination differs'):
            self.act('push')

    def test_push_uses_explicit_branch_and_no_force(self):
        calls = []
        real_git = projects.git
        def call(path, *args, **kwargs):
            calls.append(args)
            if args[0] == 'push':
                return 'pushed'
            return real_git(path, *args, **kwargs)
        with patch.object(projects, 'git', side_effect=call):
            self.act('push')
        self.assertIn(('push', '--set-upstream', 'origin', 'HEAD:refs/heads/main'), calls)

    def test_pr_requires_pushed_head(self):
        real_git = projects.git
        def call(path, *args, **kwargs):
            return '' if args[0] == 'ls-remote' else real_git(path, *args, **kwargs)
        with patch.object(projects, 'git', side_effect=call):
            with self.assertRaisesRegex(ValueError, 'Push this branch'):
                self.act('pr', title='Example', base='main')

    def test_pr_body_file_preserves_multiline_and_no_shell_expansion(self):
        sha = self.git('rev-parse', 'HEAD')
        real_git = projects.git
        real_run = projects.run
        body = 'First line\n\nLiteral `code` and $(not-executed)\n'
        def call(path, *args, **kwargs):
            return sha + '\trefs/heads/main' if args[0] == 'ls-remote' else real_git(path, *args, **kwargs)
        def run(*args, **kwargs):
            if args[0] == 'gh':
                self.assertEqual(Path(args[args.index('--body-file') + 1]).read_text(), body)
                self.assertIn('--draft', args)
                self.assertEqual(kwargs['cwd'], self.repo)
                return 'https://github.com/example/project/pull/1'
            return real_run(*args, **kwargs)
        with patch.object(projects, 'git', side_effect=call), patch.object(projects, 'run', side_effect=run):
            result = self.act('pr', title='Example', base='main', body=body)
        self.assertIn('/pull/1', result['output'])

    def test_clone_selects_and_remembers_new_checkout(self):
        destination = self.root / 'cloned'
        real_run = projects.run
        def run(*args, **kwargs):
            if args[:2] == ('git', 'clone'):
                rewritten = list(args)
                rewritten[-2] = str(self.repo)
                output = real_run(*rewritten, **kwargs)
                real_run('git', '-C', str(destination), 'remote', 'set-url', 'origin',
                         'https://github.com/example/project.git')
                return output
            return real_run(*args, **kwargs)
        with patch.object(projects.shutil, 'which', return_value=None), \
             patch.object(projects, 'run', side_effect=run), \
             patch.dict(os.environ, {'XDG_STATE_HOME': str(self.root / 'state')}):
            result = projects.action({'action': 'clone', 'repository': 'example/project',
                                      'destination': str(destination)})
            self.assertEqual(projects.saved_paths(), [str(destination)])
        self.assertEqual(result['path'], str(destination))
        self.assertEqual((destination / 'one.txt').read_text(), 'original\n')

    def test_clone_does_not_overwrite_existing_folder(self):
        with self.assertRaisesRegex(ValueError, 'already exists'):
            projects.action({'action': 'clone', 'repository': 'example/project', 'destination': str(self.repo)})

    def test_remember_keeps_personal_paths_in_state(self):
        with patch.dict(os.environ, {'XDG_STATE_HOME': str(self.root / 'state')}):
            self.act('add')
            self.assertEqual(projects.saved_paths(), [str(self.repo)])
            self.assertEqual(projects.state_file().stat().st_mode & 0o777, 0o600)

    def test_github_cli_404_keeps_local_comparison_available(self):
        with patch.object(projects.shutil, 'which', return_value='/usr/bin/gh'), \
             patch.object(projects, 'run', side_effect=ValueError('gh: Not found (HTTP 404)')):
            with self.assertRaises(projects.status.urllib.error.HTTPError) as error:
                projects.api('example/project', '/compare/old...new')
            error.exception.close()

    def test_unpublished_project_commit_compares_using_its_own_history(self):
        published = self.git('rev-parse', 'HEAD')
        (self.repo / 'one.txt').write_text('local commit')
        self.git('add', 'one.txt')
        self.git('commit', '-qm', 'Unpublished')
        error = projects.status.urllib.error.HTTPError('url', 404, 'Not found', {}, None)
        self.addCleanup(error.close)
        with patch.object(projects, 'api', side_effect=[{'default_branch': 'main'}, {'sha': published}, error]):
            result = projects.inspect(str(self.repo))
        self.assertEqual(result['status'], 'ahead')
        self.assertEqual(result['ahead'], 1)
        self.assertEqual(result['behind'], 0)

    def test_inspection_retains_local_details_when_remote_is_offline(self):
        with patch.object(projects, 'api', side_effect=OSError('offline')):
            result = projects.inspect(str(self.repo))
        self.assertTrue(result['ok'])
        self.assertEqual(result['status'], 'error')
        self.assertEqual(result['branches'], ['main'])
        self.assertEqual(result['history'][0]['title'], 'Initial')

    def test_empty_repository_can_be_inspected_and_make_first_commit(self):
        empty = self.root / 'empty'
        empty.mkdir()
        projects.git(empty, 'init', '-q', '-b', 'main')
        projects.git(empty, 'config', 'user.name', 'Test')
        projects.git(empty, 'config', 'user.email', 'test@example.invalid')
        projects.git(empty, 'remote', 'add', 'origin', 'https://github.com/example/empty.git')
        result = projects.inspect(str(empty))
        self.assertTrue(result['ok'])
        self.assertEqual(result['status'], 'unborn')
        self.assertEqual(result['branch'], 'main')
        (empty / 'first.txt').write_text('first')
        projects.action({'action': 'stage', 'path': str(empty), 'files': ['first.txt']})
        diff = projects.action({'action': 'diff', 'path': str(empty), 'files': ['first.txt']})
        self.assertIn('+first', diff['output'])
        projects.action({'action': 'commit', 'path': str(empty), 'files': ['first.txt'], 'message': 'First'})
        self.assertEqual(projects.git(empty, 'log', '-1', '--format=%s'), 'First')

    def test_action_cli_reads_one_json_line_without_requiring_eof(self):
        process = subprocess.Popen(['python3', str(SCRIPTS / 'github_projects.py'), 'action'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: process.kill() if process.poll() is None else None)
        process.stdin.write(json.dumps({'action': 'switch', 'path': str(self.repo), 'branch': 'main'}) + '\n')
        process.stdin.flush()
        process.wait(timeout=5)
        self.assertTrue(json.loads(process.stdout.read())['ok'])
        process.stdin.close()
        process.stdout.close()
        process.stderr.close()


if __name__ == '__main__':
    unittest.main()
