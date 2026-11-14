#!/usr/bin/env python3
"""Read a user-selected screen region locally; never retain captures."""
import json
import subprocess
import tempfile


def capture():
    selection = subprocess.run(['slurp'], capture_output=True, text=True)
    if selection.returncode:
        return {'cancelled': True}
    with tempfile.TemporaryDirectory(prefix='enclosure-ocr-') as directory:
        image = directory + '/region.png'
        subprocess.run(['grim', '-g', selection.stdout.strip(), image], check=True, capture_output=True)
        result = subprocess.run(['tesseract', image, 'stdout', '-l', 'eng'],
                                check=True, capture_output=True, text=True)
    text = result.stdout.strip()
    return {'text': text, 'error': '' if text else 'No text found. Try a tighter selection with larger text.'}


def main():
    try:
        result = capture()
    except (OSError, subprocess.CalledProcessError) as error:
        result = {'error': 'Could not read screen text. Check grim, slurp and Tesseract English data. ' + str(error)}
    print(json.dumps(result))


if __name__ == '__main__':
    main()
