"""Create explicitly synthetic full-floor placement reviews; never reads saves or launches the game."""
from pathlib import Path
import argparse,json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'emulator'))
from render import render
from annotations import replay

def rooms_place(index):
 from annotations import catalogue
 return catalogue()[0][index][6]
def build(game,out):
 native=json.loads((ROOT/'data/native-map.json').read_text());pieces=native['map_pieces'];regions={r['region']:r['region_index'] for r in native['native_regions']}
 out.mkdir(parents=True,exist_ok=True);reports=[]
 for floor in native['floors']:
  image,trace=render(game,floor['region'],floor['floor'])
  boxes={}
  for r in trace['drawn']:
   b=r['canvas_box'];prev=boxes.get(r['instance'],b);boxes[r['instance']]=[min(b[0],prev[0]),min(b[1],prev[1]),max(b[2],prev[2]),max(b[3],prev[3])]
  rows=[dict(index=i,box=boxes[p['id']]) for i,p in enumerate(pieces) if p['region']==floor['region'] and p['floor']==floor['floor'] and p['id'] in boxes]
  for english in [0,1]:
   capture=dict(schema_version=1,profile_sha256='67418c3a307b49e9bde8123df4cad1fa910f3a29adc3e4c0ba64eb96524bc14b',evidence='synthetic-resource-preview',region=regions[floor['region']],target=list(image.size),settings=dict(english=english,size=100,opacity=70),rooms=rows,obstacles=[])
   composite,report=replay(capture,image);stem=f'{floor["region"]}-{floor["floor"]}-'+('en' if english else 'ko')
   composite.save(out/(stem+'.png'));(out/(stem+'.json')).write_text(json.dumps(capture,indent=2)+'\n');reports.append(dict(scene=stem,**report))
 # Same op list as the ASI after each key, so toggled states are looked at before a live run.
 floor=next(f for f in native['floors'] if f['region']=='sh' and f['floor']=='2f')
 image,trace=render(game,floor['region'],floor['floor']);boxes={}
 for r in trace['drawn']:
  b=r['canvas_box'];prev=boxes.get(r['instance'],b);boxes[r['instance']]=[min(b[0],prev[0]),min(b[1],prev[1]),max(b[2],prev[2]),max(b[3],prev[3])]
 rows=[dict(index=i,box=boxes[p['id']]) for i,p in enumerate(pieces) if p['region']=='sh' and p['floor']=='2f' and p['id'] in boxes]
 for name,settings in [('default',{}),('all-off',dict(enabled=0)),('names-off',dict(names=0)),('locks-enemies-off',dict(contents=63-1-32)),('hard-english',dict(difficulty=2,english=1)),('room-selected',dict(selected=None))]:
  if 'selected' in settings:settings=dict(selected=rooms_place(rows[0]['index']))
  capture=dict(schema_version=1,profile_sha256='67418c3a307b49e9bde8123df4cad1fa910f3a29adc3e4c0ba64eb96524bc14b',evidence='synthetic-resource-preview',region=regions['sh'],target=list(image.size),settings=dict(dict(size=100,opacity=70,english=0),**settings),rows=None,rooms=rows,obstacles=[])
  replay(capture,image)[0].save(out/f'state-{name}.png')
 (ROOT/'verification/annotation-review.json').write_text(json.dumps(dict(evidence='synthetic-resource-preview',scenes=reports),indent=2)+'\n')
 print(f'Built {len(reports)} synthetic annotation scenes, no runtime/GPU claim')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 if a.output.resolve().is_relative_to(a.game.resolve()):p.error('output must be outside game')
 build(a.game,a.output)
