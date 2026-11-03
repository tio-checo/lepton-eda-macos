#!/usr/bin/env python3
"""Check Mach-O closure, signatures, architecture and symlink containment."""
import json,pathlib,subprocess,sys
app=pathlib.Path(sys.argv[1]).resolve()
assert app.is_dir()
images=[]
for p in app.rglob('*'):
    if p.is_symlink():
        assert p.resolve().is_relative_to(app), f'Escaping symlink: {p}'
        assert p.exists(), f'Broken symlink: {p}'
        continue
    if not p.is_file(): continue
    with p.open('rb') as stream: magic=stream.read(4)
    if magic not in (b'\xcf\xfa\xed\xfe',b'\xca\xfe\xba\xbe',b'\xfe\xed\xfa\xcf'): continue
    arch=subprocess.check_output(['/usr/bin/lipo','-archs',str(p)],text=True).strip()
    assert arch=='arm64', (p,arch)
    deps=subprocess.check_output(['/usr/bin/otool','-L',str(p)],text=True).splitlines()[1:]
    for line in deps:
        dep=line.strip().split(' (compatibility')[0]
        if dep.startswith(('/usr/lib/','/System/Library/')): continue
        if dep=='@rpath/'+p.name: continue # dylib install ID
        assert dep.startswith('@loader_path/'), (p,dep)
        target=(p.parent/dep[len('@loader_path/'):]).resolve()
        assert target.is_relative_to(app) and target.is_file(), (p,dep,target)
    commands=subprocess.check_output(['/usr/bin/otool','-l',str(p)],text=True)
    assert 'cmd LC_RPATH' not in commands, p
    images.append(str(p.relative_to(app)))
subprocess.run(['/usr/bin/codesign','--verify','--deep','--strict',str(app)],check=True)
for p in (app/'Contents/Resources/share/lepton-eda/scheme').rglob('*.scm'):
    text=p.read_text()
    assert '/opt/homebrew' not in text and str(pathlib.Path(__file__).resolve().parents[2]) not in text,p
print(json.dumps({'result':'PASS','bundle':str(app),'arm64_images':len(images),'no_external_non_Apple_load_commands':True,'no_external_rpaths':True,'all_symlinks_contained':True,'ad_hoc_signature_valid':True},indent=2))
