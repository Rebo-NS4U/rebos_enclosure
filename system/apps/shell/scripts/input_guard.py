#!/usr/bin/env python3
"""Session-only evdev input toggles; closing the helper releases every grab."""
import fcntl
import json
import os
from pathlib import Path
import select
import sys

EVIOCGRAB = 0x40044590


def devices():
    result = {"keyboard": [], "touchscreen": []}
    for path in Path('/dev/input').glob('event*'):
        stat = path.stat()
        data = Path(f'/run/udev/data/c{os.major(stat.st_rdev)}:{os.minor(stat.st_rdev)}')
        try:
            properties = data.read_text().splitlines()
        except OSError:
            continue
        for kind, key in (("keyboard", "ID_INPUT_KEYBOARD"), ("touchscreen", "ID_INPUT_TOUCHSCREEN")):
            if f'E:{key}=1' in properties:
                result[kind].append(str(path))
    return result


class Guard:
    def __init__(self):
        self.handles = []
        self.disabled = None
        self.error = ''

    def restore(self):
        for fd in self.handles:
            os.close(fd)  # Kernel releases EVIOCGRAB even after a crash.
        self.handles = []
        self.disabled = None

    def toggle(self, kind, found):
        self.error = ''
        if kind == self.disabled:
            self.restore()
            return
        if kind not in found:
            return
        other = 'touchscreen' if kind == 'keyboard' else 'keyboard'
        if (self.disabled or not found[kind] or not found[other]
                or set(found[kind]) & set(found[other])):
            self.error = 'Keep the other input enabled and connected first.'
            return
        try:
            # Check that the fallback devices are accessible to this session.
            for path in found[other]:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
                os.close(fd)
            for path in found[kind]:
                fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
                self.handles.append(fd)
                fcntl.ioctl(fd, EVIOCGRAB, 1)
            self.disabled = kind
        except OSError as error:
            self.restore()
            self.error = f'Input control unavailable: {error.strerror}'

    def state(self, found):
        if self.disabled:
            other = 'touchscreen' if self.disabled == 'keyboard' else 'keyboard'
            if not found[other]:
                self.restore()
        return dict(disabled=self.disabled or '', keyboard=bool(found['keyboard']),
                    touchscreen=bool(found['touchscreen']), error=self.error)


def main():
    guard = Guard()
    try:
        while True:
            found = devices()
            print(json.dumps(guard.state(found)), flush=True)
            if select.select([sys.stdin], [], [], 1)[0]:
                line = sys.stdin.readline()
                if not line:
                    break
                guard.toggle(line.strip(), devices())
    finally:
        guard.restore()


if __name__ == '__main__':
    main()
