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
