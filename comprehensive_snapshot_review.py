"""Offline v4 snapshot assembly. No credentials, network or database writes."""
from datetime import datetime
from phase3.comprehensive_capture import prepare_capture
from snapshot_predictions import within_capture_window, select_top12

def assemble_snapshot(event, season, advanced, alternatives, reports, now):
    kickoff=datetime.fromisoformat(event['kickoff'].replace('Z','+00:00'))
    if not within_capture_window(kickoff,now):
        raise ValueError('Outside authentic pregame window')
    if not isinstance(reports,list):
        raise ValueError('Injury reports unavailable')
    # Reuse legacy eligibility for every player candidate without altering v3.
    def eligible(rows):
        result=[]
        for row in rows:
            if row.get('market')=='player':
                result.extend(select_top12([row],reports,event['week']))
            else:
                result.append(row)
        return result
    preferred=eligible(advanced)
    picks=prepare_capture(preferred,eligible(alternatives))
    if sum(p['legacy_player_top12'] for p in picks)!=12:
        raise ValueError('Legacy Top 12 coverage incomplete')
    if not event.get('a') or not event.get('h') or event['a']==event['h']:
        raise ValueError('Invalid matchup')
    return dict(season=season,week=event['week'],game_id=str(event['id']),
                away_team=event['a'],home_team=event['h'],kickoff_at=event['kickoff'],
                model_version='browser-model-2026-comprehensive-review-v1',
                picks=picks,suggested_parlays=[])

# Server must generate created_at. This module deliberately has no publish path.
