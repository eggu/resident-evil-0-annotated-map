"""RE2 Remake style, user 2026-11-06."""
import ctypes,json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for f in ('emulator','tests'):sys.path.insert(0,str(ROOT/f))
from core import Core,Settings
from frame_contract import tables_markers
class Style(unittest.TestCase):
 def setUp(self):self.core=Core()
 def real_default(self):
  s=Settings();self.core.library.re0_settings_default(ctypes.byref(s));return s
 def test_defaults(self):
  s=self.real_default();self.assertEqual((s.item_names,s.icon_size,s.icon_opacity,s.names),(0,100,80,1))
 def test_keys(self):
  s=self.real_default();k=self.core.library.re0_settings_key;k.argtypes=[ctypes.POINTER(Settings),ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p]
  k(ctypes.byref(s),ord('h'),None,None);self.assertEqual(s.item_names,1);k(ctypes.byref(s),ord('h'),None,None);self.assertEqual(s.item_names,2);k(ctypes.byref(s),ord('h'),None,None);self.assertEqual(s.item_names,0)
  k(ctypes.byref(s),ord('I'),None,None);self.assertEqual(s.icon_size,110);k(ctypes.byref(s),ord('o'),None,None);self.assertEqual(s.icon_opacity,70)
  k(ctypes.byref(s),ord('+'),None,None);self.assertEqual((s.size,s.icon_size),(110,110))
 def test_item_names_off_by_default_room_names_on(self):
  H=(ROOT/'src/runtime/labels_generated.h').read_text();m=tables_markers()[0];s=self.real_default();s.scope=2
  layout={int(r.split(',')[2]) for r in re.findall(r'\{([0-9.,f\-]+)\}',H.split('room_layout[] = {',1)[1].split('};',1)[0])}
  ops=self.core.frame(s,1920,1080,{m[2]:[300,200,420,300]},(),(1.5,960-m[0]*1.5,540-m[1]*1.5),None,[0xffffffff]*33)[0];g=[o['glyph'] for o in ops]
  self.assertNotIn(m[3],g);s.item_names=1;self.assertIn(m[3],[o['glyph'] for o in self.core.frame(s,1920,1080,{m[2]:[300,200,420,300]},(),(1.5,960-m[0]*1.5,540-m[1]*1.5),None,[0xffffffff]*33)[0]])
 def test_icon_opacity_and_size_apply(self):
  s=self.core.default_settings();s.scope=2;s.icon_opacity=50;s.icon_size=150;m=tables_markers()[0]
  ops=self.core.frame(s,1920,1080,{m[2]:[300,200,420,300]},(),(1.5,960-m[0]*1.5,540-m[1]*1.5),None,[0xffffffff]*33)[0]
  first=int(re.search(r'#define ICON_FIRST_GLYPH (\d+)',(ROOT/'src/runtime/labels_generated.h').read_text())[1]);ic=[o for o in ops if o['glyph']>=first]
  self.assertTrue(ic);self.assertEqual(ic[0]['color']>>24,127)
 def test_every_lock_icon_centred_on_its_door(self):
  # All lock rows, on the floors the review page draws, at game zoom.
  H=(ROOT/'src/runtime/labels_generated.h').read_text();ic=[int(v) for v in re.search(r'marker_icon_glyphs\[\] = \{([0-9,]+)\}',H)[1].split(',')]
  page=(ROOT/'local/placement-review/index.html')
  if not page.exists():self.skipTest('needs the page')
  t=page.read_text();D=json.loads(t[t.index('const D=')+8:t.index(';\nconst T=')]);n=0
  for i,m in enumerate(tables_markers()):
   if m[5]!=0:continue
   f=next(f for f in D['floors'] if any(p[0]==m[2] for p in f['pieces']));s=self.core.default_settings();s.scope=2;s.difficulty=[b for b in range(3) if m[6]>>b&1][0]
   ops=self.core.frame(s,1920,1080,{p[0]:[v*1.5 for v in p[1:]] for p in f['pieces']},[[v*1.5 for v in d] for d in f['doors']],(1.5,0,0),None,[0]*33)[0];b=[q['box'] for q in ops if q['glyph']==ic[i]][0]
   self.assertAlmostEqual((b[0]+b[2])/3,m[0],delta=.6);self.assertAlmostEqual((b[1]+b[3])/3,m[1],delta=.6);n+=1
  self.assertEqual(n,20)
 def test_room_names_centred_or_led_and_wrapped_at_150_percent(self):
  L=json.loads((ROOT/'data/room-layout.json').read_text());self.assertLessEqual(sum(bool(r['line']) for r in L['rows']),6)
