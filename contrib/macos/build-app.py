#!/usr/bin/env python3
"""Build a relocatable arm64 bundle; never alter installed dependencies."""
import collections, hashlib, json, os, pathlib, plistlib, re, shutil, subprocess, sys
TOOLS=pathlib.Path(__file__).resolve().parent
ROOT=TOOLS.parents[1]
PREFIX=ROOT/'build/macos/install'
OUT=ROOT/'dist/LeptonEDA.app'
if OUT.exists():
    raise SystemExit('dist/LeptonEDA.app exists; move it aside before rebuilding')
CONT=OUT/'Contents'; RES=CONT/'Resources'; FW=CONT/'Frameworks'
for p in [RES,FW,CONT/'MacOS',RES/'entry',RES/'bin']:
    p.mkdir(parents=True,exist_ok=True)
def run(*args): return subprocess.check_output([str(a) for a in args],text=True).strip()
def copytree(src,dst,ignore=None):
    shutil.copytree(src,dst,symlinks=False,ignore=ignore,dirs_exist_ok=True)
copytree(PREFIX/'share',RES/'share',shutil.ignore_patterns('ccache'))
copytree('/opt/homebrew/opt/guile/share/guile/3.0',RES/'share/guile/3.0')
copytree('/opt/homebrew/opt/guile/lib/guile/3.0/ccache',RES/'lib/guile/3.0/ccache')
copytree('/opt/homebrew/share/glib-2.0/schemas',RES/'share/glib-2.0/schemas')
copytree('/opt/homebrew/share/icons/Adwaita',RES/'share/icons/Adwaita')
copytree('/opt/homebrew/share/icons/hicolor',RES/'share/icons/hicolor')
copytree('/opt/homebrew/share/mime',RES/'share/mime')
# Installed scripts contain the build prefix and intentionally select the build
# tree when LIBLEPTON is set. Replace only their generated bootstrap in the copy.
for tool in ['schematic','export','netlist','config','shell','cli']:
    text=(PREFIX/'bin'/f'lepton-{tool}').read_text()
    marker='(use-modules (lepton m4))'
    assert text.count(marker)==1
    text=text[text.index(marker):]
    bootstrap='(define %bitmap-directory (string-append (getenv "LEPTON_BUNDLE_RESOURCES") "/share/lepton-eda/bitmap"))\n'
    text=text.replace('"@LEPTON_CCACHE_DIR@"','(string-append (getenv "LEPTON_BUNDLE_RESOURCES") "/share/lepton-eda/ccache")')
    (RES/'entry'/f'lepton-{tool}.scm').write_text(bootstrap+text)
    wrapper=RES/'bin'/f'lepton-{tool}'
    wrapper.write_text('#!/bin/sh\ncontents=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)\nexec "$contents/MacOS/LeptonEDA" --tool '+tool+' "$@"\n')
    wrapper.chmod(0o755)
# Convert generated Scheme constants to runtime resource paths in copied data.
for p in (RES/'share/lepton-eda/scheme').rglob('*.scm'):
    text=p.read_text()
    def relocate_string(match):
        chunks=match[0][1:-1].split(str(PREFIX))
        if len(chunks)==1: return match[0]
        pieces=[]
        for i,chunk in enumerate(chunks):
            if i: pieces.append('(getenv "LEPTON_BUNDLE_RESOURCES")')
            if chunk: pieces.append(json.dumps(chunk))
        return '(string-append '+' '.join(pieces)+')'
    text=re.sub(r'"[^"\n]*"',relocate_string,text)
    p.write_text(text)
# Include an upstream example without any private user files.
copytree(ROOT/'examples/TwoStageAmp',RES/'examples/TwoStageAmp')
example=RES/'examples/TwoStageAmp/gafrc'
example.write_text('(component-library "./sym" "TwoStageAmp example")\n')
# Native embedded interpreter, before rewriting its complete library closure.
flags=run('/opt/homebrew/bin/pkg-config','--cflags','--libs','guile-3.0').split()
subprocess.run(['/usr/bin/clang',str(TOOLS/'bundle-launcher.c'),*flags,'-Wl,-headerpad_max_install_names','-o',str(CONT/'MacOS/LeptonEDA')],check=True)
plist={'CFBundleExecutable':'LeptonEDA','CFBundleIdentifier':'local.lepton-eda.Quartz','CFBundleName':'Lepton EDA','CFBundleDisplayName':'Lepton EDA','CFBundlePackageType':'APPL','CFBundleVersion':'1','CFBundleShortVersionString':'1.9.18','NSHighResolutionCapable':True,'LSMinimumSystemVersion':run('/usr/bin/sw_vers','-productVersion').split('.')[0]+'.0'}
with (CONT/'Info.plist').open('wb') as f: plistlib.dump(plist,f)
# Dynamic modules are roots too; they are not in otool's static closure.
roots=[(PREFIX/'lib/liblepton.dylib',FW/'liblepton.11.dylib'),(PREFIX/'lib/libleptongui.dylib',FW/'libleptongui.5.dylib')]
modules=[('/opt/homebrew/lib/gtk-3.0/3.0.0/printbackends','lib/gtk-3.0/3.0.0/printbackends'),('/opt/homebrew/lib/gdk-pixbuf-2.0/2.10.0/loaders','lib/gdk-pixbuf-2.0/2.10.0/loaders'),('/opt/homebrew/opt/guile/lib/guile/3.0/extensions','lib/guile/3.0/extensions')]
module_links=[]
for src,dst in modules:
    for p in pathlib.Path(src).glob('*.so'):
        if p.is_symlink() and p.name != p.resolve().name:
            module_links.append((RES/dst/p.name,p.resolve().name))
            roots.append((p.resolve(),RES/dst/p.resolve().name))
            continue
        roots.append((p,RES/dst/p.name))
# The pixbuf cache is materialized with the current bundle path by the launcher.
cache=pathlib.Path('/opt/homebrew/lib/gdk-pixbuf-2.0/2.10.0/loaders.cache').read_text()
cache=re.sub(r'"[^"\n]+/(libpixbufloader[-_][^/"\n]+)"',r'"@BUNDLE_RESOURCES@/lib/gdk-pixbuf-2.0/2.10.0/loaders/\1"',cache)
(RES/'pixbuf-loaders.cache.in').write_text(cache)
queue=collections.deque(roots)
sources={}; destinations={}; aliases={}; edges={}
formulas={pathlib.Path('/opt/homebrew/opt'/pathlib.Path(name)).resolve()
          for name in ['adwaita-icon-theme','hicolor-icon-theme','shared-mime-info','gsettings-desktop-schemas']
          if pathlib.Path('/opt/homebrew/opt'/pathlib.Path(name)).exists()}
def system(path): return path.startswith('/usr/lib/') or path.startswith('/System/Library/')
def dependencies(src):
    return [line.strip().split(' (compatibility')[0] for line in run('/usr/bin/otool','-L',src).splitlines()[1:]]
def resolve(dep,src):
    if dep.startswith('@loader_path/'):
        return (src.parent/dep[len('@loader_path/'):]).resolve()
    if dep.startswith('@rpath/'):
        name=dep[len('@rpath/'):]
        # Resolve against the original LC_RPATHs, not the staged bundle.
        lines=run('/usr/bin/otool','-l',src).splitlines()
        paths=[]
        for i,line in enumerate(lines):
            if 'cmd LC_RPATH' in line:
                value=lines[i+2].strip().split('path ',1)[1].split(' (offset')[0]
                value=value.replace('@loader_path',str(src.parent))
                paths.append(pathlib.Path(value)/name)
        for p in [*paths,src.parent/name,pathlib.Path('/opt/homebrew/lib')/name]:
            if p.exists(): return p.resolve()
        raise RuntimeError(f'Cannot resolve {dep} from {src}')
    return pathlib.Path(dep).resolve()
while queue:
    src,dst=queue.popleft(); original=pathlib.Path(src); src=original.resolve()
    if src in sources:
        if dst.parent==FW: aliases[dst.name]=sources[src].name
        continue
    if not src.exists(): raise RuntimeError(f'Missing dependency {src}')
    if dst in destinations and destinations[dst]!=src: raise RuntimeError(f'Collision {dst}')
    dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst); dst.chmod(0o755)
    sources[src]=dst; destinations[dst]=src
    if '/Cellar/' in str(src): formulas.add(pathlib.Path(*src.parts[:src.parts.index('Cellar')+3]))
    deps=dependencies(src); edges[dst]=deps
    # The first dylib load command is its own install ID.
    for dep in deps:
        if system(dep): continue
        target=resolve(dep,src)
        if target==src: continue
        queue.append((target,FW/target.name))
    # Keep unversioned dynamic-link names without copying library bytes twice.
    for sibling in original.parent.glob('*.dylib'):
        if sibling.is_symlink() and sibling.resolve()==src and dst.parent==FW:
            aliases[sibling.name]=dst.name
# Executable is already in place, but its dependencies must enter the same graph.
exe=CONT/'MacOS/LeptonEDA'
# Collect executable dependencies by rerunning this same queue processing for roots
# via an explicit check: all its non-system dependencies must already be included.
for dep in dependencies(exe):
    if not system(dep) and resolve(dep,exe) not in sources:
        raise RuntimeError(f'Executable dependency not collected: {dep}')
for alias,target in {'liblepton.dylib':'liblepton.11.dylib','libleptongui.dylib':'libleptongui.5.dylib',**aliases}.items():
    p=FW/alias
    if alias!=target and not p.exists(): p.symlink_to(target)
for alias,target in module_links:
    alias.symlink_to(target)
# libguile is collected through liblepton; rewrite all copied images including exe.
for dst,src in [*destinations.items(),(exe,exe)]:
    changes=[]
    for dep in dependencies(dst):
        if system(dep): continue
        target=resolve(dep,src)
        if target==src and dst!=exe:
            subprocess.run(['/usr/bin/install_name_tool','-id','@rpath/'+dst.name,str(dst)],check=True,capture_output=True)
            continue
        bundled=sources[target]
        relative=os.path.relpath(bundled,dst.parent)
        changes.extend(['-change',dep,'@loader_path/'+relative])
    # Remove external LC_RPATHs even if no load command currently uses them.
    lines=run('/usr/bin/otool','-l',dst).splitlines()
    for i,line in enumerate(lines):
        if 'cmd LC_RPATH' in line:
            value=lines[i+2].strip().split('path ',1)[1].split(' (offset')[0]
            changes.extend(['-delete_rpath',value])
    if changes: subprocess.run(['/usr/bin/install_name_tool',*changes,str(dst)],check=True,capture_output=True)
# Include upstream licenses and formula provenance for every bundled dependency.
licenses=RES/'licenses'; licenses.mkdir()
for formula in sorted(formulas):
    dest=licenses/(formula.parent.name+'-'+formula.name); dest.mkdir()
    for p in formula.iterdir():
        if p.is_file() and re.search(r'COPYING|LICENSE|COPYRIGHT|AUTHORS|NOTICE|INSTALL_RECEIPT|sbom',p.name,re.I): shutil.copy2(p,dest/p.name)
shutil.copy2(ROOT/'COPYING',licenses/'Lepton-COPYING')
# Preserve the exact Lepton source and local changes used for this build.
source_dir=RES/'source'; source_dir.mkdir()
subprocess.run(['git','-C',str(ROOT),'archive','--format=tar.gz','-o',str(source_dir/'lepton-eda-source.tar.gz'),'HEAD'],check=True)
(source_dir/'local-changes.patch').write_text(run('git','-C',ROOT,'diff','HEAD')+'\n')
(source_dir/'packaging').mkdir()
for name in ['bundle-launcher.c','build-app.py','audit-app.py']:
    shutil.copy2(TOOLS/name,source_dir/'packaging'/name)
# Fresh ad hoc signatures are required after changing signed arm64 images.
for dst in destinations:
    subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(dst)],check=True,capture_output=True)
subprocess.run(['/usr/bin/codesign','--force','--sign','-',str(OUT)],check=True,capture_output=True)
manifest={'lepton_commit':run('git','-C',ROOT,'rev-parse','HEAD'),'architecture':'arm64','ad_hoc_signed':True,'notarized':False,'libraries':{str(dst.relative_to(CONT)):str(src) for dst,src in destinations.items()},'source_patch_sha256':hashlib.sha256(run('git','-C',ROOT,'diff','HEAD').encode()).hexdigest()}
(ROOT/'build/macos/reports').mkdir(parents=True,exist_ok=True)
(ROOT/'build/macos/reports/build-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(OUT)
print(f'{len(destinations)} bundled native libraries/modules; {len(formulas)} dependency formulae')

subprocess.run([sys.executable, str(TOOLS/"audit-app.py"), str(OUT)], check=True)
