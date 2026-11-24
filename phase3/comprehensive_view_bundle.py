"""Single offline view bundle for dashboard and workbook consumers."""
from phase3.comprehensive_export_review import export_tables

def build_view_bundle(picks, parlays):
    tables = export_tables(picks, parlays)
    return {
        'schema_version': 4,
        'dashboard': {
            'individual': tables['AI Performance'],
            'suggested_parlays': tables['Suggested Performance'],
            'accuracy_threshold': .75,
            'denominator': 'hit_plus_miss',
            'all_eligible_is_model_accuracy': False,
        },
        'workbook_tables': tables,
    }
