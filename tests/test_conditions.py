"""Conditional rows reach the shared rule with their record byte and follow live flags; native addresses are pinned so the reason cannot drift."""
import json,re,struct,sys,unittest
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
for f in ('tools','tools/extract','tools/crosscheck','tools/inspect'):sys.path.insert(0,str(ROOT/f))
import build_labels
from build_labels import marker_defs,catalogue
from conditions import UNLOCK,FLAG_BASE,reward_rank,catalogue_condition
from placements_external import rows_of
IMAGE=ROOT/'local/research/re0hd.analysis.bin'
CABIN_202=5
HIDDEN=('Magnum Revolver','Machinegun Ammo','Molotov Cocktail')
KEPT=("Passenger's Diary",'Handgun Ammo','Ink Ribbon')
load=lambda n:json.loads((ROOT/'data'/n).read_text())
def places():
 return catalogue(load('native-map.json'),load('room-matches.json')['claims'],load('room-contents.json'),load('names-ko.json')['names'],load('item-uses.json'))
class RuleTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.d=load('placements.json');cls.native=load('native-map.json')
 def test_condition_is_carried_as_the_single_byte(self):
  game=[r for r in self.d['rows'] if 'world' in r]
  self.assertTrue(all(isinstance(r['condition'],int) and 0<=r['condition']<=255 for r in game))
  self.assertEqual(sum(r['condition'] in UNLOCK for r in game),9)
 def here(self):
  rows=self.d['rows'];return {rows[d['row']]['name_en']:d for d in marker_defs(self.d,self.native) if rows[d['row']].get('room')==CABIN_202 and 'world' in rows[d['row']]}
 def test_cabin_202_defs_carry_their_conditions(self):
  here=self.here()
  self.assertEqual([here[n]['condition'] for n in HIDDEN],[160,161,162])
  for n in KEPT:self.assertEqual(here[n]['condition'],0)
 def test_conditional_rows_stay_in_the_table(self):
  # Hiding them at build time would make the live flag unable to bring them back.
  defs=marker_defs(self.d,self.native);self.assertEqual(len({d['row'] for d in defs if d['condition'] in UNLOCK}),9)
  self.assertGreater(sum(d['condition'] not in(0,*UNLOCK) for d in defs),250)
 def test_room_counts_carry_the_same_byte(self):
  cabin=next(p for p in places() if p['claim']['external_id']=='train-1f/cabin-202')['rows']
  self.assertEqual({k[0].split(' (')[0]:k[2] for k in cabin if k[0].startswith(('Magnum Revolver','Machinegun Ammo'))},{'Magnum Revolver':160,'Machinegun Ammo':161})
  self.assertTrue(all(k[2]==0 for k in cabin if k[0].startswith("Passenger's Diary")))
  self.assertEqual((catalogue_condition({'reward_rank':'B'}),catalogue_condition({'reward_rank':'E'}),catalogue_condition({})),(160,161,0))
 def test_generated_table_keeps_them_for_the_shared_rule(self):
  text=(ROOT/'src/runtime/labels_generated.h').read_text()
  self.assertEqual(int(re.search(r'#define MARKER_COUNT (\d+)',text)[1]),len(marker_defs(self.d,self.native)))
class LiveFlagTests(unittest.TestCase):
 """Through the same C the ASI links: the mark and the room count both follow the flag."""
 def setUp(self):
  sys.path.insert(0,str(ROOT/'emulator'))
  from core import Core
  self.core=Core();self.s=self.core.default_settings();self.s.scope=2;native=load('native-map.json');self.piece=next(i for i,p in enumerate(native['map_pieces']) if p['id']=='i_tr0590')
 def flags(self,*conditions):
  out=[0]*33
  for c in conditions:f=FLAG_BASE+c;out[f>>5]|=1<<(f&31)
  return out
 def marks(self,flags):
  ops,_=self.core.frame(self.s,1920,1080,{self.piece:[700,450,900,560]},(),(1.5,0,0),flags=flags);first=int(__import__('re').search(r'ICON_FIRST_GLYPH (\d+)',(Path(__file__).resolve().parents[1]/'src/runtime/labels_generated.h').read_text())[1]);return sum(o['glyph']>=first for o in ops) # icons: names may move or give way when a row appears
 def counts(self,flags):
  _,results=self.core.frame(self.s,1920,1080,{self.piece:[700,450,900,560]},(),None,flags=flags);return [r['counts'] for r in results if r['result']=='placed'][0]
 def test_marks_follow_each_flag(self):
  base=self.marks(self.flags())
  self.assertEqual(self.marks(None),base) # unknown behaves as unset
  for c in UNLOCK:self.assertGreater(self.marks(self.flags(c)),base,c)
  self.assertEqual(self.marks(self.flags(163)),base) # a flag no row here uses
 def test_room_count_follows_the_flag(self):
  base=self.counts(self.flags());self.assertEqual(self.counts(None),base)
  with_b=self.counts(self.flags(160));self.assertEqual(sum(with_b)-sum(base),1)
  self.assertEqual(sum(self.counts(self.flags(160,161)))-sum(base),2)
class CatalogueTests(unittest.TestCase):
 def row(self,text):return f'<li data-gamemode="gm11"><h3 class="h6 x">Magnum Revolver</h3><div class="text">{text}</div><div class="actions"> <a href="/resident-evil-zero/weaponry/x">a</a></div></li>'
 def test_wording_counts(self):
  r=rows_of(self.row('Only appears here after achieving at least a B Rank in the Leech Hunter mini-game.'))[0]
  self.assertTrue(r['conditional']);self.assertEqual(r['reward_rank'],'B')
  plain=rows_of(self.row('On the bed.'))[0];self.assertFalse(plain['conditional']);self.assertIsNone(plain['reward_rank'])
  self.assertIsNone(reward_rank('Only appears here after the MO Disk.'))
 def test_crosscheck_reports_conditional_rows_apart(self):
  c=json.loads((ROOT/'verification/placement-crosscheck.json').read_text())
  self.assertEqual(c['condition_conflicts'],[])
  self.assertEqual({m:v['conditional'] for m,v in c['by_difficulty'].items()},{'easy':8,'normal':8,'hard':8})
  for r in c['conditional']:
   if r['catalogue_rank']:self.assertEqual(r['catalogue_rank'],r['game_rank'],r)
  # The native gate has one row the catalogue never lists: Molotov Cocktail, rank A.
  self.assertEqual({r['name'] for r in c['conditional'] if r['place'] is None},{'Molotov Cocktail'})
@unittest.skipUnless(IMAGE.exists(),'local analysis image required')
class NativeTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  from capstone import Cs,CS_ARCH_X86,CS_MODE_32
  cls.b=IMAGE.read_bytes();cls.cs=Cs(CS_ARCH_X86,CS_MODE_32);pe=struct.unpack_from('<I',cls.b,60)[0];opt=pe+24;cls.secs=[]
  for i in range(struct.unpack_from('<H',cls.b,pe+6)[0]):
   o=opt+struct.unpack_from('<H',cls.b,pe+20)[0]+i*40;_,_,va,sz,raw=struct.unpack_from('<8sIIII',cls.b,o);cls.secs.append((va,sz,raw))
 def off(self,a):
  for va,sz,raw in self.secs:
   if va<=a-0x400000<va+sz:return a-0x400000-va+raw
  raise ValueError(hex(a))
 def ins(self,a):
  i=next(self.cs.disasm(self.b[self.off(a):self.off(a)+16],a));return f'{i.mnemonic} {i.op_str}'
 def u32s(self,a,n):return struct.unpack_from(f'<{n}I',self.b,self.off(a))
 def test_spawn_needs_clear_byte_or_set_flag(self):
  self.assertEqual(self.ins(0x410c46),'cmp dword ptr [edi + esi + 0x3c], eax')
  self.assertEqual(self.ins(0x410c4a),'je 0x410c7f')
  self.assertEqual(self.ins(0x410c65),f'lea ecx, [esi + {FLAG_BASE:#x}]')
  self.assertEqual(self.ins(0x410c6e),'call 0x59b8d0')
  self.assertEqual((self.ins(0x410c73),self.ins(0x410c75)),('test eax, eax','je 0x410e79'))
 def test_map_and_item_list_share_the_test(self):
  self.assertEqual(self.ins(0x5b693a),f'add eax, {FLAG_BASE:#x}')
  self.assertEqual(self.ins(0x57da66),f'add eax, {FLAG_BASE:#x}')
 def test_unlock_flags_come_from_reward_bits(self):
  # 0x59d2a0: mask test, then set; each flag is FLAG_BASE plus the record byte.
  for byte,(flag,bit,_,_) in UNLOCK.items():self.assertEqual(flag,FLAG_BASE+byte)
  sites={160:(0x59d336,0x59d37a),161:(0x59d387,0x59d3d0),162:(0x59d2e1,0x59d329)}
  for byte,(mask,push) in sites.items():
   self.assertEqual(self.ins(mask),f'and eax, {UNLOCK[byte][1]:#x}')
   self.assertEqual(self.ins(push),f'push {UNLOCK[byte][0]:#x}')
 def test_rank_tables(self):
  self.assertEqual(self.u32s(0xd9cd98,5),(0x10,0x20,0x40,0x80,0x100))
  self.assertEqual(self.u32s(0xcdb59c,5)[:4],(100,90,60,30))
  for flag,bit,index,_ in UNLOCK.values():self.assertEqual(self.u32s(0xd9cd98,5)[index],bit)
if __name__=='__main__':unittest.main()
