"""Weapon rows carry loaded rounds in amount; only stacks show a count."""
import json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from build_labels import WEAPONS,marker_label
class MarkerLabel(unittest.TestCase):
 def row(self,name,amount):return dict(name_en=name,name_ko=name,category='item',amount=dict(normal=amount))
 def test_weapon_has_no_count(self):
  for name in WEAPONS:self.assertEqual(marker_label(self.row(name,7),'normal',1,None),name)
 def test_stacks_keep_count(self):
  self.assertEqual(marker_label(self.row('Shotgun Ammo',7),'normal',1,None),'Shotgun Ammo ×7')
  self.assertEqual(marker_label(self.row('Machinegun Ammo',300),'normal',1,None),'Machinegun Ammo 100%')
 def test_catalogue_family(self):
  # A name the source lists without a count must not gain one from a raw amount.
  listed={r['name'] for p in json.loads((ROOT/'data/room-contents.json').read_text())['places'] for r in p['contents']}
  counted={re.sub(r' \(.*\)$','',n) for n in listed if '×' in n}
  rows=json.loads((ROOT/'data/placements.json').read_text())['rows'];wrong=set()
  for r in rows:
   if r['category']=='item' and r['name_en'] not in counted:
    for mode,a in r['amount'].items():
     if '×' in marker_label(r,mode,1,None):wrong.add((r['name_en'],a))
  self.assertEqual(wrong,set())
if __name__=='__main__':unittest.main()
