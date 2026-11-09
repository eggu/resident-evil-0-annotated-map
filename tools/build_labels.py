"""Rasterize project labels; no game resources or font binaries enter the package."""
from pathlib import Path
import argparse,json,hashlib,math,re,sys
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/extract'))
from conditions import catalogue_condition
FONT=Path(__file__).resolve().parents[1]/'fonts/Pretendard-Medium.otf' # SIL OFL 1.1; see fonts/Pretendard-LICENSE.txt
# Category ids (data order): locks, key items, files/maps, puzzles, items, enemies, events. The legend lists events after puzzles (frame.c legend_category); badges follow the ids.
CATEGORIES='LKFPIEV'
PREFIX={0:'★',1:'◇',2:'□',3:'◆'}
RECOVERY=('Herb','First-Aid','Ink Ribbon','Gas Tank','Empty Bottle')
# Text and sizes follow the RE1 HD legend rasters (src/labels.h).
TITLE=('지도 메모','Map Notes')
# One hint format in both panels, user review of 46: keys, then the label (the readout panel adds the value); '·' between alternatives, '+' for combinations, and a lone key in brackets like the legend's [0]..[9] rows ([H], [~]); the readout panel's pairs have none.
OPACITY=('[ · ] 이름 불투명도','[ · ] Name opacity')
SIZE=('- · + 이름 크기','- · + Name size')
ROWS=[('[0] 전체','[0] All'),('[1] 방 이름','[1] Rooms'),('[2] 잠긴 문','[2] Locks'),('[3] 핵심 아이템','[3] Key items'),('[4] 문서·지도','[4] Files/Maps'),('[5] 퍼즐','[5] Puzzles'),('[6] 이벤트','[6] Events'),('[7] 일반 아이템','[7] Items'),('[8] 적','[8] Enemies')] # user 2026-11-08 numbering
SCOPE=[('[9] 방문한 방','[9] Visited'),('[9] 공개된 방','[9] Revealed'),('[9] 모든 방','[9] All rooms')] # RE1 HD's labels and order; difficulty is read from the game and has no key
LANGUAGE=('[\\] 언어: 한국어','[\\] LANGUAGE: ENGLISH') # user 2026-11-08: the same row, colour and size as the [H] label; the backslash key (₩ on Korean keyboards)
HOLD=[('[H] 아이템 이름: 끔','[H] Item names: Off'),('[H] 아이템 이름: 모두','[H] Item names: All'),('[H] 아이템 이름: 일반 제외','[H] Item names: No common')] # indexed by ItemNames 0 off, 1 all, 2 all except common; the panel is as wide as the widest of the three
LEGEND_ICON_OPACITY=('Ctrl + [ · ] 아이콘 불투명도','Ctrl + [ · ] Icon opacity');LEGEND_ICON_SIZE=('Ctrl + - · + 아이콘 크기','Ctrl + - · + Icon size')
HIDE=('[~] 숨김','[~] Hide');FOLD=('[~] 범례','[~] Legend') # RE2 annotated map's wording; [,] [.] still selects a room, as a debug key without a legend line
MODES=[('쉬움','Easy'),('보통','Normal'),('어려움','Hard')]
PANEL=[('연결된 곳','Exits'),('내용 없음','No contents'),('…','…')]
ROW_FONT=24;SMALL_FONT=15;READOUT_FONT=20 # the bottom-right panel: larger than the legend's hints
def category(row):
 if row['kind']=='weaponry':return 1 if row['name'] in WEAPONS else 4 # user: weapons are key items
 if row['kind']=='files':return 2
 if row['kind']=='enemies':return 5
 if row['kind']=='miscellaneous-objects':return None if row['name']=='Typewriter' else 2 # the game's map already marks typewriters
 if row['kind']=='items':return 4 if any(k in row['name'] for k in RECOVERY) else 1
 return None # characters are story presence, not collectable annotations
def korean(name,names):
 """Keep the source's count and pack size around the translated base name."""
 m=re.match(r'^(\d+|∞) (.+)$',name);count,rest=(m[1],m[2]) if m else (None,name)
 suffix=re.search(r' \((?!Second)[^)]*\)$',rest);base=rest[:suffix.start()] if suffix else rest
 single={'Zombies':'Zombie','Hunters':'Hunter','Eliminators':'Eliminator','Plague Crawlers':'Plague Crawler','Cerberuses':'Cerberus','Giant Spiders':'Giant Spider','Crows':'Crow','Bats':'Bat','Green Herbs':'Green Herb','Blue Herbs':'Blue Herb','First-Aid Sprays':'First-Aid Spray'}
 ko=names.get(base) or names.get(single.get(base,base))
 if not ko:raise ValueError('no Korean name: '+name)
 return ko+(suffix[0] if suffix else '')+(f' ×{count}' if count else '')
def shown(text,cat):return PREFIX.get(cat,'')+text
def catalogue(native,claims,contents,names,uses):
 """Merge external places onto native pieces; one row per place even when a piece has sections."""
 records={p['id']:p for p in contents['places']};owner={};places=[]
 for c in claims:
  index=len(places);ids=[c['external_id'],*c.get('also_covers',[])]
  rows={};links=[]
  for i in ids:
   owner[i]=index;links+=records[i]['linked']
   for r in records[i]['contents']:
    cat=category(r)
    if cat is None:continue
    row=rows.setdefault((r['name'],cat,catalogue_condition(r)),[0,0,0]);row[('easy','normal','hard').index(r['mode'])]+=1
  places.append(dict(claim=c,rows=rows,links=links))
 for use in uses['uses']:
  cat=0 if use['kind']=='lock' else 3
  places[owner[use['place']]]['rows'].setdefault((use['item'],cat,0),[1,1,1])
 for p in places:
  p['links']=sorted({owner[l] for l in p['links']}-{places.index(p)})
 return places
# A weapon row's amount is the rounds loaded in it, not a count of weapons. The catalogue lists all of these with no count.
WEAPONS=('Knife','Handgun','Shotgun','Hunting Gun','Magnum','Magnum Revolver','Grenade Launcher','Submachine Gun','Molotov Cocktail')
# User: item names AA의 BB drop 의. One-syllable stems read wrong without it (선 서); those stay, listed in verification/ko-name-changes.md for review.
KEEP_UI=('선의 서','악의 서','백의 조각상','흑의 조각상','불의 열쇠','물의 열쇠','시의 한 구절')
def short_ko(name):
 if name in KEEP_UI:return name
 return re.sub(r'(?<=\S)의 ',' ',name,count=1)
def split_label(text):
 """Map name lines, user 2026-11-05: a count always goes on line 2; otherwise 8 or more characters including spaces wrap, at the space nearest the middle; one word stays on one line."""
 m=re.match(r'^(.+) (×\d+|\d+%)$',text)
 if m:return m[1],m[2]
 if len(text)<8:return text,None
 at=min((i for i,c in enumerate(text) if c==' '),key=lambda i:abs(i-len(text)/2),default=None)
 return (text[:at],text[at+1:]) if at is not None else (text,None) # a word is never split: user, Hookshot
NO_LINE=0xffff;DROP_ROOMS=175
# Icon choice, from the game's item text (message_item_text_eng 46-51). User: the name stays the game's, the same for all six.
HERB_MIX={46:'G+G',47:'G+G+G',48:'G+R',49:'G+B',50:'G+G+B',51:'G+R+B'}
# Rooms on two floors whose heights separate in the table rows and script data: below this world y, the lower floor. Inferred, not native. Other two-floor rooms draw on every floor the point falls on.
DROP_FLOOR_Y={36:('1f','2f',300.0),45:('1f','3f',500.0)}
DROP_WEAPONS=('Sub-Machinegun','Custom Handgun','Rocket Launcher') # weapons in the game's item table with no placed row
DROP_ICON={'Fire Key':'Fire','Water Key':'Water',"Conductor's Key":"Conductor's",'Bl. Leech Charm':'Blue Leech Charm'}
def drop_level(p,native):
 f=DROP_FLOOR_Y.get(p['room']);floor=native['map_pieces'][p['piece']]['floor']
 return (1 if f and floor==f[0] else 2 if f and floor==f[1] else 0,)
def marker_label(row,mode,english,names):
 """Name as shown on the map. Machinegun amounts are raw (300 = the catalogue's 100%); 65535 looks like no count."""
 name=row['name_en'] if english else short_ko(row['name_ko']) if row['category']!='enemy' else row['name_ko'];amount=row['amount'].get(mode)
 if row['category'] in('enemy','lock','puzzle') or row['name_en'] in WEAPONS or amount is None or amount<=1 or amount>=65535:return name
 return f'{name} {(amount+2)//3}%' if row['name_en']=='Machinegun Ammo' else f'{name} ×{amount}'
MARKER_GROUPS=('lock','key','file','puzzle','item','enemy')
EVENT_CATEGORY=6 # events were puzzles with a flag until candidate 51
def marker_defs(placements,native):
 """One def per row and distinct label, in a stable order the review page shares through 'row'."""
 pieces=native['map_pieces'];index={p['id']:i for i,p in enumerate(pieces)};out=[];door_rooms=json.loads((ROOT/'data/room-state.json').read_text())['doors']
 for row_index,r in enumerate(placements['rows']):
  if r['x'] is None:continue
  piece=index.get(r['piece']);rooms=()
  if piece is None: # a door instance: shown when a room the game joins to it is (data/room-state.json, native 0x5bb420)
   rooms=tuple(index[p] for p in door_rooms.get(r['piece'],()))
   if not rooms:raise ValueError(f"lock {r['name_en']} on door {r['piece']} with no room")
   piece=next((i for i in rooms if pieces[i]['native_room_id']==r['room']),rooms[0])
  labels={}
  for bit,mode in enumerate(('easy','normal','hard')):
   if mode in r['amount']:
    key=(marker_label(r,mode,0,None),marker_label(r,mode,1,None));labels[key]=labels.get(key,0)|1<<bit
  for (ko,en),modes in labels.items():out.append(dict(row=row_index,x=r['x'],y=r['y'],piece=piece,ko=ko,en=en,category=EVENT_CATEGORY if r.get('event') else MARKER_GROUPS.index(r['category']),modes=modes,hollow=int('room centre' in r['evidence']),condition=r.get('condition',0),rooms=rooms,event=int(bool(r.get('event')))))
 return out
# Names are rastered near their 1080p size: 20 px art stretched 1.65x read as blurred. Icons moved out, so the atlas is 32 MB (4096x2048) again; a layout past 4096 raises below.
NAME_FONT=30
# Large source shown small, user 2026-11-05. Never upscaled to get here: assets/icons/manifest.json.
ICON_SIZE=96;NO_ICON=0xffff
# Icons live in their own mipped texture: mips on the shared atlas would add 21 MB and bleed across its 2 px gutters into text.
ICON_TEX=2048;ICON_TEX_H=1024;ICON_CELL=102;ICON_LEVELS=5 # 120 cells fill 6 of 10 rows: half the square's memory, same texels and mips
def icon_cell(i):
 x,y=3+i%20*ICON_CELL,3+i//20*ICON_CELL
 if y+ICON_SIZE>ICON_TEX_H:raise ValueError('too many icons for the icon texture')
 return x,y
EDGE_STRONG=.8 # user, live candidate 33: herbs and keys darker still
EDGE_DARKEN=.45 # user: outlines a little darker. Band of about 3 px inside the alpha edge, fading inward; alpha and interior unchanged.
def strong_edge(name):return 'Herb' in name or 'Key' in name or name in ('Fire','Water',"Conductor's")
def darken_edge(icon,amount=EDGE_DARKEN):
 from PIL import ImageFilter,ImageChops
 a=icon.getchannel('A');inner=a.filter(ImageFilter.MinFilter(9 if amount>EDGE_DARKEN else 7));band=ImageChops.subtract(a,inner).filter(ImageFilter.GaussianBlur(.7)).point(lambda v:int(v*amount))
 rgb=Image.composite(Image.new('RGB',icon.size),icon.convert('RGB'),band);out=rgb.convert('RGBA');out.putalpha(a);return out
def diamond(symbol):
 """White so the mark's colour tints it; outline and symbol dark. Drawn, not a font: stem and dot stay apart down to 19 px, and the shape is centred by construction."""
 S=4;D=lambda *v:[x*S for x in v];im=Image.new('RGBA',(96*S,96*S));d=ImageDraw.Draw(im);ink=(8,8,8,255)
 d.polygon(D(48,4,92,48,48,92,4,48),fill=ink);d.polygon(D(48,12,84,48,48,84,12,48),fill='white')
 if symbol=='!':
  d.polygon(D(41,24,55,24,52,56,44,56),fill=ink);d.ellipse(D(41,62,55,76),fill=ink)
 else:
  Q=lambda *v:D(*[48+(c-48)*.9 for c in v]) # user: ? 10% smaller, about the diamond's centre
  d.arc(Q(33,20,63,50),150,70,fill=ink,width=int(9*.9*S));d.polygon(Q(54,40,44,48,43,57,53,57,53,52,60,45),fill=ink);d.ellipse(Q(41,62,55,76),fill=ink)
 return im.resize((96,96),Image.Resampling.LANCZOS)
def reduce_premult(im):
 """Half size, channel by channel. Pillow's resize on RGBA treats colour as straight and un-premultiplies the result; on data already premultiplied that brightened every soft edge to a white rim (live, candidate 29)."""
 return Image.merge('RGBA',[c.resize((im.width//2,im.height//2),Image.Resampling.BOX) for c in im.split()])
def mip_defect(levels,w):
 """Largest brightening of any level against level 0: alpha-weighted colour must be preserved by reduction. levels: BGRA bytes."""
 def weighted(raw):
  s=[0,0,0];a=0
  for i in range(0,len(raw),4):
   k=raw[i+3];a+=k
   for c in range(3):s[c]+=raw[i+c]*k
  return [v/max(a,1) for v in s]
 base=weighted(levels[0]);return max(weighted(l)[c]-base[c] for l in levels[1:] for c in range(3))
MIP_BRIGHTEN_LIMIT=6
def icon_mips(sheet,reduce=reduce_premult):
 """BGRA levels from an RGBA sheet: reduced premultiplied, stored straight as the ASI blends. Fully transparent texels take the colour of what is nearest (coarser level), so linear filtering pulls no black into soft edges."""
 from PIL import ImageChops
 r,g,b,a=sheet.split();levels=[Image.merge('RGBA',(ImageChops.multiply(r,a),ImageChops.multiply(g,a),ImageChops.multiply(b,a),a))]
 while min(levels[-1].size)>1:levels.append(reduce(levels[-1]))
 out=[];coarse=None
 for im in reversed(levels):
  raw=bytearray(im.tobytes());w,h=im.size;fill=coarse.resize((w,h),Image.Resampling.NEAREST).tobytes() if coarse else bytes(w*h*3)
  rgb=bytearray(w*h*3)
  for i in range(w*h):
   p=raw[i*4+3]
   if p>=8: # below this, 8-bit premultiplied colour has rounded towards black
    for c in range(3):rgb[i*3+c]=min(255,(raw[i*4+c]*255+p//2)//p)
   else:rgb[i*3:i*3+3]=fill[i*3:i*3+3]
  coarse=Image.frombytes('RGB',(w,h),bytes(rgb))
  bgra=bytearray(w*h*4)
  bgra[0::4]=rgb[2::3];bgra[1::4]=rgb[1::3];bgra[2::4]=rgb[0::3];bgra[3::4]=raw[3::4]
  out.append(bytes(bgra))
 chain=list(reversed(out))[:ICON_LEVELS]
 if mip_defect(chain,ICON_TEX)>MIP_BRIGHTEN_LIMIT:raise ValueError('icon mips brighten soft edges')
 return chain
LOCK_ICON={'Fire Key':'Fire','Water Key':'Water',"Conductor's Key":"Conductor's",'Breeding Room Key':'Breeding Rm. Key','Green Leech Charm':'Gr. Leech Charm','Shaft Key (L)':'Shaft Key','Shaft Key (R)':'Shaft Key'}
def icon_for(row,icon_names):
 """Icon name for a placed row. Puzzles and events (event rows are category puzzle in the data) stay code-drawn diamonds and have none."""
 if row['category']=='puzzle':return None
 if row['category']=='file':return 'Map' if row['name_en'].endswith('Map') else 'Document'
 if row['category']=='lock': # the key that opens it; no icon yet, padlock. Manifest names are the game's short names.
  return LOCK_ICON.get(row['name_en'],row['name_en']) if LOCK_ICON.get(row['name_en'],row['name_en']) in icon_names else 'Padlock'
 return row['name_en']
def marker_state_row(row,states,placed):
 """From verification/state-flags.json: table slots per difficulty, or the flags that finish a row. 0xffff none. An enemy row's item is not guarded: 0x412c30 rewrites row+8 from the actor."""
 s=states.get(row,{});slots=s.get('slot') or {};flags=[f for f in (s.get('done_any_of') or [s.get('done_flag')]) if f is not None]+[0xffff,0xffff];r=placed[row]
 return (*[slots.get(m,0xffff) for m in ('easy','normal','hard')],flags[0],flags[1],0xffff if r['category']=='enemy' else r.get('item') or 0,r.get('room') or 0,r.get('kind') or 0,0xffff if r.get('need_flag') is None else r['need_flag'])
def measure(text,font=FONT):
 """Atlas size of a room name: the box build() gives it. Multi-line text is wrapped between words."""
 box=ImageDraw.Draw(Image.new('L',(1,1))).multiline_textbbox((0,0),text,font=ImageFont.truetype(str(font),NAME_FONT),stroke_width=2,align='center');return math.ceil(box[2]-box[0])+12,math.ceil(box[3]-box[1])+12
def build(font=FONT):
 native=json.loads((ROOT/'data/native-map.json').read_text())
 matches_document=json.loads((ROOT/'data/room-matches.json').read_text());contents=json.loads((ROOT/'data/room-contents.json').read_text());names=json.loads((ROOT/'data/names-ko.json').read_text())['names'];uses=json.loads((ROOT/'data/item-uses.json').read_text())
 sys.path.insert(0,str(ROOT/'tools/crosscheck'))
 from room_matches import validate
 validate(native,json.loads((ROOT/'data/external-locations.json').read_text()),matches_document)
 claims=matches_document['claims']
 if len({(r['region'],r['gui_id']) for r in native['map_pieces']})!=len(native['map_pieces']):raise ValueError('duplicate runtime room IDs')
 places=catalogue(native,claims,contents,names,uses)
 piece_place={p:i for i,place in enumerate(places) for p in [*place['claim']['native_pieces'],*[a['piece'] for a in place['claim'].get('alias_pieces',[])]]}
 regions={r['region']:r['region_index'] for r in native['native_regions']}
 fonts={size:ImageFont.truetype(str(font),size) for size in (NAME_FONT,ROW_FONT,SMALL_FONT,READOUT_FONT)}
 texts=[];lookup={}
 def add(t,size=NAME_FONT):
  if (t,size) not in lookup:lookup[(t,size)]=len(texts);texts.append((t,size))
  return lookup[(t,size)]
 def pair(texts_,size):return [add(t,size) for t in texts_]
 def flat(pairs,size):return [add(t,size) for p in pairs for t in p]
 rows=[]
 for r in native['map_pieces']:
  if r['id'] not in piece_place:raise ValueError('unnamed native piece '+r['id'])
  c=places[piece_place[r['id']]]['claim']
  rows.append((regions[r['region']],r['gui_id'],r['floor_gui_id'],1,add(c['name_ko']),add(c['name_en']),piece_place[r['id']]))
 place_rows=[];content_rows=[];link_rows=[]
 for p in places:
  first=len(content_rows)
  for (name,cat,condition),counts in sorted(p['rows'].items(),key=lambda kv:(kv[0][1],kv[0][0],kv[0][2])):
   content_rows.append((cat,*counts,add(shown(short_ko(korean(name,names)),cat)),add(shown(name,cat)),condition))
  link_first=len(link_rows);link_rows+=p['links']
  c=p['claim'];place_rows.append((add(c['name_ko']),add(c['name_en']),first,len(content_rows)-first,link_first,len(p['links'])))
 states={r['index']:r for r in json.loads((ROOT/'verification/state-flags.json').read_text())['rows']};placed=json.loads((ROOT/'data/placements.json').read_text())['rows']
 layout=json.loads((ROOT/'data/room-layout.json').read_text());piece_index={p['id']:i for i,p in enumerate(native['map_pieces'])}
 defs=marker_defs(json.loads((ROOT/'data/placements.json').read_text()),native)
 room_lists={};marker_room_ids=[]
 for m in defs:
  if m['rooms'] and m['rooms'] not in room_lists:room_lists[m['rooms']]=len(marker_room_ids);marker_room_ids+=m['rooms']
 marker_rows=[(f"{m['x']:.1f}f",f"{m['y']:.1f}f",m['piece'],add(split_label(m['ko'])[0]),add(split_label(m['en'])[0]),m['category'],m['modes'],m['hollow'],m['condition'],room_lists.get(m['rooms'],0),len(m['rooms']),m['event']) for m in defs]
 line2=[v for m in defs for v in (*[(add(split_label(m[k])[1]) if split_label(m[k])[1] else NO_LINE) if m['category']!=5 and not m['event'] else NO_LINE for k in ('ko','en')],)]
 state=json.loads((ROOT/'data/room-state.json').read_text())['pieces'];none=0xffff
 state_rows=[(*(state[p['id']]['visited']+[none])[:2],*(state[p['id']]['revealed']+[none])[:2]) for p in native['map_pieces']]
 layout_rows=[(piece_index[r['piece']],piece_place[r['piece']],add(r['text']),r['lang'],f"{r['x']:.1f}f",f"{r['y']:.1f}f",*[f'{float(v):.1f}f' for v in (r['line'] or (0,0,0,0))],int(bool(r['line']))) for r in layout['rows']]
 canvas_rows=[tuple(f'{float(v):.1f}f' for v in layout['pieces'].get(p['id'],(0,0,0,0))) for p in native['map_pieces']]
 modes=flat(MODES,NAME_FONT);panel=flat(PANEL,NAME_FONT);badges=[add(t) for t in CATEGORIES];digits=[add(str(i)) for i in range(10)]
 small=[add(str(i),READOUT_FONT) for i in range(10)];percent=add('%',READOUT_FONT)
 row_ids=flat(ROWS,ROW_FONT);title=pair(TITLE,ROW_FONT);opacity_ids=pair(OPACITY,READOUT_FONT);icon_opacity_ids=pair(LEGEND_ICON_OPACITY,READOUT_FONT);icon_size_ids=pair(LEGEND_ICON_SIZE,READOUT_FONT);size_ids=pair(SIZE,READOUT_FONT);scope_ids=flat(SCOPE,ROW_FONT);language=pair(LANGUAGE,SMALL_FONT);hold=flat(HOLD,SMALL_FONT);hide=pair(HIDE,SMALL_FONT);fold=pair(FOLD,SMALL_FONT)
 icon_manifest=json.loads((ROOT/'assets/icons/manifest.json').read_text())
 icon_names=icon_manifest['names'];icon_first=len(texts)
 # Dropped items: whole table by item id. Icon NO_ICON or no name means the generic mark, counted in the log.
 item_names=json.loads((ROOT/'data/item-names.json').read_text());drop_n=max(map(int,item_names))+1;drop_rows=[];drop_mult,drop_pct=add('×'),add('%')
 for i in range(drop_n):
  r=item_names.get(str(i))
  if not r or not r['en'].strip() or r['en'] in ('Invalid Message','Nothing') or r['en'].endswith('-NULL'):drop_rows+=[NO_LINE,NO_LINE,NO_LINE,NO_LINE,NO_ICON,MARKER_GROUPS.index('item'),0];continue
  mix=HERB_MIX.get(i)
  w=r['en'] in WEAPONS or r['en'] in DROP_WEAPONS;cat=('key' if w else r['category']);row=dict(category=cat,name_en=r['en']);icon=icon_for(row,icon_names);icon=f'Herbal Mix {mix}' if mix else DROP_ICON.get(r['en'],icon);count=0 if w else 2 if r['en']=='Machinegun Ammo' else 1
  lines=[split_label(short_ko(r['ko'])),split_label(r['en'])]
  if count:lines=[(short_ko(r['ko']),None),(r['en'],None)]
  drop_rows+=[add(lines[0][0]),add(lines[0][1]) if lines[0][1] else NO_LINE,add(lines[1][0]),add(lines[1][1]) if lines[1][1] else NO_LINE,icon_names.index(icon) if icon in icon_names else NO_ICON,MARKER_GROUPS.index(cat),count]
 icon_first=len(texts)
 marker_icons=[NO_ICON if icon_for(placed[m['row']],icon_names) is None else icon_first+icon_names.index(icon_for(placed[m['row']],icon_names)) for m in defs]
 d0=ImageDraw.Draw(Image.new('L',(1,1)));PAD={NAME_FONT:6,ROW_FONT:4,SMALL_FONT:4,READOUT_FONT:4};W=4096; x=y=2;row_h=0;boxes=[]
 for t,size in texts:
  box=d0.multiline_textbbox((0,0),t,font=fonts[size],stroke_width=2,align='center');margin=PAD[size];w=math.ceil(box[2]-box[0])+margin*2;h=math.ceil(box[3]-box[1])+margin*2 # multiline boxes are fractional
  if w>W-4:raise ValueError('label too wide')
  if x+w>W:x=2;y+=row_h+2;row_h=0
  boxes.append((x,y,w,h,box));x+=w+2;row_h=max(row_h,h)
 for name in [*icon_names,'!','?']: # the diamonds too: mipped, or their stem and dot melt when small
  ix,iy=icon_cell(len(boxes)-icon_first);boxes.append((ix,iy,ICON_SIZE,ICON_SIZE,(0,0,ICON_SIZE,ICON_SIZE)))
 if x+8>W:x=2;y+=row_h+2;row_h=0
 solid=(x,y,8,8);row_h=max(row_h,8);y+=row_h+2
 H=1
 while H<y:H*=2
 if H>4096:raise ValueError(f'atlas needs height {H}; 4096 is the limit for a 32-bit game')
 atlas=Image.new('RGBA',(W,H));d=ImageDraw.Draw(atlas)
 for (t,size),(x,y,w,h,b) in zip(texts,boxes):
  d.text((x+PAD[size]-b[0],y+PAD[size]-b[1]),t,font=fonts[size],fill='white',stroke_width=2,stroke_fill=(8,8,8,255),align='center')
 sheet=Image.new('RGBA',(ICON_TEX,ICON_TEX_H))
 for name,(ix,iy,iw,ih,_) in zip(icon_names,boxes[icon_first:]):
  icon=Image.open(ROOT/'assets/icons'/icon_manifest['files'][name]).convert('RGBA')
  if icon.size!=(ICON_SIZE,ICON_SIZE):raise ValueError(f'icon must be {ICON_SIZE}px: '+name)
  sheet.paste(darken_edge(icon,EDGE_STRONG if strong_edge(name) else EDGE_DARKEN),(ix,iy))
 for symbol,(ix,iy,iw,ih,_) in zip('!?',boxes[icon_first+len(icon_names):]):sheet.paste(diamond(symbol),(ix,iy))
 d.rectangle((solid[0],solid[1],solid[0]+solid[2]-1,solid[1]+solid[3]-1),fill='white')
 # D3DFMT_A8R8G8B8 memory order is BGRA.
 (ROOT/'assets').mkdir(exist_ok=True)
 blob=atlas.tobytes('raw','BGRA')
 icon_blob=b''.join(icon_mips(sheet));(ROOT/'assets/icons.bgra').write_bytes(icon_blob)
 (ROOT/'assets/labels.bgra').write_bytes(blob)
 def table(kind,name,items):return [f'static const {kind} {name}[] = {{']+['{'+','.join(map(str,i))+'},' for i in items]+['};']
 def ints(name,items):return [f'static const unsigned short {name}[] = {{'+','.join(map(str,items))+'};']
 lines=['/* Generated by tools/build_labels.py. Project text and generated icon raster snapshots. */',f'#define NAME_FONT {NAME_FONT}',f'#define ATLAS_W {W}',f'#define ATLAS_H {H}',
  'typedef struct { unsigned short x,y,w,h; } Glyph;','typedef struct { unsigned region,id,floor,mapped,ko,en,place; } Room;','typedef struct { unsigned short ko,en,first,count,first_link,links; } Place;']
 lines+=table('Glyph','glyphs',[b[:4] for b in boxes])+[f'static const Glyph solid_glyph = {{{",".join(map(str,solid))}}};']
 lines+=table('Room','rooms',rows)+table('Place','places',place_rows)+table('RE0Content','contents',content_rows)+ints('place_links',link_rows or [0])
 proj=json.loads((ROOT/'data/room-projection.json').read_text());first=[0]*(DROP_ROOMS+1)
 for p in proj:first[p['room']+1]+=1
 for i in range(DROP_ROOMS):first[i+1]+=first[i]
 proj=sorted(proj,key=lambda p:p['room'])
 lines+=[f'#define DROP_ITEMS {drop_n}',f'#define DROP_ROOMS {DROP_ROOMS}',f'#define DROP_MULT {drop_mult}',f'#define DROP_PCT {drop_pct}','typedef struct { unsigned short piece,level; float bx,by,split; } DropProj;']+ints('drop_items',[(v+icon_first if j%7==4 and v!=NO_ICON else v) for j,v in enumerate(drop_rows)])+ints('drop_proj_first',first)+table('DropProj','drop_proj',[(p['piece'],*drop_level(p,native),f"{p['bx']:.6f}f",f"{p['by']:.6f}f",f"{DROP_FLOOR_Y.get(p['room'],(0,0,0.0))[2]:.1f}f") for p in proj])
 lines+=ints('marker_line2',line2)+['#define NO_LINE 65535']
 lines+=[f'#define ICON_FIRST_GLYPH {icon_first}',f'#define NO_ICON {NO_ICON}',f'#define ICON_TEX {ICON_TEX}',f'#define ICON_TEX_H {ICON_TEX_H}',f'#define ICON_LEVELS {ICON_LEVELS}',f'#define ICON_BYTES {len(icon_blob)}']+ints('marker_icon_glyphs',marker_icons)
 lines+=table('RE0MarkerDef','markers',marker_rows)+ints('marker_rooms',marker_room_ids or [0])+table('RE0RoomState','room_state',state_rows)
 lines+=table('RE0MarkerState','marker_state',[marker_state_row(m['row'],states,placed) for m in defs])+table('RE0RoomLayout','room_layout',layout_rows)+table('RE0Box','piece_canvas',canvas_rows)+[f'#define LAYOUT_COUNT {len(layout_rows)}']
 lines+=ints('mode_ids',modes)+ints('panel_ids',panel)+ints('badge_ids',badges)+ints('digit_ids',digits)+ints('small_digit_ids',small)+[f'#define SMALL_PERCENT_ID {percent}',f'#define PUZZLE_MARK_ID {icon_first+len(icon_names)}',f'#define EVENT_MARK_ID {icon_first+len(icon_names)+1}']
 lines+=ints('row_ids',row_ids)+ints('title_ids',title)+ints('opacity_ids',opacity_ids)+ints('icon_opacity_ids',icon_opacity_ids)+ints('icon_size_ids',icon_size_ids)+ints('size_ids',size_ids)+ints('scope_ids',scope_ids)+ints('language_ids',language)+ints('hold_ids',hold)+ints('hide_ids',hide)+ints('fold_ids',fold)
 lines+=[f'#define ROOM_COUNT {len(rows)}',f'#define PLACE_COUNT {len(place_rows)}',f'#define MARKER_COUNT {len(marker_rows)}']
 (ROOT/'src/runtime/labels_generated.h').write_text('\n'.join(lines)+'\n')
 inputs=['data/native-map.json','data/room-matches.json','data/external-locations.json','data/room-contents.json','data/names-ko.json','data/item-uses.json','data/placements.json','data/room-state.json','assets/icons/manifest.json','data/item-names.json','data/room-projection.json']
 report=dict(font_name=font.name,font_sha256=hashlib.sha256(font.read_bytes()).hexdigest(),font_file_distributed=False,
   inputs_sha256={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in inputs},
   header_sha256=hashlib.sha256((ROOT/'src/runtime/labels_generated.h').read_bytes()).hexdigest(),
   atlas_sha256=hashlib.sha256(blob).hexdigest(),icons_sha256=hashlib.sha256(icon_blob).hexdigest(),width=W,height=H,room_pieces=len(rows),mapped_pieces=sum(r[3] for r in rows),named_locations=len(claims),places=len(place_rows),content_rows=len(content_rows),links=len(link_rows))
 (ROOT/'verification/label-build.json').write_text(json.dumps(report,indent=2)+'\n')
 print(f"Markers {len(marker_rows)}"); print(f'Built {len(texts)} rasters ({W}x{H}), {len(rows)} room pieces, {len(place_rows)} places, {len(content_rows)} content rows, {len(link_rows)} links')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--font',type=Path,default=FONT);a=p.parse_args();build(a.font)
