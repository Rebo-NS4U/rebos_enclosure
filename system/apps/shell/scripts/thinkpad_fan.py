#!/usr/bin/python3
"""Read ThinkPad telemetry and apply explicit, approved fan operations."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

FAN = Path('/proc/acpi/ibm/fan')
CONTROL = Path('/sys/module/thinkpad_acpi/parameters/fan_control')


def status():
    values = dict(line.split(':', 1) for line in FAN.read_text().splitlines() if ':' in line)
    return {key: values.get(key, '').strip() for key in ('status', 'speed', 'level')}


def apply(mode):
    if mode not in ('off', 'auto'):
        raise ValueError('Unknown fan operation')
    if CONTROL.read_text().strip() not in ('Y', '1'):
        if mode == 'auto':
            if status()['level'] == 'auto':
                return
            raise RuntimeError('Manual control is unavailable; cannot restore automatic mode.')
        subprocess.run(['modprobe', '-r', 'thinkpad_acpi'], check=True)
        try:
            subprocess.run(['modprobe', 'thinkpad_acpi', 'fan_control=1'], check=True)
        except subprocess.CalledProcessError:
            subprocess.run(['modprobe', 'thinkpad_acpi'], check=False)
            raise
    FAN.write_text('level ' + ('0' if mode == 'off' else 'auto') + '\n')
    expected = '0' if mode == 'off' else 'auto'
    if status()['level'] != expected:
        raise RuntimeError('The driver did not accept the requested fan mode.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['status', 'off', 'auto'])
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        if args.mode == 'status':
            print(json.dumps(status()))
        elif args.apply:
            apply(args.mode)
            print('Stop requested. Checking live RPM.' if args.mode == 'off' else 'Automatic cooling restored.')
        else:
            helper = Path.home() / '.local/bin/assistant-sudo'
            result = subprocess.run([str(helper), '--reason',
                'Stop ThinkPad fans for this session' if args.mode == 'off' else 'Restore ThinkPad automatic cooling',
                '--', '/usr/bin/python3', str(Path(__file__).resolve()), args.mode, '--apply'])
            return result.returncode
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
