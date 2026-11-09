"""Curated key-item uses from private external item pages; targets are checked against each page's own room links."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TF='training-facility';L='laboratory';T='train';F='factory';P='treatment-plant';B='facility-basement'
# RE1 HD groups: a lock names the key at the locked room; a puzzle names the item where it gets used.
LOCKS={
 "Conductor's Key":[f'{T}-1f/conductors-office'],'Dining Car Key':[f'{T}-1f/dining-car'],'Blue Keycard':[f'{T}-1f/engine-carriage'],'Ice Pick':[f'{T}-2f/service-room'],
 'Breeding Room Key':[f'{L}-b1/breeding-room'],'Blue Leech Charm':[f'{L}-b2/marcuss-study'],'Green Leech Charm':[f'{L}-b1/morgue'],'Dial':[f'{L}-b2/machine-room-1f'],
 'Fire Key':[f'{TF}-1f/kitchen',f'{TF}-2f/assistant-directors-office'],'Water Key':[f'{TF}-2f/narrow-corridor-a'],'MO Disk':[f'{TF}-1f/training-facility-entrance',f'{TF}-2f/private-corridor',f'{TF}-3f/observatory-tower'],
 'Iron Needle':[f'{TF}-2f/private-study-room',f'{TF}-1f/west-wing-corridor'],'Handle':[f'{P}-b6/l-corridor'],'Keycard':[f'{P}-b9/fenced-area'],'Shaft Key (L)':[f'{P}-b9/storage'],'Shaft Key (R)':[f'{P}-b9/storage'],
}
PUZZLES={
 'Crank Handle':[f'{TF}-2f/main-library'],'Discipline Tablet':[f'{TF}-3f/observatory-tower'],'Obedience Tablet':[f'{TF}-3f/observatory-tower'],'Unity Tablet':[f'{TF}-3f/observatory-tower'],
 'Elevator Key':[f'{F}-b4/turntable-platform'],'Up Key':[f'{F}-1f/turntable-control-room'],'Hookshot':[f'{T}-1f/passenger-car-2',f'{L}-1f/church',f'{L}-b2/reference-room',f'{L}-b2/machine-room-1f'],
 'Input Regulator Coil':[f'{L}-b1/machine-room-2f'],'Output Regulator Coil':[f'{L}-b1/machine-room-2f'],'Iron Needle':[f'{TF}-3f/clock-room'],'MO Disk':[f'{TF}-2f/lecture-room'],'Magnetic Card':['train-1f/rear-carriage'],
 'Microfilm A':[f'{TF}-1f/projection-room'],'Microfilm B':[f'{TF}-1f/projection-room'],'Motherboard':[f'{P}-b7/cargo-control-room'],'Panel Opener':[f'{T}-1f/dining-car'],'Sterilizing Agent':[f'{L}-b1/leech-laboratory'],'Locker Key':[f'{B}-b3/training-room'],
 'Battery':[f'{TF}-1f/training-facility-entrance'],'Vise Handle':[f'{TF}-2f/maintenance-room'],
}
# Page names the facility only; the room comes from the sentence (lift outside the main entrance) or from where the vise's tablet is listed.
# Magnetic Card: the catalogue names the Engine Cab for the brakes; the card is used at the rear console (script tr0a, Gamepressure, Twinfinite).
INFERRED={('Magnetic Card','train-1f/rear-carriage'),('Battery',f'{TF}-1f/training-facility-entrance'),('Vise Handle',f'{TF}-2f/maintenance-room')}
def page_links(page):
 a=page.find('<h1');b=page.find('Category',a)
 if a<0 or b<0:raise ValueError('item page layout changed')
 return set(re.findall(r'href="/resident-evil-zero/maps/[^/"#]+/([^"#]+)"',page[a:b]))
def build(pages,slugs):
 uses=[]
 for kind,table in (('lock',LOCKS),('puzzle',PUZZLES)):
  for name,targets in sorted(table.items()):
   links=page_links((pages/(slugs[name]+'.html')).read_text())
   for target in targets:
    inferred=(name,target) in INFERRED
    if target not in links and not inferred:raise ValueError(f'{name}: {target} is not linked from its page')
    uses.append(dict(item=name,slug=slugs[name],kind=kind,place=target,inferred_from_text=inferred))
 return dict(schema_version=1,evidence='curated from external item pages',source='https://www.evilresource.com/resident-evil-zero/items',checked_on='2026-11-03',caveat='Static placement of requirements; lock and solved state are not read from the game.',uses=uses)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pages',type=Path,default=ROOT/'local/external/items');p.add_argument('--output',type=Path,default=ROOT/'data/item-uses.json');a=p.parse_args()
 contents=json.loads((ROOT/'data/room-contents.json').read_text());slugs={r['name']:r['slug'] for x in contents['places'] for r in x['contents']}
 d=build(a.pages,slugs);a.output.write_text(json.dumps(d,ensure_ascii=False,indent=1)+'\n');print(len(d['uses']),'item uses')
