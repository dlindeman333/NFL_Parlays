// Read-only reporting UI. The existing account transport owns authentication.
(function(){
 const panel=document.getElementById('comprehensiveCloudPanel');
 const scope=document.getElementById('comprehensiveCloudScope');
 const status=document.getElementById('comprehensiveCloudStatus');
 const report=document.getElementById('comprehensiveCloudReport');
 const refresh=document.getElementById('comprehensiveCloudRefresh');
 const exportButton=document.getElementById('comprehensiveCloudExport');
 let generation=0;
 function reset(){
  generation++;
  report.replaceChildren();
  exportButton.disabled=true;
  exportButton.onclick=null;
 }
 async function load(){
  reset();
  const current=generation, season=Number(SEASON), week=scope.value==='season'?0:Number(wk);
  const label=week?'Week '+week:'Season '+season;
  status.textContent='Loading '+label+'…';
  try{
   const row=await window.phase3ReadComprehensiveReport(season,week);
   if(current!==generation)return;
   if(row===null){status.textContent='Sign in to view comprehensive AI prediction history.';return;}
   if(!row.length){status.textContent='No authenticated V4 captures available for '+label+'.';return;}
   const [record]=row;
   if(record.season!==season||record.week!==week)throw Error('Cloud report scope mismatch');
   const sheets=mountComprehensiveReview(report,record.bundle,[]);
   appendDetails(report,record.bundle.workbook_tables);
   exportButton.onclick=()=>downloadFile(makeXlsx(sheets,{styled:true}),
    'NFL_AI_Predictions_'+season+(week?'_Week_'+week:'')+'.xlsx');
   exportButton.disabled=false;
   status.textContent=label+' · Cloud report updated '+new Date(record.generated_at).toLocaleString();
  }catch(error){
   if(current===generation)status.textContent='Cloud report unavailable. '+error.message;
  }
 }
 function appendDetails(container,tables){
  const tally=r=>[r.hit+' HIT',r.miss+' MISS',r.pending+' pending',
   r.hit_rate===null?'No graded decisions':(r.hit_rate*100).toFixed(1)+'%'].join(' · ');
  for(const [name,rows,describe] of [
   ['Market breakdown',tables['AI Performance']?.filter(r=>r.market!=='all'),r=>[
     ({top12:'Top 12',recommended:'Recommendations',all_eligible:'All eligible'})[r.category],
     r.market.replace(/^market:/,'').replaceAll('_',' '), tally(r)]],
   ['Suggested parlay breakdown',tables['Suggested Performance']?.filter(r=>r.kind!=='all'),r=>[
     r.kind==='same'?'Same game':'Multiple games',r.leg_count+' legs',tally(r)]],
   ['Individual predictions',tables['AI Prediction Details'],r=>[
     'Week '+r.week,r.away_team&&r.home_team?r.away_team+' @ '+r.home_team:r.game_id,
     r.label||[r.team,r.market,r.side,r.line].filter(v=>v!=null).join(' '),r.outcome?.toUpperCase(),'Actual '+(r.actual_value??'—')]],
   ['Suggested parlays',tables['Suggested Parlays'],r=>[
     'Week '+r.week,r.kind==='same'?'Same game':'Multiple games',r.category,r.outcome?.toUpperCase(),r.snapshot_id]],
   ['Suggested parlay legs',tables['Suggested Legs'],r=>[
     r.snapshot_id,'Leg '+r.leg_number,r.leg?.label||[r.leg?.team,r.leg?.market,r.leg?.side,r.leg?.line].filter(v=>v!=null).join(' '),
     r.outcome?.toUpperCase(),'Actual '+(r.actual_value??'—')]]
  ]){
   if(!rows?.length)continue;
   const section=document.createElement('details');
   const title=document.createElement('summary');
   title.textContent=name+' ('+rows.length+')';section.append(title);
   const list=document.createElement('ul');section.append(list);
   const more=document.createElement('button');more.type='button';more.className='btn alt';
   more.textContent='Show 50 more';section.append(more);
   let offset=0;
   function append(){
    for(const row of rows.slice(offset,offset+50)){
     const li=document.createElement('li');li.textContent=describe(row).filter(Boolean).join(' · ');list.append(li);
    }
    offset+=50;more.hidden=offset>=rows.length;
   }
   section.addEventListener('toggle',()=>{if(section.open&&!offset)append();});
   more.onclick=append;container.append(section);
  }
 }
 refresh.onclick=load;
 scope.onchange=load;
 panel.addEventListener('toggle',()=>{if(panel.open)load();});
 for(const id of ['wkTop','wk']){
  document.getElementById(id)?.addEventListener('change',()=>{if(panel.open&&scope.value==='week')load();});
 }
 document.addEventListener('phase3-account-verified',()=>{if(panel.open)load();});
 document.addEventListener('phase3-account-signed-out',()=>{reset();status.textContent='Sign in to view comprehensive AI prediction history.';});
})();
