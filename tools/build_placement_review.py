"""Local review page. It runs the ASI's own frame code as WebAssembly and paints the draw list it returns, so names,
marks, leader lines, legend and keys follow one rule set. Map art comes from a legally owned install, so it stays under local/.
"""
import argparse,base64,hashlib,io,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for folder in ('emulator','tools','tools/inspect'):sys.path.insert(0,str(ROOT/folder))
from render import render,decode_texture
from resources import Arc
from build_labels import marker_defs
from build_core import build_wasm
from PIL import Image
GROUPS=[('lock','[2] 잠긴 문','[2] Locks','#ffcd46'),('key','[3] 핵심 아이템','[3] Key items','#5adcff'),('file','[4] 문서·지도','[4] Files/Maps','#ff8cd2'),('puzzle','[5] 퍼즐','[5] Puzzles','#ff9628'),('event','[6] 이벤트','[6] Events','#b070ff'),('item','[7] 일반 아이템','[7] Items','#b8bcc4'),('enemy','[8] 적','[8] Enemies','#eb3c3c')]
# English: map_text00_eng_ID, the art the map itself shows, in region order. Korean: installed patch's map item names.
AREAS={'tr':('열차','Train'),'sh':('양성소','Training Facility'),'dm':('양성소 지하','Facility Basement'),'ch':('연구소','Laboratory'),'bt':('공장','Factory'),'pl':('처리장','Treatment Plant')}
FLOOR_ORDER=['roof','3f','2f','1f','b1','b2','b3','b4','b5','b6','b7','b8','b9']
def floor_label(region,floor):
 """Floor text as the map's own tabs write it: Roof, 3F .. B9."""
 text='Roof' if floor=='roof' else floor.upper()
 return f'{AREAS[region][0]} {text}',f'{AREAS[region][1]} {text}'
PAGE='''<!doctype html><meta charset="utf-8"><title>RE0 Map Review</title>
<style>body{margin:0;background:#222;color:#eee;font:14px sans-serif}#bar{padding:8px;display:flex;gap:10px;flex-wrap:wrap;align-items:center}canvas{display:block;margin:auto;background:#000;width:100%;max-width:calc((100vh - 90px)*16/9);cursor:grab;touch-action:none}input[type=range]{width:90px;vertical-align:middle}label{cursor:pointer}#info{padding:6px 10px;min-height:38px;white-space:pre-wrap}#ext{padding:0 10px 12px;color:#bbb;font-size:13px}button{cursor:pointer}</style>
<div id="bar"><label><input type="checkbox" id="frame" checked>프레임(V)</label><label><input type="checkbox" id="drop">합성 드롭: 잉크 리본 ×2, 대강당 1층(합성)</label><label><input type="checkbox" id="list">아이템 목록(Enter)</label><select id="floor"></select><select id="mode"></select><select id="check"></select><select id="flagset"></select><select id="roomset"></select><button id="fit"></button><button id="out">−</button><button id="in">+</button><button id="game1"></button><button id="game"></button><span id="zoom"></span><label><span id="t_size"></span> <input type="range" id="size" min="50" max="150" step="10"></label><label><span id="t_opacity"></span> <input type="range" id="opacity" min="10" max="100" step="10"></label><span id="count"></span></div>
<canvas id="c" width="1920" height="1080"></canvas><div id="info"></div><div id="ext"></div>
<script>
/* Native 0x5b5320 at progress t, as canvas scale and origin; tests compare this with the shared C transform. */
function gameView(fx,fy,t){const k=1+2*t,tx=k==1?0:(fx-640)*-3*t,ty=k==1?0:(fy-360)*-3*t;return{k,ox:640*(1-k)+tx,oy:360*(1-k)+ty}}
const D=DATA;
const T={help:['키는 왼쪽 아래 범례 그대로 | H: 아이템 이름 켜기·끄기 | Ctrl+[ ]: 아이콘 불투명도 | Ctrl+-/+: 아이콘 크기 | , . : 방 선택 | 휠·트랙패드: 스크롤 | Ctrl+휠·핀치: 확대 | 드래그: 이동 | 게임 확대 후 클릭: 그 지점 중심','Keys as in the bottom-left legend | H: item names on/off | Ctrl+[ ]: icon opacity | Ctrl+-/+: icon size | , . : select room | Wheel/trackpad: scroll | Ctrl+wheel/pinch: zoom | Drag: move | After game zoom, click: centre there'],fit:['층 맞춤','Fit floor'],game1:['게임 기본(1배)','Game view (1x)'],game:['게임 확대(3배)','Game zoom (3x)'],size:['이름 크기','Name size'],opacity:['이름 불투명도','Name opacity'],modes:[['쉬움','보통','어려움'],['Easy','Normal','Hard']],roomsets:[['방: 전부 방문','방: 절반 방문, 지도 없음','방: 절반 방문, 지도 있음','방: 방문 없음, 지도 있음'],['Rooms: all visited','Rooms: half visited, no map','Rooms: half visited, map held','Rooms: none visited, map held']],flagsets:[['플래그: 시작 직후','플래그: 초반 일괄 후','플래그: 진행 전부','플래그: 진행 전부 + 보상','플래그: 전부 완료(획득·해결)'],['Flags: at start','Flags: after opening','Flags: all progress','Flags: all progress + rewards','Flags: all finished (taken, solved)']],checks:[['외부 대조: 전체','외부 자료와 일치','게임 자료에만 있음'],['External check: all','Matches external','Game data only']],count:[n=>n+'개',n=>n+' marks'],only:['외부 자료에만 있음(좌표 없음, 이벤트로 얻는 항목 포함): ','Only in external source (no coordinates, includes event items): '],evidence:['근거: ','Evidence: '],room:['방 ','Room '],world:['월드 ','World '],external:['외부 대조: ','External check: '],outside:['방 경계 밖 ','Outside room by ']};
const $=i=>document.getElementById(i),c=$('c'),x=c.getContext('2d'),F=$('floor'),M=$('mode'),X=$('check'),P=$('flagset'),Q=$('roomset');const W=1920,H=1080,BASE=1.5;const imgs={},tiles=new Map();let v={k:1,ox:0,oy:0},gameMode=false,drag=null,lastOps=[],lastDoors=0,shown=[],api,mem,atlas;
const MODES=['easy','normal','hard'];
const bytes=s=>Uint8Array.from(atob(s),ch=>ch.charCodeAt(0));
for(const f of D.floors){const o=document.createElement('option');o.value=f.key;F.append(o)}
for(const m of MODES){const o=document.createElement('option');o.value=m;M.append(o)}
const SETS=['start','opening','progress','rewards','finished'];for(const k of SETS){const o=document.createElement('option');o.value=k;P.append(o)}
const ROOMS=['visited','half','half-map','map'];for(const k of ROOMS){const o=document.createElement('option');o.value=k;Q.append(o)}
/* No capture here: this choice stands in for the flags the ASI reads for rooms. Half: rooms by whether their first visited flag is even, not a real progress state. The map art stays whole, so only the shared rule's names and marks show the choice. */
function setRooms(name){Q.value=name;const a=new Uint32Array(mem.buffer,api.re0_wasm_flags(),33),put=(f,on)=>{if(on)a[f>>>5]|=1<<(f&31);else if(f>=0x200)a[f>>>5]&=~(1<<(f&31))};for(const r of D.room_state){const v=name=='visited'||(name!='map'&&r.v[0]%2==0),m=name=='half-map'||name=='map';for(const f of r.r)put(f,false);for(const f of r.v)put(f,false);for(const f of r.v)if(v)put(f,true);for(const f of r.r)if(m)put(f,true)}}
/* No live game here: named sets stand in for the array the ASI reads. */
function setFlags(name){P.value=name;const a=new Uint32Array(mem.buffer,api.re0_wasm_flags(),33);a.fill(0);for(const c of D.flagsets[name=='finished'?'rewards':name]){const f=0x312+c;a[f>>>5]|=1<<(f&31)}if(name=='finished')a.fill(0xffffffff,0,13);setRooms(Q.value||'visited');fillRows()}
/* Stands in for the placement manager: row kind 0 means taken. Native layout: room +0, kind +4, item +8. */
function fillRows(){const on=P.value=='finished',drop=$('drop').checked,m=sget('difficulty'),v=new DataView(mem.buffer,api.re0_wasm_arrange_rows(),0x30+0x4e8*0x5c);api.re0_wasm_arrange_set(on||drop?D.table_rows[m]:0);if(on||drop)for(const d of D.defs){const r=D.states[d.row];if(r&&r[m]!=0xffff){const o=0x30+r[m]*0x5c;v.setUint32(o,r[3],true);v.setUint32(o+4,r[5],true);v.setUint32(o+8,r[4],true);v.setUint8(o+0x39,on&&r[5]?1:0)}}
/* SYNTHETIC: the live Ink Ribbon row of slot 589 put in the first free slot. */const s=D.table_rows[m];for(let k=s;k<s+1;k++){v.setUint32(0x2c+k*0x5c,drop?36:0xffffffff,true);const o=0x30+k*0x5c;v.setUint32(o+4,drop?0x71:0,true);v.setUint32(o+8,55,true);v.setUint32(o+0x3c,2,true);v.setFloat32(o+0x20,1096.29,true);v.setFloat32(o+0x28,955.42,true)}}
for(const k of ['all','match','game-only']){const o=document.createElement('option');o.value=k;X.append(o)}
const saved=k=>{try{return localStorage.getItem('re0review_'+k)}catch(e){return null}};const store=(k,val)=>{try{localStorage.setItem('re0review_'+k,val)}catch(e){}};
const S=['enabled','names','english','size','opacity','difficulty','mask','selected','hidden','scope','icon_size','icon_opacity','item_names','legend'];
const sget=k=>new Int32Array(mem.buffer,api.re0_wasm_settings(),14)[S.indexOf(k)];const sset=(k,val)=>{new Int32Array(mem.buffer,api.re0_wasm_settings(),14)[S.indexOf(k)]=val};
const fill=(s,list)=>{[...(s.children||[])].forEach((o,i)=>o.textContent=list[i])};
function labels(){const l=sget('english');fill(F,D.floors.map(f=>f.name[l]));fill(M,T.modes[l]);fill(P,T.flagsets[l]);fill(Q,T.roomsets[l]);fill(X,T.checks[l]);$('fit').textContent=T.fit[l];$('game1').textContent=T.game1[l];$('game').textContent=T.game[l];$('info').textContent=T.help[l];$('t_size').textContent=T.size[l];$('t_opacity').textContent=T.opacity[l];M.value=MODES[sget('difficulty')];$('size').value=sget('size');$('opacity').value=sget('opacity')}
function persist(){for(const k of['english','size','opacity','difficulty','mask','enabled','names','scope','icon_size','icon_opacity','item_names','legend'])store(k,sget(k))}
function fit(){const f=D.floors.find(f=>f.key==F.value),a=f.pieces;if(!a.length){v={k:1,ox:0,oy:0};return}const L=Math.min(...a.map(p=>p[1])),R=Math.max(...a.map(p=>p[3])),U=Math.min(...a.map(p=>p[2])),B=Math.max(...a.map(p=>p[4])),k=Math.min(4,1240/(R-L+20),680/(B-U+20));v={k,ox:640-k*(L+R)/2,oy:360-k*(U+B)/2}}
/* Atlas tiles are white with a dark outline; multiply gives the colour D3D's diffuse modulation gives the ASI. */
const iconSheet=new Image();iconSheet.onload=()=>{tiles.clear();draw()};iconSheet.src=D.icons;
function tile(g,rgb){const key=g+'|'+rgb;let t=tiles.get(key);if(t)return t;const [gx,gy,w,h]=D.glyphs[g];t=document.createElement('canvas');t.width=w;t.height=h;const q=t.getContext('2d');const src=g>=D.icon_first?iconSheet:atlas;q.drawImage(src,gx,gy,w,h,0,0,w,h);q.globalCompositeOperation='multiply';q.fillStyle='#'+rgb.toString(16).padStart(6,'0');q.fillRect(0,0,w,h);q.globalCompositeOperation='destination-in';q.drawImage(src,gx,gy,w,h,0,0,w,h);tiles.set(key,t);return t}
const bgImage=new Image();bgImage.onload=()=>draw();bgImage.src=D.bg.image;
function sprite(p,st){const key=p.fill?st:0;p.cache=p.cache||{};if(p.cache[key])return p.cache[key];const im=p.im||(p.im=Object.assign(new Image(),{onload:()=>{p.cache={};draw()},src:p.image}));if(!p.fill)return im;const t=document.createElement('canvas');t.width=p.w;t.height=p.h;const q=t.getContext('2d');q.drawImage(im,0,0);q.globalCompositeOperation='multiply';q.fillStyle='#'+D.face_colours[st].slice(0,6);q.fillRect(0,0,p.w,p.h);q.globalCompositeOperation='destination-in';q.drawImage(im,0,0);if(im.complete)p.cache[key]=t;return t}
function draw(){if(!api)return;const f=D.floors.find(f=>f.key==F.value);const i=imgs[f.key]||(imgs[f.key]=Object.assign(new Image(),{src:f.image,onload:draw}));const R=c.width/W;x.setTransform(R,0,0,R,0,0);x.imageSmoothingQuality='high';x.globalAlpha=1;x.fillStyle='#000';x.fillRect(0,0,W,H);const s=v.k*BASE,ox=v.ox*BASE,oy=v.oy*BASE;if(bgImage.complete!==false)x.drawImage(bgImage,D.bg.xy[0]*s+ox,D.bg.xy[1]*s+oy,D.bg.size[0]*s,D.bg.size[1]*s);if(i.complete!==false)x.drawImage(i,ox,oy,1280*s,720*s);
/* As the game: fill (_b sheet) tinted by the piece state's entry in 0xd9de40, then outline (_a sheet) as is. State 0 is not drawn; All scope makes it 2 (0x5b4afa patch). */
const frameOn=$('frame').checked;const frameState=frameOn?($('list').checked?2:1):0;api.re0_wasm_set_frame(frameState);
for(const p of f.sprites){const st=api.re0_wasm_room_state(p.piece)||(sget('scope')==2?2:0);if(!st)continue;x.drawImage(sprite(p,st),p.x*s+ox,p.y*s+oy,p.w*s,p.h*s)}
/* Door places from the GUI's door groups. The whole quad is what the ASI captures as an obstacle; only its painted part is drawn. State colour not modelled. */
const obstacles=new Float32Array(mem.buffer,api.re0_wasm_obstacles(),256*4);lastDoors=f.doors.length;f.doors.forEach((d,j)=>{obstacles.set([d[0]*s+ox,d[1]*s+oy,d[2]*s+ox,d[3]*s+oy],j*4);const e=f.door_ink[j],b=[e[0]*s+ox,e[1]*s+oy,e[2]*s+ox,e[3]*s+oy];x.fillStyle='#101010';x.fillRect(b[0]-1,b[1]-1,b[2]-b[0]+2,b[3]-b[1]+2);x.fillStyle='#b8b8a8';x.fillRect(b[0],b[1],b[2]-b[0],b[3]-b[1])});
const seen=new Uint8Array(mem.buffer,api.re0_wasm_seen(),256),boxes=new Float32Array(mem.buffer,api.re0_wasm_boxes(),256*4),off=new Uint8Array(mem.buffer,api.re0_wasm_marker_off(),2048);seen.fill(0);
/* As the game: a room in neither state is not drawn, except what the All scope patch adds. */
for(const p of f.pieces)if(api.re0_wasm_room_state(p[0])||sget('scope')==2){seen[p[0]]=1;boxes.set([p[1]*s+ox,p[2]*s+oy,p[3]*s+ox,p[4]*s+oy],p[0]*4)}
const mode=MODES[sget('difficulty')],check=X.value;shown=[];D.defs.forEach((d,n)=>{const r=D.rows[d.row];const pass=check=='all'||(r.external&&r.external[mode]==check);off[n]=pass?0:1;if(pass&&!api.re0_wasm_done(n)&&(api.re0_wasm_met(d.condition)||(d.also&&api.re0_wasm_met(d.also)))&&r.key==f.key&&api.re0_wasm_marker_on(n)&&(d.modes>>sget('difficulty')&1)&&(sget('mask')>>d.category&1)&&sget('enabled'))shown.push(d)});
const n=api.re0_wasm_frame(W,H,s,ox,oy,f.doors.length),raw=new DataView(mem.buffer,api.re0_wasm_ops(),n*24);lastOps=[];
if(frameOn){const cb=new Float32Array(mem.buffer,api.re0_wasm_chrome(),48);x.fillStyle='rgba(60,55,45,.85)';for(let q=0;q<(frameState==2?12:11);q++)x.fillRect(cb[q*4],cb[q*4+1],cb[q*4+2]-cb[q*4],cb[q*4+3]-cb[q*4+1]);}for(let j=0;j<n;j++){const o=j*24,l=raw.getFloat32(o,true),t=raw.getFloat32(o+4,true),r=raw.getFloat32(o+8,true),b=raw.getFloat32(o+12,true),col=raw.getUint32(o+16,true),g=raw.getInt32(o+20,true);lastOps.push({l,t,r,b,col,g});x.globalAlpha=(col>>>24)/255;const rgb=col&0xffffff;if(g<0){x.fillStyle='#'+rgb.toString(16).padStart(6,'0');x.fillRect(l,t,r-l,b-t)}else if(atlas)x.drawImage(tile(g,rgb),l,t,r-l,b-t)}x.globalAlpha=1;
const lang=sget('english');$('count').textContent=T.count[lang](shown.length);$('zoom').textContent=Math.round(v.k*100)+'%';const e=D.only_external.filter(o=>o.key==F.value&&o.mode==mode);$('ext').textContent=e.length?T.only[lang]+e.map(o=>o.place+' '+o.name).join(' · '):''}
const point=e=>{const b=c.getBoundingClientRect();return[(e.clientX-b.left)*1280/b.width,(e.clientY-b.top)*720/b.height]};
function zoomAt(px,py,f){const k=Math.max(.5,Math.min(16,v.k*f));v.ox=px-(px-v.ox)*k/v.k;v.oy=py-(py-v.oy)*k/v.k;v.k=k;gameMode=false;draw()}
c.onwheel=e=>{e.preventDefault();const[p,q]=point(e);if(e.ctrlKey)zoomAt(p,q,Math.exp(-e.deltaY*.01));else{v.ox-=e.deltaX;v.oy-=e.deltaY;draw()}};
c.onpointerdown=e=>{drag={p:point(e),o:[v.ox,v.oy],moved:false}};
c.onpointerup=e=>{if(drag&&!drag.moved&&gameMode){const[p,q]=point(e);v=gameView((p-v.ox)/v.k,(q-v.oy)/v.k,1);draw()}drag=null};
c.onpointermove=e=>{const[p,q]=point(e);if(drag){const dx=p-drag.p[0],dy=q-drag.p[1];if(Math.abs(dx)+Math.abs(dy)>3)drag.moved=true;if(drag.moved){v.ox=drag.o[0]+dx;v.oy=drag.o[1]+dy;draw()}return}const l=sget('english'),h=shown.filter(d=>Math.abs(d.x*v.k+v.ox-p)<6&&Math.abs(d.y*v.k+v.oy-q)<6);if(h.length)$('info').textContent=h.map(d=>{const r=D.rows[d.row];return(l?r.name_en:r.name_ko)+'  '+T.room[l]+r.room+'  '+T.evidence[l]+r.evidence+(r.world?'  '+T.world[l]+r.world.map(n=>Math.round(n)).join(','):'')+(r.external?'  '+T.external[l]+r.external[MODES[sget('difficulty')]]:'')+(r.distance>2?'  '+T.outside[l]+Math.round(r.distance)+'px':'')}).join('\\n')};
$('frame').onchange=draw;$('drop').onchange=()=>{fillRows();draw()};$('list').onchange=draw;$('in').onclick=()=>zoomAt(640,360,1.25);$('out').onclick=()=>zoomAt(640,360,.8);$('fit').onclick=()=>{gameMode=false;fit();draw()};
$('game1').onclick=()=>{gameMode=false;v={k:1,ox:0,oy:0};draw()};
$('game').onclick=()=>{gameMode=true;v=gameView((640-v.ox)/v.k,(360-v.oy)/v.k,1);draw()};
F.onchange=()=>{gameMode=false;v={k:1,ox:0,oy:0};draw()};X.onchange=draw;P.onchange=()=>{setFlags(P.value);draw()};Q.onchange=()=>{setRooms(Q.value);draw()};M.onchange=()=>{sset('difficulty',MODES.indexOf(M.value));fillRows();persist();draw()};
$('size').oninput=()=>{sset('size',+$('size').value);persist();draw()};$('opacity').oninput=()=>{sset('opacity',+$('opacity').value);persist();draw()};
/* Every key goes to the C handler the ASI calls. */
function press(key){if(key=='='||key=='_')key=key=='='?'+':'-';if(key=='₩')key='\\\\';if(!'0123456789[]-+,.hiIoO\\\\'.includes(key)||!key)return false;api.re0_wasm_key(key.charCodeAt(0));fillRows();persist();labels();draw();return true}
document.addEventListener('keydown',e=>{if(e.ctrlKey&&!e.metaKey&&!e.altKey){const m={'[':'o',']':'O','-':'i','_':'i','=':'I','+':'I'}[e.key];if(m){press(m);e.preventDefault&&e.preventDefault()}return}if(e.metaKey||e.altKey)return;if(e.key=='v'||e.key=='V'||e.key=='ㅍ'){$('frame').checked=!$('frame').checked;draw();return}if(e.key=='h'||e.key=='H'||e.key=='ㅗ'){press('h');return}if(press(e.key))e.preventDefault&&e.preventDefault()});

const q=new URLSearchParams((typeof location=='undefined'?'':location.hash).slice(1));
/* Backing store at device pixels, layout still at 1920x1080: a fixed 1920 buffer resampled by CSS blurred every glyph. */
function fitBacking(){const b=c.getBoundingClientRect(),d=typeof devicePixelRatio=='number'?devicePixelRatio:1,w=Math.round(b.width*d);if(w&&w!=c.width){c.width=w;c.height=Math.round(w*H/W);draw()}}
if(typeof ResizeObserver!='undefined')new ResizeObserver(fitBacking).observe(c);
globalThis.re0Review={iconFirst:D.icon_first,ready:WebAssembly.instantiate(bytes(D.wasm),{}).then(w=>{api=w.instance.exports;mem=api.memory;for(const[k,val]of[['enabled',1],['names',1],['english',0],['size',100],['opacity',60],['difficulty',1],['mask',63],['selected',-1],['hidden',0],['scope',0],['icon_size',100],['icon_opacity',80],['item_names',0],['legend',1]]){const s=saved(k);sset(k,s===null?val:+s)}if(q.get('lang'))sset('english',q.get('lang')=='en'?1:0);if(q.get('size'))sset('size',+q.get('size'));if(q.get('opacity'))sset('opacity',+q.get('opacity'));F.value=q.get('f')||D.floors[0].key;X.value=q.get('check')||'all';Q.value=q.get('rooms')||'visited';setFlags(q.get('flags')||'progress');if(q.get('k')){const k=+q.get('k');v={k,ox:640-k*+q.get('x'),oy:360-k*+q.get('y')}}labels();const a=new Image();a.onload=()=>{atlas=a;tiles.clear();draw()};a.src=D.atlas;draw()}),ops:()=>lastOps,mismatches:()=>api.re0_wasm_arrange_mismatches(),setFlags:n=>{setFlags(n);draw()},setRooms:n=>{setRooms(n);draw()},view:()=>v,doors:()=>lastDoors,obstaclesPassed:()=>api.re0_wasm_kept(),press,setting:sget,shown:()=>shown,draw};
</script>'''
def row_states(data):
 """Table row -> [slot easy, normal, hard, room, item, enemy kind or 0], for the page's stand-in placement table. Under 'finished' an item row reads as picked up (kind 0) and an enemy as killed (+0x39), as native code leaves them."""
 out={}
 for r in json.loads((ROOT/'verification/state-flags.json').read_text())['rows']:
  s=r.get('slot')
  if s:out[str(r['index'])]=[*[s.get(m,0xffff) for m in('easy','normal','hard')],data['rows'][r['index']].get('room') or 0,data['rows'][r['index']].get('item') or 0,data['rows'][r['index']].get('kind',0) if r['category']=='enemy' else 0]
 return out
def flag_sets(report):
 """Stand-ins for the live array, widest last. Classes come from the native and script scan; when opening-block flags land is inferred."""
 by={};sets={}
 for v in report['values']:by.setdefault(v['cls'],[]).append(v['condition'])
 start=by['native-start'];opening=start+by['opening-block'];progress=opening+by['script-later']+by['no-writer']
 return dict(start=start,opening=opening,progress=progress,rewards=progress+by['fresh-unlock'])
def glyph_table():
 text=(ROOT/'src/runtime/labels_generated.h').read_text();part=text.split('glyphs[] = {',1)[1].split('};',1)[0]
 return [list(map(int,m.split(','))) for m in re.findall(r'\{([0-9,]+)\}',part)]
def icons_png(header):
 """Level 0 of the icon texture the ASI loads."""
 side=int(re.search(r'#define ICON_TEX (\d+)',header)[1]);side_h=int(re.search(r'#define ICON_TEX_H (\d+)',header)[1]);b=io.BytesIO();Image.frombytes('RGBA',(side,side_h),(ROOT/'assets/icons.bgra').read_bytes()[:side*side_h*4],'raw','BGRA').save(b,'PNG',optimize=True);return 'data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
def build(game,out):
 data=json.loads((ROOT/'data/placements.json').read_text());native=json.loads((ROOT/'data/native-map.json').read_text());out.mkdir(parents=True,exist_ok=True)
 check=json.loads((ROOT/'verification/placement-crosscheck.json').read_text());status={c['index']:c['external'] for c in check['rows']}
 rows={}
 for index,r in enumerate(data['rows']):
  if r['x'] is None:continue
  rows[index]=dict(key=f"{r['region']}-{r['floor']}",name_ko=r['name_ko'],name_en=r['name_en'],room=r['room'],evidence=r['evidence'],world=r.get('world'),distance=r['distance'],external=status.get(index))
 defs=[dict(row=d['row'],x=d['x'],y=d['y'],category=d['category'],modes=d['modes'],condition=d['condition']) for d in marker_defs(data,native)]
 flagsets=flag_sets(json.loads((ROOT/'verification/arrange-conditions.json').read_text()))
 regions=[r['region'] for r in native['native_regions']];piece_index={p['id']:i for i,p in enumerate(native['map_pieces'])};floors=[]
 for floor in sorted(native['floors'],key=lambda f:(regions.index(f['region']),FLOOR_ORDER.index(f['floor']))):
  key=f"{floor['region']}-{floor['floor']}";drawn=[];_,trace=render(game,floor['region'],floor['floor'],sprites=drawn);boxes={}
  for d in trace['drawn']:
   b=d['canvas_box'];m=boxes.get(d['instance'],b);boxes[d['instance']]=[min(b[0],m[0]),min(b[1],m[1]),max(b[2],m[2]),max(b[3],m[3])]
  # Room pieces are drawn by state on the page. The rest of the group (the floor title sheet) stays white as captured.
  image=Image.new('RGBA',(1280,720));sprite_rows=[]
  for d in drawn:
   if d['instance'] in piece_index:
    b=io.BytesIO();d['tile'].save(b,'PNG');sprite_rows.append(dict(piece=piece_index[d['instance']],fill=d['texture'].endswith('_b_ID'),x=d['box'][0],y=d['box'][1],w=d['tile'].width,h=d['tile'].height,image='data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()))
   else:image.alpha_composite(d['tile'],(max(0,d['box'][0]),max(0,d['box'][1])))
  buffer=io.BytesIO();image.save(buffer,'PNG')
  try:_,door_trace=render(game,floor['region'],floor['floor'],group_suffix='_door',geometry_only=True);doors=[d['canvas_box'] for d in door_trace['drawn']];door_ink=[d['ink_box'] for d in door_trace['drawn']]
  except ValueError as e:
   if 'floor group not found' not in str(e):raise
   doors=door_ink=[]
  floors.append(dict(sprites=sprite_rows,key=key,name=floor_label(floor['region'],floor['floor']),doors=doors,door_ink=door_ink,image='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode(),pieces=[[piece_index[i],*b] for i,b in boxes.items() if i in piece_index]))
 matches=json.loads((ROOT/'data/room-matches.json').read_text());pieces={p['id']:p for p in native['map_pieces']};floor_of={};room_state=json.loads((ROOT/'data/room-state.json').read_text())['pieces']
 for c in matches['claims']:
  p=pieces[c['native_pieces'][0]]
  for ext in [c['external_id'],*c.get('also_covers',[])]:floor_of[ext]=f"{p['region']}-{p['floor']}"
 only=[dict(key=floor_of[o['place']],mode=o['mode'],place=o['place'].split('/')[1],name=o['name']) for o in check['only_external'] if not o.get('catalogue_rank')] # hidden rewards, as on the map
 colours=json.loads((ROOT/'data/map-colours.json').read_text());bg_arc=Arc((game/'nativePC/arc/ui'/colours['background']['archive']).read_bytes());bg_tex=decode_texture(bg_arc.read(next(m for m in bg_arc.members if m.name==colours['background']['texture'])))
 if hashlib.sha256(bg_tex.tobytes()).hexdigest()!=colours['background']['decoded_rgba_sha256']:raise ValueError('map background differs from the recorded texture')
 bg_png=io.BytesIO();bg_tex.convert('RGB').save(bg_png,'PNG')
 wasm=build_wasm(ROOT/'local/re0map.wasm');header=(ROOT/'src/runtime/labels_generated.h').read_text();atlas=Image.frombytes('RGBA',tuple(int(re.search(rf'#define ATLAS_{a} (\d+)',header)[1]) for a in 'WH'),(ROOT/'assets/labels.bgra').read_bytes(),'raw','BGRA');png=io.BytesIO();atlas.save(png,'PNG',optimize=True)
 (out/'index.html').write_text(PAGE.replace('DATA',json.dumps(dict(icon_first=int(re.search(r'#define ICON_FIRST_GLYPH (\d+)',header)[1]),icons=icons_png(header),face_colours=[colours['face_table']['states'][str(i)] for i in range(8)],bg=dict(xy=colours['background']['canvas_xy'],size=colours['background']['size'],image='data:image/png;base64,'+base64.b64encode(bg_png.getvalue()).decode()),floors=floors,defs=defs,flagsets=flagsets,room_state=[{'v':room_state[p['id']]['visited'],'r':room_state[p['id']]['revealed']} for p in native['map_pieces']],table_rows=[647,589,568],states=row_states(data),rows={str(k):v for k,v in rows.items()},only_external=only,glyphs=glyph_table(),wasm=base64.b64encode(wasm.read_bytes()).decode(),atlas='data:image/png;base64,'+base64.b64encode(png.getvalue()).decode()),ensure_ascii=False),1))
 return len(defs),len(floors)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game',type=Path,required=True);p.add_argument('--output',type=Path,default=ROOT/'local/placement-review');a=p.parse_args()
 if not a.output.resolve().is_relative_to(ROOT/'local'):p.error('map art must stay under local/')
 print('Review: %d marks on %d floors'%build(a.game,a.output))
