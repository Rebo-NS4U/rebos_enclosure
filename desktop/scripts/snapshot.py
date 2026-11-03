#!/usr/bin/env python3
"""Verify reviewed source or export a committed release; never snapshot a live home."""
import argparse
from pathlib import Path
import subprocess
from develop import refresh_checksums
from deploy import verify

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--hashes', action='store_true', help='Rebuild hashes from explicitly tracked source')
    group.add_argument('--output', type=Path, help='Export committed HEAD to a new .tar.gz file')
    group.add_argument('--verify', action='store_true', help='Verify source and defaults (the default)')
    args = parser.parse_args()
    if args.hashes:
        refresh_checksums(ROOT)
    elif args.output:
        if args.output.exists():
            parser.error('Output exists; choose a new archive path')
        subprocess.run(['git', 'archive', '--format=tar.gz', '--output', str(args.output.resolve()), 'HEAD'], cwd=ROOT, check=True)
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        print(f'Exported committed revision {revision}; uncommitted edits are excluded.')
    else:
        print(f'Verified {len(verify(ROOT / "desktop/payload"))} installation groups.')


if __name__ == '__main__':
    main()
