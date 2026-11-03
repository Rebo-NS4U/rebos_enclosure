import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import hardware
spec = importlib.util.spec_from_file_location('profile_setup', SCRIPTS / 'setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class HardwareProfileTests(unittest.TestCase):
    def test_mixed_gpu_and_custom_kernel_detection_has_no_machine_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cpuinfo = root / 'cpuinfo'
            cpuinfo.write_text('vendor_id : GenuineIntel\n')
            for slot, vendor in [('0000:00:02.0', '0x8086'), ('0000:01:00.0', '0x10de')]:
                device = root / 'bus/pci/devices' / slot
                device.mkdir(parents=True)
                (device / 'class').write_text('0x030000\n')
                (device / 'vendor').write_text(vendor + '\n')
            modules = root / 'modules/custom'
            modules.mkdir(parents=True)
            (modules / 'pkgbase').write_text('linux-custom\n')
            output = root / 'class/drm/card3-DP-9'
            output.mkdir(parents=True)
            (output / 'status').write_text('connected\n')
            (output / 'modes').write_text('2560x1440\n')
            def command(args):
                return 'linux\n' if args == ['pacman', '-Qq'] else ''
            detected = hardware.detect(root, cpuinfo, root / 'modules', command, '')
            self.assertEqual(detected['cpu'], 'intel')
            self.assertEqual(detected['gpus'], ['intel', 'nvidia'])
            self.assertEqual(detected['kernels'], ['linux', 'linux-custom'])
            self.assertEqual(detected['outputs'], [{'name': 'DP-9', 'modes': ['2560x1440']}])

    def test_detection_uses_battery_or_chassis_without_vendor_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(hardware.machine_policy('auto', hardware.capabilities(root, ''))['profile'], 'desktop')
            battery = root / 'class/power_supply/BAT9'
            battery.mkdir(parents=True)
            (battery / 'type').write_text('Battery\n')
            detected = hardware.capabilities(root, '')
            self.assertTrue(detected['battery'])
            self.assertEqual(hardware.machine_policy('auto', detected)['profile'], 'laptop')
            (battery / 'type').unlink()
            chassis = root / 'class/dmi/id/chassis_type'
            chassis.parent.mkdir(parents=True)
            chassis.write_text('10\n')
            self.assertTrue(hardware.capabilities(root, '')['portable'])

    def test_virtual_and_manual_profiles_override_chassis(self):
        detected = {'portable': True, 'virtualization': 'kvm'}
        self.assertEqual(hardware.machine_policy('auto', detected)['profile'], 'virtual')
        self.assertEqual(hardware.machine_policy('desktop', detected)['profile'], 'desktop')
        with self.assertRaises(ValueError):
            hardware.machine_policy('unsafe', {})

    def test_rendered_policies_validate_with_niri(self):
        for profile in ('desktop', 'laptop', 'virtual'):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as tmp:
                machine = hardware.machine_policy(profile, {})
                path = Path(tmp) / 'hardware.kdl'
                path.write_text(hardware.render(machine))
                result = subprocess.run(['niri', 'validate', '-c', str(path)], text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual('numlock' in path.read_text(), profile == 'desktop')
                self.assertEqual('animations { off;' in path.read_text(), profile == 'virtual')

    def test_machine_and_monitor_includes_are_idempotent(self):
        for profile in ('desktop', 'laptop', 'virtual'):
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / 'config.kdl').write_text('// Personal configuration retained.\n')
                plan = {'machine': hardware.machine_policy(profile, {}), 'monitors': {'outputs': []}}
                setup.customize_niri(root, plan)
                setup.customize_niri(root, plan)
                text = (root / 'config.kdl').read_text()
                self.assertEqual(text.count('include "hardware.kdl"'), 1)
                self.assertEqual(text.count('include "monitors.kdl"'), 1)
                result = subprocess.run(['niri', 'validate', '-c', str(root / 'config.kdl')], text=True, capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_malformed_saved_policy_is_rejected(self):
        machine = hardware.machine_policy('desktop', {})
        machine['numlock'] = False
        with self.assertRaises(ValueError):
            hardware.render(machine)


if __name__ == '__main__':
    unittest.main()
