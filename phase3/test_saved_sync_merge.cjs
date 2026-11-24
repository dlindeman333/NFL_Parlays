const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const stable=html.slice(html.indexOf('function safe6StableValue('),html.indexOf('function safe6Active('));
const merge=html.slice(html.indexOf('function safe6Equal('),html.indexOf('async function safe6Cycle('));
const ctx=vm.createContext({});vm.runInContext(stable+merge+';this.plan=safe6MergePlan;this.canonical=safe6Canonical;',ctx);
const p=(id,name=id)=>({id,name,legs:[{pick:'synthetic'}]});const s=(saved=[],deleted=[])=>({saved,deleted});const a=p('a'),b=p('b'),c=p('c');
const eq=(x,y)=>assert.equal(ctx.canonical(x),ctx.canonical(y));
let n=0;function test(name,fn){fn();n++;console.log('PASS '+name);}
test('cloud addition',()=>eq(ctx.plan(s([a]),s([a,b]),s([a])).device,s([a,b])));
test('device addition',()=>eq(ctx.plan(s([a]),s([a]),s([a,b])).cloud,s([a,b])));
test('independent additions',()=>eq(ctx.plan(s([a]),s([a,b]),s([a,c])).device,s([a,b,c])));
test('one sided rename',()=>eq(ctx.plan(s([a]),s([p('a','new')]),s([a])).device,s([p('a','new')])));
test('ordering',()=>eq(s([a,b]),s([b,{legs:a.legs,name:a.name,id:a.id}])));
test('isolated concurrent edits',()=>{const r=ctx.plan(s([a]),s([p('a','cloud'),b]),s([p('a','device'),c]));assert.equal(r.conflicts.length,1);eq(r.cloud,s([p('a','cloud'),b,c]));eq(r.device,s([p('a','device'),b,c]));});
test('verified deletion',()=>eq(ctx.plan(s([a,b]),s([b],['a']),s([a,b])).device,s([b],['a'])));
test('delete/edit blocks',()=>assert.equal(ctx.plan(s([a]),s([],['a']),s([p('a','edit')])).blocked,true));
test('missing without marker preserved',()=>{const r=ctx.plan(s([a]),s([]),s([a,b]));assert.equal(r.conflicts.length,1);eq(r.device,s([a,b]));});
test('duplicate rejected',()=>assert.throws(()=>ctx.plan(s([a,a]),s(),s())));
console.log(`${n} integrated saved-sync merge tests passed; no network or live data.`);
