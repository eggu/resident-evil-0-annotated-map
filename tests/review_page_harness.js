// Runs the review page's own script against a stub canvas and the real WebAssembly: proves page wiring, not browser layout or GPU.
const fs=require('fs');const js=fs.readFileSync(process.argv[2],'utf8').match(/<script>([\s\S]*)<\/script>/)[1];
const ctx=new Proxy({},{get:(t,k)=>k in t?t[k]:()=>{},set:(t,k,v)=>{t[k]=v;return true}});
const mk=()=>({children:[],style:{},value:'',textContent:'',append(...c){this.children.push(...c);if(!this.value&&c[0]&&c[0].value!==undefined)this.value=c[0].value},getContext:()=>ctx,getBoundingClientRect:()=>({left:0,top:0,width:1280,height:720})});
const els={},listeners={};global.document={getElementById:i=>els[i]||(els[i]=mk()),createElement:()=>mk(),addEventListener(n,f){listeners[n]=f}};global.Image=function(){};global.atob=s=>Buffer.from(s,'base64').toString('binary');
new Function(js)();
const R=globalThis.re0Review;
R.ready.then(()=>{const F=els.floor;const set=k=>{F.value=k;F.onchange()};const g=()=>R.ops().map(o=>o.g);const out={floors:F.children.map(o=>o.textContent)};
set('tr-1f');out.view=R.view();out.doors=R.doors();out.obstaclesPassed=R.obstaclesPassed();out.ko=g();out.marks=R.shown().length;R.press('\\');out.en=g();out.floorsEn=F.children.map(o=>o.textContent);R.press('\\');
R.press('1');out.noNames=g();R.press('1');R.press('0');out.allOff=g();R.press('0');
const fw=()=>{const room=R.ops().filter(o=>o.g>=0);return room.map(o=>o.r-o.l)};const tot=()=>fw().reduce((a,b)=>a+b,0);const w0=tot();R.press('+');out.bigger=tot()>w0;R.press('-');
const alpha=()=>R.ops().filter(o=>o.g>=0).reduce((a,o)=>a+(o.col>>>24),0);const a0=alpha();R.press('[');out.opacityApplied=alpha()<a0;R.press(']');
const hb0=g().length;listeners.keydown({key:'h'});const hb1=g().length;out.itemNamesOn=hb1>hb0;listeners.keydown({key:'h'});out.itemNamesNoCommon=g().length>=hb0&&g().length<=hb1;listeners.keydown({key:'h'});out.itemNamesOff=g().length==hb0;
const here=()=>R.shown().filter(d=>out.cabin.includes(d.row)).length;out.cabin=[21,22,23];R.setFlags('progress');out.rewardsOff=here();R.setFlags('rewards');out.rewardsOn=here();const all=R.shown().length;R.setFlags('start');out.startFewer=R.shown().length<all;out.progressLeft=R.shown().map(d=>d.category);R.setFlags('finished');out.finishedLeft=R.shown().map(d=>d.category);out.finishedMismatches=R.mismatches();R.setFlags('progress');out.size=R.setting('size');set('tr-1f');R.setFlags('progress');const mode=()=>els.mode.value,before=mode(),marksAt=()=>R.shown().length,cycle=()=>{const c=[marksAt()];R.press('9');c.push(marksAt());R.press('9');c.push(marksAt());R.press('9');return c};
R.setRooms('visited');out.scopeAllVisited=cycle();R.setRooms('half');out.scopeHalfNoMap=cycle();R.setRooms('half-map');out.scopeHalfMap=cycle();R.setRooms('map');out.scopeMapOnly=cycle();R.setRooms('visited');out.difficultyKept=mode()==before;
console.log(JSON.stringify(out))});
