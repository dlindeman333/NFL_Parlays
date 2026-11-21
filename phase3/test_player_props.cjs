'use strict';
const assert=require('node:assert/strict'),vm=require('node:vm');
const {backtestPlayerProps,propSource}=require('./backtest_player_props.cjs');
let history=[];
const ctx={Math,Number,sourcePlayer:p=>p,nc:x=>1/(1+Math.exp(-1.702*x)),
 phase4PlayerHistory:()=>history,S:{BUF:{ppg:24}}};
vm.createContext(ctx);vm.runInContext(propSource,ctx);
const evaluate=(expression)=>vm.runInContext(expression,ctx);
const sample=Array.from({length:8},(_,index)=>({season:2026,week:10-index,player:'Test Receiver',team:'BUF',
 targets:7+(index%3),receptions:4+(index%4),receiving_yards:35+index*9,game_status:'COMPLETED'}));
history=sample;
const context=evaluate("propReceivingContext({n:'Test Receiver'})");
assert.equal(context.samples,8);
assert(context.catchRate>0&&context.catchRate<1);
assert(context.yardsPerCatch>0);
assert(context.dispersion>=2.5);
const reception=evaluate("propReceivingOver('rcp',5.5,4.5,propReceivingContext({n:'Test Receiver'}))");
const receptionHigh=evaluate("propReceivingOver('rcp',5.5,7.5,propReceivingContext({n:'Test Receiver'}))");
assert(reception>receptionHigh,'raising the reception threshold decreases its over chance');
const receivingYards=evaluate("propReceivingOver('rec',58,51.5,propReceivingContext({n:'Test Receiver'}))");
assert(receivingYards>0&&receivingYards<1);
const yardsWithBetterYpc=evaluate("propReceivingOver('rec',58,51.5,{yardsPerCatch:16,dispersion:10})");
const yardsWithWorseYpc=evaluate("propReceivingOver('rec',58,51.5,{yardsPerCatch:8,dispersion:10})");
assert(Math.abs(yardsWithBetterYpc-yardsWithWorseYpc)>.005,'yardage probability must depend on yards per catch, not merely on a generic normal curve');
const g={a:'BUF',h:'MIA',m:0,pp:{a:{pts:24},h:{pts:20}}};ctx.g=g;
const rec=evaluate("pstat({k:'rec',v:60,tm:'BUF',n:'Test Receiver'},g)");
const rcp=evaluate("pstat({k:'rcp',v:5.5,tm:'BUF',n:'Test Receiver'},g)");
for(const result of [rec,rcp]){assert(Number.isFinite(result.proj)&&Number.isFinite(result.p));assert(result.p>=.05&&result.p<=.95);}
assert.equal(rec.line,60.5);assert.equal(rcp.line,5.5);
const evidence=evaluate("propMarketOver('rcp',5.5,4.5,{n:'Test Receiver'})");
history=[];
const sparse=evaluate("propMarketOver('rcp',5.5,4.5,{n:'Test Receiver'})");
assert(Math.abs(sparse-.5)<Math.abs(evidence-.5),'no history must reduce confidence');
const fixtures=[];
for(let week=1;week<=15;week++)for(let id=0;id<6;id++){
 const catches=2+(week*3+id*5)%6,ypc=7+(id%3)*3;
 fixtures.push({season:2026,week,team:'BUF',player:'Receiver '+id,
  targets:catches+1+(week%2),receptions:catches,receiving_yards:catches*ypc+(week%3)*4,
  passing_yards:205+(week*17+id*6)%95,rushing_yards:25+(week*9+id*7)%50,
  touchdowns:(week+id)%4===0?1:0,
  game_status:'COMPLETED'});
}
const report=backtestPlayerProps(fixtures);
assert(report.receptions.evaluated>=60&&report.receivingYards.evaluated>=60);
assert(report.passingYards.evaluated>=60&&report.rushingYards.evaluated>=60);
assert(report.anytimeTD.evaluated>=50);
assert(report.receptions.brier>=0&&report.receptions.brier<=1);
assert(report.receivingYards.brier>=0&&report.receivingYards.brier<=1);
const augmented=[...fixtures,{...fixtures[0],week:99,receptions:200,receiving_yards:2000,targets:205}];
const earlier=backtestPlayerProps(fixtures,{includeDetails:true});
const later=backtestPlayerProps(augmented,{includeDetails:true});
for(const kind of ['rcp','rec']){
 assert.deepEqual(later.details[kind].filter(r=>r.week<99),earlier.details[kind],
  'adding future game data cannot change earlier-week predictions');
}
assert.throws(()=>backtestPlayerProps([fixtures[0],fixtures[0]]),/Duplicate player-week/);
console.log('Player prop distribution and synthetic walk-forward regression: passed; authentic calibration is evaluated separately with source provenance.');
