"""Pure helpers for comprehensive capture; not wired into production automation."""
import math

PLAYER_STATS = frozenset(('passing_yards','rushing_yards','receiving_yards','receptions','touchdowns'))
TEAM_MARKETS = frozenset(('ml','spread','total','team_total','team_touchdowns'))

def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def rank_predictions(candidates):
    """Preserve supplied model ordering; distinguish legacy player Top 12."""
    result, seen = [], set()
    player_rank = 0
    for pick in candidates:
        market = pick.get('market')
        if not finite(pick.get('probability')) or not 0 <= pick['probability'] <= 1:
            continue
        if market == 'player':
            if pick.get('stat') not in PLAYER_STATS or not str(pick.get('player_name') or '').strip():
                continue
        elif market not in TEAM_MARKETS:
            continue
        if pick.get('side') not in (('a','h') if market in ('ml','spread') else ('o','u')):
            continue
        if market != 'ml' and not finite(pick.get('line')):
            continue
        if market in ('player','team_total','team_touchdowns') and not str(pick.get('team') or '').strip():
            continue
        identity = (market, str(pick.get('team') or '').upper(), str(pick.get('player_name') or '').casefold(),
                    pick.get('stat'), pick.get('side'), pick.get('line'))
        if identity in seen:
            continue
        seen.add(identity)
        if market == 'player':
            player_rank += 1
        result.append({**pick, 'capture_rank': len(result)+1,
                       'legacy_player_top12': market == 'player' and player_rank <= 12})
    return result

def grade_parlay(outcomes):
    """Only settle when every frozen leg has a supported final outcome."""
    if not outcomes or any(x not in ('hit','miss') for x in outcomes):
        return None
    return 'hit' if all(x == 'hit' for x in outcomes) else 'miss'
