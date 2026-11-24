// Review-only Playwright evaluation function. Not loaded by production index.html.
(e) => {
  const a=normalizeTeam(e.a), h=normalizeTeam(e.h);
  if (!T[a] || !T[h] || a===h) throw Error('Invalid matchup');
  const g=build([['espn'+e.id,a,h,'Scheduled',null]])[0];
  const stats={ps:'passing_yards',ru:'rushing_yards',rec:'receiving_yards',rcp:'receptions',td:'touchdowns'};
  const advanced=[], alternatives=[];
  for(const x of window.phase4Top12GameCandidates(g)){
    const p=x.p, stat=stats[p.k], line=p.k==='td'?0.5:Number(x.line);
    if(!stat || !Number.isFinite(line) || !Number.isFinite(x.prob)) continue;
    const side=advancedPickSide(x);
    const row={market:'player',team:p.tm,player_name:p.n,stat,line,
      model_line:x.line,away_team:a,home_team:h,probability_source:'model',
      projection:Number.isFinite(x.projection)?x.projection:null};
    const make=s=>({...row,side:s,probability:s==='u'?1-x.prob:x.prob,
      label:p.n+' '+(s==='u'?'Under ':'Over ')+line+' '+stat});
    advanced.push(make(side));
    if(p.k!=='td') alternatives.push(make(side==='o'?'u':'o'));
  }
  for(const side of ['a','h']){
    const probability=side==='h'?g.p:1-g.p;
    alternatives.push({market:'ml',side,team:side==='a'?a:h,probability,
      probability_source:'model',model_preferred:probability>.5,line:null});
    if(Number.isFinite(g.sp)) alternatives.push({market:'spread',side,
      team:side==='a'?a:h,line:side==='h'?-g.sp:g.sp,
      line_convention:'selected_team_signed',probability:.5,probability_source:'placeholder'});
  }
  if(Number.isFinite(g.tot)) for(const side of ['o','u'])
    alternatives.push({market:'total',side,line:g.tot,probability:.5,probability_source:'placeholder'});
  for(const t of ['a','h']){
    const line=PN.td[1], over=g.pp?.[t]?.tdp;
    if(Number.isFinite(line)&&Number.isFinite(over)&&over>0&&over<1)
      for(const side of ['o','u']) alternatives.push({market:'team_touchdowns',
        team:t==='a'?a:h,side,line,probability:side==='o'?over:1-over,
        probability_source:'model',model_preferred:false,line_source:'model_default'});
  }
  return {away_team:a,home_team:h,advanced,alternatives,
    unavailable_markets:['team_total'],
    unavailable_reason:'Team points lines are device-entered; no automated verified source'};
}
