"""Review-only grading helpers. No network or database access."""
import math

def number(v):
    if isinstance(v,bool): return None
    try:
        n=float(v)
        return n if math.isfinite(n) else None
    except (ValueError,TypeError): return None

def grade_team(pick, *, away_team, home_team, away_score, home_score,
               completed=False, touchdowns=None):
    if not completed or away_team == home_team: return None
    a,h=number(away_score),number(home_score)
    if a is None or h is None or min(a,h)<0: return None
    market,side=pick.get('market'),pick.get('side')
    line=number(pick.get('line'))
    if market in ('ml','spread'):
        if side not in ('a','h'): return None
        margin=(a-h) if side=='a' else (h-a)
        if market=='ml': return ('hit' if margin>0 else 'miss', a if side=='a' else h)
        if line is None: return None
        # Contract: signed handicap for selected team, e.g. -3.5.
        return ('hit' if margin+line>0 else 'miss',margin)
    if side not in ('o','u') or line is None: return None
    if market=='total': actual=a+h
    elif market in ('team_total','team_touchdowns'):
        t=pick.get('team')
        if t not in (away_team,home_team): return None
        actual=(a if t==away_team else h) if market=='team_total' else number((touchdowns or {}).get(t))
    else: return None
    if actual is None or actual<0: return None
    return ('hit' if (actual>line if side=='o' else actual<line) else 'miss',actual)
