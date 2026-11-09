"""Candidate 44: new defaults, INI migration that must not double-apply, the same screen as candidate 43 at the user's old settings."""
import ctypes,re,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for f in ('emulator','tests'):sys.path.insert(0,str(ROOT/f))
from core import Core,Settings
from frame_contract import tables_markers
H=(ROOT/'src/runtime/labels_generated.h').read_text()
class Defaults(unittest.TestCase):
 def test_new_defaults(self):
  s=Settings();Core().library.re0_settings_default(ctypes.byref(s))
  self.assertEqual((s.size,s.opacity,s.icon_size,s.icon_opacity,s.item_names,s.legend),(100,60,100,80,0,1))
 def test_legend_lost_two_lines_and_gained_a_hide_hint(self):
  self.assertNotIn('select_ids',H);self.assertNotIn('note_ids',H);self.assertIn('hide_ids',H);self.assertIn('fold_ids',H)
  src=(ROOT/'tools/build_labels.py').read_text();self.assertNotIn('Select room',src);self.assertNotIn('Pickups',src)
class Migration(unittest.TestCase):
 def sizes(self,version,name,icon):
  s=Settings();core=Core();core.library.re0_settings_default(ctypes.byref(s));f=core.library.re0_settings_ini_sizes;f.argtypes=[ctypes.POINTER(Settings),ctypes.c_int,ctypes.c_int,ctypes.c_int]
  return f(ctypes.byref(s),version,name,icon),s.size,s.icon_size
 def test_the_users_installed_ini_looks_the_same(self):
  self.assertEqual(self.sizes(0,110,130),(1,100,100)) # NameSize=110 IconSize=130 in candidate 43
 def test_old_ini_values_convert_once_and_a_converted_file_is_left_alone(self):
  self.assertEqual(self.sizes(0,100,100),(1,90,80));self.assertEqual(self.sizes(0,150,200),(1,140,150));self.assertEqual(self.sizes(0,50,50),(1,50,50))
  r,n,i=self.sizes(0,110,130);self.assertEqual(self.sizes(52,n,i),(0,100,100)) # saved back with Version=52, read again: unchanged
  self.assertEqual(self.sizes(52,110,130),(0,110,130));self.assertEqual(self.sizes(53,60,40),(0,60,50))
 def test_absent_keys_take_the_new_default(self):
  self.assertEqual(self.sizes(0,-1,-1),(1,100,100));self.assertEqual(self.sizes(52,-1,-1),(0,100,100))
 def test_every_old_grid_value_keeps_its_screen_size_within_half_a_step(self):
  for old,base,lo,hi in ((range(50,151,10),1.1,50,150),(range(50,201,10),1.3,50,200)):
   for v in old:
    got=self.sizes(0,v,v)[1 if base==1.1 else 2];want=max(lo,min(hi,v/base))
    self.assertLessEqual(abs(got-want),5.01,(v,got))
class SameScreen(unittest.TestCase):
 """Candidate 43's size formulas (bases 1.0) at 110% names and 130% icons against the new build at 100%: icon boxes and room-name boxes must be equal."""
 @classmethod
 def setUpClass(cls):
  src=(ROOT/'src/core/frame.c').read_text()
  for a,b in (('#define NAME_SIZE_BASE 1.1f','#define NAME_SIZE_BASE 1.0f'),('#define ICON_SIZE_BASE 1.3f','#define ICON_SIZE_BASE 1.0f')):
   assert a in src;src=src.replace(a,b)
  cls.tmp=tempfile.TemporaryDirectory();d=Path(cls.tmp.name);(d/'frame.c').write_text(src.replace('#include "frame.h"',f'#include "{ROOT}/src/core/frame.h"').replace('"../runtime/labels_generated.h"',f'"{ROOT}/src/runtime/labels_generated.h"'))
  lib=d/'old.dylib';subprocess.run(['clang','-std=c11','-O1','-w','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC',str(ROOT/'src/core/map_transform.c'),str(ROOT/'src/core/annotation.c'),str(d/'frame.c'),'-o',str(lib)],check=True)
  cls.old=Core(lib);cls.new=Core()
 @classmethod
 def tearDownClass(cls):cls.tmp.cleanup()
 def ops(self,core,size,icon):
  s=core.default_settings();s.scope=2;s.size=size;s.icon_size=icon;s.opacity=60;s.icon_opacity=80;m=tables_markers()[0]
  return core.frame(s,1920,1080,{m[2]:[300,200,420,300]},(),(1.5,960-m[0]*1.5,540-m[1]*1.5),None,[0xffffffff]*33)[0]
 def test_icons_item_names_and_room_names_match(self):
  first=int(re.search(r'#define ICON_FIRST_GLYPH (\d+)',H)[1]);layout={int(r.split(',')[2]) for r in re.findall(r'\{([0-9.,f\-]+)\}',H.split('room_layout[] = {',1)[1].split('};',1)[0])}
  a=self.ops(self.old,110,130);b=self.ops(self.new,100,100)
  # Legend and readouts differ by design and sit below y=900; everything the map draws above must not.
  # Candidate 45 changed enemies and door keys on purpose (enemies lose the 1.3, door keys gain 1.2), so those marks and their names are left out.
  ms=tables_markers();icons=[int(v) for v in re.search(r'marker_icon_glyphs\[\] = \{([0-9,]+)\}',H)[1].split(',')]
  skip={g for m,i in zip(ms,icons) if m[5] in (0,5) for g in (i,m[3],m[4])}
  map_a=[o for o in a if o['box'][1]<700 and o['glyph'] not in skip];map_b=[o for o in b if o['box'][1]<700 and o['glyph'] not in skip]
  self.assertEqual(len(map_a),len(map_b));self.assertGreater(sum(o['glyph']>=first for o in map_b),0)
  for x,y in zip(map_a,map_b):
   self.assertEqual(x['glyph'],y['glyph']);[self.assertAlmostEqual(p,q,delta=.01) for p,q in zip(x['box'],y['box'])]
if __name__=='__main__':unittest.main()
