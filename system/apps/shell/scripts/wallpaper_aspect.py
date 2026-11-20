"""Read displayed wallpaper proportions without decoding a full-size frame."""
import json
import subprocess
import sys
from fractions import Fraction

from PIL import Image, UnidentifiedImageError


def display_aspect(path):
    try:
        with Image.open(path) as image:
            width, height = image.size
            if image.getexif().get(274) in (5, 6, 7, 8):
                return height / width
            return width / height
    except UnidentifiedImageError:
        pass

    result = subprocess.check_output([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
        "stream=width,height,display_aspect_ratio:stream_side_data=rotation",
        "-of", "json", path,
    ], timeout=5)
    stream = json.loads(result)["streams"][0]
    try:
        aspect = float(Fraction(stream["display_aspect_ratio"].replace(":", "/")))
    except (KeyError, ValueError, ZeroDivisionError):
        aspect = stream["width"] / stream["height"]
    if any(abs(item.get("rotation", 0)) % 180 == 90 for item in stream.get("side_data_list", [])):
        return 1 / aspect
    return aspect


if __name__ == "__main__":
    print(display_aspect(sys.argv[1]))
