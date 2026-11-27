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
vm.runInContext(snippet('function advancedSelectionHit(','function advCard('),evCtx);
vm.runInContext(snippet('function advancedPickSide(','function advancedPickOdds('),evCtx);
const rank=vm.runInContext('rankAdvancedSelections',evCtx);
const suggest=vm.runInContext('advancedSuggestedLegs',evCtx);
const unpriced={p:{k:'rec'},g:{id:'a'},prob:.9,line:50.5,score:9};
const under={p:{k:'rec'},g:{id:'a'},prob:.3,line:50.5,manual:{side:'u'},odds:-180,score:9};
const touchdown={p:{k:'td'},g:{id:'b'},prob:.45,line:null,manual:{side:'o'},odds:200,score:1};
const push={...under,g:{id:'c'},line:50,odds:250};
assert.equal(rank([unpriced,under,touchdown,push],false)[0],unpriced);
const priced=rank([unpriced,under,touchdown,push],true);
assert.equal(priced.length,2,'unpriced picks and push lines have no comparable expected value');
assert.equal(priced[0],touchdown,'payout affects value ranking independently of hit probability');
assert.equal(priced[1],under,'manual Under value uses the complement of Over probability');
assert.equal(suggest([unpriced,under,touchdown]).length,2,'suggested legs use one displayed selection per game');
assert.equal(suggest([unpriced,under,touchdown])[0],unpriced);
assert(html.includes("manual.side==='u'"),'manual sportsbook selection retains under side');
assert(html.includes('id="advSide"'),'line editor labels the sportsbook side');
assert(html.includes('Selected line:')&&html.includes('Selection HIT probability vs. bet value'));
// Four comparison recommendations must be built regardless of the selected
// 2-8 leg filter; no UI operation here can mutate the active saved parlay.
// The comparison renderer now reads both the whole-parlay odds range and the
// optional model break-even filter. Keep the VM fixture aligned with that UI.
// Unbounded defaults let all mocked 3/4/5/6-leg combinations qualify.
const comparisonCtx={Math,Number,Map,Set,riskParlayLegs:2,riskParlayFrom:'',riskParlayThrough:'',riskParlayHideBelowBreakEven:false,
 filteredParlayCandidates:()=>[],filteredParlayContext:()=>'{"week":11}',
 parlayJointScenario:rows=>({joint:.2,independent:.18}),esc:s=>String(s),am:n=>'+'+Math.round((n-1)*100),
 searchCombinedParlays:(pool,count,options)=>{
  assert.equal(options.comparison,true);
  return {best:{rows:Array.from({length:count},(_,i)=>({text:'Leg '+i,matchup:'BUF @ MIA',odds:120,decimal:2.2,gid:'g'+i,probability:.6})),
   price:Math.pow(2.2,count),scenario:{joint:.2,independent:.18}}};
 }};
vm.createContext(comparisonCtx);
vm.runInContext(snippet('function oddsDecimal(','function applyOddsRange('),comparisonCtx);
vm.runInContext(snippet('let riskComparisonPlans={};','function renderRiskBasedParlays(){'),comparisonCtx);
const compareHtml=vm.runInContext('renderRiskComparisonParlays()',comparisonCtx);
assert.equal(vm.runInContext('riskParlayLegs',comparisonCtx),2);
assert(compareHtml.includes('Show all qualifying odds results'),'the optional break-even filter defaults to off');
for(const count of [3,4,5,6]){
 assert(compareHtml.includes('data-risk-comparison="'+count+'"'));
 assert.equal(vm.runInContext('riskComparisonPlans['+count+'].rows.length',comparisonCtx),count);
}
// The 3/4/5/6 comparison must honor the entire-parlay odds bounds even when
// a stale search result (such as a +174 six-leg plan) falls outside +500..+1500.
assert.equal(vm.runInContext("combinedOddsInRange(2.74,'+500','+1500')",comparisonCtx),false);
assert.equal(vm.runInContext("combinedOddsInRange(10,'+500','+1500')",comparisonCtx),true);
comparisonCtx.riskParlayFrom='+500';comparisonCtx.riskParlayThrough='+1500';
comparisonCtx.searchCombinedParlays=(pool,count)=>({best:{
 rows:Array.from({length:count},(_,i)=>({text:'Leg '+i,matchup:'BUF @ MIA',odds:120,decimal:2.2,gid:'g'+i,probability:.6})),
 price:count===6?2.74:10,scenario:{joint:.08,independent:.07}}});
const boundedHtml=vm.runInContext('renderRiskComparisonParlays()',comparisonCtx);
assert(boundedHtml.includes('Active whole-parlay odds range: +500 through +1500'));
assert(boundedHtml.includes('A candidate was rejected because its combined odds fell outside the active range'));
assert(!boundedHtml.includes('6-leg recommendation'),'the out-of-range six-leg result must not be recommended');
assert.equal(vm.runInContext('riskComparisonPlans[6]',comparisonCtx),undefined);
assert(boundedHtml.includes('data-risk-value="below-break-even"'),'below-break-even options need a visible warning');
comparisonCtx.riskParlayHideBelowBreakEven=true;
const filteredHtml=vm.runInContext('renderRiskComparisonParlays()',comparisonCtx);
assert(filteredHtml.includes('Experimental break-even filter ON'));
assert(filteredHtml.includes('candidate was hidden by the optional uncalibrated break-even filter'));
assert.equal(vm.runInContext('riskComparisonPlans[3]',comparisonCtx),undefined,'filtered-out plans are not loadable');
// A no-winner search may show explanatory examples, but never add-to-draft actions.
comparisonCtx.riskParlayFrom='+100';comparisonCtx.riskParlayThrough='+1500';
comparisonCtx.searchCombinedParlays=(pool,count)=>({best:null,groupCount:12,truncated:count===4,
 informationalBest:{rows:Array.from({length:count},(_,i)=>({text:'Under '+i,matchup:'BUF @ MIA',odds:-110,decimal:1.5,gid:'g'+i,probability:.3})),
 price:Math.pow(1.5,count),scenario:{joint:.02,independent:.02}}});
const infoHtml=vm.runInContext('renderRiskComparisonParlays()',comparisonCtx);
for(const count of [3,4,5,6])assert(infoHtml.includes('data-risk-comparison="'+count+'" data-risk-info-only="true"'),
 count+'-leg explanatory result must be informational only');
assert(!infoHtml.includes('Use 3-leg option in new draft'));
assert.equal(vm.runInContext('riskComparisonPlans[4]',comparisonCtx),undefined);
assert(html.includes('renderFilteredParlays()+renderRiskComparisonParlays()'),
 'best 3-6 leg suggestions must be below the chosen-leg recommendations');
console.log('Advanced parlay scenarios, defensive data guards, manual bet value, and under-side contracts passed (synthetic, read-only).');
