"""Exceptions must not hide new warnings, growing complexity, or stale waivers."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts/quality.py'
spec = importlib.util.spec_from_file_location('quality_gate', SOURCE)
quality = importlib.util.module_from_spec(spec)
spec.loader.exec_module(quality)


class QualityGateTests(unittest.TestCase):
    def diagnostic(self, observed=18, symbol='too-many-locals'):
        return {'path': 'system/example.py', 'obj': 'parse', 'symbol': symbol,
                'message': f'Complexity ({observed}/15)'}

    def exception(self, ceiling=18, symbol='too-many-locals'):
        return {'path': 'system/example.py', 'object': 'parse', 'symbol': symbol, 'ceiling': ceiling}

    def test_new_or_larger_findings_fail(self):
        self.assertTrue(quality.check_ceilings([self.diagnostic()], []))
        self.assertTrue(quality.check_ceilings([self.diagnostic(19)], [self.exception()]))
        self.assertFalse(quality.check_ceilings([self.diagnostic(18)], [self.exception()]))
        self.assertFalse(quality.check_ceilings([self.diagnostic(17)], [self.exception()]))

    def test_missing_exception_and_unknown_diagnostic_fail(self):
        self.assertTrue(quality.check_ceilings([], [self.exception()]))
        finding = self.diagnostic()
        finding['message'] = 'Unrecognized diagnostic'
        self.assertTrue(quality.check_ceilings([finding], [self.exception()]))

    def test_minimum_method_count_cannot_shrink(self):
        symbol = 'too-few-public-methods'
        self.assertTrue(quality.check_ceilings([self.diagnostic(0, symbol)], [self.exception(1, symbol)]))
        self.assertFalse(quality.check_ceilings([self.diagnostic(1, symbol)], [self.exception(1, symbol)]))

    def test_directives_are_removed_without_altering_executable_code(self):
        source = 'def parse():  # pylint: disable=too-many-locals\n    return "pylint: disable is plain text"\n'
        raw = quality.without_exceptions(source)
        self.assertNotIn('# pylint:', raw)
        namespace = {}
        exec(compile(raw, '<test>', 'exec'), namespace)
        self.assertEqual(namespace['parse'](), 'pylint: disable is plain text')
