import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / 'system/apps/assistant/scripts/preset_tools.py'
spec = importlib.util.spec_from_file_location('preset_tools', SCRIPT)
tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tools)


class PresetToolsTest(unittest.TestCase):
    def test_decimal_arithmetic(self):
        self.assertEqual(tools.calculate('0.1 + 0.2'), '0.3')
        self.assertEqual(tools.calculate(' -(12.5 + 7.5) / 4 '), '-5.0')
        self.assertEqual(tools.calculate('1 / 3'), '0.3333333333333333333333333333')

    def test_rejects_execution_and_unbounded_operations(self):
        for value in ('__import__("os")', '2**100000', '1//2', '1e100', '9' * 513):
            with self.subTest(value=value[:40]), self.assertRaises((ValueError, SyntaxError)):
                tools.calculate(value)
        with self.assertRaises(ArithmeticError):
            tools.calculate('1/0')

    def test_environment_is_metadata_only(self):
        result = tools.environment()
        self.assertEqual(set(result), {'system', 'release', 'tools'})
        self.assertIn('systemctl', result['tools'])


if __name__ == '__main__':
    unittest.main()
