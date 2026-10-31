"""Check real parsing, native validation, editing and reinstall preservation."""
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'payload/home/.config/quickshell/scripts'
sys.path.insert(0, str(SCRIPTS))
from list_keybindings import collect
from edit_keybinding import save, add
sys.path.pop(0)
spec = importlib.util.spec_from_file_location('binding_deploy', ROOT / 'scripts/deploy.py')
deploy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deploy)


class PersonalBindingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'
        self.config = self.home / '.config'
        self.niri = self.config / 'niri'
        self.kitty = self.config / 'kitty'
        self.niri.mkdir(parents=True)
        self.kitty.mkdir()
        (self.niri / 'config.kdl').write_text('include "keybindings-defaults.kdl"\ninclude "keybindings-personal.kdl"\n')
        (self.niri / 'keybindings-defaults.kdl').write_text('binds {\n Mod+H { focus-column-left; }\n Mod+J { focus-window-down; }\n}\n')
        (self.niri / 'keybindings-personal.kdl').write_text('// My local keys\n')
        (self.niri / 'keybindings-defaults.sha256').write_text(hashlib.sha256((self.niri / 'keybindings-defaults.kdl').read_bytes()).hexdigest() + '\n')
        (self.kitty / 'kitty.conf').write_text('include keybindings-defaults.conf\ninclude keybindings-personal.conf\n')
        (self.kitty / 'keybindings-defaults.conf').write_text('map ctrl+shift+c copy_to_clipboard\n')
        (self.kitty / 'keybindings-personal.conf').write_text('# My terminal keys\n')

    def row(self, key):
        return next(row for row in collect(self.config)['bindings'] if row['rawKey'] == key)

    def validate(self):
        result = subprocess.run(['niri', 'validate', '-c', str(self.niri / 'config.kdl')], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_standard_movement_matrix_and_unique_chords(self):
        defaults = ROOT / 'defaults/keybindings-defaults.kdl'
        self.assertEqual(defaults.read_bytes(), (ROOT / 'payload/home/.config/niri/keybindings-defaults.kdl').read_bytes())
        text = defaults.read_text()
        for key, focus, move, direction in [('H','focus-column-left','consume-or-expel-window-left','left'),
                                           ('J','focus-window-down','move-window-down','down'),
                                           ('K','focus-window-up','move-window-up','up'),
                                           ('L','focus-column-right','consume-or-expel-window-right','right')]:
            for mods, action in [('',focus),('Shift+',move),('Ctrl+',f'focus-monitor-{direction}'),
                                 ('Shift+Ctrl+',f'move-window-to-monitor-{direction}')]:
                self.assertIn(f'Mod+{mods}{key} {{ {action}; }}', text)
        shutil.copyfile(defaults, self.niri / defaults.name)
        self.validate()
        rows = collect(self.config)['bindings']
        self.assertTrue(rows)

    def test_default_remap_and_second_remap_only_write_personal_file(self):
        defaults = (self.niri / 'keybindings-defaults.kdl').read_bytes()
        save({'binding': self.row('Mod+H'), 'key': 'Super+Y'}, self.config)
        self.validate()
        self.assertEqual((self.niri / 'keybindings-defaults.kdl').read_bytes(), defaults)
        self.assertFalse(any(row['rawKey'] == 'Mod+H' for row in collect(self.config)['bindings']))
        row = self.row('Mod+Y')
        self.assertEqual(row['action'], 'Focus column left')
        self.assertEqual(Path(row['source']).name, 'keybindings-personal.kdl')
        save({'binding': row, 'key': 'Super+U'}, self.config)
        self.validate()
        self.assertEqual(self.row('Mod+U')['action'], 'Focus column left')
        self.assertFalse(any(row['rawKey'] in ('Mod+H','Mod+Y') for row in collect(self.config)['bindings']))

    def test_new_shortcut_saves_to_personal_without_executing_command(self):
        before = (self.niri / 'config.kdl').read_text()
        sentinel = self.root / 'must-not-exist'
        add({'key':'Super+Y','command':f'touch {sentinel}','name':'Personal'},self.config)
        self.assertFalse(sentinel.exists())
        self.assertEqual((self.niri / 'config.kdl').read_text(),before)
        self.assertEqual(Path(self.row('Mod+Y')['source']).name,'keybindings-personal.kdl')
        self.validate()

    def test_kitty_remap_uses_personal_file_and_disables_old_key(self):
        defaults = (self.kitty / 'keybindings-defaults.conf').read_bytes()
        with patch('edit_keybinding.subprocess.run', return_value=subprocess.CompletedProcess([],0)):
            save({'binding':self.row('ctrl+shift+c'),'key':'Ctrl+Shift+Y'},self.config)
        self.assertEqual((self.kitty / 'keybindings-defaults.conf').read_bytes(),defaults)
        rows = collect(self.config)['bindings']
        self.assertFalse(any(row['rawKey']=='ctrl+shift+c' for row in rows))
        self.assertEqual(Path(self.row('Ctrl+Shift+y')['source']).name,'keybindings-personal.conf')

    def test_includes_are_positional_and_disabled_keys_stay_disabled(self):
        (self.niri / 'config.kdl').write_text('include "keybindings-defaults.kdl"\nbinds { Mod+H { focus-column-right; }; }\ninclude "keybindings-personal.kdl"\n')
        (self.niri / 'keybindings-personal.kdl').write_text('binds { Mod+H hotkey-overlay-title=null { spawn "/usr/bin/true"; }\n Mod+J { focus-window-up; }; }\n')
        self.validate()
        self.assertFalse(any(row['rawKey']=='Mod+H' for row in collect(self.config)['bindings']))
        self.assertEqual(self.row('Mod+J')['action'],'Focus window up')

    def payload(self):
        payload = self.root / 'payload'
        for name in ['niri','kitty']:
            shutil.copytree(self.config / name,payload / 'home/.config' / name)
        (payload / 'home/.config/niri/keybindings-personal.kdl').write_text('// empty user defaults\n')
        (payload / 'home/.config/kitty/keybindings-personal.conf').write_text('# empty user defaults\n')
        (payload / 'manifest.json').write_text(json.dumps({'units':['.config/niri','.config/kitty']}))
        (payload / 'checksums.json').write_text(json.dumps({str(p.relative_to(payload)):hashlib.sha256(p.read_bytes()).hexdigest()
            for p in payload.rglob('*') if p.is_file()}))
        return payload

    def test_two_reinstalls_update_and_restore_preserve_custom_and_disabled_keys(self):
        payload = self.payload()
        (self.niri / 'keybindings-personal.kdl').write_text('binds { Mod+H hotkey-overlay-title=null { spawn "/usr/bin/true"; }\n Mod+Y { focus-column-right; }; }\n')
        (self.kitty / 'keybindings-personal.conf').write_text('map ctrl+shift+y copy_to_clipboard\n')
        original = (self.niri / 'keybindings-personal.kdl').read_text()
        backups = []
        for _ in range(2):
            backups.append(deploy.install(payload,self.home))
            self.validate()
            self.assertEqual(self.row('Mod+Y')['action'],'Focus column right')
            self.assertFalse(any(row['rawKey']=='Mod+H' for row in collect(self.config)['bindings']))
            self.assertEqual(self.row('ctrl+shift+y')['action'],'Copy selection')
            self.assertNotIn('Mod+J', (self.niri / 'keybindings-personal.kdl').read_text())
        before = (self.niri / 'keybindings-personal.kdl').read_bytes()
        deploy.install(payload,self.home,preserve_preferences=True)
        self.assertEqual((self.niri / 'keybindings-personal.kdl').read_bytes(),before)
        deploy.restore(backups[1]);deploy.restore(backups[0])
        self.assertEqual((self.niri / 'keybindings-personal.kdl').read_text(),original)

    def test_kitty_include_with_spaces_is_read_and_preserved(self):
        payload = self.payload()
        (self.kitty / 'kitty.conf').write_text('include custom keys.conf\n')
        (self.kitty / 'custom keys.conf').write_text('map ctrl+y copy_to_clipboard\n')
        self.assertEqual(self.row('ctrl+y')['action'],'Copy selection')
        deploy.install(payload,self.home)
        self.assertEqual(self.row('ctrl+y')['action'],'Copy selection')

    def test_direct_edits_to_defaults_are_saved_on_reinstall(self):
        payload = self.payload()
        path = self.niri / 'keybindings-defaults.kdl'
        path.write_text(path.read_text().replace('focus-column-left','focus-column-right'))
        deploy.install(payload,self.home)
        self.validate()
        self.assertEqual(self.row('Mod+H')['action'],'Focus column right')
        self.assertEqual(Path(self.row('Mod+H')['source']).name,'keybindings-personal.kdl')

    def test_legacy_included_profile_and_kitty_options_are_preserved(self):
        payload = self.payload()
        (self.niri / 'keybindings-defaults.kdl').unlink()
        (self.niri / 'config.kdl').write_text('include "old.kdl"\n')
        (self.niri / 'old.kdl').write_text('binds { Mod+Y repeat=false hotkey-overlay-title="Mine" { spawn "echo" "{quoted}"; } }\n')
        (self.kitty / 'kitty.conf').write_text("font_family Wizard's font\ninclude extras.conf\n")
        (self.kitty / 'extras.conf').write_text('kitty_mod ctrl+alt\nmap --when-focus-on=title:notes kitty_mod+y copy_to_clipboard\n')
        deploy.install(payload,self.home)
        self.validate()
        self.assertEqual(self.row('Mod+Y')['action'],'Mine')
        text = (self.niri / 'keybindings-personal.kdl').read_text()
        self.assertIn('repeat=false',text);self.assertIn('"{quoted}"',text)
        terminal=(self.kitty / 'keybindings-personal.conf').read_text()
        self.assertIn('kitty_mod ctrl+alt',terminal)
        self.assertIn('--when-focus-on=title:notes',terminal)


if __name__=='__main__':unittest.main()
