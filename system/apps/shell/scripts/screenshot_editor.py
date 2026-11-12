#!/usr/bin/env python3
"""Private capture sessions and native-resolution screenshot export for Quickshell."""
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from PIL import Image, ImageDraw, ImageFont


def render(source, spec):
    image = source.convert('RGB')
    sx, sy = image.width / spec['width'], image.height / spec['height']
    draw = ImageDraw.Draw(image)
    for op in spec['operations']:
        points = [(p['x'] * sx, p['y'] * sy) for p in op['points']]
        color = op.get('color', '#ff5252')
        width = max(1, round(op.get('size', 4) * (sx + sy) / 2))
        if op['tool'] == 'pen' and len(points) > 1:
            draw.line(points, fill=color, width=width, joint='curve')
        elif op['tool'] in ('arrow', 'rectangle', 'redact') and len(points) == 2:
            a, b = points
            box = (min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))
            if op['tool'] == 'redact':
                draw.rectangle(box, fill='black')
            elif op['tool'] == 'rectangle':
                draw.rectangle(box, outline=color, width=width)
            else:
                draw.line(points, fill=color, width=width)
                angle = math.atan2(b[1]-a[1], b[0]-a[0])
                head = 16 * (sx + sy) / 2
                draw.polygon([b, (b[0]-head*math.cos(angle-.5), b[1]-head*math.sin(angle-.5)),
                              (b[0]-head*math.cos(angle+.5), b[1]-head*math.sin(angle+.5))], fill=color)
        elif op['tool'] == 'text' and points:
            font = ImageFont.truetype('DejaVuSans.ttf', max(1, round(22 * sy)))
            draw.text(points[0], op['text'], fill=color, font=font, anchor='lt')
    c = spec['crop']
    box = (max(0, round(c['x']*sx)), max(0, round(c['y']*sy)),
           min(image.width, round((c['x']+c['width'])*sx)),
           min(image.height, round((c['y']+c['height'])*sy)))
    if box[2] <= box[0] or box[3] <= box[1]:
        raise ValueError('Select a non-empty area first')
    return image.crop(box)


def capture(mode):
    runtime = Path(os.environ['XDG_RUNTIME_DIR']) / 'enclosure-screenshots'
    runtime.mkdir(mode=0o700, exist_ok=True)
    # Clean abandoned captures after a day, never another active session.
    for old in runtime.iterdir():
        if old.is_dir() and time.time()-old.stat().st_mtime > 86400:
            shutil.rmtree(old)
    session = Path(tempfile.mkdtemp(dir=runtime))
    try:
        output = json.loads(subprocess.check_output(['niri', 'msg', '-j', 'focused-output']))
        path = session / 'source.png'
        if mode == 'window':
            subprocess.run(['niri', 'msg', 'action', 'screenshot-window', '--path', str(path)], check=True, stdout=subprocess.DEVNULL)
        else:
            subprocess.run(['grim', '-o', output['name'], str(path)], check=True)
        for _ in range(100):
            if path.exists():
                try:
                    with Image.open(path) as image:
                        image.load()
                    break
                except OSError:
                    pass
            time.sleep(.02)
        else:
            raise RuntimeError('The compositor did not finish the screenshot')
        return {'path': str(path), 'screen': output['name']}
    except Exception:
        shutil.rmtree(session)
        raise


def main():
    action = sys.argv[1]
    if action == 'capture':
        print(json.dumps(capture(sys.argv[2])))
    elif action == 'export':
        path = Path(sys.argv[2])
        spec = json.loads(sys.argv[3])
        with Image.open(path) as source:
            result = render(source, spec)
        export = path.parent / 'export.png'
        result.save(export)
        if sys.argv[4] == 'save':
            directory = Path.home() / 'Pictures/Screenshots'
            directory.mkdir(parents=True, exist_ok=True)
            dest = directory / ('Screenshot ' + time.strftime('%Y-%m-%d %H%M%S') + '-' + str(time.time_ns())[-6:] + '.png')
            shutil.copyfile(export, dest)
            print(str(dest))
        else:
            with export.open('rb') as data:
                subprocess.run(['wl-copy', '--type', 'image/png'], stdin=data, check=True)
            print('Screenshot copied')
    elif action == 'clean':
        path = Path(sys.argv[2])
        runtime = Path(os.environ['XDG_RUNTIME_DIR']) / 'enclosure-screenshots'
        if path.name == 'source.png' and path.parent.parent == runtime:
            shutil.rmtree(path.parent, ignore_errors=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
