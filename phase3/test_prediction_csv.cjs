// Read-only Prediction Results CSV contract. All records below are synthetic;
// none represent real 2026 sportsbook lines, cloud grades, or saved parlays.
'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(path.resolve(__dirname,'../index.html'),'utf8');
const start=html.indexOf('<script id="phase3PredictionCsvExport">');
const cut=html.indexOf(" const section=document.createElement('section')",start);
assert(start>0&&cut>start,'CSV export script and pure helpers must exist');
const segment=html.slice(start+'<script id="phase3PredictionCsvExport">'.length,cut)+'\n})();';
const context={window:{},document:{getElementById:()=>({})},Date,Number,Math,JSON,Map,Set,Object,String,Array,RegExp};
vm.runInNewContext(segment,context,{filename:'prediction-csv-helpers.js'});
const core=context.window.phase3PredictionCsvCore;
assert(core,'Export core must remain regression-testable');
let checks=0;

// RFC4180, Excel formula safety, UTF-8 BOM, and explicit provenance columns.
const csv=core.csv([{season:2026,week:11,record_type:'INDIVIDUAL_PICK',
 prediction:'=HYPERLINK("https://invalid.test","fake")',
 notes:'second line\n\"quoted\"',source:'RETROSPECTIVE_MODEL'}]);
assert(csv.charCodeAt(0)===0xfeff);
assert(csv.startsWith('\ufeff"season","week","record_type"'));
assert(csv.includes('"\'=HYPERLINK(""https://invalid.test"",""fake"")"'));
assert(csv.includes('"second line\n""quoted"""'));
assert(csv.includes('\r\n"2026","11"'));
assert(csv.includes('"outcome_provenance"'));
checks++;

const kickoff='2099-11-22T18:00:00Z';
const capture='2099-11-22T17:28:00Z';
const mk=(game_id,created_at,extra={})=>({season:2026,week:11,game_id,
 created_at,kickoff_at:kickoff,away_team:'BUF',home_team:'MIA',
 picks:[{market:'player',player_name:'Example Player',stat:'receptions',
    side:'u',line:4.5,probability:.58,label:'Example Player Under 4.5 receptions'}],...extra});
assert(core.validCapture(mk('a',capture)));
assert(!core.validCapture(mk('a','2099-11-22T17:24:59Z')));
assert(!core.validCapture(mk('a','2099-11-22T17:30:01Z')));
checks++;

const grade=(game_id,outcome,index=0)=>({season:2026,week:11,game_id,
 pick_key:'v1:'+index+':'+'a'.repeat(64),outcome,actual_value:3});
const archived=core.officialRows([
 {version:'v2',snapshots:[mk('one','2099-11-22T17:24:59Z'),mk('two',capture)],
  grades:[grade('one','hit'),grade('two','miss')]},
 {version:'v3',snapshots:[mk('two',capture),mk('three',capture),mk('four',capture),mk('five',capture)],
  grades:[grade('two','hit'),grade('three','push'),grade('four','hit',1)]}
]);
assert.equal(archived.excludedCount,1,'early snapshot excluded');
assert.equal(archived.rows.length,4,'v3 precedence suppresses duplicate v2 grade');
assert.equal(archived.rows.find(r=>r.game_id==='two').source,'OFFICIAL_TOP12_V3');
assert.equal(archived.rows.find(r=>r.game_id==='two').outcome,'HIT');
assert.equal(archived.rows.find(r=>r.game_id==='three').outcome,'PUSH');
assert.equal(archived.rows.find(r=>r.game_id==='four').outcome,'PENDING');
assert.equal(archived.rows.find(r=>r.game_id==='five').outcome,'PENDING');
assert(archived.rows.every(r=>r.outcome_provenance!=='MODEL_GENERATED_HISTORICAL_BACKTEST'));
checks++;

const saved=[
 {id:1,season:2026,wk:11,stake:10,dec:11,name:'4 legs',status:'lost',legs:[{t:'One under',m:'BUF @ MIA'},{t:'Two over',m:'BUF @ MIA'}]},
 {id:2,season:2025,wk:11,status:'won',legs:[{t:'Old year'}]},
 {id:3,wk:11,status:'won',legs:[{t:'Unknown year'}]}
];
const defaultSaved=core.savedRows(saved,2026);
assert.equal(defaultSaved.rows.length,3,'one summary and two leg rows');
assert.equal(defaultSaved.unknownSeason,1);
assert.equal(defaultSaved.rows[0].outcome,'MANUAL_LOST');
assert.equal(defaultSaved.rows[0].outcome_provenance,'USER_RECORDED_NOT_SPORTSBOOK_VERIFIED');
assert(defaultSaved.rows.slice(1).every(r=>r.outcome==='UNVERIFIED'));
const legacy=core.savedRows(saved,2026,{includeUnattributed:true});
assert.equal(legacy.rows.length,5);
assert(legacy.rows.filter(r=>r.parlay_id==='3').every(r=>r.season===''));
checks++;

const retro=core.retrospectiveRows(2026,2026,[11],()=>[{id:12,a:'BUF',h:'MIA',sc:[20,17]}],
 games=>games.map(g=>({g,x:{m:'rec',s:'u',p:.55},result:false,reason:'synthetic data'})),
 ()=> 'Example Under receiving yards');
assert.equal(retro.length,1);
assert.equal(retro[0].outcome,'MISS');
assert.equal(retro[0].source,'RETROSPECTIVE_MODEL');
assert.equal(retro[0].outcome_provenance,'MODEL_GENERATED_HISTORICAL_BACKTEST');
assert.equal(core.retrospectiveRows(2025,2026,[11],()=>[],()=>[],()=>'' ).length,0);
checks++;

// Explicit full-week checks prevent single-game/truncated scoreboard exports.
const events=Array.from({length:13},(_,i)=>({id:String(i+1),status:{type:{completed:true}}}));
assert(core.completedFromEspn({events}));
assert(!core.completedFromEspn({events:events.slice(0,10)}));
assert(!core.completedFromEspn({events:[...events.slice(0,-1),{...events[12],status:{type:{completed:false}}}]}));
assert(!core.completedFromEspn({events:[...events.slice(0,-1),events[0]]}));
assert(!core.completedFromEspn({events:[]}));
checks++;

assert(html.includes('id="predictionCsvSeason"')&&html.includes('id="predictionCsvScope"')&&html.includes('id="predictionCsvWeek"'));
assert(html.includes('All fully completed weeks')&&html.includes('Specific week'));
assert(html.includes('Download CSV report'));
assert(html.includes('phase3ReadSavedParlaysForCsv'));
assert(html.includes('season:original?original.season:SEASON'));
assert(html.includes('Only verified 30-35-minute snapshots count as official predictions'));
assert(html.includes('prediction-csv-controls{display:grid;grid-template-columns:repeat(2,minmax(0,1fr))}'));
checks++;
console.log(checks+' Prediction Results CSV contract groups passed (synthetic data; read-only).');

// Exercise the real download button with a simulated browser and read-only
// responses. Confirm the release works while the optional v3 tables are absent.
(async()=>{
 const elems={},requests=[],downloads=[];
 const el=id=>elems[id]||(elems[id]={value:'',textContent:'',disabled:false,checked:false,
  handlers:{},addEventListener(name,handler){this.handlers[name]=handler},append(){},after(){},replaceChildren(){}});
 const panel={firstChild:null,insertBefore(node){this.node=node}};
 const fakeDocument={
  addEventListener(name,handler){this.handlers[name]=handler},handlers:{},
  getElementById:id=>id==='advPerformancePanel'?panel:id==='cloudOfficialGrades'?null:elems[id]||null,
  createElement:tag=>{
   if(tag==='a')return {click(){downloads.push({blob:blobs.get(this.href),filename:this.download})}};
   if(tag==='option')return {value:'',textContent:''};
   return {className:'',id:'',setAttribute(){},
    set innerHTML(value){this._html=value;for(const match of value.matchAll(/id="([^"]+)"/g))el(match[1]);},
    get innerHTML(){return this._html}};
  }
 };
 const cloudRows=[mk('browser-game',capture)];
 const gradeRows=[grade('browser-game','hit')];
 const fetch=async(url,options={})=>{
  requests.push({url,options});
  assert.equal(options.method,'GET','Report may make GET requests only');
  if(url.includes('_v3?'))return {ok:false,status:404,text:async()=>'{"code":"PGRST205","message":"Could not find the table in the schema cache"}'};
  if(url.includes('_v2?'))return {ok:true,json:async()=>url.includes('snapshots_v2')?cloudRows:gradeRows};
  if(url.includes('/scoreboard?'))return {ok:true,json:async()=>({events})};
  throw Error('Unexpected read endpoint: '+url);
 };
 const blobs=new Map();
 const browserContext={window:{phase3FetchCsvArchive:path=>fetch(path,{method:'GET'})},document:fakeDocument,fetch,
  URL:{createObjectURL(blob){const key='blob:'+blobs.size;blobs.set(key,blob);return key},revokeObjectURL(key){blobs.delete(key)}},
  performancePickExportFields:()=>({}),
  CLOUD_URL:'https://example.invalid',CLOUD_PUBLIC_KEY:'synthetic-read-key',
  currentNFLSeason:()=>2026,SEASON:2026,MODEL_SEASON:2026,wk:11,WKS:{},
  performanceRows:()=>[],performancePickName:()=>'',hasCompletedPlayerStats:()=>false,
  downloadFile:(blob,filename)=>downloads.push({blob,filename}),
  Blob,Date,Number,Math,JSON,Map,Set,Object,String,Array,RegExp,Error,Promise};
 const fullScript=html.slice(start+'<script id="phase3PredictionCsvExport">'.length,
  html.indexOf('</script>',start));
 vm.runInNewContext(fullScript,browserContext,{filename:'prediction-csv-browser-sim.js'});
 el('predictionCsvScope').value='specific';el('predictionCsvKind').value='individual';
 el('predictionCsvSeason').value='2026';el('predictionCsvWeek').value='11';
 await el('predictionCsvDownload').handlers.click();
 assert.equal(downloads.length,1);
 assert.equal(downloads[0].filename,'NFL_Prediction_Results_2026_Week_11.csv');
 assert((await downloads[0].blob.text()).includes('"OFFICIAL_TOP12_V2"'));
 assert.match(el('predictionCsvStatus').textContent,/Optional v3 archive not installed/);
 assert(requests.every(r=>r.options.method==='GET'));
 checks++;

 el('predictionCsvScope').value='completed';
 await el('predictionCsvDownload').handlers.click();
 assert.equal(downloads.length,2);
 assert.equal(downloads[1].filename,'NFL_Prediction_Results_2026_All_Completed_Weeks.csv');
 assert(requests.some(r=>r.url.includes('/scoreboard?')));
 checks++;

 el('predictionCsvScope').value='specific';el('predictionCsvWeek').value='10';
 await el('predictionCsvDownload').handlers.click();
 assert.equal(downloads.length,2,'No empty CSV should be downloaded');
 assert.match(el('predictionCsvStatus').textContent,/No eligible predictions or saved parlays/);
 checks++;

 browserContext.window.phase3ReadSavedParlaysForCsv=async()=>[saved[0]];
 el('predictionCsvKind').value='parlays';el('predictionCsvWeek').value='11';
 await el('predictionCsvDownload').handlers.click();
 assert.equal(downloads.length,3);
 assert((await downloads[2].blob.text()).includes('"PARLAY_SUMMARY"'));
 assert((await downloads[2].blob.text()).includes('"UNVERIFIED"'));
 assert(!requests.some(r=>r.options.method==='POST'||r.options.method==='PATCH'||r.options.method==='DELETE'));
 checks++;
 console.log('4 CSV export UI flows passed (synthetic data, v2-only compatibility, no writes).');
})().catch(error=>{console.error(error);process.exitCode=1});
