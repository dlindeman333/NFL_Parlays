"""JSON-ready reporting contract for dashboard and workbook consumers."""
from phase3.comprehensive_reporting import summarize
from collections import defaultdict

def report_payload(picks, parlays):
    individual=[dict(category=c,market=m,**counts) for (c,m),counts in sorted(summarize(picks).items())]
    groups=defaultdict(lambda:dict(captured=0,hit=0,miss=0,pending=0))
    seen=set()
    for p in parlays:
        identity=p['snapshot_id']
        if identity in seen: raise ValueError('Duplicate suggested parlay')
        seen.add(identity)
        outcome=p.get('outcome')
        if outcome not in ('hit','miss',None,'pending'): raise ValueError('Unsupported parlay outcome')
        for key in [('all',0),(p['kind'],len(p['legs']))]:
            g=groups[key];g['captured']+=1;g[outcome or 'pending']+=1
    result=[]
    for (kind,count),g in sorted(groups.items()):
        n=g['hit']+g['miss']
        result.append(dict(kind=kind,leg_count=count,**g,graded_decisions=n,hit_rate=g['hit']/n if n else None))
    return dict(individual=individual,suggested_parlays=result,accuracy_threshold=.75,
                denominator='hit_plus_miss',all_eligible_is_model_accuracy=False)
