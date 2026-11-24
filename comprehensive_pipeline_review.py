"""Offline integration entry point; deliberately no cloud publishing."""
from pathlib import Path
from comprehensive_snapshot_review import assemble_snapshot
from snapshot_predictions import select_top12

def capture_from_page(page,event,season,reports,now):
    source=Path(__file__).resolve().parent/'phase3'/'comprehensive_browser_extract.js'
    data=page.evaluate(source.read_text(encoding='utf-8'),event)
    normalized={**event,'a':data['away_team'],'h':data['home_team']}
    snapshot=assemble_snapshot(normalized,season,data['advanced'],data['alternatives'],reports,now)
    legacy=select_top12(data['advanced'],reports,event['week'])
    def key(p):
        return tuple(p.get(k) for k in ('team','player_name','stat','side','line','probability'))
    if [key(p) for p in legacy]!=[key(p) for p in snapshot['picks'] if p['legacy_player_top12']]:
        raise RuntimeError('Top 12 parity failure')
    return {'snapshot':snapshot,'unavailable_markets':data['unavailable_markets']}

def attach_suggestions(capture, generated, frozen_by_key, now):
    """Offline only; require exact generator legs and preserve original snapshot."""
    from copy import deepcopy
    from phase3.comprehensive_suggestion_bridge import assemble_suggestions
    result=deepcopy(capture)
    snapshot=result['snapshot']
    if snapshot['suggested_parlays']:
        raise ValueError('Suggestions already assembled')
    snapshot['suggested_parlays']=assemble_suggestions(
        generated,frozen_by_key,now,snapshot['model_version'])
    return result
