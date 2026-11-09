"""Suggest external-place to native-piece matches by floor geometry; output needs visual review, it is not evidence."""
import argparse,json,sys
from pathlib import Path
from PIL import Image,ImageChops,ImageDraw
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'emulator'))
FLOORS={'tr':'train','sh':'training-facility','dm':'facility-basement','ch':'laboratory','bt':'factory','pl':'treatment-plant'}
def polygons(area):
 c=area['coords']
 if area['shape']=='rect':return [(c[0],c[1]),(c[2],c[1]),(c[2],c[3]),(c[0],c[3])]
 if area['shape'] in ('poly','polygon'):return list(zip(c[0::2],c[1::2]))
 if area['shape']=='circle':return [(c[0]-c[2],c[1]-c[2]),(c[0]+c[2],c[1]-c[2]),(c[0]+c[2],c[1]+c[2]),(c[0]-c[2],c[1]+c[2])]
 raise ValueError('unsupported area shape')
def fit(image,external):
 """Best uniform scale/offset between external room union and non-background native pixels, on a half-size grid."""
 small=image.convert('RGB').resize((640,360));bg=small.getpixel((0,0))
 target=small.point(lambda v:v).convert('L');target=ImageChops.difference(small,Image.new('RGB',small.size,bg)).convert('L').point(lambda v:255 if v>12 else 0).convert('1')
 el=min(p[0] for ps in external for p in ps);et=min(p[1] for ps in external for p in ps);bb=target.getbbox()
 def search(scales,centre,reach,step):
  found=(-1,)
  for k in scales:
   sc=k/100/2;union=raster([[((p[0]-el)*sc,(p[1]-et)*sc) for p in ps] for ps in external],small.size)
   for dy in range(centre[1]-reach,centre[1]+reach+1,step):
    for dx in range(centre[0]-reach,centre[0]+reach+1,step):
     moved=ImageChops.offset(union,dx,dy);score=ImageChops.logical_and(moved,target).histogram()[-1]/max(ImageChops.logical_or(moved,target).histogram()[-1],1)
     if score>found[0]:found=(score,k,dx,dy)
  return found
 best=search(range(116,136,4),(bb[0],bb[1]),24,4)
 if best[0]<.85:
  wide=search(range(116,136,4),(bb[0],bb[1]),120,6)
  if wide[0]>best[0]:best=wide
 best=search(range(best[1]-3,best[1]+4),(best[2],best[3]),6,1)
 best=(best[0],best[1]/100,best[2]*2,best[3]*2)
 return best[1],best[2]-el*best[1],best[3]-et*best[1],best[0]
def raster(polys,size):
 m=Image.new('1',size);d=ImageDraw.Draw(m)
 for p in polys:d.polygon(p,fill=1)
 return m
def suggest(game,out):
 from render import render
 native=json.loads((ROOT/'data/native-map.json').read_text());external=json.loads((ROOT/'data/external-locations.json').read_text())
 result=[]
 for floor in native['floors']:
  key=FLOORS[floor['region']]+'-'+floor['floor']
  places=[l for l in external['locations'] if l['id'].split('/')[0]==key]
  image,trace=render(game,floor['region'],floor['floor']);boxes={}
  for r in trace['drawn']:
   b=r['canvas_box'];p=boxes.get(r['instance'],b);boxes[r['instance']]=[min(b[0],p[0]),min(b[1],p[1]),max(b[2],p[2]),max(b[3],p[3])]
  if not boxes or not places:result.append(dict(floor=key,error='no geometry'));continue
  scale,ox,oy,quality=fit(image,[polygons(a) for l in places for a in l['areas']])
  def to_native(p):return (ox+p[0]*scale,oy+p[1]*scale)
  size=image.size;shapes={l['id']:[[to_native(p) for p in polygons(a)] for a in l['areas']] for l in places}
  masks={k:raster(v,size) for k,v in shapes.items()};rows=[]
  for piece,b in boxes.items():
   m=raster([[(b[0],b[1]),(b[2],b[1]),(b[2],b[3]),(b[0],b[3])]],size);area=max(ImageChops.logical_and(m,m).histogram()[-1],1);scores=[]
   for k,e in masks.items():
    inter=ImageChops.logical_and(m,e).histogram()[-1];scores.append((inter/area,k))
   scores.sort(reverse=True);rows.append(dict(piece=piece,box=b,best=scores[0][1],cover=round(scores[0][0],3),second=scores[1][1] if len(scores)>1 else None,second_cover=round(scores[1][0],3) if len(scores)>1 else 0))
  covered={r['best'] for r in rows}
  result.append(dict(floor=key,scale=scale,fit_iou=round(quality,3),rows=rows,uncovered=[l['id'] for l in places if l['id'] not in covered]))
  vis=image.convert('RGBA');d=ImageDraw.Draw(vis)
  for k,ps in shapes.items():
   for p in ps:d.polygon(p,outline=(255,40,40,255))
   x=sum(q[0] for q in ps[0])/len(ps[0]);y=sum(q[1] for q in ps[0])/len(ps[0]);d.text((x-20,y-5),k.split('/')[1][:14],fill=(255,255,0,255))
  for r in rows:d.rectangle(r['box'],outline=(40,220,255,255));d.text((r['box'][0]+1,r['box'][1]+1),r['piece'][2:],fill=(120,255,255,255))
  vis.save(out/(key+'.png'))
 (out/'suggestions.json').write_text(json.dumps(result,indent=1)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 a.output.mkdir(parents=True,exist_ok=True)
 for f in suggest(a.game,a.output):
  if 'error' in f:print(f);continue
  print(f"{f['floor']} scale={f['scale']} iou={f['fit_iou']} uncovered={f['uncovered']}")
  for r in f['rows']:print(f"  {r['piece']:<10} {r['best'].split('/')[1]:<28} {r['cover']:.2f}  | {(r['second'] or '/').split('/')[1]:<24} {r['second_cover']:.2f}")
