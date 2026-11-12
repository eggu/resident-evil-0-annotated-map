"""End-to-end offline gate: objects built by the game's own constructors, drawn by the game's own dispatch, through the real hook slots.

Everything hand-written is kept to wiring (tree links, visibility). Field values come from native code, because
hand-written fixtures repeat the author's assumptions. Mutants re-introduce past live failures and must be caught.
"""
from pathlib import Path
import argparse,concurrent.futures,json,math,os,shutil,struct,subprocess,sys,tempfile
from unicorn import Uc,UcError,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_PROT_ALL
from unicorn.x86_const import UC_X86_REG_EBP,UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EIP,UC_X86_REG_EAX
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/inspect'))
from check_adapter import load_dll,INI
CC='i686-w64-mingw32-gcc'
FLAGS=['-std=c11','-O2','-shared','-static-libgcc','-w','-Wl,--image-base,0x62000000','-Wl,--dynamicbase']
LIBS=['-lkernel32','-luser32','-ladvapi32']
BASE=0x400000;DONE=0x1000
HEAP=0x30000000
# Live candidate 3 log, 2026-11-03: values this harness must reproduce from native code alone.
LIVE=dict(sprite_a0=0xff5,instance_vtable=0xd25448)
# Past live failures. Each must make this harness fail, or the harness proves nothing.
MUTANTS={
 'Original menu ignored':('src/runtime/re0_map.c','c.display_mode=display_mode();','c.display_mode=0;'),
 'native viewport right not read':('src/runtime/re0_map.c','(int)u32(r+0xc4),(int)u32(r+0xc8)','0,0'),
 'whole gradient band treated as outside (candidate 55, user shot 21)':('src/core/annotation.h','(79.0f/224.0f)','(1.0f)'),
 'gradient spill reported by user':('src/runtime/re0_map.c','dim[0]==224.0f&&dim[1]==720.0f','0'),

 '21:9 overlay ignores the render rect (candidate 23)':('src/runtime/re0_map.c','box=re0_gui_to_backbuffer(box,&rect);','(void)rect;'),
 'render rect read from the display size':('src/runtime/re0_map.c','(int)u32(s+0xa4),(int)u32(s+0xa8)','(int)u32(s+0xb8),(int)u32(s+0xa8)'),
 'icons drawn without mips':('src/runtime/re0_map.c','on?D3DTEXF_LINEAR:D3DTEXF_NONE','D3DTEXF_NONE'),
 'mip filter left on for text':('src/runtime/re0_map.c','on?D3DTEXF_LINEAR:D3DTEXF_NONE','D3DTEXF_LINEAR'),
 'icons sampled from the atlas':('src/runtime/re0_map.c','on?(IDirect3DBaseTexture9 *)icon_tex:(IDirect3DBaseTexture9 *)atlas','(IDirect3DBaseTexture9 *)atlas'),
 'bind not restored for text':('src/runtime/re0_map.c',' bind_icons(dev,0);\n',''),
 'every level gets level 0':('src/runtime/re0_map.c','  src+=w*h*4;\n',''),
 'level lock failure ignored':('src/runtime/re0_map.c','{icon_load_failures++;IDirect3DTexture9_Release(t);return 0;}','continue;'),
 'annotations on the frame (candidate 29, 2560x1440 shot)':('src/runtime/re0_map.c','dim[0]==176.0f&&dim[1]==152.0f','0'),
 'list box stays with the list closed (candidate 31, door icon cut)':('src/runtime/re0_map.c','list_seen&&present_count-list_seen_at<=2?2:1','2'),
 'list open not seen':('src/runtime/re0_map.c','dim[0]==744.0f&&dim[1]==93.0f','0'),
 'rows dump on the wrong global':('src/runtime/re0_map.c','const BYTE *mgr=(const BYTE *)(uintptr_t)u32(VA(0xdcc010));\n if(!mgr||!readable(mgr,ROWS_MODE+4)','const BYTE *mgr=(const BYTE *)(uintptr_t)u32(VA(0xdcc00c));\n if(!mgr||!readable(mgr,ROWS_MODE+4)'),
 'rows dump count unchecked':('src/runtime/re0_map.c',' if(count>ROWS_SLOTS)return 0;\n',''),
 'rows dump manager unchecked':('src/runtime/re0_map.c',' if(!mgr||!readable(mgr,ROWS_MODE+4)||!readable(mgr,ROWS_FIRST+ROWS_SLOTS*ROWS_STEP))return 0;\n',''),
 'rows dump wrong stride':('src/runtime/re0_map.c','mgr+ROWS_FIRST+s*ROWS_STEP,ROWS_STEP','mgr+ROWS_FIRST+s*0x58,ROWS_STEP'),
 'freed slot draws its stale bytes (rows-03, candidate 33)':('src/core/frame.c','if(link==0xffffffffu||kind!=DROP_KIND)continue;','if(kind!=DROP_KIND)continue;link=36;'),
 'dropped room read from row +0 (0 in live slot 589)':('src/core/frame.c','drop_project(link,pos[0],pos[1],pos[2]','drop_project(0,pos[0],pos[1],pos[2]'),
 'dropped amount from the wrong field':('src/core/frame.c','memcpy(&amount,row+0x3c,4)','memcpy(&amount,row+0x18,4)'),
 'frame stays on after V':('src/runtime/re0_map.c','present_count-frame_seen_at<=2','1'),
 'instance hook on AnimVariable slot (candidate 1)':('src/runtime/re0_map.c','VA(0xd25478)','VA(0xd254e0)'),
 'anchor rejected instead of masked (candidates 1-3)':('src/core/map_transform.c','anchor &= 15;',';'),
 'room owner read from the wrong field (sensitivity check)':('src/runtime/re0_map.c','owner=u32(self+0x6c)','owner=u32(self+0x70)'),
 'flag owner pointer at the wrong global':('src/runtime/re0_map.c','u32(VA(0xdcc014))','u32(VA(0xdcc018))'),
 'flag array at the wrong offset':('src/runtime/re0_map.c','memcpy(live_flags,owner+0x20,','memcpy(live_flags,owner+0x24,'),
 'condition flag base off by one':('src/core/annotation.h','#define RE0_FLAG_BASE 0x312','#define RE0_FLAG_BASE 0x313'),
 'game draws no location marks (candidates up to 17)':('src/runtime/re0_map.c','fixed?&view:0,0,live_flags,&live_arrange,','0,0,live_flags,&live_arrange,'),
 'game ignores the condition flags':('src/runtime/re0_map.c','fixed?&view:0,0,live_flags,&live_arrange,','fixed?&view:0,0,0,&live_arrange,'),
 'placement manager at the wrong global':('src/runtime/re0_map.c','u32(VA(0xdcc010))','u32(VA(0xdcc00c))'),
 'row stride wrong':('src/core/annotation.c','STRIDE=0x5c','STRIDE=0x58'),
 'taken state ignored':('src/core/frame.c','return !re0_marker_state_done(&marker_state[index],flags,arrange)&&re0_condition_met','return re0_condition_met'),
 'taken rows stay shown':('src/core/annotation.c','if(kind==0||row[GONE]||','if(row[GONE]||'),
 'difficulty stays manual':('src/runtime/re0_map.c','if(difficulty>=0)cfg.difficulty=difficulty;else cfg.difficulty=ini_difficulty;','(void)difficulty;'),
 'table told by the mode field (candidate 21, save load)':('src/core/annotation.c','for(int i=0;i<3;i++)if(a->count==table_rows[i]) return i;','for(int i=0;i<3;i++)if(a->count==table_rows[i]&&read_u32(a->rows+0x24ff0)==(unsigned)i) return i;'),
 'row guard dropped':('src/core/annotation.c','if(read_u32(row)!=m->room||(kind&&kind!=m->kind)||(m->item!=0xffff&&read_u32(row+ITEM)!=m->item)){a->mismatches++;return 0;}',''),
 'fade owner at the wrong global':('src/runtime/re0_map.c','u32(VA(0xdcbea4))','u32(VA(0xdcbea8))'),
 'fade alpha at the wrong offset':('src/runtime/re0_map.c','return fade[0x277]<=FADE_DRAW_ALPHA;','return fade[0x276]<=FADE_DRAW_ALPHA;'),
 'drawn through a fade':('src/runtime/re0_map.c','return fade[0x277]<=FADE_DRAW_ALPHA;','return 1;'),
 'fade only: stale capture drawn when a fast fade returns to clear':('src/runtime/re0_map.c','const int allowed=re0_present_gate(&present_gate,c->generation,clear,live);','const int allowed=clear;'),
 'map state ignored at Present':('src/runtime/re0_map.c','const int live=map_live(c);','const int live=1;'),
 'hidden through a whole fade':('src/runtime/re0_map.c','return fade[0x277]<=FADE_DRAW_ALPHA;','return fade[0x277]==0;'),
 'condition polarity inverted':('src/core/annotation.c','return (int)(flags[flag>>5]>>(flag&31)&1);','return !(flags[flag>>5]>>(flag&31)&1);'),
 'killed enemy stays shown (candidate 22, live report)':('src/core/annotation.c','if(kind==0||row[GONE]||','if(kind==0||'),
 'row+0x41 read as killed (earlier note): every saved actor sets it':('src/core/annotation.c','GONE=0x39','GONE=0x41'),
 'kills in a loaded room not read':('src/runtime/re0_map.c','live_table_mode=(int)u32(mgr+MODE);read_actors();','live_table_mode=(int)u32(mgr+MODE);'),
 'live HP polarity inverted':('src/core/annotation.c','||hp>0) return;','||hp<=0) return;'),
 'item or player actor at HP 0 counts as a kill':('src/core/annotation.c','if(re0_kind_is_enemy(read_u32(a->rows+ROW_BASE+(unsigned)slot*STRIDE+KIND))) killed','killed'),
 'actor list next link wrong':('src/runtime/re0_map.c','NEXT=0x14,STATE','NEXT=0x18,STATE'),
 'actor list head wrong':('src/runtime/re0_map.c','LAYER=0x18,HEAD=0x2c','LAYER=0x18,HEAD=0x28'),
 'one actor layer walked':('src/runtime/re0_map.c','for(unsigned l=0;l<3;l++) {','for(unsigned l=0;l<1;l++) {'),
 'deleted actor counts as a kill':('src/runtime/re0_map.c','if(state!=3&&state!=4)re0_arrange_note_actor','re0_arrange_note_actor'),
 'actor HP at the wrong offset':('src/runtime/re0_map.c','SLOT=0xff0,HP=0x1030','SLOT=0xff0,HP=0x1034'),
 'enemy row guarded on row+8, which 0x412c30 rewrites':('src/core/annotation.c','(m->item!=0xffff&&read_u32(row+ITEM)!=m->item)','read_u32(row+ITEM)!=m->item'),
 'row guard ignores the kind':('src/core/annotation.c','(kind&&kind!=m->kind)||',''),
 'mark tied to one piece of its room (candidate 22, live report: Ice Pick)':('src/core/frame.c','(allowed&&rooms[j].place==rooms[i].place)','(allowed&&j==i)'),
 'room name tied to one piece of its room':('src/core/frame.c','clip,legend,readout,room_on,used,n,','clip,legend,readout,room_seen,used,n,'),
 'door mark follows one room only':('src/core/frame.c','for(unsigned i=0;i<m->rooms;i++)if(room_on[marker_rooms[m->first_room+i]])return 1;\n return 0;','return room_on[m->piece];'),
 'visited rule drops the per-floor flag':('src/core/frame.c','&&(r->visited1==0xffff||flag_set(flags,r->visited1))',''),
 'visited polarity inverted':('src/core/frame.c','(flag_set(flags,r->visited0)&&','(!flag_set(flags,r->visited0)&&'),
 'revealed polarity inverted':('src/core/frame.c','(flag_set(flags,r->revealed0)||flag_set(flags,r->revealed1))<<1','!(flag_set(flags,r->revealed0)||flag_set(flags,r->revealed1))<<1'),
 'room 0x19 of region 5 misses the on-screen map':('src/core/frame.c','||flag_set(flags,r->revealed1))<<1',')<<1'),
 'visited base flag off by one in the table':('src/core/frame.c','room_state[i];','room_state[i?i-1:0];'),
 'scope ignored: every drawn room counts':('src/core/frame.c','allowed=!flags||(s->scope==RE0_SCOPE_REVEALED?state!=0:state&1)','allowed=1'),
 'revealed scope acts as visited':('src/core/frame.c','(s->scope==RE0_SCOPE_REVEALED?state!=0:state&1)','(state&1)'),
 'All scope only lights drawn rooms':('src/core/frame.c','s->scope==RE0_SCOPE_ALL||(allowed&&rooms[j].place==rooms[i].place)','(allowed&&rooms[j].place==rooms[i].place)'),
 'All patch on another call':('src/runtime/re0_map.c','BYTE *call_site=VA(0x5b4afa);','BYTE *call_site=VA(0x5b4b73);'),
 'All patch answers yes in every scope':('src/runtime/re0_map.c','if(cfg.enabled&&cfg.scope==RE0_SCOPE_ALL)return 1;','return 1;'),
 'All patch opens the floor tabs too':('src/runtime/re0_map.c','VirtualProtect(call_site+1,4,old,&old);FlushInstructionCache','{BYTE *t=VA(0x5bb998);const int r=(int)((BYTE *)flag_all_scope-(t+5));memcpy(t+1,&r,4);}VirtualProtect(call_site+1,4,old,&old);FlushInstructionCache'),
 'All patch opens the region count too':('src/runtime/re0_map.c','VirtualProtect(call_site+1,4,old,&old);FlushInstructionCache','{BYTE *t=VA(0x5b3c5b);const int r=(int)((BYTE *)flag_all_scope-(t+5));memcpy(t+1,&r,4);}VirtualProtect(call_site+1,4,old,&old);FlushInstructionCache'),
 'All patch never answers':('src/runtime/re0_map.c','if(cfg.enabled&&cfg.scope==RE0_SCOPE_ALL)return 1;','if(cfg.enabled&&cfg.scope==RE0_SCOPE_ALL)return 0;'),
 'scope not read from the INI':('src/runtime/re0_map.c','cfg.scope=(int)GetPrivateProfileIntA("Map","Visibility",RE0_SCOPE_VISITED,ini_path);','cfg.scope=RE0_SCOPE_VISITED;'),
 'out-of-range scope kept':('src/runtime/re0_map.c','if(cfg.scope<RE0_SCOPE_VISITED||cfg.scope>RE0_SCOPE_ALL)cfg.scope=RE0_SCOPE_VISITED;',''),
 'ItemNames not read from the INI':('src/runtime/re0_map.c','cfg.item_names=re0_settings_item_names(version,(int)GetPrivateProfileIntA("Map","ItemNames",0,ini_path));','cfg.item_names=0;'),
 'Contents not migrated by Version':('src/core/frame.c','return version<RE0_CONTENTS_VERSION?v&63u:v;','return v;'),
 'Contents default shows events':('src/runtime/re0_map.c','(int)RE0_MASK_DEFAULT,ini_path','127,ini_path'),
 'colours not read from the INI':('src/runtime/re0_map.c','if(re0_color_parse(text,&rgb))re0_frame_set_color(i,rgb);','if(re0_color_parse(text,&rgb))(void)rgb;'),
 'a bad colour replaces the shipped one':('src/core/frame.c','if(*t&&*t!=\';\'&&*t!=\'\\r\'&&*t!=\'\\n\')return 0;','(void)0;'),
 'colour keys shifted':('src/runtime/re0_map.c','{"Lock","KeyItem","File","Puzzle","Item","Enemy","Event"}','{"Lock","KeyItem","File","Puzzle","Enemy","Item","Event"}'),
 'ItemNames not migrated by Version':('src/core/frame.c','return version<RE0_ITEM_NAMES_VERSION?value!=0:value>=0&&value<=2?value:0;','return value>=0&&value<=2?value:0;'),
 'ItemNames 2 not kept':('src/core/frame.c','return version<RE0_ITEM_NAMES_VERSION?value!=0:value>=0&&value<=2?value:0;','return value!=0;'),
 'unknown table keeps the last difficulty, not the INI value':('src/runtime/re0_map.c','if(difficulty>=0)cfg.difficulty=difficulty;else cfg.difficulty=ini_difficulty;','if(difficulty>=0)cfg.difficulty=difficulty;'),
}
def header_mutants():
 """Past live failures in generated data, built from the header as it stands so regenerating keeps them aimed. The position is the row's own from before Flag decided the door."""
 rows=json.loads((ROOT/'data/placements.json').read_text())['rows'];conductor=next(r for r in rows if r['category']=='lock' and r['name_en']=="Conductor's Key")
 return {"Conductor's Key on the Cabin 201 door (live report)":('src/runtime/labels_generated.h',f"{{{conductor['x']:.1f}f,{conductor['y']:.1f}f,",'{489.0f,368.0f,')}
def compile_probe(root,output):
 subprocess.run([CC,*FLAGS,str(root/'tests/runtime_probe.c'),str(root/'src/core/map_transform.c'),str(root/'src/core/annotation.c'),str(root/'src/core/frame.c'),'-o',str(output),*LIBS],check=True)
class Game:
 def __init__(self,image,dll):
  self.image=image;self.uc=uc=Uc(UC_ARCH_X86,UC_MODE_32);pe=struct.unpack_from('<I',image,60)[0];opt=pe+24
  size=struct.unpack_from('<I',image,opt+56)[0];uc.mem_map(BASE,(size+0xfff)&~0xfff);uc.mem_write(BASE,image[:0x1000])
  for i in range(struct.unpack_from('<H',image,pe+6)[0]):
   o=opt+struct.unpack_from('<H',image,pe+20)[0]+i*40;vs,va,raw_size,raw=struct.unpack_from('<4I',image,o+8)
   if raw_size:uc.mem_write(BASE+va,image[raw:raw+raw_size])
  uc.mem_map(DONE,0x1000);uc.mem_map(0x20000000,0x200000);uc.mem_map(HEAP,0x400000);self.heap=HEAP
  self.exports,_=load_dll(uc,dll);self.stubs={};self.stop_at=None;self.stopped=False;self.seen_calls={};self.answers={}
  uc.hook_add(UC_HOOK_CODE,self.on_code)
 def alloc(self,size):
  at=self.heap;self.heap+=(size+0xf)&~0xf;return at
 def stub(self,address,clean):self.stubs[address]=clean
 def on_code(self,uc,address,size,_):
  if address==self.stop_at:self.stopped=True;uc.emu_stop();return
  if address in self.seen_calls:self.seen_calls[address].append(struct.unpack('<I',bytes(uc.mem_read(uc.reg_read(UC_X86_REG_ESP)+4,4)))[0])
  if address in self.stubs:
   sp=uc.reg_read(UC_X86_REG_ESP);ret=struct.unpack('<I',bytes(uc.mem_read(sp,4)))[0];answer=self.answers.get(address)
   uc.reg_write(UC_X86_REG_EAX,answer(sp) if answer else 0);uc.reg_write(UC_X86_REG_ESP,sp+4+self.stubs[address]);uc.reg_write(UC_X86_REG_EIP,ret)
 def call(self,address,ecx=0,*args,thiscall=True,limit=3000000):
  """Run with a fresh stack; thiscall/stdcall callees clean their own arguments."""
  uc=self.uc;sp=0x201f0000-0x100
  uc.mem_write(sp,struct.pack(f'<{1+len(args)}I',DONE,*args));uc.reg_write(UC_X86_REG_ESP,sp);uc.reg_write(UC_X86_REG_ECX,ecx)
  uc.emu_start(address,DONE,count=limit)
  if uc.reg_read(UC_X86_REG_EIP)!=DONE:raise RuntimeError(f'{address:#x} did not return')
  return uc.reg_read(UC_X86_REG_EAX)
 def reaches(self,address,stop,ecx,*args):
  """Runs until stop or the function's return; True when stop came first."""
  self.stop_at=stop;self.stopped=False
  uc=self.uc;sp=0x201f0000-0x100;uc.mem_write(sp,struct.pack(f'<{1+len(args)}I',DONE,*args));uc.reg_write(UC_X86_REG_ESP,sp);uc.reg_write(UC_X86_REG_ECX,ecx);uc.emu_start(address,DONE,count=3000000)
  self.stop_at=None;return self.stopped
 def u32(self,a):return struct.unpack('<I',bytes(self.uc.mem_read(a,4)))[0]
 def put(self,a,v):self.uc.mem_write(a,struct.pack('<I',v))
 def putf(self,a,*v):self.uc.mem_write(a,struct.pack(f'<{len(v)}f',*v))
def icon_gate(g):
 """The icon path against a fake device: levels, failures, bind and mip filter. Not D3D: no pixels or sampling are exercised."""
 up=g.exports['re0_probe_icon_upload'];dr=g.exports['re0_probe_icon_draw'];c=lambda a,*v:g.call(a,0,*v,thiscall=False,limit=2000000)
 return dict(upload=c(up,0,0xffffffff),create_fails=c(up,1,0xffffffff),level1_fails=c(up,0,1),loaded=c(dr,1),failed=c(dr,0))
def frame_gate(g,slot,map_,args,obj,fresh):
 """Live 2560x1440 shot: annotations on the shown frame. The help panel sprite through the real slot turns the frame on; absent for three Presents it is off, as after V."""
 shown=g.exports['re0_probe_frame_shown'];c=lambda a,*v:g.call(a,0,*v,thiscall=False);out=dict(before=c(shown))
 g.uc.mem_write(HEAP,fresh);g.putf(obj+0xc0,176,152);g.putf(obj+0x10,1.5);g.putf(obj+0x24,1.5);g.call(slot,map_,args);g.putf(obj+0xc0,172,48);g.putf(obj+0x10,1);g.putf(obj+0x24,1);out['seen']=c(shown);out['right']=c(g.exports['re0_probe_frame_right'])
 g.uc.mem_write(HEAP,fresh);g.putf(obj+0xc0,744,93);g.call(slot,map_,args);g.putf(obj+0xc0,172,48);out['list_open']=c(shown);c(g.exports['re0_probe_frames'],3);g.uc.mem_write(HEAP,fresh);g.putf(obj+0xc0,176,152);g.call(slot,map_,args);g.putf(obj+0xc0,172,48);out['list_closed']=c(shown)
 c(g.exports['re0_probe_frames'],3);out['after_v']=c(shown);return out
def rows_gate(g):
 """F8 rows diagnostic against a manager filled with a pattern the author does not pick per slot: no manager, count over the bound, and a real read that writes nothing."""
 import random
 fmt=lambda:g.call(g.exports['re0_probe_rows_format'],thiscall=False,limit=30000000);mgr=g.alloc(0x30000);old=g.u32(0xdcc010);out={}
 g.put(0xdcc010,0);out['no_manager']=fmt()
 g.put(0xdcc010,mgr);g.put(mgr+0x24fac,0x4e9);out['count_over']=fmt()
 r=random.Random(0xdcc010);g.uc.mem_write(mgr,bytes(r.getrandbits(8) for _ in range(0x30+0x4e8*0x5c)));g.put(mgr+0x24fac,0x4e0);g.put(mgr+0x24ff0,1)
 before=bytes(g.uc.mem_read(mgr,0x25000));n=fmt();out['wrote']=bytes(g.uc.mem_read(mgr,0x25000))!=before
 try:doc=json.loads(bytes(g.uc.mem_read(g.call(g.exports['re0_probe_rows_text'],thiscall=False),n)))
 except ValueError as e:raise AssertionError(f'rows dump unreadable: {e}')
 rows=doc['rows']
 out['count']=doc['count'];out['slots']=[x['slot'] for x in rows]
 out['bytes_ok']=all(bytes.fromhex(x['hex'])==before[0x30+x['slot']*0x5c:0x30+(x['slot']+1)*0x5c] and x['link']==struct.unpack_from('<I',before,0x2c+x['slot']*0x5c)[0] for x in rows)
 g.put(mgr+0x24fac,0x4e8);out['count_at_bound_rows']=len(json.loads(bytes(g.uc.mem_read(g.call(g.exports['re0_probe_rows_text'],thiscall=False),fmt())))['rows'])
 g.put(0xdcc010,old);return out
def drop_gate(g,native):
 """Live row, slot 589, through the overlay: drawn with its icon and x2, gone when freed or picked up, off with its category, and through the ASI's real table read. Native manager is hand-filled from the live capture; the native drop function is not run."""
 import re
 H=(ROOT/'src/runtime/labels_generated.h').read_text();items=[int(v) for v in re.search(r'drop_items\[\] = \{([0-9,]+)\}',H)[1].split(',')];icon=items[55*7+4];mult=int(re.search(r'#define DROP_MULT (\d+)',H)[1])
 old=g.u32(0xdcc010);mgr=g.alloc(0x30000);g.put(0xdcc010,mgr);g.put(mgr+0x24fac,589);slot=mgr+589*0x5c
 for s in range(589,0x4e8):g.put(mgr+0x2c+s*0x5c,0xffffffff)
 pieces=native['map_pieces'];idx=next(i for i,p in enumerate(pieces) if p['id']=='i_sh0090')
 lay=json.loads((ROOT/'data/room-layout.json').read_text())['pieces']['i_sh0090'];box=g.alloc(16);g.putf(box,*[v*1.5 for v in lay])
 g.call(g.exports['re0_probe_rooms_clear'],thiscall=False);g.call(g.exports['re0_probe_room_box'],0,idx,box,thiscall=False);g.call(g.exports['re0_probe_set_scope'],0,2,thiscall=False)
 def glyphs():
  g.call(g.exports['re0_probe_read_arrange'],thiscall=False);n=g.call(g.exports['re0_probe_overlay'],0,1920,1080,thiscall=False,limit=60000000);at=g.call(g.exports['re0_probe_ops'],thiscall=False);d=bytes(g.uc.mem_read(at,n*24));return [struct.unpack_from('<i',d,i*24+20)[0] for i in range(n)]
 out={}
 base_name=glyphs().count(items[55*7]);base=glyphs().count(icon) # static Ink Ribbon marks of the room
 g.put(mgr+0x2c+589*0x5c,36);g.put(mgr+0x30+589*0x5c+4,0x71);g.put(mgr+0x30+589*0x5c+8,55);g.put(mgr+0x30+589*0x5c+0x3c,2);g.putf(mgr+0x30+589*0x5c+0x20,1096.29,-1,955.42)
 a=glyphs();out['icon']=a.count(icon)-base;out['count']=int(mult in a)
 out['name']=a.count(items[55*7])-base_name
 g.put(mgr+0x2c+589*0x5c,0xffffffff);out['freed']=glyphs().count(icon)-base
 g.put(mgr+0x2c+589*0x5c,36);g.put(mgr+0x30+589*0x5c+4,0);out['kind_zero']=glyphs().count(icon)-base
 g.put(0xdcc010,old);g.call(g.exports['re0_probe_rooms_clear'],thiscall=False);g.call(g.exports['re0_probe_set_scope'],0,0,thiscall=False);return out
def flag_gate(g):
 """The ASI's read and shared rule against native 0x59b8d0, every condition byte, with bit patterns the author did not choose."""
 import random
 rng=random.Random(0x59b8d0);holder=g.alloc(0x200);g.put(0xdcc014,holder);words=33;bad=[]
 patterns=[[0]*words,[0xffffffff]*words,[0x55555555]*words,[0xaaaaaaaa]*words]+[[rng.getrandbits(32) for _ in range(words)] for _ in range(4)]
 for words_now in patterns:
  g.uc.mem_write(holder+0x20,struct.pack(f'<{words}I',*words_now));g.call(g.exports['re0_probe_read_flags'],thiscall=False)
  for condition in range(1,256):
   native=g.call(0x59b8d0,holder,0x312+condition)
   if bool(native)!=bool(g.call(g.exports['re0_probe_condition'],0,condition,thiscall=False)):bad.append(condition)
 # Condition 0 skips the gate natively (0x410c4a); no owner yet means unknown, which must count and not pass.
 zero=g.call(g.exports['re0_probe_condition'],0,0,thiscall=False)
 g.put(0xdcc014,0);before=g.call(g.exports['re0_probe_counter'],0,17,thiscall=False);g.call(g.exports['re0_probe_read_flags'],thiscall=False)
 after=g.call(g.exports['re0_probe_counter'],0,17,thiscall=False);unknown=g.call(g.exports['re0_probe_condition'],0,1,thiscall=False)
 return dict(mismatches=len(bad),patterns=len(patterns),condition_zero=zero,unreadable_counted=after-before,unknown_passes=unknown)
def fade_gate(g):
 """Native starters 0x5aa410 (clear to opaque) and 0x5aa2c0 (opaque to clear) set the start colour the overlay reads. Mid-fade alpha is set by hand: the per-frame update 0x5aa060 is not run here."""
 ONE=0x3f800000;holder=g.alloc(0x40);fade=g.alloc(0x300);g.put(0xdcbea4,holder);g.put(holder+0x20,fade);g.put(0xdc20e0,0);clear=lambda:g.call(g.exports['re0_probe_screen_clear'],thiscall=False)
 alpha=lambda v:g.uc.mem_write(fade+0x277,bytes([v]));out={}
 g.call(0x5aa410,fade,ONE);out['fade_out_just_started']=clear();alpha(40);out['fade_out_early']=clear();alpha(200);out['fade_out_late']=clear();alpha(255);out['black']=clear()
 g.call(0x5aa2c0,fade,ONE);out['fade_in_just_started']=clear();alpha(200);out['fade_in_early']=clear();alpha(40);out['fade_in_late']=clear();alpha(0);out['clear']=clear()
 # User 2026-11-06 (RE0.NoUIWait, fade 3x): the fade returned to clear while the closed map's last capture was young and the overlay drew it again. Per Present: open with a live map draws; the fade up (map closing) holds every capture so far back, whatever the fade does next; only a later map draw, with the map object still live (state 3 at +0x27c), draws again.
 mp=g.alloc(0x300);g.put(mp,0xcdc650);g.put(mp+0x27c,3);gate=lambda gen:g.call(g.exports['re0_probe_gate'],0,gen,mp,thiscall=False);alpha(0)
 out['gate_open']=gate(1);out['gate_present_outpaces_map']=gate(1);alpha(200);out['gate_closing']=gate(1);alpha(0);out['gate_fade_back_to_clear_stale']=gate(1);out['gate_new_map_draw']=gate(2)
 g.put(mp+0x27c,4);out['gate_map_not_live']=gate(3);g.put(mp+0x27c,3);out['gate_still_stale']=gate(3);out['gate_next_draw']=gate(4)
 before=g.call(g.exports['re0_probe_counter'],0,19,thiscall=False);g.put(0xdcbea4,0);out['no_owner']=clear();out['unreadable_counted']=g.call(g.exports['re0_probe_counter'],0,19,thiscall=False)-before
 return out
def marker_states():
 text=(ROOT/'src/runtime/labels_generated.h').read_text()
 return [[int(v) for v in m.split(',')] for m in __import__('re').findall(r'\{([0-9,]+)\}',text.split('marker_state[] = {',1)[1].split('};',1)[0])]
ACTOR_HP=0x1030;ACTOR_SLOT=0xff0;ACTOR_SCENE=0xff4;ACTOR_NEXT=0x14;ACTOR_STATE=0xc;CERBERUS=0xcc3fe8;CERBERUS_DTI=0xdce524;LIST_OWNER=0xe2d434
def enemy_gate(g):
 """Kill state through native code: the Cerberus class's save virtual through native 0x412c30, the spawn gate 0x410bb0, native save 0x4115d0 and restore 0x4103e0 into a fresh manager.
 Hand wired: table rows, list links, the DTI id set by 0x67d860 at startup. Stubbed: random, ground check, the emission calls the pickup makes."""
 STRIDE=0x5c;states=marker_states();mgr=g.alloc(0x30000);owner=g.alloc(0x400);scene=g.alloc(0x100);out={};mismatches=lambda:g.call(g.exports['re0_probe_counter'],0,21,thiscall=False);base=mismatches()
 g.put(0xdcc010,mgr);g.put(mgr+0x24fac,589);g.put(mgr+0x24ff0,1);g.put(LIST_OWNER,owner);g.put(0xdcc014,g.alloc(0x200));g.put(0xdcc0d0,g.alloc(0x2000));g.put(CERBERUS_DTI+0x1c,0x8000002a)
 for a,c in ((0x660070,0),(0x4c8e80,4),(0x51fed0,4)):g.stub(a,c)
 enemies=[i for i,s in enumerate(states) if s[7]==0x2a and s[1]!=0xffff]
 def mark(i):
  s=states[i];row=mgr+0x30+s[1]*STRIDE;g.put(row,s[6]);g.put(row+4,s[7]);g.put(row+8,0);return row,s[1]
 done=lambda i:g.call(g.exports['re0_probe_marker_done'],0,i,thiscall=False)
 def actor(slot,layer,vt=CERBERUS,hp=100):
  a=g.alloc(0x8000);g.put(a,vt);g.put(a+ACTOR_SLOT,slot);g.put(a+ACTOR_SCENE,scene);g.put(a+ACTOR_STATE,1);g.call(0x529310,a,hp&0xffffffff);g.put(a+ACTOR_NEXT,g.u32(owner+layer*0x18+0x2c));g.put(owner+layer*0x18+0x2c,a);return a
 live,dead=enemies[:2];live_row,live_slot=mark(live);dead_row,dead_slot=mark(dead);a_live=actor(live_slot,9);a_dead=actor(dead_slot,0xc)
 # An item actor at HP 0 on its own table row, in front of the dead enemy on its list: not a kill, and the walk has to follow the link past it.
 item=next(i for i,s in enumerate(states) if s[7]==0x71 and s[1]!=0xffff);item_row=mgr+0x30+states[item][1]*STRIDE;g.put(item_row,states[item][6]);g.put(item_row+4,0x71);g.put(item_row+8,states[item][5]);a_item=actor(states[item][1],0xc,hp=0)
 # 0x412c30 writes row+8 from the actor; the class leaves it as spawned, but nothing promises that, so give it another value through native setter 0x529110 to see the guard hold.
 g.call(0x529110,a_dead,7,0)
 out['alive_in_room']=done(dead);g.call(0x529310,a_dead,0);out['killed_in_room_row_unset']=g.uc.mem_read(dead_row+0x39,1)[0];out['killed_in_room']=done(dead);out['other_alive_in_room']=done(live)
 # The walk against native 0x51fd40 over the same list, one callback per actor, and the native filter 0x5201d0: a deleted actor is not visited and does not count.
 cb=g.alloc(0x40);code=g.alloc(0x10);g.put(cb,cb+8);g.put(cb+8,code);g.stub(code,4);g.seen_calls[code]=[];visited={}
 for layer in (9,0xc,0xd):g.seen_calls[code]=[];g.uc.mem_write(g.alloc(4),b'\0'*4);g.call(0x51fd40,0,cb,scene,layer,thiscall=False);visited[layer]=list(g.seen_calls[code])
 out['native_walk']=[len(visited[9]),len(visited[0xc]),len(visited[0xd])];out['native_walk_found_actors']=int(a_live in visited[9] and a_dead in visited[0xc])
 g.seen_calls.pop(code)
 g.put(a_dead+ACTOR_STATE,3);out['deleted_actor_counts']=done(dead);g.put(a_dead+ACTOR_STATE,1)
 out['item_actor_hp_zero']=done(item)
 # Native save of both on leaving: the room walk 0x61d510 calls 0x412c30 per actor.
 g.call(0x412c30,mgr,a_live);g.call(0x412c30,mgr,a_dead)
 out['saved_alive_gone_byte']=g.uc.mem_read(live_row+0x39,1)[0];out['saved_alive_mark_41']=g.uc.mem_read(live_row+0x41,1)[0];out['saved_alive']=done(live);out['spawn_alive_refused']=int(not g.reaches(0x410bb0,0x410c36,mgr,0,live_slot,0))
 out['saved_dead_gone_byte']=g.uc.mem_read(dead_row+0x39,1)[0];out['row8_rewritten']=g.u32(dead_row+8);out['spawn_dead_refused']=int(not g.reaches(0x410bb0,0x410c36,mgr,0,dead_slot,0))
 g.put(owner+9*0x18+0x2c,a_live);g.put(a_live+ACTOR_NEXT,0);g.put(owner+0xc*0x18+0x2c,0);g.put(a_dead+ACTOR_NEXT,0);g.put(owner+0xd*0x18+0x2c,0)
 out['after_leaving']=done(dead);done(dead);out['no_mismatch']=int(mismatches()==base)
 g.put(dead_row+4,0x71);out['other_kind_in_row']=done(dead);done(dead);out['other_kind_counted']=mismatches()-base;g.put(dead_row+4,0x2a);done(dead);done(dead);base=mismatches()
 # A second save and load, as the live failure of candidate 21: native save to a buffer, native restore into a fresh manager, whose mode field stays 0.
 g.stub(0x61b100,4);g.stub(0x51f460,4);g.put(g.u32(0xdcc0d0)+0xff0,states[item][1]);g.put(0xdcbf40,g.u32(0xdcc0d0));g.call(0x4de730,g.u32(0xdcc0d0),g.u32(0xdcc0d0))
 buffer=g.alloc(0x20000);g.call(0x4115d0,mgr,buffer);fresh=g.alloc(0x30000);g.call(0x4103e0,fresh,buffer);g.put(0xdcc010,fresh);out['restored_mode']=g.u32(fresh+0x24ff0);out['restored_count']=g.u32(fresh+0x24fac)
 g.put(owner+9*0x18+0x2c,0);g.put(a_live+ACTOR_NEXT,0)
 out['restored_dead']=done(dead);out['restored_alive']=done(live);out['restored_item']=done(item);done(item);out['restored_no_mismatch']=int(mismatches()==base)
 # A live kill on top of the restored state, for the emulator comparison that follows.
 g.put(owner+9*0x18+0x2c,a_live);g.call(0x529310,a_live,0);out['restored_live_kill']=done(live);g.put(LIST_OWNER,0);before=g.call(g.exports['re0_probe_counter'],0,22,thiscall=False);done(live);out['unreadable_counted']=g.call(g.exports['re0_probe_counter'],0,22,thiscall=False)-before;g.put(LIST_OWNER,owner)
 out['cerberus_rows']=len(enemies);return out
PIECE_STATE=0x5b4060;FLOOR_TABS=0x5bb930;MAP_TEST=0x59b8d0;SITE_PIECE=0x5b4afa;SITE_REGIONS=0x5b3c5b;SITE_TABS=0x5bb998
REGION_NAMES=('tr','sh','dm','ch','bt','pl')
# Pieces the native gate skips whatever their state (bl at 0x5b4818-0x5b4a05, 0x81 and 0xea decide), on the patterns of room_flag_patterns; the names as the map's instances write them, without their section.
GATED_ON_PATTERNS=['i_ch0c7','i_ch0c8','i_sh07a','i_sh07b'];GATED_WITH_NO_FLAGS=['i_ch0c8','i_sh07a']
def native_pieces(g,native):
 """A map object for the game's own piece-state function 0x5b4060. Hand wired: object layout it reads, GUI lookups by name. Stubbed: instance and sprite calls. Native: the function, its flag tests, its tables."""
 names={p['id'] for p in native['map_pieces']};by_ptr={};states={};doors_on=set();doors=g.alloc(0x1000);map_=g.alloc(0x1300);state=g.alloc(0x200);res=g.alloc(0x80);res2=g.alloc(0x80);lookup={};names_at={}
 g.put(map_+0xf0,res);g.put(res+0x68,res2);g.put(res2+0x44,0x400);g.put(map_+0xf8,doors);g.put(map_+0x278,state);g.put(map_+0x284,state);g.put(map_+0x294,0xffffffff);g.put(map_+0x290,0xffffffff)
 for i in range(0x400):g.put(doors+i*4,0x70000000+i)
 holder=g.alloc(0x40);g.putf(holder+0x2c,-1.0);g.put(0xdcbebc,holder);g.put(0xdcbf40,g.alloc(0x2000));vtable=g.alloc(0x100);paint=g.alloc(0x10);g.put(vtable+0x58,paint)
 def on_name(sp):
  buf,_,_,_,region,room,floor,section=struct.unpack('<8I',bytes(g.uc.mem_read(sp+4,32)));text=bytes(g.uc.mem_read(region,2)).decode();names_at[buf]=f'i_{text}{room:02x}{floor:x}{section}';return 0
 def on_lookup(sp):
  name=names_at.get(struct.unpack('<I',bytes(g.uc.mem_read(sp+4,4)))[0])
  if name not in names:return 0
  if name not in lookup:lookup[name]=g.alloc(8);g.put(lookup[name],vtable);by_ptr[lookup[name]]=name
  return lookup[name]
 def on_paint(sp):
  states[by_ptr[g.uc.reg_read(UC_X86_REG_ECX)]]=(struct.unpack('<I',bytes(g.uc.mem_read(sp+4,4)))[0]-0xd9de40)//4;return 0
 def on_door(sp):doors_on.add(g.uc.reg_read(UC_X86_REG_ECX)-0x70000000);return 0
 for address,clean,answer in ((0x526490,0,lambda sp:state),(0x5f0030,8,None),(0x875030,4,None),(0x401f50,0,None),(0xc460a4,0,on_name),(0x883920,4,on_lookup),(0x5ef240,8,lambda sp:struct.unpack('<I',bytes(g.uc.mem_read(sp+4,4)))[0]),(paint,4,on_paint),(0x880d30,4,on_door)):
  g.stub(address,clean)
  if answer:g.answers[address]=answer
 def run(region,floor):
  states.clear();doors_on.clear();g.put(state+0x44,region);g.call(PIECE_STATE,map_,floor);return dict(states),set(doors_on)
 return run,state
def flag_words(bits):
 words=[0]*33
 for b in bits:words[b>>5]|=1<<(b&31)
 return words
def room_flag_patterns():
 """A random array, an empty and a full one, and each map held alone, which is what tells room 0x19 of region 5 apart. Bits outside the rooms' range are random too: gates and section choice read them."""
 import random
 rng=random.Random(0x5b4afa);return [[0]*33,[0xffffffff]*33,[rng.getrandbits(32) for _ in range(33)],*[flag_words([0x2c8+region]) for region in range(6)]]
def scope_gate(g):
 """The game's piece state against the shared rule, then the All scope patch through the real call site, floor by floor, on the same arrays. Hand wired: see native_pieces. Not run: the sprite pass, the game's own map update."""
 native=json.loads((ROOT/'data/native-map.json').read_text());run,state=native_pieces(g,native);holder=g.alloc(0x200);g.put(0xdcc014,holder);rule=json.loads((ROOT/'data/room-state.json').read_text())['pieces']
 index={p['id']:i for i,p in enumerate(native['map_pieces'])};by_floor={}
 for p in native['map_pieces']:by_floor.setdefault((REGION_NAMES.index(p['region']),int(p['id'][6],16)),[]).append(p['id'])
 def load(words):
  g.uc.mem_write(holder+0x20,struct.pack('<33I',*words));g.call(g.exports['re0_probe_read_flags'],thiscall=False)
 shared=lambda i:g.call(g.exports['re0_probe_room_state'],0,i,thiscall=False)
 out=dict(compared=0,state_mismatch=[],gated=set(),drawn_with_no_state=[]);baseline={}
 for pattern,words in enumerate(room_flag_patterns()):
  load(words)
  for (region,floor),ids in by_floor.items():
   got,_=run(region,floor);baseline[(pattern,region,floor)]=got
   for piece in ids:
    want=shared(index[piece]);have=got.get(piece);twin=next((s for k,s in got.items() if k[:-1]==piece[:-1]),None);out['compared']+=1
    if twin is None and want:out['gated'].add(piece[:-1])
    if twin is not None and twin!=want:out['state_mismatch'].append((piece,twin,want))
    if have==0:out['drawn_with_no_state'].append(piece)
 out['gated']=sorted(out['gated'])
 # The patch: nothing changes outside All, and All draws what the map flag would. Floor tabs and the region count keep reading the flag themselves.
 tabs=lambda:bytes(g.uc.mem_read(state+0x74,12));target=lambda site:site+5+struct.unpack('<i',bytes(g.uc.mem_read(site+1,4)))[0]
 load([0]*33);g.put(state+0x44,0);g.call(FLOOR_TABS,state);out['tabs_empty_before']=int(not any(tabs()))
 out['installed']=g.call(g.exports['re0_probe_install_all_scope'],thiscall=False);out['site_moved']=int(target(SITE_PIECE)!=MAP_TEST)
 out['tabs_site_native']=int(target(SITE_TABS)==MAP_TEST);out['regions_site_native']=int(target(SITE_REGIONS)==MAP_TEST)
 setscope=lambda v:g.call(g.exports['re0_probe_set_scope'],0,v,thiscall=False);out['changed_in_visited']=0
 for pattern,words in enumerate(room_flag_patterns()):
  load(words)
  for v in (0,1):
   setscope(v)
   for key in by_floor:
    got,_=run(*key)
    if got!=baseline[(pattern,*key)]:out['changed_in_visited']+=1
 load([0]*33);setscope(2);out['all_state']={};out['all_undrawn']=[];all_doors=set()
 for (region,floor),ids in by_floor.items():
  got,doors=run(region,floor);all_doors|=doors
  for s in got.values():out['all_state'][s]=out['all_state'].get(s,0)+1
  out['all_undrawn']+=[p[:-1] for p in ids if not any(k[:-1]==p[:-1] for k in got)]
 out['all_undrawn']=sorted(set(out['all_undrawn']));out['all_doors_on']=int(bool(all_doors))
 g.put(state+0x44,0);g.call(FLOOR_TABS,state);out['tabs_all_empty']=int(not any(tabs()))
 # A visited room stays green under All: colour 3 against 1, both green in 0xd9de40.
 piece=native['map_pieces'][0]['id'];load(flag_words(rule[piece]['visited']));got,_=run(*next(k for k,v in by_floor.items() if piece in v));out['all_visited_state']=got.get(piece);setscope(0);return out
def lock_gate(g):
 """Generated marks of locks on doors: each at its door's painted centre, the door's GUI Flag is the mark's done flag, and its rooms are the ones native 0x5bb420 joins to the door."""
 native=json.loads((ROOT/'data/native-map.json').read_text());places=json.loads((ROOT/'data/placements.json').read_text())['rows']
 sys.path.insert(0,str(ROOT/'tools'));from build_labels import marker_defs
 defs=marker_defs(dict(rows=places),native);doors={d['id']:d for d in native['door_instances']};by_gui={(d['region'],d['instance_index']):d['id'] for d in native['door_instances']}
 out=dict(on_door=0,moved=[],wrong_flag=[],wrong_rooms=[]);pieces=native['map_pieces'];room_list=g.call(g.exports['re0_probe_marker_rooms'],thiscall=False)
 for i,d in enumerate(defs):
  r=places[d['row']]
  if r['category']!='lock' or r['piece'] not in doors:continue
  # From the compiled tables: 24 bytes of RE0MarkerDef, 16 of RE0MarkerState.
  raw=bytes(g.uc.mem_read(g.call(g.exports['re0_probe_marker_def'],0,i,thiscall=False),24));x,y=struct.unpack_from('<2f',raw);first=struct.unpack_from('<H',raw,18)[0];count=raw[20];flag=struct.unpack('<H',bytes(g.uc.mem_read(g.call(g.exports['re0_probe_marker_state'],0,i,thiscall=False)+6,2)))[0]
  door=doors[r['piece']];out['on_door']+=1
  if abs(x-r['x'])>.05 or abs(y-r['y'])>.05:out['moved'].append(r['name_en'])
  if door['properties']['Flag']!=flag:out['wrong_flag'].append(r['name_en'])
  have={pieces[v]['id'] for v in struct.unpack(f'<{count}H',bytes(g.uc.mem_read(room_list+first*2,count*2)))};region=REGION_NAMES.index(door['region']);joined=set()
  for p in pieces:
   if p['region']!=door['region'] or p['floor']!=door['floor']:continue
   local=int(p['id'][4:6],16);floor=int(p['id'][6],16);at=g.call(0x5bb420,0,region,floor,local);n=0
   while at:
    v=struct.unpack('<H',bytes(g.uc.mem_read(at+n*2,2)))[0]
    if v==0xffff:break
    if by_gui.get((door['region'],v))==door['id']:joined.add(p['id'])
    n+=1
  if joined!=have:out['wrong_rooms'].append((r['name_en'],sorted(joined),sorted(have)))
 return out
def overlay_ops_of(g,scope,width=1920,height=1080):
 g.call(g.exports['re0_probe_set_scope'],0,scope,thiscall=False);n=g.call(g.exports['re0_probe_overlay'],0,width,height,thiscall=False,limit=60000000);at=g.call(g.exports['re0_probe_ops'],thiscall=False);data=bytes(g.uc.mem_read(at,n*24));return [struct.unpack_from('<4fIi',data,i*24) for i in range(n)]
def overlay_gate(g):
 """The ASI's overlay against the live reports, and against the emulator, on flag arrays from the native rule: one piece of a room drawn, a door between two rooms, each scope. Boxes are static, as the page's are."""
 sys.path.insert(0,str(ROOT/'emulator'));from core import Core
 re_=__import__('re');native=json.loads((ROOT/'data/native-map.json').read_text());rule=json.loads((ROOT/'data/room-state.json').read_text())['pieces'];places=json.loads((ROOT/'data/placements.json').read_text())['rows']
 sys.path.insert(0,str(ROOT/'tools'));from build_labels import marker_defs
 text=(ROOT/'src/runtime/labels_generated.h').read_text();canvas=[[float(v.rstrip('f')) for v in m.split(',')] for m in re_.findall(r'\{([0-9.,f]+)\}',text.split('piece_canvas[] = {',1)[1].split('};',1)[0])]
 markers=[m.split(',') for m in re_.findall(r'\{([0-9.,f]+)\}',text.split('markers[] = {',1)[1].split('};',1)[0])];layout=[m.split(',') for m in re_.findall(r'\{([0-9.,f]+)\}',text.split('room_layout[] = {',1)[1].split('};',1)[0])]
 index={p['id']:i for i,p in enumerate(native['map_pieces'])};defs=marker_defs(dict(rows=places),native);holder=g.alloc(0x200);g.put(0xdcc014,holder);g.put(0xdcc010,0);g.call(g.exports['re0_probe_read_arrange'],thiscall=False);scratch=g.alloc(16);core=Core()
 def scene(ids,words):
  g.call(g.exports['re0_probe_rooms_clear'],thiscall=False);rooms={}
  for p in ids:
   b=[v*1.5 for v in canvas[index[p]]];rooms[index[p]]=b;g.uc.mem_write(scratch,struct.pack('<4f',*b));g.call(g.exports['re0_probe_room_box'],0,index[p],scratch,thiscall=False)
  g.uc.mem_write(holder+0x20,struct.pack('<33I',*words));g.call(g.exports['re0_probe_read_flags'],thiscall=False);return rooms
 name_of=lambda d:int(markers[defs.index(d)][3]);def_of=lambda cat,row_name,room:next(d for d in defs if places[d['row']]['category']==cat and places[d['row']]['name_en']==row_name and places[d['row']]['room']==room);layout_of=lambda piece:int(next(r for r in layout if int(r[0])==index[piece] and int(r[3])==0)[2])
 shows=lambda ops,glyph:int(any(o[5]==glyph for o in ops));every=[0xffffffff]*33;out={};worst=0.0;same=True
 def compare(rooms,scope,words):
  nonlocal worst,same
  ops=overlay_ops_of(g,scope);s=core.default_settings();s.scope=scope;emu,_=core.frame(s,1920,1080,rooms,(),(1.5,0,0),flags=words);same=same and len(ops)==len(emu)
  if len(ops)==len(emu):
   for a,b in zip(ops,emu):
    same=same and a[4]==b['color'] and a[5]==b['glyph'];worst=max([worst,*[abs(x-y) for x,y in zip(a[:4],b['box'])]])
  return ops
 # Live report 2: Ice Pick on piece i_tr0ca0, the game drawing i_tr0ca1 (and a neighbour the view needs nothing from).
 ice=def_of('key','Ice Pick',12);words=flag_words(rule['i_tr0ca1']['visited']);rooms=scene(['i_tr0ca1'],words);ops=compare(rooms,0,words)
 out['second_piece_mark']=shows(ops,name_of(ice));out['second_piece_name']=shows(ops,layout_of('i_tr0ca0'))
 # A lock on a door: seen from the room it does not sit in. Conductor's Key: door between Cabin rooms tr02 and tr03.
 door=def_of('lock',"Conductor's Key",2);other=[p for p in ('i_tr0290','i_tr0390') if index[p]!=door['piece']][0];words=flag_words(rule[other]['visited']);rooms=scene([other],words);ops=compare(rooms,0,words);out['door_from_other_room']=shows(ops,name_of(door))
 # Visited, revealed, all: i_tr0090 visited with no map; i_tr0190 drawn by the map only; i_tr1?: every other room of the floor undrawn.
 v,r=rule['i_tr0090'],rule['i_tr0190'];both=['i_tr0090','i_tr0190'];visited_only=flag_words(v['visited']);with_map=flag_words(v['visited']+v['revealed']);rooms=scene(both,visited_only);ops=compare(rooms,0,visited_only)
 out['visited_scope_visited_room']=shows(ops,layout_of('i_tr0090'));out['visited_scope_map_room']=shows(ops,layout_of('i_tr0190'))
 rooms=scene(both,with_map);ops=compare(rooms,0,with_map);out['visited_scope_with_map']=shows(ops,layout_of('i_tr0190'));ops=compare(rooms,1,with_map);out['revealed_scope_map_room']=shows(ops,layout_of('i_tr0190'))
 rooms=scene(both,visited_only);ops=compare(rooms,1,visited_only);out['revealed_scope_without_map']=shows(ops,layout_of('i_tr0190'));ops=compare(rooms,2,visited_only);out['all_scope_map_room']=shows(ops,layout_of('i_tr0190'))
 undrawn=next(p['id'] for p in native['map_pieces'] if p['region']=='tr' and p['floor']=='1f' and p['id'] not in both and any(int(r[0])==index[p['id']] for r in layout));out['all_scope_undrawn_room']=shows(ops,layout_of(undrawn));out['undrawn_room_in_visited']=shows(compare(rooms,0,visited_only),layout_of(undrawn))
 g.call(g.exports['re0_probe_set_scope'],0,0,thiscall=False);out['same_as_emulator']=int(same);out['worst_px']=worst;return out
def ini_gate(g):
 """Scope from the INI as RE1 HD reads it; difficulty while the table is unknown is the INI's, no key."""
 out={}
 for name,value in (('visited',0),('revealed',1),('all',2),('too_big',7)):
  INI.clear();INI['Visibility']=value;out[name]=g.call(g.exports['re0_probe_settings_load'],thiscall=False)
 INI.clear();out['absent']=g.call(g.exports['re0_probe_settings_load'],thiscall=False)
 # Candidate 50: ItemNames 0 off, 1 all, 2 no common from Version 50; an older file's on/off (any non-zero is on) becomes 1/0 once.
 for name,keys in (('item_names_absent',{}),('item_names_old_on',{'ItemNames':1}),('item_names_old_two',{'Version':44,'ItemNames':2}),('item_names_old_off',{'ItemNames':0}),('item_names_new_all',{'Version':50,'ItemNames':1}),('item_names_new_no_common',{'Version':50,'ItemNames':2}),('item_names_new_off',{'Version':50,'ItemNames':0}),('item_names_new_bad',{'Version':50,'ItemNames':3})):
  INI.clear();INI.update(keys);out[name]=g.call(g.exports['re0_probe_item_names'],thiscall=False)
 # Candidate 51: Contents gains the event bit (bit 6) from the puzzle bit in older files; [Colors] sets the category colours, a bad value keeps the shipped one.
 for name,keys in (('contents_absent',{}),('contents_old_puzzle_on',{'Contents':63}),('contents_old_puzzle_off',{'Contents':55}),('contents_v51_events_on',{'Version':51,'Contents':127}),('contents_new_absent',{'Version':52}),('contents_new_keeps',{'Version':52,'Contents':55}),('contents_new_events_on',{'Version':52,'Contents':127}),('contents_new_event_only',{'Version':52,'Contents':64})):
  INI.clear();INI.update(keys);out[name]=g.call(g.exports['re0_probe_contents'],thiscall=False)
 INI.clear();out['color_defaults']=[g.call(g.exports['re0_probe_color'],0,c,thiscall=False) for c in range(7)]
 INI.clear();INI.update({'Lock':'#112233','KeyItem':'445566','File':'bogus','Puzzle':'#1234567','Event':'#00FF00','Item':'#6a6a6a ; grey','Enemy':'#ABCDEF'})
 out['color_from_ini']=[g.call(g.exports['re0_probe_color'],0,c,thiscall=False) for c in range(7)]
 INI.clear();INI['Difficulty']=2;g.call(g.exports['re0_probe_settings_load'],thiscall=False);g.put(0xdcc010,0);out['difficulty_no_table']=g.call(g.exports['re0_probe_difficulty'],thiscall=False)
 mgr=g.alloc(0x30000);g.put(0xdcc010,mgr);g.put(mgr+0x24fac,300);out['difficulty_unknown_table']=g.call(g.exports['re0_probe_difficulty'],thiscall=False);g.put(mgr+0x24fac,647);out['difficulty_read']=g.call(g.exports['re0_probe_difficulty'],thiscall=False)
 g.put(mgr+0x24fac,300);out['difficulty_table_gone']=g.call(g.exports['re0_probe_difficulty'],thiscall=False);g.put(0xdcc010,0);INI.clear();g.call(g.exports['re0_probe_settings_load'],thiscall=False);return out
def arrange_gate(g):
 """Native pickup 0x4de730 on a table row, then the ASI's read and the shared rule. Row contents are placed by hand, as the room loader 0x412110 is not run."""
 STRIDE=0x5c;mgr=g.alloc(0x30000);actor=g.alloc(0x2000);g.put(0xdcc010,mgr);g.put(0xdcbf40,actor);g.put(0xdcc0d0,actor);g.stub(0x61b100,4);g.stub(0x51f460,4)
 states=marker_states();index=next(i for i,s in enumerate(states) if s[1]!=0xffff and s[1]>0 and s[7]==0x71);s=states[index];slot=s[1];row=mgr+0x30+slot*STRIDE
 g.put(mgr+0x24fac,589);g.put(mgr+0x24ff0,1);g.put(row,s[6]);g.put(row+4,0x71);g.put(row+8,s[5]);done=lambda:g.call(g.exports['re0_probe_marker_done'],0,index,thiscall=False);out={}
 out['before']=done();g.put(actor+0xff0,slot);g.call(0x4de730,actor,actor);out['kind_after_pickup']=g.u32(row+4);out['after_pickup']=done()
 # Live failure, candidate 21: after a save load the mode field stays 0, as restore 0x4103e0 does not write it. The taken row must still count.
 g.put(mgr+0x24ff0,0);out['loaded_save_mode_zero']=done();g.put(mgr+0x24ff0,1)
 g.put(row+4,0x71);g.put(mgr+0x24fac,600);out['wrong_count']=done();g.put(mgr+0x24fac,589)
 g.put(row+8,s[5]+1);g.put(row+4,0);out['other_item']=done();g.put(row+8,s[5]);g.put(mgr+0x2c+slot*STRIDE,0xffffffff);g.put(row+4,0x71);out['unlinked']=done()
 difficulty=lambda:g.call(g.exports['re0_probe_difficulty'],thiscall=False)
 g.put(0xdcc010,mgr);g.put(mgr+0x24fac,568);g.put(mgr+0x24ff0,0);out['hard_table']=difficulty();g.put(mgr+0x24fac,647);out['easy_table']=difficulty()
 g.put(mgr+0x24fac,300);out['other_table_keeps']=difficulty() # the INI's value, 1 here
 g.put(0xdcc010,0);out['no_manager']=done();return out
def emulator_gate(g):
 """The game's overlay call under x86 against the native build the review page's parity test uses: same floor, same flags, same ops. Boxes are static, as the page's are."""
 sys.path.insert(0,str(ROOT/'emulator'));from core import Core
 text=(ROOT/'src/runtime/labels_generated.h').read_text();canvas=[[float(v.rstrip('f')) for v in m.split(',')] for m in __import__('re').findall(r'\{([0-9.,f]+)\}',text.split('piece_canvas[] = {',1)[1].split('};',1)[0])]
 raw=[[int(v) for v in m.split(',')] for m in __import__('re').findall(r'\{([0-9,]+)\}',text.split('rooms[] = {',1)[1].split('};',1)[0])]
 floor=(raw[0][0],raw[0][2]);rooms={i:[v*1.5 for v in canvas[i]] for i,r in enumerate(raw) if (r[0],r[2])==floor and canvas[i][2]>canvas[i][0]}
 scratch=g.alloc(16)
 for i,b in rooms.items():g.uc.mem_write(scratch,struct.pack('<4f',*b));g.call(g.exports['re0_probe_room_box'],0,i,scratch,thiscall=False)
 flags=[0xffffffff]*33;holder=g.alloc(0x200);g.put(0xdcc014,holder);g.uc.mem_write(holder+0x20,struct.pack('<33I',*flags));g.call(g.exports['re0_probe_read_flags'],thiscall=False)
 restored=g.u32(0xdcc010);g.put(0xdcc010,0);g.call(g.exports['re0_probe_read_arrange'],thiscall=False) # no table first
 n=g.call(g.exports['re0_probe_overlay'],0,1920,1080,thiscall=False,limit=60000000);at=g.call(g.exports['re0_probe_ops'],thiscall=False)
 data=bytes(g.uc.mem_read(at,n*24));game=[struct.unpack_from('<4fIi',data,i*24) for i in range(n)]
 core=Core();s=core.default_settings();emulator,_=core.frame(s,1920,1080,rooms,(),(1.5,0,0),flags=flags)
 worst=0 if len(game)==len(emulator) else 1e9;same=len(game)==len(emulator)
 if same:
  for a,b in zip(game,emulator):
   same=same and a[4]==b['color'] and a[5]==b['glyph'];worst=max([worst,*[abs(x-y) for x,y in zip(a[:4],b['box'])]])
 first_icon=int(text.split('#define ICON_FIRST_GLYPH ',1)[1].split()[0]);marks=sum(1 for a in game if a[5]>=first_icon)
 # Again with the restored save and a live kill left by enemy_gate: the ASI reads the list, the emulator gets the same rows and slot bits. Row bytes are the game's.
 import ctypes;from core import ArrangeView
 def compare(arrange):
  n=g.call(g.exports['re0_probe_overlay'],0,1920,1080,thiscall=False,limit=60000000);at=g.call(g.exports['re0_probe_ops'],thiscall=False);data=bytes(g.uc.mem_read(at,n*24));ops=[struct.unpack_from('<4fIi',data,i*24) for i in range(n)]
  emu,_=core.frame(core.default_settings(),1920,1080,rooms,(),(1.5,0,0),flags=flags,arrange=arrange)
  good=len(ops)==len(emu) and all(a[4]==b['color'] and a[5]==b['glyph'] and all(abs(x-y)<=.01 for x,y in zip(a[:4],b['box'])) for a,b in zip(ops,emu))
  return good,sum(1 for a in ops if a[5]>=first_icon)
 g.put(0xdcc010,restored);g.call(g.exports['re0_probe_read_arrange'],thiscall=False);mgr=restored;count=g.u32(mgr+0x24fac);bits=g.call(g.exports['re0_probe_killed'],thiscall=False)
 raw=ctypes.create_string_buffer(bytes(g.uc.mem_read(mgr,0x30+0x4e8*0x5c)));killed=(ctypes.c_uint*40)(*struct.unpack('<40I',bytes(g.uc.mem_read(bits,160)))) if bits else None
 same_state,marks_state=compare(ArrangeView(count,ctypes.cast(raw,ctypes.c_char_p),0,killed))
 return dict(game_ops=len(game),emulator_ops=len(emulator),same_ops=same,worst_px=worst,marks=marks,same_ops_restored=same_state,marks_restored=marks_state)
def aspect_gate(g,slot,map_,args,renderer,region,gui_id,fresh,obj):
 """21:9 display, Aspect 16:9. The rect comes from native code: sRender centring 0x72376a and the viewport setter 0x866ac0. Sprite centre is (300,200) in GUI space."""
 uc=g.uc;render=0x50000000;uc.mem_map(render,0x434000);g.put(0xe2d40c,render)
 def box(view,target,back,size):
  uc.mem_write(render+0x433e50,struct.pack('<2I',*back));uc.mem_write(render+0xb8,struct.pack('<2I',*size))
  uc.reg_write(UC_X86_REG_EBP,render);uc.reg_write(UC_X86_REG_ESP,0x201f0000-0x400);uc.mem_write(0x201f0000-0x400,bytes(0x60))
  uc.mem_write(HEAP,fresh)
  saved=g.stubs;g.stubs={}
  uc.emu_start(0x72376a,0x7237b0,count=64);g.stubs=saved
  rect=g.alloc(16);uc.mem_write(rect,struct.pack('<4I',*view));uc.mem_write(renderer+0xfc,struct.pack('<2H',0,0))
  uc.reg_write(UC_X86_REG_ESP,0x201f0000-0x100);g.call(0x866ac0,renderer,rect)
  uc.mem_write(renderer+0xfc,struct.pack('<2H',*target))
  uc.reg_write(UC_X86_REG_ESP,0x201f0000-0x100);g.call(slot,map_,args)
  index=g.call(g.exports['re0_probe_room_index'],0,region,gui_id,thiscall=False);uc.reg_write(UC_X86_REG_ESP,0x201f0000-0x100)
  at=g.call(g.exports['re0_probe_room'],0,index,thiscall=False);b=struct.unpack('<4f',bytes(uc.mem_read(at,16)))
  return [(b[0]+b[2])/2,(b[1]+b[3])/2]
 out=dict(rt_pillarbox=box((0,0,2560,1440),(2560,1440),(3440,1440),(2560,1440)),
          direct_viewport=box((440,0,3000,1440),(3440,1440),(3440,1440),(2560,1440)),
          letterbox=box((0,0,1920,1080),(1920,1080),(1920,1200),(1920,1080)),
          same_16_9=box((0,0,1920,1080),(1920,1080),(1920,1080),(1920,1080)))
 # Resource evidence is independent of the handwritten wiring below.
 from resources import Gui
 grad=Gui((ROOT/'local/research/map_bg01.gui').read_bytes())
 assert [(r['properties'].get('PosX'),r['properties'].get('Size')) for r in grad.objects[1:]]==[(0.0,[224.0,720.0,0.0,0.0]),(1056.0,[224.0,720.0,0.0,0.0])]
 menu_gui=Gui((ROOT/'local/research/option_ds.gui').read_bytes())
 assert [(r['raw'][0],r['name']) for r in menu_gui.instances if r['raw'][0] in (7,19)]==[(7,'i_menu_00_ds'),(19,'i_menu_01_ds')]
 # Execute the real display-menu commit (0 Wide, 1 Original), not config/window heuristics.
 option=g.alloc(0xb0);scr=g.alloc(0x300);menu=g.alloc(0x2a0);g.put(0xdcc06c,option);g.put(0xdcf344,scr)
 bounds=lambda:struct.unpack('<4f',bytes(uc.mem_read(g.call(g.exports['re0_probe_display_bounds'],0,1920,1080,thiscall=False,limit=60000000),16)))
 display=[]
 for mode in (0,1):
  g.put(menu+0x268,mode);g.call(0x5c0d40,menu)
  if g.call(g.exports['re0_probe_display_mode'],thiscall=False)!=mode:raise AssertionError('native display selection not read')
  box((0,0,1920,1080),(1920,1080),(1920,1080),(1920,1080));display.append(list(bounds()))
 out['display_bounds']=display
 g.put(menu+0x268,0);g.call(0x5c0d40,menu) # Wide: the gradient's opaque cut, not Original's own box, bounds the map
 # Resource map_bg01.gui: left ControlPoint 0 at x=0, right edge's native quad at x=1056, both Size 224x720.
 for x in (0,1056):
  uc.mem_write(HEAP,fresh);g.putf(obj+0xc0,224,720);g.call(0x893890,obj,0)
  g.putf(obj+0x10,1.5,0,0,0,0,1.5,0,0,0,0,1,0,x*1.5,0,0,1);g.call(slot,map_,args)
 out['gradient_bounds']=list(bounds())
 g.call(g.exports['re0_probe_frames'],0,3,thiscall=False);g.put(0xdcc06c,0);g.put(0xdcf344,0)
 # Back to the plain state the rest of the run built.
 uc.mem_write(renderer+0xbc,struct.pack('<4I',0,0,1920,1080));uc.mem_write(renderer+0xfc,struct.pack('<2H',0,0));g.put(0xe2d40c,0);uc.reg_write(UC_X86_REG_EBP,0)
 uc.mem_write(HEAP,fresh);g.call(slot,map_,args)
 return out
def run(image,dll):
 """Returns observed native facts and the capture; raises when the chain breaks."""
 g=Game(image,dll);uc=g.uc
 # Scratch for the globals constructors and the viewport prefix read; the values are irrelevant to room capture.
 scratch=g.alloc(0x1000);g.put(0xe2daa4,scratch)
 g.call(g.exports['re0_probe_install'],thiscall=False)
 # Native constructors for the two classes the map uses.
 obj=g.alloc(0x120);g.call(0x887fa0,obj)
 g.call(0x893890,obj,5) # native ControlPoint setter with the resource value
 inst=g.alloc(0x100);g.call(0x8753b0,inst)
 facts=dict(sprite_a0=g.u32(obj+0xa0),sprite_vtable=g.u32(obj),instance_vtable=g.u32(inst))
 if facts['sprite_a0']!=LIVE['sprite_a0'] or facts['instance_vtable']!=LIVE['instance_vtable']:raise AssertionError(f'native constructors disagree with live values: {facts}')
 # Emission and per-node preparation are GPU/command-buffer work outside what is captured.
 for address,clean in [(0x890ae0,4),(0x888bb0,4),(0x875920,4),(0x891ce0,4),(0x87d160,4)]:g.stub(address,clean)
 # Wiring only: map -> root -> instance -> animation -> sprite.
 region=0;gui_id=3
 args,info,meta,out=[g.alloc(0x300) for _ in range(4)];renderer=g.alloc(0x2000);g.put(renderer+0xcfc,scratch)
 root=g.alloc(0x100);anim=g.alloc(0x100);objects=g.alloc(0x20);map_=g.alloc(0x1300);state=g.alloc(0x100);res=g.alloc(0x100)
 g.put(map_,0xcdc650);g.put(map_+0x27c,3);g.put(map_+0x278,state);g.put(state+0x44,region)
 g.put(map_+0xf0,res);g.put(map_+0xf4,root);g.put(map_+0x148,1);g.putf(map_+0x40,0,0);g.putf(map_+0x60,1,1)
 g.put(res+0x70,2);g.put(res+0x78,1280);g.put(res+0x7c,720)
 g.put(args+4,renderer);g.put(args+0xc,2);uc.mem_write(renderer+0xbc,struct.pack('<4I',0,0,1920,1080))
 g.put(renderer+8,info);g.put(info+0xb14,meta);uc.mem_write(meta+0x18,struct.pack('<H',4));uc.mem_write(renderer+0x14,struct.pack('<2I',out,out+256))
 g.put(root+0x60,inst);g.put(inst+0x6c,map_);g.put(inst+4,gui_id);g.put(inst+0xec,anim);g.put(inst+0x60,0);g.put(inst+0x64,0)
 g.put(inst+0x54,g.u32(inst+0x54)|0x100000)
 g.put(anim+0x80,objects);uc.mem_write(objects,struct.pack('<4I',0,obj,2,0))
 # Size and final matrix are what native preparation would leave; the sample live size was 172x48.
 g.putf(obj+0xc0,172,48);g.put(obj+0xe4,0x1234);g.putf(obj+0x10,1,0,0,0,0,1,0,0,0,0,1,0,300,200,0,1);g.put(obj+0xb0,0xffffffff)
 # The real vtable slot, as the game's unit loop would use it.
 slot=g.u32(0xcdc650+0x58)
 fresh=bytes(uc.mem_read(HEAP,g.heap-HEAP)) # the first draw consumes per-frame visibility; the aspect gate redraws from here
 g.call(slot,map_,args)
 index=g.call(g.exports['re0_probe_room_index'],0,region,gui_id,thiscall=False)
 uc.reg_write(UC_X86_REG_ESP,0x201f0000-0x100)
 at=g.call(g.exports['re0_probe_room'],0,index,thiscall=False)
 result_frame=frame_gate(g,slot,map_,args,obj,fresh)
 result_aspect=aspect_gate(g,slot,map_,args,renderer,region,gui_id,fresh,obj)
 uc.reg_write(UC_X86_REG_ESP,0x201f0000-0x100)
 result_arrange=arrange_gate(g);result_enemy=enemy_gate(g);result_emulator=emulator_gate(g);result_flags=flag_gate(g);result_fade=fade_gate(g)
 result_lock=lock_gate(g);result_overlay=overlay_gate(g);result_ini=ini_gate(g);result_scope=scope_gate(g)
 names=['maps','closed','empty','instances','no_context','owner_miss','id_miss','id_hit','sprites','sprite_no_context','unreadable','no_texture','alt_mode','transparent','bad_quad','sprite_room','sprite_other']
 counters={n:g.call(g.exports['re0_probe_counter'],0,i,thiscall=False) for i,n in enumerate(names)}
 box=struct.unpack('<4f',bytes(uc.mem_read(at,16))) if at else None
 return dict(drop_gate=drop_gate(g,json.loads((ROOT/'data/native-map.json').read_text())),rows_gate=rows_gate(g),frame_gate=result_frame,icon_gate=icon_gate(g),aspect_gate=result_aspect,lock_gate=result_lock,overlay_gate=result_overlay,ini_gate=result_ini,scope_gate=result_scope,arrange_gate=result_arrange,enemy_gate=result_enemy,emulator_gate=result_emulator,fade_gate=result_fade,flag_gate=result_flags,facts=facts,counters=counters,box=box,view=struct.unpack('<4f',bytes(uc.mem_read(args+0xb8,16))))
def verdict(result):
 """The capture the overlay depends on: a finite room box at the viewport-scaled sprite centre."""
 if result['arrange_gate']!=dict(before=0,kind_after_pickup=0,after_pickup=1,loaded_save_mode_zero=1,wrong_count=0,other_item=0,unlinked=1,hard_table=2,easy_table=0,other_table_keeps=1,no_manager=0):raise AssertionError(f"arrange gate wrong: {result['arrange_gate']}")
 want_enemy=dict(alive_in_room=0,killed_in_room_row_unset=0,killed_in_room=1,other_alive_in_room=0,native_walk_found_actors=1,deleted_actor_counts=0,item_actor_hp_zero=0,saved_alive_gone_byte=0,saved_alive_mark_41=1,saved_alive=0,spawn_alive_refused=0,saved_dead_gone_byte=1,row8_rewritten=7,spawn_dead_refused=1,after_leaving=1,no_mismatch=1,other_kind_in_row=0,other_kind_counted=1,restored_mode=0,restored_count=589,restored_dead=1,restored_alive=0,restored_item=1,restored_no_mismatch=1,restored_live_kill=1,unreadable_counted=1)
 got={k:result['enemy_gate'].get(k) for k in want_enemy}
 if got!=want_enemy:raise AssertionError(f'enemy gate wrong: {[(k,got[k],want_enemy[k]) for k in want_enemy if got[k]!=want_enemy[k]]}')
 lock=result['lock_gate']
 if lock!=dict(on_door=20,moved=[],wrong_flag=[],wrong_rooms=[]):raise AssertionError(f'lock on the wrong door: {lock}')
 want_overlay=dict(second_piece_mark=1,second_piece_name=1,door_from_other_room=1,visited_scope_visited_room=1,visited_scope_map_room=0,visited_scope_with_map=0,revealed_scope_map_room=1,revealed_scope_without_map=0,all_scope_map_room=1,all_scope_undrawn_room=1,undrawn_room_in_visited=0,same_as_emulator=1)
 got={k:result['overlay_gate'].get(k) for k in want_overlay}
 if got!=want_overlay or result['overlay_gate']['worst_px']>.01:raise AssertionError(f"overlay gate wrong: {result['overlay_gate']}")
 if result['ini_gate']!=dict(visited=0,revealed=1,all=2,too_big=0,absent=0,item_names_absent=0,item_names_old_on=1,item_names_old_two=1,item_names_old_off=0,item_names_new_all=1,item_names_new_no_common=2,item_names_new_off=0,item_names_new_bad=0,contents_absent=63,contents_old_puzzle_on=63,contents_old_puzzle_off=55,contents_v51_events_on=63,contents_new_absent=63,contents_new_keeps=55,contents_new_events_on=127,contents_new_event_only=64,color_defaults=[0xffcd46,0x5adcff,0xff8cd2,0xff9628,0xb8bcc4,0xeb3c3c,0xb070ff],color_from_ini=[0x112233,0x445566,0xff8cd2,0xff9628,0x6a6a6a,0xabcdef,0x00ff00],difficulty_no_table=2,difficulty_unknown_table=2,difficulty_read=0,difficulty_table_gone=2):raise AssertionError(f"INI gate wrong: {result['ini_gate']}")
 want_scope=dict(state_mismatch=[],gated=GATED_ON_PATTERNS,drawn_with_no_state=[],tabs_empty_before=1,installed=1,site_moved=1,tabs_site_native=1,regions_site_native=1,changed_in_visited=0,all_state={2:123},all_undrawn=GATED_WITH_NO_FLAGS,all_doors_on=1,tabs_all_empty=1,all_visited_state=3)
 got={k:result['scope_gate'].get(k) for k in want_scope}
 if got!=want_scope or not result['scope_gate']['compared']:raise AssertionError(f'scope gate wrong: {[(k,got[k],want_scope[k]) for k in want_scope if got[k]!=want_scope[k]]}')
 if result['aspect_gate']['display_bounds']!=[[0,0,1920,1080],[240,0,1680,1080]]:raise AssertionError(result['aspect_gate'])
 if any(abs(a-b)>.01 for a,b in zip(result['aspect_gate']['gradient_bounds'],[336*79/224,0,1920-336*79/224,1080])):raise AssertionError(result['aspect_gate'])
 want_aspect=dict(rt_pillarbox=[740,200],direct_viewport=[740,200],letterbox=[300,260],same_16_9=[300,200])
 if any(abs(a-b)>.01 for k,w in want_aspect.items() for a,b in zip(result['aspect_gate'][k],w)):raise AssertionError(f"aspect gate wrong: {result['aspect_gate']}")
 e=result['emulator_gate']
 if not e['same_ops'] or e['worst_px']>.01 or not e['marks']:raise AssertionError(f'game and emulator differ: {e}')
 if not e['same_ops_restored'] or e['marks_restored']>=e['marks']:raise AssertionError(f'game and emulator differ on a restored save: {e}')
 if result['fade_gate']!=dict(fade_out_just_started=1,fade_out_early=1,fade_out_late=0,black=0,fade_in_just_started=0,fade_in_early=0,fade_in_late=1,clear=1,gate_open=1,gate_present_outpaces_map=1,gate_closing=0,gate_fade_back_to_clear_stale=0,gate_new_map_draw=1,gate_map_not_live=0,gate_still_stale=0,gate_next_draw=1,no_owner=1,unreadable_counted=1):raise AssertionError(f"fade gate wrong: {result['fade_gate']}")
 # Per draw, two bits: icon texture bound, mip filter linear. Text, icon, text, icon. Failed: atlas and no mips throughout, two plain squares counted.
 if result['icon_gate']!=dict(upload=1,create_fails=0,level1_fails=0,loaded=0b11001100,failed=2<<8):raise AssertionError(f"icon gate wrong: {result['icon_gate']}")
 if result['frame_gate']!=dict(before=0,seen=1,right=1920,list_open=2,list_closed=1,after_v=0):raise AssertionError(f"frame gate wrong: {result['frame_gate']}")
 if result['rows_gate']!=dict(no_manager=0,count_over=0,wrote=False,count=0x4e0,slots=list(range(0x4e0,0x4e8)),bytes_ok=True,count_at_bound_rows=0):raise AssertionError(f"rows gate wrong: {result['rows_gate']}")
 if result['drop_gate']!=dict(icon=1,count=1,name=1,freed=0,kind_zero=0):raise AssertionError(f"drop gate wrong: {result['drop_gate']}")
 flags=result['flag_gate']
 if flags['mismatches'] or flags['condition_zero']!=1 or flags['unreadable_counted']!=1 or flags['unknown_passes']:raise AssertionError(f'flag gate wrong: {flags}')
 box=result['box']
 if box is None:raise AssertionError(f"room not captured: {result['counters']}")
 x,y,sx,sy=result['view']
 # Anchor 5 is centred, so the box centre is the matrix translation in screen space.
 cx,cy=(box[0]+box[2])/2,(box[1]+box[3])/2;ex,ey=300*sx+x,200*sy+y
 if not all(map(math.isfinite,box)) or abs(cx-ex)>.01 or abs(cy-ey)>.01 or abs(box[2]-box[0]-172*abs(sx))>.01:raise AssertionError(f'room box wrong: {box} view {result["view"]}')
 return box
def run_mutant(job):
 """One mutant in its own tree: (name, False if the gates still pass, else why they failed)."""
 name,rel,old,new,image_path=job
 with tempfile.TemporaryDirectory(prefix='re0-mutant-') as d:
  tree=Path(d)/'tree';tree.mkdir()
  for folder in ['src','tests']:shutil.copytree(ROOT/folder,tree/folder)
  source=(tree/rel).read_text()
  if old not in source:raise ValueError('mutant target gone: '+name)
  (tree/rel).write_text(source.replace(old,new));mutant=Path(d)/'mutant.dll';compile_probe(tree,mutant)
  try:verdict(run(Path(image_path).read_bytes(),mutant));return name,False
  except (AssertionError,RuntimeError,UcError) as e:return name,str(e)[:160]
def mip_mutant():
 """Live failure, candidate 29: colour un-premultiplied twice in the mip chain, white outlines. The data defect must be detected on real art."""
 sys.path.insert(0,str(ROOT/'tools'));from build_labels import icon_mips,mip_defect,MIP_BRIGHTEN_LIMIT
 from PIL import Image
 m=json.loads((ROOT/'assets/icons/manifest.json').read_text());sheet=Image.new('RGBA',(128,128));sheet.paste(Image.open(ROOT/'assets/icons'/m['files']['Green Herb']).convert('RGBA'),(16,16))
 import build_labels as b
 limit=b.MIP_BRIGHTEN_LIMIT;b.MIP_BRIGHTEN_LIMIT=1e9 # let the chain out so the check itself is judged
 try:bad=b.icon_mips(sheet,lambda im:im.resize((im.width//2,im.height//2),Image.Resampling.BOX));good=b.icon_mips(sheet)
 finally:b.MIP_BRIGHTEN_LIMIT=limit
 if mip_defect(bad,128)<=limit:raise AssertionError('white rim mip mutant survives')
 if mip_defect(good,128)>limit:raise AssertionError('mip check rejects a good chain')
def main():
 mip_mutant()
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--analysis-image',type=Path,default=ROOT/'local/research/re0hd.analysis.bin');p.add_argument('--quick',action='store_true',help='gates only, no mutants, no report: for use while editing');p.add_argument('--output',type=Path,default=ROOT/'verification/native-dispatch.json');a=p.parse_args()
 image=a.analysis_image.read_bytes()
 with tempfile.TemporaryDirectory(prefix='re0-dispatch-') as d:
  d=Path(d);dll=d/'probe.dll';compile_probe(ROOT,dll);result=run(image,dll);box=verdict(result);caught={}
  if a.quick:
   print(f'Native dispatch, no mutants: room captured at {box}; a0={result["facts"]["sprite_a0"]:#x}; nothing recorded. Run without --quick before building.');return
  # Each mutant recompiles the probe and reruns the gates, 3 to 4 s of pure CPU. Independent, so one process each.
  jobs=[(name,rel,old,new,str(a.analysis_image)) for name,(rel,old,new) in {**MUTANTS,**header_mutants()}.items()]
  with concurrent.futures.ProcessPoolExecutor(max_workers=max(1,(os.cpu_count() or 2)-1)) as pool:caught=dict(pool.map(run_mutant,jobs))
 survived=[n for n,v in caught.items() if v is False]
 if survived:raise SystemExit('Mutants survived, harness proves nothing: '+'; '.join(survived))
 report=dict(evidence='original-x86-constructors-and-dispatch-through-real-hook-slots',aspect_gate=result['aspect_gate'],lock_gate=result['lock_gate'],overlay_gate=result['overlay_gate'],ini_gate=result['ini_gate'],scope_gate=result['scope_gate'],arrange_gate=result['arrange_gate'],enemy_gate=result['enemy_gate'],emulator_gate=result['emulator_gate'],flag_gate=result['flag_gate'],fade_gate=result['fade_gate'],facts=result['facts'],counters=result['counters'],room_box=box,view=result['view'],mutants_caught=caught,
  scope='map draw -> root walk -> instance -> animation -> sprite with native vtables and constructors. Stubbed: sprite emission and per-node preparation. Not covered: D3D/GPU, Present target, native matrix construction, real resource loading.')
 a.output.write_text(json.dumps(report,indent=1)+'\n');print(f'Native dispatch: room captured at {box}; a0={result["facts"]["sprite_a0"]:#x}; {len(caught)} mutants caught')
if __name__=='__main__':main()
