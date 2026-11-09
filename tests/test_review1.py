"""User emulator review 2026-11-05: one check per defect."""
import json,re,sys,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
for f in ('tools','tests','emulator'):sys.path.insert(0,str(ROOT/f))
from build_labels import WEAPONS,short_ko,icon_for,marker_label
from core import Core
from frame_contract import tables_markers,word_bits
H=(ROOT/'src/runtime/labels_generated.h').read_text();define=lambda n:int(re.search(rf'#define {n} (\d+)',H)[1])
ints=lambda n:[int(v) for v in re.search(n+r'\[\] = \{([0-9,]+)\}',H)[1].split(',')]
GLYPHS=[tuple(map(int,g)) for g in re.findall(r'\{(\d+),(\d+),(\d+),(\d+)\},',H.split('glyphs[] = {')[1].split('};')[0])]
ROWS=json.loads((ROOT/'data/placements.json').read_text())['rows'];NATIVE=json.loads((ROOT/'data/native-map.json').read_text())['map_pieces'];RULE=json.loads((ROOT/'data/room-state.json').read_text())['pieces'];MANIFEST=json.loads((ROOT/'assets/icons/manifest.json').read_text())
def frame(core,m,k=1.5,flags=None,**kw):
 s=core.default_settings();[setattr(s,a,b) for a,b in kw.items()]
 return core.frame(s,1920,1080,{m[2]:[300,200,420,300]},(),(k,960-m[0]*k,540-m[1]*k),None,flags or word_bits(RULE[NATIVE[m[2]]['id']]['visited']))[0]
class Review(unittest.TestCase):
 def test_1_diamond_symbols_centred_with_a_separate_dot(self):
  # Live, candidate 33: ! read as one line, ? off centre with no dot. Checked at each mip level used, 96 down to 24 px, as the texture stores them.
  side,levels=define('ICON_TEX'),define('ICON_LEVELS');blob=(ROOT/'assets/icons.bgra').read_bytes();at=0
  for l in range(3):
   w=side>>l;h_=define('ICON_TEX_H')>>l;im=Image.frombytes('RGBA',(w,h_),blob[at:at+w*h_*4],'raw','BGRA');at+=w*h_*4
   for mark in ('PUZZLE_MARK_ID','EVENT_MARK_ID'):
    x,y,gw,gh=GLYPHS[define(mark)];c=im.crop((x>>l,y>>l,(x+gw)>>l,(y+gh)>>l));s=c.width;inner=[(i,j) for j in range(int(s*.2),int(s*.82)) for i in range(int(s*.3),int(s*.7)) if c.getpixel((i,j))[0]<110]
    xs=[p[0] for p in inner];self.assertLess(abs((min(xs)+max(xs))/2-(s-1)/2),1.6+s*.03,(mark,l))
    rows=sorted({p[1] for p in inner});gaps=[b-a for a,b in zip(rows,rows[1:]) if b-a>1];self.assertTrue(gaps,(mark,l,'dot joined to the stem'))
 def test_1_events_have_no_name(self):
  core=Core();seen=0
  for m in tables_markers():
   if m[11] and m[6]>>1&1:
    g=[o['glyph'] for o in frame(core,m)];seen+=define('EVENT_MARK_ID') in g;self.assertFalse({m[3],m[4]}&set(g),'event name drawn')
  self.assertTrue(seen)
 def test_1_event_stands_beside_a_key_it_overlaps(self):
  core=Core();ms=tables_markers();icons=ints('marker_icon_glyphs');found=0
  for i,e in enumerate(ms):
   if not e[11]:continue
   for j,k in enumerate(ms):
    if k[5]==1 and k[2]==e[2] and not k[8] and abs(k[0]-e[0])<4 and abs(k[1]-e[1])<4:
     off=[0 if n in(i,j) else 1 for n in range(len(ms))];s=core.default_settings();rooms={e[2]:[300,200,420,300]}
     ops=core.frame(s,1920,1080,rooms,(),(1.5,960-e[0]*1.5,540-e[1]*1.5),off,word_bits(RULE[NATIVE[e[2]]['id']]['visited']))[0]
     a=[o['box'] for o in ops if o['glyph']==icons[j]];b=[o['box'] for o in ops if o['glyph']==define('EVENT_MARK_ID')]
     if a and b:found+=1;self.assertLess(max(a[0][0]+1,b[0][0]+1),min(a[0][2],b[0][2])+9,'stacked');self.assertGreater(abs((a[0][0]+a[0][2])-(b[0][0]+b[0][2]))/2,10,'stacked')
  self.assertTrue(found,'no event on a key in the data: use a synthetic pair')
 def test_2_lock_shows_its_key(self):
  n=MANIFEST['names'];self.assertEqual(icon_for(dict(category='lock',name_en='Iron Needle'),n),'Iron Needle');self.assertEqual(icon_for(dict(category='lock',name_en='Shaft Key (L)'),n),'Shaft Key');self.assertEqual(icon_for(dict(category='lock',name_en='No Such Key'),n),'Padlock')
 def test_3_no_leader_past_the_limit_unless_listed(self):
  far=sorted({r['piece'] for r in json.loads((ROOT/'data/room-layout.json').read_text())['rows'] if r['line'] and abs(r['line'][0]-r['line'][2])+abs(r['line'][1]-r['line'][3])>64})
  self.assertLessEqual(len(far),KNOWN_FAR,far)
 def test_5_same_pickup_listed_twice_shows_once(self):
  # Battery, sh-2f: a table row behind a condition flag and a script row at the same spot, both visible.
  core=Core();ms=tables_markers();icons=ints('marker_icon_glyphs');i=next(i for i,m in enumerate(ms) if m[5]==1 and m[8] and any(o[8]==0 and (o[0],o[1],o[3])==(m[0],m[1],m[3]) for o in ms));m=ms[i]
  flags=list(word_bits(RULE[NATIVE[m[2]]['id']]['visited']));f=0x312+m[8];flags[f>>5]|=1<<(f&31)
  g=[o['glyph'] for o in frame(core,m,flags=flags)];self.assertEqual(g.count(icons[i]),1);self.assertEqual(g.count(m[3]),1)
 def test_4b_mark_follows_the_name_ratio(self):
  core=Core();ms=tables_markers();icons=ints('marker_icon_glyphs')
  # Candidate 45, user 2026-11-06: enemies are not enlarged; keys on doors are 120% (zoomed out) to 150% (3x) of the 1.3 base; every other icon 100% to 130% of it. 18.9 and 27 are 18*screen*the name zoom at game zoom and 3x.
  expect={0:(1.3*.96*1.1,1.3*1.5*1.1),1:(1.3*1.1,1.3*1.3*1.1),2:(1.3,1.3*1.3),3:(1.3,1.3*1.3),4:(1.3,1.3*1.3),5:(1.0,1.0)}
  for cat,(near,far) in expect.items():
   glyph=lambda j:define('PUZZLE_MARK_ID') if cat==3 else icons[j] # a puzzle's diamond reaches 2/9 past its square
   j,m=next((j,m) for j,m in enumerate(ms) if m[5]==cat and not m[11] and glyph(j)!=define('NO_ICON') and any(o['glyph']==glyph(j) for o in frame(core,m)))
   size=lambda k:next(o['box'][3]-o['box'][1] for o in frame(core,m,k=k) if o['glyph']==glyph(j));diamond=11/9 if cat==3 else 1
   self.assertAlmostEqual(size(1.5),18.9*1.2*near*diamond,places=1,msg=cat);self.assertAlmostEqual(size(4.5),27*1.2*far*diamond,places=1,msg=cat)
  mid=ms[next(j for j,m in enumerate(ms) if m[5]==1 and not m[8] and m[6]>>1&1)] # halfway along the curve: t=.5 is k=3
  j=ms.index(mid);half=next(o['box'][3]-o['box'][1] for o in frame(core,mid,k=3.0) if o['glyph']==icons[j]);self.assertAlmostEqual(half,18*1.5*.85*1.2*1.3*1.15*1.1,places=1)
 def test_6_rooms_are_drawn_by_piece_not_by_box(self):
  # Live defect: one piece per box hid sections of a room, leaving its items on the background.
  self.assertNotIn('painted.has',(ROOT/'tools/build_placement_review.py').read_text())
 def test_6_marks_lie_in_their_rooms_unless_listed(self):
  self.assertEqual([r for r in ROWS if r.get('x') is not None and r['category']!='lock' and r.get('distance',0)>2.2 and r['evidence']=='arrange table' and r['category']!='enemy'],[])
 def test_7_weapons_are_key_items(self):
  got=[r for r in ROWS if r['name_en'] in WEAPONS];self.assertTrue(got)
  for r in got:self.assertEqual(r['category'],'key',r['name_en'])
 def test_8a_possessive(self):
  for a,b in (('샷건의 탄약','샷건 탄약'),('양성소의 지도','양성소 지도'),('선의 서','선의 서'),('악의 서','악의 서')):self.assertEqual(short_ko(a),b)
  self.assertEqual(marker_label(dict(name_en='x',name_ko='샷건의 탄약',amount={'normal':7},category='item'),'normal',0,None),'샷건 탄약 ×7')
 def test_8b_every_map_name_wraps_by_the_rule(self):
  from build_labels import split_label,marker_defs
  self.assertEqual(split_label('샷건 탄약 ×7'),('샷건 탄약','×7'));self.assertEqual(split_label('Machinegun Ammo 50%'),('Machinegun Ammo','50%'));self.assertEqual(split_label('Blue Key'),('Blue','Key'));self.assertEqual(split_label('짧은 이름'),('짧은 이름',None));self.assertEqual(split_label('긴이름공백없는것'),('긴이름공백없는것',None));self.assertEqual(split_label('Hookshot'),('Hookshot',None))
  defs=marker_defs(json.loads((ROOT/'data/placements.json').read_text()),json.loads((ROOT/'data/native-map.json').read_text()));ms=tables_markers();l2=ints('marker_line2');self.assertEqual(len(l2),2*len(ms))
  for i,d in enumerate(defs):
   for j,k in enumerate(('ko','en')):
    a,b=split_label(d[k]);named=d['category']!=5 and not d['event']
    if b:self.assertEqual(a+' '+b,d[k]) # nothing lost, no word split
    self.assertEqual(l2[i*2+j]!=define('NO_LINE'),bool(b and named),d[k])
 def test_8b_wrapped_box_alignment_and_collision(self):
  core=Core();ms=tables_markers();l2=ints('marker_line2');no=define('NO_LINE');icons=ints('marker_icon_glyphs');n=0
  for i,m in enumerate(ms):
   if l2[i*2]==no or m[8] or not m[6]>>1&1:continue
   s=core.default_settings();s.scope=2;off=[0 if q==i else 1 for q in range(len(ms))];view=(1.5,960-m[0]*1.5,540-m[1]*1.5);rooms={m[2]:[300,200,420,300]};flags=word_bits(RULE[NATIVE[m[2]]['id']]['visited'])
   ops=core.frame(s,1920,1080,rooms,(),view,off,flags)[0];a=next((o['box'] for o in ops if o['glyph']==m[3]),None);b=next((o['box'] for o in ops if o['glyph']==l2[i*2]),None)
   if not a or not b:continue
   self.assertGreater(b[1],a[1]);n+=1
   if a[0]>960:self.assertAlmostEqual(a[0],b[0],places=2) # free right slot: icon on the left, left-aligned
   # An obstacle on the whole wrapped box moves it: line 2 counts for collisions.
   ops2=core.frame(s,1920,1080,rooms,[[b[0]+1,b[1]+8,b[2]-1,b[3]-1]],view,off,flags)[0];c=next((o['box'] for o in ops2 if o['glyph']==l2[i*2]),None)
   if c and n==1:self.assertNotEqual(c,b)
  self.assertGreater(n,50)
 def test_all_locks_use_their_key_when_the_manifest_has_it(self):
  from build_labels import LOCK_ICON
  n=MANIFEST['names'];rows=[r for r in ROWS if r['category']=='lock' and r.get('x') is not None];self.assertEqual(len(rows),20)
  for r in rows:
   self.assertEqual(icon_for(r,n),LOCK_ICON.get(r['name_en'],r['name_en']),r['name_en']) # every lock has its key's art, no padlock left
 def test_all_duplicate_groups_show_once(self):
  core=Core();ms=tables_markers();icons=ints('marker_icon_glyphs');groups={}
  for i,m in enumerate(ms):groups.setdefault((m[5],m[3],ints('marker_line2')[i*2],m[0],m[1]),[]).append(i)
  groups=[v for v in groups.values() if len(v)>1];self.assertTrue(groups);checked=0
  for v in groups:
   m=ms[v[0]];modes=[b for b in range(3) if all(ms[i][6]>>b&1 for i in v)]
   if not modes or m[5]==3:continue # a diamond has no icon glyph per row; its name is off for events
   s=core.default_settings();s.difficulty=modes[0];s.scope=2;flags=list(word_bits(RULE[NATIVE[m[2]]['id']]['visited']))
   for i in v:
    if ms[i][8]:f=0x312+ms[i][8];flags[f>>5]|=1<<(f&31)
   off=[0 if q in v else 1 for q in range(len(ms))];g=[o['glyph'] for o in core.frame(s,1920,1080,{m[2]:[300,200,420,300]},(),(1.5,960-m[0]*1.5,540-m[1]*1.5),off,flags)[0]]
   self.assertLessEqual(g.count(icons[v[0]]),1,m);checked+=g.count(icons[v[0]])
  self.assertTrue(checked)
 def test_all_events_beside_every_key_they_overlap(self):
  core=Core();ms=tables_markers();icons=ints('marker_icon_glyphs');n=0
  for i,e in enumerate(ms):
   if not e[11]:continue
   for j,k in enumerate(ms):
    if k[5]!=1 or k[2]!=e[2] or abs(k[0]-e[0])>=12.6 or abs(k[1]-e[1])>=12.6 or not k[6]&e[6]:continue
    s=core.default_settings();s.scope=2;s.difficulty=[b for b in range(3) if (k[6]&e[6])>>b&1][0];flags=list(word_bits(RULE[NATIVE[e[2]]['id']]['visited']))
    if k[8]:f=0x312+k[8];flags[f>>5]|=1<<(f&31)
    if e[8]:f=0x312+e[8];flags[f>>5]|=1<<(f&31)
    ops=core.frame(s,1920,1080,{e[2]:[300,200,420,300]},(),(1.5,960-e[0]*1.5,540-e[1]*1.5),[0 if q in(i,j) else 1 for q in range(len(ms))],flags)[0]
    a=[o['box'] for o in ops if o['glyph']==icons[j]];b=[o['box'] for o in ops if o['glyph']==define('EVENT_MARK_ID')]
    if a and b:n+=1;self.assertLessEqual(max(a[0][0],b[0][0]+2.1),min(a[0][2],b[0][2]-2.1)+.1,(i,j))
  self.assertTrue(n)
 def test_all_item_names_lose_the_possessive(self):
  from build_labels import KEEP_UI,korean,category
  names=json.loads((ROOT/'data/names-ko.json').read_text())['names'];cont=json.loads((ROOT/'data/room-contents.json').read_text())
  labels={r['name_ko'] for r in ROWS if r['category']!='enemy'}|{korean(r['name'],names) for p in cont['places'] for r in p['contents'] if category(r) is not None}
  self.assertGreater(len(labels),100)
  for n in labels:
   if n not in KEEP_UI and not any(n.startswith(k) for k in KEEP_UI):self.assertNotIn('의 ',short_ko(n),n)
 def test_all_marks_within_12px_of_their_room(self):
  import hashlib
  A=json.loads((ROOT/'verification/mark-room-audit.json').read_text());self.assertEqual(A['placements_sha256'],hashlib.sha256((ROOT/'data/placements.json').read_bytes()).hexdigest(),'rerun the audit');self.assertGreater(A['checked'],700);self.assertEqual(A['over_12'],0)
 def test_no_mark_keeps_a_placeholder_position(self):
  for r in ROWS:
   if r.get('world') and r['world'][1]<-1000 and r.get('x') is not None:self.assertTrue(r.get('placeholder_position'),r['name_en'])
 def test_all_conditional_twins_near_each_other_show_once(self):
  core=Core();ms=tables_markers();icons=ints('marker_icon_glyphs');n=0
  for i,a_ in enumerate(ms):
   for j,b in enumerate(ms):
    if i<j and a_[5]==b[5]!=5 and a_[5]!=3 and a_[3]==b[3] and ints('marker_line2')[i*2]==ints('marker_line2')[j*2] and a_[2]==b[2] and bool(a_[8])!=bool(b[8]) and abs(a_[0]-b[0])<4 and abs(a_[1]-b[1])<4 and a_[6]&b[6]:
     s=core.default_settings();s.scope=2;s.difficulty=[q for q in range(3) if (a_[6]&b[6])>>q&1][0];flags=list(word_bits(RULE[NATIVE[a_[2]]['id']]['visited']));f=0x312+(a_[8] or b[8]);flags[f>>5]|=1<<(f&31)
     g=[o['glyph'] for o in core.frame(s,1920,1080,{a_[2]:[300,200,420,300]},(),(1.5,960-a_[0]*1.5,540-a_[1]*1.5),[0 if q in(i,j) else 1 for q in range(len(ms))],flags)[0]]
     self.assertEqual(g.count(a_[3]),1,a_);n+=1
  self.assertGreaterEqual(n,8)
KNOWN_FAR=1 # Narrow Corridor B, English, 70 px: no spot free of marks and names on its corridor
if __name__=='__main__':unittest.main()
