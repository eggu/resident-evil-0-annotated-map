"""Room names fixed at generation: the file is current and obeys RE2's rules without the generator's own search."""
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for f in ('tools','tools/extract'):sys.path.insert(0,str(ROOT/f))
L=json.loads((ROOT/'data/room-layout.json').read_text())
class LayoutTests(unittest.TestCase):
 def test_generated_from_current_inputs(self):
  for name,digest in L['inputs_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest,name)
 def test_leaders_are_axis_aligned(self):
  for r in L['rows']:
   if r['line']:self.assertTrue(r['line'][0]==r['line'][2] or r['line'][1]==r['line'][3],r)
 def test_every_piece_group_named_in_both_languages(self):
  self.assertEqual(sum(r['lang']==0 for r in L['rows']),sum(r['lang']==1 for r in L['rows']))
 def test_wrapping_only_between_words(self):
  for r in L['rows']:
   if '\n' in r['text']:self.assertTrue(all(p.strip()==p and p for p in r['text'].split('\n')),r)
 def test_silhouette_fills_the_floor_and_closes_door_gaps(self):
  # Live defect: sprite alpha is walls, so reading it directly sent nearly every name outside.
  from PIL import Image,ImageDraw
  from room_layout import silhouette,cells,W,H
  ring=Image.new('L',(W,H));d=ImageDraw.Draw(ring);d.rectangle((100,100,200,160),outline=255,width=2);d.rectangle((140,100,150,101),fill=0) # outline with a door gap
  got=cells(silhouette(ring));self.assertIn((150,130),got);self.assertIn((145,100),got);self.assertNotIn((90,130),got);self.assertNotIn((210,130),got)
 def test_names_sit_inside_when_they_fit(self):
  by=lambda piece,lang:next(r for r in L['rows'] if r['piece']==piece and r['lang']==lang)
  # The floor the user reported: both Korean names fit their roofs (48 canvas px high, 166 and 170 wide).
  for piece in ('i_tr0eb0','i_tr11b0'):self.assertIsNone(by(piece,0)['line'],piece)
  ko=[r for r in L['rows'] if r['lang']==0];self.assertGreater(sum(not r['line'] for r in ko)/len(ko),.5)

 def test_every_name_anchor_lies_inside_its_room_shape(self):
  # Candidate 44, whole data: all 248 placements, both languages. A leader's anchor is where it leaves the room.
  inside=lambda piece,x,y:any(run[0]==y and run[1]<=x<=run[2] for run in L['shapes'][piece])
  self.assertEqual(len(L['rows']),248)
  for r in L['rows']:
   x,y=(r['line'][0],r['line'][1]) if r['line'] else (r['x'],r['y'])
   self.assertTrue(inside(r['piece'],x,y),r)
 def test_every_shape_belongs_to_a_named_room(self):
  self.assertEqual(set(L['shapes']),{r['piece'] for r in L['rows']});self.assertEqual(len(L['shapes']),124)
 def test_pole_of_inaccessibility_is_deepest_point_not_the_box_centre(self):
  from room_layout import pole,place_floor,Sat,cells
  # An L: the bounding box centre (60,60) is outside it; the pole sits in the thick arm.
  shape={(x,y) for x in range(20,100) for y in range(20,50)}|{(x,y) for x in range(20,50) for y in range(50,100)}
  (px,py),depth=pole(shape);self.assertNotIn((60,60),shape);self.assertEqual(depth[(px,py)],max(depth.values()));self.assertGreaterEqual(depth[(px,py)],14)
  rows=[dict(cells=shape,image=None,name='n')];size=lambda t:(20,8)
  out=place_floor(rows,[],[(300,300,10,10)],size)[id(rows[0])]
  self.assertIsNone(out['line']);self.assertIn((out['x'],out['y']),shape)
  self.assertTrue(all((x,y) in shape for x in range(out['x']-10,out['x']+10) for y in range(out['y']-4,out['y']+4)),'name box inside the shape where it fits')
  self.assertLessEqual((out['x']-px)**2+(out['y']-py)**2,(px-60)**2+(py-60)**2) # not further from the pole than the box centre is
 def test_rule_checker_rejects_violations(self):
  from room_layout import check_floor
  cells={(x,y) for x in range(10,40) for y in range(10,30)};rows=[dict(cells=cells,name='a')];size=lambda t:(10,6);good={id(rows[0]):dict(text='a',x=25,y=20,line=None)}
  check_floor(rows,good,[],[(300,300,10,10)],size)
  with self.assertRaises(ValueError):check_floor(rows,good,[(24,19,4,4)],[(300,300,10,10)],size) # on a mark
  with self.assertRaises(ValueError):check_floor(rows,{id(rows[0]):dict(text='a',x=5,y=5,line=None)},[],[(300,300,10,10)],size) # anchor outside its shape
  with self.assertRaises(ValueError):check_floor(rows,{id(rows[0]):dict(text='a',x=25,y=20,line=(0,0,1,1))},[],[(300,300,10,10)],size) # outside name on a room
if __name__=='__main__':unittest.main()
