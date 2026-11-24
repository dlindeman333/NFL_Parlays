import unittest
from phase3.comprehensive_view_bundle import build_view_bundle

class ViewBundleTests(unittest.TestCase):
    def test_empty(self):
        b=build_view_bundle(iter([]),iter([]))
        self.assertEqual(b['schema_version'],4)
        self.assertEqual(len(b['workbook_tables']),5)
        self.assertEqual(b['dashboard']['individual'],[])
    def test_streamed_details_and_totals(self):
        p=dict(season=2026,week=12,game_id='g',pick_key='k',market='player',recommended=True,legacy_player_top12=True,outcome='hit')
        s=dict(snapshot_id='s',kind='same',legs=[dict(pick_key='k')],outcome='pending')
        b=build_view_bundle(iter([p]),iter([s]))
        t=b['workbook_tables']
        self.assertEqual(t['AI Prediction Details'],[p])
        self.assertEqual(len(t['Suggested Legs']),1)
        self.assertEqual(len(t['Suggested Parlays']),1)
        self.assertEqual(b['dashboard']['individual'],t['AI Performance'])
        self.assertEqual(b['dashboard']['suggested_parlays'],t['Suggested Performance'])
        self.assertFalse(b['dashboard']['all_eligible_is_model_accuracy'])
