"""Icon contract: 96px RGBA source for every located row, no enemy map names, puzzles and events stay code-drawn diamonds."""
import hashlib,json,re,sys,unittest
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'));sys.path.insert(0,str(ROOT/'tests'));sys.path.insert(0,str(ROOT/'emulator'))
from core import Core
from frame_contract import tables_markers,word_bits
HEADER=(ROOT/'src/runtime/labels_generated.h').read_text()
def ints(name):return [int(v) for v in re.search(name+r'\[\] = \{([0-9,]+)\}',HEADER)[1].split(',')]
def define(name):return int(re.search(rf'#define {name} (\d+)',HEADER)[1])
NATIVE=json.loads((ROOT/'data/native-map.json').read_text())['map_pieces'];RULE=json.loads((ROOT/'data/room-state.json').read_text())['pieces']
def frame_for(core,m,settings=None,height=1080):
 """A frame centred on one marker at game scale, its room visited and nothing finished (a set flag removes a diamond)."""
 k=height/720
 return core.frame(settings or core.default_settings(),height*16//9,height,{m[2]:[300,200,420,300]},(),(k,height*8/9-m[0]*k,height/2-m[1]*k),None,word_bits(RULE[NATIVE[m[2]]['id']]['visited']))[0]
class Icons(unittest.TestCase):
 def test_assets_are_96px_soft_alpha(self):
  manifest=json.loads((ROOT/'assets/icons/manifest.json').read_text())
  self.assertEqual(len(manifest['names']),118);self.assertNotIn('Puzzle',manifest['names'])
  for name in manifest['names']:
   path=ROOT/'assets/icons'/manifest['files'][name];self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),manifest['sha256'][name],name)
   im=Image.open(path);self.assertEqual((im.size,im.mode),((96,96),'RGBA'),name)
   alpha=im.getchannel('A').histogram();self.assertTrue(alpha[0] and alpha[255] and sum(alpha[1:255]),name)
 def test_atlas_glyphs_are_96px_and_inside_4096(self):
  glyphs=re.findall(r'\{(\d+),(\d+),(\d+),(\d+)\},',HEADER.split('glyphs[] = {')[1].split('};')[0]);first=define('ICON_FIRST_GLYPH')
  self.assertEqual(len(glyphs)-first,120);self.assertEqual((define('ATLAS_W'),define('ATLAS_H')),(4096,4096)) # dropped items' names for every id took it past 2048
  for x,y,w,h in glyphs[first:]:
   self.assertEqual((w,h),('96','96'));self.assertLessEqual(int(x)+96,define('ICON_TEX'));self.assertLessEqual(int(y)+96,define('ICON_TEX_H'))
 def test_mip_chain(self):
  # Every level's alpha is the 2x2 average of the level above; transparent texels beside an icon carry its colour, not black; level 0 holds each manifest icon unchanged.
  side,levels=define('ICON_TEX'),define('ICON_LEVELS');blob=(ROOT/'assets/icons.bgra').read_bytes();self.assertEqual(len(blob),define('ICON_BYTES'));self.assertEqual(len(blob),sum(4*(side>>l)*(define('ICON_TEX_H')>>l) for l in range(levels)))
  at=0;im=[]
  for l in range(levels):
   w=side>>l;h=define('ICON_TEX_H')>>l;im.append(Image.frombytes('RGBA',(w,h),blob[at:at+w*h*4],'raw','BGRA'));at+=w*h*4
  for l in range(1,levels):
   a=im[l-1].getchannel('A').resize(im[l].size,Image.Resampling.BOX);b=im[l].getchannel('A')
   from PIL import ImageChops
   self.assertLessEqual(ImageChops.difference(a,b).getextrema()[1],2,l)
  manifest=json.loads((ROOT/'assets/icons/manifest.json').read_text());first=define('ICON_FIRST_GLYPH');G=re.findall(r'\{(\d+),(\d+),(\d+),(\d+)\},',HEADER.split('glyphs[] = {')[1].split('};')[0])[first:]
  for name,g in zip(manifest['names'],G):
   x,y=int(g[0]),int(g[1]);got=im[0].crop((x,y,x+96,y+96));src=Image.open(ROOT/'assets/icons'/manifest['files'][name]).convert('RGBA')
   self.assertEqual(got.getchannel('A').tobytes(),src.getchannel('A').tobytes(),name)
  for l in range(levels):
   p=im[l].load();w=im[l].width;edge=black=0
   for j in range(1,im[l].height-1):
    for i in range(1,w-1):
     if p[i,j][3]==0 and p[i+1,j][3]>200:
      edge+=1;black+=sum(p[i,j][:3])==0 and sum(p[i+1,j][:3])>30
   self.assertEqual(black,0,f'black fringe texels, level {l}');self.assertTrue(edge or w<128,l)
 def test_edge_luminance_per_level_whole_set(self):
  # Live, candidate 29: outlines looked white. For all icons, at all levels, the soft edge may not be much lighter than the source's, by alpha-weighted luminance.
  side,levels=define('ICON_TEX'),define('ICON_LEVELS');blob=(ROOT/'assets/icons.bgra').read_bytes();at=0;im=[]
  for l in range(levels):
   w=side>>l;h=define('ICON_TEX_H')>>l;im.append(Image.frombytes('RGBA',(w,h),blob[at:at+w*h*4],'raw','BGRA'));at+=w*h*4
  manifest=json.loads((ROOT/'assets/icons/manifest.json').read_text());first=define('ICON_FIRST_GLYPH');G=re.findall(r'\{(\d+),(\d+),(\d+),(\d+)\},',HEADER.split('glyphs[] = {')[1].split('};')[0])[first:]
  def edge(c):
   s=a=0
   for r,g,b,k in c.getdata():
    if 0<k<=192:s+=(.2126*r+.7152*g+.0722*b)*k;a+=k
   return s/a if a else 0
  bad=[]
  for name,g in zip(manifest['names'],G):
   x,y=int(g[0]),int(g[1]);pic=Image.open(ROOT/'assets/icons'/manifest['files'][name]).convert('RGBA');src=edge(pic);d=[p for p in pic.getdata() if p[3]>192];body=max(src,sum(.2126*r+.7152*g+.0722*b for r,g,b,_ in d)/max(len(d),1)) # small levels mix the body into the edge; a pale statue's edge is legitimately pale
   for l in range(levels):
    v=edge(im[l].crop((x>>l,y>>l,(x+96)>>l,(y+96)>>l)))
    if l==0 and v>src+12 or v>body+40:bad.append((name,l,round(src),round(v)))
  self.assertEqual(bad,[])
 def test_only_puzzle_rows_have_no_icon(self):
  icons=ints('marker_icon_glyphs');first=define('ICON_FIRST_GLYPH');markers=tables_markers();self.assertEqual(len(icons),len(markers))
  for m,icon in zip(markers,icons):
   if m[5] in (3,6):self.assertEqual(icon,define('NO_ICON'),'puzzle or event row has an icon')
   else:self.assertTrue(first<=icon<first+118)
 def test_frames_draw_icons_diamonds_and_no_enemy_name(self):
  from build_labels import MARKER_GROUPS
  core=Core()
  markers=tables_markers();icons=ints('marker_icon_glyphs');first=define('ICON_FIRST_GLYPH');puzzle,event=define('PUZZLE_MARK_ID'),define('EVENT_MARK_ID')
  enemy_names={g for m in markers if m[5]==MARKER_GROUPS.index('enemy') for g in (m[3],m[4])}-{g for m in markers if m[5]!=MARKER_GROUPS.index('enemy') for g in (m[3],m[4])}
  drew=dict(enemy=0,diamond=0,other_named=0)
  for m,icon in zip(markers,icons):
   ops=frame_for(core,m);glyphs=[o['glyph'] for o in ops]
   self.assertFalse(enemy_names&set(glyphs),'enemy name came back')
   if m[5]==3 and any(g in glyphs for g in (puzzle,event)):
    drew['diamond']+=1
   if m[5]==5 and icon in glyphs:drew['enemy']+=1
   if m[5] in (1,4) and m[3] in glyphs:drew['other_named']+=1
  self.assertTrue(drew['enemy'] and drew['diamond'] and drew['other_named'],drew)
 def test_a_puzzle_row_alone_never_paints_an_icon(self):
  # Hide every other category so an icon in the frame can only be the puzzle or event row's own.
  core=Core();settings=core.default_settings();settings.mask=1<<3|1<<6;markers=tables_markers();first=define('ICON_FIRST_GLYPH');puzzle,event=define('PUZZLE_MARK_ID'),define('EVENT_MARK_ID');seen=set()
  for m in markers:
   if m[5] not in (3,6):continue
   glyphs=[o['glyph'] for o in frame_for(core,m,settings)]
   seen|={g for g in (puzzle,event) if g in glyphs}
   self.assertFalse([g for g in glyphs if first<=g<first+118],'puzzle or event frame painted an icon')
  self.assertEqual(seen,{puzzle,event})
 def test_mark_size_formula(self):
  core=Core();m=next(m for m,i in zip(tables_markers(),ints('marker_icon_glyphs')) if i!=define('NO_ICON') and not m[8] and m[6]>>1&1);icon=ints('marker_icon_glyphs')[tables_markers().index(m)]
  for h in (720,1080,2160):
   op=next((o for o in frame_for(core,m,height=h) if o['glyph']==icon),None)
   self.assertIsNotNone(op);self.assertAlmostEqual(op['box'][3]-op['box'][1],18*1.2*{0:1.3*.96,1:1.3}.get(m[5],1.3 if m[5]<5 else 1.0)*h/720*.7*(1.1 if m[5]<2 else 1),places=1) # game zoom: same ratio as names
if __name__=='__main__':unittest.main()
