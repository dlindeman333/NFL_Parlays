// Review-only workbook adapter. Input must already be authenticated and week-scoped.
function comprehensiveWorkbookSheets(existing, tables) {
 const names=new Set(existing.map(s=>s[0].toLowerCase()));
 const out=existing.slice();
 for(const [name,rows] of Object.entries(tables)){
  const title=('V4 '+name).slice(0,31);
  if(names.has(title.toLowerCase()))throw Error('Duplicate workbook sheet: '+title);
  if(!Array.isArray(rows))throw Error('Invalid report rows');
  const columns=[...new Set(rows.flatMap(r=>Object.keys(r)))];
  const cell=v=>v==null?'':typeof v==='object'?JSON.stringify(v):typeof v==='boolean'?String(v):v;
  out.push([title,columns.length?[columns,...rows.map(r=>columns.map(k=>cell(r[k])))]:[['No authentic captured records in selected scope']]]);
  names.add(title.toLowerCase());
 }
 return out;
}
