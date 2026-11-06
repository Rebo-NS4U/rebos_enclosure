#!/usr/bin/env python3
"""Run the typing rendering and loop checks in an isolated Wayland panel."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]

def main():
    with tempfile.TemporaryDirectory(prefix="enclosure-typing-") as directory:
        target = Path(directory)
        source = ROOT / "system/apps/shell"
        for name in ("config", "modules", "TypingMenu.qml", "TypingTexts.js", "TypingSpeed.js", "TypingPaging.js", "scripts", "version"):
            if (source / name).is_dir():
                shutil.copytree(source / name, target / name)
            else:
                shutil.copyfile(source / name, target / name)
        shutil.copyfile(ROOT / "desktop/tests/fixtures/typing_practice.qml", target / "shell.qml")
        book = target / 'picker test book.epub'
        with zipfile.ZipFile(book, 'w') as archive:
            archive.writestr('META-INF/container.xml', '<container><rootfile full-path="book.opf"/></container>')
            archive.writestr('book.opf', '<package xmlns="http://www.idpf.org/2007/opf"><manifest><item id="one" href="one.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="one"/></spine></package>')
            archive.writestr('one.xhtml', '<h1>Picker chapter</h1><p>This book arrived through the file picker.</p>')
        binaries = target / 'bin'
        binaries.mkdir()
        picker = binaries / 'zenity'
        # A deterministic chooser stand-in exercises success and cancellation.
        picker.write_text("#!/usr/bin/env python3\nimport pathlib, sys, time\nflag = pathlib.Path(" + repr(str(target / 'picked')) + ")\nif flag.exists():\n    time.sleep(2)\n    sys.exit(1)\nflag.touch()\nassert any('*.epub' in arg for arg in sys.argv)\ntime.sleep(4)\nprint(" + repr(str(book)) + ")\n")
        picker.chmod(0o755)
        try:
            result = subprocess.run(["qs", "-p", str(target / "shell.qml")], capture_output=True, text=True, timeout=40, env=dict(os.environ, XDG_DATA_HOME=str(target / "data"), PATH=str(binaries) + os.pathsep + os.environ['PATH']))
        except subprocess.TimeoutExpired as error:
            print((error.stdout or b" ").decode(errors="replace"))
            print((error.stderr or b" ").decode(errors="replace"))
            raise
        output = result.stdout + result.stderr
        print(output)
        assert result.returncode == 0 and "PASS:" in output and "ERROR" not in output

if __name__ == "__main__":
    main()
