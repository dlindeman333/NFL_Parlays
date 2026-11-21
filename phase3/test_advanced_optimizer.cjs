'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const html=fs.readFileSync(__dirname+'/../index.html','utf8');
const snippet=(start,end)=>{
 const a=html.indexOf(start),b=html.indexOf(end,a);
 assert(a>=0&&b>a,`Cannot locate ${start} / ${end}`);return html.slice(a,b);
};
const ctx={Math,Number,Map,Set,phase4Clamp:(n,a,b)=>Math.max(a,Math.min(b,n))};
vm.createContext(ctx);
vm.runInContext(snippet('function propNormalCdf(','function propReceivingContext('),ctx);
vm.runInContext(snippet('function parlayRiskLoadings(','function searchCombinedParlays('),ctx);
const estimate=vm.runInContext('parlayJointScenario',ctx);
const pick=(gid,side='o',market='rec',team='BUF',p=.64)=>({gid,away:'BUF',home:'MIA',mkt:'p01',side,
  player:{tm:team,k:market},probability:p});
const correlated=estimate([pick('a'),pick('a')]);
assert(correlated.correlated);
assert(correlated.joint>correlated.independent,'same-game aligned overs share positive scenario exposure');
assert(correlated.joint<.64,'joint outcomes cannot exceed either marginal');
const opposing=estimate([pick('a'),pick('a','u')]);
assert(opposing.joint<opposing.independent,'opposite exposure decreases joint hit estimate');
const separate=estimate([pick('a'),pick('b')]);
assert.equal(separate.correlated,false);
assert(Math.abs(separate.joint-.64**2)<1e-12,'different games have no invented correlation');
const ml=estimate([{gid:'a',mkt:'ml',side:'h',probability:.60,home:'MIA',away:'BUF'},
 {gid:'a',mkt:'tot',side:'u',probability:.65,home:'MIA',away:'BUF'}]);
assert(ml.joint>0&&ml.joint<1);
// A scheduled matchup can use verified exported defensive yardage; its rank
// is relative to actual scheduled opponents, never filled with invented data.
const teams=['BUF','MIA','NYJ','NE','KC','DEN','LV','LAC','ATL','CAR','NO','TB','PIT','BAL','CLE','CIN'];
ctx.SEASON=2026;ctx.wk=11;ctx.S={MIA:{opp:23.5}};
ctx.normalizeTeam=s=>s;
ctx.advAvg=values=>values.reduce((sum,x)=>sum+x,0)/values.length;
ctx.imported=teams.map((team,i)=>({season:2026,week:11,game_status:'SCHEDULED',team:team==='MIA'?'BUF':'ANY',opponent:team,
 opp_pass_yds_allowed_pg:team==='MIA'?250:180+i*3,opp_rush_yds_allowed_pg:110+i*3}));
vm.runInContext(snippet('function phase4OpponentDefense(','function advMetrics('),ctx);
const defense=vm.runInContext('phase4OpponentDefense',ctx);
const game={a:'BUF',h:'MIA'};
const pass=defense({tm:'BUF',k:'ps'},game),receptions=defense({tm:'BUF',k:'rcp'},game);
assert(pass.verified&&pass.factor>1);
assert(receptions.verified&&receptions.factor>1&&receptions.factor<pass.factor);
ctx.imported=[];
assert.equal(defense({tm:'BUF',k:'ps'},game).verified,false,'no imputed positional strength');
assert(html.includes("opp_pass_yds_allowed_pg:['opp_pass_yds_allowed_pg']"));
assert(html.includes("opp_rush_yds_allowed_pg:['opp_rush_yds_allowed_pg']"));
assert(html.includes("rz_targets_10:['rz_targets_10']"));
assert(html.includes("rz_rush_10:['rz_rush_10']"));
const evCtx={oddsDecimal:v=>v>0?1+v/100:1+100/Math.abs(v),Number};
vm.createContext(evCtx);
vm.runInContext(snippet('function phase4ExpectedValue(','function advAdd('),evCtx);
const ev=vm.runInContext('phase4ExpectedValue',evCtx);
assert(Math.abs(ev(.6,100)-.2)<1e-12);
assert(Math.abs(ev(.5,-110)-(-.04545454545454547))<1e-10);
assert(html.includes("manual.side==='u'"),'manual sportsbook selection retains under side');
assert(html.includes('id="advSide"'),'line editor labels the sportsbook side');
assert(html.includes('Selected line:')&&html.includes('Selection HIT probability vs. bet value'));
// Four comparison recommendations must be built regardless of the selected
// 2-8 leg filter; no UI operation here can mutate the active saved parlay.
const comparisonCtx={Math,Number,Map,Set,riskParlayLegs:2,riskParlayFrom:'+500',riskParlayThrough:'+2000',
 filteredParlayCandidates:()=>[],filteredParlayContext:()=>'{"week":11}',
 parlayJointScenario:rows=>({joint:.2,independent:.18}),esc:s=>String(s),am:n=>'+'+Math.round((n-1)*100),
 searchCombinedParlays:(pool,count,options)=>{
  assert.equal(options.comparison,true);
  return {best:{rows:Array.from({length:count},(_,i)=>({text:'Leg '+i,matchup:'BUF @ MIA',odds:120,decimal:2.2,gid:'g'+i,probability:.6})),
   price:Math.pow(2.2,count),scenario:{joint:.2,independent:.18}}};
 }};
vm.createContext(comparisonCtx);
vm.runInContext(snippet('let riskComparisonPlans={};','function renderRiskBasedParlays(){'),comparisonCtx);
const compareHtml=vm.runInContext('renderRiskComparisonParlays()',comparisonCtx);
assert.equal(vm.runInContext('riskParlayLegs',comparisonCtx),2);
for(const count of [3,4,5,6]){
 assert(compareHtml.includes('data-risk-comparison="'+count+'"'));
 assert.equal(vm.runInContext('riskComparisonPlans['+count+'].rows.length',comparisonCtx),count);
}
assert(html.includes('renderFilteredParlays()+renderRiskComparisonParlays()'),
 'best 3-6 leg suggestions must be below the chosen-leg recommendations');
console.log('Advanced parlay scenarios, defensive data guards, manual bet value, and under-side contracts passed (synthetic, read-only).');
