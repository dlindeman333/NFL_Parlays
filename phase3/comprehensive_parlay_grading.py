"""Offline suggested-parlay settlement using exact frozen leg identities."""
from .grade_contract import canonical_pick

def settle_suggestion(parlay, grades_by_leg):
    legs=parlay.get('legs',[])
    if len(legs)<2:
        raise ValueError('Invalid frozen suggestion')
    keys=[canonical_pick(leg) for leg in legs]
    if len(set(keys))!=len(keys):
        raise ValueError('Duplicate frozen leg')
    results=[]
    for leg,key in zip(legs,keys):
        grade=grades_by_leg.get(key)
        outcome=grade.get('outcome') if grade else None
        if outcome not in (None,'hit','miss'):
            raise ValueError('Unsupported leg outcome')
        results.append(dict(leg=leg,outcome=outcome or 'pending',
                            actual_value=grade.get('actual_value') if grade else None))
    outcomes=[r['outcome'] for r in results]
    status='miss' if 'miss' in outcomes else ('hit' if all(x=='hit' for x in outcomes) else 'pending')
    return dict(outcome=status,legs=results)
