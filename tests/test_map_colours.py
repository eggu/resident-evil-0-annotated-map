"""Emulator map colours against the game: recorded values, the EXE table, the F8 capture and the built page. The EXE and capture parts need local/."""
import json,re,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];C=json.loads((ROOT/'data/map-colours.json').read_text());TABLE=C['face_table']['states']
IMAGE=ROOT/'local/research/re0hd.analysis.bin';CAPTURE=ROOT/'local/live/candidate18/RE0.AnnotatedMap-sprites.json';PAGE=ROOT/'local/placement-review/index.html'
FILL,OUTLINE,BG=0x1a789500,0x1a7894c0,0x1a357650
class MapColours(unittest.TestCase):
 @unittest.skipUnless(IMAGE.exists(),'local analysis image required')
 def test_recorded_table_is_the_exe_table(self):
  b=IMAGE.read_bytes();pe=struct.unpack_from('<I',b,60)[0];n=struct.unpack_from('<H',b,pe+6)[0];sec=pe+24+struct.unpack_from('<H',b,pe+20)[0];rva=0xd9de40-0x400000
  at=next(rp+rva-v for i in range(n) for vs,v,rs,rp in [struct.unpack_from('<4I',b,sec+i*40+8)] if v<=rva<v+max(vs,rs))
  self.assertEqual({str(i):b[at+i*4:at+i*4+4].hex() for i in range(8)},TABLE)
  # The read site: lea eax,[edi*4+0xd9de40].
  rs=0x5b4cfc-0x400000;site=next(rp+rs-v for i in range(n) for vs,v,_,rp in [struct.unpack_from('<4I',b,sec+i*40+8)] if v<=rs<v+vs);self.assertEqual(b[site:site+7].hex(),'8d04bd40ded900')
 @unittest.skipUnless(CAPTURE.exists(),'local capture required')
 def test_capture_agrees(self):
  sprites=[(s['texture'],bytes.fromhex(s['bytes'])[0xb0:0xb4].hex()) for s in json.loads(CAPTURE.read_text())['sprites']]
  fill={c for t,c in sprites if t==FILL};self.assertEqual(fill,{TABLE['1'],TABLE['4']})
  self.assertEqual({c for t,c in sprites if t==OUTLINE},{C['outline']['vertex_color']});self.assertEqual({c for t,c in sprites if t==BG},{C['background']['vertex_color']})
 def test_page_uses_the_recorded_values(self):
  if not PAGE.exists():self.skipTest('needs the locally built page')
  text=PAGE.read_text();D=json.loads(text[text.index('const D=')+8:text.index(';\nconst T=')])
  self.assertEqual(D['face_colours'],[TABLE[str(i)] for i in range(8)]);self.assertEqual(D['bg']['xy'],C['background']['canvas_xy'])
  self.assertTrue(all('face_colours' in text and p['fill'] in (True,False) for f in D['floors'] for p in f['sprites']))
  self.assertEqual({p['fill'] for f in D['floors'] for p in f['sprites']},{True,False})
  self.assertIn("D.face_colours[st]",text);self.assertNotIn('#a09b8c',text.split('<script>')[1].split('const D=')[0])
if __name__=='__main__':unittest.main()
