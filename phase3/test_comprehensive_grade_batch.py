import unittest
from phase3.comprehensive_grade_batch import grade_snapshot
from phase3.grade_contract import validate_row

class GradeBatchTest(unittest.TestCase):
    def setUp(self):
        self.snapshot=dict(season=2026,week=12,game_id='123',away_team='BUF',home_team='KC',picks=[dict(market='ml',side='a'),dict(market='player'),dict(market='team_touchdowns',team='BUF',side='o',line=2.5)])
        self.final=dict(game_id='123',away_team='BUF',home_team='KC',completed=True,away_score=28,home_score=20)
    def test_batch(self):
        rows=grade_snapshot(self.snapshot,self.final,lambda *a:('miss',20))
        self.assertEqual([r['outcome'] for r in rows],['hit','miss'])
        self.assertTrue(all(validate_row(r) for r in rows))
        self.assertEqual(grade_snapshot(self.snapshot,self.final,lambda *a:('miss',20),[r['pick_key'] for r in rows]),[])
    def test_pending(self):
        self.assertEqual(grade_snapshot(self.snapshot,dict(self.final,completed=False),lambda *a:None),[])
    def test_mismatch(self):
        with self.assertRaises(ValueError):
            grade_snapshot(self.snapshot,dict(self.final,home_team='NYJ'),lambda *a:None)
