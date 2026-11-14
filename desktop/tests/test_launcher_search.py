"""Provider behavior and hostile input regression tests (no desktop required)."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

SOURCE = Path(__file__).resolve().parents[2] / 'system/apps/shell/scripts/launcher_search.py'
spec = importlib.util.spec_from_file_location('launcher_search', SOURCE)
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherSearchTests(unittest.TestCase):
    def test_math(self):
        for expression, expected in [('2+3*4', '14'), ('sqrt(144)+2^3', '20'),
                                     ('-2.5*4', '-10'), ('round(pi, 2)', '3.14'),
                                     ('10%3', '1'), ('(10-4)/2', '3')]:
            with self.subTest(expression=expression):
                self.assertEqual(launcher.calculate(expression), expected)
        self.assertEqual(launcher.search('= 2+2')[0]['target'], '4')

    def test_unsafe_and_expensive_math(self):
        for expression in ['__import__("os").system("false")', '(1).__class__',
                           '2^10000', '9^(9^9)', '1/0', '[1]*999999',
                           'sqrt(-1)', 'True', '1e999', 'pow(2,3)', '2+' ]:
            with self.subTest(expression=expression):
                self.assertEqual(launcher.search('= ' + expression)[0]['kind'], 'hint')

    def test_google_encoding(self):
        term = 'cats & dogs # 日本 $(touch /tmp/never)'
        result = launcher.search('g ' + term)
        self.assertEqual(len(result), 1)
        self.assertEqual(parse_qs(urlsplit(result[0]['target']).query)['q'], [term])
        self.assertEqual(launcher.search('firefox')[-1]['name'], 'Google: firefox')
        self.assertEqual(launcher.search(''), [])

    def test_urls(self):
        self.assertEqual(launcher.search('example.org/docs')[0]['target'], 'https://example.org/docs')
        self.assertEqual(launcher.search('http://localhost:3000')[0]['target'], 'http://localhost:3000')
        for query in ['javascript:alert(1)', 'file:///etc/passwd', 'two words.com']:
            self.assertTrue(all(r['comment'] != 'Default browser' for r in launcher.search(query)))
        self.assertEqual(launcher.search('https://[')[0]['comment'], 'Search in default browser')

    def test_files_and_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / 'Documents').mkdir()
            (home / 'Documents' / 'A report.txt').touch()
            (home / '.secret').mkdir()
            (home / '.secret' / 'report.txt').touch()
            (home / 'linked').symlink_to(home / '.secret', target_is_directory=True)
            results = launcher.search('files REPORT', home)
            files = [r for r in results if r['kind'] == 'open']
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0]['target'], (home / 'Documents' / 'A report.txt').as_uri())
            self.assertEqual(launcher.search(str(home / 'Documents'))[0]['kind'], 'open')
            self.assertEqual(launcher.search(str(home / 'missing'))[0]['kind'], 'hint')


if __name__ == '__main__':
    unittest.main()
