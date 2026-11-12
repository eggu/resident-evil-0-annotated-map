"""Leech Hunter: the shared C tells loctbl0300..0304 apart and finishes their markers. Row memory is synthetic, filled from the game's own tables (needs the local game files)."""
import ctypes,json,os,re,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for folder in ('emulator','tools/inspect','tools/extract'):sys.path.insert(0,str(ROOT/folder))
from core import ArrangeView,Core
GAME=Path(os.environ.get('RE0_GAME','/nonexistent'))
STRIDE=0x5c
def states():
 text=(ROOT/'src/runtime/labels_generated.h').read_text()
 return [[int(v) for v in m.split(',')] for m in re.findall(r'\{([0-9,]+)\}',text.split('marker_state[] = {',1)[1].split('};',1)[0])]
@unittest.skipUnless(GAME.exists(),'needs the local game files')
class LeechHunter(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from resources import Arc
  from arrange import parse
  arc=Arc((GAME/'nativePC/arc/arrange/loctbl.arc').read_bytes())
  cls.tables=[[(rm['room'],r['kind'],r['item']) for rm in parse(arc.read(next(m for m in arc.members if m.name.endswith(f'030{t}')))) for r in rm['records']] for t in range(5)]
  cls.core=Core();cls.lib=cls.core.library;cls.lib.re0_arrange_difficulty.argtypes=[ctypes.POINTER(ArrangeView)];cls.lib.re0_arrange_difficulty.restype=ctypes.c_int
 def view(self,t,taken=()):
  rows=self.tables[t];buf=bytearray(0x30+len(rows)*STRIDE)
  for s,(room,kind,item) in enumerate(rows):struct.pack_into('<III',buf,0x30+s*STRIDE,room,0 if s in taken else kind,item);struct.pack_into('<I',buf,0x2c+s*STRIDE,room)
  self.raw=ctypes.create_string_buffer(bytes(buf),len(buf));return ArrangeView(len(rows),ctypes.cast(self.raw,ctypes.c_char_p),0,None)
 def test_each_table_is_told_apart_even_when_everything_is_taken(self):
  for t in range(5):
   self.assertEqual(self.lib.re0_arrange_difficulty(ctypes.byref(self.view(t))),3+t)
   self.assertEqual(self.lib.re0_arrange_difficulty(ctypes.byref(self.view(t,range(len(self.tables[t]))))),3+t) # pickup clears only the kind
 def test_markers_follow_their_table(self):
  st=states()
  for t in range(5):
   mine=[i for i,s in enumerate(st) if s[9+t]!=0xffff and s[7]==0x71];self.assertGreater(len(mine),40)
   for i in mine[:20]:
    v=self.view(t);self.assertFalse(self.core.marker_done(i,None,v),i);self.assertEqual(v.mismatches,0)
    self.assertTrue(self.core.marker_done(i,None,self.view(t,{st[i][9+t]})),i)
class LeechData(unittest.TestCase):
 def setUp(self):self.rows=json.loads((ROOT/'data/placements.json').read_text())['rows']
 def test_decor_zombie_is_not_marked(self):
  # User 2026-11-11: the Small Library zombie lying in pose 12 takes no damage and stays.
  self.assertFalse([r for r in self.rows if r['room']==52 and r.get('kind')==0x10 and any(k.startswith('leech') for k in r['amount']) and [round(v) for v in r['world']]==[242,0,350]])
 def test_waves_follow_the_charm_count_flags(self):
  # 0x59d28e sets 0x313 at the start; at 90 charms 0x552c30 clears it and sets 0x314. Spawn 0x410c46 needs flag 0x312+condition.
  lh=[r for r in self.rows if r['category']=='enemy' and any(k.startswith('leech') for k in r['amount'])]
  self.assertEqual({r['condition'] for r in lh},{0,1,2})
  lib=Core().library;lib.re0_condition_met.argtypes=[ctypes.c_uint,ctypes.POINTER(ctypes.c_uint)];lib.re0_condition_met.restype=ctypes.c_int
  def met(c,flag):
   f=(ctypes.c_uint*64)();f[flag>>5]|=1<<(flag&31);return lib.re0_condition_met(c,f)
  self.assertEqual((met(1,0x313),met(2,0x313)),(1,0));self.assertEqual((met(1,0x314),met(2,0x314)),(0,1))
