#!/usr/bin/env python3
"""Use the shared ACP transport while retaining the shell's nonparking protocol."""
from pathlib import Path
import runpy

_shared = runpy.run_path(str(Path(__file__).resolve().parents[2] / 'assistant/scripts/ai_bridge.py'))
globals().update({name: value for name, value in _shared.items() if not name.startswith('_')})
Bridge = _shared['Bridge']
main = _shared['main']
Bridge.parking_enabled = False

if __name__ == '__main__':
    raise SystemExit(main())
