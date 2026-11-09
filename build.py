"""Build and package the release ZIP; never install, launch or publish it."""
from pathlib import Path
import argparse,hashlib,json,subprocess,sys,tempfile,zipfile,struct
ROOT=Path(__file__).resolve().parent
CC='i686-w64-mingw32-gcc'
VERSION=(ROOT/'VERSION').read_text().strip()
FLAGS=['-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-shared','-static-libgcc',
       '-Wl,--no-insert-timestamp','-Wl,--image-base,0x62000000','-Wl,--dynamicbase','-Wl,--nxcompat']
LIBS=['-lkernel32','-luser32','-ladvapi32']
def sha(blob):return hashlib.sha256(blob).hexdigest()
def compile_to(output,probe=False):
 sources=['tests/runtime_probe.c' if probe else 'src/runtime/re0_map.c','src/core/map_transform.c','src/core/annotation.c','src/core/frame.c']
 subprocess.run([CC,*FLAGS,f'-DRE0_MAP_VERSION="{VERSION}"',*[str(ROOT/f) for f in sources],'-o',str(output),*LIBS],check=True)

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--test',action='store_true');a=p.parse_args();gate_passed=False
 if a.test:
  subprocess.run([sys.executable,str(ROOT/'tools/build_core.py')],check=True)
  subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT,check=True)
  # ponytail: needs the private analysis image, so public checkouts skip it.
  if (ROOT/'local/research/re0hd.analysis.bin').exists():
   subprocess.run([sys.executable,str(ROOT/'tools/inspect/check_hook_classes.py')],check=True)
   # Fails if native-built objects do not reach the overlay's capture, or a past live failure goes uncaught.
   subprocess.run([sys.executable,str(ROOT/'tools/inspect/check_native_dispatch.py')],check=True)
   gate_passed=True
 atlas=(ROOT/'assets/labels.bgra').read_bytes();labels=json.loads((ROOT/'verification/label-build.json').read_text())
 if len(atlas)!=labels['width']*labels['height']*4 or sha(atlas)!=labels['atlas_sha256']:raise ValueError('atlas does not match label build record')
 icons=(ROOT/'assets/icons.bgra').read_bytes()
 if sha(icons)!=labels['icons_sha256']:raise ValueError('icon texture does not match label build record')
 if sha((ROOT/'src/runtime/labels_generated.h').read_bytes())!=labels['header_sha256'] or any(sha((ROOT/name).read_bytes())!=digest for name,digest in labels['inputs_sha256'].items()):raise ValueError('stale label catalogue; run tools/build_labels.py')
 dist=ROOT/'dist';dist.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory(prefix='re0-annotated-map-') as d:
  temp=Path(d);binary=temp/'RE0.AnnotatedMap.asi';compile_to(binary)
  blob=binary.read_bytes();pe=struct.unpack_from('<I',blob,60)[0]
  if blob[:2]!=b'MZ' or struct.unpack_from('<H',blob,pe+4)[0]!=0x14c or not struct.unpack_from('<H',blob,pe+22)[0]&0x2000:raise ValueError('output is not an x86 DLL')
  # The same sources/options must produce the same artifact before packaging it.
  compile_to(binary)
  if binary.read_bytes()!=blob:raise ValueError('nonreproducible ASI build')
  if a.test:
   probe=temp/'adapter-probe.dll';compile_to(probe,True)
   subprocess.run([sys.executable,str(ROOT/'tools/inspect/check_adapter.py'),'--dll',str(probe),'--output',str(ROOT/'verification/adapter-synthetic.json')],check=True)
  loader=ROOT/'packaging/ultimate-asi-loader' # Ultimate ASI Loader; re0hd.exe imports DINPUT8.dll
  members={'scripts/RE0.AnnotatedMap.asi':blob,'scripts/RE0.AnnotatedMap.bgra':atlas,'scripts/RE0.AnnotatedMap.icons.bgra':icons,
           'scripts/RE0.AnnotatedMap.ini':(ROOT/'packaging/RE0.AnnotatedMap.ini').read_bytes(),
           'scripts/UltimateASILoader-LICENSE.txt':(loader/'UltimateASILoader-LICENSE.txt').read_bytes(),'dinput8.dll':(loader/'dinput8.dll').read_bytes(),
           'RE0-Annotated-Map-README.txt':(ROOT/'packaging/README.txt').read_bytes(),'LICENSE.txt':(ROOT/'LICENSE').read_bytes(),'NOTICE.md':(ROOT/'NOTICE.md').read_bytes()}
  path=dist/f'RE0-Annotated-Map-{VERSION}.zip';tmp=path.with_suffix('.zip.tmp')
  with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
   for name,data in sorted(members.items()):
    info=zipfile.ZipInfo(name,date_time=(2026,11,3,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
    z.writestr(info,data,compresslevel=9)
  with zipfile.ZipFile(tmp) as z:
   if z.testzip() is not None or set(z.namelist())!=set(members) or any(z.read(n)!=data for n,data in members.items()):raise ValueError('package verification failed')
  tmp.replace(path)
 sources=sorted(f for folder in ['src','tools','emulator','data','packaging','tests'] for f in (ROOT/folder).rglob('*') if f.is_file() and f.suffix not in ('.pyc',) and '__pycache__' not in f.parts)
 report=dict(version=VERSION,asi_sha256=sha(blob),zip_sha256=sha(path.read_bytes()),compiler=subprocess.check_output([CC,'--version'],text=True).splitlines()[0],
  portable_and_synthetic_tests_run=a.test,native_dispatch_gate_passed=gate_passed,reproducible_asi_rebuild=True,game_executed=False,installed=False,published=False,
  support_exe_sha256='67418c3a307b49e9bde8123df4cad1fa910f3a29adc3e4c0ba64eb96524bc14b',
  members={name:dict(size=len(data),sha256=sha(data)) for name,data in sorted(members.items())},
  source_sha256={str(f.relative_to(ROOT)):sha(f.read_bytes()) for f in [ROOT/'build.py',*sources]})
 (dist/'build-report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(f'Built and verified {path}\nASI SHA256: {report["asi_sha256"]}\nZIP SHA256: {report["zip_sha256"]}')
if __name__=='__main__':main()
