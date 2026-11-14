#!/usr/bin/env python3
"""Verify reviewed source or export a committed release; never snapshot a live home."""
import argparse
import hashlib
from pathlib import Path
import subprocess
from develop import refresh_checksums
from deploy import verify

ROOT = Path(__file__).resolve().parents[2]


def export(output):
    checksum = output.with_name(output.name + '.sha256')
    if output.exists() or output.is_symlink() or checksum.exists() or checksum.is_symlink():
        raise ValueError('Output or checksum exists; choose a new archive path')
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    with output.open('xb') as stream:
        subprocess.run(['git', 'archive', '--format=tar.gz', revision], cwd=ROOT, stdout=stream, check=True)
    with output.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    with checksum.open('x') as stream:
        stream.write(digest + '  ' + output.name + '\n')
    print(f'Exported committed revision {revision}; uncommitted edits are excluded.')
    print(f'SHA-256 written to {checksum}')


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
        try:
            export(args.output.resolve() if not args.output.is_symlink() else args.output)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            parser.exit(1, str(error) + '\n')
    else:
        print(f'Verified {len(verify(ROOT / "desktop/payload"))} installation groups.')


if __name__ == '__main__':
    main()
