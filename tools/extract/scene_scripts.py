"""Inventory main-game scene script groups without interpreting tags as items or doors."""
import argparse
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/inspect'))
from resources import Arc,event_script_index,resource_kind,sha256
sys.path.insert(0,str(ROOT/'tools/extract'))
from map_data import native_room_index


def export(game):
    exe=(game/'re0hd.exe').read_bytes()
    regions=native_room_index(exe)
    kinds={name:resource_kind(name) for name in ['rSceneInfo','rEventScript','rEventCollision','rCollision','rCutScrParamPackage']}
    for name in kinds:
        if name.encode()+b'\0' not in exe:raise ValueError('native resource class name missing')
    rooms=[];seen=set()
    scene_dir=game/'nativePC/arc/scene'
    for region in regions:
        for local in range(region['count']):
            key=region['region']+f'{local:02x}'
            path=scene_dir/(key+'.arc');row=dict(id=key,native_room_id=region['base']+local,scene_present=path.exists())
            if path.exists():
                seen.add(path.name);data=path.read_bytes();arc=Arc(data)
                row.update(archive_sha256=sha256(data),scripts=[])
                for member in arc.members:
                    if member.kind!=kinds['rEventScript']:continue
                    payload=arc.read(member)
                    row['scripts'].append(dict(resource=member.name,sha256=sha256(payload),size=len(payload),**event_script_index(payload)))
            rooms.append(row)
    return dict(schema_version=1,evidence='native-typed-structural-index',exe_sha256=sha256(exe),
                resource_classes={name:f'{value:08x}' for name,value in kinds.items()},rooms=rooms,
                unindexed_scene_archives=sorted(p.name for p in scene_dir.glob('*.arc') if p.name not in seen),
                caveats=['Group tags and extra words are not interpreted as item IDs, spawn predicates or door links',
                         'A zero payload offset is preserved as unresolved, not an empty item/door',
                         'Absent scene archives can correspond to unused native room slots',
                         'Unindexed scene archives require separate mode/usage analysis'])


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if a.output.resolve().is_relative_to(a.game.resolve()):p.error('output must be outside game')
    report=export(a.game);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(report,indent=2)+'\n')
    present=[r for r in report['rooms'] if r['scene_present']]
    scripts=[s for r in present for s in r['scripts']]
    print(f"Scene index: {len(present)}/{len(report['rooms'])} slots have archives; {len(scripts)} scripts, {sum(len(s['groups']) for s in scripts)} unresolved groups")


if __name__=='__main__':main()
