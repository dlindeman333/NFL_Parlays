// Offline Top 12 front-end contract test; no network or browser/cloud writes.
const fs=require('fs');
const vm=require('vm');
const assert=require('assert');
const html=fs.readFileSync(require('path').join(__dirname,'..','index.html'),'utf8');
const start=html.indexOf('function phase4Top12GameCandidates(g){');
const end=html.indexOf('window.phase4Top12GameCandidates=phase4Top12GameCandidates;',start);
assert(start>0&&end>start,'Top12 helper must exist');
const players=Array.from({length:17},(_,i)=>({i,n:'Player '+String(i).padStart(2,'0'),tm:i%2?'MIA':'BUF',k:'rec',dynamic:false}));
players.push(
 {i:17,n:'Opponent',tm:'NYJ',k:'rec'},
 {i:18,n:'Unlisted',tm:'BUF',k:'rec'},
 {i:19,n:'Manual',tm:'BUF',k:'rec'},
 {i:20,n:'Missing Line',tm:'BUF',k:'rec'},
 {i:21,n:'Touchdown',tm:'BUF',k:'td'},
 {i:22,n:'Invalid Line',tm:'BUF',k:'rec'});
const sandbox={PLY:players,window:{},playerSuggested:p=>p.i!==18,phase3PlayerOut:p=>p.i===3,
 reliablePlayerUsage:p=>p.i!==19,advancedPickSide:x=>x.p.k==='td'?'o':'u',
 advMetrics:(p,g,options)=>(assert.strictEqual(options.useManual,false),{p,g,line:p.i===20||p.i===21?null:p.i===22?'not-a-number':49.5,
   prob:.51+p.i/100,score:p.i===21?-100:100-p.i})};
vm.createContext(sandbox);
vm.runInContext(html.slice(start,end)+'\nwindow.phase4Top12GameCandidates=phase4Top12GameCandidates;',sandbox);
const candidates=sandbox.window.phase4Top12GameCandidates({a:'BUF',h:'MIA'});
assert.strictEqual(candidates.length,17);
assert(!candidates.some(x=>x.p.i===3));
assert.deepStrictEqual(candidates.slice(0,12).map(x=>x.p.i),[0,1,2,4,5,6,7,8,9,10,11,12]);
assert.deepStrictEqual(candidates.map(x=>x.p.i),[0,1,2,4,5,6,7,8,9,10,11,12,13,14,15,16,21]);
assert(!candidates.some(x=>[17,18,19,20,22].includes(x.p.i)),'exclude opposing teams, unsuggested, ineligible, and invalid-line picks');
assert(candidates.some(x=>x.p.k==='td'&&x.line===null),'touchdowns permit missing numeric lines');
assert(html.includes('phase4Top12GameCandidates(g).slice(0,12)'),'local capture uses the canonical 12-pick cap');
assert(html.includes('Optional legacy browser-only Top 12 tracking and backups'));
assert(html.includes('original_grades:'));
assert(html.includes('window.phase3AuthenticPregameSnapshot(original)'),'cloud history checks authentic capture provenance');
console.log('Top 12 selection, exclusions, cap and cloud-history contract passed (synthetic; no writes)');
