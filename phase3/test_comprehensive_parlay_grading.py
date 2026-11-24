import unittest
from phase3.comprehensive_parlay_grading import settle_suggestion
from phase3.grade_contract import canonical_pick

class ParlaySettlementTest(unittest.TestCase):
    def test_outcomes(self):
        a,b=dict(game_id='1',line=20),dict(game_id='2',line=30)
        p=dict(legs=[a,b])
        grades={canonical_pick(a):dict(outcome='hit',actual_value=21)}
        self.assertEqual(settle_suggestion(p,grades)['outcome'],'pending')
        grades[canonical_pick(b)]=dict(outcome='hit',actual_value=31)
        self.assertEqual(settle_suggestion(p,grades)['outcome'],'hit')
        grades={canonical_pick(a):dict(outcome='miss',actual_value=19)}
        self.assertEqual(settle_suggestion(p,grades)['outcome'],'miss')
        self.assertEqual(settle_suggestion(p,grades)['legs'][1]['outcome'],'pending')
        self.assertEqual(settle_suggestion(dict(legs=[dict(a,line=19),b]),grades)['outcome'],'pending')
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            settle_suggestion(dict(legs=[{},{}]),{})
