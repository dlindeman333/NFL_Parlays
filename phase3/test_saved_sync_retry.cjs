const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'../index.html'),'utf8');
const code=html.slice(html.indexOf('function safe6Retryable('),html.indexOf('async function safe6Cycle('));
const ctx=vm.createContext({});vm.runInContext(code+';this.retry=safe6Retryable;',ctx);
const cases=[['network read', {safeReadRetry:true},false,true],['revision race',{message:'Cloud changed before write'},false,true],['uncertain write',{safeReadRetry:true},true,false],['revision after write',{message:'Cloud changed before write'},true,false],['ownership',{message:'Account ownership changed'},false,false],['delete/edit',{message:'Deletion/edit conflict; review required'},false,false],['readback mismatch',{message:'Cloud readback mismatch'},true,false],['device changed before write',{message:'Device changed during synchronization'},false,true],['device changed after write',{message:'Device changed during synchronization'},true,false],['account changed during read',{message:'Account changed during cloud read'},false,false],['manual pause',{message:'Synchronization paused'},false,false],['unknown error',{},false,false]];
for(const [name,error,attempted,expected] of cases){assert.equal(ctx.retry(error,attempted),expected,name);console.log('PASS '+name);}
console.log(`${cases.length} retry classification tests passed (not end-to-end).`);

// Regression guards for the production baseline-loss incident.
const reconcile=html.slice(html.indexOf('async function reconcileSavedParlays('),html.indexOf('reconcileSavedButton.onclick'));
assert.ok(reconcile.indexOf('phase3LocalStorage.removeItem(safe6Key(uid))')>reconcile.indexOf("if(!await phase3V10Confirm("),'cancel must preserve baseline');
assert.ok(reconcile.includes('safe6Running=!writeAttempted&&priorRunning'),'resume only before attempted write');
const cycle=html.slice(html.indexOf('async function safe6Cycle('),html.indexOf('safe6Button.onclick'));
assert.ok(cycle.includes("if(c!==l||!part||safe6Canonical(safe6View(JSON.parse(part),'Account partition'))!==l)throw Error('Missing verified baseline; reconciliation required')"),'missing baseline recovery requires three matching copies');
assert.ok(html.includes("blockers.push('no verified baseline for divergent records; review reconciliation first')"),'preflight must report missing baseline');
console.log('PASS four baseline incident source guards (not behavioral tests)');
