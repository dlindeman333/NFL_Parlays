"""Review-only performance aggregation for frozen predictions."""
from collections import defaultdict

def summarize(rows):
    groups=defaultdict(lambda: dict(captured=0,hit=0,miss=0,push=0,pending=0))
    seen=set()
    for row in rows:
        identity=tuple(row[k] for k in ('season','week','game_id','pick_key'))
        if identity in seen:
            raise ValueError('Duplicate prediction identity; reconcile versions before reporting')
        seen.add(identity)
        outcome=row.get('outcome')
        if outcome not in ('hit','miss','push',None,'pending'):
            raise ValueError('Unknown outcome')
        outcome=outcome if outcome in ('hit','miss','push') else 'pending'
        categories=['all_eligible']
        if row.get('recommended') is True: categories.append('recommended')
        if row.get('legacy_player_top12') is True: categories.append('top12')
        for category in categories:
            for key in ((category,'all'),(category,'market:'+str(row.get('market','unknown')))):
                g=groups[key]; g['captured']+=1; g[outcome]+=1
    for g in groups.values():
        n=g['hit']+g['miss']
        g['graded_decisions']=n
        g['hit_rate']=g['hit']/n if n else None
    return dict(groups)
