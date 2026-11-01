import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
spec = importlib.util.spec_from_file_location('installer_setup', SCRIPTS / 'setup.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


def hardware(**kwargs):
    result = dict(cpu='amd', gpus=['amd'], gpu_descriptions=[], kernels=['linux'],
                  installed=[], outputs=[], mkinitcpio=True)
    result.update(kwargs)
    return result


def options(**kwargs):
    result = dict(profile='full', groups=None, graphics='auto', microcode='auto', no_aur=False,
                  no_bluetooth=False, no_power=False, login='regreet', network='networkmanager',
                  kernel_headers=None, early_kms=False, hybrid=None, files_only=False,
                  monitor_config={'layout': 'auto', 'outputs': []})
    result.update(kwargs)
    return argparse.Namespace(**result)


class SetupTests(unittest.TestCase):
    def test_default_login_installs_regreet_instead_of_ly(self):
        plan = setup.build_plan(options(), hardware())
        self.assertEqual(plan['login'], 'regreet')
        self.assertTrue({'greetd', 'greetd-regreet', 'cage'} <= set(plan['packages']))
        self.assertNotIn('ly', plan['packages'])
        setup.validate_plan(plan)

    def test_groups_cover_previous_full_app_selection(self):
        for category, filename in [('repo', 'apps.txt'), ('aur', 'aur.txt')]:
            selected = {p for group in setup.GROUPS.values() for p in group[category]}
            self.assertEqual(selected, set(setup.packages_from(setup.ROOT / 'packages' / filename)))

    def test_core_and_custom_groups_do_not_install_unselected_apps(self):
        plan = setup.build_plan(options(profile='core'), hardware())
        self.assertNotIn('discord', plan['packages'])
        self.assertEqual(plan['aur_packages'], [])
        plan = setup.build_plan(options(groups='notes,communication', no_aur=True), hardware())
        self.assertIn('obsidian', plan['packages'])
        self.assertIn('discord', plan['packages'])
        self.assertNotIn('nodejs', plan['packages'])
        self.assertEqual(plan['aur_packages'], [])

    def test_service_and_microcode_choices_change_packages(self):
        plan = setup.build_plan(options(login='keep', no_bluetooth=True, no_power=True,
                                        microcode='keep', graphics='keep'), hardware())
        self.assertFalse({'greetd', 'greetd-regreet', 'cage', 'ly', 'blueman', 'bluez', 'power-profiles-daemon', 'amd-ucode', 'vulkan-radeon'} & set(plan['packages']))
        self.assertIn('mesa', plan['packages'])

    def test_nvidia_open_includes_headers_for_each_installed_kernel(self):
        plan = setup.build_plan(options(graphics='nvidia-open', groups='none'),
                                hardware(gpus=['intel', 'nvidia'], kernels=['linux', 'linux-lts']))
        self.assertTrue({'nvidia-open-dkms', 'nvidia-utils', 'dkms', 'linux-headers', 'linux-lts-headers'} <= set(plan['packages']))
        self.assertTrue(plan['hybrid'])
        self.assertNotIn('nvidia-580xx-dkms', plan['aur_packages'])

    def test_nvidia_legacy_does_not_pull_current_driver_utils(self):
        plan = setup.build_plan(options(graphics='nvidia-580', groups='none'), hardware(gpus=['nvidia']))
        self.assertIn('nvidia-580xx-dkms', plan['aur_packages'])
        self.assertIn('nvidia-580xx-utils', plan['aur_packages'])
        self.assertNotIn('nvidia-utils', plan['packages'])
        self.assertFalse(plan['hybrid'])

    def test_hybrid_machine_can_choose_integrated_only_or_keep_with_offload(self):
        hw = hardware(gpus=['amd', 'nvidia'])
        plan = setup.build_plan(options(graphics='amd'), hw)
        self.assertFalse(plan['hybrid'])
        self.assertIn('vulkan-radeon', plan['packages'])
        plan = setup.build_plan(options(graphics='keep', hybrid=True), hw)
        self.assertTrue(plan['hybrid'])
        self.assertNotIn('nvidia-open-dkms', plan['packages'])

    def test_invalid_driver_prerequisites_fail_during_planning(self):
        for opts, hw in [(options(graphics='nvidia-580', no_aur=True), hardware()),
                         (options(graphics='nvidia-open'), hardware(kernels=[])),
                         (options(graphics='nvidia-open', early_kms=True), hardware(mkinitcpio=False)),
                         (options(graphics='mesa', early_kms=True), hardware()),
                         (options(graphics='nvidia-open', kernel_headers='-unsafe-headers'), hardware())]:
            with self.subTest(opts=opts), self.assertRaises(ValueError):
                setup.build_plan(opts, hw)

    def test_driver_conflicts_preserve_existing_driver_family(self):
        plan = setup.build_plan(options(graphics='nvidia-open'), hardware())
        with self.assertRaisesRegex(ValueError, 'conflict'):
            setup.driver_conflicts(plan, ['nvidia-580xx-dkms', 'nvidia-580xx-utils'])
        setup.driver_conflicts(plan, ['nvidia-open-dkms', 'nvidia-utils'])
        plan['graphics'] = 'keep'
        setup.driver_conflicts(plan, ['nvidia-580xx-dkms'])

    def test_scaled_rotated_layout_uses_logical_dimensions(self):
        config = {'layout': 'horizontal', 'outputs': [
            {'name': 'DP-1', 'mode': '3840x2160@144', 'scale': 2},
            {'name': 'HDMI-A-1', 'mode': '1920x1080@60', 'transform': '90'},
            {'name': 'DP-2', 'mode': '1920x1080@60'}]}
        outputs = setup.normalize_monitors(config)['outputs']
        self.assertEqual([o['position']['x'] for o in outputs], [0, 1920, 3000])
        config['layout'] = 'vertical'
        self.assertEqual([o['position']['y'] for o in setup.normalize_monitors(config)['outputs']], [0, 1080, 3000])

    def test_automatic_positioning_does_not_guess_unknown_resolutions(self):
        with self.assertRaisesRegex(ValueError, 'known resolutions'):
            setup.normalize_monitors({'layout': 'horizontal', 'outputs': [{'name': 'DP-1'}]})
        text = setup.render_monitors({'outputs': []})
        self.assertNotIn('output ', text)

    def test_bad_monitors_and_kdl_injection_are_rejected(self):
        cases = [ [{'name': 'DP-1'}, {'name': 'DP-1'}], [{'name': 'DP-1', 'enabled': False}],
                  [{'name': 'DP-1', 'scale': float('nan')}], [{'name': 'DP-1', 'mode': '1920x1080"; spawn "bad'}],
                  [{'name': 'DP-1"\nspawn "bad'}], [{'name': 'DP-1', 'primary': True}, {'name': 'DP-2', 'primary': True}]]
        for outputs in cases:
            with self.subTest(outputs=outputs), self.assertRaises(ValueError):
                setup.normalize_monitors({'outputs': outputs})
        with self.assertRaisesRegex(ValueError, 'overlap'):
            setup.normalize_monitors({'layout': 'manual', 'outputs': [
                {'name': 'DP-1', 'mode': '1920x1080', 'position': {'x': 0, 'y': 0}},
                {'name': 'DP-2', 'mode': '1920x1080', 'position': {'x': 0, 'y': 0}}]})

    def test_rendered_monitor_kdl_validates_with_real_niri(self):
        config = {'layout': 'horizontal', 'outputs': [
            {'name': 'DP-1', 'mode': '3840x2160@144', 'scale': 2},
            {'name': 'HDMI-A-1', 'mode': '1920x1080@60', 'transform': '90', 'primary': True},
            {'name': 'eDP-1', 'enabled': False}]}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'monitors.kdl'
            path.write_text(setup.render_monitors(config))
            result = subprocess.run(['niri', 'validate', '-c', str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('off', path.read_text())
            self.assertIn('focus-at-startup', path.read_text())


if __name__ == '__main__':
    unittest.main()
