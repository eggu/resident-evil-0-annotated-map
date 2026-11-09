"""Execute the bounded original x86 map-zoom method under Unicorn and compare C setter values.

External native setter calls are intercepted. This is not a whole-game/GPU emulator.
"""
import argparse
import json
from pathlib import Path
import struct
import sys
from unicorn import Uc, UC_ARCH_X86, UC_MODE_32, UC_HOOK_CODE
from unicorn.x86_const import UC_X86_REG_ESP, UC_X86_REG_ECX, UC_X86_REG_EIP
from verify_native import verify
from inspect_game import pe_info

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'emulator'))
from core import Core

SETTERS={0x880a20:'scale_x',0x880a50:'scale_y',0x880610:'x',0x880640:'y'}


def native_transform(image,profile,progress,focus,sparse=False):
    def readva(address,size):
        rva=address-profile['image_base']
        for s in profile['sections']:
            if s['rva']<=rva and rva+size<=s['rva']+s['raw_size']:
                at=s['raw_offset']+rva-s['rva'];return image[at:at+size]
        raise ValueError('native evidence address outside file')
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    for address in [0x5b5000,0xcb4000,0xcba000,0xcbf000,0xcdc000]:
        uc.mem_map(address,0x1000);uc.mem_write(address,readva(address,0x1000))
    uc.mem_map(0x880000,0x1000)
    uc.mem_map(0x100000,0x10000);uc.mem_map(0x200000,0x10000)
    uc.mem_map(0x1000,0x1000)
    owner,state,stack=0x200000,0x204000,0x108000
    uc.mem_write(owner+0x278,struct.pack('<I',state))
    uc.mem_write(state+0x5c,struct.pack('<2f',*focus))
    objects=[]
    for index in range(24):
        pointer=0 if sparse and index%3==0 else 0x206000+index*32
        uc.mem_write(owner+0x2a8+index*4,struct.pack('<I',pointer))
        if pointer:objects.append(pointer)
    uc.mem_write(stack,struct.pack('<If',0x1000,progress))
    uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,owner)
    seen={pointer:{} for pointer in objects}
    def hook(machine,address,size,_):
        if address not in SETTERS:return
        sp=machine.reg_read(UC_X86_REG_ESP)
        ret,value=struct.unpack('<I4s',bytes(machine.mem_read(sp,8)))
        this=machine.reg_read(UC_X86_REG_ECX)
        if this not in seen:raise ValueError('native called setter on unknown instance')
        seen[this][SETTERS[address]]=value.hex()
        machine.reg_write(UC_X86_REG_ESP,sp+8);machine.reg_write(UC_X86_REG_EIP,ret)
    uc.hook_add(UC_HOOK_CODE,hook)
    uc.emu_start(0x5b5320,0x1000,count=10000)
    if uc.reg_read(UC_X86_REG_EIP)!=0x1000:raise ValueError('native method did not return within instruction limit')
    return seen


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exe',type=Path,required=True);p.add_argument('--analysis-image',type=Path,required=True)
    p.add_argument('--core',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.resolve().is_relative_to(a.exe.resolve().parent):p.error('report must be outside game')
    original,image=a.exe.read_bytes(),a.analysis_image.read_bytes();evidence=verify(original,image)
    profile=pe_info(original);core=Core(a.core)
    cases=[]
    for progress in [0,1e-9,0.125,0.25,0.5,0.75,1]:
        for focus in [(640,360),(240,363),(1050,355),(-120,960)]:
            for sparse in [False,True]:
                expected=core.transform(progress,focus)
                f=lambda value:struct.pack('<f',value).hex()
                expected=dict(scale_x=f(expected.scale),scale_y=f(expected.scale),x=f(expected.translate_x),y=f(expected.translate_y))
                seen=native_transform(image,profile,progress,focus,sparse)
                if any(value!=expected for value in seen.values()):
                    raise ValueError(f'native/C transform mismatch: {progress}, {focus}, {sparse}, {seen}, {expected}')
                cases.append(dict(progress=progress,focus=focus,sparse=sparse,instances=len(seen)))
    report=dict(evidence='bounded-original-x86-vs-shared-C',original_sha256=evidence['original_sha256'],
                analysis_sha256=evidence['analysis_sha256'],function='0x005b5320',
                comparisons='bit-exact float32 setter values',cases=cases,
                scope='native GUI scale/translation setters only; viewport, clipping, input and GPU are excluded')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(f'Native/C zoom: {len(cases)} cases match bit-exact setter values; no game run')


if __name__=='__main__':main()
