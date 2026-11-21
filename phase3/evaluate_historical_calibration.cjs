// Read-only historical scoring and exploratory train/holdout calibration.
// No saved calibration coefficients enter production automatically.
// The observations are MODEL-RECONSTRUCTED using earlier weeks, NOT actual
// archived Top 12 picks and NOT sportsbook lines or prices.
'use strict';
const fs=require('node:fs');
const {backtestPlayerProps}=require('./backtest_player_props.cjs');
const MARKETS={rcp:'receptions',rec:'receivingYards',ps:'passingYards',ru:'rushingYards',td:'anytimeTD'};
const round=(n,d=5)=>Number(n.toFixed(d));
const safe=p=>Math.max(.001,Math.min(.999,p));
const transform=(p,intercept,slope)=>1/(1+Math.exp(-(intercept+slope*Math.log(safe(p)/(1-safe(p))))));
const brier=(observations,fn=x=>x.probability)=>observations.reduce((s,x)=>s+(fn(x)-x.outcome)**2,0)/observations.length;
const logLoss=(observations,fn=x=>x.probability)=>observations.reduce((s,x)=>{
 const p=safe(fn(x));return s-(x.outcome?Math.log(p):Math.log(1-p));
},0)/observations.length;
const metrics=(observations,fn=x=>x.probability)=>{
 if(!observations.length)return {n:0,note:'No observations'};
 const sum=selector=>observations.reduce((s,x)=>s+selector(x),0);
 const over=observations.filter(x=>fn(x)>=.5),under=observations.filter(x=>fn(x)<.5);
 return {n:observations.length,brier:round(brier(observations,fn)),logLoss:round(logLoss(observations,fn)),
  meanOverProbability:round(sum(fn)/observations.length,3),actualOverRate:round(sum(x=>x.outcome)/observations.length,3),
  favoredOver:{count:over.length,hits:over.reduce((s,x)=>s+x.outcome,0),hitRate:over.length?round(over.reduce((s,x)=>s+x.outcome,0)/over.length,3):null},
  favoredUnder:{count:under.length,hits:under.reduce((s,x)=>s+(1-x.outcome),0),hitRate:under.length?round(under.reduce((s,x)=>s+(1-x.outcome),0)/under.length,3):null}};
};
function evaluate(input,{calibrationEndWeek=7,holdoutStartWeek=8}={}){
 if(holdoutStartWeek<=calibrationEndWeek)throw Error('Training and holdout weeks overlap');
 const backtest=backtestPlayerProps(input,{minimumPastGames:4,includeDetails:true}),markets={};
 for(const [key,label] of Object.entries(MARKETS)){
  const rows=backtest.details[key],train=rows.filter(r=>r.week<=calibrationEndWeek),holdout=rows.filter(r=>r.week>=holdoutStartWeek);
  let exploratory=null;
  if(train.length>=40&&holdout.length>=30){
   let candidate={intercept:0,slope:1,score:Infinity};
   for(let i=-6;i<=6;i++)for(const slope of [.6,.8,1,1.2]){
    const intercept=round(i*.1,1),score=brier(train,x=>transform(x.probability,intercept,slope));
    // Small sample regularization: do not overfit near-identical candidates.
    const penalized=score+.0005*(Math.abs(intercept)+Math.abs(slope-1));
    if(penalized<candidate.score)candidate={intercept,slope,score:penalized};
   }
   const adjusted=x=>transform(x.probability,candidate.intercept,candidate.slope);
   exploratory={trainingWindow:`weeks <=${calibrationEndWeek}`,holdoutWindow:`weeks >=${holdoutStartWeek}`,
    intercept:candidate.intercept,slope:candidate.slope,train:metrics(train,adjusted),holdout:metrics(holdout,adjusted),
    holdoutBrierGain:round(brier(holdout)-brier(holdout,adjusted)),
    decision:'Exploratory only; do not activate without independent repeat-season/sportsbook-line verification'};
  }
  markets[label]={all:metrics(rows),training:metrics(train),holdout:metrics(holdout),exploratory};
 }
 return {status:'historical_model_reconstruction_not_official_top12_grading',
  method:'2026 player-game results, every forecast uses strictly earlier same-season games; derived half-point thresholds',
  trainHoldout:`Training completed Weeks 5-${calibrationEndWeek}; holdout Weeks ${holdoutStartWeek}-9; player sample minimum 4 prior games`,
  limitations:['Source is third-party archived snapshot attributed to nflverse; independent primary-release comparison outstanding',
   'Cannot infer profitable betting or actual Top 12 prediction performance from reconstructed forecasts',
   'Model-derived thresholds are not recorded sportsbook lines; no bet prices or vig',
   'Market observations are repeated by player and week; no independent standard-error claim',
   'No correlation coefficients or probability recalibration applied to production from this analysis'],
  inputRows:backtest.inputRows,validRows:backtest.validRows,markets};
}
if(require.main===module){
 const get=flag=>{const i=process.argv.indexOf(flag);return i>=0?process.argv[i+1]:null;};
 const file=get('--file'),output=get('--out');
 if(!file){console.error('Usage: node phase3/evaluate_historical_calibration.cjs --file completed-player-weeks.json [--out report.json]');process.exitCode=2;}
 else try{const report=JSON.stringify(evaluate(JSON.parse(fs.readFileSync(file,'utf8'))),null,2)+'\n';
  if(output)fs.writeFileSync(output,report);else process.stdout.write(report);
 }catch(e){console.error('Calibration evaluation failed:',e.message);process.exitCode=1;}
}
module.exports={evaluate,transform,metrics};
