from pathlib import Path
import sys,unittest,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'emulator'))
from annotations import replay,catalogue,tables
HASH='67418c3a307b49e9bde8123df4cad1fa910f3a29adc3e4c0ba64eb96524bc14b'
def fixture():
 return dict(schema_version=1,profile_sha256=HASH,evidence='synthetic-resource-preview',region=0,target=[1280,720],settings=dict(size=100,opacity=70,english=0),rooms=[dict(index=0,box=[300,300,400,340])],obstacles=[[300,300,400,340]])
class ReplayTests(unittest.TestCase):
 def test_obstacle_moves_label_and_render_has_pixels(self):
  image,r=replay(fixture());b=r['placement'][0]['box']
  self.assertIsNotNone(b);self.assertTrue(b[3]<=298 or b[1]>=342 or b[2]<=298 or b[0]>=402)
  self.assertIsNotNone(image.getchannel('R').getextrema());self.assertGreater(image.getchannel('R').getextrema()[1],45)
 def test_profile_region_duplicates_and_bounds_refused(self):
  for key,value in [('profile_sha256','unsupported'),('region',9),('target',[0,720]),('rooms',[dict(index=0,box=[300,300,400,340])]*2),('obstacles',[[float('nan'),0,1,1]]),('settings',dict(size=100,opacity=70,english=0,difficulty=7))]:
   f=fixture();f[key]=value
   with self.subTest(key=key),self.assertRaises(ValueError):replay(f)
 def test_catalogue_unique_and_bounded(self):
  rooms,glyphs,image=catalogue();self.assertEqual(len(rooms),138)
  self.assertEqual(sum(row[3] for row in rooms),138)
  self.assertEqual(len({r[:2] for r in rooms}),len(rooms))
  for x,y,w,h in glyphs:self.assertTrue(0<=x<x+w<=image.width and 0<=y<y+h<=image.height)
 def test_section_pieces_merge_and_difficulty_changes_badges(self):
  rooms,_,_=catalogue();data=tables();by={}
  for i,r in enumerate(rooms):by.setdefault(r[6],[]).append(i)
  place,pieces=next((p,v) for p,v in by.items() if len(v)>1 and rooms[v[0]][0]==rooms[v[1]][0])
  f=fixture();f['region']=rooms[pieces[0]][0];f['obstacles']=[];f['rooms']=[dict(index=pieces[0],box=[500,300,600,380]),dict(index=pieces[1],box=[580,300,700,380])]
  _,r=replay(f);self.assertEqual(r['places'],1);self.assertEqual(r['placement'][0]['place'],place)
  self.assertEqual(sum(sum(row[1:4]) for row in data['contents'][:0]),0)
  index=next(i for i,row in enumerate(data['contents']) if sum(1 for v in row[1:4] if v)==1)
  place=next(p for p,row in enumerate(data['places']) if row[2]<=index<row[2]+row[3]);piece=next(i for i,r in enumerate(rooms) if r[6]==place)
  f=fixture();f['region']=rooms[piece][0];f['obstacles']=[];f['rooms']=[dict(index=piece,box=[500,300,700,420])];results=[]
  for mode in range(3):
   f['settings']=dict(f['settings'],difficulty=mode);results.append(replay(f)[1]['placement'][0]['counts'])
  self.assertGreater(len({tuple(c) for c in results}),1)
