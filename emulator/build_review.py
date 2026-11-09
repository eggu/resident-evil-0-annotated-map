"""Build an offline review page from native resource previews (not live-game validation)."""
import argparse
import base64
import io
import json
from pathlib import Path
from render import PROJECT, load_scene, render

PAGE=r'''<!doctype html><html lang="ko"><meta charset="utf-8"><title>RE0 지도 리소스 검수</title>
<style>body{margin:0;background:#202225;color:#eee;font:15px system-ui}header{padding:16px 24px}h1{font-size:22px;margin:0 0 8px}p{margin:8px 0;color:#ccc}nav{display:flex;gap:16px;align-items:center;flex-wrap:wrap}select,button{font:inherit;padding:6px}canvas{display:block;background:#a09b8c;max-width:100%;touch-action:none}#details{white-space:pre-wrap;font:13px monospace;padding:12px 24px}a{color:#9bc8ff}label{display:flex;gap:6px;align-items:center}</style>
<header><h1>RE0 지도 리소스 검수</h1><p>방 조각·공용 아이콘 미리보기 · 문 그룹 제외 · 게임 화면 대조 전 · 방문/아이템/적 상태와 기본 확대 동작은 아직 재현하지 않습니다. 대응명은 교차 검수된 열차 장소에만 있으며 한글명은 프로젝트 번역안입니다.</p>
<nav><select id="floor" aria-label="지역과 층"></select><label>검수 배율 <input id="zoom" type="range" min="0.5" max="4" step="0.1" value="1"><output id="scale">1.0×</output></label><label>이름 <select id="labels"><option value="off">숨김</option><option value="id">내부 ID</option><option value="en">영문 대응명</option><option value="ko">한글 번역안</option></select></label><button id="reset">위치 초기화</button><button id="save">현재 화면 PNG</button><a id="source" target="_blank" rel="noopener">외부 지도 열기</a></nav><p>드래그: 이동 · 방 조각 클릭: 근거 확인 · 배율/이동은 검수용이며 게임의 값으로 검증되지 않았습니다.</p></header>
<canvas id="map" width="1280" height="720" aria-label="지도 미리보기"></canvas><div id="details" role="status"></div>
<script>const scenes=SCENE_DATA;
const canvas=document.querySelector('#map'),ctx=canvas.getContext('2d'),selector=document.querySelector('#floor');
let image=new Image(),selected=null,pan=[0,0],drag=null;
for(let i=0;i<scenes.length;i++){const o=document.createElement('option');o.value=i;o.textContent=scenes[i].label;selector.append(o)}
function paint(){if(!selected||!image.complete)return;const z=Number(document.querySelector('#zoom').value);document.querySelector('#scale').textContent=z.toFixed(1)+'×';ctx.fillStyle='#202225';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.save();ctx.translate(canvas.width/2+pan[0],canvas.height/2+pan[1]);ctx.scale(z,z);ctx.drawImage(image,-canvas.width/2,-canvas.height/2);if(document.querySelector('#labels').value!=='off'){ctx.font='10px system-ui';ctx.textAlign='center';ctx.fillStyle='#b00000';const seen=new Set();for(const row of selected.trace.drawn){if(seen.has(row.instance))continue;seen.add(row.instance);const mode=document.querySelector('#labels').value;const mapped=selected.names?.[row.instance];const text=mode==='id'?row.instance.slice(2):(mapped?.[mode]||'['+row.instance.slice(2)+']');ctx.fillText(text,row.canvas_anchor[0]-canvas.width/2,row.canvas_anchor[1]-canvas.height/2);}}ctx.restore();}
function select(){selected=scenes[Number(selector.value)];image=new Image();image.onload=paint;image.src=selected.image;pan=[0,0];document.querySelector('#source').href=selected.source;document.querySelector('#details').textContent=selected.trace.drawn.length+' sprites / '+selected.trace.omitted.length+' omissions\n'+JSON.stringify(selected.trace.omitted,null,2);}
function point(e){const r=canvas.getBoundingClientRect();return[(e.clientX-r.left)*canvas.width/r.width,(e.clientY-r.top)*canvas.height/r.height]}
canvas.onpointerdown=e=>{drag={start:point(e),pan:[...pan]};canvas.setPointerCapture(e.pointerId)};
canvas.onpointermove=e=>{if(!drag)return;const p=point(e);pan=[drag.pan[0]+p[0]-drag.start[0],drag.pan[1]+p[1]-drag.start[1]];paint()};
canvas.onpointerup=e=>{const p=point(e);if(drag&&Math.hypot(p[0]-drag.start[0],p[1]-drag.start[1])<3){const z=Number(document.querySelector('#zoom').value),x=(p[0]-canvas.width/2-pan[0])/z+canvas.width/2,y=(p[1]-canvas.height/2-pan[1])/z+canvas.height/2;const hits=selected.trace.drawn.filter(r=>x>=r.canvas_box[0]&&x<=r.canvas_box[2]&&y>=r.canvas_box[1]&&y<=r.canvas_box[3]);document.querySelector('#details').textContent=JSON.stringify(hits.map(row=>({name:selected.names?.[row.instance]||null,draw:row})),null,2)}drag=null};canvas.onpointercancel=()=>drag=null;
selector.onchange=select;document.querySelector('#zoom').oninput=paint;document.querySelector('#labels').onchange=paint;document.querySelector('#reset').onclick=()=>{pan=[0,0];document.querySelector('#zoom').value=1;paint()};document.querySelector('#save').onclick=()=>{const a=document.createElement('a');a.download=selected.key+'-review.png';a.href=canvas.toDataURL('image/png');a.click()};select();</script></html>'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--game',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    if not a.output.resolve().is_relative_to(PROJECT/'local'):p.error('review page must stay under local/')
    regions={'tr':('열차','train'),'sh':('양성소','training-facility'),'dm':('양성소 지하','facility-basement'),
             'ch':('연구소','laboratory'),'bt':('공장','factory'),'pl':('처리장','treatment-plant')}
    matches=json.loads((PROJECT/'data/room-matches.json').read_text())
    scenes=[]
    for region,(label,slug) in regions.items():
        _,g,_=load_scene(a.game,region)
        for root in g.instances:
            name=root['name']
            if not name.startswith('Null_'+region) or name.endswith('_door'):continue
            floor=name[len('Null_'+region):];im,trace=render(a.game,region,floor)
            names={}
            for claim in matches['claims']:
                if claim['region']!=region or claim['floor']!=floor:continue
                if claim['evidence']['native_gui_sha256']!=trace['source']['sha256']:
                    raise ValueError('curated place names refer to a different native GUI; re-review needed')
                for piece in claim['native_pieces']:
                    names[piece]=dict(en=claim['name_en'],ko=claim['name_ko'],source=claim['evidence']['source_url'],scope=claim['result'])
            buffer=io.BytesIO();im.save(buffer,format='PNG')
            scenes.append(dict(key=region+'-'+floor,label=label+' / '+floor.upper(),trace=trace,
                               names=names,source='https://www.evilresource.com/resident-evil-zero/maps/'+slug,
                               image='data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode()))
    data=json.dumps(scenes,ensure_ascii=False).replace('<','\\u003c')
    a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(PAGE.replace('SCENE_DATA',data))
    print(f'Offline review page: {len(scenes)} floors, {a.output}')


if __name__=='__main__':main()
