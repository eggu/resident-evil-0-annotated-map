"""Placement parsers refuse wrong layouts, and the location data keeps the properties that made it trustworthy."""
import json,os,re,shutil,struct,subprocess,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools/extract'))
from arrange import parse as parse_arrange
from event_collision import parse as parse_collision
from event_disasm import decode,SIZES
def record(kind,item,amount,x,z):return struct.pack('<6BH',kind,item,0,0,0,255,amount)+struct.pack('<6f',x,0,z,0,0,0)
def table(rows):return b'loc2'+struct.pack('<II',1,1)+struct.pack('<HH',7,len(rows))+b''.join(rows)
class Commands:ops=[('nop',[],0),('door',['U2','U1','U2','U2'],0),('flag',['Fn','Rn','F4'],0)]
class ParserTests(unittest.TestCase):
 def test_hunter_kind_is_named(self):
  rows=json.loads((ROOT/'data/placements.json').read_text())['rows']
  self.assertEqual({r['name_en'] for r in rows if r.get('kind')==0x2f},{'Hunter'})
 def test_every_puzzle_at_its_trigger(self):
  d=json.loads((ROOT/'data/placements.json').read_text());rows=[r for r in d['rows'] if r['category']=='puzzle' and not r.get('event')]
  self.assertEqual(d['puzzles_without_position'],[]);self.assertEqual(len(rows),37)
  for r in rows:self.assertIn('trigger volume',r['evidence'],r['name_en']);self.assertLessEqual(r['distance'],2,r['name_en'])
 def test_statue_room_lighter_is_placed(self):
  # User report 2026-11-10: no puzzle in the Statue Room, B2. Six statues, one mark between them; filled Lighter 106, not 105.
  r=next(r for r in json.loads((ROOT/'data/placements.json').read_text())['rows'] if r['category']=='puzzle' and r['name_en']=='Lighter')
  self.assertEqual((r['room'],r['script']['item'],r['script']['groups'],r['distance']),(90,106,[16,17,18,19,20,21],0.0))
 def test_cable_car_puzzle_is_always_shown(self):
  # User 2026-11-11: Cable Car, Laboratory B2, showed only the Magnum. A repeatable ride, so a puzzle mark with no done flag.
  rows=json.loads((ROOT/'data/placements.json').read_text())['rows'];states=json.loads((ROOT/'verification/state-flags.json').read_text())['rows']
  i=next(i for i,r in enumerate(rows) if r['category']=='puzzle' and r['room']==111)
  self.assertEqual((rows[i]['name_en'],rows[i]['event'],states[i]['done_flag']),('Cable Car',0,None))
 def test_storage_lift_is_always_shown(self):
  # User 2026-11-11: the Storage lift, Treatment Plant B9, marked because it matters, not as a puzzle.
  rows=json.loads((ROOT/'data/placements.json').read_text())['rows'];states=json.loads((ROOT/'verification/state-flags.json').read_text())['rows']
  i=next(i for i,r in enumerate(rows) if r['category']=='puzzle' and r['room']==173)
  self.assertEqual((rows[i]['name_en'],rows[i]['event'],rows[i]['piece'][:7],states[i]['done_flag']),('Elevator',0,'i_pl200',None))
 def test_turntable_yard_name_on_either_piece(self):
  # User 2026-11-11, Factory 1F: the game drew the small yard piece i_bt0290 and the name sat off it, on i_bt0291.
  L=json.loads((ROOT/'data/room-layout.json').read_text());b=L['pieces']['i_bt0290']
  for r in L['rows']:
   if r['piece']=='i_bt0291':self.assertTrue(b[0]<=r['x']<=b[2] and b[1]<=r['y']<=b[3],(r['x'],r['y']))
 def test_factory_dial_and_elevator_key(self):
  # User 2026-11-11: the yard's Dial is a row under the world that is only ever deleted; the Elevator Key was picked up on B4.
  rows=json.loads((ROOT/'data/placements.json').read_text())['rows']
  self.assertEqual([(r['room'],r['floor']) for r in rows if r['name_en']=='Dial' and r['category']=='key'],[(109,'b1')])
  k=next(r for r in rows if r['name_en']=='Elevator Key' and r['category']=='key');self.assertEqual((k['room'],k['floor'],k['piece']),(134,'b4','i_bt0250'))
 def test_keycard_lock_on_engine_room_door(self):
  # User report 2026-11-11: no lock in the Engine Room, B9. The reader sets 0x2d, this door's Flag.
  d=json.loads((ROOT/'data/placements.json').read_text());self.assertEqual(d['locks_without_door'],[])
  self.assertEqual([(r['piece'],r['door_flag']) for r in d['rows'] if r['category']=='lock' and r['name_en']=='Keycard'],[('i_door_3d_2d',0x2d)])
 def test_air_regulator_room_rows_on_b6(self):
  # User 2026-11-11: the herbs shown at the B5 Control Room entrance are on B6, with the zombies and the Empty Bottle.
  rows=[r for r in json.loads((ROOT/'data/placements.json').read_text())['rows'] if r['room']==142 and r.get('world')]
  self.assertEqual(sorted((r['name_en'],r['floor']) for r in rows if r['world'][1]<200),[('Empty Bottle','b6'),('Green Herb','b6'),('Red Herb','b6'),('Zombie','b6'),('Zombie','b6'),('Zombie','b6')])
  self.assertEqual({r['floor'] for r in rows if r['world'][1]>=200},{'b5'})
 def test_piano_bar_battery_follows_its_stand(self):
  # User 2026-11-10: put back on its stand, the Battery had no key mark. 0x9b: set by taking it (sh1a g6), cleared by putting it back (g7).
  rows=json.loads((ROOT/'data/placements.json').read_text())['rows'];states=json.loads((ROOT/'verification/state-flags.json').read_text())['rows']
  i=next(i for i,r in enumerate(rows) if r['name_en']=='Battery' and r['room']==62 and r.get('kind')==120)
  self.assertEqual(states[i]['done_flag'],0x9b);self.assertFalse(any(r['name_en']=='Battery' and r['room']==62 and r['category']=='puzzle' for r in rows))
 def test_door_form_item_use_binds_its_volume(self):
  # ch01 g2 shape: tag 30, x = volume, y = item; a door script behind SubItemJp. tag 8 stays bound.
  import placements as P
  groups=lambda data:[((30,1,0,104),2),((8,3,4,104),5)]
  original=P.groups;P.groups=groups
  try:self.assertEqual(P.puzzle_trigger(b'',104,None),None) # two volumes, ambiguous
  finally:P.groups=original
  P.groups=lambda data:[((30,1,5,104),2)]
  try:self.assertEqual(P.puzzle_trigger(b'',104,None),([0],5))
  finally:P.groups=original
 def test_arrange_fields(self):
  r=parse_arrange(table([record(0x71,77,1,82,186)]))[0]
  self.assertEqual((r['room'],r['records'][0]['kind'],r['records'][0]['item'],r['records'][0]['amount'],r['records'][0]['pos'][0]),(7,0x71,77,1,82.0))
 def test_arrange_refuses_wrong_layout(self):
  for bad in (b'nope'+table([])[4:],table([record(1,1,1,0,0)])+b'x'*64):
   with self.assertRaises(ValueError):parse_arrange(bad)
 def test_disassembler_stops_at_group_bounds(self):
  code=struct.pack('>HHBHH',1,3,0,1,0)
  self.assertEqual(decode(code,0,len(code),Commands)[0][1:],('door',[3,0,1,0]))
  with self.assertRaises(ValueError):decode(code,0,len(code)-1,Commands)
  with self.assertRaises(ValueError):decode(struct.pack('>H',99),0,2,Commands)
 def test_flag_and_register_argument_sizes_match_native_reader(self):
  self.assertEqual((SIZES['Fn'][0],SIZES['Rn'][0],SIZES['F4'][0]),(2,1,4))
 def test_collision_refuses_bad_list_size(self):
  head=b'data\0'+b'\0'*24+struct.pack('<I',1<<8|1)[:4]+b'\0'
  body=struct.pack('<HHII',5,2,999,1)+b'\0'*48+struct.pack('<II',1,2)
  with self.assertRaises(ValueError):parse_collision(head+body)
class DataTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=json.loads((ROOT/'data/placements.json').read_text())
 def test_true_scale_beats_every_wrong_scale(self):
  fit=self.d['wall_fit'];true=fit['native 0.07']
  self.assertLess(true['median_edge_error'],2)
  for name,row in fit.items():
   if name!='native 0.07':self.assertGreater(row['p90'],true['p90']*2,name)
 def test_game_table_rows_lie_in_their_rooms(self):
  rows=[r for r in self.d['rows'] if 'world' in r]
  self.assertGreater(len(rows),600)
  self.assertLessEqual(sum(1 for r in rows if r['distance'] is None or r['distance']>3),0)
 def test_every_legend_group_present_and_room_level_marked(self):
  groups={r['category'] for r in self.d['rows']}
  self.assertEqual(groups,{'lock','key','file','puzzle','item','enemy'})
  for r in self.d['rows']:
   if 'world' not in r:self.assertTrue('door instance' in r['evidence'] or 'room centre' in r['evidence'] or 'trigger volume' in r['evidence'] or 'table row' in r['evidence'] or 'room level' in r['evidence'],r['evidence'])
@unittest.skipUnless(shutil.which('node'),'Node required')
class ReviewTests(unittest.TestCase):
 def test_game_zoom_matches_shared_c_transform(self):
  sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'emulator'))
  from build_placement_review import PAGE
  from core import Core
  fn=re.search(r'function gameView.*',PAGE)[0];core=Core()
  for fx,fy,t in [(640,360,1),(300,500,1),(900,120,.5),(100,100,0)]:
   out=json.loads(subprocess.check_output(['node','-e',f'{fn};console.log(JSON.stringify(gameView({fx},{fy},{t})))'],text=True))
   n=core.transform(t,(fx,fy))
   self.assertAlmostEqual(out['k'],n.scale,5)
   # A point at canvas (X,Y) lands at 640+scale*(X-640)+tx in both.
   self.assertAlmostEqual(out['k']*fx+out['ox'],640+n.scale*(fx-640)+n.translate_x,3)
   self.assertAlmostEqual(out['k']*fy+out['oy'],360+n.scale*(fy-360)+n.translate_y,3)
GAME=Path(os.environ.get('RE0_GAME','/nonexistent')) # your own game folder containing re0hd.exe
@unittest.skipUnless(GAME.exists(),'needs the local game files')
class DoorSizeTests(unittest.TestCase):
 def test_painted_part_matches_the_live_screenshot(self):
  # Live crop 2026-11-03: doors measured about 21x8 and 8x22 screen px at 1080p, scale 1.5, so about 14x6 and 6x14 canvas px. The quad is 26x8.
  sys.path.insert(0,str(ROOT/'emulator'));from render import door_ink
  box=lambda rect:(lambda b:(b[2]-b[0],b[3]-b[1]))(door_ink(GAME,rect))
  self.assertEqual(box((0,16,26,24)),(14,6));self.assertEqual(box((48,0,56,26)),(6,14))
  self.assertEqual(box((0,24,26,32)),(22,6));self.assertEqual(box((56,0,64,26)),(6,22))
class RealFloorTests(unittest.TestCase):
 """Every floor's own piece and door boxes through the shared C: what the review page feeds it, not a made-up scene."""
 def floors(self,k=1,ox=0,oy=0):
  page=ROOT/'local/placement-review/index.html'
  if not page.exists():self.skipTest('needs the locally built page')
  sys.path.insert(0,str(ROOT/'emulator'));from core import Core
  text=page.read_text();D=json.loads(text[text.index('const D=')+8:text.index(';\nconst T=')]);core=Core();flags=[0]*33
  for c in D['flagsets']['progress']:flags[(0x312+c)>>5]|=1<<((0x312+c)&31)
  header=(ROOT/'src/runtime/labels_generated.h').read_text();part=lambda n:[m.split(',') for m in re.findall(r'\{([0-9.,f]+)\}',header.split(n+'[] = {',1)[1].split('};',1)[0])]
  layout={int(r[2]) for r in part('room_layout')};s0=k*1.5;x0,y0=ox*1.5,oy*1.5
  for f in D['floors']:
   t=lambda b:[b[0]*s0+x0,b[1]*s0+y0,b[2]*s0+x0,b[3]*s0+y0]
   rm={p[0]:t(p[1:]) for p in f['pieces']};obs=[t(d) for d in f['doors']];s=core.default_settings();s.opacity=100;s.scope=2 # every room of the floor: these rules hold whatever was visited
   ops,res=core.frame(s,1920,1080,rm,[b for b in obs if core.obstacle_fits(b)],(s0,x0,y0),flags=flags)
   yield f,ops,res,layout
 def test_fixed_room_names_keep_off_marks_and_each_other(self):
  # Ink box: the atlas tile has a 6 px margin, 4.06 screen px at this scale (3.69 before the +10% name base).
  ink=lambda o:[o['box'][0]+4.06,o['box'][1]+4.06,o['box'][2]-4.06,o['box'][3]-4.06];hit=lambda a,b:a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
  header=(ROOT/'src/runtime/labels_generated.h').read_text();define=lambda n:int(re.search(rf'#define {n} (\d+)',header)[1]);categories=[int(m.split(',')[5]) for m in re.findall(r'\{([0-9.,f]+)\}',header.split('markers[] = {',1)[1].split('};',1)[0])];icons=[int(v) for v in re.search(r'marker_icon_glyphs\[\] = \{([0-9,]+)\}',header)[1].split(',')]
  keep={i for c,i in zip(categories,icons) if c<3}|{define('PUZZLE_MARK_ID'),define('EVENT_MARK_ID')};bad=[];names=0
  for f,ops,res,layout in self.floors():
   marks=[o['box'] for o in ops if o['glyph'] in keep]
   rooms=[r for r in res if r['box']];names+=len(rooms) # the placement results, not every op with a room name's glyph: a marker's name can share one
   # RE2 Remake style, 2026-11-06: room names are drawn first and marks may cover them; names still keep off each other.
   bad+=[(f['key'],a['place'],b['place']) for i,a in enumerate(rooms) for b in rooms[i+1:] if hit(ink(a),ink(b))]
  self.assertEqual(bad,[]);self.assertGreater(names,100)
 def test_names_are_the_set_size_zoomed_in_and_70_percent_out(self):
  sys.path.insert(0,str(ROOT/'emulator'));from core import Core
  header=(ROOT/'src/runtime/labels_generated.h').read_text();row=re.findall(r'\{([0-9.,f\-]+)\}',header.split('markers[] = {',1)[1].split('};',1)[0])[0].split(',');i=int(row[2]);glyph=int(row[3]);core=Core();s=core.default_settings();off=[1]*int(re.search(r'MARKER_COUNT (\d+)',header)[1]);off[0]=0;flags=[0xffffffff]*33
  width=lambda view:[o['box'][2]-o['box'][0] for o in core.frame(s,1920,1080,{i:[-5000,-5000,-4990,-4990]},(),view,off,flags)[0] if o['glyph']==glyph][0]
  out=width((1.5,0,0));zoomed=width((4.5,float(row[0].rstrip('f'))*-4.5+900,float(row[1].rstrip('f'))*-4.5+500));self.assertAlmostEqual(out/zoomed,.7,places=3)
 def test_every_room_on_a_floor_gets_its_name(self):
  for f,ops,res,layout in self.floors():self.assertEqual([r['place'] for r in res if r['result']!='placed'],[],f['key'])
class ReviewPageTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  page=ROOT/'local/placement-review/index.html'
  if not page.exists() or not shutil.which('node'):raise unittest.SkipTest('needs the locally built page and Node')
  cls.r=json.loads(subprocess.check_output(['node','--no-warnings',str(ROOT/'tests/review_page_harness.js'),str(page)],text=True))
  sys.path.insert(0,str(ROOT/'emulator'))
  from annotations import tables
  cls.engine_cab=tables()['places'][0]
 def test_floors_use_game_names_in_both_languages(self):
  self.assertEqual(len(self.r['floors']),23);self.assertIn('열차 1F',self.r['floors']);self.assertIn('Treatment Plant B9',self.r['floorsEn']);self.assertIn('Train Roof',self.r['floorsEn'])
  self.assertFalse(any('-' in f for f in self.r['floors']))
 def test_finished_state_hides_taken_and_solved_rows(self):
  # Only rows with no done state by evidence remain on this floor: a reusable Hookshot shortcut. Enemies go too, read as killed through +0x39.
  self.assertNotIn(1,self.r['finishedLeft']);self.assertNotIn(4,self.r['finishedLeft']);self.assertNotIn(5,self.r['finishedLeft'])
  self.assertIn(5,self.r['progressLeft']);self.assertEqual(self.r['finishedMismatches'],0)
 def test_page_room_choice_stands_in_for_the_game_scope(self):
  # Marks at [8] visited, revealed, all, on train 1F. What the page's room choice sets is a stand-in, not a capture.
  visited,revealed,every=self.r['scopeAllVisited'];self.assertEqual(visited,revealed);self.assertEqual(revealed,every);self.assertGreater(visited,0)
  visited,revealed,all_=self.r['scopeHalfNoMap'];self.assertEqual(visited,revealed);self.assertGreater(visited,0);self.assertGreater(all_,visited)
  visited,revealed,all_=self.r['scopeHalfMap'];self.assertGreater(revealed,visited);self.assertEqual(revealed,all_)
  visited,revealed,all_=self.r['scopeMapOnly'];self.assertEqual(visited,0);self.assertEqual(revealed,all_);self.assertGreater(all_,0)
  self.assertTrue(self.r['difficultyKept'])
 def test_flag_sets_reach_the_shared_rule(self):
  self.assertEqual((self.r['rewardsOff'],self.r['rewardsOn']),(0,3));self.assertTrue(self.r['startFewer'])
 def test_page_opens_at_the_games_view_with_door_obstacles(self):
  self.assertEqual(self.r['view'],dict(k=1,ox=0,oy=0));self.assertGreater(self.r['doors'],0);self.assertEqual(self.r['doors'],self.r['obstaclesPassed'])
 def test_room_names_come_from_the_shared_frame_in_both_languages(self):
  ko,en=self.engine_cab[:2]
  self.assertIn(ko,self.r['ko']);self.assertIn(en,self.r['en']);self.assertNotIn(ko,self.r['en'])
 def test_keys_reach_the_shared_handler(self):
  ko=self.engine_cab[0]
  self.assertTrue(self.r['itemNamesOn'] and self.r['itemNamesNoCommon'] and self.r['itemNamesOff']) # H cycles all, no common, off
  for state in ('noNames','allOff'):self.assertNotIn(ko,self.r[state],state)
  self.assertTrue(self.r['bigger']);self.assertTrue(self.r['opacityApplied']);self.assertEqual(self.r['size'],100);self.assertGreater(self.r['marks'],20)
FLAGS=[0x5a5aa5a5+i*0x01010101&0xffffffff for i in range(33)]
DOORS=[[330,210,342,249],[1000,500,1039,512],[100,100,300,400]]
class LockDoorTests(unittest.TestCase):
 """Live report: Conductor's Key on the Cabin 201 door. The door is the one whose GUI Flag is the lock's done flag."""
 @classmethod
 def setUpClass(cls):
  for f in ('tools','tools/extract','tools/crosscheck'):sys.path.insert(0,str(ROOT/f))
  load=lambda n:json.loads((ROOT/'data'/n).read_text());cls.d=load('placements.json');cls.native=load('native-map.json');cls.doors={d['id']:d for d in cls.native['door_instances']};cls.rule=load('room-state.json')
  cls.locks=[r for r in cls.d['rows'] if r['category']=='lock']
 def test_door_flag_equals_the_done_flag_for_every_placed_lock(self):
  from state_flags import CLAIMS
  placed=[r for r in self.locks if r['piece'] in self.doors];self.assertEqual(len(placed),20)
  for r in placed:self.assertEqual(self.doors[r['piece']]['properties']['Flag'],CLAIMS[('lock',r['name_en'],r['room'])][3],(r['name_en'],r['room']))
 def test_state_flags_report_agrees(self):
  states={r['index']:r for r in json.loads((ROOT/'verification/state-flags.json').read_text())['rows']}
  for i,r in enumerate(self.d['rows']):
   if r in self.locks and r['piece'] in self.doors:self.assertEqual(states[i]['done_flag'],self.doors[r['piece']]['properties']['Flag'],r['name_en'])
 def test_doors_the_user_verified(self):
  want={("Conductor's Key",2):'i_door_02_01',('Dining Car Key',7):'i_door_08_02',('Blue Keycard',1):'i_door_07_00',('Fire Key',48):'i_door_15_25',('Fire Key',38):'i_door_15_1b',('Iron Needle',56):'i_door_0f_24',('Iron Needle',40):'i_door_0f_1d',('Water Key',58):'i_door_19_23',('Ice Pick',17):'i_door_05_06',('Blue Leech Charm',113):'i_door_2d_11',('Breeding Room Key',109):'i_door_2c_13',('Dial',102):'i_door_55_12',('Green Leech Charm',108):'i_door_2f_14',('Handle',145):'i_door_71_28',('Shaft Key (L)',173):'i_door_36_2c',('Shaft Key (R)',173):'i_door_36_2c',('MO Disk',45):'i_door_51_1a_1f',('MO Disk',53):'i_door_51_1a_2f',('MO Disk',43):'i_door_51_1a_3f'}
  self.assertEqual({(r['name_en'],r['room']):r['piece'] for r in self.locks if r['piece'] in self.doors and r['name_en']!='Keycard'},want) # Keycard: not yet checked in game, see test_keycard_lock_on_engine_room_door
 def test_placed_locks_are_not_hollow_and_carry_the_door_floor(self):
  from build_labels import marker_defs
  for m in marker_defs(self.d,self.native):
   r=self.d['rows'][m['row']]
   if r['category']=='lock' and r['piece'] in self.doors:
    self.assertEqual(m['hollow'],0,r['name_en']);self.assertEqual(r['floor'],self.doors[r['piece']]['floor'],r['name_en']);self.assertTrue(m['rooms'],r['name_en'])
    for i in m['rooms']:self.assertEqual(self.native['map_pieces'][i]['floor'],r['floor'],r['name_en'])
 @unittest.skipUnless(GAME.exists(),'needs the game')
 def test_placed_locks_sit_at_the_painted_centre(self):
  sys.path.insert(0,str(ROOT/'emulator'));from placements import door_paint
  paint=door_paint(GAME,self.native)
  for r in self.locks:
   if r['piece'] in self.doors:
    b=paint[r['piece']];self.assertEqual((r['x'],r['y']),((b[0]+b[2])/2,(b[1]+b[3])/2),r['name_en'])
 @unittest.skipUnless((ROOT/'local/research/re0hd.analysis.bin').exists(),'needs the local analysis image')
 def test_room_state_is_what_native_code_says_now(self):
  from room_state import build
  got=build((ROOT/'local/research/re0hd.analysis.bin').read_bytes(),self.native);self.assertEqual(json.loads(json.dumps(got)),self.rule)
@unittest.skipUnless(shutil.which('node'),'Node required')
class WasmParityTests(unittest.TestCase):
 def test_webassembly_and_native_build_of_frame_agree(self):
  sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'emulator'))
  from build_core import build_wasm
  from annotations import catalogue
  from core import Core
  wasm=build_wasm(ROOT/'local/re0map.wasm');core=Core();rooms,_,_=catalogue()
  scenes=[]
  for floor_pieces,view in (([0,1,2,3,4,5,6,7,8,9,10],(1.5,0,0)),([0,1,2],(4.5,-300,-800)),(list(range(21,44)),(2.0,10,-100))):
   scenes.append(({i:[300+40*n,200+15*n,420+40*n,300+15*n] for n,i in enumerate(floor_pieces)},view))
  for rm,view in scenes:
   for fields in ((1,1,0,100,100,1,63,-1,0,2,100,100,1,1),(1,1,1,150,40,2,21,-1,0,0,150,40,1,0),(1,0,0,50,10,0,63,-1,0,1,60,100,0,1),(0,1,0,100,70,1,63,-1,0,2,100,100,1,0)):
    s=core.default_settings()
    for name,value in zip(('enabled','names','english','size','opacity','difficulty','mask','selected','hidden','scope','icon_size','icon_opacity','item_names','legend'),fields):setattr(s,name,value)
    for obstacles in ((),DOORS):
     native,_=core.frame(s,1920,1080,rm,[b for b in obstacles if core.obstacle_fits(b)],view,flags=FLAGS)
     out=json.loads(subprocess.check_output(['node','--no-warnings',str(ROOT/'tests/wasm_parity.js'),str(wasm),json.dumps(dict(settings=fields,rooms=rm,w=1920,h=1080,view=view,obstacles=obstacles,flags=FLAGS))],text=True))
     self.assertEqual(len(out),len(native));self.assertGreaterEqual(len(out),2)
     for o,n in zip(out,native):
      self.assertEqual((o[4],o[5]),(n['color'],n['glyph']));self.assertEqual(o[:4],n['box'])
 def test_obstacles_move_names_and_oversize_ones_do_not(self):
  # Mutants of the shared rule: ignoring obstacles, or keeping the zoomed-up ones the ASI's capture drops.
  sys.path.insert(0,str(ROOT/'emulator'))
  from core import Core
  core=Core();s=core.default_settings();room={0:[300,200,420,300]};names=lambda o:[n['box'] for n in core.frame(s,1920,1080,room,o,(1.5,0,0))[0] if n['glyph']>=0]
  free=names(())
  self.assertTrue(core.obstacle_fits([0,0,64,64]));self.assertFalse(core.obstacle_fits([0,0,64.5,10]));self.assertFalse(core.obstacle_fits([0,0,10,64.5]))
  self.assertNotEqual(free,names([[300,200,364,264],[356,200,420,264],[300,240,364,300],[356,240,420,300]]))
if __name__=='__main__':unittest.main()
