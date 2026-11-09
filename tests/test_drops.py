"""Dropped items. Fixture: live Ink Ribbon, slot 589 (candidate 33); other rows synthetic, labelled by their use. Projection is checked over every placed table row."""
import ctypes,json,re,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for f in ('tools','emulator','tests'):sys.path.insert(0,str(ROOT/f))
from core import Core,ArrangeView
H=(ROOT/'src/runtime/labels_generated.h').read_text();ints=lambda n:[int(v) for v in re.search(n+r'\[\] = \{([0-9,]+)\}',H)[1].split(',')];define=lambda n:int(re.search(rf'#define {n} (\d+)',H)[1])
ITEMS=ints('drop_items');NO=define('NO_ICON');FIRST=define('ICON_FIRST_GLYPH');NATIVE=json.loads((ROOT/'data/native-map.json').read_text())['map_pieces'];CANVAS=json.loads((ROOT/'data/room-layout.json').read_text())['pieces'];INDEX={p['id']:i for i,p in enumerate(NATIVE)};COUNT=589
S=json.loads((ROOT/'tests/fixtures/live-samples.json').read_text())['drop_row']
def frame(core,room,item,amount,pos,piece,kind=0x71,link=None,**kw):
 buf=bytearray(0x30+0x4e8*0x5c)
 for s in range(COUNT,0x4e8):struct.pack_into('<I',buf,0x2c+s*0x5c,0xffffffff)
 o=0x30+COUNT*0x5c;struct.pack_into('<I',buf,0x2c+COUNT*0x5c,room if link is None else link);struct.pack_into('<III',buf,o,0,kind,item);struct.pack_into('<3f',buf,o+0x20,*pos);struct.pack_into('<I',buf,o+0x3c,amount)
 raw=ctypes.create_string_buffer(bytes(buf),len(buf));view=ArrangeView(COUNT,ctypes.cast(raw,ctypes.c_char_p),0,None)
 s=core.default_settings();s.scope=2;[setattr(s,a,b) for a,b in kw.items()];k=1.5;room_pieces=[p['id'] for p in NATIVE if p['native_room_id']==NATIVE[INDEX[piece]]['native_room_id'] and p['floor']==NATIVE[INDEX[piece]]['floor'] and p['id'] in CANVAS]
 return core.frame(s,1920,1080,{INDEX[q]:[v*k for v in CANVAS[q]] for q in room_pieces},(),(k,0,0),[1]*define('MARKER_COUNT'),[0]*33,arrange=view)[0]
DROP_ALPHA=0xa6*(80*255//100)//255 # 65% drop icon at the default icon opacity 80
class Drops(unittest.TestCase):
 def setUp(self):self.core=Core();self.ink=ITEMS[55*7+4];self.pos=S['position']
 def live(self,**kw):return frame(self.core,S['slot_room_at_2c'],S['item'],S['current_amount_at_3c'],self.pos,'i_sh0090',**kw)
 def test_live_row_draws_icon_name_count_at_its_place(self):
  ops=self.live();icon=[o for o in ops if o['glyph']==self.ink];self.assertEqual(len(icon),1)
  g=[o['glyph'] for o in ops];self.assertIn(ITEMS[55*7],g);self.assertIn(define('DROP_MULT'),g);self.assertIn(ints('digit_ids')[2],g)
  b=icon[0]['box'];side=b[2]-b[0];self.assertAlmostEqual((b[0]+b[2])/2,S['canvas'][0]*1.5,delta=2);self.assertAlmostEqual((b[1]+b[3])/2,S['canvas'][1]*1.5,delta=2)
 def test_freed_kind_zero_and_toggles(self):
  self.assertNotIn(self.ink,[o['glyph'] for o in self.live(link=0xffffffff)])
  self.assertNotIn(self.ink,[o['glyph'] for o in self.live(kind=0)])
  self.assertNotIn(self.ink,[o['glyph'] for o in self.live(mask=127&~(1<<4))])
  self.assertNotIn(ITEMS[55*7],[o['glyph'] for o in self.live(item_names=0)])
 def test_other_floor_not_drawn(self):
  o=frame(self.core,36,55,2,self.pos,'i_sh00a0');self.assertNotIn(self.ink,[x['glyph'] for x in o])
 def test_every_real_id_draws_its_icon_see_through(self):
  # Live: Herbal Mix, Handgun and others had no icon. Every id the table names, including variants such as 3 and 4, 46 to 51.
  n=0
  for i in range(len(ITEMS)//7):
   if ITEMS[i*7]==define('NO_LINE'):continue
   ops=frame(self.core,36,i,1,self.pos,'i_sh0090');o=[q for q in ops if q['glyph']==ITEMS[i*7+4]];self.assertEqual(len(o),1,i);self.assertEqual(o[0]['color']>>24,DROP_ALPHA,i);self.assertNotEqual(ITEMS[i*7+4],NO,i);n+=1
  self.assertGreater(n,140)
 def test_icon_centres_on_the_live_dots(self):
  # Sprite dump and rows-04 of one F8: replayed with that capture's view.
  L=json.loads((ROOT/'tests/fixtures/live-samples.json').read_text())['drop_dots'];k=L['view'][0];bad=[]
  for d in L['dots']:
   ops=frame(self.core,36,d['item'],2,d['pos'],'i_sh0090')
   o=[q for q in ops if q['glyph']==ITEMS[d['item']*7+4]][0]['box'];cx=((o[0]+o[2])/2)/1.5*k+L['view'][1];cy=((o[1]+o[3])/2)/1.5*k+L['view'][2]
   if abs(cx-d['dot'][0])>3 or abs(cy-d['dot'][1])>3:bad.append((d['item'],round(cx,1),round(cy,1),d['dot']))
  self.assertEqual(bad,[])
 def test_mix_ids_have_their_own_icon_and_name(self):
  # Game's item text 46-51. Six different icons, each the manifest's entry with that item id; one name.
  man=json.loads((ROOT/'assets/icons/manifest.json').read_text());mixes={46:'G+G',47:'G+G+G',48:'G+R',49:'G+B',50:'G+G+B',51:'G+R+B'}
  for name,i in man['item_ids'].items():self.assertEqual(ITEMS[i*7+4],FIRST+man['names'].index(name),name);self.assertTrue(name.endswith(mixes[i]))
  self.assertEqual(len({ITEMS[i*7+4] for i in mixes}),6);self.assertEqual(len({ITEMS[i*7] for i in mixes}),1);self.assertEqual(len({ITEMS[i*7+2] for i in mixes}),1) # user: the game's one name
 def test_whole_item_table(self):
  names=json.loads((ROOT/'data/item-names.json').read_text());self.assertEqual(len(ITEMS)//7,max(map(int,names))+1)
  for i in range(len(ITEMS)//7):
   n=names.get(str(i),{}).get('en','');real=n.strip() and n!='Invalid Message' and n!='Nothing' and not n.endswith('-NULL')
   self.assertEqual(ITEMS[i*7]!=define('NO_LINE'),bool(real),n)
   if ITEMS[i*7+4]!=NO:self.assertTrue(FIRST<=ITEMS[i*7+4]<FIRST+120)
 def test_unmapped_ids_draw_a_generic_mark(self):
  for item in (1,9999):
   ops=frame(self.core,36,item,1,self.pos,'i_sh0090');self.assertTrue([o for o in ops if o['glyph']<0 and o['color']==(DROP_ALPHA<<24|0xa0a0a0)],item)
 def test_every_placed_table_row_projects_to_its_place(self):
  rows=[r for r in json.loads((ROOT/'data/placements.json').read_text())['rows'] if r.get('evidence')=='arrange table' and r.get('x') is not None and not r.get('moved_into_room') and not r.get('placeholder_position') and r['world'][1]>-1000 and r['category']!='enemy'];bad=[];n=0
  for r in rows:
   ops=frame(self.core,r['room'],55,1,r['world'],r['piece']);o=[q for q in ops if q['glyph']==self.ink]
   if not o:bad.append((r['name_en'],'none'));continue
   n+=1;b=o[0]['box'];c=CANVAS[r['piece']];x,y=r['x'],r['y']
   if abs((b[0]+b[2])/2-x*1.5)>1.5 or abs((b[1]+b[3])/2-y*1.5)>1.5:bad.append((r['name_en'],r['room'],x,y,b))
  self.assertEqual(bad,[]);self.assertGreater(n,200)
if __name__=='__main__':unittest.main()
