const fs=require('fs'),vm=require('vm'),assert=require('assert');
const html=fs.readFileSync(__dirname+'/../index.html','utf8');
let checks=0;
for(const match of html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/gi))new vm.Script(match[1]);
checks++;
// A schedule refresh does not refresh model baselines. Keep the selected week
// in the notice, flag other weeks as provisional, and never recycle Week 10
// games when the selected week's schedule has not loaded.
const potentialStart=html.indexOf('function potentialPlaysNotice(');
const potentialEnd=html.indexOf('\nfunction plays()',potentialStart);
assert(potentialStart>0&&potentialEnd>potentialStart,'Potential Plays notice must exist');
const potentialContext={};vm.createContext(potentialContext);
vm.runInContext(html.slice(potentialStart,potentialEnd),potentialContext);
const potentialNotice=(w,available=true,supported=true)=>vm.runInContext(`potentialPlaysNotice(${w},10,${available},${supported})`,potentialContext);
assert.match(potentialNotice(10).text,/Week 10 potential plays/);
assert.equal(potentialNotice(10).warning,false);
assert.match(potentialNotice(11).text,/Week 11 matchups/);
assert.match(potentialNotice(11).text,/NOT a verified Week 11 model refresh/);
assert.equal(potentialNotice(11).warning,true);
assert.match(potentialNotice(9).text,/Week 9 matchups/);
assert.match(potentialNotice(11,false).text,/no verified schedule loaded/);
assert.match(potentialNotice(11,true,false).text,/predictions are disabled/);
assert(html.includes("if(!hasSchedule){$(\"plays\").innerHTML="));
assert(html.includes("noticeEl.textContent=notice.text"));
assert(html.includes('href="./NFL_Parlay_Builder_User_Guide.pdf"'),'help links to the one current full guide');
assert(html.includes('href="./NFL_Parlay_Builder_Quick_Start_Guide.pdf"'),'quick-start help link retained');
assert(/function setWk\(w\)\{[^\n]*plays\(\)/.test(html),'week changes rerender Potential Plays notice');
assert(/if\(target===wk\)\{[^\n]*plays\(\)/.test(html),'schedule refresh rerenders Potential Plays notice');
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
const bridge=html.slice(html.indexOf('window.phase3AuthenticPregameSnapshot='),html.indexOf('\nsettings();auth=',html.indexOf('window.phase3TrackUpcomingPredictions=async')));
let active=true,writeCount=0,subscribed=true,archiveRecords;
const uid='00000000-0000-0000-0000-000000000001';
const snapshot={season:2026,week:10,game_id:'123',kickoff_at:'2099-01-01T00:00:00Z',created_at:'2098-12-31T23:28:00Z',away_team:'BUF',home_team:'MIA',picks:[{label:'BUF moneyline'}]};
archiveRecords=[snapshot];
let mutateDuringPost=false,subscriptionSnapshot=snapshot;
const context={window:{},auth:{},SEASON:2026,Date,Set,Map,Number,Array,Error,encodeURIComponent,userId:async()=>uid,safe6Active:id=>active&&id===uid,token:async()=>'mock',api:async(path,options={})=>{
 if(options.method==='POST'){
  assert(path.startsWith('/rest/v1/nfl_prediction_subscriptions_v2?'));
  assert.equal(options.headers.Authorization,'Bearer mock');
  const rows=JSON.parse(options.body);assert(rows.every(r=>r.user_id===uid));writeCount++;
  if(mutateDuringPost)active=false;return [];
 }
 if(path.includes('nfl_prediction_snapshots_v2?'))return archiveRecords;
 if(path.includes('nfl_prediction_grades_v2?'))return [{season:2026,week:10,game_id:'123',outcome:'hit'}];
 if(path.includes('nfl_prediction_subscriptions_v2?'))return subscribed?[{user_id:uid,season:2026,week:10,game_id:'123',tracked_at:'2098-12-31T23:28:00Z',nfl_prediction_snapshots_v2:subscriptionSnapshot}]:[];
 throw Error('Unexpected backend route');
}};
vm.createContext(context);vm.runInContext(bridge,context);
(async()=>{
 for(const [created,expected] of [['2098-12-31T23:25:00Z',true],['2098-12-31T23:30:00Z',true],['2098-12-31T23:24:59Z',false],['2098-12-31T23:30:01Z',false],['2099-01-01T00:00:00Z',false],['not-a-date',false]]){
  assert.equal(context.window.phase3AuthenticPregameSnapshot({...snapshot,created_at:created}),expected,created);
 }checks++;
 assert.equal(await context.window.phase3TrackUpcomingPredictions(2026,10),1);assert.equal(writeCount,1);checks++;
 const rows=await context.window.phase3ReadOwnPredictionHistory();assert(rows[0].payload.grade_summary.includes('1 hits'));assert.equal(rows[0].payload.picks[0].label,'BUF moneyline');checks++;
 assert.equal(rows.length,1);assert.equal(rows[0].archive_only,false);checks++;
 subscribed=false;
 const automatic=await context.window.phase3ReadOwnPredictionHistory();
 assert.equal(automatic.length,1);assert.equal(automatic[0].archive_only,true);
 assert.equal(automatic[0].payload.picks[0].label,'BUF moneyline');assert.equal(writeCount,1);checks++;
 const early={...snapshot,game_id:'early',created_at:'2098-12-31T23:24:59Z'};
 const late={...snapshot,game_id:'late',created_at:'2098-12-31T23:30:01Z'};
 archiveRecords=[early,late];subscriptionSnapshot=early;subscribed=true;
 assert.equal((await context.window.phase3ReadOwnPredictionHistory()).length,0);checks++;
 await assert.rejects(()=>context.window.phase3TrackUpcomingPredictions(2026,10),/No authentic/);assert.equal(writeCount,1);checks++;
 archiveRecords=[snapshot,early,late];
 assert.equal(await context.window.phase3TrackUpcomingPredictions(2026,10),1);assert.equal(writeCount,2);checks++;
 subscriptionSnapshot=late;
 assert.equal((await context.window.phase3ReadOwnPredictionHistory()).length,1);checks++;
 archiveRecords=[snapshot];subscriptionSnapshot=snapshot;subscribed=true;
 active=false;await assert.rejects(()=>context.window.phase3TrackUpcomingPredictions(2026,10),/ownership/);assert.equal(writeCount,2);checks++;
 await assert.rejects(()=>context.window.phase3ReadOwnPredictionHistory(),/ownership/);checks++;
 active=true;mutateDuringPost=true;await assert.rejects(()=>context.window.phase3TrackUpcomingPredictions(2026,10),/Account changed/);checks++;
 await assert.rejects(()=>context.window.phase3TrackUpcomingPredictions(2026,0),/Invalid/);checks++;
 context.auth=null;assert.equal(await context.window.phase3ReadOwnPredictionHistory(),null);checks++;
 const gradeMarker=html.indexOf('/* Official cloud grades: immutable snapshot-backed');
 const gradeScript=html.slice(html.lastIndexOf('<script>',gradeMarker)+8,html.indexOf('</script>',gradeMarker));
 const gradeCallbacks={};
 const gradeElements={seasonSelect:{value:'2026',addEventListener:()=>{}}};
 for(const name of ['cloudOfficialGradesStatus','cloudOfficialGradesResults','cloudOfficialGradesRefresh']){
  gradeElements[name]={textContent:'',innerHTML:'',disabled:false,addEventListener:(event,fn)=>{gradeCallbacks[name+':'+event]=fn}};
 }
 const gradeRows=[{season:2026,week:10,game_id:'123',pick_key:'v1:0:'+'a'.repeat(64),outcome:'hit',actual_value:24},
  {season:2026,week:10,game_id:'early',pick_key:'v1:0:'+'b'.repeat(64),outcome:'miss',actual_value:17}];
 let gradeArchive=[snapshot,early],gradeArchiveError=false,cloudWrites=0;
 const gradeContext={window:{phase3AuthenticPregameSnapshot:context.window.phase3AuthenticPregameSnapshot},
  document:{getElementById:id=>gradeElements[id]||null},
  fetch:async(url,options)=>{if(options.method&&options.method!=='GET')cloudWrites++;
   if(url.includes('nfl_prediction_snapshots_v2?')&&gradeArchiveError)return {ok:false,status:503};
   return {ok:true,json:async()=>url.includes('nfl_prediction_grades_v2?')?gradeRows:gradeArchive};}};
 vm.runInNewContext(gradeScript,gradeContext);
 await gradeCallbacks['cloudOfficialGradesRefresh:click']();
 assert.match(gradeElements.cloudOfficialGradesStatus.textContent,/1 eligible of 2 grade records/);
 assert.match(gradeElements.cloudOfficialGradesStatus.textContent,/1 excluded/);
 assert.match(gradeElements.cloudOfficialGradesResults.innerHTML,/1 \/ 0/);
 assert(!gradeElements.cloudOfficialGradesResults.innerHTML.includes('Week 10 · BUF @ MIA</b><span class="official-grade-result is-miss"'));
 assert.equal(cloudWrites,0);checks++;
 gradeArchiveError=true;
 await gradeCallbacks['cloudOfficialGradesRefresh:click']();
 assert.match(gradeElements.cloudOfficialGradesStatus.textContent,/provenance unavailable/);
 assert.match(gradeElements.cloudOfficialGradesResults.textContent,/No verified grading totals/);
 assert.equal(cloudWrites,0);checks++;
 console.log(checks+' focused frontend checks passed (VM/mocked backend; not live RLS proof)');
})().catch(e=>{console.error(e);process.exitCode=1});
