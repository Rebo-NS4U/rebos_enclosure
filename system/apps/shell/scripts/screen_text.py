#!/usr/bin/env python3
"""Private frozen-screen OCR session. JSON lines in/out; EOF deletes captures."""
import json
import math
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from PIL import Image


def recognize(path, region):
    """Map logical selection coordinates to native pixels, including scaled outputs."""
    values = [float(region[k]) for k in ('x', 'y', 'width', 'height', 'viewWidth', 'viewHeight')]
    x, y, width, height, vw, vh = values
    if not all(math.isfinite(v) for v in values) or min(width, height, vw, vh) <= 0:
        raise ValueError('Select a larger region.')
    with Image.open(path) as image:
        sx, sy = image.width / vw, image.height / vh
        box = (max(0, math.floor(x * sx)), max(0, math.floor(y * sy)),
               min(image.width, math.ceil((x + width) * sx)),
               min(image.height, math.ceil((y + height) * sy)))
        if box[2] <= box[0] or box[3] <= box[1]:
            raise ValueError('Selection is outside the screen.')
        with tempfile.TemporaryDirectory(prefix='enclosure-ocr-region-') as directory:
            crop = Path(directory) / 'region.png'
            image.crop(box).save(crop)
            result = subprocess.run(['tesseract', str(crop), 'stdout', '-l', 'eng'],
                                    check=True, capture_output=True, text=True)
    text = result.stdout.strip()
    return {'text': text, 'error': '' if text else 'No text found. Try larger text or a tighter selection.'}


def emit(result):
    print(json.dumps(result), flush=True)


def session():
    # Termination also unwinds TemporaryDirectory if the owning window exits.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    with tempfile.TemporaryDirectory(prefix='enclosure-screen-text-') as directory:
        outputs = json.loads(subprocess.check_output(['niri', 'msg', '-j', 'outputs'], text=True))
        images = {}
        for index, (name, output) in enumerate(outputs.items()):
            if not output.get('logical'):
                continue
            path = Path(directory) / f'{index}.png'
            subprocess.run(['grim', '-l', '0', '-o', name, str(path)], check=True, capture_output=True)
            images[name] = str(path)
        if not images:
            raise ValueError('No active screens found.')
        emit({'screens': images})
        for line in sys.stdin:
            try:
                region = json.loads(line)
                result = recognize(images[region['screen']], region)
            except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
                result = {'error': 'Could not read this selection. ' + str(error)}
            emit(result)


def main():
    try:
        session()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        emit({'error': 'Could not capture the screen. ' + str(error)})


if __name__ == '__main__':
    main()
