#!/usr/bin/env python3
"""Run the canonical assistant helper from the shared application layout."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[2] / "assistant/scripts/ai_questions.py"),
                   run_name="__main__")
