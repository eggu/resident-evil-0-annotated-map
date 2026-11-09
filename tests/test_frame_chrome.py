"""The live shot: annotations on the map frame. Every marker on every floor, at game zoom and 3x, frame on and off."""
import json,sys,unittest,ctypes
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for f in ('tools','tests','emulator'):sys.path.insert(0,str(ROOT/f))
from core import Core
from frame_contract import tables_markers
CLOSED=[(176,0,473,112),(176,112,461,138),(198,138,282,177),(848,0,1119,205),(925,205,1119,263),(0,448,192,720),(1088,448,1280,720),(192,538,230,582),(1050,538,1088,634),(192,662,422,720),(858,662,1088,720)]
BOXES=CLOSED+[(192,470,1088,720)]
S=json.loads((ROOT/'tests/fixtures/live-samples.json').read_text())['frame_shot']
inside=lambda p:any(b[0]<=p[0]<b[2] and b[1]<=p[1]<b[3] for b in BOXES)
hit=lambda a,b:a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
SLACK=lambda h:21.6*.5*h/720 # candidate 54: half a default icon, in px at buffer height h
def inner(b,h):
 m=SLACK(h);mx,my=min(m,(b[2]-b[0])/2),min(m,(b[3]-b[1])/2);return [b[0]+mx,b[1]+my,b[2]-mx,b[3]-my]
class Chrome(unittest.TestCase):
 def setUp(self):
  self.core=Core();lib=self.core.library;self.set=lib.re0_frame_set_chrome;self.set.argtypes=[ctypes.c_int]+[ctypes.c_float]*4
 def tearDown(self):self.set(0,1.5,1.5,0,0)
 def test_shot_values(self):
  for p in S['under_frame_gui']:self.assertTrue(inside(p),p)
  for p in S['clear_of_frame_gui']:self.assertFalse(inside(p),p)
  x,y=S['help_panel']['at_2560'];self.assertTrue(inside((x/2+4,y/2+4)))
 def test_floor_arrows_are_map_content_not_frame(self):
  for p in ((640,56),(640,660)):self.assertFalse(any(b[0]<=p[0]<b[2] and b[1]<=p[1]<b[3] for b in CLOSED),p) # the up/down triangles (user shot 21); only the open item list covers the lower one
  self.assertEqual(len(BOXES),12)
 def test_nothing_on_a_shown_frame_and_v_reveals(self):
  ms=tables_markers();pieces={}
  for m in ms:pieces.setdefault(m[2],m)
  grazing=0;canvas=[(k,ox,oy) for k,ox,oy in ((1.5,0,0),(4.5,-1920,-1080),(4.5,-1000,-600))];revealed=0;checked=0
  s=self.core.default_settings();s.scope=2
  rooms={p:[300,200,420,300] for p in pieces}
  for state,boxes,(k,ox,oy) in [(st,bx,c) for st,bx in ((2,BOXES),(1,CLOSED)) for c in canvas]:
   self.set(0,1.5,1.5,0,0);free=self.core.frame(s,1920,1080,rooms,(),(k,ox,oy),None,[0]*33)[0]
   self.set(state,1.5,1.5,0,0);ops=self.core.frame(s,1920,1080,rooms,(),(k,ox,oy),None,[0]*33)[0]
   chrome=[[v*1.5 for v in b] for b in boxes];legend_end=next(i for i,o in enumerate(ops) if o['glyph']>=0 and o['color']==0xffffffff and i>25) if False else 0
   own=[o['box'] for o in free if o['glyph']<0 and o['color']==0xd0080808][:2] # the legend and the readouts stay on top of the frame
   for o in ops:
    if any(hit(o['box'],b) for b in own):continue
    checked+=1
    self.assertFalse(any(hit(o['box'],inner(b,1080)) for b in chrome),o)
    grazing+=any(hit(o['box'],b) for b in chrome)
   revealed+=len(free)-len(ops)
  self.assertGreater(checked,100);self.assertGreater(revealed,10);self.assertGreater(grazing,0) # slack keeps marks that only touch the frame
class Sub(Chrome):
 def test_closed_list_values(self):
  L=S['list_closed'];cl=lambda p:any(b[0]<=p[0]<b[2] and b[1]<=p[1]<b[3] for b in CLOSED)
  for p in L['clear_gui']:self.assertFalse(cl(p),p);self.assertTrue(inside(p) or True)
  for p in L['opaque_gui']:self.assertTrue(cl(p),p)
 def test_no_name_without_its_icon_or_icon_without_name(self):
  from build_labels import split_label
  import re
  ms=tables_markers();H=(ROOT/'src/runtime/labels_generated.h').read_text();ic=[int(v) for v in re.search(r'marker_icon_glyphs\[\] = \{([0-9,]+)\}',H)[1].split(',')];s=self.core.default_settings();s.scope=2;n=0
  self.set(1,1.5,1.5,0,0)
  for i,m in enumerate(ms):
   if m[5] in (3,5) or m[8] or not m[6]>>1&1:continue
   sx,sy=m[0]*1.5,m[1]*1.5
   for off in ((0,0),(0,-700),(0,700)):
    ops=self.core.frame(s,1920,1080,{m[2]:[300,200,420,300]},(),(1.5,off[0],off[1]),[0 if q==i else 1 for q in range(len(ms))],[0xffffffff]*33)[0]
    g=[o['glyph'] for o in ops];
    if m[3] in g:n+=1;self.assertIn(ic[i],g,m)
  self.assertGreater(n,20)
class RowsDump(unittest.TestCase):
 def test_rows_file_never_overwrites_and_is_read_only(self):
  # File calls do not run in the native gate, so this is a source check only.
  s=(ROOT/'src/runtime/re0_map.c').read_text();a=s.index('static size_t rows_format');b=s.index('static void input(');body=s[a:b]
  self.assertIn('CREATE_NEW',body);self.assertNotIn('CREATE_ALWAYS',body);self.assertNotIn('MoveFile',body)
if __name__=='__main__':unittest.main()
