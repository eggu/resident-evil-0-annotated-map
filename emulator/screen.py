"""Compose the game's map screen from its own GUI resources: every layer the native screen draws, in GUI order.

Static properties only: native animation tracks are not evaluated, so anything they move or fade differs from the game.
"""
import sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools/inspect'))
from resources import Arc,Gui
from render import decode_texture
TEXTURE=0x241f5deb;GUI=None
class Assets:
 def __init__(self,game):
  self.ui=game/'nativePC/arc/ui';self.arcs=[Arc((self.ui/n).read_bytes()) for n in ('map_eng.arc','map.arc')];self.cache={}
 def member(self,name,kind=None):
  for a in self.arcs:
   for m in a.members:
    if m.name==name and (kind is None or m.kind==kind):return a,m
  raise KeyError(name)
 def gui(self,name):
  for a in self.arcs:
   for m in a.members:
    if m.name==name and m.kind!=TEXTURE:return Gui(a.read(m))
  raise KeyError(name)
 def texture(self,path):
  if path not in self.cache:
   # The eng archive holds the English text sheet under its own name.
   a,m=self.member(path.replace('_jpn_','_eng_'),TEXTURE) if '_jpn_' in path else self.member(path,TEXTURE)
   self.cache[path]=decode_texture(a.read(m))
  return self.cache[path]
def number(v):
 """Keyframed properties decode to a track reference; their value is unevaluated, so 0 until tracks are read."""
 return v if isinstance(v,(int,float)) else 0
def walk(records,index,x=0.0,y=0.0,visible=True):
 """Depth-first by the GUI's sibling and child links, children sorted by Priority."""
 out=[];i=index
 while i!=0xffffffff:
  row=records[i];p=row['properties'];vis=visible and p.get('Visible',True);px,py=x+number(p.get('PosX',0)),y+number(p.get('PosY',0))
  out.append((row,px,py,vis));child=row['raw'][3]
  if child!=0xffffffff:out+=walk(records,child,px,py,vis)
  i=row['raw'][2]
 return out
def anchor(point,w,h):
 """ControlPoint low bits: 0/1/2 left/centre/right, then top/middle/bottom."""
 return {0:0,1:-.5,2:-1}[point&3]*w,{0:0,4:-.5,8:-1}[point&12]*h
def objects(gui,assets,instance,x,y,skip):
 """Sprites of one instance: (layer name, texture, rect, box)."""
 anim=gui.animations.get(instance['properties'].get('AnimationId'))
 if not anim:return []
 out=[]
 for row,ox,oy,vis in sorted(walk(gui.objects,anim['root'],x,y),key=lambda r:number(r[0]['properties'].get('Priority',0))):
  p=row['properties']
  if not vis or 'Texture' not in p or not isinstance(p.get('mTextureRect'),list):continue
  ref=gui.textures.get(p['Texture'])
  if not ref or 'dummy' in ref['path']:continue
  if not isinstance(p.get('Size'),list):continue
  w,h=p['Size'][:2];ax,ay=anchor(p.get('ControlPoint',0),abs(w),abs(h));out.append((row['name'],ref['path'],p['mTextureRect'],(ox+ax,oy+ay,abs(w),abs(h)),w<0,h<0,p.get('BlendState',0)))
 return out
def draw_gui(image,gui,assets,skip=lambda name:False,log=None,tint=None):
 """Paint a whole GUI: the root sits at the canvas centre, as native 0x883090's origin does."""
 root=next(i for i,r in enumerate(gui.instances) if not any(o['raw'][2]==i or o['raw'][3]==i for o in gui.instances))
 for row,x,y,vis in walk(gui.instances,root,640.0,360.0):
  if not vis or skip(row['name']):continue
  for name,path,rect,(l,t,w,h),fx,fy,blend in objects(gui,assets,row,x,y,None):
   try:tex=assets.texture(path)
   except (ValueError,KeyError) as e:
    if log is not None:log.append((row['name'],name,str(e)[:40]))
    continue
   tile=tex.crop(tuple(map(int,rect))).resize((max(1,round(w)),max(1,round(h))),Image.Resampling.BILINEAR)
   if fx:tile=tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
   if fy:tile=tile.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
   if tint:
    col=tint(row['name'],name)
    if col:tile=Image.merge('RGBA',[c.point(lambda v,k=col[i]:v*k//255) for i,c in enumerate(tile.split()[:3])]+[tile.getchannel('A').point(lambda v,k=col[3]:v*k//255)])
   layer=Image.new('RGBA',image.size);layer.paste(tile,(round(l),round(t)));image.alpha_composite(layer)
