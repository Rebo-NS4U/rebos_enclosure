"""Exercise the QML tree builder with nested, filtered and changing processes."""
import pathlib
import shutil
import subprocess
import unittest


@unittest.skipUnless(shutil.which('node'), 'node is required for QML JavaScript checks')
class ProcessTreeTests(unittest.TestCase):
    def test_nested_totals_filters_and_cycles(self):
        source = pathlib.Path(__file__).resolve().parents[2] / 'system/apps/shell/modules/widgets/dashboard/metrics/ProcessTree.js'
        checks = r'''
const assert = require('assert');
const row = (pid, ppid, cpu, sockets = 0, gpu = {}) => ({pid, ppid, name: 'p'+pid, cpu, sockets, gpu, ram: 10, disk: 2});
const rows = [row(1,0,1), row(10,1,2), row(11,10,3), row(12,11,4,1, {card: 5}), row(20,999,6)];
const trees = groups(rows, 'cpu', '');
const tree = trees.find(t => t.ppid === 10);
assert.equal(tree.cpu, 9);
assert.equal(tree.ram, 30);
assert.deepEqual(tree.children.map(r => [r.pid,r.depth]), [[10,0],[11,1],[12,2]]);
assert.equal(new Set(trees.flatMap(t => t.children.map(r => r.pid))).size, rows.length);
assert.deepEqual(groups(rows, 'network', '').map(t=>t.ppid), [10]);
assert.equal(groups(rows, 'gpu:card', 'card')[0].children.length, 3);
assert.equal(groups(rows.filter(r=>r.pid!==11), 'cpu', '').find(t=>t.ppid===12).children.length, 1);
assert.equal(groups([row(30,31,1),row(31,30,2)], 'cpu', '')[0].children.length, 2);
assert.deepEqual(groups([], 'cpu', ''), []);
'''
        subprocess.run(['node', '-e', source.read_text() + checks], check=True, capture_output=True, text=True)
