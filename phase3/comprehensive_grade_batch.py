"""Offline grading batch; no publishing or network access."""
from .comprehensive_grading import grade_team, number
from .grade_contract import pick_key

def grade_snapshot(snapshot, final, player_grade, existing=()):
    if not final.get('completed'):
        return []
    if str(final.get('game_id')) != str(snapshot['game_id']):
        raise ValueError('Game identity mismatch')
    if (final.get('away_team'),final.get('home_team')) != (snapshot['away_team'],snapshot['home_team']):
        raise ValueError('Matchup mismatch')
    seen=set(existing)
    rows=[]
    for index,pick in enumerate(snapshot['picks']):
        key=pick_key(index,pick)
        if key in seen:
            continue
        if pick.get('market')=='player':
            result=player_grade(pick,snapshot,final)
        else:
            result=grade_team(pick,away_team=final['away_team'],home_team=final['home_team'],
                away_score=final.get('away_score'),home_score=final.get('home_score'),
                completed=True,touchdowns=final.get('touchdowns'))
        if result is None:
            continue
        status,actual=result
        if status not in ('hit','miss') or number(actual) is None:
            raise ValueError('Invalid grade')
        rows.append(dict(pick_key=key,result=status,actual=actual))
    return rows
