"""Values seen in the real game must pass the shared code that once refused them."""
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'emulator'))
from core import Core
class LiveSampleTests(unittest.TestCase):
 def test_live_sprites_produce_a_box(self):
  core=Core();matrix=[1,0,0,0,0,1,0,0,0,0,1,0,300,200,0,1]
  for s in json.loads((ROOT/'tests/fixtures/live-samples.json').read_text())['samples']:
   w,h=s['size'];flip=int(bool(s['sprite_f54']&(1<<22)))
   box=core.project(core.quad(w,h,s['sprite_a0'],flip,matrix),[0,0,1.5,1.5])
   self.assertEqual(box,[(300-w/2)*1.5,(200-h/2)*1.5,(300+w/2)*1.5,(200+h/2)*1.5])
if __name__=='__main__':unittest.main()
