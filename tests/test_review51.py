"""Candidate 51, user 2026-11-08: events are a category, legend renumbered, language on the backslash key, cool-grey common items, [Colors] in the INI."""
import ctypes,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for f in ('emulator','tests'):sys.path.insert(0,str(ROOT/f))
from core import Core,Settings
from frame_contract import category_rules,tables,rows_of
INI=(ROOT/'packaging/RE0.AnnotatedMap.ini').read_text()
class Renumbering(unittest.TestCase):
 def setUp(self):self.core=Core()
 def real_default(self):
  s=Settings();self.core.library.re0_settings_default(ctypes.byref(s));return s # the emulator's helper turns every category on
 def test_keys_2_to_8_follow_the_legend_order_and_9_is_the_scope(self):
  expect={'2':0,'3':1,'4':2,'5':3,'6':6,'7':4,'8':5} # [6] is events, [7] common items, [8] enemies
  for key,cat in expect.items():
   s=self.real_default();self.core.key(s,key);self.assertEqual(s.mask,63^(1<<cat),key) # events (bit 6) start off, so key 6 turns them on
  s=self.core.default_settings();self.core.key(s,'9');self.assertEqual((s.scope,s.english),(1,0))
 def test_backslash_switches_the_language_and_nothing_else(self):
  s=self.core.default_settings();before=(s.scope,s.mask,s.item_names);self.assertEqual(self.core.key(s,'\\'),1);self.assertEqual(s.english,1);self.assertEqual((s.scope,s.mask,s.item_names),before)
 def test_runtime_reads_the_backslash_vk(self):
  src=(ROOT/'src/runtime/re0_map.c').read_text();self.assertIn("edge(VK_OEM_5))changed|=re0_settings_key(&cfg,'\\\\',",src) # VK_OEM_5 is the backslash key, Won on Korean keyboards
  self.assertNotIn("edge('H'))changed|=re0_settings_key(&cfg,'9'",src)
 def test_legend_text_in_both_languages(self):
  src=(ROOT/'tools/build_labels.py').read_text()
  for text in ('[5] 퍼즐','[6] 이벤트','[7] 일반 아이템','[8] 적','[9] 방문한 방','[\\\\] 언어: 한국어','[5] Puzzles','[6] Events','[7] Items','[8] Enemies','[\\\\] LANGUAGE: ENGLISH'):self.assertIn(text,src)
 def test_old_contents_gain_the_event_bit_from_puzzles(self):
  f=self.core.library.re0_settings_contents;f.argtypes=[ctypes.c_int,ctypes.c_int];f.restype=ctypes.c_uint
  self.assertEqual([f(50,63),f(0,55),f(44,8),f(50,127),f(51,127)],[63,55,8,63,63]) # users decision 2026-11-08: events are spoilers, off after any migration, also from Version 51 which had copied the puzzle bit
  self.assertEqual([f(52,55),f(52,64),f(52,127),f(52,200)],[55,64,127,72]) # a current file keeps the user's choice (bits above 6 dropped)
  self.assertEqual(self.real_default().mask,63) # new installs: events off
class Ini(unittest.TestCase):
 def test_shipped_ini_has_every_colour_at_its_default_and_the_new_version(self):
  self.assertIn('Version=52',INI);self.assertIn('Contents=63',INI)
  want={'Lock':'FFCD46','KeyItem':'5ADCFF','File':'FF8CD2','Puzzle':'FF9628','Event':'B070FF','Item':'B8BCC4','Enemy':'EB3C3C'}
  got=dict(re.findall(r'^(\w+)=#([0-9A-F]{6})$',INI.split('[Colors]')[1],re.M));self.assertEqual(got,want)
 def test_saving_the_shipped_ini_with_its_own_values_changes_nothing(self):
  core=Core();m=core.library.re0_ini_merge;m.argtypes=[ctypes.c_char_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_char_p),ctypes.POINTER(ctypes.c_char_p),ctypes.c_uint,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint];m.restype=ctypes.c_uint
  pairs=re.findall(r'^(\w+)=(\d+)$',INI.split('[Colors]')[0],re.M);keys=(ctypes.c_char_p*len(pairs))(*[k.encode() for k,_ in pairs]);vals=(ctypes.c_char_p*len(pairs))(*[v.encode() for _,v in pairs]);out=ctypes.create_string_buffer(8192)
  old=INI.encode();n=m(old,len(old),keys,vals,len(pairs),b'[Colors]\r\nx=1\r\n',out,8192);self.assertEqual(out.raw[:n],old)
 def test_category_rules_through_the_contract(self):category_rules(Core()) # also run, with mutants, by test_frame
if __name__=='__main__':unittest.main()
