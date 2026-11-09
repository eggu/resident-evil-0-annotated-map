"""Bounded original-x86 draw contracts: instance animation dispatch and viewport constants."""
from pathlib import Path
import argparse,json,struct,sys
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EIP
from check_geometry import machine
from inspect_game import pe_info
from verify_native import verify
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'emulator'))
from core import Core

def instance(image,profile):
 uc=machine(image,profile,[0x87c000,0x87d000,0x892000])
 owner,args,anim,sp=0x200000,0x202000,0x204000,0x108000
 uc.mem_write(args+0xc,struct.pack('<I',2));uc.mem_write(owner+0xec,struct.pack('<I',anim));uc.mem_write(sp,struct.pack('<II',0x1000,args))
 uc.reg_write(UC_X86_REG_ESP,sp);uc.reg_write(UC_X86_REG_ECX,owner);seen=[]
 objects, obj, table=0x205000,0x206000,0x207000
 uc.mem_write(anim+0x80,struct.pack('<I',objects))
 uc.mem_write(objects,struct.pack('<4I',0,obj,2,0))
 uc.mem_write(obj,struct.pack('<I',table))
 uc.mem_write(table+0x2c,struct.pack('<2I',0x892ff0,0x892ff8))
 def hook(u,a,size,_):
  if a==0x892ce0:
   assert u.reg_read(UC_X86_REG_ECX)==anim
   seen.append('animation');return
  if a not in (0x892ff0,0x892ff8):return
  p=u.reg_read(UC_X86_REG_ESP);ret,arg=struct.unpack('<II',bytes(u.mem_read(p,8)))
  assert u.reg_read(UC_X86_REG_ECX)==obj and arg==args
  seen.append('sprite-prepare' if a==0x892ff0 else 'sprite-draw')
  u.reg_write(UC_X86_REG_ESP,p+8);u.reg_write(UC_X86_REG_EIP,ret)
 uc.hook_add(UC_HOOK_CODE,hook);uc.emu_start(0x87cc40,0x1000,count=5000)
 assert seen==['animation','sprite-prepare','sprite-draw'] and uc.reg_read(UC_X86_REG_ESP)==sp+8
 return dict(animation='instance+0xec',arguments='same render-argument pointer',calls=seen,stack='ret 4',result='pass')

def viewport(image,profile,W,H,origin,scale,adjust):
 uc=machine(image,profile,[0x883000,0xdc1000,0xcba000,0xcb4000,0xcc1000])
 uc.mem_map(0xe2d000,0x1000)
 owner,res,args,renderer,info,meta,out,sp=0x200000,0x201000,0x202000,0x204000,0x206000,0x207000,0x208000,0x108000
 uc.mem_write(owner+0x40,struct.pack('<2f',*origin));uc.mem_write(owner+0x60,struct.pack('<2f',*scale))
 uc.mem_write(owner+0xf0,struct.pack('<I',res));uc.mem_write(owner+0x148,struct.pack('<I',4 if adjust else 0))
 uc.mem_write(res+0x70,struct.pack('<I',2));uc.mem_write(res+0x78,struct.pack('<2I',1280,720))
 uc.mem_write(args+4,struct.pack('<I',renderer));uc.mem_write(renderer+0xbc,struct.pack('<4I',0,0,W,H))
 uc.mem_write(renderer+8,struct.pack('<I',info));uc.mem_write(info+0xb14,struct.pack('<I',meta));uc.mem_write(meta+0x18,struct.pack('<H',4))
 uc.mem_write(renderer+0x14,struct.pack('<2I',out,out+256));uc.mem_write(sp,struct.pack('<II',0x1000,args))
 uc.reg_write(UC_X86_REG_ESP,sp);uc.reg_write(UC_X86_REG_ECX,owner)
 uc.emu_start(0x883090,0x883320,count=10000)
 assert uc.reg_read(UC_X86_REG_EIP)==0x883320
 return struct.unpack('<4f',bytes(uc.mem_read(args+0xb8,16))),struct.unpack('<4f',bytes(uc.mem_read(out,16)))

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--exe',type=Path,required=True);p.add_argument('--analysis-image',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 image=a.analysis_image.read_bytes();evidence=verify(a.exe.read_bytes(),image);profile=pe_info(image);core=Core();cases=[]
 for W,H in [(1280,720),(1920,1080),(1024,768),(3440,1440)]:
  for adjust in [False,True]:
   for origin,scale in [((0,0),(1,1)),((120,50),(.5,2)),((-20,310),(3,3))]:
    view,shader=viewport(image,profile,W,H,origin,scale,adjust)
    # Compare screen coordinates against native shader constants, independently of direct projection.
    quad=core.quad(80,24,5,0,[1,0,0,0,0,1,0,0,0,0,1,0,640,360,0,1])
    box=core.project(quad,view)
    points=[((shader[0]*quad[i]+shader[2]+1)*W/2, (1-(shader[1]*quad[i+1]+shader[3]))*H/2) for i in range(0,16,4)]
    expected=(min(x for x,y in points),min(y for x,y in points),max(x for x,y in points),max(y for x,y in points))
    error=max(abs(x-y) for x,y in zip(box,expected));assert error<.001,(box,expected,error)
    cases.append(dict(size=[W,H],resolution_adjust=adjust,origin=origin,scale=scale,max_pixel_error=error))
 report=dict(evidence='bounded-original-x86-draw-contract',original_sha256=evidence['original_sha256'],instance_dispatch=instance(image,profile),viewport_cases=cases,
  scope='native instance animation dispatch; GUI viewport shader constants vs C projection; no native instance-scissor/GPU/final composition validation')
 a.output.write_text(json.dumps(report,indent=2)+'\n');print(f'Native draw route: instance dispatch and {len(cases)} viewport cases passed')
if __name__=='__main__':main()
