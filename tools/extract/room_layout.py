"""Fix room names when data is generated, by the rules in RE2's tools/mapgen/generate_room_names.py (place_labels), in the map GUI's 1280x720 space.

Names never move at runtime. Tightest rooms first; inside the room's real shape when the name fits (8, 4, 0 px from walls, then 80% of it, then wrapped between
words); otherwise on an axis-aligned leader from a mask pixel, shortest into free space, then outside the floor's bounds. Names never overlap key items, documents,
locks, puzzles, doors or the legend; they may cover common items and enemies. Violations stop the build. Masks are alpha of the game's own room sprites.
"""
import argparse,concurrent.futures,hashlib,json,math,os,sys
from pathlib import Path
from PIL import Image,ImageChops,ImageDraw,ImageFilter
ROOT=Path(__file__).resolve().parents[2]
for folder in ('emulator','tools','tools/inspect','tools/extract'):sys.path.insert(0,str(ROOT/folder))
from render import render,decode_texture
from resources import Arc
GRID=2 # canvas px per cell; all geometry below is in cells
W,H=1280//GRID,720//GRID
SCALE=.88*.8*1.1*.7*20/30 # room names 20% smaller, RE2 Remake style, then +10%: the user's 110% setting became size 100 (candidate 44) # canvas px per atlas px at size 100: frame.c room k is screen*1.1*NAME_SCALE, and screen px per canvas px is screen
FIT,SMALL=.9,.8
MARGINS=(4,2,0)
TILE_MARGIN=12 # both sides of build_labels PAD for names
DOOR_GAP=7 # cells; a piece's outline is open at its doors (26 canvas px wide), closed before filling
LEADER_CLEAR,LEADER_MARGIN=4,6
KEEP=('key','file','lock','puzzle')
MARK=12.6/GRID # mark side at its largest on canvas: frame.c is=18*screen*zoom_name, .7 at game zoom, and zooming in spreads the canvas faster than the mark grows
def inputs():
 names=('data/placements.json','data/room-matches.json','data/native-map.json','verification/label-build.json')
 return {n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names[:3]}
def textures(game):
 arcs=[Arc((game/'nativePC/arc/ui'/n).read_bytes()) for n in ('map_eng.arc','map.arc')];cache={}
 def get(path):
  if path not in cache:
   for a in arcs:
    m=next((m for m in a.members if m.kind==0x241f5deb and m.name==path),None)
    if m:cache[path]=decode_texture(a.read(m));break
  return cache[path]
 return get
def piece_masks(game,region,floor,get,known,fill=False):
 """Piece id -> set of occupied cells and its canvas box."""
 _,trace=render(game,region,floor);images={};boxes={}
 for d in trace['drawn']:
  if d['instance'] not in known:continue
  b=d['canvas_box'];l,t,r,bt=[int(v) for v in b];p=boxes.get(d['instance'],b);boxes[d['instance']]=[min(b[0],p[0]),min(b[1],p[1]),max(b[2],p[2]),max(b[3],p[3])]
  if fill!=d['texture'].endswith('_b_ID') and (fill or d['texture'].endswith('_b_ID')):continue # the translucent floor sheet (alpha about 93) is the room's floor, walls are the _a sheet
  if 'map_text' in d['texture']:continue # the floor title sheet, not room shape; it still counts in the box, as the ASI's capture does
  tile=get(d['texture']).crop(tuple(int(v) for v in d['uv'])).getchannel('A').resize((max(1,(r-l)//GRID),max(1,(bt-t)//GRID)),Image.Resampling.BILINEAR)
  image=images.setdefault(d['instance'],Image.new('L',(W,H)));layer=Image.new('L',(W,H));layer.paste(tile,(l//GRID,t//GRID));images[d['instance']]=ImageChops.lighter(image,layer)
 cut=20 if fill else 128;return {k:v.point(lambda a:255 if a>cut else 0) for k,v in images.items()},boxes
def dilate(image,n):
 for _ in range(n):image=image.filter(ImageFilter.MaxFilter(3))
 return image
def silhouette(opaque):
 """The room's shape. Sprite alpha holds walls and dark areas; the light floor is a transparent hole, so it must be filled in, not read as outside."""
 pad=DOOR_GAP+2;big=Image.new('L',(W+pad*2,H+pad*2));big.paste(opaque,(pad,pad));closed=dilate(big,DOOR_GAP)
 ImageDraw.floodfill(closed,(0,0),128)
 filled=closed.point(lambda v:0 if v==128 else 255)
 return ImageChops.lighter(erode(filled,DOOR_GAP),big).crop((pad,pad,pad+W,pad+H))
def cells(image):
 return {(i%W,i//W) for i,v in enumerate(image.tobytes()) if v}
def erode(image,n):
 for _ in range(n):image=image.filter(ImageFilter.MinFilter(3))
 return image
class Sat:
 def __init__(self,occupied):
  self.t=[[0]*(W+1) for _ in range(H+1)]
  for y in range(H):
   run=0;row=self.t[y+1];up=self.t[y]
   for x in range(W):
    run+=(x,y) in occupied;row[x+1]=up[x+1]+run
 def sum(self,x,y,w,h):
  a,b,c,d=max(0,x),max(0,y),min(W,x+w),min(H,y+h)
  if c<=a or d<=b:return 0
  t=self.t;return t[d][c]-t[b][c]-t[d][a]+t[b][a]
def hit(a,b):return a[0]<b[0]+b[2] and b[0]<a[0]+a[2] and a[1]<b[1]+b[3] and b[1]<a[1]+a[3]
def fit_inside(image,own,lw,lh,placed):
 """Label centre whose box sits on the shape, nearest its centroid."""
 pts=cells(image)
 if not pts:return None
 sat=Sat(pts);cx,cy=sum(p[0] for p in pts)/len(pts),sum(p[1] for p in pts)/len(pts);xs=[p[0] for p in pts];ys=[p[1] for p in pts];best=None
 for scale,need in ((1.0,FIT),(SMALL,1.0)):
  bw,bh=max(1,round(lw*scale)),max(1,round(lh*scale))
  for by in range(min(ys)-bh//2,max(ys)-bh//2+1):
   for bx in range(min(xs)-bw//2,max(xs)-bw//2+1):
    cov=sat.sum(bx,by,bw,bh)/(bw*bh)
    if cov<need:continue
    px,py=bx+bw//2,by+bh//2
    if (px,py) not in pts or any(hit((px-lw//2,py-lh//2,lw,lh),b) for b in placed):continue
    score=(px-cx)**2+(py-cy)**2-cov*400
    if best is None or score<best[0]:best=(score,px,py)
  if best:return best[1:]
 return None
def depth_map(pts):
 """Chamfer distance (cells) from each cell of the shape to the nearest cell outside it."""
 xs=[p[0] for p in pts];ys=[p[1] for p in pts];x0,y0=min(xs)-1,min(ys)-1;w,h=max(xs)-x0+2,max(ys)-y0+2;big=10**6
 d=[[big if (x+x0,y+y0) in pts else 0 for x in range(w)] for y in range(h)]
 for y in range(1,h):
  for x in range(1,w-1):d[y][x]=min(d[y][x],d[y][x-1]+3,d[y-1][x]+3,d[y-1][x-1]+4,d[y-1][x+1]+4)
 for y in range(h-2,-1,-1):
  for x in range(w-2,0,-1):d[y][x]=min(d[y][x],d[y][x+1]+3,d[y+1][x]+3,d[y+1][x+1]+4,d[y+1][x-1]+4)
 return {(x+x0,y+y0):d[y][x]/3 for y in range(h) for x in range(w) if d[y][x]}
def pole(pts):
 """Pole of inaccessibility: the cell of the shape farthest from its edge; ties go nearest the centroid."""
 depth=depth_map(pts);cx,cy=sum(p[0] for p in pts)/len(pts),sum(p[1] for p in pts)/len(pts)
 return max(depth,key=lambda p:(depth[p],-((p[0]-cx)**2+(p[1]-cy)**2))),depth
def interior_spot(pts,sat,centre,lw,lh,placed):
 """Label centre on the shape with the most of its box on the shape, nearest the pole; None when every spot hits a placed box."""
 found=[]
 for px,py in pts:
  box=(px-lw//2,py-lh//2,lw,lh)
  if any(hit(box,b) for b in placed):continue
  found.append((sat.sum(*box)/(lw*lh),px,py))
 if not found:return None
 top=max(f[0] for f in found);floor=1.0 if top>=1.0 else top-.05
 c=min((f for f in found if f[0]>=floor),key=lambda f:(f[1]-centre[0])**2+(f[2]-centre[1])**2)
 return c[1],c[2],c[0]
def along_outline(occ,line):
 """A leader may not share a line with a room outline: away from its room's corners and clear of walls beside it."""
 sx,sy,ex,ey=line;px,py=(1,0) if sx==ex else (0,1);a=b=0
 while occ.get((sx+px*(a+1),sy+py*(a+1)))==occ.get((sx,sy)):a+=1
 while occ.get((sx-px*(b+1),sy-py*(b+1)))==occ.get((sx,sy)):b+=1
 if min(a,b)<min(LEADER_MARGIN,(a+b)//2) or not a+b:return True
 dx,dy=(ex>sx)-(ex<sx),(ey>sy)-(ey<sy)
 return any(occ.get((sx+dx*k+px*d,sy+dy*k+py*d))!=occ.get((sx+dx*k,sy+dy*k)) for k in range(1,max(abs(ex-sx),abs(ey-sy))+1) for d in (-LEADER_CLEAR,-2,2,LEADER_CLEAR))
def line_box(line):
 lo_x,hi_x=sorted((line[0],line[2]));lo_y,hi_y=sorted((line[1],line[3]));return lo_x,lo_y,hi_x-lo_x+1,hi_y-lo_y+1
LEADER_MAX=30 # cells: 60 canvas px. A name further out than this no longer reads as its room's (user 2026-11-05)
def near_spot(own,occ,blocked,lw,lh,placed,lines,kmax=LEADER_MAX):
 """Shortest axis-aligned leader from a mask edge cell to a box in free space."""
 best=None
 for sx,sy in sorted(own):
  for dx,dy in ((0,-1),(0,1),(-1,0),(1,0)):
   if (sx+dx,sy+dy) in own:continue
   for k in range(1,kmax):
    if best and k>=best[0]:break
    ex,ey=sx+dx*k,sy+dy*k
    if (ex,ey) in occ:break
    line=(sx,sy,ex,ey)
    if along_outline(occ,line):continue
    for sh in (0,6,-6,12,-12,18,-18):
     if (abs(sh)>lw//2-2 and dy) or (abs(sh)>lh//2-1 and dx):continue
     box=(ex-lw//2+sh,ey-lh+1 if dy<0 else ey,lw,lh) if dy else (ex-lw+1 if dx<0 else ex,ey-lh//2+sh,lw,lh)
     if box[0]<1 or box[1]<1 or box[0]+lw>W-1 or box[1]+lh>H-1 or blocked.sum(*box):continue
     if any(hit(box,b) for b in placed) or any(hit(line_box(line),b) for b in placed) or any(hit(box,line_box(o)) for o in lines):continue
     cost=k+abs(sh)*.1
     if best is None or cost<best[0]:best=(cost,box[0]+lw//2,box[1]+lh//2,line,box)
 return best
def outside_bounds(px,occ,row_id,bounds,lw,lh,placed,lines,fixed):
 """Fallback: outside the floor's bounds, which may cross another room at a right angle."""
 bx0,by0,bx1,by1=bounds;best=None
 for side in ('top','bottom','left','right'):
  key=0 if side in('top','bottom') else 1;vals=sorted({p[key] for p in px});n=len(vals)
  for i,c in enumerate(dict.fromkeys((vals[n//2],vals[n//4],vals[n*3//4],*vals[::4]))):
   run=[p for p in px if p[key]==c];sx,sy=(min(run,key=lambda p:p[1]) if side=='top' else max(run,key=lambda p:p[1])) if key==0 else (min(run,key=lambda p:p[0]) if side=='left' else max(run,key=lambda p:p[0]))
   for along in (0,1,-1):
    for ring in range(40):
     if side=='top':ly=by0-3-lh//2-ring*(lh+1);lx=c+along*(lw//3);line=(c,sy,c,ly+lh//2)
     elif side=='bottom':ly=by1+3+lh//2+ring*(lh+1);lx=c+along*(lw//3);line=(c,sy,c,ly-lh//2)
     elif side=='left':lx=bx0-3-lw//2-ring*(lw+2);ly=c+along*(lh//2+1);line=(sx,c,lx+lw//2,c)
     else:lx=bx1+3+lw//2+ring*(lw+2);ly=c+along*(lh//2+1);line=(sx,c,lx-lw//2,c)
     box=(lx-lw//2,ly-lh//2,lw,lh)
     if box[0]<1 or box[1]<1 or box[0]+lw>W-1 or box[1]+lh>H-1 or any(hit(box,b) for b in placed):continue
     lb=line_box(line)
     if any(hit(lb,b) for b in placed[fixed:]) or any(hit(box,line_box(o)) for o in lines):continue # hard rules: this ring fails, the next may pass
     crossed=sum((x,y) in occ and occ[(x,y)]!=row_id for y in range(lb[1],lb[1]+lb[3]) for x in range(lb[0],lb[0]+lb[2]))
     cost=(crossed>0)*1000+sum(hit(lb,b) for b in placed[:fixed])*3000+along_outline(occ,line)*2000+lb[2]+lb[3]+abs(along)*4+i # a line may pass a mark, at a price
     if best is None or cost<best[0]:best=(cost,lx,ly,line,box)
     break
 return best
def fit_over(image,lw,lh,placed,need=.25):
 """User: inside the room beats fitting its width. Centred on the room's shape, may run over its walls; never on a mark or another name."""
 pts=cells(image)
 if not pts:return None
 sat=Sat(pts);cx,cy=sum(p[0] for p in pts)/len(pts),sum(p[1] for p in pts)/len(pts);best=None
 for px,py in pts:
  box=(px-lw//2,py-lh//2,lw,lh)
  if box[0]<1 or box[1]<1 or box[0]+lw>W-1 or box[1]+lh>H-1 or sat.sum(*box)/(lw*lh)<need or any(hit(box,b) for b in placed):continue
  score=(px-cx)**2+(py-cy)**2
  if best is None or score<best[0]:best=(score,px,py)
 return best[1:] if best else None
def even_up(v):
 """Cells, rounded up to even so a box centred on a cell holds the real name exactly; odd sizes let two names touch in real pixels."""
 v=math.ceil(v);return v+v%2
def ink_size(text):
 """Name size in cells without the atlas tile's transparent margin, which counted as text and sent names out of rooms they fit."""
 from build_labels import measure
 return tuple(even_up((v-TILE_MARGIN)*SCALE/GRID) for v in measure(text))
def split(text):
 """Two-line break between words nearest the middle; None for one word."""
 parts=text.split(' ')
 if len(parts)<2:return None
 at=min(range(1,len(parts)),key=lambda i:abs(len(' '.join(parts[:i]))-len(' '.join(parts[i:]))));return ' '.join(parts[:at])+'\n'+' '.join(parts[at:])
def place_floor(rows,marks,legend,size_of):
 """RE2 Remake style (user 2026-11-06), candidate 44: each name at the pole of inaccessibility of its room's shape, not the bounding box centre; a corridor too narrow for it gets a leader instead. A one-line name wider
 than 150% of the room wraps. Names ignore marks: they are drawn first and anything may cover them. Names keep off each other and the legend."""
 occ={}
 for r in rows:
  for c in r['cells']:occ[c]=id(r)
 xs=[c[0] for c in occ];ys=[c[1] for c in occ];bounds=(min(xs),min(ys),max(xs),max(ys))
 blocked=Sat({(x+i,y+j) for x,y in occ for j in(-1,0,1) for i in(-1,0,1)})
 placed=list(legend);lines=[];out={};later=[]
 for r in sorted(rows,key=lambda r:len(r['cells'])):
  cs=r['cells'];x0,x1=min(c[0] for c in cs),max(c[0] for c in cs);y0,y1=min(c[1] for c in cs),max(c[1] for c in cs);bw,bh=x1-x0+1,y1-y0+1
  text=r['name'];lw,lh=size_of(text)
  if lw>1.5*bw and split(text):text=split(text);lw,lh=size_of(text)
  sat=Sat(cs);centre=pole(cs)[0];ideal=interior_spot(cs,sat,centre,lw,lh,[])
  corridor=min(bw,bh)<lh*2 and ideal[2]<.5
  spot=None
  if not corridor:
   spot=interior_spot(cs,sat,centre,lw,lh,placed) or fit_inside(r['image'],cs,lw,lh,placed)
  if spot:out[id(r)]=dict(text=text,x=spot[0],y=spot[1],line=None);placed.append((spot[0]-lw//2,spot[1]-lh//2,lw,lh));continue
  later.append((r,text))
 for r,text in sorted(later,key=lambda q:(min(c[1] for c in q[0]['cells']),min(c[0] for c in q[0]['cells']))):
  lw,lh=size_of(text);px=r['cells'];best=near_spot(px,occ,blocked,lw,lh,placed,lines) or outside_bounds(sorted(px),occ,id(r),bounds,lw,lh,placed,lines,len(legend))
  if not best:raise ValueError('no place for '+r['name'])
  _,x,y,line,box=best;out[id(r)]=dict(text=text,x=x,y=y,line=line);placed.append(box);lines.append(line)
 return out
def check_floor(rows,out,marks,legend,size_of):
 """The rules, restated apart from the search: a defect here stops generation."""
 occ={c for r in rows for c in r['cells']};boxes={}
 for r in rows:
  o=out[id(r)];lw,lh=size_of(o['text']);boxes[id(r)]=(o['x']-lw//2,o['y']-lh//2,lw,lh);b=boxes[id(r)]
  if b[0]<0 or b[1]<0 or b[0]+lw>W or b[1]+lh>H:raise ValueError('off screen: '+r['name'])
  for m in [*marks,*legend]:
   if hit(b,m):raise ValueError(f"{r['name']} overlaps a mark or the legend")
  if o['line'] and any((x,y) in occ for y in range(b[1],b[1]+lh) for x in range(b[0],b[0]+lw)):raise ValueError(f"outside name on a room: {r['name']}")
  if not o['line'] and (o['x'],o['y']) not in r['cells']:raise ValueError(f"name anchor outside its room shape: {r['name']}")
  if o['line'] and tuple(o['line'][:2]) not in r['cells']:raise ValueError(f"leader starts off its room: {r['name']}")
 ids=list(boxes)
 for i,a in enumerate(ids):
  for b in ids[i+1:]:
   if hit(boxes[a],boxes[b]):raise ValueError('room names overlap')
 for r in rows:
  o=out[id(r)]
  if o['line']:
   for s in rows:
    if s is not r and hit(line_box(o['line']),boxes[id(s)]):raise ValueError(f"leader of {r['name']} runs through {s['name']}")
def layout_floor(job):
 """Every name on one floor, in both languages: (piece boxes, rows)."""
 from build_labels import measure
 game,region,name,legends=job
 native=json.loads((ROOT/'data/native-map.json').read_text());data=json.loads((ROOT/'data/placements.json').read_text());matches=json.loads((ROOT/'data/room-matches.json').read_text())
 owner={p:c for c in matches['claims'] for p in [*c['native_pieces'],*[a['piece'] for a in c.get('alias_pieces',[])]]}
 pieces={p['id']:p for p in native['map_pieces']};get=textures(game);masks,boxes=piece_masks(game,region,name,get,pieces);fills,_=piece_masks(game,region,name,get,pieces,fill=True);rows_out=[]
 ids=[i for i in masks if i in pieces];groups={}
 for i in ids:
  groups.setdefault(owner[i]['external_id'],[]).append(i)
 marks=[]
 for r in data['rows']:
  if r.get('x') is not None and r['region']==region and r['floor']==name and r['category'] in KEEP:
   grow=1 if r.get('event') else 0 # the event diamond is wider than a square mark
   marks.append((int(r['x']/GRID-MARK/2)-1-grow,int(r['y']/GRID-MARK/2)-1-grow,int(MARK)+3+2*grow,int(MARK)+3+2*grow))
   # frame.c moves a lock or document centred on a key or puzzle mark down and right by is*.6; keep that place clear too.
   if r['category'] in ('lock','file') and any(o is not r and o.get('x') is not None and o['region']==region and o['floor']==name and o['category'] in ('key','puzzle') and not o.get('event') and abs(o['x']-r['x'])<12.6 and abs(o['y']-r['y'])<12.6 for o in data['rows']):
    d=12.6*.6/GRID;marks.append((int(r['x']/GRID-MARK/2+d)-1,int(r['y']/GRID-MARK/2+d)-1,int(MARK)+3,int(MARK)+3))
 try:
  _,door_trace=render(game,region,name,group_suffix='_door',geometry_only=True)
  marks+=[(int(d['ink_box'][0]//GRID),int(d['ink_box'][1]//GRID),int((d['ink_box'][2]-d['ink_box'][0])//GRID)+1,int((d['ink_box'][3]-d['ink_box'][1])//GRID)+1) for d in door_trace['drawn']]
 except ValueError as e:
  if 'floor group not found' not in str(e):raise
 shapes={}
 for lang,key in enumerate(('name_ko','name_en')):
  rows=[]
  for ext,group in groups.items():
   image=Image.new('L',(W,H))
   opaque=Image.new('L',(W,H))
   for i in group:image=ImageChops.lighter(ImageChops.lighter(image,silhouette(masks[i])),fills.get(i,image));opaque=ImageChops.lighter(opaque,masks[i])
   claim=owner[group[0]];rows.append(dict(image=image,floor=ImageChops.subtract(image,opaque),cells=cells(image),name=claim[key],anchor=max(group,key=lambda i:(boxes[i][2]-boxes[i][0])*(boxes[i][3]-boxes[i][1]))))
  if not rows:continue
  size_of=ink_size
  out=place_floor(rows,[],legends[lang],size_of);check_floor(rows,out,[],legends[lang],size_of) # names no longer avoid marks
  for r in rows:
   shapes[r['anchor']]=runs(r['cells'])
   o=out[id(r)];rows_out.append(dict(piece=r['anchor'],lang=lang,text=o['text'],x=o['x']*GRID,y=o['y']*GRID,line=[v*GRID for v in o['line']] if o['line'] else None))
 return boxes,rows_out,shapes
def runs(cells):
 """A shape as [y,x0,x1] runs in canvas px: the room-layout.json evidence that each anchor lies inside its room."""
 out=[]
 for y in sorted({c[1] for c in cells}):
  xs=sorted(c[0] for c in cells if c[1]==y);a=xs[0];p=a
  for x in xs[1:]+[None]:
   if x is None or x!=p+1:out.append([y*GRID,a*GRID,p*GRID+GRID-1]);a=x
   p=x
 return out
def generate(game):
 from build_labels import measure,marker_defs
 from core import Core
 native=json.loads((ROOT/'data/native-map.json').read_text());data=json.loads((ROOT/'data/placements.json').read_text());matches=json.loads((ROOT/'data/room-matches.json').read_text())
 owner={p:c for c in matches['claims'] for p in [*c['native_pieces'],*[a['piece'] for a in c.get('alias_pieces',[])]]}
 pieces={p['id']:p for p in native['map_pieces']};core=Core();get=textures(game);piece_box={};rows_out=[]
 legends=[]
 for english in (0,1):
  s=core.default_settings();s.english=english;ops=core.frame(s,1920,1080,{},())[0];boxes=[o['box'] for o in ops if o['glyph']<0 and o['color']==0xd0080808][:2] # legend, then the name/icon readouts
  legends.append([tuple(int(v/1.5/GRID) for v in b[:2])+tuple(int((b[i+2]-b[i])/1.5/GRID)+2 for i in (0,1)) for b in boxes])
 # One floor is 2 to 6 s of pure Python and floors share nothing, so one process each. Results keep floor order, so the file does not depend on scheduling.
 with concurrent.futures.ProcessPoolExecutor(max_workers=max(1,(os.cpu_count() or 2)-1)) as pool:
  done=list(pool.map(layout_floor,[(game,f['region'],f['floor'],legends) for f in native['floors']]))
 shape_out={}
 for boxes,rows,shapes in done:
  piece_box.update(boxes);rows_out+=rows;shape_out.update(shapes)
 return dict(schema_version=1,evidence='generated from game sprite alpha and project placements; rule source RE2 tools/mapgen/generate_room_names.py',inputs_sha256=inputs(),pieces=piece_box,shapes=shape_out,rows=rows_out)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game',type=Path,required=True);a=p.parse_args();r=generate(a.game);(ROOT/'data/room-layout.json').write_text(json.dumps(r,ensure_ascii=False,indent=0)+'\n')
 print(f"{len(r['rows'])} placements; inside {sum(not x['line'] for x in r['rows'])}, leader {sum(bool(x['line']) for x in r['rows'])}, wrapped {sum(chr(10) in x['text'] for x in r['rows'])}")
