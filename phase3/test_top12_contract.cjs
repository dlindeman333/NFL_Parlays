// Offline Top 12 front-end contract test; no network or browser/cloud writes.
const fs=require('fs');
const vm=require('vm');
const assert=require('assert');
const html=fs.readFileSync(require('path').join(__dirname,'..','index.html'),'utf8');
const start=html.indexOf('function phase4Top12GameCandidates(g){');
const end=html.indexOf('window.phase4Top12GameCandidates=phase4Top12GameCandidates;',start);
assert(start>0&&end>start,'Top12 helper must exist');
const players=Array.from({length:17},(_,i)=>({i,n:'Player '+String(i).padStart(2,'0'),tm:i%2?'MIA':'BUF',k:'rec',dynamic:false}));
const sandbox={PLY:players,window:{},playerSuggested:()=>true,phase3PlayerOut:p=>p.i===3,
 advMetrics:(p,g)=>({p,g,line:49.5,prob:.51+p.i/100,score:100-p.i,manual:null})};
vm.createContext(sandbox);
vm.runInContext(html.slice(start,end)+'\nwindow.phase4Top12GameCandidates=phase4Top12GameCandidates;',sandbox);
const candidates=sandbox.window.phase4Top12GameCandidates({a:'BUF',h:'MIA'});
assert.strictEqual(candidates.length,16);
assert(!candidates.some(x=>x.p.i===3));
assert.deepStrictEqual(candidates.slice(0,12).map(x=>x.p.i),[0,1,2,4,5,6,7,8,9,10,11,12]);
assert(html.includes('Optional legacy browser-only Top 12 tracking and backups'));
assert(html.includes('original_grades:'));
console.log('Top 12 browser-model selection and cloud-history contract passed (synthetic; no writes)');
