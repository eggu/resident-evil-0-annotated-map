import json,re,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
rows=json.loads((ROOT/'data/placements.json').read_text())['rows'];audit=json.loads((ROOT/'verification/event-audit.json').read_text())['rows'];states=json.loads((ROOT/'verification/state-flags.json').read_text())['rows']
class EventsTest(unittest.TestCase):
 def mark(self,scene,group):return next((i,r) for i,r in enumerate(rows) if 'done_flag' in r and r['script']['scene']==scene and r['script']['group']==group)
 def shown(self,scene,group,flag_on):
  # The real frame path, room drawn, one synthetic flag set per state. Scripts, not the game, say which flags these are.
  sys.path[:0]=[str(ROOT/'emulator'),str(ROOT/'tools')]
  from core import Core
  from build_labels import marker_defs
  native=json.loads((ROOT/'data/native-map.json').read_text());_,r=self.mark(scene,group);defs=marker_defs(dict(rows=rows),native);i=next(k for k,d in enumerate(defs) if d['row']==self.mark(scene,group)[0])
  header=(ROOT/'src/runtime/labels_generated.h').read_text();event=int(re.search(r'#define EVENT_MARK_ID (\d+)',header).group(1));canvas=[tuple(float(v[:-1]) for v in c.split(',')) for c in re.findall(r'\{([-0-9.]+f,[-0-9.]+f,[-0-9.]+f,[-0-9.]+f)\}',header.split('piece_canvas[] = {',1)[1].split('};',1)[0])]
  piece=defs[i]['piece'];flags=[0]*71
  state=json.loads((ROOT/'data/room-state.json').read_text())['pieces'][native['map_pieces'][piece]['id']]['visited']
  for f in [*state,*flag_on]:flags[f>>5]|=1<<(f&31)
  core=Core();off=[1]*len(defs);off[i]=0;box=[v*1.5 for v in canvas[piece]]
  return any(o['glyph']==event for o in core.frame(core.default_settings(),1920,1080,{piece:box},(),(1.5,0,0),off,flags[:33])[0])
 def test_large_hall_key_through_its_states(self):
  # Live report 2026-11-05: taking the key in the Large Hall on 3F ran an event with nothing on the map.
  i,key=self.mark('sh1d',15);self.assertEqual((key['floor'],key['done_flag'],states[i]['done_flag'],key.get('need_flag')),('3f',178,178,None))
  table=next(r for r in rows if r.get('item')==68 and r.get('kind')==113);self.assertEqual((key['x'],key['y']),(table['x'],table['y']))
  self.assertTrue(self.shown('sh1d',15,[]),'room entry, before taking it')
  self.assertFalse(self.shown('sh1d',15,[178]),'after, and on re-entry: the flag stays')
 def test_stinger_group_through_its_states(self):
  # Live report 2026-11-05: the Stinger's appearance had no mark. That tr0b g6 is that event is inferred: the movie was not viewed.
  i,s=self.mark('tr0b',6);self.assertEqual((s['piece'],s['done_flag'],states[i]['done_flag'],s['need_flag']),('i_tr0ba0',78,78,120))
  self.assertFalse(self.shown('tr0b',6,[]),'room entry with its precondition clear')
  self.assertTrue(self.shown('tr0b',6,[120]),'just before it runs')
  self.assertFalse(self.shown('tr0b',6,[120,78]),'after, and on re-entry')
  self.assertFalse(self.shown('tr0b',6,[78]),'other branch: done without the precondition')
 def test_power_regulator_is_a_puzzle(self):
  # User report 2026-11-10: Torture Room B showed an event where the power regulator puzzle is.
  # Follow-up 2026-11-10: the event stays too, both marks.
  both=[r for r in rows if 'done_flag' in r and (r['script']['scene'],r['script']['group'])==('dm02',5)]
  self.assertEqual(sorted((r['event'],r['name_en'],r['done_flag'],r['room'],r['x'],r['y']) for r in both),[(0,'Power Regulator',10,88,607.0,265.0),(1,'Event',10,88,607.0,265.0)])
 def test_script_puzzles_have_both_marks(self):
  for scene,group in [('pl01',6),('sh00',15),('tr00',2)]:
   both=[r for r in rows if 'done_flag' in r and (r['script']['scene'],r['script']['group'])==(scene,group)]
   self.assertEqual(sorted(r['event'] for r in both),[0,1],scene);self.assertEqual(len({(r['x'],r['y'],r['done_flag']) for r in both}),1,scene)
 def test_item_puzzle_with_a_cutscene_has_an_event(self):
  # User 2026-11-10: every puzzle that runs an event shows both marks. The event is done when its puzzle is.
  ev={rows[r['puzzle_row']]['name_en']:(i,r) for i,r in enumerate(rows) if 'puzzle_row' in r and r['event']}
  self.assertTrue({'Panel Opener','Magnetic Card','Vise Handle','Input Regulator Coil','Unity Tablet'}<=set(ev),sorted(ev))
  self.assertNotIn('Battery',ev) # its use group has no cutscene
  for i,r in ev.values():
   p=rows[r['puzzle_row']];self.assertEqual((r['event'],r['x'],r['y']),(1,p['x'],p['y']))
   self.assertEqual((states[i]['done_flag'],states[i]['store']),(states[r['puzzle_row']]['done_flag'],states[r['puzzle_row']]['store']))
 def test_every_group_is_accounted_for(self):
  self.assertEqual({r['status'] for r in audit},{'script_read','unresolved','excluded','named_puzzle'})
  drawn={(r['script']['scene'],r['script']['group']) for r in rows if 'done_flag' in r}
  self.assertEqual(drawn,{(r['scene'],r['group']) for r in audit if r['status']=='script_read'}|{('sh12',7),('dm0a',8)}) # named puzzles that keep a flag
  for r in audit:self.assertTrue(r['reason'])
 def test_named_puzzles_replace_their_event(self):
  # User 2026-11-11: one puzzle mark each. Crates and Piano go with their pickup row, Chessboard and Control Panel with a flag.
  named={r['name_en']:(i,r) for i,r in enumerate(rows) if r['category']=='puzzle' and (r['script'].get('scene'),r['script'].get('group')) in {('pl0d',6),('sh1a',5),('sh12',7),('dm0a',8)}}
  self.assertEqual(sorted(named),['Chessboard','Control Panel','Crates','Piano'])
  for i,r in named.values():self.assertEqual(r['event'],0)
  for name,item in (('Crates',87),('Piano',94)):
   i,r=named[name];p=r['puzzle_row'];self.assertEqual((rows[p]['item'],rows[p]['room'],r['item'],r['kind']),(item,r['room'],item,113));self.assertEqual(states[i]['slot'],states[p]['slot'])
  self.assertEqual((states[named['Chessboard'][0]]['done_flag'],states[named['Control Panel'][0]]['done_flag']),(169,205))
 def test_room_setup_and_cleared_flags_never_draw(self):
  self.assertTrue(all(r['status']=='excluded' for r in audit if r['tag']==18))
  for r in audit:
   if 'cleared again' in r['reason']:self.assertEqual(r['status'],'unresolved')
 def test_room_level_never_looks_placed(self):
  for r in rows:
   if r.get('event'):self.assertEqual('room level' in r['evidence'],'(room)' in r['name_en'],r['evidence'])
 def test_existing_rows_keep_their_indexes(self):
  # Event rows are appended after every other row. Indexes are build-internal, nothing persists them.
  first=next(i for i,r in enumerate(rows) if 'done_flag' in r or 'puzzle_row' in r)
  self.assertTrue(all('done_flag' in r or 'puzzle_row' in r for r in rows[first:]));self.assertGreater(first,700)
if __name__=='__main__':unittest.main()
