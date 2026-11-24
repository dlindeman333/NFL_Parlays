import unittest
from comprehensive_reporting import summarize

class ReportingTests(unittest.TestCase):
    def row(self,key,**kw):
        return dict(season=2026,week=12,game_id='1',pick_key=key,market='player',**kw)
    def test_categories(self):
        r=summarize([self.row('a',recommended=True,legacy_player_top12=True,outcome='hit'),
                     self.row('b',outcome='miss'),self.row('c',recommended=True)])
        self.assertEqual(r['all_eligible','all']['hit_rate'],.5)
        self.assertEqual(r['recommended','all']['hit_rate'],1)
        self.assertEqual(r['recommended','all']['pending'],1)
        self.assertEqual(r['top12','all']['captured'],1)
    def test_no_decisions(self):
        self.assertIsNone(summarize([self.row('a',outcome='push')])['all_eligible','all']['hit_rate'])
    def test_duplicate(self):
        with self.assertRaises(ValueError): summarize([self.row('a'),self.row('a')])
if __name__=='__main__': unittest.main()
