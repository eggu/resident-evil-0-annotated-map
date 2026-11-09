"""Disassemble rEventScript with the game's own command table; argument layout from native reader 0x57ccc0."""
import struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/inspect'))
BASE=0x400000;TABLE=0xcd57dc # reader: fmt=[TABLE+12*op]; then name, handler
class Commands:
 def __init__(self,image):
  self.b=image;pe=struct.unpack_from('<I',image,60)[0];opt=pe+24;self.secs=[]
  for i in range(struct.unpack_from('<H',image,pe+6)[0]):
   o=opt+struct.unpack_from('<H',image,pe+20)[0]+i*40;_,_,va,sz,raw=struct.unpack_from('<8sIIII',image,o);self.secs.append((va,sz,raw))
  self.ops=[]
  while True:
   k=len(self.ops);f,n,h=[self.u32(TABLE+12*k+4*j) for j in range(3)]
   if not all(0xc00000<p<0xe00000 for p in (f,n)) or not 0x400000<h<0xc00000:break
   self.ops.append((self.cstr(n),self.fmt(self.cstr(f)),h))
 def off(self,a):
  for rva,sz,raw in self.secs:
   if rva<=a-BASE<rva+sz:return a-BASE-rva+raw
  raise ValueError(hex(a))
 def u32(self,a):return struct.unpack_from('<I',self.b,self.off(a))[0]
 def cstr(self,a):
  o=self.off(a);return self.b[o:self.b.index(b'\0',o)].decode('latin1')
 @staticmethod
 def fmt(text):
  out=[];i=0
  while i<len(text):out.append(text[i:i+2]);i+=2
  return out
SIZES={'U1':(1,'>B'),'U2':(2,'>H'),'U4':(4,'>I'),'S1':(1,'>b'),'S2':(2,'>h'),'S4':(4,'>i'),'F4':(4,'>f'),'Rn':(1,'>B'),'Fn':(2,'>H')}
def decode(data,start,end,commands):
 """Yield (offset, name, args). Raises when a command leaves the group's bounds, which means the layout is wrong."""
 at=start;rows=[]
 while at<end:
  if at+2>end:raise ValueError(f'trailing byte at {at}')
  op=struct.unpack_from('>H',data,at)[0]
  if op>=len(commands.ops):raise ValueError(f'bad opcode {op} at {at}')
  name,fmt,_=commands.ops[op];here=at;at+=2;args=[]
  for f in fmt:
   if f not in SIZES:raise ValueError(f'unknown argument type {f} in {name}')
   size,code=SIZES[f]
   if at+size>end:raise ValueError(f'{name} runs past group end at {here}')
   args.append(struct.unpack_from(code,data,at)[0]);at+=size
  rows.append((here,name,args))
 return rows
def groups(data):
 count=struct.unpack_from('>I',data,0)[0];rows=[struct.unpack_from('>4I',data,16+i*16) for i in range(min(count,32))]
 ends=[r[1] for r in rows[1:]]+[len(data)]
 return [(r,e) for r,e in zip(rows,ends)]
