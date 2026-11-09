"""Candidate 53: native display mode and transformed gradient bounds share the frame path."""
import ctypes,re,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'emulator'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
from core import Core,Box
from frame_contract import tables_markers
ROOT=Path(__file__).resolve().parents[1]
F=79.0/224.0 # RE0_GRADIENT_OPAQUE
class DisplayArea(unittest.TestCase):
 def setUp(self):self.core=Core()
 def test_original_and_wide_in_same_backbuffer(self):
  f=self.core.library.re0_display_area;f.argtypes=[Box,ctypes.c_int];f.restype=Box
  self.assertEqual(f(Box(0,0,1920,1080),0).values(),[0,0,1920,1080])
  self.assertEqual(f(Box(0,0,1920,1080),1).values(),[240,0,1680,1080])
  self.assertEqual(f(Box(0,0,1440,1080),1).values(),[0,0,1440,1080])
  self.assertEqual(f(Box(0,0,2560,1440),0).values(),[0,0,2560,1440])
  self.assertEqual(f(Box(0,0,2560,1440),1).values(),[320,0,2240,1440])
 def test_every_emulator_quad_stays_outside_transformed_gradient(self):
  settings=self.core.default_settings();settings.scope=2
  for w,h in ((1920,1080),(2560,1440)):
   k=h/1080;quad=(336*k,w-336*k);edge=(quad[0]*F,w-(w-quad[1])*F) # the game's quads, then where they turn nearly opaque
   for mode in (0,1):
    ops,_=self.core.frame(settings,w,h,{i:[300*k,200*k,420*k,300*k] for i in range(self.core.library.re0_frame_room_count())},view=(1.5,0,0),display_mode=mode,gradients=((0,0,quad[0],h),(quad[1],0,w,h)))
    self.assertGreater(len(ops),100)
    # Slack: a mark or name may reach half a default icon past a gradient edge, never past the display's own box or the buffer.
    slack=21.6*.5*h/720;vp=((w-h*4/3)/2,(w+h*4/3)/2) if mode==1 else (0,w)
    lo,hi=max(edge[0]-slack,vp[0]),min(edge[1]+slack,vp[1])
    own=[o['box'] for o in ops if o['glyph']<0 and o['color']==0xd0080808][:2] # the legend and readouts sit on the display edges, not inside the map area
    for op in ops:
     l,t,r,b=op['box']
     if any(l>=a[0] and r<=a[2] and t>=a[1] and b<=a[3] for a in own):continue
     self.assertTrue(lo<=l<r<=hi and 0<=t<b<=h,(w,h,mode,op))
    # Legend and readouts follow the same area: the legend sits at its left/bottom corner, not in the pillarbox.
  # A subsequent frame must not retain the earlier display's clip.
  f=self.core.library.re0_frame_map;f.restype=Box
  self.core.frame(self.core.default_settings(),1920,1080,{})
  self.assertEqual(f().values(),[0,0,1920,1080])

 def test_mark_threshold_follows_screen_height_and_display_mode(self):
  # A mark stays while it overlaps the gradient by less than half a default icon (candidate 54); beyond that it goes whole.
  ms=tables_markers();H=(ROOT/'src/runtime/labels_generated.h').read_text()
  ic=[int(v) for v in re.search(r'marker_icon_glyphs\[\] = \{([0-9,]+)\}',H)[1].split(',')]
  i=next(i for i,m in enumerate(ms) if m[5] not in (3,5) and not m[8] and m[6]>>1&1);m=ms[i]
  settings=self.core.default_settings();settings.scope=2;settings.item_names=0
  for w,h in ((1280,720),(1920,1080),(2560,1440)):
   for mode in (0,1):
    quad=336*h/1080;edge=quad*F;slack=21.6*.5*h/720;vp=((w-h*4/3)/2,(w+h*4/3)/2) if mode==1 else (0,w);slack=slack if edge>vp[0] else 0;edge=max(edge,vp[0]) # the display's own edge gets no slack
    def icon_at(depth):
     # centre `depth` px inside the left gradient edge
     ops,_=self.core.frame(settings,w,h,{m[2]:[300,200,420,300]},view=(1.5*h/1080,edge-depth-m[0]*1.5*h/1080,h/2-m[1]*1.5*h/1080),off=[0 if q==i else 1 for q in range(len(ms))],flags=[0xffffffff]*33,display_mode=mode,gradients=((0,0,quad,h),(w,0,w,h)))
     return [o for o in ops if o['glyph']==ic[i]]
    side=icon_at(-21.6*h/720-40*h/720);self.assertTrue(side,(w,h,mode,edge));side=side[0]['box'];side=side[2]-side[0]
    self.assertTrue(icon_at(slack-side*.5-side/9-1),(w,h,mode)) # slight overlap: still drawn
    self.assertFalse(icon_at(slack-side*.5+1),(w,h,mode))      # past the threshold: hidden whole

 def test_gradient_cut_is_where_the_texture_is_85_percent_dark(self):
  # map_bg01 is DXT5, black, alpha only. The cut is the first column below 85%, as a fraction of the 224-wide sprite.
  prof=ROOT/'local/research/map_bg01_alpha_row.json'
  if prof.exists():
   import json;a=json.loads(prof.read_text());self.assertEqual(len(a),224)
   self.assertEqual(next(x for x in range(224) if a[x]<.85*255),79)
  rows=[]
  f=self.core.library.re0_display_bounds;f.argtypes=[Box,ctypes.c_int,Box,Box];f.restype=Box
  for mode in (0,1):
   for w,h in ((1280,720),(1920,1080),(2560,1440)):
    q=336*h/1080;vp=Box(0,0,w,h);b=f(vp,mode,Box(0,0,q,h),Box(w-q,0,w,h)).values()
    rows.append((mode,h,round(b[0],1),round(b[2],1)))
    self.assertAlmostEqual(b[0],max(q*F,(w-h*4/3)/2 if mode else 0),places=2)
  print('display mode, height, left cut, right cut:',rows)

 def test_legend_and_readouts_sit_on_the_display_edges(self):
  # Candidate 56: the legend's left and the readouts' right edge are the display box's own edges (screen edges in Wide, the 4:3 box in Original) plus the old 28/1440-of-height margin.
  settings=self.core.default_settings();rows=[]
  for w,h in ((1280,720),(1920,1080),(2560,1440)):
   for mode in (0,1):
    q=336*h/1080;vp=((w-h*4/3)/2,(w+h*4/3)/2) if mode==1 else (0,w);m=28*h/1440
    ops,_=self.core.frame(settings,w,h,{},display_mode=mode,gradients=((0,0,q,h),(w-q,0,w,h)))
    panels=[o['box'] for o in ops if o['glyph']<0 and o['color']==0xd0080808]
    self.assertGreaterEqual(len(panels),2,(w,h,mode))
    self.assertAlmostEqual(panels[0][0],vp[0]+m,places=1);self.assertAlmostEqual(panels[1][2],vp[1]-m,places=1)
    rows.append((mode,h,round(panels[0][0],1),round(panels[1][2],1)))
  print('mode, height, legend left, readout right:',rows)

if __name__=='__main__':unittest.main()
