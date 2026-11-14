#!/usr/bin/env python3
"""Build the local Lyrics Plus adapter from the installed Spicetify package."""
import argparse
from pathlib import Path
import subprocess

FILES = ['Utils.js', 'ProviderLRCLIB.js', 'ProviderMusixmatch.js', 'ProviderNetease.js', 'Providers.js']


def bundle(package, adapter):
    return '(() => {\n' + '\n'.join((package / name).read_text() for name in FILES) + '\n' + adapter.read_text() + '\n})();\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--package', type=Path, default=Path('/opt/spicetify-cli/CustomApps/lyrics-plus'))
    parser.add_argument('--spotify', type=Path, default=Path.home() / '.local/share/spotify-launcher/install/usr/share/spotify')
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    config = Path(subprocess.check_output(['spicetify', '-c'], text=True).strip()).parent
    output = config / 'Extensions/enclosure-lyrics-plus.js'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(bundle(args.package, source / 'lyrics_plus_extension.js'))
    subprocess.run(['node', '--check', str(output)], check=True)
    subprocess.run(['spicetify', 'config', 'spotify_path', str(args.spotify), 'prefs_path', str(Path.home() / '.config/spotify/prefs'),
                    'custom_apps', 'lyrics-plus', 'extensions', output.name], check=True)
    print('Prepared Lyrics Plus and local adapter. Apply without restarting: spicetify backup apply -n')


if __name__ == '__main__':
    main()
