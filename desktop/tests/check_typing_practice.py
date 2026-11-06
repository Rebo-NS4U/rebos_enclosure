#!/usr/bin/env python3
"""Run the typing rendering and loop checks in an isolated Wayland panel."""
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]

def main():
    with tempfile.TemporaryDirectory(prefix="enclosure-typing-") as directory:
        target = Path(directory)
        source = ROOT / "system/apps/shell"
        for name in ("config", "modules", "TypingMenu.qml", "TypingTexts.js", "scripts", "version"):
            if (source / name).is_dir():
                shutil.copytree(source / name, target / name)
            else:
                shutil.copyfile(source / name, target / name)
        shutil.copyfile(ROOT / "desktop/tests/fixtures/typing_practice.qml", target / "shell.qml")
        result = subprocess.run(["qs", "-p", str(target / "shell.qml")], capture_output=True, text=True, timeout=15)
        output = result.stdout + result.stderr
        print(output)
        assert result.returncode == 0 and "PASS:" in output and "ERROR" not in output

if __name__ == "__main__":
    main()
