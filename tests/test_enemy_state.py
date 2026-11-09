"""Script-given items and enemy kill state in the generated data, and the shared rule on synthetic row memory (labelled so: native values are checked by tools/inspect/check_native_dispatch.py)."""
import ctypes,json,re,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'emulator'))
from core import ArrangeView,Core
LIB=ROOT/'local'/('libre0map.dylib' if sys.platform=='darwin' else 'libre0map.so')
ROWS=0x24ff0+4 # through the mode field
def table(name):
 text=(ROOT/'src/runtime/labels_generated.h').read_text()
 return [[int(v) for v in m.split(',')] for m in re.findall(r'\{([0-9,]+)\}',text.split(name+'[] = {',1)[1].split('};',1)[0])]
class ScriptItems(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rows=json.loads((ROOT/'data/placements.json').read_text())['rows'];cls.states={r['index']:r for r in json.loads((ROOT/'verification/state-flags.json').read_text())['rows']};cls.cross=json.loads((ROOT/'verification/placement-crosscheck.json').read_text())
 def script(self,room,name):return next((i,r) for i,r in enumerate(self.rows) if 'script' in r and r['room']==room and r['name_en']==name)
 def test_officers_car_handgun_ammo(self):
  i,r=self.script(2,'Handgun Ammo');s=self.states[i]
  self.assertEqual((r['category'],r['amount'],r['script']['scene'],r['script']['group']),('item',dict(easy=15,normal=15,hard=15),'tr02',9))
  self.assertEqual((s['done_flag'],s['status']),(0x65,'proven'));self.assertEqual(s['done_any_of'],[0x65,0x79]);self.assertIn('flag set blocks the grant',s['evidence'])
  self.assertEqual(r['trigger'],[667.5,45.0]);self.assertEqual(r['piece'],'i_tr0290');self.assertNotIn('room centre',r['evidence'])
 def test_automatic_events_are_room_level_and_stations_have_no_done_state(self):
  for room,name in ((0,'Brake Operation Manual'),(15,"Player's Manual 2"),(165,'Gate Operation Manual')):
   self.assertIn('room centre',self.script(room,name)[1]['evidence'])
  i,r=self.script(49,'Green Chemical');self.assertEqual((self.states[i]['store'],self.states[i]['done_flag']),('none',None));self.assertIn('trigger volume',r['evidence'])
 def test_every_external_only_row_is_classified(self):
  rows=self.cross['only_external'];self.assertTrue(rows);self.assertEqual({r['class'] for r in rows},{'catalogue-repeat','inside-item'})
  self.assertEqual(sum(r['mode']=='normal' for r in rows),18)
 def test_script_rows_match_the_catalogue(self):
  self.assertFalse([r for r in self.cross['only_external'] if r['name'] in('Brake Operation Manual','Microfilm Image',"Marcus' Diary 1",'Old Photograph','Red Chemical','Blue Chemical')])
class EnemyRows(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.rows=json.loads((ROOT/'data/placements.json').read_text())['rows'];cls.doc=json.loads((ROOT/'verification/state-flags.json').read_text());cls.states={r['index']:r for r in cls.doc['rows']}
 def test_every_enemy_row_has_its_own_slot_per_table(self):
  seen={'easy':set(),'normal':set(),'hard':set()}
  for i,r in enumerate(self.rows):
   if r['category']!='enemy':continue
   slots=self.states[i]['slot']
   self.assertEqual(set(slots),set(r['amount']))
   for m,v in slots.items():
    self.assertLess(v,self.doc['row_store']['table_counts'][m]);self.assertNotIn(v,seen[m]);seen[m].add(v)
 def test_player_rows_are_not_enemies_and_every_enemy_class_is_kept(self):
  kinds={r['kind'] for r in self.rows if r['category']=='enemy'}
  self.assertFalse(kinds&{2,5});self.assertLessEqual({0x6a,0x6b,0x2a},kinds);self.assertTrue(all(0x10<=k<0x70 and k!=0x3b for k in kinds))
 def test_alternate_conditions_are_separate_rows(self):
  here=[r['condition'] for r in self.rows if r['category']=='enemy' and r['room']==150 and r['world'][0]==296]
  self.assertEqual(sorted(here),[173,174]);self.assertFalse([r for r in self.rows if 'condition_also' in r])
 def test_native_class_runs_decide_the_status(self):
  runs=self.doc['native_checks']['enemy_saves']
  self.assertEqual(sorted(hex(int(k)) for k,v in runs.items() if v['at_hp_zero']!=1),['0x47'])
  self.assertEqual(runs[str(0x2a)]['at_hp_zero'],1)
  self.assertEqual({self.rows[r['index']]['name_en'] for r in self.doc['rows'] if r['status']=='live-only'},{'Queen Leech (Second Form)'})
@unittest.skipUnless(LIB.exists(),'needs tools/build_core.py')
class SharedRule(unittest.TestCase):
 """Synthetic row memory."""
 @classmethod
 def setUpClass(cls):
  cls.core=Core();cls.st=table('marker_state');cls.enemy=next(i for i,s in enumerate(cls.st) if s[7]==0x2a and s[1]!=0xffff);cls.item=next(i for i,s in enumerate(cls.st) if s[7]==0x71 and s[1]!=0xffff)
 def view(self,count=589,**rows):
  raw=bytearray(ROWS)
  for i in (self.enemy,self.item):
   s=self.st[i];at=0x30+s[1]*0x5c;struct.pack_into('<III',raw,at,s[6],s[7],s[5] if s[5]!=0xffff else 0)
  return raw
 def done(self,i,raw,killed=None,count=589):
  c=ctypes.create_string_buffer(bytes(raw),len(raw));self.keep=c
  return self.core.marker_done(i,None,ArrangeView(count,ctypes.cast(c,ctypes.c_char_p),0,killed))
 def row(self,i):return 0x30+self.st[i][1]*0x5c
 def test_live_enemy_stays_and_killed_goes(self):
  raw=self.view();self.assertFalse(self.done(self.enemy,raw))
  raw[self.row(self.enemy)+0x41]=1;self.assertFalse(self.done(self.enemy,raw),'row+0x41 is set for every saved actor, alive too')
  raw[self.row(self.enemy)+0x39]=1;self.assertTrue(self.done(self.enemy,raw))
 def test_restored_from_save_mode_field_zero(self):
  raw=self.view();struct.pack_into('<I',raw,0x24ff0,0);raw[self.row(self.enemy)+0x39]=1;self.assertTrue(self.done(self.enemy,raw))
  self.assertFalse(self.done(self.enemy,raw,count=600),'unknown table is unknown')
 def test_enemy_kept_when_actor_rewrites_row_8(self):
  raw=self.view();struct.pack_into('<I',raw,self.row(self.enemy)+8,7);raw[self.row(self.enemy)+0x39]=1;self.assertTrue(self.done(self.enemy,raw))
 def test_kill_in_a_loaded_room_reads_the_slot_bit(self):
  words=(ctypes.c_uint*40)();slot=self.st[self.enemy][1];words[slot>>5]=1<<(slot&31);self.assertTrue(self.done(self.enemy,self.view(),words));words[slot>>5]=0;self.assertFalse(self.done(self.enemy,self.view(),words))
 def test_guard_counts_wrong_rows(self):
  raw=self.view();struct.pack_into('<I',raw,self.row(self.enemy)+4,0x71);raw[self.row(self.enemy)+0x39]=1
  c=ctypes.create_string_buffer(bytes(raw),len(raw));v=ArrangeView(589,ctypes.cast(c,ctypes.c_char_p),0,None);self.assertFalse(self.core.marker_done(self.enemy,None,v));self.assertEqual(v.mismatches,1)
if __name__=='__main__':unittest.main()
