"""Verify bounded native evidence against a private analysis-only image; never patch game files."""
import argparse
import json
from pathlib import Path
import struct
from resources import sha256, unpack
from inspect_game import pe_info

ORIGINAL='67418c3a307b49e9bde8123df4cad1fa910f3a29adc3e4c0ba64eb96524bc14b'
ANALYSIS='ee00723d5dc55781e31d14977f77b1a7d6bbe68ace06b6eb455b3744e2e7e7a2'
SITES=[
    (0x5aa09d,'80bd77020000','fade update tests current alpha at +0x277'),
    (0x5aa1c6,'8d9574020000','fade update writes current colour at +0x274'),
    (0x56aa02,'8b0da4bedc00','fade owner singleton at 0xdcbea4'),
    (0x410c65,'8d8e12030000','spawn gate tests flag 0x312+condition byte'),
    (0x59b8d0,'8bd10fb74c24048bc1c1e80583e11f8b448220','flag test indexes the bit array at owner+0x20'),
    (0xcdc6a8,'90308800','uGUIMap draw vtable slot +0x58 points to 0x883090'),
    (0xd25478,'40cc8700','cGUIInstAnimation vtable 0xd25448 slot +0x30 points to 0x87cc40'),
    (0x8753c6,'c7064854d200','cGUIInstAnimation constructor installs vtable 0xd25448'),
    (0x87d535,'397904','GUI instance lookup compares resource ID at +4'),
    (0x6021c0,'c74500c05fce00','renderer subclass installs vtable 0xce5fc0 over base sRender'),
    (0xd26168,'e00a8900','GUI sprite draw vtable slot +0x30 points to 0x890ae0'),
    (0x5b2c3f,'c70650c6cd00','uGUIMap instance vtable is 0xcdc650'),
    (0x5b4e0c,'8b837c020000','map update uses phase at owner+0x27c'),
    (0x5b5008,'8b8578020000578b5844','map uses owner+0x278 state then region +0x44'),
    (0x87ccf5,'8b466c8b8048010000','GUI instance owner at +0x6c'),
    (0x87d0ef,'8b8eec00000085c9740657','instance draw dispatches its animation at +0xec'),
    (0x8832f7,'8b4508f30f10442438','native draw writes GUI viewport arguments +0xb8..+0xc4'),
    (0x71c448,'893d0cd4e200','sRender constructor publishes singleton at 0xe2d40c'),
    (0x71c2a3,'c70778b2d100','sRender instance vtable is 0xd1b278'),
    (0x7205cb,'8bbb98000000','sRender draw uses device at owner+0x98'),
    (0x7206bf,'8b0757ff90a8000000','sRender calls D3D9 EndScene at device vtable+0xa8'),
    (0x57d123,'6a0c8d4c241089436c','event-script loader skips 12 bytes after big-endian count'),
    (0x57d140,'8d4c240c83fe20','event-script loader retains at most 32 four-word slots'),
    (0x68455a,'8bc28bcac1e910','event-script u32 reader swaps byte order'),
    (0x61a260,'8b4424048b0485700bdb0003442408','global room ID = region base plus local room index'),
    (0x61a500,'8b442404b90b0000003bc10f47c18b04851011db00','region name lookup from 12-entry table with out-of-range sentinel'),
    (0x5bd6f3,'686ce1cd0068dcd9e200','maploc archive path and resource manager argument'),
    (0x5bd6fd,'ff5030898688000000','archive load result stored at owner +0x88'),
    (0x885e8c,'8b82a4000000','GUI relocation reads animation table at header +0xa4'),
    (0x886213,'8b43688b8004010000014608','GUI property names use string pool at header +0x104'),
    (0x886275,'4783c610','GUI static property stride 16 bytes'),
    (0x88645d,'0fb64ff0','GUI object property count is low byte of packed field'),
    (0x885ab7,'3930740a4283c018','animation lookup compares ID and advances 24 bytes'),
    (0x5b4a3c,'6838c7cd00','map instance formatted resource name argument'),
]


def verify(original,analysis):
    if sha256(original)!=ORIGINAL or sha256(analysis)!=ANALYSIS:
        raise ValueError('unsupported original or analysis image hash')
    pe=pe_info(original)
    def offset(address):
        rva=address-pe['image_base']
        for s in pe['sections']:
            if s['rva']<=rva<s['rva']+s['raw_size']:
                return s['raw_offset']+rva-s['rva']
        raise ValueError('address outside file-backed sections')
    # Require all differences to stay in .text; no rebuilt EXE/entry point is accepted.
    text=next(s for s in pe['sections'] if s['name']=='.text')
    lo,hi=text['raw_offset'],text['raw_offset']+text['raw_size']
    if len(original)!=len(analysis) or original[:lo]!=analysis[:lo] or original[hi:]!=analysis[hi:]:
        raise ValueError('analysis changed bytes outside .text')
    sites=[]
    for address,signature,claim in SITES:
        expected=bytes.fromhex(signature);at=offset(address)
        actual=analysis[at:at+len(expected)]
        if actual!=expected:
            raise ValueError(f'native evidence signature mismatch at {address:#x}: {actual.hex()}')
        sites.append(dict(address=f'0x{address:08x}',bytes=signature,claim=claim))
    for address,text in [(0xcde16c,b'arc\\map\\maploc\0'),(0xcdc738,b'i_%2s%02x%1x%1d\0')]:
        at=offset(address)
        if analysis[at:at+len(text)]!=text:raise ValueError('resource name string mismatch')
    return dict(evidence='static-byte-checked',original_sha256=ORIGINAL,analysis_sha256=ANALYSIS,
                installed_files_modified=False,sites=sites)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exe',type=Path,required=True);p.add_argument('--analysis-image',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.resolve().is_relative_to(a.exe.resolve().parent):p.error('output must be outside game')
    report=verify(a.exe.read_bytes(),a.analysis_image.read_bytes())
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(f"Verified {len(report['sites'])} bounded native signatures; no runtime claim")


if __name__=='__main__':main()
