"""Execute a separately built synthetic x86 adapter probe in Unicorn, without Wine/game."""
from pathlib import Path
import argparse,struct,json,sys
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_EIP,UC_X86_REG_EAX
ROOT=Path(__file__).resolve().parents[2]
INI={} # what the stubbed GetPrivateProfileIntA finds, by key
def load_dll(uc,path,ticks=None,extra=None):
 """Map a built probe DLL with API stubs; returns its exports. Used by the synthetic and native-dispatch checks."""
 blob=path.read_bytes();u16=lambda o:struct.unpack_from('<H',blob,o)[0];u32=lambda o:struct.unpack_from('<I',blob,o)[0]
 ticks=ticks or [100];pe=u32(60);opt=pe+24;base=u32(opt+28);size=u32(opt+56)
 uc.mem_map(base,(size+4095)&~4095);uc.mem_write(base,blob[:u32(opt+60)])
 for i in range(u16(pe+6)):
  o=opt+u16(pe+20)+i*40;_,va,sz,raw=struct.unpack_from('<4I',blob,o+8)
  if sz:uc.mem_write(base+va,blob[raw:raw+sz])
 def read32(a):return struct.unpack('<I',bytes(uc.mem_read(a,4)))[0]
 def string(a):
  b=bytearray()
  while (v:=bytes(uc.mem_read(a+len(b),1)))!=b'\0':
   b.extend(v)
   if len(b)>1024:raise ValueError('unterminated PE name')
  return b.decode('ascii')
 uc.mem_map(0x100000,0x20000);uc.mem_map(0x200000,0x20000)
 imports={};slot=0x200000
 imp=u32(opt+104)
 if imp:
  a=base+imp
  while read32(a+12):
   oft,_,_,name,ft=struct.unpack('<5I',bytes(uc.mem_read(a,20)))
   dll=string(base+name);i=0
   while (v:=read32(base+(oft or ft)+i*4)):
    name=f'ordinal-{v&0xffff}' if v&0x80000000 else string(base+v+2)
    imports[slot]=(dll,name);uc.mem_write(base+ft+i*4,struct.pack('<I',slot));uc.mem_write(slot,b'\xc3');slot+=16;i+=1
   a+=20
 export=base+u32(opt+96)
 count=read32(export+24);funcs=base+read32(export+28);names=base+read32(export+32);ords=base+read32(export+36)
 entries={string(base+read32(names+i*4)):base+read32(funcs+struct.unpack('<H',bytes(uc.mem_read(ords+i*2,2)))[0]*4) for i in range(count)}
 tls={};seen={}
 def hook(machine,address,size,_):
  if address not in imports:return
  dll,name=imports[address];seen[name]=seen.get(name,0)+1
  sp=machine.reg_read(UC_X86_REG_ESP);ret=read32(sp);arg=lambda i:read32(sp+4+4*i)
  clean=0;result=0
  if name=='TlsGetValue':result=tls.get(arg(0),0);clean=4
  elif name=='TlsSetValue':tls[arg(0)]=arg(1);result=1;clean=8
  elif name in ('EnterCriticalSection','LeaveCriticalSection'):clean=4
  elif name=='GetTickCount':ticks[0]+=200;result=ticks[0]
  elif name=='VirtualQuery':
   p=arg(0);start=p&~4095
   machine.mem_write(arg(1),struct.pack('<7I',start,start,4,4096,0x1000,4,0x20000));result=28;clean=12
  elif name=='VirtualProtect':machine.mem_write(arg(3),struct.pack('<I',4));result=1;clean=16
  elif name=='FlushInstructionCache':result=1;clean=12
  elif name=='GetPrivateProfileIntA':result=INI.get(string(arg(1)),arg(2));clean=16
  elif name=='GetPrivateProfileStringA':
   value=INI.get(string(arg(1)));text=value if isinstance(value,str) else string(arg(2));data=text.encode()[:max(arg(4)-1,0)]+b'\0'
   machine.mem_write(arg(3),data);result=len(data)-1;clean=24
  elif name=='GetCurrentProcess':result=0xffffffff
  elif name in ('memcpy','memmove'):
   machine.mem_write(arg(0),bytes(machine.mem_read(arg(1),arg(2))));result=arg(0)
  elif name=='memset':machine.mem_write(arg(0),bytes([arg(1)&255])*arg(2));result=arg(0)
  elif name in ('WriteFile',):machine.mem_write(arg(3),struct.pack('<I',arg(2)));result=1;clean=20
  elif name.endswith('snprintf') or name=='sprintf':result=0
  else:raise ValueError(f'unhandled called import {dll}!{name}')
  machine.reg_write(UC_X86_REG_EAX,result);machine.reg_write(UC_X86_REG_ESP,sp+4+clean);machine.reg_write(UC_X86_REG_EIP,ret)
 uc.hook_add(UC_HOOK_CODE,hook)
 return entries,seen
def execute(path):
 uc=Uc(UC_ARCH_X86,UC_MODE_32);entries,seen=load_dll(uc,path);entry=entries['re0_adapter_selftest']
 # This adapter has no game-settings owner; the native gate supplies and exercises it.
 uc.mem_map(0xdcc000,0x1000)
 def read32(a):return struct.unpack('<I',bytes(uc.mem_read(a,4)))[0]
 stack=0x11f000;uc.mem_write(stack,struct.pack('<I',0x210000));uc.reg_write(UC_X86_REG_ESP,stack)
 uc.emu_start(entry,0x210000,count=2000000)
 if uc.reg_read(UC_X86_REG_EIP)!=0x210000:raise ValueError('adapter did not return within limit')
 result=uc.reg_read(UC_X86_REG_EAX)
 if result:raise ValueError(f'adapter synthetic selftest failed case {result}')
 if uc.reg_read(UC_X86_REG_ESP)!=stack+4:raise ValueError('adapter stack imbalance')
 return dict(evidence='synthetic-compiled-x86-adapter',result='pass',abi='thiscall originals; fastcall hooks; balanced stack',
  cases=['native call count/order','room ID/owner/region','quad and viewport','TLS restoration','closed-map clear','unsupported-region refusal','unknown-ID refusal','transparent sprite refusal'],called_imports=seen,game_executed=False)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--dll',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 report=execute(a.dll);a.output.write_text(json.dumps(report,indent=2)+'\n');print('Compiled x86 adapter: 8 synthetic cases passed; stack balanced')
