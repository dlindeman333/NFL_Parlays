// Optional, read-only walk-forward backtest of the SAME browser player-prop math.
// Usage: node phase3/backtest_player_props.cjs --file completed-player-logs.json
// Input: array of completed NFL player-week rows, with season, week, player,
// team, game_status=COMPLETED and available passing_yards, rushing_yards,
// receptions, receiving_yards, targets, and/or touchdowns.
// No live feeds, cloud writes, sportsbook lines, or fabricated historical data.
'use strict';
const fs=require('fs'),path=require('path'),vm=require('vm');
const html=fs.readFileSync(path.join(__dirname,'../index.html'),'utf8');
const start=html.indexOf('function propNormalCdf('),end=html.indexOf('// Device-local, game-specific',start);
if(start<0||end<start)throw Error('Shared prop probability functions not found in index.html');
const propSource=html.slice(start,end);
const identity=s=>String(s||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase().replace(/\b(jr|sr|ii|iii|iv)\b/g,'').replace(/[^a-z0-9]/g,'');
function testHistory(row){
 return row&&Number.isInteger(Number(row.season))&&Number.isInteger(Number(row.week))&&Number(row.week)>0&&
  row.player&&row.team&&row.game_status==='COMPLETED'&&
  ['targets','receptions','receiving_yards','passing_yards','rushing_yards','touchdowns'].some(k=>typeof row[k]==='number'&&Number.isFinite(row[k])&&row[k]>=0)&&
  (!Number.isFinite(row.targets)||!Number.isFinite(row.receptions)||row.targets>=row.receptions);
}
function backtestPlayerProps(input,{minimumPastGames=4,includeDetails=false}={}){
 if(!Array.isArray(input))throw Error('Expected an array of completed NFL player-week stats');
 const rows=input.filter(testHistory);
 const seen=new Set();
 for(const row of rows){const key=[row.season,row.week,identity(row.player)].join('|');if(seen.has(key))throw Error('Duplicate player-week: '+key);seen.add(key);}
 rows.sort((a,b)=>Number(a.season)-Number(b.season)||Number(a.week)-Number(b.week)||identity(a.player).localeCompare(identity(b.player)));
 let past=[];
 const sandbox={Math,Number,sourcePlayer:p=>p,nc:x=>1/(1+Math.exp(-1.702*x)),
  phase4Clamp:(value,min,max)=>Math.max(min,Math.min(max,value)),
  phase4PlayerHistory:()=>past,S:{TEAM:{ppg:21}}};
 vm.createContext(sandbox);vm.runInContext(propSource,sandbox);
 const observations={rcp:[],rec:[],ps:[],ru:[],td:[]};
 for(const row of rows){
  const playerId=identity(row.player);
  past=rows.filter(r=>Number(r.season)===Number(row.season)&&Number(r.week)<Number(row.week)&&identity(r.player)===playerId)
   .sort((a,b)=>Number(b.week)-Number(a.week));
  if(past.length<minimumPastGames)continue;
  const g={a:'TEAM',h:'OTHER',m:0,pp:{a:{pts:21},h:{pts:21}}};
  for(const [kind,field] of [['rcp','receptions'],['rec','receiving_yards'],['ps','passing_yards'],['ru','rushing_yards'],['td','touchdowns']]){
   const available=past.slice(0,8).map(r=>r[field]).filter(v=>Number.isFinite(v)&&v>=0);
   if(available.length<minimumPastGames||!Number.isFinite(row[field])||row[field]<0)continue;
   const mean=available.reduce((s,v)=>s+v,0)/available.length;
   if(!(mean>0))continue;
   const p={n:row.player,tm:'TEAM',k:kind,v:mean};
   const result=vm.runInContext('pstat',sandbox)(p,g);
   if(!result||!Number.isFinite(result.p))continue;
   const threshold=kind==='td'?.5:result.line;
   const outcome=Number(row[field])>threshold?1:0;
   observations[kind].push({season:row.season,week:row.week,probability:result.p,outcome,line:threshold,actual:row[field]});
  }
 }
 const summarize=list=>{
  const n=list.length;
  if(!n)return {evaluated:0,note:'No eligible held-out player-weeks'};
  const avg=fn=>list.reduce((sum,x)=>sum+fn(x),0)/n;
  const bins=Array.from({length:5},(_,i)=>{
   const selected=list.filter(x=>Math.min(4,Math.floor(x.probability*5))===i);
   return {range:`${(i*20)}-${(i+1)*20}%`,n:selected.length,
    predicted:selected.length?selected.reduce((s,x)=>s+x.probability,0)/selected.length:null,
    observed:selected.length?selected.reduce((s,x)=>s+x.outcome,0)/selected.length:null};
  });
  return {evaluated:n,brier:Number(avg(x=>(x.probability-x.outcome)**2).toFixed(5)),
   overForecastRate:Number(avg(x=>x.probability>=.5?1:0).toFixed(3)),
   observedOverRate:Number(avg(x=>x.outcome).toFixed(3)),
   meanForecast:Number(avg(x=>x.probability).toFixed(3)),
   calibrationGap:Number((bins.reduce((s,b)=>s+b.n*Math.abs((b.predicted??0)-(b.observed??0)),0)/n).toFixed(3)),bins};
 };
 return {method:'strict earlier-week walk-forward; model-derived half-point thresholds; no sportsbook odds',
  source:'user-supplied completed player-week stats only',inputRows:input.length,validRows:rows.length,
  minimumPastGames,receptions:summarize(observations.rcp),receivingYards:summarize(observations.rec),
  passingYards:summarize(observations.ps),rushingYards:summarize(observations.ru),anytimeTD:summarize(observations.td),
  ...(includeDetails?{details:observations}:{})};
}
if(require.main===module){
 const filename=process.argv[2]==='--file'?process.argv[3]:null;
 if(!filename){console.error('Usage: node phase3/backtest_player_props.cjs --file completed-player-logs.json');process.exitCode=2;}
 else try{console.log(JSON.stringify(backtestPlayerProps(JSON.parse(fs.readFileSync(filename,'utf8'))),null,2));}
 catch(e){console.error('Backtest failed:',e.message);process.exitCode=1;}
}
module.exports={backtestPlayerProps,propSource};
