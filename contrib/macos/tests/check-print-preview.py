#!/usr/bin/env python3
"""Exercise actual Quartz GTK preview, with an optional real PDF viewer launch."""
import argparse
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
from urllib.parse import unquote, urlparse

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--library-dir', type=Path, default=ROOT/'build/macos/gtk/install/lib')
parser.add_argument('--work', type=Path, required=True)
parser.add_argument('--native', action='store_true', help='Also open a real native PDF viewer')
parser.add_argument('--app', type=Path, help='Also exercise Lepton x_print with its bundled example')
args = parser.parse_args()
work = args.work.resolve()
if work.exists() and any(work.iterdir()):
    parser.error('--work must name an empty or new directory')
work.mkdir(parents=True, exist_ok=True)
lib = args.library_dir.resolve()
source = TOOLS/'print-preview-test.c'
flags = shlex.split(subprocess.check_output(
    ['/opt/homebrew/bin/pkg-config', '--cflags', '--libs', 'gtk+-3.0'], text=True))
flags = [f for f in flags if f not in ('-lgtk-3', '-lgdk-3')]
launchers = {}


def library_flags(library_dir):
    # Bundled libraries have relocated install IDs. Linking their Homebrew
    # counterparts as well would load two independent GLib type registries.
    return [str(library_dir/('lib'+f[2:]+'.dylib'))
            if f.startswith('-l') and (library_dir/('lib'+f[2:]+'.dylib')).exists()
            else f for f in flags]


def compile_test(name, library_dir):
    exe = work/name
    link_flags = library_flags(library_dir)
    launcher = work/(name+'-capture.dylib')
    subprocess.run(['/usr/bin/clang', '-dynamiclib', '-DPREVIEW_INTERPOSER', str(source),
                    *link_flags, f'-Wl,-rpath,{library_dir}', '-o', str(launcher)], check=True)
    subprocess.run(['/usr/bin/clang', str(source),
                    str(library_dir/'libgtk-3.0.dylib'),
                    str(library_dir/'libgdk-3.0.dylib'), *link_flags,
                    f'-Wl,-rpath,{library_dir}', '-o', str(exe)], check=True)
    launchers[exe] = launcher
    return exe


fixed = compile_test('fixed-preview', lib)
baseline = compile_test('baseline-preview', Path('/opt/homebrew/lib'))
cases = []


def invoke(exe, case, *, exporting=False, fail=False, native=False):
    case_dir = work/case
    case_dir.mkdir(parents=True, exist_ok=True)
    cache = case_dir/'cache with space ž'
    temporary = case_dir/'tmp'
    temporary.mkdir(exist_ok=True)
    env = dict(os.environ, GDK_BACKEND='quartz', XDG_CACHE_HOME=str(cache),
               TMPDIR=str(temporary)+'/', LEPTON_TEST_CAPTURE=str(case_dir/'launch-uri'))
    for key in ('DYLD_LIBRARY_PATH', 'DYLD_FRAMEWORK_PATH', 'LEPTON_TEST_LAUNCH_FAIL',
                'DYLD_INSERT_LIBRARIES'):
        env.pop(key, None)
    if not native:
        env['DYLD_INSERT_LIBRARIES'] = str(launchers[exe])
    if fail:
        env['LEPTON_TEST_LAUNCH_FAIL'] = '1'
    command = [str(exe)] + ([str(case_dir/'export.pdf')] if exporting else [])
    run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=40)
    (case_dir/'stdout.txt').write_text(run.stdout)
    (case_dir/'stderr.txt').write_text(run.stderr)
    assert run.returncode == 0, run.stderr
    assert 'drawn=1\n' in run.stdout, run.stdout
    return case_dir, cache, run.stdout


case, _, output = invoke(baseline, 'baseline')
assert 'result=0\n' in output and 'Creating an app info from a command line' in output, output
assert not (case/'launch-uri').exists()
cases.append('unpatched GTK reproduces the reported error')

# Expiration must retain fresh previews and unrelated files, dirs and symlinks.
preview_dir = work/'preview'/'cache with space ž'/'gtk-3.0/print-preview'
preview_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
old = preview_dir/'gtk-preview-old.pdf'
fresh = preview_dir/'gtk-preview-fresh.pdf'
unrelated = preview_dir/'personal.pdf'
for file in (old, fresh, unrelated):
    file.write_text('fixture')
for file in (old, unrelated):
    os.utime(file, (time.time()-8*86400,)*2)
link = preview_dir/'gtk-preview-link.pdf'
link.symlink_to(unrelated.name)
os.utime(link, (time.time()-8*86400,)*2, follow_symlinks=False)
directory = preview_dir/'gtk-preview-directory.pdf'
directory.mkdir()
os.utime(directory, (time.time()-8*86400,)*2)

case, _, output = invoke(fixed, 'preview')
assert 'result=1\n' in output and 'error=none\n' in output, output
uri = (case/'launch-uri').read_text()
assert '%20' in uri and '%C5%BE' in uri, uri
pdf = Path(unquote(urlparse(uri).path))
assert pdf.parent == preview_dir and pdf.is_file()
assert pdf.stat().st_mode & 0o777 == 0o600
assert not old.exists() and fresh.exists() and unrelated.exists()
assert link.is_symlink() and directory.is_dir()
assert not list((case/'tmp').glob('settings*.ini'))
cases.extend(['completed PDF reaches the native URI launcher',
              'spaces and Unicode survive filename/URI conversion; PDF mode is 0600',
              'expires only old owned previews; preserves fresh/unrelated files, symlinks and directories',
              'does not create unused Evince settings files'])

case, _, output = invoke(fixed, 'launch-failure', fail=True)
assert 'result=0\n' in output and 'Injected PDF launch failure' in output, output
failed_pdf = Path(unquote(urlparse((case/'launch-uri').read_text()).path))
assert not failed_pdf.exists()
cases.append('launch error propagates and removes the failed preview')

case, _, output = invoke(fixed, 'export', exporting=True)
assert 'result=1\n' in output and (case/'export.pdf').is_file(), output
assert not (case/'launch-uri').exists()
cases.append('ordinary PDF export works without launching a viewer')

if args.native:
    case, cache, output = invoke(fixed, 'native', native=True)
    assert 'result=1\n' in output and 'error=none\n' in output, output
    cases.append('real Launch Services PDF viewer launch succeeds')

if args.app:
    app = args.app.resolve()
    case = work/'schematic'
    case.mkdir()
    integration = case/'schematic-print-capture.dylib'
    subprocess.run(['/usr/bin/clang', '-dynamiclib', '-DPREVIEW_INTERPOSER',
                    '-DLEPTON_PREVIEW_FROM_DIALOG', str(source),
                    str(lib/'libgtk-3.0.dylib'), str(lib/'libgdk-3.0.dylib'),
                    *library_flags(lib), f'-Wl,-rpath,{lib}', '-o', str(integration)], check=True)
    env = dict(os.environ, LEPTON_BUNDLE_PROFILE=str(case/'profile'),
               DYLD_INSERT_LIBRARIES=str(integration),
               LEPTON_TEST_CAPTURE=str(case/'launch-uri'),
               LEPTON_TEST_PRINT_RESULT=str(case/'print-result'))
    for key in ('DYLD_LIBRARY_PATH', 'DYLD_FRAMEWORK_PATH', 'LEPTON_TEST_LAUNCH_FAIL'):
        env.pop(key, None)
    example = app/'Contents/Resources/examples/TwoStageAmp'
    expression = ('(begin (use-modules (schematic ffi) (schematic window global)) '
                  '(x_print (*current-window)) (primitive-exit 0))')
    run = subprocess.run([str(app/'Contents/MacOS/LeptonEDA'), '--tool', 'schematic',
                          '-c', expression, str(example/'TwoStageAmp.sch')],
                         cwd=example, env=env, capture_output=True, text=True, timeout=45)
    (case/'stdout.txt').write_text(run.stdout)
    (case/'stderr.txt').write_text(run.stderr)
    assert run.returncode == 0, run.stderr
    assert (case/'print-result').read_text() == 'result=1\nerror=none\n'
    assert (case/'launch-uri.pdf').is_file()
    cases.append('Lepton x_print renders bundled TwoStageAmp through the fixed preview path')

(work/'result.json').write_text(json.dumps({'result': 'PASS', 'checks': cases}, indent=2)+'\n')
print(json.dumps({'result': 'PASS', 'checks': cases}, indent=2))
