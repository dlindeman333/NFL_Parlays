"""Offline immutable suggested-parlay assembly; no publishing."""
from datetime import datetime, timedelta
from math import isfinite
from copy import deepcopy

def freeze_parlay(rows, *, kind, generated_at, settings, joint_probability, model_version):
    if kind not in ('same','multi') or len(rows)<2:
        raise ValueError('Invalid parlay type or leg count')
    if generated_at.tzinfo is None: raise ValueError('Timezone required')
    if not isinstance(joint_probability,(int,float)) or isinstance(joint_probability,bool) or not isfinite(joint_probability) or not 0<=joint_probability<=1:
        raise ValueError('Invalid joint probability')
    games=set(); markets=set(); kickoffs=[]; price=1.
    for row in rows:
        game=str(row['game_id'])
        market=(game,row['market'],row.get('team'),row.get('player_name'),row.get('stat'))
        if market in markets or (kind=='multi' and game in games):
            raise ValueError('Conflicting or duplicate market')
        markets.add(market); games.add(game)
        kickoff=datetime.fromisoformat(row['kickoff_at'].replace('Z','+00:00'))
        captured=datetime.fromisoformat(row['captured_at'].replace('Z','+00:00'))
        if captured>generated_at or captured>=kickoff or generated_at>=kickoff:
            raise ValueError('Invalid leg chronology')
        kickoffs.append(kickoff)
        odds=row['decimal']
        if isinstance(odds,bool) or not isinstance(odds,(int,float)) or not isfinite(odds) or odds<=1:
            raise ValueError('Invalid estimated price')
        price*=odds
    if kind=='same' and len(games)!=1: raise ValueError('Mixed games')
    if not timedelta(minutes=30)<=min(kickoffs)-generated_at<=timedelta(minutes=35):
        raise ValueError('Outside earliest kickoff capture window')
    if not isfinite(price): raise ValueError('Invalid combined price')
    return dict(kind=kind,generated_at=generated_at.isoformat(),settings=deepcopy(settings),
                model_version=model_version,legs=deepcopy(rows),estimated_combined_decimal=price,
                odds_source='model_estimate',joint_probability=joint_probability)
