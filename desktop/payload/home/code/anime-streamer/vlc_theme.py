"""Use the shell's Qt 5 colors with dark hover hints, only inside VLC."""
import configparser
import os
from pathlib import Path
import re


def parser():
    config = configparser.ConfigParser(interpolation=None)
    config.optionxform = str
    return config


def vlc_environment():
    home = Path.home()
    source = parser()
    source.read(home / '.config/qt5ct/qt5ct.conf')
    palette = parser()
    palette.read(source.get('Appearance', 'color_scheme_path', fallback=str(home / '.config/qt5ct/colors/rebos_shell.conf')))
    defaults = ['#dee4e0', '#202825', '#3a4540', '#303b35', '#38564e', '#28332d',
                '#dee4e0', '#ffffff', '#dee4e0', '#141a18', '#181f1b', '#0a0b0b',
                '#8bbda5', '#101a14', '#8bbda5', '#a4b4ac', '#202825', '#101512',
                '#141a18', '#dee4e0', '#808b84', '#8bbda5']
    if not palette.has_section('ColorScheme'):
        palette.add_section('ColorScheme')
    for group in ('active_colors', 'inactive_colors', 'disabled_colors'):
        colors = [value.strip() for value in palette.get('ColorScheme', group, fallback='').split(',')]
        if len(colors) < 20 or any(not re.fullmatch(r'#[a-fA-F0-9]{6}(?:[a-fA-F0-9]{2})?', value) for value in colors):
            colors = defaults.copy()
        colors[18], colors[19] = colors[9], colors[6]  # ToolTipBase, ToolTipText
        palette.set('ColorScheme', group, ', '.join(colors))
    root = home / '.config/anime-streamer/vlc-qt'
    target = root / 'qt5ct'
    target.mkdir(parents=True, exist_ok=True)
    scheme = target / 'colors.conf'
    with scheme.open('w') as output:
        palette.write(output)
    colors = [value.strip() for value in palette.get('ColorScheme', 'active_colors').split(',')]
    def rgb(value):
        return '#' + value[-6:]
    stylesheet = target / 'hover.qss'
    stylesheet.write_text(f'''
QToolTip {{ background-color: {rgb(colors[18])}; color: {rgb(colors[19])}; border: 1px solid {rgb(colors[4])}; border-radius: 6px; padding: 6px 8px; }}
QMenuBar, QStatusBar, QToolBar {{ background: {rgb(colors[10])}; color: {rgb(colors[0])}; border: none; }}
QToolButton {{ padding: 6px; border: 1px solid transparent; border-radius: 6px; }}
QToolButton:hover, QToolButton:focus {{ background: {rgb(colors[1])}; border-color: {rgb(colors[4])}; }}
QToolButton:checked {{ background: {rgb(colors[12])}; color: {rgb(colors[13])}; }}
QMenu {{ background: {rgb(colors[9])}; color: {rgb(colors[6])}; border: 1px solid {rgb(colors[4])}; padding: 4px; }}
QMenu::item {{ padding: 6px 24px; }}
QMenu::item:selected {{ background: {rgb(colors[12])}; color: {rgb(colors[13])}; }}
''')
    for section in ('Appearance', 'Interface'):
        if not source.has_section(section):
            source.add_section(section)
    source.set('Appearance', 'custom_palette', 'true')
    source.set('Appearance', 'style', 'Fusion')
    source.set('Appearance', 'color_scheme_path', str(scheme))
    existing = source.get('Interface', 'stylesheets', fallback='')
    source.set('Interface', 'stylesheets', (existing + ', ' if existing and existing != '@Invalid()' else '') + str(stylesheet))
    with (target / 'qt5ct.conf').open('w') as output:
        source.write(output)
    environment = os.environ.copy()
    environment.update(QT_QPA_PLATFORMTHEME='qt5ct', QT_STYLE_OVERRIDE='Fusion', XDG_CONFIG_HOME=str(root),
                       XCURSOR_THEME='GoogleDot-Black', XCURSOR_SIZE='20')
    return environment
