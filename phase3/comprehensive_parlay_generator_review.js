// Offline review adapter: invoke existing generator with canonical settings.
// Input pools must be injury-filtered, nonmanual, and have structured frozen legs.
({pools}) => {
 const old={mode, riskParlayFrom,riskParlayThrough,riskParlayHideBelowBreakEven};
 const output=[];
 try {
  riskParlayFrom='';riskParlayThrough='';riskParlayHideBelowBreakEven=false;
  for(const pool of pools){
   if(!['same','multi'].includes(pool.kind))throw Error('Invalid pool kind');
   mode=pool.kind;
   for(const count of [2,3,4]){
    const result=searchCombinedParlays(pool.rows,count,{aboveBreakEvenOnly:false});
    const seen=new Set();
    for(const category of ['best','lower','higher']){
     const candidate=result[category];
     if(!candidate||candidate.rows.length!==count)continue;
     const key=candidate.rows.map(r=>r.key).sort().join(';');
     if(seen.has(key))continue;seen.add(key);
     output.push({kind:pool.kind,category,count,keys:candidate.rows.map(r=>r.key),
       estimated_decimal:candidate.price,joint_probability:candidate.scenario.joint,
       correlated:candidate.scenario.correlated,settings:{odds:'unrestricted',aboveBreakEvenOnly:false}});
    }
   }
  }
  return output;
 } finally {
  mode=old.mode;riskParlayFrom=old.riskParlayFrom;riskParlayThrough=old.riskParlayThrough;
  riskParlayHideBelowBreakEven=old.riskParlayHideBelowBreakEven;
 }
}
