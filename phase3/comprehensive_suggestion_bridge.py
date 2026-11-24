"""Resolve generator output against frozen leg identities; never reconstruct legs."""
from phase3.comprehensive_parlays import freeze_parlay

def assemble_suggestions(generated, frozen_by_key, now, model_version):
    result=[]
    seen=set()
    for candidate in generated:
        keys=candidate['keys']
        if len(keys)!=candidate['count'] or len(set(keys))!=len(keys):
            raise ValueError('Invalid generator leg count')
        identity=tuple(sorted(keys))
        if identity in seen: continue
        rows=[frozen_by_key[key] for key in keys]
        record=freeze_parlay(rows,kind=candidate['kind'],generated_at=now,
            settings={**candidate['settings'],'leg_count':candidate['count']},
            joint_probability=candidate['joint_probability'],model_version=model_version)
        if abs(record['estimated_combined_decimal']-candidate['estimated_decimal'])>1e-8*max(1,record['estimated_combined_decimal']):
            raise ValueError('Generator odds mismatch')
        record.update(category=candidate['category'],correlated=candidate['correlated'])
        seen.add(identity)
        result.append(record)
    return result
