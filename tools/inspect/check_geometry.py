"""Compare actual native sprite-quad instructions with shared C; no game process/GPU."""
import argparse
import json
from pathlib import Path
import random
import struct
import sys
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32
from unicorn.x86_const import UC_X86_REG_ESP,UC_X86_REG_ECX,UC_X86_REG_EIP
from verify_native import verify
from inspect_game import pe_info

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'emulator'))
from core import Core


def machine(image,profile,pages):
    uc=Uc(UC_ARCH_X86,UC_MODE_32)
    for address in pages:
        uc.mem_map(address,0x1000)
        rva=address-profile['image_base']
        section=next(s for s in profile['sections'] if s['rva']<=rva and rva+0x1000<=s['rva']+s['raw_size'])
        at=section['raw_offset']+rva-section['rva'];uc.mem_write(address,image[at:at+0x1000])
    uc.mem_map(0x100000,0x10000);uc.mem_map(0x200000,0x10000);uc.mem_map(0x1000,0x1000)
    return uc


def native_quad(image,profile,width,height,anchor,flip_y,matrix):
    uc=machine(image,profile,[0x889000,0x892000,0xcba000,0xcbf000,0xcb4000,0xcbd000])
    owner,output,size,stack=0x200000,0x202000,0x203000,0x108000
    uc.mem_write(owner+0x10,struct.pack('<16f',*matrix))
    uc.mem_write(owner+0x54,struct.pack('<I',(1<<22) if flip_y else 0))
    uc.mem_write(owner+0xa0,struct.pack('<I',anchor))
    uc.mem_write(size,struct.pack('<4f',width,height,0,0))
    uc.mem_write(stack,struct.pack('<IIIf',0x1000,output,size,1.0))
    uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,owner)
    uc.emu_start(0x889300,0x1000,count=3000)
    if uc.reg_read(UC_X86_REG_EIP)!=0x1000:raise ValueError('native quad did not return')
    return bytes(uc.mem_read(output,64))


def native_uv(image,profile,rect,sampler):
    uc=machine(image,profile,[0x891000,0x892000,0xcba000,0xcbf000,0xcb4000])
    uc.mem_map(0xe2d000,0x1000)
    owner,render_args,sampler_arg,renderer,vertices,stack=0x200000,0x202000,0x203000,0x204000,0x208000,0x108000
    uc.mem_write(0xe2daa4,struct.pack('<I',renderer))
    uc.mem_write(renderer+0x98,struct.pack('<I',7));uc.mem_write(renderer+0xb0,struct.pack('<I',vertices))
    uc.mem_write(owner+0xcc,struct.pack('<I',0x03000000))
    uc.mem_write(owner+0xa0,struct.pack('<I',5));uc.mem_write(owner+0xc0,struct.pack('<2f',60,48))
    uc.mem_write(owner+0xec,struct.pack('<4f',*rect))
    uc.mem_write(sampler_arg,struct.pack('<I',sampler))
    uc.mem_write(stack,struct.pack('<3I',0x1000,render_args,sampler_arg))
    uc.reg_write(UC_X86_REG_ESP,stack);uc.reg_write(UC_X86_REG_ECX,owner)
    uc.emu_start(0x8918d0,0x891b4e,count=5000)
    if uc.reg_read(UC_X86_REG_EIP)!=0x891b4e:raise ValueError('native vertex emitter did not reach bounded stop')
    return b''.join(bytes(uc.mem_read(vertices+i*24+16,8)) for i in range(4))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exe',type=Path,required=True);p.add_argument('--analysis-image',type=Path,required=True)
    p.add_argument('--core',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.resolve().is_relative_to(a.exe.resolve().parent):p.error('report must be outside game')
    original,image=a.exe.read_bytes(),a.analysis_image.read_bytes();evidence=verify(original,image)
    profile=pe_info(original);core=Core(a.core)
    matrices=[
        [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1],
        [3,0,0,0,0,3,0,0,0,0,1,0,640,360,0,1],
        [0,1,0,0,-1,0,0,0,0,0,1,0,12.5,-31.25,8,1],
    ]
    cases=[]
    for w,h in [(60,48),(122,48),(1.25,10.5)]:
        for anchor in [0,1,2,4,5,6,8,9,10,0xff5]:
            for flip in [0,1]:
                for index,matrix in enumerate(matrices):
                    native=native_quad(image,profile,w,h,anchor,flip,matrix)
                    c=struct.pack('<16f',*core.quad(w,h,anchor,flip,matrix))
                    if native!=c:raise ValueError(f'native/C quad mismatch {w,h,anchor,flip,index}: {struct.unpack("<16f",native)} != {struct.unpack("<16f",c)}')
                    cases.append(dict(size=[w,h],anchor=anchor,flip_y=flip,matrix=index))
    # Shared code must not be stricter than native: any packed field with a valid low nibble is drawn by the game.
    rng=random.Random(0x7e0)
    for _ in range(64):
        anchor=(rng.getrandbits(28)<<4)|rng.choice([0,1,2,4,5,6,8,9,10])
        matrix=[1,0,0,0,0,1,0,0,0,0,1,0,300,200,0,1]
        native=native_quad(image,profile,172,48,anchor,0,matrix);c=struct.pack('<16f',*core.quad(172,48,anchor,0,matrix))
        if native!=c:raise ValueError(f'native/C quad mismatch on packed anchor {anchor:#x}')
        cases.append(dict(size=[172,48],anchor=anchor,flip_y=0,matrix='packed-field-sample'))
    uv_cases=[]
    for rect in [(0,0,60,48),(170,192,336,240),(10.25,20.5,40.75,50.5),(60,0,0,48),(0,48,60,0)]:
        for sampler in [0,1,2]:
            native=native_uv(image,profile,rect,sampler)
            shared=struct.pack('<8f',*core.uv(rect,sampler))
            if native!=shared:raise ValueError(f'native/C UV mismatch: {rect,sampler}')
            uv_cases.append(dict(rect=rect,sampler=sampler))
    report=dict(evidence='bounded-original-x86-vs-shared-C',original_sha256=evidence['original_sha256'],
                analysis_sha256=evidence['analysis_sha256'],functions=['0x00889300','0x00892680','0x008918d0'],
                comparisons='bit-exact float32 quad xyz0',scope='unit expansion; supplied affine matrix; no native parent-matrix construction or GPU',cases=cases,uv_cases=uv_cases)
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(f'Native/C geometry: {len(cases)} quad and {len(uv_cases)} UV cases match bit-exactly; no game run')


if __name__=='__main__':main()
