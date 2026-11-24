// Adapt frozen prediction lines to the existing suggestion generator.
(snapshots) => {
 const statCodes={passing_yards:'ps',rushing_yards:'ru',receiving_yards:'rec',
  receptions:'rcp',touchdowns:'td'};
 return snapshots.map(snapshot=>snapshot.picks.flatMap((pick,index)=>{
  const {market,team,side,probability:prob}=pick;
  if(!(prob>0&&prob<1))return [];
  const {game_id:gid,away_team:away,home_team:home}=snapshot;
  const t=team===away?'a':'h';
  const player=market==='player'?{tm:team,k:statCodes[pick.stat]}:null;
  const mkt=player?['player',team,pick.player_name,pick.stat].join('|'):
   ({ml:'ml',spread:'sp',total:'tot',team_touchdowns:'td'+t,team_total:'teamtot'+t})[market];
  const decimal=pick.probability_source==='placeholder'?1.91:oddsDecimal(Number(am(dec(prob))));
  if(!mkt||!Number.isFinite(decimal)||decimal<=1)return [];
  return [{key:gid+':'+index,gid,mkt,side,probability:prob,decimal,player,away,home}];
 }));
}
