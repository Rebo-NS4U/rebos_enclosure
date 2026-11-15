#!/usr/bin/env python3
"""Private frozen-screen OCR session. JSON lines in/out; EOF deletes captures."""
import csv
import json
import math
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from PIL import Image, ImageOps, ImageStat


def selection_values(region):
    values = [float(region[k]) for k in ('x', 'y', 'width', 'height', 'viewWidth', 'viewHeight')]
    x, y, width, height, vw, vh = values
    if not all(math.isfinite(v) for v in values) or min(width, height, vw, vh) <= 0:
        raise ValueError('Select a larger region.')
    return values


def selection_box(image, values):
    x, y, width, height, vw, vh = values
    sx, sy = image.width / vw, image.height / vh
    box = (max(0, math.floor(x * sx)), max(0, math.floor(y * sy)),
           min(image.width, math.ceil((x + width) * sx)),
           min(image.height, math.ceil((y + height) * sy)))
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError('Selection is outside the screen.')
    return box


def prepare_text(image, scale=3, binary=False):
    """Retain antialiasing and punctuation while enlarging screen text."""
    image = ImageOps.grayscale(image)
    # Screen selections normally contain more background than foreground.
    if ImageStat.Stat(image).median[0] < 128:
        image = ImageOps.invert(image)
    image = ImageOps.autocontrast(image)
    # Bound enlargement for full-screen selections to avoid excessive memory.
    scale = max(1, min(scale, 6000 / max(image.size)))
    if scale > 1:
        image = image.resize(tuple(round(size * scale) for size in image.size),
                             Image.Resampling.LANCZOS)
    if binary:
        image = image.point(lambda value: 255 if value > 160 else 0)
    return ImageOps.expand(image, border=20, fill=255)


def read_text(crop, mode='6', dictionaries=False):
    """Collect exact text and word confidence from the same recognition pass."""
    output = crop.with_suffix('')
    command = ['tesseract', str(crop), str(output), '-l', 'eng',
               '--dpi', '300', '--psm', mode]
    if not dictionaries:
        command += ['-c', 'load_system_dawg=0', '-c', 'load_freq_dawg=0',
                    '-c', 'preserve_interword_spaces=1']
    subprocess.run(command + ['txt', 'tsv'], check=True, capture_output=True, text=True)
    text = output.with_suffix('.txt').read_text().strip()
    with output.with_suffix('.tsv').open(newline='') as handle:
        words = [(float(row['conf']), len(row['text'].strip()))
                 for row in csv.DictReader(handle, delimiter='\t', quoting=csv.QUOTE_NONE)
                 if row['level'] == '5' and row['text'].strip()]
    weight = sum(length for _, length in words)
    confidence = sum(score * length for score, length in words) / weight if weight else 0
    return text, confidence


def refine_prose(crop, text, count):
    words = text.split()
    prose_words = sum(word.strip('.,!?;:\"\'()-').isalpha() for word in words)
    if len(words) >= 4 and prose_words / len(words) >= 0.7:
        mode = '3' if len(text.splitlines()) > 1 else '6'
        regular, _ = read_text(crop, mode=mode, dictionaries=True)
        if regular and count(regular) >= count(text) * 0.8:
            text = regular
    return text


def recognize(path, region):
    """Map logical selection coordinates to native pixels, including scaled outputs."""
    values = selection_values(region)
    with Image.open(path) as image:
        box = selection_box(image, values)
        with tempfile.TemporaryDirectory(prefix='enclosure-ocr-region-') as directory:
            crop = Path(directory) / 'region.png'
            selection = image.crop(box)
            prepare_text(selection).save(crop)
            text, confidence = read_text(crop)
            count = lambda value: sum(character.isalnum() for character in value)
            # A second rendering can separate tiny dots/stems that antialiasing
            # merges. Never guess an extension or rewrite identifiers by spelling.
            if confidence < 85:
                alternate = Path(directory) / 'contrast.png'
                prepare_text(selection, scale=4, binary=True).save(alternate)
                candidate, score = read_text(alternate)
                if candidate and score > confidence + 2 and count(candidate) >= count(text) * 0.9:
                    text, confidence = candidate, score
            text = refine_prose(crop, text, count)
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
