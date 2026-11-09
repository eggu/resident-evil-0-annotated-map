import concurrent.futures,os,re,subprocess,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'));sys.path.insert(0,str(ROOT/'tools'))
from frame_contract import check
from build_labels import ROWS,TITLE,SCOPE
from core import Core
RE1=ROOT.parents[1]/'re1-hd/resident-evil-hd-annotated-map/src/labels.h'
# Each reproduces a defect the user found on screen, or its neighbour. A surviving mutant means the contract is decorative.
MUTANTS={
 '0 hides the legend':('RE0Box legend=legend_ops(s,lk,&l);','RE0Box legend={0,0,1,1};if(s->enabled)legend=legend_ops(s,lk,&l);'),
 'legend moved back to top-left':('x0=edge_l+28*k,y0=area.b-28*k-h;','x0=28*k,y0=8;'),
 'row colour dropped':('on=on&&((s->mask>>c)&1);color=category_color[c];}','on=on&&((s->mask>>c)&1);}'),
 'legend rows in category id order':('static const unsigned char order[7]={0,1,2,3,6,4,5};','static const unsigned char order[7]={0,1,2,3,4,5,6};'),
 'event row shares the puzzle bit':('on=on&&((s->mask>>c)&1);color','on=on&&((s->mask>>(c==6?3:c))&1);color'),
 'off row not gray':('on?color:OFF_GRAY','color'),
 'single column':('r<5?x:x1,y+(float)(r<5?r:r-5)*lh','x,y+(float)r*lh'),
 '1 also hides counts':('bw=markers?0:badge_width(counts,bk,&bh);','bw=markers?0:(s->names?badge_width(counts,bk,&bh):0);'),
 'annotations ignore 0':('if(s->hidden||!s->enabled)return l.n;','if(s->hidden)return l.n;'),
 'panel over the legend':('legend.l,legend.t-4,screen*.62f','legend.l,legend.b,screen*.62f'),
 'no leader line':('leader_ops(&b,&shown->box[i],screen,alpha,l);',''),
 'leader drawn always':('if(lx>=room->l&&lx<=room->r&&ly>=room->t&&ly<=room->b)return;',''),
 'H hides the legend':('RE0Box legend=legend_ops(s,lk,&l);','if(s->hidden)return 0;RE0Box legend=legend_ops(s,lk,&l);'),
 'obstacles skipped when choosing a name slot':('for(unsigned i=0;i<n;i++)occ[no++]=(Occupied){used[i],','for(unsigned i=n_obstacles;i<n;i++)occ[no++]=(Occupied){used[i],'),
 'marker name ignores cover':('return least<0||a<least;','return least<0;'),
 'common mark kept on a key mark':('if(common(markers[shown[i]].category)||!centred){state[i]=DROP;continue;}',''),
 'common name covers key items':('||overlap_score(b,occ,no,2)>0',''),
 'marker ignores difficulty':('(m->modes>>s->difficulty&1)&&','1&&'),
 'marker shown on undrawn piece':('&&marker_room_on(m,room_on)&&','&&1&&'),
 'mark tied to one piece of its room (live: Ice Pick)':('(allowed&&rooms[j].place==rooms[i].place)','(allowed&&j==i)'),
 'room name tied to one piece of its room':('clip,legend,readout,room_on,used,n,','clip,legend,readout,room_seen,used,n,'),
 'door mark follows one room':('for(unsigned i=0;i<m->rooms;i++)if(room_on[marker_rooms[m->first_room+i]])return 1;\n return 0;','return room_on[m->piece];'),
 'door mark on any room of the floor':('if(room_on[marker_rooms[m->first_room+i]])return 1;\n return 0;','if(room_on[marker_rooms[m->first_room+i]])return 1;\n return room_on[m->piece]||1;'),
 'place lit across floors':('same_floor(i,j)&&(s->scope','(s->scope'),
 '9 still cycles difficulty':("if(key=='9'){s->scope=(s->scope+1)%3;return 1;}","if(key=='9'){s->difficulty=(s->difficulty+1)%3;return 1;}"),
 '9 not saved':("s->scope=(s->scope+1)%3;return 1;","s->scope=(s->scope+1)%3;return 0;"),
 '9 runs backwards':("(s->scope+1)%3","(s->scope+2)%3"),
 'language still on 9':("if(key=='9'){s->scope=(s->scope+1)%3;return 1;}\n if(key=='\\\\')","if(key=='9'){s->english=!s->english;return 1;}\n if(key=='\\\\'&&0)"),
 'backslash does not switch the language':("{s->english=!s->english;return 1;} /* VK_OEM_5","{return 0;} /* VK_OEM_5"),
 '8 toggles the wrong category':("1u<<re0_legend_category((unsigned)(key-'2'))","1u<<(unsigned)(key-'2')"),
 'event drawn as a puzzle':('d->category==CAT_EVENT?EVENT_MARK_ID:PUZZLE_MARK_ID','PUZZLE_MARK_ID'),
 'event not a diamond':('static int diamond(unsigned c){return c==CAT_PUZZLE||c==CAT_EVENT;}','static int diamond(unsigned c){return c==CAT_PUZZLE;}'),
 'event hidden by the puzzle bit only':('(s->mask>>m->category&1)&&!(off','(s->mask>>(m->category==6?3:m->category)&1)&&!(off'),
 'category colours ignore the INI':('void re0_frame_set_color(unsigned c,unsigned rgb){if(c<RE0_CATEGORIES)','void re0_frame_set_color(unsigned c,unsigned rgb){if(0)'),
 'item colour back to orange':('0xffff9628u,0xffb8bcc4u','0xffff9628u,0xffff783cu'),
 'scope defaults to All':('.scope=RE0_SCOPE_VISITED','.scope=RE0_SCOPE_ALL'),
 'scope ignored':('allowed=!flags||(s->scope==RE0_SCOPE_REVEALED?state!=0:state&1)','allowed=1'),
 'unknown flags hide everything':('allowed=!flags||(s->','allowed=(s->'),
 'revealed acts as visited':('s->scope==RE0_SCOPE_REVEALED?state!=0:state&1','state&1'),
 'visited acts as revealed':('s->scope==RE0_SCOPE_REVEALED?state!=0:state&1','state!=0'),
 'All needs a drawn room of the place':('s->scope==RE0_SCOPE_ALL||(allowed','(allowed'),
 'selection ignores scope':('scope_rooms(s,flags,room_seen,on);merge_places(on,0,&shown)','(void)on;merge_places(room_seen,0,&shown)'),
 'All panel has no box for an undrawn room':('place_box[i]=(RE0Box){c.l*fixed.scale+fixed.ox,c.t*fixed.scale+fixed.oy,c.r*fixed.scale+fixed.ox,c.b*fixed.scale+fixed.oy};placed_on[i]=1;','(void)c;'),
 'crowded room loses its name':('if(re0_place_label(room,w,h,clip,used,n,out))return 1;','return re0_place_label(room,w,h,clip,used,n,out);'),
 'room names placed without knowing the marks':('  if(view)n=reserve_marks(s,view,room_on,marker_off,flags,arrange,mh,used,n);\n',''),
 'fixed room name on the legend':('placed=w>0&&!on_legend&&b.r>clip.l','placed=w>0&&(on_legend||1)&&b.r>clip.l'),
 'mark under the legend':('if(boxes_hit(seen_box,used[n_obstacles])||boxes_hit(seen_box,used[n_obstacles+1]))continue;',''),
 'mark under the readouts':('||boxes_hit(seen_box,used[n_obstacles+1]))continue;',')continue;'),
 'diamond corners under the legend':('const float grow=diamond(markers[i].category)?side/9.0f:0;','const float grow=0;'),
 'readouts not bottom-right':('x0=edge_r-28*k-w,','x0=28*k,'),
 'readouts panel not drawn':('RE0Box box={x0,y0,x0+w,y0+hh};add(l,box.l,box.t,box.r,box.b,0xd0080808u,-1);\n float y=y0+pad;','RE0Box box={0,0,0,0};float y=y0+pad;'),
 '~ ignored':('if(key==\'`\'){s->legend=!s->legend;return 1;}','if(key==\'`\')return 0;'),
 'folded legend keeps the rows':('if(!s->legend) {\n  const float w=','if(0) {\n  const float w='),
 'readouts stay when the legend folds':('s->legend?readout_ops(s,lk,&l):(RE0Box){-1e9f,-1e9f,-1e9f,-1e9f}','readout_ops(s,lk,&l)'),
 'enemies enlarged':('return category==CAT_ENEMY?1.0f:ICON_SIZE_BASE','return ICON_SIZE_BASE'),
 'locks no bigger zoomed in':('(category==CAT_LOCK?.8f*1.2f+(1.5f-.8f*1.2f)*t:','(category==CAT_LOCK?.8f*1.2f:'),
 'items no bigger zoomed in':('1.0f+.3f*t)','1.0f)'),
 'names ignore the zoom':('return ZOOM_OUT_NAME+(1-ZOOM_OUT_NAME)*(t<0?0:t>1?1:t);','return 1;'),
 'names change with the pan':('return ZOOM_OUT_NAME+(1-ZOOM_OUT_NAME)*(t<0?0:t>1?1:t);','return ZOOM_OUT_NAME+(1-ZOOM_OUT_NAME)*(t<0?0:t>1?1:t)+v->ox*.0001f;'),
 'event ignores its precondition':('if(need!=0xffff&&(!flags||!flag_set(flags,need)))return 0;',''),
 'layout view accepts any box':('for(unsigned j=0;j<4;j++)if(e[j]>4||e[j]<-4)return 0;','(void)e;'),
 'marker ignores its condition':('&&re0_condition_met(m->condition,flags)&&','&&'),
 'item names stay when H is off':('if(s->item_names)for(unsigned t=0;t<4;t++)','for(unsigned t=0;t<4;t++)'),
 'state 2 keeps common marker names':('if(s->item_names==1)for(unsigned i=0;i<count;i++)if(state[i]==KEEP','if(s->item_names)for(unsigned i=0;i<count;i++)if(state[i]==KEEP'),
 'state 2 keeps common drop names':('!(s->item_names==2&&common(cat))&&',''),
 'state 2 drops key names too':('if(s->item_names)for(unsigned t=0;t<4;t++)','if(s->item_names==1)for(unsigned t=0;t<4;t++)'),
 'H toggles two states':('s->item_names=(s->item_names+1)%3;','s->item_names=!s->item_names;'),
 'H skips no-common':('s->item_names=(s->item_names+1)%3;','s->item_names=s->item_names==1?0:1;'),
 'legend row ignores the state':('hold_ids[(s->item_names>=0&&s->item_names<3?s->item_names:0)*2+lang]','hold_ids[2+lang]'),
 'counts drawn with markers':('bw=markers?0:badge_width(counts,bk,&bh)','bw=badge_width(counts,bk,&bh)'),
 'right column folded into the left':('const float x1=x+col[0]+gap;','const float x1=x;'),
 'legend row ignores scope':('scope_ids[s->scope*2+lang],x1,y+4*lh,','scope_ids[lang],x1,y+4*lh,'),
 'scope back beside [7]':('scope_ids[s->scope*2+lang],x1,y+4*lh,','scope_ids[s->scope*2+lang],x1,y+3*lh,'),
 'language label not small-line colour':('language_ids[lang],x1,y,k,SMALL_TEXT','language_ids[lang],x1,y,k,0xffffffffu'),
 'language label under the left column':('language_ids[lang],x1,y,k','language_ids[lang],x,y,k'),
 'item-names label under the right column':('?s->item_names:0)*2+lang],x,y,k','?s->item_names:0)*2+lang],x1,y,k'),
 'language value frozen':('add_text(l,language_ids[lang],','add_text(l,language_ids[0],'),
}
def build(replace,out):
 source=(ROOT/'src/core/frame.c').read_text()
 if replace[0] not in source:raise ValueError('mutant target gone: '+replace[0])
 tree=out.parent/'core';tree.mkdir(exist_ok=True);(tree/'frame.c').write_text(source.replace(*replace).replace('#include "frame.h"',f'#include "{ROOT}/src/core/frame.h"').replace('"../runtime/labels_generated.h"',f'"{ROOT}/src/runtime/labels_generated.h"'))
 subprocess.run(['clang','-std=c11','-O1','-w','-dynamiclib' if sys.platform=='darwin' else '-shared','-fPIC',str(ROOT/'src/core/map_transform.c'),str(ROOT/'src/core/annotation.c'),str(tree/'frame.c'),'-o',str(out)],check=True)
def mutant_survives(replace):
 with tempfile.TemporaryDirectory() as d:
  lib=Path(d)/'m.dylib';build(replace,lib)
  try:check(Core(lib))
  except AssertionError:return False
  return True
class FrameTests(unittest.TestCase):
 def test_contract_holds(self):check(Core())
 @unittest.skipUnless(RE1.exists(),'RE1 HD source not beside this project')
 def test_legend_text_matches_re1_hd(self):
  source=RE1.read_text();found=re.findall(r'/\* legend (.*?) \*/',source)
  # RE1 HD still has the old numbering; candidate 51 renumbered (user 2026-11-08), so the labels are compared without their [n], except the two rows that are new here.
  bare=lambda t:re.sub(r'^\[\d\] ','',t);theirs=[bare(re.split(r' · | \(',f)[0]) for f in found];new={'퍼즐','이벤트','Puzzles','Events','Items'}
  for pair in [TITLE,*ROWS]:
   for text in pair:self.assertTrue(bare(text) in theirs or bare(text) in new,text) # RE1 HD added ' · 길게: 시간' to its enemy row, 2026-11-05, and now writes it as ' (길게: 시간)'
 def test_item_and_room_names_scale_alike_through_zoom(self):
  # User: item names must follow the room name's zoom. Output size over raster size, read from what is drawn: the same ratio at 1x and 3x.
  import json
  from build_labels import marker_defs
  from frame_contract import tables_markers,word_bits
  core=Core();load=lambda n:json.loads((ROOT/'data'/n).read_text());native=load('native-map.json');rows=load('placements.json')['rows'];rule=load('room-state.json')['pieces'];index={p['id']:i for i,p in enumerate(native['map_pieces'])}
  ice=next(i for i,d in enumerate(marker_defs(dict(rows=rows),native)) if rows[d['row']]['name_en']=='Ice Pick');item=tables_markers()[ice][3];piece=index['i_tr0ca0']
  header=(ROOT/'src/runtime/labels_generated.h').read_text()
  glyph=[tuple(map(int,g.split(','))) for g in re.findall(r'\{(\d+,\d+,\d+,\d+)\}',header.split('glyphs[] = {',1)[1].split('};',1)[0])]
  layout=re.findall(r'\{([0-9.,f]+)\}',header.split('room_layout[] = {',1)[1].split('};',1)[0]);room=next(int(r.split(',')[2]) for r in layout if int(r.split(',')[0])==piece and int(r.split(',')[3])==0)
  canvas=[tuple(float(v[:-1]) for v in c.split(',')) for c in re.findall(r'\{([-0-9.]+f,[-0-9.]+f,[-0-9.]+f,[-0-9.]+f)\}',header.split('piece_canvas[] = {',1)[1].split('};',1)[0])][piece]
  flags=word_bits(rule['i_tr0ca0']['visited']);k={}
  for scale in (1.5,4.5):
   ox,oy=960-(canvas[0]+canvas[2])/2*scale,540-(canvas[1]+canvas[3])/2*scale
   box=[canvas[0]*scale+ox,canvas[1]*scale+oy,canvas[2]*scale+ox,canvas[3]*scale+oy]
   ops=core.frame(core.default_settings(),1920,1080,{piece:box},(),(scale,ox,oy),None,flags)[0]
   height=lambda g:next((o['box'][3]-o['box'][1])/glyph[g][3] for o in ops if o['glyph']==g)
   k[scale]=(height(room),height(item))
  self.assertAlmostEqual(k[1.5][1]/k[1.5][0],k[4.5][1]/k[4.5][0],places=4)
  self.assertAlmostEqual(k[4.5][1]/k[1.5][1],1/.7,places=3)
 def test_name_size_does_not_follow_a_pan_at_full_zoom(self):
  # Live report 2026-11-05: names looked larger after panning a zoomed map. Native pan (0x5bac00) only sets translation; scale stays 1+2t. Synthetic boxes; this does not explain that report by itself.
  import json
  from build_labels import marker_defs
  from frame_contract import tables_markers,word_bits
  core=Core();load=lambda n:json.loads((ROOT/'data'/n).read_text());native=load('native-map.json');rows=load('placements.json')['rows'];rule=load('room-state.json')['pieces'];index={p['id']:i for i,p in enumerate(native['map_pieces'])}
  ice=next(i for i,d in enumerate(marker_defs(dict(rows=rows),native)) if rows[d['row']]['name_en']=='Ice Pick');mark=tables_markers()[ice];item=mark[3];piece=index['i_tr0ca0']
  header=(ROOT/'src/runtime/labels_generated.h').read_text()
  glyph=[tuple(map(int,g.split(','))) for g in re.findall(r'\{(\d+,\d+,\d+,\d+)\}',header.split('glyphs[] = {',1)[1].split('};',1)[0])]
  canvas=[tuple(float(v[:-1]) for v in c.split(',')) for c in re.findall(r'\{([-0-9.]+f,[-0-9.]+f,[-0-9.]+f,[-0-9.]+f)\}',header.split('piece_canvas[] = {',1)[1].split('};',1)[0])][piece]
  flags=word_bits(rule['i_tr0ca0']['visited']);settings=core.default_settings();settings.size=90
  for width,height in ((1920,1080),(3840,2160)):
   screen=height/720;scale=3*screen;drawn=[]
   for dx,dy in ((0,0),(-200,-100),(200,100),(-300,120),(300,-120)):
    ox,oy=width/2-mark[0]*scale+dx*screen,height/2-mark[1]*scale+dy*screen
    box=[canvas[0]*scale+ox,canvas[1]*scale+oy,canvas[2]*scale+ox,canvas[3]*scale+oy];view=core.layout_view({piece:box})
    self.assertIsNotNone(view)
    ops=core.frame(settings,width,height,{piece:box},(),view,None,flags)[0]
    drawn.append(next((o['box'][3]-o['box'][1])/glyph[item][3]/screen for o in ops if o['glyph']==item))
   for value in drawn:self.assertAlmostEqual(value,drawn[0],places=4)
 def test_mark_and_name_stay_with_the_second_piece_drawn(self):
  # Live report: the game draws i_tr0ca1, Ice Pick and the room's name are tied to i_tr0ca0, and both vanished. The flag array is what the native rule reads for that room.
  import json
  core=Core();load=lambda n:json.loads((ROOT/'data'/n).read_text());native=load('native-map.json');rows=load('placements.json')['rows'];rule=load('room-state.json')['pieces'];index={p['id']:i for i,p in enumerate(native['map_pieces'])}
  from build_labels import marker_defs
  from frame_contract import tables_markers,word_bits
  from annotations import tables
  ice=next(i for i,d in enumerate(marker_defs(dict(rows=rows),native)) if rows[d['row']]['name_en']=='Ice Pick' and rows[d['row']]['category']=='key');m=tables_markers()[ice];self.assertEqual(m[2],index['i_tr0ca0'])
  layout=re.findall(r'\{([0-9.,f]+)\}',(ROOT/'src/runtime/labels_generated.h').read_text().split('room_layout[] = {',1)[1].split('};',1)[0]);name=next(int(r.split(',')[2]) for r in layout if int(r.split(',')[0])==index['i_tr0ca0'] and int(r.split(',')[3])==0)
  flags=word_bits(rule['i_tr0ca1']['visited'])
  for piece in ('i_tr0ca0','i_tr0ca1'):
   glyphs=[o['glyph'] for o in core.frame(core.default_settings(),1920,1080,{index[piece]:[1200,500,1400,600]},(),(1.5,0,0),None,flags)[0]]
   self.assertIn(m[3],glyphs,piece)
  # The fixed name needs the fixed view, so here the box is the piece's own.
  box=[float(v.rstrip('f'))*1.5 for v in re.findall(r'\{([0-9.,f]+)\}',(ROOT/'src/runtime/labels_generated.h').read_text().split('piece_canvas[] = {',1)[1].split('};',1)[0])[index['i_tr0ca1']].split(',')]
  self.assertIn(name,[o['glyph'] for o in core.frame(core.default_settings(),1920,1080,{index['i_tr0ca1']:box},(),(1.5,0,0),None,flags)[0]])
 @unittest.skipIf(os.environ.get('RE0_QUICK'),'RE0_QUICK: mutants run in build.py')
 def test_mutants_are_caught(self):
  check(Core()) # Otherwise a contract that always fails would make every mutant look caught.
  # Build and contract together, 1 s each: the slowest test by far, and independent.
  with concurrent.futures.ProcessPoolExecutor(max_workers=max(1,(os.cpu_count() or 2)-1)) as pool:
   for name,survived in zip(MUTANTS,pool.map(mutant_survives,MUTANTS.values())):
    with self.subTest(mutant=name):self.assertFalse(survived)
if __name__=='__main__':unittest.main()
