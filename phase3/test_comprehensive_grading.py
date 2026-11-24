import unittest
from comprehensive_grading import grade_team

class TeamGradingTests(unittest.TestCase):
    def grade(self,market,side,line=None,**kw):
        return grade_team(dict(market=market,side=side,line=line,team='BUF'),
            away_team='BUF',home_team='KC',away_score=28,home_score=24,
            completed=kw.pop('completed',True),**kw)
    def test_moneyline(self): self.assertEqual(self.grade('ml','a'),('hit',28))
    def test_spread(self):
        self.assertEqual(self.grade('spread','a',-3.5),('hit',4))
        self.assertEqual(self.grade('spread','a',-4),('miss',4))
    def test_total(self): self.assertEqual(self.grade('total','u',53),('hit',52))
    def test_team_total(self): self.assertEqual(self.grade('team_total','o',27),('hit',28))
    def test_touchdowns(self):
        self.assertIsNone(self.grade('team_touchdowns','o',2.5))
        self.assertEqual(self.grade('team_touchdowns','o',2.5,touchdowns={'BUF':3}),('hit',3))
    def test_incomplete(self): self.assertIsNone(self.grade('ml','a',completed=False))
if __name__=='__main__': unittest.main()
