"""Recovery checkpoints stay compact without losing chat or pending requests."""
import asyncio
import json
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[2]


class BridgeMemoryTests(unittest.TestCase):
    def test_compact_checkpoint_roundtrip_and_acknowledgement(self):
        bridge_type = runpy.run_path(str(ROOT / 'system/apps/assistant/scripts/ai_bridge.py'))['Bridge']
        bridge = bridge_type()
        bridge.publish('acp', message={'id': 42, 'result': 'done'})
        state = {'currentChat': [{'role': 'assistant', 'text': 'tool output\n' * 100000}],
                 'pendingPermissions': {'request': {'id': 7}}, 'inputDraft': 'unsent'}
        bridge.checkpoint({'seq': 1, 'state': state})
        self.assertEqual(bridge.state, state)
        self.assertLess(len(bridge._state), len(json.dumps(state)) // 10)
        self.assertFalse(bridge.events)
        # A decoded state is temporary; mutating it must not corrupt recovery.
        decoded = bridge.state
        decoded['inputDraft'] = 'changed'
        self.assertEqual(bridge.state['inputDraft'], 'unsent')
        bridge.send = lambda value: self.assertEqual(value['state'], state)
        bridge.send_attached(bridge.state, 1)
        asyncio.run(bridge.stop())
        self.assertIsNone(bridge.state)
        self.assertIsNone(bridge._state)
