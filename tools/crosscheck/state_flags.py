"""Which game state means a displayed row is done, proven from native code and event scripts. Analysis only.

Table items: native row store, not a flag (see verification/state-flags.md). Puzzles, locks and script-given keys: a flag of the bit array at
[0xdcc014]+0x20. Each curated claim below is re-checked here by walking the script group from its real entry with the flag forced to 0 and 1;
nothing is accepted because it looks right. Unicorn runs the native code for the bit test, the row lookup, the allocator, the pickup and the spawn gate.
Not exercised: the running game, the real table loader 0x412110 (its allocator and table order are), real saves.
"""
import argparse,collections,json,random,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for f in ('tools/extract','tools/inspect'):sys.path.insert(0,str(ROOT/f))
from arrange import parse
from event_disasm import Commands,SIZES
from resources import Arc
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_HOOK_MEM_UNMAPPED
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EAX,UC_X86_REG_EIP
BASE=0x400000;OWNER=0xdcc014;OFFSET=0x20;ARRANGE=0xdcc010;SLOT0=0x30;STRIDE=0x5c;SLOTS=0x4e8;COUNT=0x24fac;MODE=0x24ff0;ARRAY_WORDS=0x47
TABLES={'easy':'loctbl0000','normal':'loctbl0100','hard':'loctbl0200',**{f'leech{i}':f'loctbl030{i}' for i in range(5)}};MODE_INDEX={'easy':0,'normal':1,'hard':2}
EVIDENCE='static native analysis, script-group evaluation and Unicorn runs of native functions; no run of the game'
# (category, name_en, room): claim. door: scene, door target, flag guarding it. use: scene, used item id, flag set, whether the group consumes it.
# grant: scene, granted item, flag set once taken. none: why no flag exists.
L,P,K='lock','puzzle','key'
CLAIMS={
 (L,'Fire Key',48):('door','sh0c',51,0x25),(L,"Conductor's Key",2):('door','tr02',3,0x1),(L,'Dining Car Key',7):('door','tr07',8,0x2),
 (L,'Blue Keycard',1):('door','tr02',1,0x0),(L,'Blue Leech Charm',113):('door','ch04',113,0x11),(L,'Breeding Room Key',109):('door','ch04',109,0x13),(L,'Dial',102):('door','ch04',102,0x12),
 (L,'Fire Key',38):('door','sh01',38,0x1b),(L,'Green Leech Charm',108):('door','ch08',108,0x14),(L,'Handle',145):('door','pl03',145,0x28),(L,'Ice Pick',17):('door','tr11',15,0x6),
 (L,'Iron Needle',56):('door','sh00',56,0x24),(L,'Iron Needle',40):('door','sh04',39,0x1d),(L,'Keycard',174):('use','pl15',76,0x2d,False),
 (L,'MO Disk',45):('door','sh00',45,0x1a),(L,'MO Disk',53):('door','sh0b',53,0x1a),(L,'MO Disk',43):('door','sh1d',43,0x1a),
 (L,'Shaft Key (L)',173):('door','pl17',173,0x2c),(L,'Shaft Key (R)',173):('door','pl17',173,0x2c),(L,'Water Key',58):('door','sh15',58,0x23),
 (P,'Battery',45):('use','sh09',94,0x8c,True),(P,'Crank Handle',50):('use','sh0e',86,0x91,True),(P,'Discipline Tablet',43):('use','sh07',81,0x8a,False),(P,'Elevator Key',134):('use','bt02',67,0x19c,False),
 (P,'Hookshot',6):('none','tr06 g4 tag 8 is a reusable shortcut: it writes 0x75 and 0x45, both also written by other groups, then door_no_fade_out. No flag means used.'),
 (P,'Hookshot',100):('none','ch01 g2 tag 30 y=104 is a reusable door with no flag write for its use. No done state.'),
 (P,'Hookshot',112):('none','ch0d g2 tag 30 y=104 is a reusable door with no flag write. No done state.'),
 (P,'Hookshot',102):('none','ch03 g3 tag 30 y=104 is a reusable door with no flag write. No done state.'),
 (P,'Input Regulator Coil',104):('use','ch05',92,0xdf,True),(P,'Iron Needle',50):('use','sh0e',126,0xb4,True),(P,'Locker Key',96):('use','dm0a',78,0xca,True),(P,'MO Disk',47):('use','sh0b',124,0xa3,True),
 (P,'Magnetic Card',10):('use','tr0a',77,0x70,True),(P,'Microfilm A',39):('use','sh03',99,0xb5,True),(P,'Microfilm B',39):('use','sh03',100,0xbd,True),(P,'Motherboard',152):('use','pl0b',97,0xfd,True),
 (P,'Obedience Tablet',43):('use','sh07',80,0x89,False),(P,'Output Regulator Coil',104):('use','ch05',93,0xe0,True),(P,'Panel Opener',8):('use','tr08',82,0x8,True),(P,'Sterilizing Agent',105):('use','ch06',96,0xdd,True),
 (P,'Unity Tablet',43):('use','sh07',79,0x88,False),(P,'Up Key',136):('use','bt04',111,0xf8,True),(P,'Vise Handle',61):('use','sh19',83,0x99,True),(P,'Lighter',90):('use','dm04',106,0xb,False),(P,'Lighter',50):('use','sh0e',106,33,False),(P,'Factory Key',136):('use','bt04',73,248,False),(P,'Hi-Power Battery',153):('use','pl0c',95,254,False),
}
# Kind 0x78 rows never spawn (0x410c08): the item comes from a script group. (room, item): scene, flag.
GRANTS={(2,103):('tr02',0x4c),(3,59):('tr03',0x4f),(8,38):('tr08',0x53),(10,104):('tr0a',0x6e),(39,124):('sh03',0x184),(45,81):('sh09',0xba),(51,126):('sh0f',0x96),(52,88):('sh10',0x97),(54,89):('sh12',0xb0),(55,86):('sh13',0x98),
 (62,94):('sh1a',0x9b),(96,70):('dm0a',0xcf),(96,119):('dm0a',0xcb),(106,72):('ch07',0xe2),(110,117):('ch0b',0xe8),(113,92):('ch0e',0xeb),(153,76):('pl0c',0xff),(161,129):('pl14',0x105)}
NOTES={ (P,'Factory Key',136):'0xf8 is set by this use and by the Up Key (bt04 g5), never cleared; 0xf2 (turntable up) is cleared when it is lowered (bt02 g5).',(P,'Output Regulator Coil',104):'0xe0 is cleared again by ch03 g2 (with 0xd8, 0x17); that path also sets 0xef, never cleared. Use 0xe0 or 0xef.',(L,'Shaft Key (L)',173):'0x2c is door open. Per key 0x11d is set by the L use but cleared when both turn.',(L,'Keycard',174):'The Engine Room reader sets 0x2d, the GUI door Flag, with 0x11f that door g4 tests; neither is cleared (user 2026-11-11).',(L,'Shaft Key (R)',173):'0x2c is door open. Per key 0x11e is set by the R use but cleared when both turn.'}
ANY_OF={(P,'Output Regulator Coil',104):[0xe0,0xef]}
GRANT_NOTES={(62,94):'sh1a g6 sets 0x9b when the battery is taken off its stand, g7 clears it when it is put back, so the mark shows whenever the battery is on the stand (user 2026-11-10: put back, it had no mark). 0x9c is only the first take.'}
BRANCH={'je','jl','jg','SubItemJp','loop','loopReg'}
# Table kind: class vtable, DTI, class name, as registered by the static initialisers 0xc85d78..0xc8a475. Kinds with table rows only.
ENEMY_CLASSES={0x10:(0xcbdcd8,'uEnemy10'),0x11:(0xcc4f28,'uEnemy11'),0x12:(0xcc50a0,'uEnemy12'),0x14:(0xcc5218,'uEnemy14'),0x15:(0xcc5390,'uEnemy15'),0x16:(0xcc5508,'uEnemy16'),0x17:(0xcc5680,'uEnemy17'),0x19:(0xcc57f8,'uEnemy19'),0x1a:(0xcc5970,'uEnemy1a'),
 0x2a:(0xcc3fe8,'uEnemy2a'),0x2b:(0xcbf0d0,'uEnemy2b'),0x2c:(0xcbf5f8,'uEnemy2c'),0x2f:(0xcbf9a0,'uEnemy2f'),0x30:(0xcbfbc8,'uEnemy30'),0x31:(0xcbfe58,'uEnemy31'),0x34:(0xcc01a8,'uEnemy34'),0x35:(0xcc0458,'uEnemy35'),0x37:(0xcc08c0,'uEnemy37'),0x38:(0xcc5ae8,'uEnemy38'),0x39:(0xcc0cb0,'uEnemy39'),0x3a:(0xcc13d8,'uEnemy3a'),0x3c:(0xcc18e8,'uEnemy3c'),
 0x40:(0xcc1ce8,'uEnemy40'),0x43:(0xcc25d8,'uEnemy43'),0x46:(0xcc3248,'uEnemy46'),0x47:(0xcc3710,'uEnemy47'),0x50:(0xcc5dd8,'uEnemy50'),0x51:(0xcc5f50,'uEnemy51'),0x5a:(0xcc60c8,'uEnemy5a'),0x5b:(0xcc6240,'uEnemy5b'),0x6a:(0xcc63b8,'uEnemy6a'),0x6b:(0xcc6530,'uEnemy6b')}
class Scripts:
 """Event scripts of the main game (not the 'b' twin, whose doors are all unguarded and whose scene set matches the Leech Hunter tables)."""
 def __init__(self,game,commands):
  self.c=commands;self.members={};self.unknown=0
  for f in sorted((game/'nativePC/arc/scene').glob('*.arc')):
   a=Arc(f.read_bytes());ms=[(m.name.split('\\')[-1],m) for m in a.members if m.kind==0x714ec77c];names=[n for n,_ in ms]
   for n,m in ms:
    if n.endswith('b') and n[:-1] in names:continue
    self.members[f.stem]=(n,a.read(m))
 def heads(self,scene):
  _,d=self.members[scene];n=struct.unpack_from('>I',d,0)[0]
  return [(i,)+struct.unpack_from('>4I',d,16+i*16) for i in range(min(n,32))]
 def dec(self,d,at):
  op=struct.unpack_from('>H',d,at)[0]
  if op>=len(self.c.ops):return None
  name,fmt,_=self.c.ops[op];p=at+2;args=[]
  for f in fmt:
   s,code=SIZES[f];args.append(struct.unpack_from(code,d,p)[0]);p+=s
  return name,args,p
 def reach(self,d,entry):
  """Instructions reachable from a group entry, conditions ignored. Stops at the first exit; never runs into the next group. Branch target 0 is never followed: scripts contain gosub(0) as a null."""
  seen={};todo=[entry]
  while todo:
   pc=todo.pop()
   while pc not in seen and pc<len(d):
    r=self.dec(d,pc)
    if r is None:self.unknown+=1;break
    n,a,nx=r;seen[pc]=(n,a)
    if n in('exit','ret','SubItemRet','SubItemRet2'):break
    if n=='jmp':
     pc=a[0] or len(d);continue
    if (n in BRANCH or n=='gosub') and a[0]:todo.append(a[0])
    pc=nx
  return seen
 def evaluate(self,d,entry,flag,value):
  """Run the group with one flag forced. Result is a known number after ResFlag on that flag and the RegRes/CmpRegImm/je switch the compiler emits (je 0x576570 jumps when result 0, CmpRegImm 0x576960 subtracts). Anything else forks. Yields (name,args,flag value at that point)."""
  out=set();seen=set();todo=[(entry,None,(),value,())];limit=400000
  while todo and limit:
   pc,res,regs,val,stack=todo.pop();limit-=1
   key=(pc,res,regs,val,stack)
   if key in seen or pc>=len(d) or not pc:continue
   seen.add(key);r=self.dec(d,pc)
   if r is None:continue
   n,a,nx=r;R=dict(regs);out.add((n,tuple(a),val))
   def go(p,res=None,val=val,stack=stack,R=R):todo.append((p,res,tuple(sorted(R.items())),val,stack))
   if n=='ResFlag':go(nx,res=val if a[0]==flag else None)
   elif n=='RegRes':R[a[0]]=res;go(nx,res=res)
   elif n=='CmpRegImm':go(nx,res=None if R.get(a[0]) is None else R[a[0]]-a[1])
   elif n=='je':
    if res is None or res==0:go(a[0],res=res)
    if res is None or res!=0:go(nx,res=res)
   elif n=='jmp':go(a[0],res=res)
   elif n in('jl','jg','SubItemJp','loop','loopReg'):go(a[0]);go(nx)
   elif n=='gosub':
    if a[0]:go(a[0],stack=stack+(nx,))
    else:go(nx)
   elif n=='ret':
    if stack:go(stack[-1],res=res,stack=stack[:-1])
   elif n in('exit','SubItemRet','SubItemRet2'):pass
   elif n=='FlagSet':go(nx,res=res,val=(1 if a[1] else 0) if a[0]==flag else val)
   else:go(nx)
  return out
 def index(self):
  """Every reachable write and read of every flag, attributed to the group that really reaches it."""
  W=collections.defaultdict(set);Rd=collections.defaultdict(set)
  for sc,(mem,d) in self.members.items():
   for i,tag,off,x,y in self.heads(sc):
    if not off:continue
    for pc,(n,a) in self.reach(d,off).items():
     t=f'{sc}:g{i}'
     if n=='FlagSet':W[a[0]].add((t,1 if a[1] else 0))
     elif n=='FlagSetMB':
      for k in range(a[1]):W[a[0]+k].add((t,'mb'))
     elif n=='SetEnemyFlag':W[0x312+a[0]].add((t,1 if a[1] else 0))
     elif n in('ResFlag','CmpResultFlag','ResFlagF'):Rd[a[0]].add(t)
     elif n=='RegFlag':Rd[a[1]].add(t)
     elif n=='ResFlagMB':
      for k in range(a[1]):Rd[a[0]+k].add(t)
     elif n=='ParamFlagMB':
      for k in range(a[2]):Rd[a[1]+k].add(t)
  return W,Rd
def door_ok(s,scene,target,flag):
 """The group with door(target) reaches it with the flag set, and with it clear only after writing it."""
 _,d=s.members[scene]
 for i,tag,off,x,y in s.heads(scene):
  if tag!=31 or not off or not any(n in('door','door_camera') and a[0]==target for n,a in s.reach(d,off).values()):continue
  on=s.evaluate(d,off,flag,1);off0=s.evaluate(d,off,flag,0)
  hit=lambda e:[v for n,a,v in e if n in('door','door_camera') and a[0]==target]
  if hit(on) and all(v==1 for v in hit(off0)):return f'{scene} g{i} tag 31: door({target}) needs flag set; clear path only sets it first'
 return None
def use_ok(s,scene,item,flag,consumes):
 _,d=s.members[scene]
 for i,tag,off,x,y in s.heads(scene):
  if tag!=8 or y!=item or not off:continue
  e=s.evaluate(d,off,flag,0)
  if not any(n=='FlagSet' and a[0]==flag and a[1] for n,a,_ in e):continue
  if consumes and not any(n=='item_sub' for n,a,_ in e):continue
  return f'{scene} g{i} tag 8 y={item}: FlagSet(0x{flag:x},1)'+(' with item_sub' if consumes else '')
 return None
def after_taken(s,d,pc,flag):
 """Compiler pattern after a grant: Sub_GetResult, jmp to a switch, case 1 runs straight into FlagSet(flag,1). So the flag is written only when the item was taken."""
 for _ in range(4):
  n,a,pc=s.dec(d,pc)
  if n=='Sub_GetResult':break
 else:return False
 n,a,_=s.dec(d,pc)
 if n!='jmp':return False
 n,a,pc=s.dec(d,a[0])
 if n!='RegRes':return False
 n,a,pc=s.dec(d,pc)
 if n!='CmpRegImm' or a[1]!=1:return False
 n,a,_=s.dec(d,pc)
 if n!='je':return False
 pc=a[0]
 for _ in range(8):
  n,a,pc=s.dec(d,pc)
  if n=='FlagSet' and a[0]==flag and a[1]:return True
  if n in('jmp','je','exit','ret','gosub'):return False
 return False
def follows_flag(s,d,off,flag,item):
 """A second item in one taken path: linear from FlagSet(flag,1) to its Sub_ReadyGet with no branch between. Hookshot and its manual, MO Disk and Microfilm Image, and the like."""
 for pc,(n,a) in s.reach(d,off).items():
  if n!='FlagSet' or a[0]!=flag or not a[1]:continue
  at=pc
  for _ in range(40):
   n2,a2,at=s.dec(d,at)
   if n2=='Sub_ReadyGet' and a2[0]==item:return True
   if n2 in('exit','ret','jmp','je','SubItemRet','SubItemRet2'):break
 return False
def grant_ok(s,scene,item,flag):
 _,d=s.members[scene]
 for i,tag,off,x,y in s.heads(scene):
  if not off:continue
  e0=s.evaluate(d,off,flag,0);e1=s.evaluate(d,off,flag,1);give=lambda e:any(n in('Sub_ReadyGet','Sub_ReadyGetParam','item_get') and a[0]==item for n,a,_ in e)
  if give(e0) and any(n=='FlagSet' and a[0]==flag and a[1] for n,a,_ in e0) and not give(e1):return f'{scene} g{i} tag {tag}: Sub_ReadyGet({item}) then FlagSet(0x{flag:x},1); flag set blocks the grant'
 for i,tag,off,x,y in s.heads(scene):
  if not off:continue
  for pc,(n,a) in s.reach(d,off).items():
   if n=='Sub_ReadyGet' and a[0]==item and after_taken(s,d,s.dec(d,pc)[2],flag):return f'{scene} g{i} tag {tag}: Sub_ReadyGet({item}), Sub_GetResult, case 1 FlagSet(0x{flag:x},1)'
 for i,tag,off,x,y in s.heads(scene):
  if off and follows_flag(s,d,off,flag,item):return f'{scene} g{i} tag {tag}: FlagSet(0x{flag:x},1) then Sub_ReadyGet({item}) in the taken path'
 return None
def script_row(s,W,r,row):
 """Done state of a SCRIPT_GRANTS row. The group's own disassembly decides, not the table in placements.py."""
 g=r['script'];sc=g['scene'];_,d=s.members[sc];head=s.heads(sc)[g['group']];off=head[2]
 given=[(n,a) for n,a in s.reach(d,off).values() if n in('Sub_ReadyGet','item_get') and a[0]==r['item']]
 if not given:return row.update(store='none',status='unresolved',evidence=f"{sc} g{g['group']} gives no item {r['item']}")
 if 'flag' not in g:
  writes=[a[0] for n,a in s.reach(d,off).values() if n=='FlagSet']
  return row.update(store='none',status='proven',evidence=f"{sc} g{g['group']}: item_sub then item_get with {'no FlagSet' if not writes else 'no FlagSet on the path'}, a reusable station. No done state.")
 f=g['flag'];ev=grant_ok(s,sc,r['item'],f);cleared=sorted(t for t,v in W[f] if v==0)
 row.update(store='flag',done_flag=f,done_when='set',status='proven' if ev and not cleared else 'inferred',evidence=(ev or f"{sc} g{g['group']} tag {head[1]}: 0x{f:x} written once on the linear path of a one-shot event; not taken-checked")+(f'; cleared by {cleared}' if cleared else ''))
 if 'also' in g:
  a=g['also'];stops=not any(n in('Sub_ReadyGet','item_get') and x[0]==r['item'] for n,x,_ in s.evaluate(d,off,a,1))
  row['done_any_of']=[f,a];row['evidence']+=f"; also closed by 0x{a:x}: {'with it set the group does not give the item' if stops else 'not confirmed'}, written by {sorted(W[a])}"
  if not stops or any(v==0 for _,v in W[a]):row['status']='inferred'
class Native:
 def __init__(self,image):
  pe=struct.unpack_from('<I',image,60)[0];opt=pe+24;size=struct.unpack_from('<I',image,opt+56)[0]
  self.u=Uc(UC_ARCH_X86,UC_MODE_32);self.u.mem_map(BASE,(size+0xfff)&~0xfff)
  for i in range(struct.unpack_from('<H',image,pe+6)[0]):
   o=opt+struct.unpack_from('<H',image,pe+20)[0]+i*40;_,_,va,sz,raw=struct.unpack_from('<8sIIII',image,o)
   if sz:self.u.mem_write(BASE+va,image[raw:raw+sz])
  self.stack=0x20000000;self.mgr=0x30000000;self.flags=0x40000000;self.actor=0x50000000
  for a,n in ((self.stack,0x100000),(self.mgr,0x30000),(self.flags,0x3000),(self.actor,0x2000),(0x1000,0x1000)):self.u.mem_map(a,n)
  self.stubs={}
  self.u.hook_add(UC_HOOK_CODE,self._code,begin=BASE,end=0x1000000)
 def _code(self,u,addr,size,_):
  if addr==0x401f50:raise RuntimeError('native assert reached')
  if addr in self.stubs:
   sp=u.reg_read(UC_X86_REG_ESP);ret=struct.unpack('<I',bytes(u.mem_read(sp,4)))[0];n=self.stubs[addr]
   u.reg_write(UC_X86_REG_ESP,sp+4+n);u.reg_write(UC_X86_REG_EIP,ret)
 def r32(self,a):return struct.unpack('<I',bytes(self.u.mem_read(a,4)))[0]
 def w32(self,a,v):self.u.mem_write(a,struct.pack('<I',v&0xffffffff))
 def call(self,addr,ecx,*args,stop=0x1000,count=2000000):
  sp=self.stack+0x80000;self.u.mem_write(sp,struct.pack('<I',0x1000)+b''.join(struct.pack('<I',a&0xffffffff) for a in args))
  self.u.reg_write(UC_X86_REG_ESP,sp);self.u.reg_write(UC_X86_REG_ECX,ecx);self.u.reg_write(UC_X86_REG_EAX,0)
  self.u.emu_start(addr,stop,count=count);return self.u.reg_read(UC_X86_REG_EAX)
 def slot(self,i):return self.mgr+SLOT0+i*STRIDE
def enemy_save_runs(image):
 """Each enemy class's save virtual (vtable +0x94), run on a zeroed actor with native setter 0x529310 giving it HP: what 0x412c30 would store. Random 0x660070 stubbed to 0."""
 out={}
 for kind,(vt,name) in sorted(ENEMY_CLASSES.items()):
  n=Native(image);a=0x60000000;row=0x70000000;n.u.mem_map(a,0x20000);n.u.mem_map(row,0x1000);n.u.mem_map(0,0x1000)
  # Animation and ground helpers ahead of the HP test are not what is checked here. The DTI id at +0x1c is set by 0x67d860 at startup, which is not run.
  n.stubs={0x660070:0,0x43a300:0,0x4ba0a0:0,0x4c8e80:4}
  n.w32(0xdcc014,n.flags);slot=lambda:n.r32(vt+0x94);got={};dti=struct.unpack('<I',bytes(n.u.mem_read(n.r32(vt+0x10)+1,4)))[0];n.w32(dti+0x1c,0x80000000|kind)
  for hp in (1,0,-5):
   n.u.mem_write(a,b'\0'*0x20000);n.u.mem_write(row,b'\0'*0x100);n.w32(a,vt);n.call(0x529310,a,hp)
   try:got[hp]=n.call(slot(),a,row)
   except Exception as e:got[hp]=f'{type(e).__name__}'
  out[kind]=dict(name=name,save=hex(slot()),at_hp_one=got[1],at_hp_zero=got[0],at_hp_negative=got[-5],hp_stored=struct.unpack('<i',bytes(n.u.mem_read(row+0x3c,4)))[0])
 return out
def bit_test(n):
 """0x59b8d0 against flags[i>>5]>>(i&31)&1 over the whole u16 range."""
 rnd=random.Random(1);words=[rnd.getrandbits(32) for _ in range(0x800)]
 n.u.mem_write(n.flags+OFFSET,struct.pack(f'<{len(words)}I',*words));bad=0
 for i in range(0x10000):bad+=n.call(0x59b8d0,n.flags,i)!=(words[i>>5]>>(i&31)&1)
 return dict(native='0x59b8d0',samples=0x10000,mismatches=bad)
def lookup(n):
 bad=sum(n.call(0x40fd70,n.mgr,i)!=n.slot(i) for i in range(SLOTS))
 return dict(native='0x40fd70',samples=SLOTS,mismatches=bad+(n.call(0x40fd70,n.mgr,-1)!=0))
def empty_row(n):
 """0x410610 (empty-slot test) against kind==0 or byte+0x39!=0, all kinds and four byte values, slots across the range."""
 bad=tot=0
 for s in range(0,SLOTS,37):
  p=n.slot(s)
  for kind in range(256):
   for b in (0,1,2,255):
    n.w32(p+4,kind);n.u.mem_write(p+0x39,bytes([b]));tot+=1
    bad+=(n.call(0x410610,n.mgr,s)&0xff)!=int(kind==0 or b!=0)
 return dict(native='0x410610',samples=tot,mismatches=bad)
def spawn_gate(n):
 """0x410bb0 up to its first dependency: reaches 0x410c36 only for kind not 0, not 0x78, and +0x39 zero. Full kind range."""
 n.w32(0xdcc0d0,n.actor);bad=tot=0
 for s in (0,1,500,0x3e7,SLOTS-1):
  p=n.slot(s)
  for kind in range(256):
   for b in (0,1,255):
    n.w32(p+4,kind);n.u.mem_write(p+0x39,bytes([b]));tot+=1
    n.call(0x410bb0,n.mgr,0,s,0,stop=0x410c36);got=n.u.reg_read(UC_X86_REG_EIP)==0x410c36
    bad+=got!=(kind not in(0,0x78) and b==0)
 return dict(native='0x410bb0 through 0x410c36',samples=tot,mismatches=bad)
def allocator_and_pickup(n,table):
 """Native 0x4101f0 then 0x40fb10 per row in table order: slot must equal the running count. Then native 0x4de730 on every table slot, and on one dropped slot."""
 n.u.mem_write(n.mgr,b'\0'*0x30000);n.call(0x4101f0,n.mgr)
 bad=k=0
 for rm in table:
  for _ in rm['records']:
   bad+=n.call(0x40fb10,n.mgr,rm['room'])!=k;k+=1
 walked=0
 for rm in table:
  i=n.r32(n.mgr+0x24ce8+rm['room']*4);seen=[]
  while i!=0xffffffff and len(seen)<SLOTS:
   seen.append(i);i=n.r32(n.mgr+0x28+i*STRIDE)
  walked+=len(seen)
 n.w32(n.mgr+COUNT,n.r32(n.mgr+0x24fa4));count=n.r32(n.mgr+COUNT)
 n.w32(ARRANGE,n.mgr);n.w32(0xdcbf40,n.actor);n.w32(0xdcc0d0,n.actor);n.stubs={0x61b100:4,0x51f460:4}
 for s in range(count):n.w32(n.slot(s)+4,0x71)
 pick=0
 for s in range(count):
  n.w32(n.actor+0xff0,s);n.call(0x4de730,n.actor+0,n.actor)
  pick+=n.r32(n.slot(s)+4)!=0 or n.r32(n.mgr+0x2c+s*STRIDE)==0xffffffff
 gate=0
 n.w32(0xdcc0d0,n.actor)
 for s in range(0,count,7):
  n.call(0x410bb0,n.mgr,0,s,0,stop=0x410c36);gate+=n.u.reg_read(UC_X86_REG_EIP)==0x410c36
 d=n.call(0x40fb10,n.mgr,table[0]['room']);n.w32(n.actor+0xff0,d);n.call(0x4de730,n.actor,n.actor)
 dropped=n.r32(n.mgr+0x2c+d*STRIDE)==0xffffffff
 unlinked=0
 for s in (0,count//2,count-1):
  n.call(0x412060,n.mgr,s);unlinked+=n.r32(n.mgr+0x2c+s*STRIDE)==0xffffffff # script ObjDeleteType 0x5745a9 frees a table slot this way
 n.stubs={}
 return dict(native='0x4101f0,0x40fb10,0x4106c0,0x4de730,0x412060,0x412d90,0x410bb0',rows=count,slot_mismatches=bad,listed=walked,pickup_mismatches=pick,respawn_after_pickup=gate,dropped_slot_freed=dropped,freed_table_slots_unlinked=unlinked)
def spot(room,kind,item,pos,condition,nth):return room,kind,item,tuple(round(v,2) for v in pos),condition,nth
def slots(game,rows):
 """Slot of a row per table: rooms ascending (0x412110 loops 0..0xae), file order inside a room, free list from 0 (0x4101f0, 0x40fb10)."""
 arc=Arc((game/'nativePC/arc/arrange/loctbl.arc').read_bytes());tables={m:parse(arc.read(next(x for x in arc.members if x.name.endswith(t)))) for m,t in TABLES.items()}
 where={};sizes={}
 for m,t in tables.items():
  if [r['room'] for r in t]!=sorted({r['room'] for r in t}):raise ValueError('table not ascending by room')
  k=0;repeats={}
  for rm in t:
   for r in rm['records']:
    at=spot(rm['room'],r['kind'],r['item'],r['pos'],r['a'][0],0)[:5];nth=repeats[at]=repeats.get(at,-1)+1
    where[(m,*at,nth)]=k;k+=1
  sizes[m]=k
 return tables,where,sizes
def build(game,image,rows):
 s=Scripts(game,Commands(image));W,Rd=s.index();tables,where,sizes=slots(game,rows);out=[];problems=[]
 enemy_saves=enemy_save_runs(image)
 for i,r in enumerate(rows):
  cat=r['category']
  row=dict(index=i,category=cat,name_en=r['name_en'],room=r['room'],done_flag=None,done_when=None,evidence='',status='unresolved')
  if 'puzzle_row' in r: # the cutscene of an item-use puzzle runs when it is solved
   out.append(dict(out[r['puzzle_row']],index=i,name_en=r['name_en'],evidence=f"state of puzzle row {r['puzzle_row']}: "+out[r['puzzle_row']]['evidence']));continue
  if cat=='enemy' or r.get('kind')==113:
   sl={m:where.get((m,*spot(r['room'],r['kind'],r['item'],r['world'],r['condition'],r.get('nth',0)))) for m in r['amount']}
   if None in sl.values():problems.append(i)
   row.update(store='arrange_row',slot=sl,status='proven' if None not in sl.values() else 'unresolved')
   if cat=='enemy':
    how=enemy_saves.get(r['kind'],{})
    row.update(kind=r['kind'],done_when='row_gone_or_actor_hp',evidence=f"{ENEMY_CLASSES[r['kind']][1]}: save virtual {how.get('save')} returns 1 at HP 0, so 0x412d7a sets row+0x39 and spawn 0x410c02 refuses it. Actor HP +0x1030 while its room is loaded.")
    if how.get('at_hp_zero')!=1:row.update(status='live-only',evidence=f"{ENEMY_CLASSES[r['kind']][1]}: save virtual {how.get('save')} returns {how.get('at_hp_zero')} at HP 0, so the row is never marked. Only actor HP +0x1030 while its room is loaded.")
   else:row.update(done_when='row_kind_zero_or_unlinked',evidence='spawn 0x410bf5, pickup 0x4de80d-0x4de816, slot order 0x412110/0x40fb10')
  elif 'done_flag' in r: # event marks, and script puzzles that were event groups
   row.update(store='flag',done_flag=r['done_flag'],need_flag=r.get('need_flag'),done_when='set',evidence=r['evidence']+'; see verification/event-audit.json',status='script_read')
  elif 'group' in r.get('script',{}):script_row(s,W,r,row)
  elif r.get('kind')==120:
   sc,f=GRANTS[(r['room'],r['item'])];ev=grant_ok(s,sc,r['item'],f);cleared=[t for t,v in W[f] if v==0]
   row.update(store='flag',done_flag=f,done_when='set',evidence=(ev or GRANT_NOTES.get((r['room'],r['item']),'grant check failed'))+'; kind 0x78 never spawns (0x410c08)',status='proven' if ev and not cleared else 'inferred')
   if cleared:row['evidence']+=f'; cleared by {sorted(cleared)}'
  else:
   key=(cat,r['name_en'],r['room']);c=CLAIMS[key]
   if c[0]=='none':row.update(store='none',evidence=c[1])
   else:
    if c[0]=='door':f=c[3];ev=door_ok(s,c[1],c[2],f)
    else:
     f=c[3];ev=use_ok(s,c[1],c[2],f,c[4])
    cleared=sorted(t for t,v in W[f] if v==0)
    row.update(store='flag',done_flag=f,done_when='set',evidence=ev or f'check failed for 0x{f:x}',status='proven' if ev and not cleared else ('inferred' if ev else 'unresolved'))
    if cleared:row['evidence']+=f'; cleared by {cleared}'
    if key in ANY_OF:row['done_any_of']=ANY_OF[key]
    if key in NOTES:row['evidence']+='; '+NOTES[key]
  out.append(row)
 used=[r['done_flag'] for r in out if r['done_flag'] is not None]+[f for r in out for f in r.get('done_any_of',[])]
 n=Native(image);checks=dict(enemy_saves=enemy_saves,bit_test=bit_test(n),row_lookup=lookup(n),empty_row=empty_row(n),spawn_gate=spawn_gate(n),allocator_and_pickup={m:allocator_and_pickup(n,t) for m,t in tables.items()})
 return dict(schema_version=1,evidence=EVIDENCE,exe_analysis_image=str(Path('local/research/re0hd.analysis.bin')),
  array=dict(owner_address=hex(OWNER),offset=hex(OFFSET),words_needed=max(used)//32+1,words_available=ARRAY_WORDS,max_done_flag=hex(max(used))),
  row_store=dict(owner_address=hex(ARRANGE),slot_base=hex(SLOT0),stride=hex(STRIDE),kind_offset='0x4',item_offset='0x8',room_offset='0x0',taken_byte_offset='0x39',table_count_offset=hex(COUNT),table_mode_offset=hex(MODE),table_counts=sizes,
   link_offset_from_manager='0x2c+slot*0x5c',done_rule='row kind (slot base+4) is 0, byte +0x39 is set (the spawn gate refuses it, 0x410c02), or the room link at manager+0x2c+slot*0x5c is -1 (ObjDeleteType); for an enemy row also an actor on its slot with HP at or below 0. Read only when the count equals table_counts for a table, row+0 holds the room, row+4 the kind or 0, and row+8 the item (items only: 0x412c30 rewrites it for actors); otherwise not done and counted',modes='0 loctbl0000, 1 loctbl0100, 2 loctbl0200; 3 random loctbl030x; 4 and 5 others'),
  native_checks=checks,unmatched_item_rows=problems,rows=out)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game',type=Path,required=True);p.add_argument('--analysis-image',type=Path,default=ROOT/'local/research/re0hd.analysis.bin');p.add_argument('--placements',type=Path,default=ROOT/'data/placements.json');p.add_argument('--output',type=Path,default=ROOT/'verification/state-flags.json');a=p.parse_args()
 r=build(a.game,a.analysis_image.read_bytes(),json.loads(a.placements.read_text())['rows']);a.output.write_text(json.dumps(r,ensure_ascii=False,indent=1)+'\n')
 c=collections.Counter((x['category'],x['status']) for x in r['rows']);print(sorted(c.items()));print(r['array']);print(json.dumps(r['native_checks']));print('unmatched',r['unmatched_item_rows'])
 for x in r['rows']:
  if x['status']!='proven' and x['category'] in('lock','puzzle','key','item','file','enemy') and x.get('store')!='arrange_row' or x['status']=='live-only':print(x['index'],x['category'],x['name_en'],x['room'],x['status'],x['evidence'][:200])
