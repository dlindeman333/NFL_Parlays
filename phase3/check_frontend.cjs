const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(__dirname+'/../index.html','utf8');
let checks=0;
for(const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi))new vm.Script(match[1]);
checks++;
const bridge=html.slice(html.indexOf('window.phase3TrackUpcomingPredictions=async'),html.indexOf('\nsettings();auth=',html.indexOf('window.phase3TrackUpcomingPredictions=async')));
let active=true,writeCount=0;
const uid='00000000-0000-0000-0000-000000000001';
const snapshot={season:2026,week:10,game_id:'123',kickoff_at:'2099-01-01T00:00:00Z',created_at:'2026-11-14T00:00:00Z',away_team:'BUF',home_team:'MIA',picks:[{label:'BUF moneyline'}]};
let mutateDuringPost=false;
const context={window:{},auth:{},Date,Set,Number,Array,Error,encodeURIComponent,userId:async()=>uid,safe6Active:id=>active&&id===uid,token:async()=>'mock',api:async(path,options={})=>{
 if(options.method==='POST'){
  assert(path.startsWith('/rest/v1/nfl_prediction_subscriptions_v2?'));
  assert.equal(options.headers.Authorization,'Bearer mock');
  const rows=JSON.parse(options.body);assert(rows.every(r=>r.user_id===uid));writeCount++;
  if(mutateDuringPost)active=false;return [];
 }
 if(path.includes('nfl_prediction_snapshots_v2?'))return [snapshot];
 if(path.includes('nfl_prediction_grades_v2?'))return [{season:2026,week:10,game_id:'123',outcome:'hit'}];
 if(path.includes('nfl_prediction_subscriptions_v2?'))return [{user_id:uid,season:2026,week:10,game_id:'123',tracked_at:'2026-11-14T01:00:00Z',nfl_prediction_snapshots_v2:snapshot}];
 throw Error('Unexpected backend route');
}};
vm.createContext(context);vm.runInContext(bridge,context);
(async()=>{
 assert.equal(await context.window.phase3TrackUpcomingPredictions(2026,10),1);assert.equal(writeCount,1);checks++;
 const rows=await context.window.phase3ReadOwnPredictionHistory();assert(rows[0].payload.grade_summary.includes('1 hits'));assert.equal(rows[0].payload.picks[0].label,'BUF moneyline');checks++;
 active=false;await assert.rejects(()=>context.window.phase3TrackUpcomingPredictions(2026,10),/ownership/);assert.equal(writeCount,1);checks++;
 await assert.rejects(()=>context.window.phase3ReadOwnPredictionHistory(),/ownership/);checks++;
 active=true;mutateDuringPost=true;await assert.rejects(()=>context.window.phase3TrackUpcomingPredictions(2026,10),/Account changed/);checks++;
 await assert.rejects(()=>context.window.phase3TrackUpcomingPredictions(2026,0),/Invalid/);checks++;
 context.auth=null;assert.equal(await context.window.phase3ReadOwnPredictionHistory(),null);checks++;
 console.log(checks+' focused frontend checks passed (VM/mocked backend; not live RLS proof)');
})().catch(e=>{console.error(e);process.exitCode=1});
