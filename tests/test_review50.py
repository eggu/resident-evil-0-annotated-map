"""Candidate 50, user 2026-11-08: H cycles item names all -> all except common -> off, ItemNames 0 off / 1 all / 2 no common, migrated once from on/off."""
import ctypes,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for f in ('emulator','tests'):sys.path.insert(0,str(ROOT/f))
from core import Core,Settings
from frame_contract import item_name_states
class ItemNames(unittest.TestCase):
 def test_three_states_cycle_and_legend_through_the_contract(self):item_name_states(Core()) # also run, with mutants, by test_frame
 def test_labels_match_the_users_wording(self):
  src=(ROOT/'tools/build_labels.py').read_text()
  for text in ('[H] 아이템 이름: 끔','[H] 아이템 이름: 모두','[H] 아이템 이름: 일반 제외','[H] Item names: Off','[H] Item names: All','[H] Item names: No common'):self.assertIn(text,src)
class Migration(unittest.TestCase):
 def setUp(self):
  c=Core().library.re0_settings_item_names;c.argtypes=[ctypes.c_int,ctypes.c_int];c.restype=ctypes.c_int;self.f=c
 def test_old_on_off_becomes_all_or_off(self):
  for v in (0,44,49):self.assertEqual((self.f(v,0),self.f(v,1),self.f(v,2),self.f(v,7)),(0,1,1,1)) # an old file's 2 was only ever "on"
 def test_new_values_are_kept_and_bad_ones_are_off(self):
  self.assertEqual([self.f(50,v) for v in (0,1,2)],[0,1,2]);self.assertEqual([self.f(50,v) for v in (3,-1,99)],[0,0,0])
 def test_version_50_is_written_and_old_files_report_migration(self):
  s=Settings();core=Core();core.library.re0_settings_default(ctypes.byref(s));f=core.library.re0_settings_ini_sizes;f.argtypes=[ctypes.POINTER(Settings),ctypes.c_int,ctypes.c_int,ctypes.c_int]
  self.assertEqual((f(ctypes.byref(s),44,100,100),f(ctypes.byref(s),50,100,100),f(ctypes.byref(s),52,100,100)),(1,1,0)) # 44..50 are rewritten once with the current Version
  self.assertEqual((s.size,s.icon_size),(100,100)) # sizes are not converted again
  self.assertIn('Version=52',(ROOT/'packaging/RE0.AnnotatedMap.ini').read_text())
if __name__=='__main__':unittest.main()
