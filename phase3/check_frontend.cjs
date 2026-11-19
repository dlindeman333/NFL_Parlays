const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(__dirname+'/../index.html','utf8');
let checks=0;
for(const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi))new vm.Script(match[1]);
checks++;
assert(html.includes('teamtot[a-z]*|td[ah]'));
assert(html.includes("for(const t of ['a','h'])for(const side of ['o','u'])add('td'+t,side,'td')"));
assert(!html.includes("if(!supportedTeamOnly&&filterHas(pf,'td'))"));
checks++;
const teamCode=html.slice(html.indexOf("const TEAM_POINTS_LINES_KEY="),html.indexOf('\nlet startupScheduleSelection',html.indexOf("const TEAM_POINTS_LINES_KEY=")));
assert(teamCode.includes('function saveTeamPointsLines'));
const teamGame={id:'g1',a:'BUF',h:'MIA',pp:{a:{pts:25},h:{pts:20}}};
const teamFields={'team-points-line-g1-a':{value:''},'team-points-line-g1-h':{value:''},'team-points-status-g1':{textContent:''}};
let teamWrites=0,teamStored=null,teamDraws=0;
const teamContext={SEASON:2026,wk:10,games:[teamGame],Number,Math,JSON,String,Array,Object,Map,
 phase3LocalStorage:{getItem:()=>teamStored,setItem:(key,value)=>{teamStored=value;teamWrites++}},
 nc:x=>1/(1+Math.exp(-1.702*x)),document:{getElementById:id=>teamFields[id]},
 draw:()=>{teamDraws++},plays:()=>{},renderAdvanced:()=>{}};
vm.createContext(teamContext);vm.runInContext(teamCode,teamContext);
assert.equal(vm.runInContext("verifiedTeamPointsLine(games[0],'a')",teamContext),null);checks++;
teamFields['team-points-line-g1-a'].value='23.5';teamFields['team-points-line-g1-h'].value='21.5';
vm.runInContext("saveTeamPointsLines('g1')",teamContext);
assert.equal(vm.runInContext("verifiedTeamPointsLine(games[0],'a')",teamContext),23.5);
assert.equal(teamWrites,1);assert.equal(teamDraws,1);checks++;
teamFields['team-points-line-g1-a'].value='23.3';
vm.runInContext("saveTeamPointsLines('g1')",teamContext);
assert.equal(teamWrites,1);assert.match(teamFields['team-points-status-g1'].textContent,/half-point/);checks++;
assert(vm.runInContext("teamPointsOverProbability(games[0],'a',23.5)",teamContext)>.5);
assert(html.includes('teamPointsLine:line')&&html.includes('verifiedTeamPointsLine(g,t)'));
checks++;
const bridge=html.slice(html.indexOf('window.phase3TrackUpcomingPredictions=async'),html.indexOf('\nsettings();auth=',html.indexOf('window.phase3TrackUpcomingPredictions=async')));
let active=true,writeCount=0,subscribed=true,archiveRecords;
const uid='00000000-0000-0000-0000-000000000001';
const snapshot={season:2026,week:10,game_id:'123',kickoff_at:'2099-01-01T00:00:00Z',created_at:'2026-11-14T00:00:00Z',away_team:'BUF',home_team:'MIA',picks:[{label:'BUF moneyline'}]};
archiveRecords=[snapshot];
let mutateDuringPost=false;
const context={window:{},auth:{},SEASON:2026,Date,Set,Map,Number,Array,Error,encodeURIComponent,userId:async()=>uid,safe6Active:id=>active&&id===uid,token:async()=>'mock',api:async(path,options={})=>{
 if(options.method==='POST'){
  assert(path.startsWith('/rest/v1/nfl_prediction_subscriptions_v2?'));
  assert.equal(options.headers.Authorization,'Bearer mock');
  const rows=JSON.parse(options.body);assert(rows.every(r=>r.user_id===uid));writeCount++;
  if(mutateDuringPost)active=false;return [];
 }
 if(path.includes('nfl_prediction_snapshots_v2?'))return archiveRecords;
 if(path.includes('nfl_prediction_grades_v2?'))return [{season:2026,week:10,game_id:'123',outcome:'hit'}];
 if(path.includes('nfl_prediction_subscriptions_v2?'))return subscribed?[{user_id:uid,season:2026,week:10,game_id:'123',tracked_at:'2026-11-14T01:00:00Z',nfl_prediction_snapshots_v2:snapshot}]:[];
 throw Error('Unexpected backend route');
}};
vm.createContext(context);vm.runInContext(bridge,context);
(async()=>{
 assert.equal(await context.window.phase3TrackUpcomingPredictions(2026,10),1);assert.equal(writeCount,1);checks++;
 const rows=await context.window.phase3ReadOwnPredictionHistory();assert(rows[0].payload.grade_summary.includes('1 hits'));assert.equal(rows[0].payload.picks[0].label,'BUF moneyline');checks++;
 assert.equal(rows.length,1);assert.equal(rows[0].archive_only,false);checks++;
 subscribed=false;
 const automatic=await context.window.phase3ReadOwnPredictionHistory();
 assert.equal(automatic.length,1);assert.equal(automatic[0].archive_only,true);
 assert.equal(automatic[0].payload.picks[0].label,'BUF moneyline');assert.equal(writeCount,1);checks++;
 archiveRecords=[{...snapshot,created_at:'2099-01-01T00:00:00Z'}];
 assert.equal((await context.window.phase3ReadOwnPredictionHistory()).length,0);checks++;
 archiveRecords=[snapshot];subscribed=true;
 active=false;await assert.rejects(()=>context.window.phase3TrackUpcomingPredictions(2026,10),/ownership/);assert.equal(writeCount,1);checks++;
 await assert.rejects(()=>context.window.phase3ReadOwnPredictionHistory(),/ownership/);checks++;
 active=true;mutateDuringPost=true;await assert.rejects(()=>context.window.phase3TrackUpcomingPredictions(2026,10),/Account changed/);checks++;
 await assert.rejects(()=>context.window.phase3TrackUpcomingPredictions(2026,0),/Invalid/);checks++;
 context.auth=null;assert.equal(await context.window.phase3ReadOwnPredictionHistory(),null);checks++;
 console.log(checks+' focused frontend checks passed (VM/mocked backend; not live RLS proof)');
})().catch(e=>{console.error(e);process.exitCode=1});
