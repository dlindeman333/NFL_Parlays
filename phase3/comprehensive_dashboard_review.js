// Review-only dashboard renderer. Uses textContent for all report data.
function renderComprehensivePerformance(container, report) {
 const fragment=document.createDocumentFragment();
 const labels={top12:'Top 12 AI predictions',recommended:'All AI recommendations',all_eligible:'All eligible selections (not AI accuracy)'};
 const add=(label,row)=>{
  const card=document.createElement('section');
  card.className='card';
  const heading=document.createElement('h3');heading.textContent=label;card.append(heading);
  const rate=document.createElement('strong');
  const n=row?.graded_decisions||0;
  const p=row?.hit_rate;
  const valid=n>0&&Number.isFinite(p)&&p>=0&&p<=1;
  rate.textContent=valid?(p*100).toFixed(1)+'%':'Not yet graded';
  if(valid)rate.style.color=p>=.75?'#24975b':'#b58b16';
  card.append(rate);
  const details=document.createElement('p');
  details.textContent=(row?.hit||0)+' HIT · '+(row?.miss||0)+' MISS · '+(row?.pending||0)+' pending · '+(row?.push||0)+' push';
  card.append(details);fragment.append(card);
 };
 for(const [key,label] of Object.entries(labels))add(label,report.individual.find(r=>r.category===key&&r.market==='all'));
 add('Suggested parlays',report.suggested_parlays.find(r=>r.kind==='all'&&r.leg_count===0));
 container.replaceChildren(fragment);
}
