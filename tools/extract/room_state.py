"""What the map draws for each piece and which doors belong to it, evaluated by native code. Analysis only: Unicorn runs the game's own functions over its own tables.

Piece state, 0x5b4afa-0x5b4b27: state = visited + 2*revealed, read as a colour index at 0xd9de40 (0x5b4cfc). State 0 skips the piece at 0x5b4b94, so the game draws no room in neither state.
Revealed: flag 0x2c8+the piece's region, set by the map item (0x5d74a1, item id-0x8f with 4 and 5 swapped). One exception, 0x5b4b2d-0x5b4b9a: room 0x19 of region 5 also counts under the map of the region on screen.
Visited: 0x5bac90(region on screen, global room, floor) through bit test 0x59b8d0. Mostly flag 0x200+room (written at 0x60ed84, 0x60ee53, 0x61e7df), some rooms a second flag per floor, room 0xa6 one flag per floor.
Its result is checked here against the AND of the flags it asked for, on every combination, so a rule that is anything else stops the build.
Doors: 0x5bb420(region on screen, floor, local room) as the show path 0x5b4d48 calls it: GUI instance indices whose door the piece turns on (0x5b4d79).
Not exercised: the running game, real saves.
"""
import argparse,hashlib,json,struct
from pathlib import Path
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EAX
ROOT=Path(__file__).resolve().parents[2]
BASE=0x400000;DONE=0x1000;STACK=0x201f0000;OWNER=0x20100000;MAP_STATE=0x20120000
FLOOR_LISTS=0xd9eca0;REGION_FIRST=0xdb0b70;VISITED=0x5bac90;DOORS=0x5bb420;BIT=0x59b8d0;OWNER_GLOBAL=0xdcc014;PLAYER_GLOBAL=0xdcbf40
REVEALED_BASE=0x2c8;LIST_END=1000;SPECIAL_REGION=5;SPECIAL_ROOM=0x19;WORDS=33
class Native:
 def __init__(self,image):
  pe=struct.unpack_from('<I',image,60)[0];opt=pe+24;size=struct.unpack_from('<I',image,opt+56)[0]
  self.uc=uc=Uc(UC_ARCH_X86,UC_MODE_32);uc.mem_map(BASE,(size+0xfff)&~0xfff);uc.mem_write(BASE,image[:0x1000])
  for i in range(struct.unpack_from('<H',image,pe+6)[0]):
   o=opt+struct.unpack_from('<H',image,pe+20)[0]+i*40;_,va,raw_size,raw=struct.unpack_from('<4I',image,o+8)
   if raw_size:uc.mem_write(BASE+va,image[raw:raw+raw_size])
  uc.mem_map(DONE,0x1000);uc.mem_map(0x20000000,0x200000)
  uc.mem_write(OWNER_GLOBAL,struct.pack('<I',OWNER));uc.mem_write(PLAYER_GLOBAL,struct.pack('<I',0x20110000))
  self.asked=[];uc.hook_add(UC_HOOK_CODE,self.on_bit,begin=BIT,end=BIT)
 def on_bit(self,uc,address,size,_):self.asked.append(struct.unpack('<H',bytes(uc.mem_read(uc.reg_read(UC_X86_REG_ESP)+4,2)))[0])
 def u32(self,a):return struct.unpack('<I',bytes(self.uc.mem_read(a,4)))[0]
 def u16(self,a):return struct.unpack('<H',bytes(self.uc.mem_read(a,2)))[0]
 def call(self,address,ecx,*args):
  self.uc.mem_write(STACK,struct.pack(f'<{1+len(args)}I',DONE,*args));self.uc.reg_write(UC_X86_REG_ESP,STACK);self.uc.reg_write(UC_X86_REG_ECX,ecx);self.uc.emu_start(address,DONE,count=500000)
  return self.uc.reg_read(UC_X86_REG_EAX)
 def flags(self,on):
  words=[0]*WORDS
  for f in on:words[f>>5]|=1<<(f&31)
  self.uc.mem_write(OWNER+0x20,struct.pack(f'<{WORDS}I',*words))
 def visited(self,display,room,floor):
  """The flags the native test reads, proved to be their AND."""
  every=range(WORDS*32);self.flags(every);self.asked=[];all_set=self.call(VISITED,MAP_STATE,display,room,floor);asked=list(self.asked)
  if not all_set or not asked or len(asked)>2:raise ValueError(f'visited test of room {room:#x} floor {floor} is not a flag AND: {asked} -> {all_set}')
  for mask in range(1<<len(asked)):
   off={f for i,f in enumerate(asked) if not mask>>i&1};self.flags(f for f in every if f not in off)
   if bool(self.call(VISITED,MAP_STATE,display,room,floor))!=(not off):raise ValueError(f'visited test of room {room:#x} floor {floor} is not a flag AND at {mask}')
  return asked
 def doors(self,display,floor,local):
  p=self.call(DOORS,0,display,floor,local);out=[]
  while p:
   v=self.u16(p+len(out)*2)
   if v==0xffff:break
   out.append(v)
  return out
def build(image,native):
 nat=Native(image);names=[r['region'] for r in sorted(native['native_regions'],key=lambda r:r['region_index'])];pieces={};doors={}
 by_gui={(d['region'],d['instance_index']):d for d in native['door_instances']}
 for display,screen in enumerate(names):
  for floor in range(12):
   at=nat.u32(FLOOR_LISTS+(display*12+floor)*4);n=0
   while at:
    region,local=struct.unpack('<HH',bytes(nat.uc.mem_read(at+n*4,4)))
    if region>=LIST_END:break
    n+=1;room=nat.u32(REGION_FIRST+region*4)+local;prefix=f'i_{names[region]}{local:02x}{floor:x}'
    found=[p for p in native['map_pieces'] if p['region']==screen and p['id'].startswith(prefix)]
    if not found:raise ValueError(f'list entry {screen} {prefix} has no GUI piece')
    revealed=[REVEALED_BASE+region]
    if region==SPECIAL_REGION and local==SPECIAL_ROOM and display!=region:revealed.append(REVEALED_BASE+display)
    visited=nat.visited(display,room,floor)
    for p in found:
     if p['native_room_id']!=room:raise ValueError(f"{p['id']} is room {p['native_room_id']}, the list says {room}")
     pieces[p['id']]=dict(visited=visited,revealed=revealed)
     for index in nat.doors(display,floor,local):
      d=by_gui.get((screen,index))
      if d is None:continue # the GUI has no door at this index
      if d['floor']==p['floor']:doors.setdefault(d['id'],[]).append(p['id'])
 missing=[p['id'] for p in native['map_pieces'] if p['id'] not in pieces]
 if missing:raise ValueError(f'pieces no floor list holds: {missing}')
 return dict(schema_version=1,evidence='Unicorn runs of native 0x5bac90 and 0x5bb420 over the floor lists at 0xd9eca0; no run of the game',analysis_sha256=hashlib.sha256(image).hexdigest(),rule=__doc__,pieces=pieces,doors=doors,doors_without_room=[d['id'] for d in native['door_instances'] if d['id'] not in doors])
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--analysis-image',type=Path,default=ROOT/'local/research/re0hd.analysis.bin');p.add_argument('--output',type=Path,default=ROOT/'data/room-state.json');a=p.parse_args()
 r=build(a.analysis_image.read_bytes(),json.loads((ROOT/'data/native-map.json').read_text()));a.output.write_text(json.dumps(r,ensure_ascii=False,indent=0)+'\n')
 print(f"{len(r['pieces'])} pieces, {len(r['doors'])} doors with rooms, without: {r['doors_without_room']}")
