"""What the overlay must show for each state. Run against the real core and against mutants, so a pass means something."""
import re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'emulator'))
from annotations import tables,catalogue
OFF=0xff6a6a6a # user 2026-11-08: darker than the common-item grey
# RE1 HD on-state colours, sampled from its legend rasters: [0], [1], then [2]..[7].
COLORS=[0xffffffff,0xfff0e2be,0xffffcd46,0xff5adcff,0xffff8cd2,0xffff9628,0xffb070ff,0xffb8bcc4,0xffeb3c3c] # legend rows 0..8, user 2026-11-08: events after puzzles, common items cool grey
LEGEND_CATEGORY=[0,1,2,3,6,4,5] # category id of rows [2]..[8]
def tables_canvas(piece):
 header=(Path(__file__).resolve().parents[1]/'src/runtime/labels_generated.h').read_text()
 return [tuple(float(v[:-1]) for v in c.split(',')) for c in re.findall(r'\{([-0-9.]+f,[-0-9.]+f,[-0-9.]+f,[-0-9.]+f)\}',header.split('piece_canvas[] = {',1)[1].split('};',1)[0])][piece]
def tables_markers():
 text=(ROOT/'src/runtime/labels_generated.h').read_text();part=text.split('markers[] = {',1)[1].split('};',1)[0]
 return [tuple(float(v.rstrip('f')) if '.' in v else int(v) for v in m.split(',')) for m in re.findall(r'\{([0-9.,f\-]+)\}',part)]
def place_glyphs(data):
 text=(ROOT/'src/runtime/labels_generated.h').read_text();part=text.split('places[] = {',1)[1].split('};',1)[0]
 return {int(v) for m in re.findall(r'\{([0-9,]+)\}',part) for v in m.split(',')[:2]}
def icon_sizes(core):
 """Candidate 45, user 2026-11-06: icon side by category at game zoom and at 3x. Enemies are not enlarged; door keys 120% to 150%, every other icon 100% to 130%, of the 1.3 base; keys and locks keep their 10%."""
 text=(ROOT/'src/runtime/labels_generated.h').read_text();icons=[int(v) for v in re.search(r'marker_icon_glyphs\[\] = \{([0-9,]+)\}',text)[1].split(',')];puzzle=int(re.search(r'#define PUZZLE_MARK_ID (\d+)',text)[1])
 expect={0:(1.3*.96*1.1,1.3*1.5*1.1),1:(1.3*1.1,1.3*1.3*1.1),2:(1.3,1.3*1.3),3:(1.3*11/9,1.3*1.3*11/9),4:(1.3,1.3*1.3),5:(1.0,1.0)};ms=tables_markers();s=core.default_settings();s.scope=2
 def side(m,glyph,k):
  ops=core.frame(s,1920,1080,{m[2]:[300,200,420,300]},(),(k,960-m[0]*k,540-m[1]*k),None,[0]*33)[0]
  return next((o['box'][3]-o['box'][1] for o in ops if o['glyph']==glyph),None)
 for cat,(near,far) in expect.items():
  for j,m in enumerate(ms):
   glyph=puzzle if cat==3 else icons[j]
   if m[5]!=cat or m[8] or (cat==3 and m[11]) or glyph>=65535 or side(m,glyph,1.5) is None:continue
   if abs(side(m,glyph,1.5)-18.9*1.2*near)>.1 or abs(side(m,glyph,4.5)-27*1.2*far)>.1:raise AssertionError(f'category {cat} icon size by zoom')
   break
  else:raise AssertionError(f'no visible marker of category {cat}')
def real_floor_rules(core,rooms,view):
 """Priority over each real floor, boxes as the static table holds them: key items are never covered by common marks or names, nor names by each other's tier."""
 text=(ROOT/'src/runtime/labels_generated.h').read_text();canvas=[[float(v.rstrip('f')) for v in m.split(',')] for m in re.findall(r'\{([0-9.,f]+)\}',text.split('piece_canvas[] = {',1)[1].split('};',1)[0])]
 raw=[[int(v) for v in m.split(',')] for m in re.findall(r'\{([0-9,]+)\}',text.split('rooms[] = {',1)[1].split('};',1)[0])];floors={}
 for i,r in enumerate(raw):floors.setdefault((r[0],r[2]),[]).append(i)
 KEY=0xff5adcff;COMMON={0xffb8bcc4,0xffeb3c3c};first_icon=int(re.search(r'#define ICON_FIRST_GLYPH (\d+)',text)[1]);cats=[int(m.split(',')[5]) for m in re.findall(r'\{([0-9.,f]+)\}',text.split('markers[] = {',1)[1].split('};',1)[0])];icons=[int(v) for v in re.search(r'marker_icon_glyphs\[\] = \{([0-9,]+)\}',text)[1].split(',')];key_icons={i for c,i in zip(cats,icons) if c==1};common_icons={i for c,i in zip(cats,icons) if c>=4}-key_icons;hit=lambda a,b:a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1];inset=lambda b:[b[0]+3,b[1]+3,b[2]-3,b[3]-3]
 layout={int(m.split(',')[2]) for m in re.findall(r'\{([0-9.,f]+)\}',text.split('room_layout[] = {',1)[1].split('};',1)[0])}
 for ids in floors.values():
  seen={i:[v*1.5 for v in canvas[i]] for i in ids if canvas[i][2]>canvas[i][0]}
  if not seen:continue
  got=core.layout_view(seen)
  if got is None or abs(got[0]-1.5)>.001 or abs(got[1])>.01 or abs(got[2])>.01:raise AssertionError(f'static boxes rejected: {got}')
  if len(seen)>1:
   first=next(iter(seen));moved=dict(seen);moved[first]=[v+50 for v in seen[first]]
   if core.layout_view(moved) is not None:raise AssertionError('disagreeing room box accepted for fixed names')
  s=core.default_settings();s.opacity=100;ops,_=core.frame(s,1920,1080,seen,(),view,None,[0xffffffff]*33)
  mark=lambda o:o['glyph']>=first_icon
  keys=[o['box'] for o in ops if o['glyph'] in key_icons];low=[o['box'] for o in ops if o['glyph'] in common_icons]
  mid=lambda b:[(b[0]+b[2])/2-3.67,(b[1]+b[3])/2-3.67,(b[0]+b[2])/2+3.67,(b[1]+b[3])/2+3.67]
  if any(hit(mid(a),mid(b)) for a in low for b in keys):raise AssertionError('common mark on a key mark')
  drawn=[o['glyph'] for o in ops]
  if any(drawn.index(i)>len(drawn)-1-drawn[::-1].index(k) for i in common_icons&set(drawn) for k in key_icons&set(drawn)):raise AssertionError('a key mark painted under a common one')
  names=[o for o in ops if o['glyph']>=0 and o['color'] in COMMON];top=[o for o in ops if o['glyph']>=0 and o['color']==KEY];roomnames=[o for o in ops if o['glyph'] in layout]
  if any(hit(inset(n['box']),b) for n in names for b in keys):raise AssertionError('common name covers a key mark')
  if any(hit(inset(n['box']),inset(t['box'])) for n in names for t in top):raise AssertionError('common name covers a key name')
  # RE2 Remake style, 2026-11-06: room names are drawn first and other names may cover them.
  # At 3x fixed names and marks slide under the legend's place; the legend stays clear of both.
  z=3*1.5
  for px,py in ((1920,1080),(1500,1080),(1920,700),(1300,600),(900,1400),(600,900)): # pans, so names of every floor pass the legend's place
   zoom=(z,-px,-py);zs={i:[b[0]*z-px,b[1]*z-py,b[2]*z-px,b[3]*z-py] for i,b in ((i,canvas[i]) for i in seen)}
   zops,_=core.frame(s,1920,1080,zs,(),zoom,None,[0xffffffff]*33);own=[o['box'] for o in zops if o['glyph']<0 and o['color']==0xd0080808][:2];over=[o for o in zops[1:] if any(hit(o['box'],b) for b in own) and (o['glyph'] in layout or mark(o))] # legend and readouts
   if over:raise AssertionError('map annotation on the legend')
def inside(a,b):return a[0]>=b[0] and a[1]>=b[1] and a[2]<=b[2] and a[3]<=b[3]
def rows_of(ops,data,lang=0):
 ids=data['ids']['row'];by={ids[i*2+lang]:i for i in range(9)};return {by[o['glyph']]:o for o in ops if o['glyph'] in by}
def room(rooms,data):
 for i,r in enumerate(rooms):
  _,_,first,count,_,_=data['places'][r[6]]
  if len({row[0] for row in data['contents'][first:first+count] if row[2]})>=2:return i,r[6]
 raise AssertionError('no multi-category room')
def item_name_states(core):
 """Candidate 50, user 2026-11-08: ItemNames 0 off, 1 all, 2 all except common; H cycles 1, 2, 0; the legend row names the state and the panel holds its width."""
 import ctypes,test_drops
 data=tables();m=tables_markers();hold=data['ids']['hold']
 def need(ok,why):
  if not ok:raise AssertionError(why)
 k=core.library.re0_settings_key;k.argtypes=[ctypes.POINTER(type(core.default_settings())),ctypes.c_int,ctypes.c_void_p,ctypes.c_void_p]
 s=core.default_settings();s.item_names=0;seq=[]
 for _ in range(6):k(ctypes.byref(s),ord('h'),None,None);seq.append(s.item_names)
 need(seq==[1,2,0,1,2,0],f'H cycle {seq}')
 def names(i,state):
  d=m[i];t=core.default_settings();t.item_names=state;t.mask=127;t.difficulty=next(x for x in range(3) if d[6]>>x&1)
  return [o for o in core.frame(t,1920,1080,{d[2]:[1900,4,1901,5]},(),(1.5,0,0),[0 if j==i else 1 for j in range(len(m))])[0] if o['glyph']==d[3]]
 pick=lambda cat:next(i for i,d in enumerate(m) if d[5]==cat and not d[8] and names(i,1))
 key,item=pick(1),pick(4)
 need([bool(names(key,n)) for n in (1,2,0)]==[True,True,False],'key names by state');need([bool(names(item,n)) for n in (1,2,0)]==[True,False,False],'common names by state')
 need(names(key,2)[0]['box']==names(key,1)[0]['box'],'state 2 moved a kept name')
 D=test_drops;ink=D.ITEMS[55*7];need(D.ITEMS[55*7+5]==4,'ink ribbon is not a common item')
 def drawn(state):return [o['glyph'] for o in D.frame(core,D.S['slot_room_at_2c'],D.S['item'],D.S['current_amount_at_3c'],D.S['position'],'i_sh0090',item_names=state)]
 need([ink in drawn(n) for n in (1,2,0)]==[True,False,False],'drop name by state');need(D.ITEMS[55*7+4] in drawn(2),'state 2 lost the drop icon')
 for english in (0,1):
  boxes=set()
  for state in range(3):
   t=core.default_settings();t.item_names=state;t.english=english;ops=core.frame(t,1920,1080,{},())[0];g=[o['glyph'] for o in ops]
   need([i for i in range(3) if hold[i*2+english] in g]==[state],'legend row does not show the state');boxes.add(tuple(ops[0]['box']))
  need(len(boxes)==1,'legend panel width changed with the item-name state')
def category_rules(core):
 """Candidate 51, user 2026-11-08: events are their own category (purple ? diamond, own bit and legend row), colours come from set_color, the INI text is edited in place."""
 import ctypes
 text=(ROOT/'src/runtime/labels_generated.h').read_text();m=tables_markers();event_id=int(re.search(r'#define EVENT_MARK_ID (\d+)',text)[1]);puzzle_id=int(re.search(r'#define PUZZLE_MARK_ID (\d+)',text)[1])
 def need(ok,why):
  if not ok:raise AssertionError(why)
 states=[[int(v) for v in r.split(',')] for r in re.findall(r'\{([0-9,]+)\}',text.split('marker_state[] = {',1)[1].split('};',1)[0])]
 def frame(i,mask):
  # the event's own precondition flag set (the game ran up to it), nothing done; every room of the floor counts
  words=[0]*33;need_flag=states[i][8]
  if need_flag!=0xffff:words[need_flag>>5]|=1<<(need_flag&31)
  t=core.default_settings();t.mask=mask;t.scope=2;t.difficulty=next(x for x in range(3) if m[i][6]>>x&1)
  return core.frame(t,1920,1080,{m[i][2]:[1900,4,1901,5]},(),(1.5,0,0),[0 if j==i else 1 for j in range(len(m))],words)[0]
 ev=next((i for i,d in enumerate(m) if d[5]==6 and not d[8] and any(o['glyph']==event_id for o in frame(i,127))),None)
 pz=next((i for i,d in enumerate(m) if d[5]==3 and not d[8] and not d[11] and any(o['glyph']==puzzle_id for o in frame(i,127))),None)
 need(ev is not None and pz is not None,'no isolated event and puzzle marker to test')
 has=lambda ops,g:any(o['glyph']==g for o in ops)
 need(has(frame(ev,127&~(1<<3)),event_id),'event hidden when only puzzles are off');need(not has(frame(ev,127&~(1<<6)),event_id),'event shown with its own bit off')
 need(has(frame(pz,127&~(1<<6)),puzzle_id),'puzzle hidden when only events are off');need(not has(frame(pz,127&~(1<<3)),puzzle_id),'puzzle shown with its own bit off')
 need(m[ev][11]==1 and all(d[11]==0 for d in m if d[5]!=6),'event flag and event category disagree')
 # Colours: the diamond and the legend row follow set_color, then the defaults return.
 setc=core.library.re0_frame_set_color;setc.argtypes=[ctypes.c_uint,ctypes.c_uint];getc=core.library.re0_frame_color;getc.argtypes=[ctypes.c_uint];getc.restype=ctypes.c_uint
 need([getc(c) for c in range(7)]==[0xffcd46,0x5adcff,0xff8cd2,0xff9628,0xb8bcc4,0xeb3c3c,0xb070ff],'default colours')
 try:
  setc(6,0x123456);setc(4,0x654321)
  d=next(o for o in frame(ev,127) if o['glyph']==event_id);need(d['color']&0xffffff==0x123456,'event diamond ignores its colour')
  t=core.default_settings();rows=rows_of(core.frame(t,1920,1080,{},())[0],tables());need(rows[6]['color']==0xff123456 and rows[7]['color']==0xff654321,'legend rows ignore the colours')
 finally:core.library.re0_frame_reset_colors()
 need(getc(4)==0xb8bcc4,'colours not reset')
 parse=core.library.re0_color_parse;parse.argtypes=[ctypes.c_char_p,ctypes.POINTER(ctypes.c_uint)]
 def read(t):
  v=ctypes.c_uint(0xdead);return (parse(t,ctypes.byref(v)),v.value)
 need(read(b'#B8BCC4')==(1,0xb8bcc4) and read(b'ff9628')==(1,0xff9628) and read(b' #6a6a6a ; grey')==(1,0x6a6a6a),'colour parse')
 need(all(read(t)==(0,0xdead) for t in (b'',b'#12345',b'#1234567',b'#GGGGGG',b'red',b'#12345g')),'bad colours accepted')
 merge=core.library.re0_ini_merge;merge.argtypes=[ctypes.c_char_p,ctypes.c_uint,ctypes.POINTER(ctypes.c_char_p),ctypes.POINTER(ctypes.c_char_p),ctypes.c_uint,ctypes.c_char_p,ctypes.c_char_p,ctypes.c_uint];merge.restype=ctypes.c_uint
 def update(old,pairs,tail=b'',cap=4096):
  keys=(ctypes.c_char_p*len(pairs))(*[k.encode() for k,_ in pairs]);vals=(ctypes.c_char_p*len(pairs))(*[str(v).encode() for _,v in pairs]);out=ctypes.create_string_buffer(cap)
  n=merge(old,len(old),keys,vals,len(pairs),tail,out,cap);return out.raw[:n]
 old=b'; my notes\r\n[Map]\r\nVersion=50 \r\n; keep me\r\nitemnames = 1\r\nIconSize=100\r\n\r\n[Colors]\r\n; mine\r\nEvent=#00FF00\r\nItem=#B8BCC4\r\n'
 got=update(old,[('Version',51),('ItemNames',2),('Contents',127)],b'\r\n[Colors]\r\nnope\r\n')
 want=b'; my notes\r\n[Map]\r\nVersion=51\r\n; keep me\r\nItemNames=2\r\nIconSize=100\r\nContents=127\r\n\r\n[Colors]\r\n; mine\r\nEvent=#00FF00\r\nItem=#B8BCC4\r\n'
 need(got==want,f'merge changed more than the keys: {got!r}')
 need(update(b'',[('Version',51)],b'[Colors]\r\nLock=#FFCD46\r\n')==b'[Map]\r\nVersion=51\r\n[Colors]\r\nLock=#FFCD46\r\n','merge into an empty file')
 need(update(b'[Map]\nVersion=50',[('Version',51),('Legend',1)],b'')==b'[Map]\nVersion=51\r\nLegend=1\r\n','merge without a final newline or CRLF')
 need(update(b'[Maps]\r\nVersion=1\r\n',[('Version',51)],b'')==b'[Maps]\r\nVersion=1\r\n[Map]\r\nVersion=51\r\n','merge matched a section by prefix')
 need(update(old,[('Version',51)],b'',cap=10)==b'','merge overran its buffer')
 need(update(old,[('Version',51)],b'\r\n[Colors]\r\nx=1\r\n').count(b'[Colors]')==1,'merge duplicated [Colors]')
def check(core):
 data=tables();ids=data['ids'];rooms,glyphs,_=catalogue();piece,place=room(rooms,data);seen={piece:[900,300,1300,560]}
 ko,en=data['places'][place][:2];W,H=1920,1080
 def view(s,obstacles=()):return core.frame(s,W,H,seen,obstacles)
 def names(ops):return [o for o in ops if o['glyph'] in (ko,en)]
 s=core.default_settings();ops,places=view(s);rows=rows_of(ops,data);panel=ops[0]['box']
 # Bottom-left panel, user 2026-11-08, two columns: [0]..[4] | [5]..[8] with [9] under [8]; below, [H] under the left column and [\\] under the right, hint size.
 if not (panel[0]<60 and abs(panel[3]-(H-28*H/1440))<1):raise AssertionError('legend is not bottom-left')
 if len(rows)!=9:raise AssertionError('legend rows missing')
 for i in list(range(4))+list(range(5,8)):
  if rows[i]['box'][1]>=rows[i+1]['box'][1] or rows[i]['box'][0]!=rows[i+1]['box'][0]:raise AssertionError(f'column order at row {i}')
 for i in range(4):
  if rows[i+5]['box'][0]<=rows[i]['box'][2] or rows[i+5]['box'][1]!=rows[i]['box'][1]:raise AssertionError('right column does not continue beside the left')
 scope=next((o for o in ops if o['glyph']==ids['scope'][0]),None);lang_=next((o for o in ops if o['glyph']==ids['language'][0]),None);hold_=next((o for o in ops if o['glyph']==ids['hold'][2]),None)
 if not scope or not lang_ or not hold_:raise AssertionError('[9], [H] or [\\] missing')
 if not (scope['box'][0]==rows[5]['box'][0] and rows[8]['box'][1]<scope['box'][1]<hold_['box'][1] and abs(scope['box'][1]-rows[0]['box'][1]-4*(rows[1]['box'][1]-rows[0]['box'][1]))<1):raise AssertionError('[9] is not under [8]')
 if not (hold_['box'][0]==rows[0]['box'][0] and lang_['box'][0]==rows[5]['box'][0] and hold_['box'][1]==lang_['box'][1] and hold_['box'][1]-rows[4]['box'][1]>=(rows[1]['box'][1]-rows[0]['box'][1])-1):raise AssertionError('[H] is not under [4] and [\\] under [9]')
 if lang_['color']!=hold_['color'] or lang_['box'][3]-lang_['box'][1]!=hold_['box'][3]-hold_['box'][1]:raise AssertionError('[\\] differs from [H] in colour or size')
 if hold_['box'][2]>=lang_['box'][0] or lang_['box'][2]>panel[2]:raise AssertionError('[H] and [\\] overlap or leave the panel')
 if ops[1]["glyph"]!=ids["title"][0]:raise AssertionError("title not first")
 for i in range(9):
  if rows[i]['color']!=COLORS[i]:raise AssertionError(f'row {i} lost its colour')
 present=[o['glyph'] for o in ops]
 for key in ('language','hold','hide'):
  if ids[key][2 if key=='hold' else 0] not in present:raise AssertionError(f'{key} missing from legend')
 # Candidate 44: the four readouts sit in their own panel, bottom-right with the legend's margins mirrored, and are not in the legend.
 rects=[o for o in ops if o['glyph']<0 and o['color']==0xd0080808]
 if len(rects)<2:raise AssertionError('readout panel missing')
 readout=rects[1]['box']
 if not (abs(readout[2]-(W-28*H/1440))<1 and abs(readout[3]-(H-28*H/1440))<1):raise AssertionError('readouts are not bottom-right')
 for key in ('opacity','size','icon_opacity','icon_size'):
  g=[o for o in ops if o['glyph']==ids[key][0]]
  if len(g)!=1 or not inside(g[0]['box'],readout) or inside(g[0]['box'],panel):raise AssertionError(f'{key} readout is not in its own panel')
 if ids['scope'][0] not in present:raise AssertionError('[8] does not open on Visited')
 if not names(ops) or not places or places[0]['box'] is None:raise AssertionError('room name missing')
 if not any(o['glyph'] in data['badges'] for o in ops):raise AssertionError('counts missing')
 # 0: names and counts go, every row turns gray, legend stays.
 s=core.default_settings();core.key(s,'0');ops,_=view(s);rows=rows_of(ops,data)
 if len(rows)!=9:raise AssertionError('0 removed the legend')
 if any(r['color']!=OFF for r in rows.values()):raise AssertionError('0 did not gray every row')
 if names(ops) or any(o['glyph'] in data['badges'] for o in ops):raise AssertionError('0 left names or counts')
 core.key(s,'0')
 if not names(view(s)[0]):raise AssertionError('second 0 did not restore names')
 # 1: only names go.
 s=core.default_settings();core.key(s,'1');ops,_=view(s);rows=rows_of(ops,data)
 if rows[1]['color']!=OFF or rows[2]['color']!=COLORS[2]:raise AssertionError('1 legend state wrong')
 if names(ops):raise AssertionError('1 left names')
 if not any(o['glyph'] in data['badges'] for o in ops):raise AssertionError('1 removed counts')
 # 2-8: each row turns gray and its badge goes; the row order is the legend's, not the category ids'.
 for c,key in enumerate('2345678'):
  s=core.default_settings();core.key(s,key);ops,_=view(s);rows=rows_of(ops,data)
  if rows[2+c]['color']!=OFF or rows[(2+c+1-2)%7+2]['color']==OFF:raise AssertionError(f'{key} row state wrong')
  if s.mask!=127&~(1<<LEGEND_CATEGORY[c]):raise AssertionError(f'{key} cleared the wrong category')
  if any(o['glyph']==data['badges'][LEGEND_CATEGORY[c]] for o in ops):raise AssertionError(f'{key} left its badge')
 # 9 (scope), the backslash (language) and the setting values.
 s=core.default_settings();kept=s.difficulty
 for turn in (1,2,0):
  if not core.key(s,'9'):raise AssertionError('9 not saved')
  if ids['scope'][turn*2] not in [o['glyph'] for o in view(s)[0]]:raise AssertionError('9 value not shown')
 if s.difficulty!=kept:raise AssertionError('9 changed the difficulty')
 s=core.default_settings();core.key(s,'\\');ops,_=view(s)
 if len(rows_of(ops,data,1))!=9 or ids['language'][1] not in [o['glyph'] for o in ops]:raise AssertionError('backslash language not shown')
 if not s.english:raise AssertionError('backslash did not switch the language')
 s=core.default_settings();core.key(s,'\\');core.key(s,'\\')
 if s.english:raise AssertionError('second backslash did not switch back')
 s=core.default_settings();core.key(s,'+');core.key(s,']')
 if (s.size,s.opacity)!=(110,70):raise AssertionError('size/opacity keys')
 for _ in range(30):core.key(s,'-');core.key(s,'[')
 if (s.size,s.opacity)!=(50,10):raise AssertionError('size/opacity limits')
 # Selection: panel directly above the legend; . past the end closes.
 s=core.default_settings();core.key(s,'.',rooms=seen)
 if s.selected!=place:raise AssertionError('. did not select the visible room')
 ops,_=view(s);legend=ops[0]['box'];panels=[o for o in ops[1:] if o['glyph']<0 and (o['color']>>24)==0xc0]
 if len(panels)!=1 or panels[0]['box'][3]>legend[1]:raise AssertionError('panel overlaps the legend')
 if len(rows_of(ops,data))!=9:raise AssertionError('panel removed the legend')
 core.key(s,'.',rooms=seen)
 if s.selected!=-1:raise AssertionError('. past the end did not close')
 # ~ folds the legend to one hint line; the readouts stay and a second press restores it.
 s=core.default_settings()
 if not core.key(s,'`'):raise AssertionError('~ not saved')
 ops,_=view(s);g=[o['glyph'] for o in ops]
 if rows_of(ops,data) or ids['title'][0] in g or ids['fold'][0] not in g or ids['hold'][2] in g:raise AssertionError('~ did not fold the legend to its hint')
 box=ops[0]['box']
 if not (box[0]<60 and abs(box[3]-(H-28*H/1440))<1) or (box[3]-box[1])>(panel[3]-panel[1])/3:raise AssertionError('folded hint is not a small bottom-left box')
 if any(ids[k][0] in g for k in ('opacity','size','icon_opacity','icon_size')) or len([o for o in ops if o['glyph']<0 and o['color']==0xd0080808])!=1:raise AssertionError('~ left the readouts up') # user 2026-11-06: they go with the legend
 if not names(ops):raise AssertionError('~ hid room names')
 core.key(s,'`');ops,_=view(s)
 if len(rows_of(ops,data))!=9 or ops[0]['box']!=panel:raise AssertionError('second ~ did not restore the legend')
 # Held H hides names only.
 s=core.default_settings();s.hidden=1;ops,_=view(s)
 if names(ops) or len(rows_of(ops,data))!=9:raise AssertionError('H must hide names and keep the legend')
 # Leader line: none when the label sits in its room, present when an obstacle pushes it out.
 def solids(ops):return [o for o in ops[1:] if o['glyph']<0 and o['color']!=0xd0080808] # not the legend's or the readouts' panel
 s=core.default_settings();ops,_=view(s)
 if solids(ops):raise AssertionError('leader drawn for a label inside its room')
 small={piece:[900,300,990,340]};ops,found=core.frame(s,W,H,small,[[900,280,990,360]])
 if found[0]['box'] is None:raise AssertionError('displaced label not placed')
 line=solids(ops)
 if not line:raise AssertionError('displaced label has no leader line')
 tip=[o for o in line if abs((o['box'][0]+o['box'][2])/2-945)<1 and abs((o['box'][1]+o['box'][3])/2-320)<1]
 if not tip:raise AssertionError('leader does not end at the room centre')
 # Location markers: same call the review page makes.
 lib=core.library;lib.re0_frame_marker_count.restype=__import__('ctypes').c_uint
 m=tables_markers();l2=[int(v) for v in re.search(r'marker_line2\[\] = \{([0-9,]+)\}',(Path(__file__).resolve().parents[1]/'src/runtime/labels_generated.h').read_text())[1].split(',')];first=next(i for i,d in enumerate(m) if d[6]!=7 and l2[i*2]==65535);a=m[first];seen={i:[1900,4,1901,5] for i,r in enumerate(rooms) if i==a[2]};view=(1.5,0,0);only=[0 if i==first else 1 for i in range(len(m))]
 s=core.default_settings();s.mask=127;s.difficulty=[b for b in range(3) if a[6]>>b&1][0]
 ops,_=core.frame(s,W,H,seen,(),view,only)
 g=[o for o in ops if o['glyph']==a[3]]
 if not g:raise AssertionError('marker name missing')
 if any(o['glyph'] in data['badges'] for o in ops):raise AssertionError('counts drawn beside location markers')
 cx,cy=a[0]*1.5,a[1]*1.5;b=g[0]['box']
 if not (b[0]>cx and abs((b[1]+b[3])/2-cy)<1):raise AssertionError('name is not right of its mark when the slot is free')
 first_icon=int(re.search(r'#define ICON_FIRST_GLYPH (\d+)',(Path(__file__).resolve().parents[1]/'src/runtime/labels_generated.h').read_text())[1]);marks=[o for o in ops if o['glyph']>=first_icon and o['box'][0]<=cx<=o['box'][2] and o['box'][1]<=cy<=o['box'][3]]
 if not marks:raise AssertionError('mark not at its projected position')
 # Least-covered slot: an obstacle on the right moves the name, off-screen slots are refused.
 ops2,_=core.frame(s,W,H,seen,[[b[0]-2,b[1]-2,b[2]+2,b[3]+2]],view,only);b2=[o for o in ops2 if o['glyph']==a[3]][0]['box']
 if b2==b:raise AssertionError('name ignored a covering obstacle')
 # Filters: category off, marker off, other difficulty, piece not drawn.
 s3=core.default_settings();s3.difficulty=s.difficulty;s3.mask=127&~(1<<a[5])
 if [o for o in core.frame(s3,W,H,seen,(),view,only)[0] if o['glyph']==a[3]]:raise AssertionError('category filter ignored')
 if [o for o in core.frame(s,W,H,seen,(),view,[1]*len(m))[0] if o['glyph']==a[3]]:raise AssertionError('marker_off ignored')
 if [o for o in core.frame(s,W,H,{},(),view)[0] if o['glyph']==a[3]]:raise AssertionError('marker shown for a piece the game did not draw')
 # Names are the set size zoomed in and 70% of it zoomed out; the map's own zoom decides, not the mark's position.
 first_mark=m[first];zw=lambda v:[o['box'][2]-o['box'][0] for o in core.frame(s,W,H,seen,(),v,only)[0] if o['glyph']==a[3]]
 outw,inw=zw((1.5,0,0)),zw((4.5,900-first_mark[0]*4.5,500-first_mark[1]*4.5))
 if not outw or not inw or abs(outw[0]/inw[0]-.7)>.001:raise AssertionError(f'name size not following zoom: {outw} {inw}')
 # Native pan only translates at full zoom, so the name keeps its size wherever the map is.
 panw=zw((4.5,300-first_mark[0]*4.5,200-first_mark[1]*4.5))
 if not panw or abs(panw[0]-inw[0])>.001:raise AssertionError(f'name size follows the pan: {inw} {panw}')
 # User 2026-11-05: a puzzle is the ! diamond, an event the ? diamond in its own colour, until its flag is set.
 header=(Path(__file__).resolve().parents[1]/'src/runtime/labels_generated.h').read_text();mark_id=lambda n:int(re.search(rf'#define {n} (\d+)',header).group(1))
 need=[int(r.split(',')[8]) for r in re.findall(r'\{([0-9,]+)\}',header.split('marker_state[] = {',1)[1].split('};',1)[0])]
 ei=next(i for i,d in enumerate(m) if d[11] and need[i]==0xffff);ev=m[ei];eo=[1]*len(m);eo[ei]=0
 ni=next(i for i,d in enumerate(m) if d[11] and need[i]!=0xffff);no=[1]*len(m);no[ni]=0
 old_scope=s.scope;s.scope=2;nf=[0]*33;nf[need[ni]>>5]=1<<(need[ni]&31);nb={m[ni][2]:[v*1.5 for v in tables_canvas(m[ni][2])]};drawn=lambda f:[q for q in core.frame(s,W,H,nb,(),(1.5,0,0),no,f)[0] if q['glyph']==mark_id('EVENT_MARK_ID')]
 if drawn([0]*33) or not drawn(nf):raise AssertionError('event does not follow its precondition')
 s.scope=old_scope
 pi=next(i for i,d in enumerate(m) if d[5]==3 and not d[11]);pu=m[pi];po=[1]*len(m);po[pi]=0
 for d,o,want in ((ev,eo,'EVENT_MARK_ID'),(pu,po,'PUZZLE_MARK_ID')):
  if not [q for q in core.frame(s,W,H,{d[2]:[v*1.5 for v in tables_canvas(d[2])]},(),(1.5,0,0),o,None)[0] if q['glyph']==mark_id(want)]:raise AssertionError('wrong mark for '+want)
 # Top tier: a key name moves off a covering obstacle and goes with 1.
 ki0=next(i for i,d in enumerate(m) if d[5]==1 and d[6]>>s.difficulty&1);k0=m[ki0];konly0=[1]*len(m);konly0[ki0]=0;kseen={k0[2]:[1900,4,1901,5]}
 kb=[o for o in core.frame(s,W,H,kseen,(),view,konly0)[0] if o['glyph']==k0[3]][0]['box']
 kb2=[o for o in core.frame(s,W,H,kseen,[[kb[0]-2,kb[1]-2,kb[2]+2,kb[3]+2]],view,konly0)[0] if o['glyph']==k0[3]][0]['box']
 if kb2==kb:raise AssertionError('key name ignored a covering obstacle')
 s8=core.default_settings();s8.item_names=0;s8.difficulty=s.difficulty
 if [o for o in core.frame(s8,W,H,kseen,(),view,konly0)[0] if o['glyph']==k0[3]]:raise AssertionError('key name shown with names off')
 real_floor_rules(core,rooms,view);icon_sizes(core);item_name_states(core);category_rules(core)
 # Every near slot blocked: the name goes further out rather than vanish.
 blocked=[[700,380,1200,660]];ops7,_=core.frame(s,W,H,{a[2]:[900,500,1000,540]},blocked,None);far=[o for o in ops7 if o['glyph'] in place_glyphs(data)]
 if not far:raise AssertionError('crowded room lost its name')
 if any(o['box'][0]<1200 and o['box'][2]>700 and o['box'][1]<660 and o['box'][3]>380 for o in far):raise AssertionError('name placed on an obstacle')
 # Room names give way to marks: a mark at the room centre pushes the name off it, as hollow room-level marks would.
 ki=next(i for i,d in enumerate(m) if d[5]==1 and d[6]>>s.difficulty&1);kk=m[ki];cx0,cy0=kk[0]*1.5,kk[1]*1.5;konly=[1]*len(m);konly[ki]=0;centred={kk[2]:[cx0-150,cy0-60,cx0+150,cy0+60]};ops5,_=core.frame(s,W,H,centred,(),view,konly);room_names=[o for o in ops5 if o['glyph'] in place_glyphs(data)]
 if not room_names:raise AssertionError('room name dropped')
 if any(o['box'][0]<cx0+13.5 and o['box'][2]>cx0-13.5 and o['box'][1]<cy0+13.5 and o['box'][3]>cy0-13.5 for o in room_names):raise AssertionError('room name covers a mark')
 # A common icon whose middle lies on a key mark's middle is not drawn; one that only touches stays. Every real close pair, each pair alone.
 tx=(Path(__file__).resolve().parents[1]/'src/runtime/labels_generated.h').read_text();ic=[int(v) for v in re.search(r'marker_icon_glyphs\[\] = \{([0-9,]+)\}',tx)[1].split(',')];pairs=0
 for ci,c in enumerate(m):
  if c[5]<4 or c[8]:continue
  for ki,kq in enumerate(m):
   if kq[5]==1 and not kq[8] and kq[2]==c[2] and kq[6]&c[6] and ic[ki]!=ic[ci] and abs(kq[0]-c[0])<2.4 and abs(kq[1]-c[1])<2.4:
    s9=core.default_settings();s9.mask=127;s9.scope=2;s9.difficulty=[b for b in range(8) if kq[6]&c[6]>>b&1 or (kq[6]&c[6])>>b&1][0];off9=[0 if q in (ci,ki) else 1 for q in range(len(m))];g9=[o['glyph'] for o in core.frame(s9,W,H,{c[2]:[300,200,420,300]},(),(1.5,0,0),off9,[0]*33)[0]]
    if ic[ki] in g9:
     pairs+=1
     if ic[ci] in g9:raise AssertionError('common mark kept on a key mark')
 if not pairs:raise AssertionError('no close common and key pair left to test the drop rule')
 # Finished rows go: a flag-finished row with its flag set, a table row with kind 0.
 text=(ROOT/'src/runtime/labels_generated.h').read_text();st=[[int(v) for v in x.split(',')] for x in re.findall(r'\{([0-9,]+)\}',text.split('marker_state[] = {',1)[1].split('};',1)[0])]
 fi=next(i for i,x in enumerate(st) if x[3]!=0xffff);fw=[0]*33;fw[st[fi][3]>>5]=1<<(st[fi][3]&31)
 if core.marker_done(fi,[0]*33) or not core.marker_done(fi,fw):raise AssertionError('finished flag not followed')
 ri=next(i for i,x in enumerate(st) if x[1]!=0xffff and x[7]==0x71);row=0x30+st[ri][1]*0x5c;buf=bytearray(0x30+0x4e8*0x5c);__import__('struct').pack_into('<III',buf,row,st[ri][6],st[ri][7],st[ri][5] if st[ri][5]!=0xffff else 0)
 import ctypes;from core import ArrangeView
 raw=ctypes.create_string_buffer(bytes(buf),len(buf));view2=ArrangeView(589,ctypes.cast(raw,ctypes.c_char_p),0)
 if core.marker_done(ri,None,view2):raise AssertionError('untaken row counted as taken')
 raw[row+4:row+8]=b'\0\0\0\0';view2=ArrangeView(589,ctypes.cast(raw,ctypes.c_char_p),0)
 if not core.marker_done(ri,None,view2):raise AssertionError('taken row not followed')
 # An enemy row: live stays, marked gone or killed in a loaded room goes; an actor of another row's item does not. Row+0x41 and row+8 are written for live actors too.
 ei=next(i for i,x in enumerate(st) if x[1]!=0xffff and x[7] and x[7]<0x60);ir=0x30+st[ei][1]*0x5c;eb=bytearray(0x30+0x4e8*0x5c);__import__('struct').pack_into('<III',eb,ir,st[ei][6],st[ei][7],9);eb[ir+0x41]=1
 er=ctypes.create_string_buffer(bytes(eb),len(eb));bits=(ctypes.c_uint*0x28)();ev=lambda:ArrangeView(589,ctypes.cast(er,ctypes.c_char_p),0,bits)
 if core.marker_done(ei,None,ev()):raise AssertionError('live enemy counted as killed')
 hit=[0]*0x28;hit[st[ei][1]>>5]=1<<(st[ei][1]&31);bits[:]=hit
 if not core.marker_done(ei,None,ev()):raise AssertionError('kill in a loaded room not followed')
 bits[:]=[0]*0x28;er[ir+0x39]=b'\x01'
 if not core.marker_done(ei,None,ev()):raise AssertionError('killed row not followed')
 # A conditional row follows the game's flag: off when clear or unknown, on when set.
 ci,c=next((i,x) for i,x in enumerate(m) if x[8] and x[5]!=5 and x[6]>>s.difficulty&1);off=[1]*len(m);off[ci]=0;cseen={c[2]:[300,200,420,300]}
 sc=core.default_settings();sc.difficulty=s.difficulty;sc.scope=2 # the row's flag alone decides, whatever was visited
 def shown_with(flags):return [o for o in core.frame(sc,W,H,cseen,(),view,off,flags)[0] if o['glyph']==c[3]]
 flag=0x312+c[8];words=[0]*33;words[flag>>5]=1<<(flag&31)
 if shown_with(None) or shown_with([0]*33):raise AssertionError('conditional row shown with its flag clear')
 if not shown_with(words):raise AssertionError('conditional row hidden with its flag set')
 other=[d for d in range(3) if not a[6]>>d&1]
 if other:
  s6=core.default_settings();s6.difficulty=other[0]
  if [o for o in core.frame(s6,W,H,seen,(),view,only)[0] if o['glyph']==a[3]]:raise AssertionError('difficulty filter ignored')
 s4=core.default_settings();s4.item_names=0;s4.difficulty=s.difficulty;ops4,_=core.frame(s4,W,H,seen,(),view,only)
 if [o for o in ops4 if o['glyph']==a[3]]:raise AssertionError('1 left marker names')
 if not [o for o in ops4 if o['glyph']>=first_icon and o['box'][0]<=cx<=o['box'][2]]:raise AssertionError('1 removed marks')
 if any(o['glyph'] in data['badges'] for o in core.frame(core.default_settings(),W,H,{piece:[900,300,1300,560]},(),view,[1]*len(m))[0]):raise AssertionError('counts drawn beside location markers')
 s5=core.default_settings();s5.enabled=0
 if len([o for o in core.frame(s5,W,H,seen,(),view,only)[0] if o['glyph']==a[3]]):raise AssertionError('0 left marker names')
 scope_rules(core,data,rooms,m)
def word_bits(flags):
 words=[0]*33
 for f in flags:words[f>>5]|=1<<(f&31)
 return words
def scope_rules(core,data,rooms,m):
 """Native rule in data/room-state.json. Boxes are the static ones, so the fixed view holds, as on the page."""
 import json
 load=lambda n:json.loads((ROOT/'data'/n).read_text());native=load('native-map.json');rule=load('room-state.json')['pieces'];rows=load('placements.json')['rows'];index={p['id']:i for i,p in enumerate(native['map_pieces'])}
 sys.path.insert(0,str(ROOT/'tools'));from build_labels import marker_defs
 text=(ROOT/'src/runtime/labels_generated.h').read_text();canvas=[[float(v.rstrip('f')) for v in x.split(',')] for x in re.findall(r'\{([0-9.,f]+)\}',text.split('piece_canvas[] = {',1)[1].split('};',1)[0])];layout=[x.split(',') for x in re.findall(r'\{([0-9.,f]+)\}',text.split('room_layout[] = {',1)[1].split('};',1)[0])]
 defs=marker_defs(dict(rows=rows),native);W,H=1920,1080;view=(1.5,0,0)
 box=lambda *ids:{index[p]:[v*1.5 for v in canvas[index[p]]] for p in ids};mark=lambda cat,name,room:next(i for i,d in enumerate(defs) if rows[d['row']]['category']==cat and rows[d['row']]['name_en']==name and rows[d['row']]['room']==room)
 name_of=lambda piece:int(next(r for r in layout if int(r[0])==index[piece] and int(r[3])==0)[2])
 def glyphs(scope,drawn,flags,v=view):
  s=core.default_settings();s.scope=scope;return [o['glyph'] for o in core.frame(s,W,H,box(*drawn),(),v,None,flags)[0]]
 # Live report: Ice Pick on i_tr0ca0 while the game draws i_tr0ca1. Same for the room's name, which has one row on the first piece.
 ice=mark('key','Ice Pick',12);words=word_bits(rule['i_tr0ca1']['visited'])
 if m[ice][2]!=index['i_tr0ca0']:raise AssertionError('Ice Pick moved off the piece the report is about')
 if m[ice][3] not in glyphs(0,['i_tr0ca1'],words):raise AssertionError('mark gone with the second piece drawn')
 if m[ice][3] not in glyphs(0,['i_tr0ca0'],words):raise AssertionError('mark gone with the first piece drawn')
 if name_of('i_tr0ca0') not in glyphs(0,['i_tr0ca1'],words):raise AssertionError('room name gone with the second piece drawn')
 # The same place on another floor does not count: the mark sits on its own floor.
 pieces=native['map_pieces'];up=next((d,q) for d,x in zip(defs,m) for q in pieces if not x[10] and rooms[q_i:=index[q['id']]][6]==rooms[x[2]][6] and rooms[q_i][2]!=rooms[x[2]][2]);above=defs.index(up[0])
 if m[above][3] in glyphs(0,[up[1]['id']],word_bits(rule[up[1]['id']]['visited'])):raise AssertionError('mark shown from another floor')
 # A door's mark: either room joined by the door, nothing else on the floor. Conductor's Key: i_tr0290 and i_tr0390.
 door=mark('lock',"Conductor's Key",2);other=lambda p:word_bits(rule[p]['visited'])
 for p in ('i_tr0290','i_tr0390'):
  if m[door][3] not in glyphs(0,[p],other(p)):raise AssertionError(f'door mark gone from {p}')
 if m[door][3] in glyphs(0,['i_tr0090'],other('i_tr0090')):raise AssertionError('door mark shown from a room it does not join')
 # Scope, on a room's name and its mark. Visited: entered. Revealed: entered or its map held. All: the whole floor of anything drawn.
 a,b='i_tr0090','i_tr0190';room=name_of(b);v=word_bits(rule[a]['visited']);both=word_bits(rule[a]['visited']+rule[a]['revealed'])
 cases=[(0,v,0),(1,v,0),(2,v,1),(0,both,0),(1,both,1),(2,both,1)]
 for scope,flags,want in cases:
  if (room in glyphs(scope,[a,b],flags))!=bool(want):raise AssertionError(f'scope {scope} flags {flags[20:24]}: room name should be {want}')
 undrawn=next(p['id'] for p in native['map_pieces'] if p['region']=='tr' and p['floor']=='1f' and p['id'] not in (a,b) and any(int(r[0])==index[p['id']] for r in layout))
 if name_of(undrawn) not in glyphs(2,[a],v):raise AssertionError('All scope lost an undrawn room')
 if name_of(undrawn) in glyphs(0,[a],v) or name_of(undrawn) in glyphs(1,[a],both):raise AssertionError('undrawn room shown below All scope')
 if [g for g in glyphs(2,[],v) if g==name_of(undrawn)]:raise AssertionError('All scope drew a floor the game did not')
 other_floor=next(p['id'] for p in native['map_pieces'] if p['region']=='tr' and p['floor']=='2f' and any(int(r[0])==index[p['id']] for r in layout))
 if name_of(other_floor) in glyphs(2,[a],v):raise AssertionError('All scope opened another floor')
 # Room panel: selection steps through what the scope allows, and All can pick an undrawn room and box it.
 s=core.default_settings();core.key(s,'.',rooms=box(a,b),flags=v);place=rooms[index[a]][6]
 if s.selected!=place:raise AssertionError('selection did not take the visited room')
 core.key(s,'.',rooms=box(a,b),flags=v)
 if s.selected!=-1:raise AssertionError('selection took a room outside the scope')
 s=core.default_settings();s.scope=2;s.selected=rooms[index[undrawn]][6];ops,_=core.frame(s,W,H,box(a),(),view,None,v);c=[x*1.5 for x in canvas[index[undrawn]]]
 if not any(o['color']==0xffffe040 and abs(o['box'][1]+2-c[1])<1 for o in ops):raise AssertionError('All scope panel has no box for an undrawn room')
 s.difficulty=3;ops,_=core.frame(s,W,H,box(a),(),view,None,v)
 if any(o['color']==0xffffe040 for o in ops):raise AssertionError('Leech Hunter drew the room panel')
 # Unknown flags: what was drawn counts, as the capture replay of an old report has none.
 s=core.default_settings();ops,_=core.frame(s,W,H,box(b),(),view)
 if room not in [o['glyph'] for o in ops]:raise AssertionError('unknown flags hid a drawn room')

