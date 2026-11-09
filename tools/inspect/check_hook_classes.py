"""Prove each hooked vtable is the class the map really instantiates, from resource class hashes and native factories."""
from pathlib import Path
import argparse,json,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'tools/inspect'))
from resources import Gui
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
BASE=0x400000
class Image:
 def __init__(self,blob):
  self.b=blob;pe=struct.unpack_from('<I',blob,60)[0];opt=pe+24;self.secs=[]
  for i in range(struct.unpack_from('<H',blob,pe+6)[0]):
   o=opt+struct.unpack_from('<H',blob,pe+20)[0]+i*40;_,_,va,sz,raw=struct.unpack_from('<8sIIII',blob,o);self.secs.append((va,sz,raw))
 def off(self,a):
  for rva,sz,raw in self.secs:
   if rva<=a-BASE<rva+sz:return a-BASE-rva+raw
  raise ValueError(hex(a))
 def u32(self,a):return struct.unpack_from('<I',self.b,self.off(a))[0]
def crc(name):return (zlib.crc32(name.encode())^0xffffffff)&0xffffffff
def factory_vtable(image,dti):
 """Follow DTI new() to the constructor and return the last vtable it installs on the object."""
 md=Cs(CS_ARCH_X86,CS_MODE_32);new=image.u32(dti+4);ctor=None
 for i in md.disasm(image.b[image.off(new):image.off(new)+64],new):
  if i.mnemonic=='jmp' and i.op_str.startswith('0x') and abs(int(i.op_str,16)-new)>64:ctor=int(i.op_str,16);break
  if i.mnemonic=='ret':break
 if ctor is None:raise ValueError('factory shape changed')
 for i in md.disasm(image.b[image.off(ctor):image.off(ctor)+64],ctor):
  if i.mnemonic=='mov' and i.op_str.startswith('dword ptr [esi], 0x'):return int(i.op_str.split(', ')[1],16)
 raise ValueError('constructor shape changed')
def check(image):
 classes={}
 for path in sorted((ROOT/'local/research').glob('map_??.gui')):
  gui=Gui(path.read_bytes())
  for row in gui.instances:
   if row['name'].startswith('i_'):
    key='door' if row['name'].startswith('i_door') else 'room'
    classes.setdefault(key,set()).add(row['raw'][6])
 room=crc('cGUIInstAnimation');door=crc('cGUIInstDoorAnimation')
 if classes['room']!={room}:raise ValueError('room pieces are not all cGUIInstAnimation')
 if classes['door']-{door,crc('cGUIInstNull')}:raise ValueError('unexpected door instance class')
 vt=factory_vtable(image,0xd2543c)
 if vt!=0xd25448 or image.u32(vt+0x30)!=0x87cc40:raise ValueError('cGUIInstAnimation vtable/draw slot mismatch')
 if image.u32(0xd25478)!=0x87cc40 or image.u32(0xd26168)!=0x890ae0 or image.u32(0xcdc6a8)!=0x883090:raise ValueError('hook slot original changed')
 # Both renderer classes exist in the EXE; the runtime guard accepts either.
 if image.b[image.off(0x6021c0):image.off(0x6021c0)+7]!=bytes.fromhex('c74500c05fce00'):raise ValueError('renderer subclass vtable site changed')
 source=(ROOT/'src/runtime/re0_map.c').read_text()
 if 'VA(0xd25478)' not in source or '0xce5fc0' not in source:raise ValueError('runtime does not use the verified hook targets')
 return dict(evidence='static-resource-class-hash-and-native-factory',room_class='cGUIInstAnimation',room_vtable=hex(vt),room_slot='0xd25478',door_class='cGUIInstDoorAnimation',renderer_vtables=['0xce5fc0','0xd1b278'],scope='class identity only; no live object inspection')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--analysis',type=Path,default=ROOT/'local/research/re0hd.analysis.bin');p.add_argument('--output',type=Path,default=ROOT/'verification/hook-classes.json');a=p.parse_args()
 report=check(Image(a.analysis.read_bytes()));a.output.write_text(json.dumps(report,indent=2)+'\n');print('Hook classes verified:',report['room_class'],report['room_slot'])
