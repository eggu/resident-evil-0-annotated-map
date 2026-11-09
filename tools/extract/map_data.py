"""Export native location metadata; this is not a verified room/door gameplay database."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'emulator'))
from render import load_scene, descendants
from resources import Arc, mloc, sha256, unpack
from inspect_game import pe_info
from verify_native import ORIGINAL


def native_room_index(exe):
    if sha256(exe)!=ORIGINAL:
        raise ValueError('native room table is tied to the inspected EXE hash')
    profile=pe_info(exe)
    def offset(address):
        rva=address-profile['image_base']
        for section in profile['sections']:
            if section['rva']<=rva<section['rva']+section['raw_size']:
                return section['raw_offset']+rva-section['rva']
        raise ValueError('native room table reference outside image')
    rows=[]
    for index in range(6):
        pointer=unpack(exe,'<I',offset(0xdb1110+index*4))[0]
        at=offset(pointer);end=exe.find(b'\0',at,at+8)
        if end<0:raise ValueError('unterminated native region prefix')
        prefix=exe[at:end].decode('ascii')
        if prefix!=['tr','sh','dm','ch','bt','pl'][index]:raise ValueError('unexpected native main-game region order')
        start=unpack(exe,'<I',offset(0xdb0b70+index*4))[0]
        stop=unpack(exe,'<I',offset(0xdb0b70+(index+1)*4))[0]
        if stop<=start or stop-start>256:raise ValueError('invalid native room range')
        rows.append(dict(region=prefix,region_index=index,base=start,count=stop-start,
                         evidence=dict(lookup='0x0061a260',base_table='0x00db0b70',prefix_table='0x00db1110')))
    return rows


def export(game):
    path=game/'nativePC/arc/map/maploc.arc'
    raw=path.read_bytes();arc=Arc(raw)
    regions=native_room_index((game/'re0hd.exe').read_bytes())
    room_ids={r['region']+f'{local:02x}':r['base']+local for r in regions for local in range(r['count'])}
    records=[]
    for m in arc.members:
        if m.kind!=0x44c8ac26:raise ValueError('unexpected maploc resource kind')
        data=arc.read(m)
        name=m.name.split('\\')[-1]
        if name not in room_ids:raise ValueError('maploc member outside native room table')
        records.append(dict(id=name,native_room_id=room_ids[name],resource=m.name,sha256=sha256(data),location_bytes=mloc(data)))
    if {r['id'] for r in records}!=set(room_ids):raise ValueError('native room index and maploc coverage differ')
    sources=[dict(file='nativePC/arc/map/maploc.arc',sha256=sha256(raw))]
    pieces=[];doors=[];floors=[]
    for region in ['tr','sh','dm','ch','bt','pl']:
        _,gui,source=load_scene(game,region);sources.append(source)
        for root in gui.instances:
            if not root['name'].startswith('Null_'+region):continue
            is_door=root['name'].endswith('_door')
            floor=root['name'][len('Null_'+region):].removesuffix('_door')
            if not is_door:floors.append(dict(region=region,floor=floor,group=root['name']))
            for node,parents in descendants(gui.instances,root['index']):
                if not node['name'].startswith('i_'):continue
                props=node['properties']
                row=dict(id=node['name'],region=region,floor=floor,gui_member=source['member'],
                         instance_index=node['index'],gui_id=node['raw'][0],floor_gui_id=root['raw'][0],properties=props,
                         parent_chain=[n['name'] for n in parents])
                if is_door:
                    row['gameplay_connection']=None
                    doors.append(row);continue
                match=re.fullmatch(r'i_([a-z]{2})([0-9a-f]{2})([0-9a-f])([0-9])',node['name'])
                row['encoded_identity']=dict(region=match[1],room_hex=match[2],location_hex=match[3],section_digit=match[4]) if match else None
                row['native_room_id']=room_ids[match[1]+match[2]] if match else None
                row['external_match']=None
                pieces.append(row)
    return dict(schema_version=1,evidence='static-resource-metadata',sources=sources,
                caveats=['mloc bytes are not labelled as floor IDs','map pieces are not counted as unique gameplay rooms',
                         'door instances are drawing placeholders, not verified connections',
                         'static GUI visibility is not save-state eligibility'],
                native_regions=regions,floors=floors,location_records=records,map_pieces=pieces,door_instances=doors)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--game',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    if a.output.resolve().is_relative_to(a.game.resolve()):p.error('output must be outside game')
    result=export(a.game)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(f"Exported {len(result['location_records'])} mloc records, {len(result['floors'])} floors, {len(result['map_pieces'])} pieces, {len(result['door_instances'])} door drawing instances")


if __name__=='__main__':main()
