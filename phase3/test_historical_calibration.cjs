'use strict';
const assert=require('node:assert/strict'),vm=require('node:vm');
const {backtestPlayerProps,propSource}=require('./backtest_player_props.cjs');
const {evaluate,transform}=require('./evaluate_historical_calibration.cjs');
const fixtures=[];
for(let week=1;week<=12;week++)for(let id=0;id<12;id++){
 const receptions=(week+id)%5,targets=receptions+2;
 fixtures.push({season:2026,week,player_id:'gsis-'+id,player:'Person '+id,team:week<7?'BUF':'MIA',
  position:id<3?'QB':id<8?'WR':'RB',game_status:'COMPLETED',targets,receptions,
  receiving_yards:week%4===0?-2:receptions*11,passing_yards:id<3?180+week*7:0,
  rushing_yards:week%5===0?-3:20+week*4,touchdowns:week%3===0?1:0});
}
const earlier=backtestPlayerProps(fixtures.filter(x=>x.week<=9),{includeDetails:true});
const withFuture=backtestPlayerProps(fixtures,{includeDetails:true});
for(const market of ['rcp','rec','ps','ru','td']){
 assert.deepEqual(withFuture.details[market].filter(x=>x.week<=9),earlier.details[market],
  'later results must never change an earlier-week forecast');
}
const report=evaluate(fixtures.filter(x=>x.week<=9));
assert.equal(report.status,'historical_model_reconstruction_not_official_top12_grading');
assert(report.markets.receptions.all.favoredUnder.count>=0);
assert.equal(report.markets.passingYards.all.n,
 withFuture.details.ps.filter(x=>x.week<=9).length);
assert(Math.abs(transform(.3,0,1)-.3)<1e-10);
let history=[{receptions:2,receiving_yards:-4,targets:3,rushing_yards:-3,passing_yards:-2}];
const context={Math,Number,sourcePlayer:p=>p,phase4PlayerHistory:()=>history,
 phase4Clamp:(v,min,max)=>Math.max(min,Math.min(max,v)),S:{BUF:{ppg:21}}};
vm.createContext(context);vm.runInContext(propSource,context);
assert.equal(vm.runInContext("propReceivingContext({n:'Person'}).samples",context),1,
 'negative receiving yardage must not remove a completed game');
assert(Number.isFinite(vm.runInContext("propYardageOver('ru',32,31.5,{n:'Person'})",context)),
 'negative rushing yardage must not crash positive-yards distributions');
console.log('Historical calibration provenance, negative-yardage and no-lookahead contracts passed (synthetic).');
