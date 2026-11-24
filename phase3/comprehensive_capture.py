"""Normalize capture rows without inventing lines or recommendations."""
from phase3.comprehensive_tracking import rank_predictions, finite

def prepare_capture(advanced, alternatives):
    # Advanced recommendations arrive in original model order.
    preferred=[]
    for row in advanced:
        if row.get('market')!='player' or row.get('manual') or row.get('excluded'):
            continue
        preferred.append(dict(row,recommended=True))
    ranked=rank_predictions(preferred)
    identities=lambda r:(r.get('market'),str(r.get('team') or '').upper(),
        str(r.get('player_name') or '').casefold(),r.get('stat'),r.get('side'),r.get('line'))
    original={identities(r):r for r in ranked}
    pool=list(ranked)
    for row in alternatives:
        if row.get('manual') or row.get('excluded'): continue
        if row.get('market')=='team_total' and row.get('line_verified') is not True: continue
        if row.get('market')=='spread' and row.get('line_convention')!='selected_team_signed': continue
        if identities(row) in original: continue
        probability=row.get('probability')
        recommended=(row.get('market')!='player' and row.get('model_preferred') is True
                     and finite(probability) and probability>.5
                     and row.get('probability_source')=='model')
        pool.append(dict(row,recommended=recommended))
    result=rank_predictions(pool)
    for row in result:
        row['legacy_player_top12']=original.get(identities(row),{}).get('legacy_player_top12',False)
    return result
