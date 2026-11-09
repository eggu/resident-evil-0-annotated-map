"""DOM/canvas contract smoke test; deliberately not a real-browser/GPU test."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'emulator'))
from build_review import PAGE


@unittest.skipUnless(shutil.which('node'),'Node required for review interaction smoke test')
class ReviewTest(unittest.TestCase):
    def test_select_zoom_hit_test_and_export(self):
        scene=dict(names={'i_test':{'en':'Synthetic room','ko':'합성 방'}},label='synthetic',key='synthetic',source='https://example.invalid/',image='synthetic',
                   trace=dict(drawn=[dict(instance='i_test',gui_position=[0,0],canvas_anchor=[640,360],canvas_box=[630,350,650,370])],omitted=[]))
        page=PAGE.replace('SCENE_DATA',json.dumps([scene,dict(scene,key='second')]))
        js=page.split('<script>',1)[1].split('</script>',1)[0]
        pre='''const assert=require('node:assert/strict');
const context={fillRect(){},save(){},translate(){},scale(){},drawImage(){},fillText(){},restore(){}};
let exported=0,lastText='';context.fillText=(text)=>{lastText=text};const elements={};
for(const key of ['#map','#floor','#zoom','#scale','#labels','#reset','#save','#source','#details'])elements[key]={value:key==='#zoom'?'1':(key==='#labels'?'off':'0'),checked:false,children:[],append(o){this.children.push(o)}};
Object.assign(elements['#map'],{width:1280,height:720,getContext(){return context},getBoundingClientRect(){return {left:0,top:0,width:1280,height:720}},setPointerCapture(){},toDataURL(){return 'data:image/png;base64,synthetic'}});
global.document={querySelector(key){return elements[key]},createElement(){return {click(){exported++}}}};
global.Image=class{complete=true;set src(s){this.onload()}};
'''
        post='''
assert.equal(selector.children.length,2);
document.querySelector('#labels').value='en';document.querySelector('#labels').onchange();assert.equal(lastText,'Synthetic room');
document.querySelector('#labels').value='ko';document.querySelector('#labels').onchange();assert.equal(lastText,'합성 방');
assert.equal(document.querySelector('#source').href,'https://example.invalid/');
canvas.onpointerdown({clientX:640,clientY:360,pointerId:1});canvas.onpointerup({clientX:640,clientY:360});
assert.match(document.querySelector('#details').textContent,/i_test/);
document.querySelector('#zoom').value='2';document.querySelector('#zoom').oninput();assert.equal(document.querySelector('#scale').textContent,'2.0×');
canvas.onpointerdown({clientX:640,clientY:360,pointerId:1});canvas.onpointermove({clientX:660,clientY:380});canvas.onpointerup({clientX:660,clientY:380});assert.deepEqual(pan,[20,20]);
selector.value='1';selector.onchange();assert.deepEqual(pan,[0,0]);assert.equal(selected.key,'second');
document.querySelector('#reset').onclick();assert.equal(document.querySelector('#zoom').value,1);
document.querySelector('#save').onclick();assert.equal(exported,1);
'''
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'review.cjs';path.write_text(pre+js+post)
            result=subprocess.run(['node',str(path)],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
