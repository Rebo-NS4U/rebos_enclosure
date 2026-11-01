#!/usr/bin/env python3
"""Build the portable, explicitly selected desktop payload. Never copy a home wholesale."""
import argparse
import importlib.util
import hashlib
import json
from pathlib import Path
import shutil
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '__pycache__', '.ruff_cache', '.qmlls.ini', 'AGENTS.md', '.agents',
        '.sisyphus', 'fish_variables', 'config.local.fish'}


def ignore(directory, names):
    return [n for n in names if n in SKIP or n.startswith('.') or
            any(s in n.lower() for s in ('backup', '.bak', '.before-', '.log'))]


def build(home):
    payload = ROOT / 'payload'
    if payload.exists():
        raise SystemExit('payload already exists; move it aside before making a fresh snapshot')
    user = payload / 'home'
    units = []

    def copy(relative, source=None):
        source = source or home / relative
        if not source.exists():
            raise FileNotFoundError(source)
        target = user / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target, ignore=ignore)
        else:
            shutil.copy2(source, target)
        units.append(relative)

    def write(relative, content, mode=0o644):
        target = user / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
        target.chmod(mode)
        units.append(relative)

    # Source code and visual settings only; no shell state, histories, AI settings or accounts.
    for name in ('kitty', 'nvim', 'fuzzel', 'btop', 'qt5ct', 'qt6ct', 'themes'):
        copy('.config/' + name)
    for name in ('config.fish', 'conf.d', 'functions', 'completions'):
        if (home / '.config/fish' / name).exists():
            copy('.config/fish/' + name)
    for version in ('3.0', '4.0'):
        for name in ('settings.ini', 'gtk.css', 'colors.css'):
            path = f'.config/gtk-{version}/{name}'
            if (home / path).exists():
                copy(path)
    copy('.config/kdeglobals')
    # Flatten installed symlinks; never ship repository .git files or developer metadata.
    shell = home / '.config/quickshell'
    for name in ('assets', 'config', 'modules', 'scripts'):
        copy('.config/quickshell/' + name)
    for name in ('shell.qml', 'AnimeMenu.qml', 'FanShell.qml', 'cli.sh', 'version', 'LICENSE', 'README.md'):
        if (shell / name).exists():
            copy('.config/quickshell/' + name)
    # Keep the portable startup workaround versioned, independent of whether
    # the source desktop has installed the latest helper scripts yet.
    for name in ('qs-screen-guard', 'build_qt_screen_guard.sh',
                 'qt_screen_guard.cpp', 'test_qt_screen_guard.cpp'):
        shutil.copy2(ROOT.parent / '.config/quickshell/scripts' / name,
                     user / '.config/quickshell/scripts' / name)
    # The shell now launches these independent applications. Ship source only,
    # never account files, chat state, media history, downloaded models or captures.
    assistant = home / 'code/rebos-assistant'
    for name in ('assets', 'config', 'modules', 'scripts', 'shell.qml', 'version'):
        copy('code/rebos-assistant/' + name)
    for path in sorted((assistant / 'systemd').glob('*.service')):
        copy('.config/systemd/user/' + path.name, path)
    media = home / 'code/anime-streamer'
    for path in sorted(media.iterdir()):
        if path.is_file() and (path.suffix in {'.py', '.lua', '.cjs'} or path.name == 'filter_options.json'):
            if not path.name.startswith(('test_', 'check_')):
                copy('code/anime-streamer/' + path.name)
    copy('.config/systemd/user/anime-streamer.service')
    copy('.config/systemd/user/rebos-panel.service',
         ROOT.parent / '.config/systemd/user/rebos-panel.service')
    copy('.local/share/applications/rebos-assistant.desktop')
    copy('.local/bin/thinkpad-fan-control')
    copy('.local/share/applications/thinkpad-fan-control.desktop')
    write('.local/bin/assistant-sudo', '#!/bin/sh\nexec /usr/bin/python3 "$HOME/.config/quickshell/scripts/assistant_sudo.py" "$@"\n', 0o755)
    copy('.local/bin/config-browser')
    copy('.local/share/applications/config-browser.desktop')
    # Versioned install defaults also seed the bundled reset preset.
    preset = shell / 'assets/presets/rebos_shell Default'
    for name in ('bar', 'theme', 'performance', 'lockscreen', 'system'):
        source = ROOT / 'defaults' / f'{name}.json' if name in ('bar', 'theme') else preset / f'{name}.json'
        copy(f'.config/rebos_shell/config/{name}.json', source)
        if name in ('bar', 'theme'):
            shutil.copy2(source, user / '.config/quickshell/assets/presets/rebos_shell Default' / f'{name}.json')
    write('.config/rebos_shell/config/weather.json', '{"location": "", "unit": "C"}\n')
    for name in ('rice', 'rebos_shell', 'colorscheme', 'wallpaper', 'wallpaper-switcher',
                 'terminal-bonsai', 'project-picker', 'emoji-dmenu', 'wayland-screenshot',
                 'rebos-assistant', 'anime-streamer', 'ani-cli'):
        copy('.local/bin/' + name)
    shutil.copy2(ROOT.parent / '.local/bin/rice', user / '.local/bin/rice')
    for name in ('cbonsai.c', 'LICENSE', 'README.md', 'INSTALL.md'):
        copy('.local/share/cbonsai/' + name)
    copy('.local/share/fonts/rebos_shell')
    copy('.local/share/fonts/phosphor')
    copy('.local/share/icons/GoogleDot-Black')
    copy('.config/spicetify/Themes/rebos_shell')
    copy('.config/vesktop/themes/rebos_shell.css')
    for name in ('colors.json', 'effective-palette.json', 'fish.fish', 'fzf.conf',
                 'kitty.conf', 'niri-colors.kdl'):
        copy('.cache/rebos_shell/' + name)
    # Original rice wallpapers, the current Urban/Nature collection and selection.
    copy('.local/share/wallpapers/rebos', home / 'code/dots-niri/assets/wal')
    for name in ('Urban', 'Nature'):
        copy('.local/share/wallpapers/' + name)
    state = json.loads((home / '.cache/rebos_shell/wallpapers.json').read_text())
    current = Path(state['currentWall'])
    copy('.local/share/wallpapers/default' + current.suffix, current)
    state.update(currentWall='@HOME@/.local/share/wallpapers/default' + current.suffix,
                 wallPath='@HOME@/.local/share/wallpapers', perScreenWallpapers={})
    write('.cache/rebos_shell/wallpapers.json', json.dumps(state, indent=2) + '\n')

    profile = (home / '.config/niri/config-quickshell.kdl').read_text()
    # Ship versioned defaults rather than the source machine's personal chords.
    spec = importlib.util.spec_from_file_location('snapshot_binding_reader', shell / 'scripts/list_keybindings.py')
    binding_reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(binding_reader)
    matches = binding_reader.token_matches(profile)
    removals = []
    index = 0
    while index + 1 < len(matches):
        if matches[index].group() == 'binds' and matches[index + 1].group() == '{':
            start, depth = matches[index].start(), 1
            index += 2
            while index < len(matches) and depth:
                depth += (matches[index].group() == '{') - (matches[index].group() == '}')
                index += 1
            if depth:
                raise ValueError('Unclosed shortcut block in source profile')
            removals.append((start, matches[index - 1].end()))
        else:
            index += 1
    for start, end in reversed(removals):
        profile = profile[:start] + profile[end:]
    profile = '\n'.join(line for line in profile.splitlines()
                        if 'keybindings-personal' not in line and 'keybindings-defaults' not in line) + '\n'
    for application, extension in [('niri', 'kdl'), ('kitty', 'conf')]:
        filename = f'keybindings-defaults.{extension}'
        write(f'.config/{application}/{filename}', (ROOT / 'defaults' / filename).read_text())
        write(f'.config/{application}/keybindings-personal.{extension}', '// Personal shortcuts.\n' if extension == 'kdl' else '# Personal shortcuts.\n', 0o600)
    kitty = user / '.config/kitty/kitty.conf'
    kitty_lines = [line for line in kitty.read_text().splitlines()
                   if not line.lstrip().startswith('map ') and 'keybindings-personal' not in line and 'keybindings-defaults' not in line]
    kitty.write_text('\n'.join(kitty_lines).rstrip() + '\n\ninclude keybindings-defaults.conf\ninclude keybindings-personal.conf\n')
    # Use native monitor modes and normal power handling on other computers.
    import re
    profile = re.sub(r'^output "[^"]+" \{.*?^\}\n', '', profile, flags=re.M | re.S)
    profile = re.sub(r'^debug \{.*?^\}\n', '', profile, flags=re.M | re.S)
    profile = profile.replace('    disable-power-key-handling\n', '')
    # Keep essentials only; optional applications are launched explicitly by the user.
    profile = '\n'.join(line for line in profile.splitlines() if not line.startswith('spawn-at-startup ')) + '\n'
    profile = profile.replace('spawn "rsclip" "show"', 'spawn "rebos-clipboard"')
    profile = profile.replace('spawn "cider"', 'spawn "spotify-launcher"')
    profile = profile.replace('spawn "nautilus"', 'spawn "thunar"')
    profile = profile.replace('spawn "project-picker" "zed"', 'spawn "project-picker"')
    profile = profile.replace('XDG_MENU_PREFIX "arch-"',
                              'XDG_MENU_PREFIX "arch-"\n    PATH "@HOME@/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/bin"')
    profile += '\nspawn-at-startup "/usr/lib/polkit-gnome/polkit-gnome-authentication-agent-1"\n'
    profile += 'spawn-at-startup "sh" "-c" "exec udiskie --no-notify"\n'
    profile += 'spawn-at-startup "sh" "-c" "wl-paste --watch cliphist store"\n'
    write('.config/niri/config-quickshell.kdl', profile)
    write('.config/niri/config.kdl', '''// Portable rebos desktop profile.

// Keep overview activation explicit and hide the startup shortcut reminder.
gestures {
    hot-corners {
        off
    }
}

hotkey-overlay {
    skip-at-startup
}
include "config-quickshell.kdl"
include optional=true "~/.cache/rebos_shell/niri-blur.kdl"
layer-rule {
    match namespace="rebos_shell-anime"
    background-effect { blur false; }
}
include "keybindings-defaults.kdl"
include "keybindings-personal.kdl"
spawn-at-startup "sh" "-c" "exec \\"$HOME/.local/bin/rice\\" start"
cursor {
    xcursor-theme "GoogleDot-Black"
    xcursor-size 20
}
''')
    write('.config/environment.d/90-rebos-desktop.conf',
          'QT_QPA_PLATFORMTHEME=qt6ct\nPATH=${HOME}/.local/bin:${PATH}\n')
    write('.config/xdg-desktop-portal/niri-portals.conf',
          '[preferred]\ndefault=gnome;gtk;\norg.freedesktop.impl.portal.FileChooser=gtk\n')
    write('.local/bin/zen-browser', '''#!/usr/bin/env bash
set -euo pipefail
if command -v zen-browser-bin >/dev/null; then exec zen-browser-bin "$@"; fi
if [[ -x /usr/bin/zen-browser ]]; then exec /usr/bin/zen-browser "$@"; fi
if [[ -x /usr/bin/zen ]]; then exec /usr/bin/zen "$@"; fi
exec firefox "$@"
''', 0o755)
    write('.config/scripts/browser-app', '''#!/usr/bin/env bash
set -euo pipefail
exec xdg-open "${1:?A URL is required}"
''', 0o755)
    write('.local/bin/rebos-clipboard', '''#!/usr/bin/env bash
set -euo pipefail
selection=$(cliphist list | fuzzel --dmenu --prompt='Clipboard > ')
[[ -z $selection ]] || printf '%s' "$selection" | cliphist decode | wl-copy
''', 0o755)
    for name in ('install.sh', 'install-aur.sh', 'uninstall.sh', 'port-manager.sh',
                 'copy-latest-screenshot-path.sh', 'scale-adjust.sh'):
        copy('.config/scripts/' + name)
    write('.local/share/applications/rebos-shell-settings.desktop', '''[Desktop Entry]
Type=Application
Name=rebos_shell Settings
Exec=rebos_shell run settings
Icon=@HOME@/.config/quickshell/assets/rebos_shell/settings.svg
Categories=Settings;
''')
    write('.local/share/applications/wallpaper-switcher.desktop', '''[Desktop Entry]
Type=Application
Name=Wallpaper Switcher
Exec=wallpaper-switcher gui
Icon=preferences-desktop-wallpaper
Categories=Settings;
''')
    # Normalize usernames and original source paths in copied text, never in binary assets.
    text_suffixes = {'.json', '.kdl', '.conf', '.ini', '.css', '.qml', '.js', '.py',
                     '.sh', '.fish', '.lua', '.md', '.desktop', '.toml', '.service', '.cjs', ''}
    for path in user.rglob('*'):
        if path.is_file() and path.suffix in text_suffixes:
            try:
                content = path.read_text()
            except UnicodeError:
                continue
            content = content.replace(str(home / 'code/dots-niri'), '@HOME@')
            content = content.replace(str(home), '@HOME@')
            content = content.replace('gtk-cursor-theme-name=capitaine-cursors', 'gtk-cursor-theme-name=GoogleDot-Black')
            content = content.replace('font=Gabarito', 'font=JetBrains Mono')
            path.write_text(content)
    picker = user / '.local/bin/project-picker'
    content = picker.read_text().replace("\t\tzed) printf 'zed' ;;", "\t\tzed) printf 'zed' ;;\n\t\tnvim) printf 'nvim' ;;")
    content = content.replace("\tcommand -v zed >/dev/null 2>&1 && printf 'zed\\n'",
                              "\tcommand -v zed >/dev/null 2>&1 && printf 'zed\\n'\n\tcommand -v nvim >/dev/null 2>&1 && printf 'nvim\\n'\n\treturn 0")
    content = content.replace('if command -v code >/dev/null 2>&1; then next=code; else next=zed; fi',
                              'if command -v code >/dev/null 2>&1; then next=code; else next=nvim; fi')
    picker.write_text(content)
    system = payload / 'system/ly'
    system.mkdir(parents=True)
    for name in ('config.ini', 'blackhole-smooth-240x67.dur'):
        shutil.copy2(home / 'code/dots-niri/install/ly' / name, system / name)
    # Treat each dotfile component as one replacement, including symlinked installations.
    for component in ('.config/kitty', '.config/niri', '.config/fish', '.config/quickshell',
                      '.config/gtk-3.0', '.config/gtk-4.0'):
        units = [u for u in units if not u.startswith(component + '/')]
        if component not in units:
            units.append(component)
    manifest = {'created': datetime.now(timezone.utc).isoformat(),
                'description': 'Selected live desktop sources, sanitized portable snapshot',
                'shellVersion': (shell / 'version').read_text().strip(),
                'shellRepository': 'https://github.com/Rebo-NS4U/rebos_enclosure',
                'units': sorted(units)}
    (payload / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    hashes = {str(p.relative_to(payload)): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(payload.rglob('*')) if p.is_file()}
    (payload / 'checksums.json').write_text(json.dumps(hashes, indent=2) + '\n')
    print(f'Captured {len(hashes)} files in {payload}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--home', type=Path, default=Path.home())
    build(parser.parse_args().home.resolve())
