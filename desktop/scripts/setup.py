#!/usr/bin/env python3
"""Plan an installation and render portable Niri monitor settings without changing the system."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GROUPS = json.loads((ROOT / 'packages/groups.json').read_text())
GRAPHICS = ('auto', 'keep', 'amd', 'intel', 'nvidia-open', 'nvidia-580', 'nouveau', 'mesa')
TRANSFORMS = ('normal', '90', '180', '270', 'flipped', 'flipped-90', 'flipped-180', 'flipped-270')
MODE = re.compile(r'([1-9][0-9]{1,4})x([1-9][0-9]{1,4})(?:@([1-9][0-9]{0,3}(?:\.[0-9]{1,3})?))?')
PACKAGE = re.compile(r'[a-zA-Z0-9@_+][a-zA-Z0-9@_+.-]*')
PRIME = '''#!/usr/bin/env bash
# Launch an application on the NVIDIA GPU; keep the desktop's default GPU unchanged.
exec env __NV_PRIME_RENDER_OFFLOAD=1 __GLX_VENDOR_LIBRARY_NAME=nvidia __VK_LAYER_NV_optimus=NVIDIA_only "$@"
'''


def run(args):
    try:
        result = subprocess.run(args, text=True, capture_output=True, timeout=3)
        return result.stdout if result.returncode == 0 else ''
    except (OSError, subprocess.TimeoutExpired):
        return ''


def detect():
    cpuinfo = Path('/proc/cpuinfo').read_text() if Path('/proc/cpuinfo').exists() else ''
    cpu = 'intel' if 'GenuineIntel' in cpuinfo else 'amd' if 'AuthenticAMD' in cpuinfo else 'unknown'
    vendors = set()
    for device in Path('/sys/bus/pci/devices').glob('*'):
        try:
            if (device / 'class').read_text().strip().startswith('0x03'):
                vendor = {'0x8086': 'intel', '0x1002': 'amd', '0x10de': 'nvidia'}.get((device / 'vendor').read_text().strip())
                if vendor:
                    vendors.add(vendor)
        except OSError:
            pass
    descriptions = [line for line in run(['lspci', '-nn']).splitlines()
                    if any(kind in line.lower() for kind in ('vga compatible', '3d controller', 'display controller'))]
    installed = run(['pacman', '-Qq']).splitlines()
    kernels = sorted(set(installed) & {'linux', 'linux-lts', 'linux-zen', 'linux-hardened'})
    for pkgbase in Path('/usr/lib/modules').glob('*/pkgbase'):
        try:
            kernel = pkgbase.read_text().strip()
            if PACKAGE.fullmatch(kernel) and kernel not in kernels:
                kernels.append(kernel)
        except OSError:
            pass
    outputs = []
    try:
        data = json.loads(run(['niri', 'msg', '--json', 'outputs']) or '{}')
        for name, output in data.items():
            modes = [f'{m["width"]}x{m["height"]}@{m["refresh_rate"]/1000:.3f}' for m in output.get('modes', [])]
            outputs.append({'name': name, 'modes': list(dict.fromkeys(modes))})
    except (ValueError, TypeError, KeyError):
        outputs = []
    if not outputs:
        for path in sorted(Path('/sys/class/drm').glob('card*-*')):
            try:
                if (path / 'status').read_text().strip() != 'connected':
                    continue
                name = re.sub(r'^card[0-9]+-', '', path.name)
                modes = [m for m in (path / 'modes').read_text().splitlines() if MODE.fullmatch(m)]
                if name not in {o['name'] for o in outputs}:
                    outputs.append({'name': name, 'modes': list(dict.fromkeys(modes))})
            except OSError:
                pass
    return {'cpu': cpu, 'gpus': sorted(vendors), 'gpu_descriptions': descriptions,
            'kernels': sorted(kernels), 'installed': installed, 'outputs': outputs,
            'mkinitcpio': bool(shutil.which('mkinitcpio'))}


def normalize_monitors(config):
    if not isinstance(config, dict) or set(config) - {'layout', 'outputs'}:
        raise ValueError('Monitor configuration must contain layout and outputs only')
    layout = config.get('layout', 'auto')
    if layout not in ('auto', 'horizontal', 'vertical', 'manual'):
        raise ValueError('Monitor layout must be auto, horizontal, vertical or manual')
    raw = config.get('outputs', [])
    if not isinstance(raw, list) or len(raw) > 16:
        raise ValueError('outputs must be a list of up to 16 monitors')
    outputs, names = [], set()
    allowed = {'name', 'enabled', 'mode', 'scale', 'transform', 'position', 'primary', 'preferred_mode'}
    for item in raw:
        if not isinstance(item, dict) or set(item) - allowed:
            raise ValueError('Unknown monitor field')
        name = item.get('name', '')
        if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,128}', name) or name in names:
            raise ValueError('Each monitor needs a unique connector name such as eDP-1 or HDMI-A-1')
        names.add(name)
        enabled = item.get('enabled', True)
        primary = item.get('primary', False)
        if type(enabled) is not bool or type(primary) is not bool:
            raise ValueError('enabled and primary must be booleans')
        mode = item.get('mode', 'auto')
        preferred = item.get('preferred_mode', '')
        if not isinstance(mode, str) or (mode != 'auto' and not MODE.fullmatch(mode)):
            raise ValueError('Mode must be auto or WIDTHxHEIGHT[@REFRESH], such as 1920x1080@144')
        if not isinstance(preferred, str) or (preferred and not MODE.fullmatch(preferred)):
            raise ValueError('Invalid preferred monitor mode')
        scale = item.get('scale', 1)
        if type(scale) not in (int, float) or not math.isfinite(scale) or not 0 < scale <= 10:
            raise ValueError('Monitor scale must be greater than 0 and at most 10')
        transform = item.get('transform', 'normal')
        if transform not in TRANSFORMS:
            raise ValueError('Invalid monitor rotation/transform')
        pos = item.get('position')
        if pos is not None and (not isinstance(pos, dict) or set(pos) != {'x', 'y'} or
                                any(type(v) is not int or abs(v) > 100000 for v in pos.values())):
            raise ValueError('Monitor position must contain integer x and y coordinates')
        if primary and not enabled:
            raise ValueError('The startup monitor must be enabled')
        outputs.append(dict(name=name, enabled=enabled, mode=mode, scale=scale,
                            transform=transform, primary=primary, preferred_mode=preferred, position=pos))
    enabled = [o for o in outputs if o['enabled']]
    if outputs and not enabled:
        raise ValueError('At least one monitor must stay enabled')
    if sum(o['primary'] for o in outputs) > 1:
        raise ValueError('Choose only one startup monitor')
    if enabled and not any(o['primary'] for o in enabled):
        enabled[0]['primary'] = True
    cursor = 0
    for output in enabled:
        if layout in ('horizontal', 'vertical'):
            dimensions = MODE.fullmatch(output['mode'] if output['mode'] != 'auto' else output['preferred_mode'])
            if not dimensions:
                raise ValueError('Automatic rows/columns need known resolutions. Choose a mode or use automatic/manual positioning.')
            width, height = map(int, dimensions.group(1, 2))
            if output['transform'] in ('90', '270', 'flipped-90', 'flipped-270'):
                width, height = height, width
            output['position'] = {'x': cursor if layout == 'horizontal' else 0,
                                  'y': cursor if layout == 'vertical' else 0}
            cursor += math.ceil((width if layout == 'horizontal' else height) / output['scale'])
        elif layout == 'auto':
            output['position'] = None
    if layout == 'manual':
        rectangles = []
        for output in enabled:
            dimensions = MODE.fullmatch(output['mode'] if output['mode'] != 'auto' else output['preferred_mode'])
            if not dimensions or output['position'] is None:
                continue
            w, h = map(int, dimensions.group(1, 2))
            if output['transform'] in ('90', '270', 'flipped-90', 'flipped-270'):
                w, h = h, w
            x, y = output['position']['x'], output['position']['y']
            rect = (x, y, x + math.ceil(w / output['scale']), y + math.ceil(h / output['scale']))
            for name, other in rectangles:
                if max(x, other[0]) < min(rect[2], other[2]) and max(y, other[1]) < min(rect[3], other[3]):
                    raise ValueError(f'Monitor positions overlap: {name} and {output["name"]}')
            rectangles.append((output['name'], rect))
    return {'layout': layout, 'outputs': outputs}


def render_monitors(config):
    config = normalize_monitors(config)
    lines = ['// Monitor settings selected by the rebos installer.']
    for o in config['outputs']:
        lines.append(f'output {json.dumps(o["name"])} {{')
        if not o['enabled']:
            lines.append('    off')
        else:
            if o['mode'] != 'auto':
                lines.append(f'    mode {json.dumps(o["mode"])}')
            lines += [f'    scale {o["scale"]:g}', f'    transform {json.dumps(o["transform"])}']
            if o['position'] is not None:
                lines.append(f'    position x={o["position"]["x"]} y={o["position"]["y"]}')
            if o['primary']:
                lines.append('    focus-at-startup')
        lines.append('}')
    return '\n'.join(lines) + '\n'


def packages_from(path):
    return [line.split('#')[0].strip() for line in path.read_text().splitlines() if line.split('#')[0].strip()]


def build_plan(options, hardware):
    groups = list(GROUPS) if options.groups == 'all' or (options.groups is None and options.profile == 'full') else []
    if options.groups not in (None, 'all', 'none', ''):
        groups = list(dict.fromkeys(options.groups.split(',')))
    if set(groups) - set(GROUPS):
        raise ValueError('Unknown application group. Choose: ' + ','.join(GROUPS))
    graphics = options.graphics
    if options.early_kms and graphics not in ('nvidia-open', 'nvidia-580'):
        raise ValueError('Early NVIDIA KMS requires an NVIDIA driver choice')
    if options.early_kms and not hardware['mkinitcpio']:
        raise ValueError('Early KMS setup currently supports mkinitcpio only; leave it off for other initramfs generators')
    repo = packages_from(ROOT / 'packages/core.txt')
    aur = []
    for group in groups:
        repo += GROUPS[group]['repo']
        if not options.no_aur:
            aur += GROUPS[group]['aur']
    if options.login == 'keep':
        repo = [p for p in repo if p != 'ly']
    if options.no_bluetooth:
        repo = [p for p in repo if p not in ('bluez', 'bluez-utils', 'blueman')]
    if options.no_power:
        repo = [p for p in repo if p != 'power-profiles-daemon']
    microcode = hardware['cpu'] if options.microcode == 'auto' else options.microcode
    if microcode in ('amd', 'intel'):
        repo.append(microcode + '-ucode')
    vendors = hardware['gpus'] if graphics in ('auto', 'nvidia-open', 'nvidia-580') else [graphics]
    if 'amd' in vendors:
        repo += ['vulkan-radeon', 'libva-mesa-driver']
    if 'intel' in vendors:
        repo += ['vulkan-intel', 'intel-media-driver']
    headers = []
    if graphics in ('nvidia-open', 'nvidia-580'):
        headers = options.kernel_headers.split(',') if options.kernel_headers else [k + '-headers' for k in hardware['kernels']]
        if not headers or any(not PACKAGE.fullmatch(p) or not p.endswith('-headers') for p in headers):
            raise ValueError('NVIDIA DKMS needs kernel headers; supply --kernel-headers linux-headers (or your kernel equivalent)')
        repo += ['dkms', *headers]
        if graphics == 'nvidia-open':
            repo += ['nvidia-open-dkms', 'nvidia-utils', 'nvidia-settings']
        else:
            if options.no_aur:
                raise ValueError('NVIDIA 580 uses AUR packages; enable AUR or choose another graphics option')
            aur += ['nvidia-580xx-dkms', 'nvidia-580xx-utils', 'nvidia-580xx-settings']
    monitors = normalize_monitors(options.monitor_config)
    hybrid = options.hybrid if options.hybrid is not None else (
        graphics in ('nvidia-open', 'nvidia-580') and 'nvidia' in hardware['gpus'] and len(hardware['gpus']) > 1)
    if hybrid and graphics not in ('nvidia-open', 'nvidia-580', 'keep', 'auto'):
        raise ValueError('NVIDIA offload requires an NVIDIA driver selection or an existing NVIDIA setup')
    return {'version': 1, 'profile': options.profile, 'groups': groups,
            'graphics': graphics, 'microcode': options.microcode,
            'hybrid': hybrid,
            'early_kms': options.early_kms, 'kernel_headers': headers,
            'login': options.login, 'network': options.network,
            'bluetooth': not options.no_bluetooth, 'power': not options.no_power,
            'files_only': options.files_only, 'monitors': monitors,
            'packages': sorted(set(repo)), 'aur_packages': sorted(set(aur)),
            'hardware': {key: value for key, value in hardware.items() if key != 'installed'}}


def validate_plan(plan):
    if not isinstance(plan, dict) or plan.get('version') != 1 or plan.get('graphics') not in GRAPHICS:
        raise ValueError('Invalid installer settings')
    for key in ('hybrid', 'early_kms', 'bluetooth', 'power', 'files_only'):
        if type(plan.get(key)) is not bool:
            raise ValueError(f'Invalid setting: {key}')
    if plan.get('login') not in ('ly', 'keep') or plan.get('network') not in ('networkmanager', 'keep'):
        raise ValueError('Invalid service choices')
    for key in ('packages', 'aur_packages', 'kernel_headers'):
        if not isinstance(plan.get(key), list) or any(not isinstance(p, str) or not PACKAGE.fullmatch(p) for p in plan[key]):
            raise ValueError(f'Invalid package list: {key}')
    plan['monitors'] = normalize_monitors(plan.get('monitors', {}))
    return plan


def driver_conflicts(plan, installed):
    modules = {p for p in installed if p in ('nvidia', 'nvidia-dkms', 'nvidia-lts', 'nvidia-open',
               'nvidia-open-lts', 'nvidia-open-dkms') or re.fullmatch(r'nvidia-[0-9]+xx-dkms', p)}
    desired = {'nvidia-open': 'nvidia-open-dkms', 'nvidia-580': 'nvidia-580xx-dkms'}.get(plan['graphics'])
    conflict = modules - {desired} if desired else modules if plan['graphics'] == 'nouveau' else set()
    if plan['graphics'] == 'nvidia-open':
        conflict |= {p for p in installed if re.fullmatch(r'nvidia-[0-9]+xx-utils', p)}
    elif plan['graphics'] == 'nvidia-580' and 'nvidia-utils' in installed:
        conflict.add('nvidia-utils')
    elif plan['graphics'] == 'nouveau':
        conflict |= {p for p in installed if p == 'nvidia-utils' or re.fullmatch(r'nvidia-[0-9]+xx-utils', p)}
    if conflict:
        raise ValueError('Existing NVIDIA driver packages conflict with this choice: ' + ', '.join(sorted(conflict)) +
                         '. Choose keep, or explicitly replace the old driver before rerunning. No packages were removed.')


def ask(prompt, default=''):
    suffix = f' [{default}]' if default != '' else ''
    print(prompt + suffix + ': ', end='', file=sys.stderr, flush=True)
    value = sys.stdin.readline()
    if not value:
        raise ValueError('Setup cancelled: terminal input ended')
    value = value.strip()
    if value.lower() in ('q', 'quit'):
        raise ValueError('Setup cancelled')
    return value or str(default)


def choice(prompt, values, default):
    print('\n' + prompt, file=sys.stderr)
    for i, (key, label) in enumerate(values, 1):
        print(f'  {i}) {label}', file=sys.stderr)
    default_number = next(i for i, (key, _) in enumerate(values, 1) if key == default)
    while True:
        value = ask('Choose a number (q cancels)', default_number)
        if value.isdigit() and 1 <= int(value) <= len(values):
            return values[int(value) - 1][0]
        print('Enter one of the listed numbers.', file=sys.stderr)


def yes(prompt, default=True):
    while True:
        value = ask(prompt + ' (y/n)', 'y' if default else 'n').lower()
        if value in ('yes', 'y', 'no', 'n'):
            return value in ('yes', 'y')
        print('Enter y or n.', file=sys.stderr)


def monitor_wizard(hardware):
    method = choice('Monitor setup', [('auto', 'Automatic display modes and placement'),
                                     ('configure', 'Configure connected monitors or enter connectors manually')], 'auto')
    if method == 'auto':
        return {'layout': 'auto', 'outputs': []}
    detected = hardware['outputs']
    print('Detected: ' + (', '.join(o['name'] for o in detected) or 'none (you may enter connector names manually)'), file=sys.stderr)
    names = ask('Connector names, in desired left-to-right/top-to-bottom order', ','.join(o['name'] for o in detected))
    outputs = []
    for name in filter(None, (n.strip() for n in names.split(','))):
        known = next((o for o in detected if o['name'] == name), {'modes': []})
        print(f'\nConfigure {name}', file=sys.stderr)
        enabled = yes('Enable this monitor?', True)
        output = dict(name=name, enabled=enabled)
        if enabled:
            print('Detected modes: ' + (', '.join(known['modes']) or 'unavailable'), file=sys.stderr)
            while True:
                output['mode'] = ask('Mode: auto or WIDTHxHEIGHT@REFRESH', 'auto')
                if output['mode'] == 'auto' or MODE.fullmatch(output['mode']):
                    break
                print('Use e.g. 1920x1080@144 or auto.', file=sys.stderr)
            output['preferred_mode'] = known['modes'][0] if known['modes'] else ''
            while True:
                try:
                    output['scale'] = float(ask('Scale (1=100%, 1.5=150%, 2=200%)', '1'))
                    if 0 < output['scale'] <= 10:
                        break
                except ValueError:
                    pass
                print('Use a number greater than 0 and at most 10.', file=sys.stderr)
            output['transform'] = choice('Rotation', [(t, t) for t in TRANSFORMS], 'normal')
        outputs.append(output)
    if not outputs or not any(o['enabled'] for o in outputs):
        raise ValueError('Monitor setup needs at least one enabled monitor')
    layout = choice('Monitor placement', [('auto', 'Automatic placement'), ('horizontal', 'Side by side in the entered order'),
                                         ('vertical', 'Stacked in the entered order'), ('manual', 'Enter logical x/y coordinates')], 'auto')
    enabled = [o for o in outputs if o['enabled']]
    if layout == 'manual':
        for output in enabled:
            while True:
                try:
                    x, y = map(int, ask(f'{output["name"]} position: x,y', '0,0').split(','))
                    output['position'] = {'x': x, 'y': y}
                    break
                except ValueError:
                    print('Enter two integers separated by a comma.', file=sys.stderr)
    primary = choice('Monitor focused at login', [(o['name'], o['name']) for o in enabled], enabled[0]['name'])
    for output in outputs:
        output['primary'] = output['name'] == primary
    return normalize_monitors({'layout': layout, 'outputs': outputs})


def wizard(options, hardware):
    print('\nrebos desktop setup — enter q at any prompt to cancel.\nCPU: ' + hardware['cpu'] +
          '\nGraphics: ' + (', '.join(hardware['gpus']) or 'unknown / virtual') +
          '\nKernels: ' + (', '.join(hardware['kernels']) or 'unknown'), file=sys.stderr)
    for line in hardware['gpu_descriptions']:
        print('  ' + line, file=sys.stderr)
    options.profile = choice('Installation profile', [('full', 'Full desktop and optional application groups'),
                                                      ('core', 'Core desktop, Firefox and Neovim')], options.profile)
    print('\nApplication groups (Firefox, Kitty and Neovim are always included):', file=sys.stderr)
    keys = list(GROUPS)
    for i, key in enumerate(keys, 1):
        print(f'  {i}) {GROUPS[key]["label"]}', file=sys.stderr)
    default = options.groups if options.groups is not None else 'all' if options.profile == 'full' else 'none'
    while True:
        selected = ask('Choose comma-separated numbers, all, or none', default)
        if selected in ('all', 'none'):
            options.groups = selected
            break
        if selected in GROUPS or set(selected.split(',')) <= set(GROUPS):
            options.groups = selected
            break
        try:
            indexes = [int(n.strip()) for n in selected.split(',')]
            if indexes and all(1 <= n <= len(keys) for n in indexes):
                options.groups = ','.join(keys[n - 1] for n in indexes)
                break
        except ValueError:
            pass
        print('Use group numbers such as 1,3,6 or all/none.', file=sys.stderr)
    options.no_aur = not yes('Allow reviewed AUR builds for selected apps/drivers?', not options.no_aur)
    options.graphics = choice('Graphics driver setup', [
        ('auto', 'Detect Intel/AMD packages; preserve NVIDIA driver selection'),
        ('keep', 'Keep the existing graphics driver setup'), ('amd', 'AMD Mesa/Vulkan'),
        ('intel', 'Intel Mesa/Vulkan'), ('nvidia-open', 'NVIDIA open DKMS — Turing/GTX 16/RTX 20 and newer'),
        ('nvidia-580', 'NVIDIA proprietary 580 DKMS — Maxwell/Pascal/Volta (AUR)'),
        ('nouveau', 'Nouveau/Mesa — use the kernel open driver'), ('mesa', 'Virtual machine / base Mesa only')], options.graphics)
    if options.graphics in ('nvidia-open', 'nvidia-580'):
        options.hybrid = yes('Add rebos-prime-run for hybrid NVIDIA offload?', len(hardware['gpus']) > 1)
        if hardware['mkinitcpio']:
            options.early_kms = yes('Load NVIDIA modules early with mkinitcpio?', options.early_kms)
        if not hardware['kernels'] and not options.kernel_headers:
            options.kernel_headers = ask('Required kernel header packages, comma-separated')
    options.microcode = choice('CPU microcode', [('auto', 'Detect CPU vendor automatically'), ('keep', 'Keep current microcode'),
                                               ('amd', 'AMD microcode'), ('intel', 'Intel microcode')], options.microcode)
    options.monitor_config = monitor_wizard(hardware)
    if not options.files_only:
        options.login = choice('Login manager', [('ly', 'Install/configure animated Ly on tty2'), ('keep', 'Keep current login setup')], options.login)
        options.network = choice('Network setup', [('networkmanager', 'Enable NetworkManager at next boot'), ('keep', 'Keep existing network services')], options.network)
        options.no_bluetooth = not yes('Install/configure Bluetooth?', not options.no_bluetooth)
        options.no_power = not yes('Install/configure power profiles?', not options.no_power)
    return options


def customize_niri(directory, plan):
    directory = Path(directory)
    config = directory / 'config.kdl'
    content = config.read_text()
    include = 'include "monitors.kdl"'
    if include not in content:
        config.write_text(content.rstrip() + '\n\n' + include + '\n')
    (directory / 'monitors.kdl').write_text(render_monitors(plan['monitors']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('plan')
    p.add_argument('--interactive', action='store_true')
    p.add_argument('--profile', choices=('core', 'full'), default='full')
    p.add_argument('--groups', help='all, none, or comma-separated group IDs')
    p.add_argument('--graphics', choices=GRAPHICS, default='auto')
    p.add_argument('--microcode', choices=('auto', 'keep', 'amd', 'intel'), default='auto')
    p.add_argument('--kernel-headers')
    p.add_argument('--monitors', type=Path)
    p.add_argument('--login', choices=('ly', 'keep'), default='ly')
    p.add_argument('--network', choices=('networkmanager', 'keep'), default='networkmanager')
    p.add_argument('--no-aur', action='store_true')
    p.add_argument('--no-bluetooth', action='store_true')
    p.add_argument('--no-power', action='store_true')
    p.add_argument('--early-kms', action='store_true')
    p.add_argument('--hybrid', action=argparse.BooleanOptionalAction, default=None)
    p.add_argument('--files-only', action='store_true')
    p = sub.add_parser('get')
    p.add_argument('keys', nargs='+')
    p = sub.add_parser('render')
    p.add_argument('directory', type=Path)
    sub.add_parser('check-drivers')
    sub.add_parser('summary')
    args = parser.parse_args()
    if args.command == 'plan':
        hardware = detect()
        args.monitor_config = json.loads(args.monitors.read_text()) if args.monitors else {'layout': 'auto', 'outputs': []}
        if args.interactive:
            if not sys.stdin.isatty():
                raise ValueError('Interactive setup needs a terminal')
            args = wizard(args, hardware)
        print(json.dumps(validate_plan(build_plan(args, hardware))))
        return
    plan = validate_plan(json.load(sys.stdin))
    if args.command == 'get':
        for key in args.keys:
            value = plan[key]
            for item in value if isinstance(value, list) else [value]:
                print(int(item) if isinstance(item, bool) else item)
    elif args.command == 'render':
        customize_niri(args.directory, plan)
    elif args.command == 'check-drivers':
        driver_conflicts(plan, run(['pacman', '-Qq']).splitlines())
    else:
        print('\nrebos desktop installation plan')
        print(f'Profile: {plan["profile"]} | Groups: {", ".join(plan["groups"]) or "none"}')
        print(f'Graphics: {plan["graphics"]} | CPU microcode: {plan["microcode"]} | Hybrid offload: {plan["hybrid"]} | Early KMS: {plan["early_kms"]}')
        print(f'Login: {plan["login"]} | Network: {plan["network"]} | Bluetooth: {plan["bluetooth"]} | Power profiles: {plan["power"]}')
        print('Monitors: ' + (f'{plan["monitors"]["layout"]} — ' + ', '.join(o['name'] for o in plan['monitors']['outputs']) if plan['monitors']['outputs'] else 'automatic modes and placement'))
        print(render_monitors(plan['monitors']), end='')
        if plan['files_only']:
            print('Files only: package and system service changes are skipped.')
        else:
            print('Official packages: ' + ' '.join(plan['packages']))
            print('AUR packages: ' + (' '.join(plan['aur_packages']) or 'none'))
        if plan['graphics'] == 'auto' and 'nvidia' in plan['hardware']['gpus']:
            print('NVIDIA detected: automatic mode preserves its driver choice; use the menu to select an NVIDIA driver.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f'Setup error: {error}', file=sys.stderr)
        sys.exit(1)
    except (KeyboardInterrupt, EOFError):
        print('\nSetup cancelled.', file=sys.stderr)
        sys.exit(130)
