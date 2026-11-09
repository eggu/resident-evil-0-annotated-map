"""Shared-C label replay for native draw captures or explicitly synthetic resource previews."""
import argparse,json,re
from pathlib import Path
from PIL import Image,ImageDraw
from core import Core
ROOT=Path(__file__).resolve().parents[1]
def catalogue():
 text=(ROOT/'src/runtime/labels_generated.h').read_text()
 def rows(name):
  part=text.split(name+'[] = {',1)[1].split('};',1)[0]
  return [tuple(map(int,m)) for m in re.findall(r'\{([0-9,]+)\}',part) for m in [m.split(',')]]
 W=int(re.search(r'#define ATLAS_W (\d+)',text)[1]);H=int(re.search(r'#define ATLAS_H (\d+)',text)[1])
 image=Image.frombytes('RGBA',(W,H),(ROOT/'assets/labels.bgra').read_bytes(),'raw','BGRA')
 return rows('rooms'),rows('glyphs'),image
def tables():
 """Place/content tables and short ID lists, parsed from the header the ASI compiles."""
 text=(ROOT/'src/runtime/labels_generated.h').read_text()
 def rows(name):
  part=text.split(name+'[] = {',1)[1].split('};',1)[0]
  return [tuple(map(int,m.split(','))) for m in re.findall(r'\{([0-9,]+)\}',part)]
 def ints(name):return [int(v) for v in re.search(name+r'\[\] = \{([0-9,]+)\}',text)[1].split(',')]
 ids={name:ints(name+'_ids') for name in ('mode','panel','badge','digit','small_digit','row','title','opacity','size','scope','language','hold','hide','fold','icon_opacity','icon_size')}
 return dict(places=rows('places'),contents=rows('contents'),ids=ids,badges=ids['badge'],modes=ids['mode'])

def replay(capture,background=None):
 if capture.get('schema_version')!=1 or capture.get('evidence') not in ('captured-native-draw','synthetic-resource-preview'):
  raise ValueError('unsupported capture schema/evidence')
 if capture.get('profile_sha256')!='67418c3a307b49e9bde8123df4cad1fa910f3a29adc3e4c0ba64eb96524bc14b':raise ValueError('unsupported capture profile')
 if not isinstance(capture['region'],int) or not 0<=capture['region']<6 or len(capture['rooms'])>138:raise ValueError('invalid capture identity/count')
 W,H=capture['target']
 if not isinstance(W,int) or not isinstance(H,int) or not 320<=W<=8192 or not 200<=H<=8192:raise ValueError('invalid target')
 region=capture['region'];settings=capture['settings']
 core=Core();cfg=core.default_settings()
 for key,field in [('enabled','enabled'),('names','names'),('english','english'),('size','size'),('opacity','opacity'),('difficulty','difficulty'),('contents','mask'),('selected','selected'),('scope','scope')]:
  if key in settings:
   if not isinstance(settings[key],int):raise ValueError('invalid settings')
   setattr(cfg,field,settings[key])
 if not 50<=cfg.size<=150 or not 10<=cfg.opacity<=100 or cfg.english not in (0,1) or cfg.difficulty not in (0,1,2) or not 0<=cfg.mask<=127 or cfg.scope not in (0,1,2):raise ValueError('invalid settings')
 rooms,glyphs,atlas=catalogue();image=Image.new('RGBA',(W,H),(45,48,50,255)) if background is None else background.convert('RGBA').copy()
 if image.size!=(W,H):raise ValueError('background/capture size mismatch')
 used=[list(b) for b in capture['obstacles']];seen={}
 if len(used)>256:raise ValueError('too many obstacles')
 import math
 if any(len(b)!=4 or not all(isinstance(v,(float,int)) and math.isfinite(v) and abs(v)<131072 for v in b) or b[0]>=b[2] or b[1]>=b[3] for b in used):raise ValueError('invalid obstacles')
 for row in capture['rooms']:
  i=row['index']
  if not isinstance(i,int) or not 0<=i<len(rooms) or i in seen or rooms[i][0]!=region:raise ValueError('invalid/duplicate room identity')
  seen[i]=row['box']
 flags=capture.get('flags')
 if flags is not None and (len(flags)!=33 or not all(isinstance(v,int) and 0<=v<2**32 for v in flags)):raise ValueError('invalid flags')
 ops,placement=core.frame(cfg,W,H,seen,used,flags=flags)
 paint(image,ops,glyphs,atlas)
 return image,dict(evidence=capture['evidence'],rooms=len(seen),places=len(placement),placement=placement,ops=ops,scope='shared C frame ops painted by Pillow; no D3D9 pixel equivalence')
def paint(image,ops,glyphs,atlas):
 """Paint the same op list the ASI hands to D3D."""
 text=(ROOT/'src/runtime/labels_generated.h').read_text();first=int(re.search(r'#define ICON_FIRST_GLYPH (\d+)',text)[1]);side=int(re.search(r'#define ICON_TEX (\d+)',text)[1]);side_h=int(re.search(r'#define ICON_TEX_H (\d+)',text)[1])
 icons=Image.frombytes('RGBA',(side,side_h),(ROOT/'assets/icons.bgra').read_bytes()[:side*side_h*4],'raw','BGRA') # level 0 of the texture the ASI loads
 for op in ops:
  l,t,r,b=op['box'];c=op['color'];size=(max(1,round(r-l)),max(1,round(b-t)));at=(round(l),round(t))
  a,red,green,blue=c>>24,(c>>16)&255,(c>>8)&255,c&255
  if op['glyph']<0:tile=Image.new('RGBA',size,(red,green,blue,a))
  else:
   x,y,w,h=glyphs[op['glyph']];tile=(icons if op['glyph']>=first else atlas).crop((x,y,x+w,y+h)).resize(size,Image.Resampling.BILINEAR) # linear like draw_op, but Pillow's is area-weighted: not the ASI's mipless GPU sample
   R,G,B,A=tile.split();tile=Image.merge('RGBA',(R.point(lambda v:v*red//255),G.point(lambda v:v*green//255),B.point(lambda v:v*blue//255),A.point(lambda v:v*a//255)))
  if at[0]>=image.width or at[1]>=image.height or at[0]+size[0]<=0 or at[1]+size[1]<=0:continue
  layer=Image.new('RGBA',image.size);layer.paste(tile,at);image.alpha_composite(layer)
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--capture',type=Path,required=True);p.add_argument('--background',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 image,report=replay(json.loads(a.capture.read_text()),Image.open(a.background) if a.background else None)
 a.output.parent.mkdir(parents=True,exist_ok=True);image.save(a.output);a.output.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n')
if __name__=='__main__':main()
