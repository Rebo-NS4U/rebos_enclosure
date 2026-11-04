"""Verify recovery refactoring with temporary payloads and stubbed host actions."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
ENTRY = ROOT / 'docs/restore-windows-vm-passthrough.sh'
MODULES = ROOT / 'docs/windows-vm-passthrough'


class VmRecoveryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='vm-recovery-test-')
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.env = dict(os.environ, VM_RECOVERY_SCRIPT=str(ENTRY),
                        VM_RECOVERY_LOG=str(self.root / 'actions.log'), TMPDIR=str(self.root))

    def shell(self, body, input=None):
        return subprocess.run(['bash', '-c', 'source "$VM_RECOVERY_SCRIPT"\n' + body],
                              input=input, env=self.env, cwd=self.root,
                              text=True, capture_output=True, timeout=10)

    def test_all_sources_and_generated_helpers_have_valid_bash_syntax(self):
        for source in (ENTRY, *MODULES.glob('*.sh')):
            subprocess.run(['bash', '-n', str(source)], check=True)
        result = self.shell('write_payloads; printf "%s" "$TEMP_DIR"')
        self.assertEqual(result.returncode, 0, result.stderr)
        output = Path(result.stdout)
        for name in ('gpu-status', 'gpu-to-vfio', 'gpu-to-nvidia', 'qemu-hook'):
            subprocess.run(['bash', '-n', str(output / name)], check=True)

    def test_generated_payloads_match_original_script_bytes(self):
        result = self.shell('write_payloads; printf "%s" "$TEMP_DIR"')
        self.assertEqual(result.returncode, 0, result.stderr)
        output = Path(result.stdout)
        actual = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()}
        expected = json.loads((Path(__file__).parent / 'fixtures/vm_passthrough_payload_hashes.json').read_text())
        self.assertEqual(actual, expected)

    def test_help_and_argument_errors_work_from_another_directory(self):
        result = subprocess.run(['bash', str(ENTRY), '--help'], cwd=self.root,
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Without this, only validate and preview', result.stdout)
        for arguments, message in [(['--unknown'], 'unknown option'),
                                   (['--vm-xml'], '--vm-xml requires a path'),
                                   (['--outbound-interface'], '--outbound-interface requires a name')]:
            with self.subTest(arguments=arguments):
                result = subprocess.run(['bash', str(ENTRY), *arguments], cwd=self.root,
                                        text=True, capture_output=True, timeout=10)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_options_keep_paths_with_spaces_and_source_does_not_run_main(self):
        result = self.shell('''
parse_args --apply --configure-boot --vm-xml "/saved images/windows.xml" --outbound-interface wlan0
printf '%s\\0' "$APPLY" "$CONFIGURE_BOOT" "$VM_XML" "$OUTBOUND_INTERFACE"
''')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split('\0'), ['1', '1', '/saved images/windows.xml', 'wlan0', ''])
        self.assertFalse((self.root / 'actions.log').exists())

    def workflow(self, arguments='', confirmation=None):
        # All hardware probes and host mutation entry points are replaced before
        # main is invoked. This test must never install packages or change /sys.
        functions = ('validate_hardware', 'preview', 'write_payloads', 'install_packages',
                     'install_host_files', 'configure_boot', 'enable_libvirt',
                     'configure_firewall', 'define_vm', 'validate_result')
        stubs = 'require_command() { :; }\n'
        stubs += '\n'.join(name + '() { printf "%s\\n" "' + name + '" >>"$VM_RECOVERY_LOG"; }'
                           for name in functions)
        stubs += '\nsudo() { { printf sudo; printf " %s" "$@"; printf "\\n"; } >>"$VM_RECOVERY_LOG"; }\n'
        result = self.shell(stubs + '\nparse_args ' + arguments + '\nmain\n', input=confirmation)
        log = self.root / 'actions.log'
        return result, log.read_text().splitlines() if log.exists() else []

    def test_default_dry_run_and_rejected_confirmation_cannot_apply_changes(self):
        for arguments, confirmation, code in [('', None, 0), ('--apply', 'no\n', 1)]:
            with self.subTest(arguments=arguments):
                (self.root / 'actions.log').unlink(missing_ok=True)
                result, commands = self.workflow(arguments, confirmation)
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual(commands, ['validate_hardware', 'preview'])

    def test_confirmed_apply_preserves_order_and_boot_option(self):
        for boot in (False, True):
            with self.subTest(configure_boot=boot):
                (self.root / 'actions.log').unlink(missing_ok=True)
                result, commands = self.workflow('--apply' + (' --configure-boot' if boot else ''),
                                                  'RESTORE-PASSTHROUGH\n')
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(commands, ['validate_hardware', 'preview', 'sudo -v',
                                           'write_payloads', 'install_packages', 'install_host_files'] +
                                 (['configure_boot'] if boot else []) +
                                 ['enable_libvirt', 'configure_firewall', 'define_vm',
                                  'sudo mkinitcpio -P', 'validate_result'])

    def test_cleanup_removes_only_generated_temporary_payload_directory(self):
        sentinel = self.root / 'keep.txt'
        sentinel.write_text('keep')
        result = self.shell('write_payloads; generated=$TEMP_DIR; cleanup; [[ ! -e $generated ]]')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(sentinel.read_text(), 'keep')
