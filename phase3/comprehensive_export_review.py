"""Review-only export tables. No reconstructed historical predictions."""
from phase3.comprehensive_report_payload import report_payload

def export_tables(picks, parlays):
    picks=list(picks)
    parlays=list(parlays)
    report=report_payload(picks,parlays)
    legs=[]
    summaries=[]
    for p in parlays:
        identity=p['snapshot_id']
        summaries.append({k:v for k,v in p.items() if k!='legs'})
        for i,leg in enumerate(p['legs'],1):
            legs.append({**leg,'snapshot_id':identity,'leg_number':i})
    return {
        'AI Performance':report['individual'],
        'AI Prediction Details':[dict(p) for p in picks],
        'Suggested Performance':report['suggested_parlays'],
        'Suggested Parlays':summaries,
        'Suggested Legs':legs,
    }
