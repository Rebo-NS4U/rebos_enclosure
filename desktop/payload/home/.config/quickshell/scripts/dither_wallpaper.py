#!/usr/bin/env python3
"""Create a cached, full-resolution dithered PNG without changing the source."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

VERSION = 3
STRENGTHS = {'normal': (24, 1), 'strong': (6, 2), 'intense': (4, 3)}


def convert(source: Path, cache: Path, palette: str = 'original', strength: str = 'strong') -> Path:
    from PIL import Image, ImageOps

    if strength not in STRENGTHS:
        raise ValueError('Unknown strength: ' + strength)
    color_count, pixel_size = STRENGTHS[strength]
    source = source.expanduser().resolve(strict=True)
    info = source.stat()
    key = hashlib.sha256(json.dumps([str(source), info.st_size, info.st_mtime_ns,
                                    palette, strength, VERSION]).encode()).hexdigest()
    cache = cache.expanduser().resolve()
    cache.mkdir(parents=True, exist_ok=True)
    output = cache / (key + '.png')
    if output.is_file():
        return output
    with Image.open(source) as raw:
        if getattr(raw, 'is_animated', False):
            raise ValueError('Choose a still image; animated wallpapers are kept unchanged.')
        image = ImageOps.exif_transpose(raw).convert('RGB')
    if palette == 'original':
        sample = image.copy()
        sample.thumbnail((512, 512))
        colors = sample.quantize(colors=color_count, method=Image.Quantize.MEDIANCUT)
        # An explicit palette enables error diffusion in the working image;
        # quantize(colors=N) alone does not produce this texture.
        entries = colors.getpalette()[:color_count * 3]
    elif palette == 'teal-orange':
        palette_colors = ('0b191a', '10363d', '135260', '137788',
                                  '05a3b5', '30cccf', '793f32', 'b3694b',
                                  'e59a72', 'ffd2a5', 'fff0d5', 'd0e7df')
        indices = {'normal': range(12), 'strong': (0, 2, 4, 7, 9, 10),
                   'intense': (0, 3, 8, 10)}[strength]
        entries = [v for index in indices for v in bytes.fromhex(palette_colors[index])]
    else:
        raise ValueError('Unknown palette: ' + palette)
    swatch = Image.new('P', (1, 1))
    # Repeat real entries so unused palette slots cannot introduce black.
    swatch.putpalette((entries * (768 // len(entries) + 1))[:768])
    original_size = image.size
    if pixel_size > 1:
        image = image.resize((max(1, (image.width + pixel_size - 1) // pixel_size),
                              max(1, (image.height + pixel_size - 1) // pixel_size)),
                             Image.Resampling.LANCZOS)
    result = image.quantize(palette=swatch, dither=Image.Dither.FLOYDSTEINBERG)
    if result.size != original_size:
        result = result.resize(original_size, Image.Resampling.NEAREST)
    fd, temporary = tempfile.mkstemp(prefix='.dither-', suffix='.png', dir=cache)
    try:
        with os.fdopen(fd, 'wb') as stream:
            result.save(stream, format='PNG', optimize=True)
        os.replace(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', type=Path)
    parser.add_argument('--palette', choices=['original', 'teal-orange'], default='original')
    parser.add_argument('--strength', choices=list(STRENGTHS), default='strong')
    parser.add_argument('--cache', type=Path, default=Path(os.environ.get(
        'XDG_CACHE_HOME', str(Path.home() / '.cache'))) / 'rebos_shell/dithered')
    args = parser.parse_args()
    try:
        print(json.dumps({'path': str(convert(args.image, args.cache, args.palette, args.strength))}))
        return 0
    except Exception as error:
        print(json.dumps({'error': str(error)}))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
