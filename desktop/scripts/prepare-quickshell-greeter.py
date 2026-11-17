#!/usr/bin/env python3
"""Assemble a greeter from portable source and the canonical shell renderer."""
import argparse
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]


def assemble(destination, root=ROOT):
    source = root / 'system/etc/rebos-greeter/quickshell'
    shell = root / 'system/apps/shell'
    shutil.copytree(source, destination, dirs_exist_ok=True)
    theme = destination / 'themes/enclosure/shell/modules'
    components = theme / 'components'
    components.mkdir(parents=True, exist_ok=True)
    for name in ('StyledRect.qml', 'StyledText.qml', 'ThemeButton.qml', 'SearchInput.qml', 'TintedWallpaper.qml'):
        shutil.copy2(shell / 'modules/components' / name, components)
    for shader in ('linear_gradient', 'radial_gradient', 'halftone', 'dither_fill'):
        for stage in ('vert', 'frag'):
            for suffix in ('', '.qsb'):
                name = f'{shader}.{stage}{suffix}'
                shutil.copy2(shell / 'modules/components' / name, components)
    material = theme / 'theme'
    material.mkdir(parents=True, exist_ok=True)
    for name in ('Styling.qml', 'Motion.qml', 'ShellStyles.js', 'Icons.qml'):
        shutil.copy2(shell / 'modules/theme' / name, material)

    wallpaper = theme / 'widgets/dashboard/wallpapers'
    wallpaper.mkdir(parents=True, exist_ok=True)
    for name in ('palette.vert', 'palette.frag', 'palette.vert.qsb', 'palette.frag.qsb'):
        shutil.copy2(shell / 'modules/widgets/dashboard/wallpapers' / name, wallpaper)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    assemble(parser.parse_args().destination)
