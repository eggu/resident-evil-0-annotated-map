"""Classify every loc2 condition byte from its writers: native constant writes and all event scripts. Writes a list; what is proven is stated per class.

fresh-unlock: only native 0x59d2a0 from Leech Hunter reward bits; hidden. native-start: set by 0x59d2a0 in both start paths. opening-block: set by the one-shot
script groups tr07/tr1f group 7, so on once those ran; when they run relative to first reaching a room is inferred. script-later: other script writers only. no-writer: none found.
"""
import argparse,collections,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for f in ('tools/extract','tools/inspect'):sys.path.insert(0,str(ROOT/f))
from arrange import parse
from event_disasm import Commands,decode,groups
from resources import Arc
from conditions import UNLOCK,FLAG_BASE
TABLES={'easy':'loctbl0000','normal':'loctbl0100','hard':'loctbl0200'}
NATIVE_START={35:0x59d2d9}
OPENING={('tr07',7),('tr1f',7)}
def script_writers(game,commands):
 """(condition byte) -> writes. SetEnemyFlag adds 0x312 (0x577970); FlagSet takes the flag itself."""
 out=collections.defaultdict(list);seen=undecoded=0
 for f in sorted((game/'nativePC/arc/scene').glob('*.arc')):
  a=Arc(f.read_bytes())
  for m in a.members:
   if m.kind!=0x714ec77c:continue
   d=a.read(m)
   for n,((tag,off,x,_),end) in enumerate(groups(d)):
    if not off:continue
    try:ops=decode(d,off,end,commands)
    except ValueError:undecoded+=1;continue
    seen+=1
    for _,name,args in ops:
     byte=args[0] if name=='SetEnemyFlag' else args[0]-FLAG_BASE if name in('FlagSet','FlagSetMB') else None
     if byte is not None and 0<byte<=255:out[byte].append(dict(scene=f.stem,group=n,tag=tag,x=x,value=args[1]))
 return out,seen,undecoded
def classify(byte,writes):
 if byte==0:return 'always'
 if byte in UNLOCK:return 'fresh-unlock' if not writes else 'unlock-with-script-writer'
 if byte in NATIVE_START:return 'native-start'
 if any((w['scene'],w['group']) in OPENING and w['value'] for w in writes):return 'opening-block'
 return 'script-later' if any(w['value'] for w in writes) else 'no-writer'
def build(game,image):
 commands=Commands(image);writers,seen,undecoded=script_writers(game,commands)
 arc=Arc((game/'nativePC/arc/arrange/loctbl.arc').read_bytes());rows=[]
 for mode,table in TABLES.items():
  for rm in parse(arc.read(next(m for m in arc.members if m.name.endswith(table)))):
   for r in rm['records']:rows.append(dict(mode=mode,room=rm['room'],kind=r['kind'],item=r['item'],byte=r['a'][0],amount=r['amount']))
 by=collections.defaultdict(list)
 for r in rows:by[r['byte']].append(r)
 values=[]
 for byte in sorted(by):
  w=writers.get(byte,[]);normal=[r for r in by[byte] if r['mode']=='normal']
  values.append(dict(condition=byte,flag=FLAG_BASE+byte,cls=classify(byte,w),normal_item_rows=sum(r['kind'] in(0x71,0x78) for r in normal),normal_enemy_rows=sum(r['kind']<0x60 for r in normal),normal_other_rows=sum(r['kind']>=0x60 and r['kind'] not in(0x71,0x78) for r in normal),rooms=sorted({r['room'] for r in normal}),set_by=sorted({f"{x['scene']}:{x['group']}" for x in w if x['value']}),cleared_by=sorted({f"{x['scene']}:{x['group']}" for x in w if not x['value']})))
 return dict(schema_version=1,evidence='static: native code and event scripts; no run of the game',script_groups_decoded=seen,script_groups_undecoded=undecoded,values=values)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game',type=Path,required=True);p.add_argument('--analysis-image',type=Path,default=ROOT/'local/research/re0hd.analysis.bin');p.add_argument('--output',type=Path,default=ROOT/'verification/arrange-conditions.json');a=p.parse_args()
 r=build(a.game,a.analysis_image.read_bytes());a.output.write_text(json.dumps(r,ensure_ascii=False,indent=1)+'\n')
 c=collections.Counter();
 for v in r['values']:
  c[v['cls'],'item']+=v['normal_item_rows'];c[v['cls'],'enemy']+=v['normal_enemy_rows'];c[v['cls'],'other']+=v['normal_other_rows']
 print(sorted(c.items()),r['script_groups_decoded'],r['script_groups_undecoded'])
