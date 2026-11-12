"""Build location data for every legend group from game data, with the map transform evaluated by native code.

Items and enemies: arrange/loctbl (loc2). Locks: curated or script key_check/item_check, placed on the door whose GUI Flag is the lock's done flag
(tools/crosscheck/state_flags.py CLAIMS), at its painted centre. Puzzles: item-use script headers bound to their interaction trigger volumes.
Script-given items: SCRIPT_GRANTS below, at their trigger volume when a tag 2 group ties them to one, otherwise room-level.
"""
import argparse,json,re,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for folder in ('tools','tools/extract','tools/inspect','emulator','tools/crosscheck'):sys.path.insert(0,str(ROOT/folder))
from arrange import parse as parse_arrange
from event_disasm import Commands,decode,groups
from events import analyse,is_room_script,ITEM_USE,__doc__ as events_rule
from event_collision import parse as parse_collision
from resources import Arc
from render import render
from state_flags import CLAIMS
from build_labels import WEAPONS
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import UC_X86_REG_ESP
BASE=0x400000;ANCHOR=0x5bb8c0;ADJUST=0x5bd390;FLOOR_TABLE=0xd9d7b8
TABLES={'easy':'loctbl0000','normal':'loctbl0100','hard':'loctbl0200',**{f'leech{i}':f'loctbl030{i}' for i in range(5)}} # Leech Hunter: 0x4111cc loads loctbl030<rand()%5> in mode 3
# Leech Hunter Small Library: a zombie lying in pose 12 (record byte 5, uEnemy10 +0x67c8) takes no damage and never goes (user 2026-11-11). (room, kind, pose).
DECOR={(52,0x10,12)}
REGIONS=[('tr',0),('sh',36),('dm',86),('ch',99),('bt',132),('pl',141)];END=175
def locate(room):
 for i,(name,base) in enumerate(REGIONS):
  if base<=room<(REGIONS[i+1][1] if i+1<len(REGIONS) else END):return i,room-base,name
 raise ValueError(room)
class Native:
 def __init__(self,image):
  self.image=image;pe=struct.unpack_from('<I',image,60)[0];opt=pe+24;size=struct.unpack_from('<I',image,opt+56)[0]
  self.secs=[];self.uc=Uc(UC_ARCH_X86,UC_MODE_32);self.uc.mem_map(BASE,(size+0xfff)&~0xfff)
  for i in range(struct.unpack_from('<H',image,pe+6)[0]):
   o=opt+struct.unpack_from('<H',image,pe+20)[0]+i*40;_,_,va,sz,raw=struct.unpack_from('<8sIIII',image,o);self.secs.append((va,sz,raw))
   if sz:self.uc.mem_write(BASE+va,image[raw:raw+sz])
  self.uc.mem_map(0x1000,0x1000);self.uc.mem_map(0x20000000,0x100000)
 def u32(self,a):return struct.unpack('<I',bytes(self.uc.mem_read(a,4)))[0]
 def anchor(self,region,floor,room):
  """Original 0x5bb8c0: the room's map anchor for this floor."""
  sp,out=0x20080000,0x20090000
  self.uc.mem_write(sp,struct.pack('<6I',0x1000,region,floor,room,out,out+4));self.uc.mem_write(out,b'\0'*8)
  self.uc.reg_write(UC_X86_REG_ESP,sp);self.uc.emu_start(ANCHOR,0x1000,count=2000)
  return struct.unpack('<2f',bytes(self.uc.mem_read(out,8)))
 def base(self,region,floor,room):
  """0x5b3e45-0x5b3e88: anchor, floor offset, +240 on y, then the original per-room correction 0x5bd390."""
  off=self.floor_offset(region,floor)
  if off is None:return None
  a=self.anchor(region,floor,room);sp,out=0x20080000,0x20090000
  self.uc.mem_write(out,struct.pack('<2f',a[0]+off[0],a[1]+off[1]+240.0))
  self.uc.mem_write(sp,struct.pack('<6I',0x1000,region,floor,room,out,out+4))
  self.uc.reg_write(UC_X86_REG_ESP,sp);self.uc.emu_start(ADJUST,0x1000,count=2000)
  return struct.unpack('<2f',bytes(self.uc.mem_read(out,8)))
 def floor_offset(self,region,floor):
  """Table read at 0x5b3dcc: a per-floor record, offset at +0x10/+0x14."""
  p=self.u32(FLOOR_TABLE+(region*12+floor)*4)
  return struct.unpack('<2f',bytes(self.uc.mem_read(p+0x10,8))) if p else None
SCALE=.01*7.0
def to_canvas(base,x,z,k=SCALE):
 """0x5b3eff-0x5b3f83, unrotated branch, in the map GUI's 1280x720 space."""
 return (base[0]+x*k)*1.5+163.0,(base[1]+z*k)*1.5-357.0
def piece_boxes(game,native,suffix='',geometry_only=False):
 out={}
 for floor in native['floors']:
  try:_,trace=render(game,floor['region'],floor['floor'],group_suffix=suffix,geometry_only=geometry_only)
  except ValueError:continue
  for r in trace['drawn']:
   b=r['canvas_box'];p=out.get(r['instance'],b);out[r['instance']]=[min(b[0],p[0]),min(b[1],p[1]),max(b[2],p[2]),max(b[3],p[3])]
 return out
def item_tables(game):
 """Item names by id from the two message archives; the short names the game itself shows."""
 def names(path):
  a=Arc(path.read_bytes());parts=a.read(next(m for m in a.members if m.name.endswith('message_item_name_eng'))).split(b'\0')
  keys=[p.decode('latin1') for p in parts if p.startswith(b'item_name_')];first=parts.index(keys[0].encode())
  return {int(k.rsplit('_',1)[1]):v.decode('utf-8','ignore').strip() for k,v in zip(keys,parts[first+len(keys):first+2*len(keys)])}
 folder=game/'nativePC/arc/message'
 return names(folder/'msg_eng_box.arc.before-ko-20261103-013234.bak'),names(folder/'msg_eng_box.arc')
FILE=re.compile(r'Map$|Diary|Report|Notes?\b|Notice|Manual|Orders|Regulations|Records|Photograph|Verse|List|^About |Image')
RECOVERY=('Herb','First-Aid','Ink Ribbon','Gas Tank','Empty Bottle','Ammo','Grenade','Knife','Handgun','Shotgun','Hunting','Magnum','Molotov','Sub-Machinegun','Rocket','Machinegun')
def category(kind,name):
 # Kinds 1..0xf are the player classes: 2 uPlayerRebecca, 5 uPlayerBilly, their rows hold 150 and 250 HP (DTI names at 0xc8aaa8, 0xc8a668). 0x61d510 walks them as a separate group.
 if kind<0x10:return None
 if kind<0x70:return 'enemy' # 0x61d544: 0x10..0x6f is the enemy group, and 0x6a, 0x6b are uEnemy6a, uEnemy6b of the zombie family
 if kind not in (0x71,0x78):return None
 if FILE.search(name):return 'file'
 if name in WEAPONS:return 'key' # user: weapons are key items
 return 'item' if any(k in name for k in RECOVERY) else 'key'
def places(native,matches):
 pieces={p['id']:p for p in native['map_pieces']};by_room={}
 for c in matches['claims']:
  for pid in [*c['native_pieces'],*[a['piece'] for a in c.get('alias_pieces',[])]]:
   by_room.setdefault(pieces[pid]['native_room_id'],[]).append((pid,c['external_id'],c['name_ko'],c['name_en']))
 return pieces,by_room
def locate_record(nat,room,x,z,by_room,pieces,boxes,locations,k=SCALE,only=None):
 """Choose the floor whose piece contains the point; report the nearest when none does, never hide it. only: the one floor to consider."""
 reg,local,_=locate(room);best=None
 for floor in sorted(set(locations.get(room,[]))):
  if floor==255:continue
  base=nat.base(reg,floor,local)
  if base is None:continue
  cx,cy=to_canvas(base,x,z,k)
  for pid,*_ in by_room.get(room,[]):
   b=boxes.get(pid)
   if not b or (only and pieces[pid]['floor']!=only):continue
   dx=max(b[0]-cx,0,cx-b[2]);dy=max(b[1]-cy,0,cy-b[3]);d=(dx*dx+dy*dy)**.5
   if best is None or d<best['distance']:best=dict(x=cx,y=cy,piece=pid,floor=pieces[pid]['floor'],region=pieces[pid]['region'],distance=d)
 return best
# Table rows of a room on several floors whose x/z fit more than one; (room, item): floor. Elevator Key: Turntable Yard and Platform share scene bt02, the key lies on the B4 platform
# (Evil Resource factory-b4/turntable-platform; the user picked it up on B4, 2026-11-11), and x/z alone put it on the 1F yard.
FLOOR_OF={(134,67):'b4'}
# Rooms whose two floors share x/z, told apart by world y: room: (y below which, floor; otherwise floor). 142: B6 Air Regulator Room rows lie at y 0 (3 Zombies, the herbs,
# Empty Bottle, as Evil Resource and the user, 2026-11-11), B5 Control Room rows at y 470-557.
# 36: Main Hall 1F and 2F balcony; Leech Hunter puts charms at y 436-520, main-game rows lie at y 0. The split is DROP_FLOOR_Y's (tools/build_labels.py).
FLOOR_BY_Y={142:(200,'b6','b5'),36:(300,'1f','2f')}
def floor_of(row):
 f=FLOOR_OF.get((row['room'],row['item']))
 if f or row['room'] not in FLOOR_BY_Y:return f
 y,low,high=FLOOR_BY_Y[row['room']];return low if row['world'][1]<y else high
# Group 3 of these three scenes of one room runs door(13) with no key check reachable; item 64 has no name, and Evil Resource lists no locked door here.
NOT_LOCKS={('tr0c',13),('tr18',13),('tr20',13)}
# Solving the Lecture Room puzzle sets flag 0x1a, which door scripts sh00, sh0b and sh1d test. Evil Resource names the same three doors, and the GUI's door instances carry 1a.
PUZZLE_DOORS={45:'i_door_51_1a_1f',53:'i_door_51_1a_2f',43:'i_door_51_1a_3f'}
# Items that come only from an event script, so no table row exists. (room, scene, group, item, amount): checked by tools/crosscheck/state_flags.py against the same group.
# flag: set once given. also: a flag after which the group no longer gives it. no flag: a reusable station. The amount holds for all difficulties: scripts have no difficulty command, and the catalogue lists every row below in all three.
SCRIPT_GRANTS=[
 dict(room=2,scene='tr02',group=9,item=32,amount=15,flag=0x65,also=0x79), # g9 needs 0x41 set and 0x79 clear: 0x79 is written once, entering the engine cab (tr00 g3)
 dict(room=0,scene='tr00',group=3,item=156,amount=1,flag=0x79),dict(room=10,scene='tr0a',group=2,item=179,amount=1,flag=0x6e,after=104),
 dict(room=15,scene='tr0f',group=5,item=32,amount=30,flag=0x63),dict(room=15,scene='tr0f',group=5,item=151,amount=1,flag=0x63),
 dict(room=39,scene='sh03',group=5,item=174,amount=1,flag=0x184,after=124),dict(room=54,scene='sh12',group=5,item=160,amount=1,flag=0xb0,after=89),
 dict(room=113,scene='ch0e',group=3,item=32,amount=16,flag=0xec),dict(room=113,scene='ch0e',group=4,item=169,amount=1,flag=0xeb,after=92),
 dict(room=165,scene='pl18',group=2,item=177,amount=1,flag=0x179),
 # Chemical stations: item_sub(mixing set) then item_get(chemical), no flag, so they stay available.
 dict(room=49,scene='sh0d',group=5,item=136,amount=1),dict(room=105,scene='ch06',group=6,item=134,amount=1),dict(room=107,scene='ch08',group=6,item=136,amount=1),
 dict(room=103,scene='ch04',group=11,item=134,amount=1),dict(room=143,scene='pl02',group=4,item=134,amount=1),dict(room=157,scene='pl10',group=5,item=135,amount=1),
]
TAG_INVESTIGATE=2
def snap_room_level(rows,game,native,by_room):
 """A room-level mark is a guess at the bounding box's centre, which an L-shaped room can leave outside. Nearest cell of the room's real shape. Every other row: real 3D positions can overshoot walls drawn thin on the map (up to 16 px once the floor sheet counts as room), so nearest cell too, flagged moved_into_room."""
 from room_layout import piece_masks,silhouette,textures,cells,GRID
 get=textures(game);shapes={};floor_of={p['id']:p['floor'] for p in native['map_pieces']}
 for f in native['floors']:
  known={p['id'] for p in native['map_pieces']}
  masks,_=piece_masks(game,f['region'],f['floor'],get,known);fills,_=piece_masks(game,f['region'],f['floor'],get,known,fill=True)
  for pid,m in masks.items():shapes[pid]=cells(silhouette(m))|cells(fills[pid]) if pid in fills else cells(silhouette(m))
 for r in rows:
  if r.get('x') is None or r['category']=='lock':continue
  own=set().union(*[shapes[p] for p,*_ in by_room.get(r['room'],[]) if p in shapes and floor_of.get(p)==r['floor']],set()) # its own floor: pieces of other floors share the canvas
  c=(int(r['x']//GRID),int(r['y']//GRID))
  if own and c not in own:
   n=min(own,key=lambda a:(a[0]-c[0])**2+(a[1]-c[1])**2);r['x'],r['y'],r['moved_into_room']=n[0]*GRID+1.0,n[1]*GRID+1.0,1
def trigger_box(arc,scene,x):
 """Volume x of member <scene>b: a tag 2 group's x picks the list. Not read from native code: on the 18 kind 0x78 rows, whose table position is independent, that list is the nearest one to the position in 15, see verification/state-flags.md."""
 member=next((m for m in arc.members if m.kind==0x2b399b97 and m.name.endswith(scene+'b')),None)
 if member is None:return None
 lists=parse_collision(arc.read(member))['lists']
 if not 0<=x<len(lists):return None
 v=lists[x];return min(p[0] for p in v),max(p[0] for p in v),min(p[2] for p in v),max(p[2] for p in v)
def script_rows(game,nat,en,ko,by_room,pieces,boxes,locations):
 out=[]
 for g in SCRIPT_GRANTS:
  name=en[g['item']];cat=category(0x71,name);arc=Arc((game/f"nativePC/arc/scene/{g['scene']}.arc").read_bytes());d=arc.read(next(m for m in arc.members if m.kind==0x714ec77c and m.name.split('\\')[-1]==g['scene']));count=struct.unpack_from('>I',d,0)[0] # the base script, not its 'b' twin
  if g['group']>=count:raise ValueError(f"no group {g['group']} in {g['scene']}")
  tag,_,x,_=struct.unpack_from('>4I',d,16+g['group']*16)
  box=trigger_box(arc,g['scene'],x) if tag==TAG_INVESTIGATE else None
  hit=None;pid=by_room[g['room']][0][0]
  if box:
   cx,cz=(box[0]+box[1])/2,(box[2]+box[3])/2;hit=locate_record(nat,g['room'],cx,cz,by_room,pieces,boxes,locations)
  how=f"script {g['scene']} g{g['group']} tag {tag}"
  if hit and hit['distance']<=2:evidence=f"{how}, trigger volume {x}";trigger=[round(cx,2),round(cz,2)]
  else:
   # Room level: an automatic event with no volume, or a volume the map cannot place.
   b=boxes[pid];p=pieces[pid];hit=dict(x=(b[0]+b[2])/2,y=(b[1]+b[3])/2,piece=pid,floor=p['floor'],region=p['region'],distance=0);trigger=None;evidence=f'{how}; room centre, exact position unresolved'
  row=dict(category=cat,room=g['room'],item=g['item'],name_en=name,name_ko=ko.get(g['item'],name),condition=0,amount=dict(easy=g['amount'],normal=g['amount'],hard=g['amount']),evidence=evidence,script=dict(scene=g['scene'],group=g['group'],tag=tag,x=x),**hit)
  if trigger:row['trigger']=trigger
  for k in ('flag','also','after'):
   if k in g:row['script'][k]=g[k]
  out.append(row)
 return out
def puzzle_trigger(data,item,commands):
 """Item-use group headers bind tag 8's or tag 30's item (y) to the same volume (x) as tag 2. Tag 30 is the door form: Hookshot in ch01, ch03, ch0d runs SubItemJp then door.
 A wildcard volume inherits a unique investigation group that calls into that use group.
 """
 gs=groups(data);uses=[(i,g,e) for i,(g,e) in enumerate(gs) if g[0] in (8,30) and g[3]==item]
 hits=[]
 for i,g,end in uses:
  tag,off,x,_=g
  if x!=0xffffffff:hits.append((i,x));continue
  callers=[]
  for j,((t,start,volume,_),stop) in enumerate(gs):
   if t==TAG_INVESTIGATE and start and any(n=='gosub' and off<=a[0]<end for _,n,a in decode(data,start,stop,commands)):
    callers.append((j,volume))
  if len(set(v for _,v in callers))==1:hits.extend(callers)
 volumes={v for _,v in hits}
 if len(volumes)!=1:return None
 return sorted({i for i,_ in hits}),volumes.pop()
SPREAD=('Lighter',) # puzzles placed at the middle of all their use volumes
def place_puzzles(rows,game,nat,en,commands,by_room,pieces,boxes,locations):
 aliases={'Input Regulator Coil':'Input Reg. Coil','Output Regulator Coil':'Output Reg. Coil'}
 ids={'Lighter':106} # 105 is the empty Lighter, 106 the filled one the statues take (dm04 g16-g21)
 unresolved=[]
 for row in rows:
  if row['category']!='puzzle':continue
  item=ids.get(row['name_en']) or next((k for k,v in en.items() if v==aliases.get(row['name_en'],row['name_en'])),None)
  _,local,region=locate(row['room']);scene=f'{region}{local:02x}'
  arc=Arc((game/f'nativePC/arc/scene/{scene}.arc').read_bytes())
  member=next(m for m in arc.members if m.kind==0x714ec77c and m.name.split('\\')[-1]==scene)
  binding=puzzle_trigger(arc.read(member),item,commands) if item is not None else None
  volume=trigger_box(arc,scene,binding[1]) if binding else None
  if not binding and item is not None and row['name_en'] in SPREAD:
   # One item on several objects, each its own volume (six statues, dm04): one mark at the middle of all of them.
   uses=[(i,g[2]) for i,(g,_) in enumerate(groups(arc.read(member))) if g[0] in (8,30) and g[3]==item];boxes_=[trigger_box(arc,scene,v) for _,v in uses]
   if boxes_ and all(boxes_):binding=([i for i,_ in uses],[v for _,v in uses]);volume=tuple(f(b[k] for b in boxes_) for k,f in enumerate((min,max,min,max)))
  hit=None
  if volume:
   x,z=(volume[0]+volume[1])/2,(volume[2]+volume[3])/2
   hit=locate_record(nat,row['room'],x,z,by_room,pieces,boxes,locations)
  if hit and hit['distance']<=2:
   row.update(**hit,trigger=[round(x,2),round(z,2)],script=dict(scene=scene,groups=binding[0],volume=binding[1],item=item),evidence=f'script {scene} item-use groups {binding[0]}, trigger volume {binding[1]}')
  else:
   # shortcut: unresolved interactions have no point marker, add only with a script-to-volume binding.
   row.update(x=None,y=None,evidence='puzzle interaction position unresolved; no point marker')
   unresolved.append(dict(room=row['room'],name_en=row['name_en']))
 return unresolved
# Event groups that are a puzzle with no item use, so they get a named puzzle mark beside the event mark (user 2026-11-10). (scene, group): (en, ko).
# dm02 g5: UpCut panel adding 30/20/40/10/50, CmpRegImm 70 then FlagSet 10. pl01 g6: message "Dam Area Power Supply Panel".
# sh00 g15: messages "The scales are balanced", "Remove a statue?". tr00 g2: UpCutProc panel in the Engine Cab, which gives the Brake Operation Manual (external page).
# Not puzzles, by their messages: levers ch03 g5 and pl11 g5, gondola pl0b g4, elevator floors pl19 g3, power cable tr11 g3.
# ch0c g2: "Use the cable car?", a repeatable ride that toggles 0xea, so no flag ever hides it. Puzzle mark only, always shown (user 2026-11-11).
# pl20 g4: the Storage lift down to the Queen Leech (Demo_Start 123), no flag ends it. Not a puzzle, marked because it matters (user 2026-11-11).
ALWAYS_PUZZLES={('ch0c',2):('Cable Car','케이블카'),('pl20',4):('Elevator','승강기')}
# Puzzles without an item use, one named puzzle mark in place of their event mark (user 2026-11-11, checked against Gamepressure's walkthrough).
# (scene, group): (en, ko, hide), hide a done flag or (room, item) of the pickup the puzzle gives.
# pl0d g6: crate room panel (FenceRot, Fill/Drain); no script sets 400, so it goes with the Handle. sh1a g5: piano, g6 clears 0x9a on a replay, so it goes with the Battery.
# sh12 g7: chessboard, the King entering volume 6 sets 169. dm0a g8: testing area panel, its red button lets the hunters in (205).
NAMED_PUZZLES={('pl0d',6):('Crates','상자 퍼즐',(154,87)),('sh1a',5):('Piano','피아노',(62,94)),('sh12',7):('Chessboard','체스판',169),('dm0a',8):('Control Panel','제어 패널',205)}
SCRIPT_PUZZLES={('dm02',5):('Power Regulator','전원 조절 장치'),('pl01',6):('Power Supply Panel','전원 공급 패널'),('sh00',15):('Scales','천칭'),('tr00',2):('Brake Controls','브레이크 장치')}
def puzzle_events(rows,audit):
 """An event mark beside each item-use puzzle whose use group runs a cutscene. It is done when the puzzle is (puzzle_row)."""
 scenes={(a['scene'],a['group']) for a in audit if a['tag'] in ITEM_USE and a['scenes']};out=[]
 for i,r in enumerate(rows):
  s=r.get('script') or {}
  if r['category']!='puzzle' or r.get('x') is None or not any((s.get('scene'),g) in scenes for g in s.get('groups',())):continue
  out.append(dict({k:v for k,v in r.items() if k not in('script','evidence')},event=1,name_en='Event',name_ko='이벤트',puzzle_row=i,script=s,evidence=f"cutscene in the use group of puzzle row {i}; {r['evidence']}"))
 return out
def place_events(rows,game,nat,image,by_room,pieces,boxes,locations):
 """Marks for readable events (tools/extract/events.py) and the audit of all of them. Appended after every other row so row indexes stay."""
 from state_flags import Scripts
 bases=dict(REGIONS);marks=[];audit=[];s=Scripts(game,Commands(image));written=s.index()[0]
 for scene in sorted(s.members):
  region=scene[:2]
  if not is_room_script(scene) or region not in bases:continue
  arc=Arc((game/f'nativePC/arc/scene/{scene}.arc').read_bytes());room=bases[region]+int(scene[2:],16)
  for g in analyse(s,scene,written):
   a=dict(g,room=room);audit.append(a)
   if (scene,g['group']) in NAMED_PUZZLES:a.update(status='named_puzzle',reason='one puzzle mark, see NAMED_PUZZLES');continue
   always=ALWAYS_PUZZLES.get((scene,g['group']))
   if g['status']!='script_read' and not always:continue
   hit=None;how=None
   if g['tag'] in (2,14):
    v=trigger_box(arc,scene,g['x'])
    if v:hit=locate_record(nat,room,(v[0]+v[1])/2,(v[2]+v[3])/2,by_room,pieces,boxes,locations);how=f"trigger volume {g['x']}"
   elif g['tag']==17:
    r=next((r for r in rows if r.get('room')==room and r.get('item')==g['x'] and r.get('kind')==113 and r.get('x') is not None),None)
    if r:hit=dict(x=r['x'],y=r['y'],region=r['region'],floor=r['floor'],piece=r['piece'],distance=0);how=f"table row of item {g['x']}"
   room_level=not hit or hit['distance']>2
   if room_level:
    found=by_room.get(room);pid=found[0][0] if found else None;b=boxes.get(pid) if pid else None
    if not b:a.update(status='unresolved',reason='no map piece for its room');continue
    p=pieces[pid];hit=dict(x=b[0]+9,y=b[1]+9,region=p['region'],floor=p['floor'],piece=pid,distance=0);how='room level, corner of its first piece, exact position unresolved'
   a['position']=how
   en,ko=always or (('Event (room)','이벤트(방)') if room_level else ('Event','이벤트'))
   if always:a.update(status='script_read',reason='repeatable, always-shown puzzle mark')
   marks.append(dict(category='puzzle',event=0 if always else 1,room=room,name_en=en,name_ko=ko,amount=dict(easy=1,normal=1,hard=1),condition=0,done_flag=g['done'],need_flag=g['need'][0] if g['need'] else None,script=dict(scene=scene,group=g['group'],tag=g['tag'],x=g['x']),evidence=f"script {scene} g{g['group']} tag {g['tag']} {g['basis']}; {how}",**hit))
   if (scene,g['group']) in SCRIPT_PUZZLES: # the puzzle beside its event (user 2026-11-10); same flag, same spot
    en,ko=SCRIPT_PUZZLES[(scene,g['group'])];marks.append(dict(marks[-1],event=0,name_en=en,name_ko=ko))
  marks+=named_puzzles(rows,scene,room,arc,s,audit,nat,by_room,pieces,boxes,locations)
 return marks,audit
def named_puzzles(rows,scene,room,arc,s,audit,nat,by_room,pieces,boxes,locations):
 """NAMED_PUZZLES of one scene: a puzzle mark at the group's trigger volume, done by a flag or with the pickup row it gives."""
 heads={h[0]:h for h in s.heads(scene)};out=[]
 for (sc,grp),(en,ko,hide) in NAMED_PUZZLES.items():
  if sc!=scene:continue
  _,tag,_,x,_=heads[grp];v=trigger_box(arc,scene,x)
  hit=v and locate_record(nat,room,(v[0]+v[1])/2,(v[2]+v[3])/2,by_room,pieces,boxes,locations)
  if not hit or hit['distance']>2:raise ValueError(f'{scene} g{grp}: trigger volume {x} not on its room')
  a=next((a for a in audit if a['scene']==scene and a['group']==grp),{})
  m=dict(category='puzzle',event=0,room=room,name_en=en,name_ko=ko,amount=dict(easy=1,normal=1,hard=1),condition=0,script=dict(scene=scene,group=grp,tag=tag,x=x),**hit)
  if isinstance(hide,int):m.update(done_flag=hide,need_flag=a['need'][0] if a.get('need') else None,evidence=f'script {scene} g{grp} tag {tag}; trigger volume {x}; done flag {hide:#x}')
  else:
   i=next(i for i,r in enumerate(rows) if r['room']==hide[0] and r.get('item')==hide[1] and r.get('kind')==113)
   m.update(kind=113,item=hide[1],puzzle_row=i,evidence=f'script {scene} g{grp} tag {tag}; trigger volume {x}; done with pickup row {i}')
  out.append(m)
 return out
def door_paint(game,native):
 """Each door's painted part in canvas space, by the same render the page's doors use, with the floor it is on."""
 out={}
 for floor in native['floors']:
  try:_,trace=render(game,floor['region'],floor['floor'],group_suffix='_door',geometry_only=True)
  except ValueError as e:
   if 'floor group not found' not in str(e):raise
   continue
  for r in trace['drawn']:out[r['instance']]=r['ink_box']
 return out
def lock_door(row,native):
 """The door of a lock: the region of its room and GUI Flag equal to its done flag. None: no claim, or the flag is on no door, and the row keeps what it has."""
 claim=CLAIMS.get(('lock',row['name_en'],row['room']))
 if claim is None:return None
 if row['name_en']=='MO Disk':return PUZZLE_DOORS[row['room']]
 region=locate(row['room'])[2];found=[d['id'] for d in native['door_instances'] if d['region']==region and d['properties']['Flag']==claim[3]]
 if len(found)>1:raise ValueError(f"{row['name_en']} room {row['room']}: flag {claim[3]:#x} on several doors {found}, name the right one in PUZZLE_DOORS")
 return found[0] if found else None
def place_locks(rows,native,paint):
 """Moves each lock onto its door; returns the rows left at room level."""
 by_id={d['id']:d for d in native['door_instances']};left=[]
 for r in rows:
  if r['category']!='lock':continue
  door=lock_door(r,native)
  if door is None:left.append(dict(name_en=r['name_en'],room=r['room']));continue
  b=paint[door];d=by_id[door];r.update(x=(b[0]+b[2])/2,y=(b[1]+b[3])/2,region=d['region'],floor=d['floor'],piece=door,distance=0,door_flag=d['properties']['Flag'],evidence=f"done flag {d['properties']['Flag']:#x} is this GUI door's Flag, map door instance")
 return left
def locks(commands,scripts,items_en):
 """Rooms whose door script checks a key: (room, door target, key ids)."""
 found={}
 for room,data in scripts.items():
  if not re.fullmatch(r'[a-z]{2}[0-9a-f]{2}',room):continue
  for (tag,off,_,_),end in groups(data):
   if not off:continue
   try:rows=decode(data,off,end,commands)
   except ValueError:continue
   if not any(r[1]=='key_check' for r in rows):continue
   keys=sorted({r[2][0] for r in rows if r[1] in('item_check','key_check')})
   for target in {r[2][0] for r in rows if r[1]=='door'}:found.setdefault((room,target),set()).update(keys)
 return [dict(room=k[0],target=k[1],keys=sorted(v)) for k,v in sorted(found.items())]
def sensitivity(nat,merged,by_room,pieces,boxes,locations):
 """Inside-room rate with the true scale and a wrong one: if both pass, room boxes are too loose to prove anything."""
 out={}
 for label,k in (('native 0.07',SCALE),('wrong 0.05',.05),('wrong 0.09',.09)):
  rows=[locate_record(nat,r['room'],r['world'][0],r['world'][2],by_room,pieces,boxes,locations,k) for r in merged.values()]
  good=sum(1 for h in rows if h and h['distance']<=2);out[label]=[good,len(rows)]
 return out
def wall_fit(game,nat,by_room,boxes,locations):
 """Project each single-piece room's trigger volume bounds and compare with its piece box.
 Edges only coincide at the true scale, so unlike the inside-room test a wrong scale cannot pass."""
 out={};scene=game/'nativePC/arc/scene'
 for label,k in (('native 0.07',SCALE),('wrong 0.05',.05),('wrong 0.06',.06),('wrong 0.08',.08),('wrong 0.09',.09)):
  errors=[]
  for room,pieces_ in by_room.items():
   ids={p[0] for p in pieces_ if p[0] in boxes}
   if len(ids)!=1:continue
   reg,local,name=locate(room);path=scene/f'{name}{local:02x}.arc'
   if not path.exists():continue
   a=Arc(path.read_bytes());verts=[v for m in a.members if m.kind==0x2b399b97 for L in parse_collision(a.read(m))['lists'] for v in L]
   floors=[f for f in sorted(set(locations.get(room,[]))) if f!=255]
   if not verts or len(floors)!=1:continue
   base=nat.base(reg,floors[0],local)
   if base is None:continue
   b=boxes[next(iter(ids))];l,t=to_canvas(base,min(v[0] for v in verts),min(v[2] for v in verts),k);r,bt=to_canvas(base,max(v[0] for v in verts),max(v[2] for v in verts),k)
   errors.append(sorted(abs(x-y) for x,y in zip((l,t,r,bt),b))[1]) # second-smallest edge error: triggers rarely reach every wall
  errors.sort();out[label]=dict(rooms=len(errors),median_edge_error=round(errors[len(errors)//2],2),p90=round(errors[len(errors)*9//10],2))
 return out
# The catalogue writes one enemy both ways. Split, Hunter's 5+4 rooms lost to Zombies on kind 0x2f.
PLURAL={'Zombies':'Zombie','Hunters':'Hunter','Eliminators':'Eliminator','Plague Crawlers':'Plague Crawler','Cerberuses':'Cerberus','Giant Spiders':'Giant Spider','Crows':'Crow'}
def enemy_names(rows,by_room,contents):
 """em id -> catalogue name by co-occurrence across rooms; an inference, kept with its support count."""
 place={p['id']:p for p in contents['places']};votes={}
 for row in rows:
  if row['category']!='enemy':continue
  for _,ext,*_ in by_room.get(row['room'],[]):
   for c in place[ext]['contents']:
    if c['kind']=='enemies':
     name=re.sub(r'^(\d+|∞) ','',c['name']);name=PLURAL.get(name,name);votes.setdefault(row['kind'],{}).setdefault(name,set()).add(row['room'])
 best={}
 for kind,v in votes.items():
  name,rooms=max(v.items(),key=lambda kv:len(kv[1]));best[kind]=(name,len(rooms))
 return best
def build(game,image,out):
 nat=Native(image);native=json.loads((ROOT/'data/native-map.json').read_text());matches=json.loads((ROOT/'data/room-matches.json').read_text());uses=json.loads((ROOT/'data/item-uses.json').read_text())
 en,ko=item_tables(game);pieces,by_room=places(native,matches);boxes=piece_boxes(game,native)
 # For dropped items, drawn at run time: every item's name and class; every room's native base per floor and piece, the choice locate_record makes here.
 (ROOT/'data/item-names.json').write_text(json.dumps({str(i):dict(en=n,ko=ko.get(i,n),category=category(0x71,n)) for i,n in sorted(en.items())},ensure_ascii=False,indent=0)+'\n')
 index={p['id']:i for i,p in enumerate(native['map_pieces'])};proj=[];floors_of={r['native_room_id']:r['location_bytes'] for r in native['location_records']}
 for room in sorted(by_room):
  reg,local,_=locate(room)
  for floor in sorted(set(floors_of.get(room,[]))):
   if floor==255:continue
   base=nat.base(reg,floor,local)
   if base is None:continue
   for pid in sorted({p for p,*_ in by_room[room]}):
    if pid in boxes:proj.append(dict(room=room,piece=index[pid],bx=base[0],by=base[1]))
 (ROOT/'data/room-projection.json').write_text(json.dumps(proj,indent=0)+'\n')
 doors=piece_boxes(game,native,'_door',geometry_only=True)
 locations={r['native_room_id']:r['location_bytes'] for r in native['location_records']}
 arc=Arc((game/'nativePC/arc/arrange/loctbl.arc').read_bytes());tables={k:parse_arrange(arc.read(next(m for m in arc.members if m.name.endswith(v)))) for k,v in TABLES.items()}
 merged={}
 for mode,rooms in tables.items():
  repeats={}
  for rm in rooms:
   for r in rm['records']:
    if mode.startswith('leech') and (rm['room'],r['kind'],r['a'][3]) in DECOR:continue
    x,y,z=r['pos'];spot=(rm['room'],r['kind'],r['item'],round(x,2),round(y,2),round(z,2),r['a'][0]);nth=repeats[spot]=repeats.get(spot,-1)+1
    # One row per table record, since each has its own slot and kill state: four leech places hold one record per condition (173 until pl0b g4 clears it and sets 174),
    # and room 104 holds two equal records at one spot (nth). Merged rows lost the other slot.
    row=merged.setdefault((*spot,nth),dict(room=rm['room'],kind=r['kind'],item=r['item'],world=[x,y,z],condition=r['a'][0],amount={},**({'nth':nth} if nth else {})))
    row['amount'][mode]=r['amount']
 rows=[];skipped={}
 for key,row in merged.items():
  name=en.get(row['item'],'') if row['kind'] in (0x71,0x78) else f"em{row['kind']:02x}"
  cat=category(row['kind'],name)
  if cat is None:skipped[f"{row['kind']:#x}"]=skipped.get(f"{row['kind']:#x}",0)+1;continue
  # Dial, room 134 at y -50000: never placed (bt02 g5 only deletes it, ObjDeleteType 113 118); the real Dial is the Breeding Room's row (user 2026-11-11).
  if row['world'][1]<-1000:skipped['under the world']=skipped.get('under the world',0)+1;continue
  hit=locate_record(nat,row['room'],row['world'][0],row['world'][2],by_room,pieces,boxes,locations,only=floor_of(row))
  rows.append(dict(row,category=cat,name_en=name,name_ko=ko.get(row['item'],name) if cat!='enemy' else name,evidence='arrange table',**(hit or dict(x=None,y=None,piece=None,floor=None,region=None,distance=None))))
 contents=json.loads((ROOT/'data/room-contents.json').read_text());ko_names=json.loads((ROOT/'data/names-ko.json').read_text())['names'];names=enemy_names(rows,by_room,contents)
 single={'Zombies':'Zombie','Hunters':'Hunter','Eliminators':'Eliminator','Plague Crawlers':'Plague Crawler','Cerberuses':'Cerberus','Giant Spiders':'Giant Spider','Crows':'Crow','Bats':'Bat'}
 for row in rows:
  if row['category']=='enemy' and row['kind'] in names:
   raw=names[row['kind']][0];base=single.get(raw,raw);row.update(name_en=base,name_ko=ko_names.get(raw) or ko_names.get(base) or next(ko_names[k] for k,v in PLURAL.items() if v==base),model=f"em{row['kind']:02x}",name_support=names[row['kind']][1])
 # Locks: the map's own door sprite for the target room.
 scene=game/'nativePC/arc/scene';scripts={}
 for f in sorted(scene.glob('*.arc')):
  a=Arc(f.read_bytes())
  for m in a.members:
   if m.kind==0x714ec77c:scripts[f.stem]=a.read(m)
 commands=Commands(image);lock_rows=[l for l in locks(commands,scripts,en) if (l['room'],l['target']) not in NOT_LOCKS];lock_out=[]
 seen_doors=set()
 for l in lock_rows:
  reg=next(i for i,(n,_) in enumerate(REGIONS) if n==l['room'][:2]);base=REGIONS[reg][1];source=base+int(l['room'][2:],16);target=l['target']
  tgt_reg,tgt_local,_=locate(target);tgt=f'{tgt_local:02x}'
  cand=[d for d in native['door_instances'] if d['region']==REGIONS[reg][0] and tgt in d['id'][7:].split('_') and d['id'] in doors]
  if (l['target'],tuple(l['keys'])) in seen_doors:continue # alternate scripts of one room (tr02/tr10) share the door
  seen_doors.add((l['target'],tuple(l['keys'])))
  names=[en.get(k,'') for k in l['keys'] if en.get(k) and en.get(k)!='Invalid Message']
  # Prefer the specific name when the generic one shares the check (Train Key alongside Conductor's Key).
  specific=[n for n in names if n not in ('Train Key','Facility Key','Factory Key')] or names
  key_ko=[ko.get(k,'') for k in l['keys'] if en.get(k) in specific]
  if cand:
   d=min(cand,key=lambda c:len(c['id']));b=doors[d['id']]
   lock_out.append(dict(category='lock',room=source,target=target,name_en=' / '.join(specific),name_ko=' / '.join(key_ko),x=(b[0]+b[2])/2,y=(b[1]+b[3])/2,region=d['region'],floor=d['floor'],piece=d['id'],distance=0,evidence='script key check, map door instance',amount=dict(easy=1,normal=1,hard=1)))
  else:lock_out.append(dict(category='lock',room=source,target=target,name_en=' / '.join(specific),name_ko=' / '.join(key_ko),x=None,y=None,region=None,floor=None,piece=None,distance=None,evidence='script key check; no door instance found',amount=dict(easy=1,normal=1,hard=1)))
 # Locks not found by key_check and all puzzle uses: curated room, centre of its piece, marked as room-level.
 place_piece={}
 for c in matches['claims']:
  for ext in [c['external_id'],*c.get('also_covers',[])]:place_piece[ext]=(c['native_pieces'][0],c['name_en'])
 seen_lock={r['name_en'] for r in lock_out}
 extra=[]
 for u in uses['uses']:
  pid,_=place_piece[u['place']];b=boxes.get(pid);p=pieces[pid]
  extra.append(dict(category='lock' if u['kind']=='lock' else 'puzzle',room=p['native_room_id'],name_en=u['item'],name_ko=ko_names.get(u['item'],u['item']),x=(b[0]+b[2])/2 if b else None,y=(b[1]+b[3])/2 if b else None,region=p['region'],floor=p['floor'],piece=pid,distance=0,evidence='external item page; room centre, exact position unresolved',amount=dict(easy=1,normal=1,hard=1)))
 placed_targets={r['target'] for r in lock_out if r['x'] is not None}
 extra=[r for r in extra if r['category']!='lock' or r['room'] not in placed_targets]
 curated_rooms={r['room'] for r in extra if r['category']=='lock'}
 lock_out=[r for r in lock_out if r['x'] is not None or r['target'] not in curated_rooms]
 for r in lock_out:
  if not r['name_en']:r.update(name_en='Key (unnamed in messages)',name_ko='열쇠(메시지 이름 없음)')
 locks_without_door=place_locks(lock_out+extra,native,door_paint(game,native))
 puzzles_without_position=place_puzzles(extra,game,nat,en,commands,by_room,pieces,boxes,locations)
 all_rows=rows+lock_out+extra+script_rows(game,nat,en,ko,by_room,pieces,boxes,locations)
 event_marks,event_audit=place_events(all_rows,game,nat,image,by_room,pieces,boxes,locations)
 event_marks+=puzzle_events(all_rows,event_audit)
 snap_room_level([*all_rows,*event_marks],game,native,by_room)
 (ROOT/'verification/event-audit.json').write_text(json.dumps(dict(schema_version=1,evidence=events_rule,rows=event_audit),ensure_ascii=False,indent=0)+'\n')
 result=dict(schema_version=1,locks_without_door=locks_without_door,puzzles_without_position=puzzles_without_position,canvas=[1280,720],sensitivity=sensitivity(nat,merged,by_room,pieces,boxes,locations),wall_fit=wall_fit(game,nat,by_room,boxes,locations),sources=dict(items_enemies='nativePC/arc/arrange/loctbl.arc',locks='event scripts and map door instances',puzzles='data/item-uses.json',script_items='SCRIPT_GRANTS in tools/extract/placements.py'),skipped_kinds=skipped,rows=all_rows+event_marks)
 out.write_text(json.dumps(result,ensure_ascii=False,indent=0)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game',type=Path,required=True);p.add_argument('--analysis-image',type=Path,default=ROOT/'local/research/re0hd.analysis.bin');p.add_argument('--output',type=Path,default=ROOT/'data/placements.json');a=p.parse_args()
 r=build(a.game,a.analysis_image.read_bytes(),a.output);import collections
 print(collections.Counter(x['category'] for x in r['rows']),'skipped',r['skipped_kinds'])
