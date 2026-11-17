#!/usr/bin/env python3
"""Build the pinned Quartz GTK privately, including the print-preview fix."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]
VERSION = '3.24.52'
SHA256 = '80931fa472a77b9a164f6740e3c0b444fac6770054632d35a7ff9d679e5e7b9f'
URL = f'https://download.gnome.org/sources/gtk/3.24/gtk-{VERSION}.tar.xz'
PATCH = TOOLS / 'patches/gtk3-quartz-print-preview.patch'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, default=ROOT / 'build/macos/gtk')
    parser.add_argument('--meson', default=shutil.which('meson', path='/opt/homebrew/bin:/usr/bin:/bin'))
    parser.add_argument('--ninja', default=shutil.which('ninja', path='/opt/homebrew/bin:/usr/bin:/bin'))
    parser.add_argument('--jobs', type=int, default=6)
    args = parser.parse_args()
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    manifest = work / 'manifest.json'
    expected = {'version': VERSION, 'url': URL, 'source_sha256': SHA256,
                'patch_sha256': digest(PATCH), 'prefix': str(work / 'install')}
    if manifest.exists():
        saved = json.loads(manifest.read_text())
        libraries = saved.get('libraries', {})
        if (all(saved.get(k) == v for k, v in expected.items()) and libraries
                and all((work / 'install/lib' / name).is_file()
                        and digest(work / 'install/lib' / name) == sha
                        for name, sha in libraries.items())):
            print(work / 'install')
            return
        raise SystemExit(f'Stale GTK build in {work}; use a fresh --work directory')
    if not args.meson or not args.ninja:
        raise SystemExit('Install meson and ninja, or specify --meson and --ninja')
    archive = work / f'gtk-{VERSION}.tar.xz'
    if not archive.exists():
        subprocess.run(['curl', '-L', '--fail', '--retry', '2', URL, '-o', str(archive)], check=True)
    if digest(archive) != SHA256:
        raise SystemExit(f'GTK source checksum mismatch: {archive}')
    source = work / f'gtk-{VERSION}'
    if not source.exists():
        subprocess.run(['tar', '-xf', str(archive), '-C', str(work)], check=True)
    patched = source / '.lepton-preview-patch'
    if not patched.exists():
        subprocess.run(['patch', '-p1', '-i', str(PATCH)], cwd=source, check=True)
        patched.write_text(digest(PATCH))
    if patched.read_text() != digest(PATCH):
        raise SystemExit('GTK patch changed; use a fresh --work directory')
    build = work / 'build'
    prefix = work / 'install'
    env = [str(TOOLS / 'build-env.sh'), '/usr/bin/env', f'NINJA={Path(args.ninja).resolve()}']
    meson = str(Path(args.meson).resolve())

    def run(*command):
        subprocess.run(['sh', *env, meson, *map(str, command)], check=True)

    if not (build / 'build.ninja').exists():
        run('setup', build, source, f'--prefix={prefix}',
            '-Dx11_backend=false', '-Dwayland_backend=false', '-Dquartz_backend=true',
            '-Dintrospection=false', '-Dtests=false', '-Ddemos=false', '-Dexamples=false',
            '-Dprint_backends=cups,file,lpr', '-Dcolord=no',
            "-Dc_args=['-I/opt/homebrew/include', '-Wno-implicit-function-declaration']",
            "-Dc_link_args=['-L/opt/homebrew/lib', '-Wl,-headerpad_max_install_names']")
    run('compile', '-C', build, '-j', args.jobs)
    run('install', '-C', build, '--no-rebuild')
    expected['libraries'] = {p.name: digest(p) for p in (prefix / 'lib').glob('libg[dt]k-3*.dylib')}
    expected['meson_version'] = subprocess.check_output([meson, '--version'], text=True).strip()
    manifest.write_text(json.dumps(expected, indent=2) + '\n')
    print(prefix)


if __name__ == '__main__':
    main()
