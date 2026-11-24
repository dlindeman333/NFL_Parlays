const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync('index.html','utf8');
const start=html.indexOf('function makeXlsx('),end=html.indexOf('function downloadFile(',start);
assert.ok(start>=0&&end>start);
const ctx=vm.createContext({TextEncoder,Blob});
vm.runInContext(html.slice(start,end),ctx);
vm.runInContext(fs.readFileSync('phase3/comprehensive_workbook_review.js','utf8'),ctx);
const tables={'AI Performance':[{category:'top12',market:'all',hit:3,miss:1,hit_rate:.75}],'AI Prediction Details':[{player:'A & B',line:12.5,outcome:'hit'}],'Suggested Performance':[],'Suggested Parlays':[{snapshot_id:'s',outcome:'pending'}],'Suggested Legs':[{snapshot_id:'s',leg_number:1}]};
(async()=>{const sheets=ctx.comprehensiveWorkbookSheets([['Legacy',[['Original']]]],tables);const blob=ctx.makeXlsx(sheets,{styled:true});fs.writeFileSync(process.argv[2],Buffer.from(await blob.arrayBuffer()));})().catch(e=>{console.error(e);process.exitCode=1});
