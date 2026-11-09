"""Compare game placement data with the external catalogue, item by item; writes a list, not a pass mark.

The catalogue has no coordinates, so this checks identity, room, difficulty, amount, height against its wording, condition wording against the game's condition byte, and doors.
It cannot confirm an x/z position, and it is one source.
"""
import argparse,collections,html,json,pickle,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for f in ('tools/extract','tools/inspect'):sys.path.insert(0,str(ROOT/f))
from event_disasm import Commands,decode,groups
from resources import Arc
from conditions import UNLOCK,CONDITIONAL,reward_rank
MODES={'33':'easy','11':'normal','32':'hard'}
# Game short names for what the catalogue spells out. Family names cover several specific keys.
ALIAS={"Conductor's Key":'Train Key','Dining Car Key':'Train Key','Fire Key':'Facility Key','Water Key':'Facility Key','Up Key':'Factory Key','Breeding Room Key':'Breeding Rm. Key','Green Leech Charm':'Gr. Leech Charm','Blue Leech Charm':'Bl. Leech Charm','Input Regulator Coil':'Input Reg. Coil','Output Regulator Coil':'Output Reg. Coil','1st Investigation Unit Notes':'First Investigation Unit Notes','Inmates List':'Correctional Institute Inmates List','Shaft Key (L)':'Shaft Key','Shaft Key (R)':'Shaft Key','Handgun Parts':'Handgun Parts'}
def base(name):
 s=re.sub(r'^(\d+|∞) ','',name)
 if not s.startswith('Shaft Key'):s=re.sub(r' \((?!Second)[^)]*\)$','',s)
 s={'Green Herbs':'Green Herb','Blue Herbs':'Blue Herb','First-Aid Sprays':'First-Aid Spray'}.get(s,s)
 return ALIAS.get(s,s)
def pack(name):
 """Expected amount per pickup from the catalogue wording: 'Handgun Ammo (1×15)' is 15, 'Gas Tank (×3)' is 3."""
 m=re.search(r'\((?:\d+)?×(\d+)%?\)$',name);return int(m[1]) if m else None
def rows_of(page):
 out=[]
 for mode,body in re.findall(r'<li data-gamemode="gm(\d+)">(.*?)</li>',page,re.S):
  title=re.search(r'<h\d class="h6[^"]*">(.*?)</h\d>',body,re.S);link=re.search(r'class="actions">\s*<a href="/resident-evil-zero/([a-z-]+)/',body);text=re.search(r'class="text">(.*?)</div>',body,re.S)
  if title and link and mode in MODES:out.append(dict(name=html.unescape(re.sub(r'<[^>]+>','',title[1])).strip(),kind=link[1],mode=MODES[mode],text=html.unescape(re.sub(r'<[^>]+>','',text[1])).strip() if text else ''))
 for r in out:r.update(conditional=bool(CONDITIONAL.search(r['text'])),reward_rank=reward_rank(r['text']))
 return out
HIGH=re.compile(r'\b(on|atop) (a |an |the |top of )*(\w+ )?(table|desk|shelf|shelves|counter|cabinet|bench|panel|bed|sink|chair|locker|box|crate|bar|piano|stand|dresser|barrel|machine|console)\b',re.I)
LOW=re.compile(r'\bon the floor\b|\bon the ground\b|\bfloor\b',re.I)
def check(game,image,pages,placements,contents,matches,native):
 pieces={p['id']:p for p in native['map_pieces']};rooms={}
 for c in matches['claims']:
  ids={pieces[p]['native_room_id'] for p in c['native_pieces']}
  for ext in [c['external_id'],*c.get('also_covers',[])]:rooms[ext]=ids
 game_rows=[(i,r) for i,r in enumerate(placements['rows']) if ('world' in r or 'script' in r) and r['category'] in('item','key','file')]
 status={};missing=[];amount_bad=[];height=collections.Counter();height_bad=[];stats={m:collections.Counter() for m in MODES.values()};conditional=[];conflicts=[];matched=set()
 for place in contents['places']:
  ids=rooms.get(place['id'],set());page=(pages/(place['id'].replace('/','__')+'.html')).read_text();ext=[r for r in rows_of(page) if r['kind'] in('items','weaponry','files','miscellaneous-objects') and r['name']!='Typewriter']
  for mode in MODES.values():
   pool=[(i,r) for i,r in game_rows if r['room'] in ids and mode in r['amount'] and (i,mode) not in status]
   for e in [x for x in ext if x['mode']==mode]:
    quantity=int(m[1]) if (m:=re.match(r'^(\d+) ',e['name'])) else 1
    for _ in range(quantity):
     name=base(e['name']);want=pack(e['name']);same=[(i,r) for i,r in pool if r['name_en']==name]
     better=[x for x in same if want is None or x[1]['amount'][mode]==want] or same
     if not better:missing.append(dict(place=place['id'],mode=mode,name=e['name'],conditional=e['conditional'],catalogue_rank=e['reward_rank'],wording=e['text']));stats[mode]['only_external']+=1;continue
     # A condition is part of the match: a reward row and an ordinary row of one name are different rows.
     i,r=([x for x in better if (x[1].get('condition',0) in UNLOCK)==e['conditional']] or better)[0];pool.remove((i,r));unlock=r.get('condition',0) in UNLOCK
     state='conditional' if unlock and e['conditional'] else 'condition-conflict' if unlock!=e['conditional'] else 'match'
     status[(i,mode)]=state;stats[mode][state]+=1;matched.add((e['name'],mode,e['text']))
     if unlock or e['conditional']:(conditional if state=='conditional' else conflicts).append(dict(place=place['id'],mode=mode,name=e['name'],index=i,condition=r.get('condition',0),catalogue_rank=e['reward_rank'],game_rank=UNLOCK[r['condition']][3] if unlock else None,wording=e['text'][:90]))
     if want is not None and r['amount'][mode]!=want:amount_bad.append(dict(place=place['id'],mode=mode,name=e['name'],game=r['amount'][mode]))
     y=r['world'][1] if 'world' in r else None;kind='low' if LOW.search(e['text']) else 'high' if HIGH.search(e['text']) else None
     if kind and y is not None:
      ok=(y<=15) if kind=='low' else (y>=15);height[(kind,ok)]+=1
      if not ok:height_bad.append(dict(place=place['id'],name=e['name'],y=round(y),wording=e['text'][:80]))
 # Why a row stayed external. The same wording matched under another floor's page of one physical room is a catalogue repeat, not a missing item;
 # 'Inside the X' comes out of an inventory item, with no script reference; anything else stays unresolved. Leech Hunter rewards keep their rank.
 for r in missing:
  r['class']='catalogue-repeat' if (r['name'],r['mode'],r['wording']) in matched else 'inside-item' if r['wording'].startswith('Inside the ') else 'reward' if r['catalogue_rank'] else 'unresolved'
 for i,r in game_rows:
  for mode in r['amount']:
   if (i,mode) not in status:
    stats[mode]['only_game']+=1
    if r.get('condition',0) in UNLOCK:conditional.append(dict(place=None,mode=mode,name=r['name_en'],index=i,room=r['room'],condition=r['condition'],catalogue_rank=None,game_rank=UNLOCK[r['condition']][3],wording=None))
 # Doors: every script door target should be a catalogue link of that room, and the other way round.
 commands=Commands(image);scene=game/'nativePC/arc/scene';room_place=collections.defaultdict(set)
 for ext,ids in rooms.items():
  for r in ids:room_place[r].add(ext)
 regions={'tr':0,'sh':36,'dm':86,'ch':99,'bt':132,'pl':141};links={p['id']:set(p['linked']) for p in contents['places']};door=collections.Counter();door_only_game=[]
 script_links=collections.defaultdict(set)
 for f in sorted(scene.glob('*.arc')):
  if not re.fullmatch(r'[a-z]{2}[0-9a-f]{2}',f.stem) or f.stem[:2] not in regions:continue
  room=regions[f.stem[:2]]+int(f.stem[2:],16);a=Arc(f.read_bytes())
  for m in a.members:
   if m.kind!=0x714ec77c:continue
   d=a.read(m)
   for (tag,off,_,_),end in groups(d):
    if not off:continue
    try:ops=decode(d,off,end,commands)
    except ValueError:continue
    for o in ops:
     if o[1]=='door':script_links[room].add(o[2][0])
 for room,targets in script_links.items():
  own=room_place.get(room,set())
  if not own:continue
  allowed={l for e in own for l in links.get(e,())}
  for t in targets:
   there=room_place.get(t,set())
   if not there:door['target_unmapped']+=1;continue
   if there&allowed:door['both']+=1
   else:
    door['only_script']+=1;door_only_game.append(dict(room=room,target=t,places=sorted(own)[:2],target_places=sorted(there)[:2]))
 flat=[dict(index=i,external={m:status.get((i,m),'game-only') for m in r['amount']}) for i,r in game_rows]
 return dict(schema_version=2,evidence='one external catalogue compared by room, name, difficulty, amount, wording and condition; no coordinates exist in it',source=contents['source'],
  by_difficulty={k:dict(v) for k,v in stats.items()},conditional=conditional,condition_conflicts=conflicts,only_external=missing,amount_mismatch=amount_bad,height={f'{k[0]}-{"ok" if k[1] else "conflict"}':v for k,v in height.items()},height_conflicts=height_bad,doors=dict(door),doors_only_in_script=door_only_game,rows=flat)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game',type=Path,required=True);p.add_argument('--analysis-image',type=Path,default=ROOT/'local/research/re0hd.analysis.bin');p.add_argument('--pages',type=Path,default=ROOT/'local/external/rooms');p.add_argument('--output',type=Path,default=ROOT/'verification/placement-crosscheck.json');a=p.parse_args()
 load=lambda n:json.loads((ROOT/'data'/n).read_text())
 r=check(a.game,a.analysis_image.read_bytes(),a.pages,load('placements.json'),load('room-contents.json'),load('room-matches.json'),load('native-map.json'))
 a.output.write_text(json.dumps(r,ensure_ascii=False,indent=1)+'\n')
 print(json.dumps({k:r[k] for k in('by_difficulty','height','doors')},ensure_ascii=False));print('amount mismatches',len(r['amount_mismatch']),'only external',len(r['only_external']),'conditional',len(r['conditional']),'condition conflicts',len(r['condition_conflicts']))
