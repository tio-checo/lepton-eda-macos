#!/usr/bin/env python3
"""Convert the upstream application SVG into a macOS icon, including Retina."""
import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path,
                        default=ROOT/'libleptongui/data/lepton-schematic.svg')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    converter = shutil.which('rsvg-convert', path='/opt/homebrew/bin:/usr/bin:/bin')
    if not converter:
        parser.error('rsvg-convert is required (brew install librsvg)')
    source = args.source.resolve(strict=True)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='lepton-icon-') as temporary:
        iconset = Path(temporary)/'LeptonEDA.iconset'
        iconset.mkdir()
        for size in (16, 32, 128, 256, 512):
            for scale in (1, 2):
                pixels = str(size * scale)
                suffix = '@2x' if scale == 2 else ''
                target = iconset/f'icon_{size}x{size}{suffix}.png'
                subprocess.run([converter, '--width', pixels, '--height', pixels,
                                '--output', str(target), str(source)], check=True)
        subprocess.run(['/usr/bin/iconutil', '--convert', 'icns', '--output', str(output),
                        str(iconset)], check=True)
    print(output)


if __name__ == '__main__':
    main()
