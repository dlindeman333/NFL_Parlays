import unittest
from phase3.comprehensive_report_payload import report_payload
from phase3.comprehensive_export_review import export_tables
class ReportIntegrationTests(unittest.TestCase):
    def test_shared_totals(self):
        picks=[dict(season=2026,week=12,game_id='1',pick_key=str(i),market='player',recommended=True,legacy_player_top12=True,outcome=o) for i,o in enumerate(['hit','miss','pending','push'])]
        parlays=[dict(snapshot_id='p1',kind='same',legs=[{'line':2.5},{'line':3.5}],outcome='hit')]
        report=report_payload(picks,parlays)
        tables=export_tables(picks,parlays)
        self.assertEqual(report['individual'],tables['AI Performance'])
        self.assertEqual(report['suggested_parlays'],tables['Suggested Performance'])
        top=next(r for r in report['individual'] if r['category']=='top12' and r['market']=='all')
        self.assertEqual(top['hit_rate'],.5)
        self.assertEqual(len(tables['Suggested Legs']),2)
        self.assertTrue(all(r['snapshot_id']=='p1' for r in tables['Suggested Legs']))
    def test_empty(self):
        self.assertEqual(report_payload([],[])['individual'],[])
    def test_duplicate_parlay(self):
        p=dict(snapshot_id='p1',kind='same',legs=[],outcome='pending')
        with self.assertRaises(ValueError): report_payload([],[p,p])
if __name__=='__main__': unittest.main()
