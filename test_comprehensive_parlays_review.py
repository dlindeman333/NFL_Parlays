import unittest
from datetime import datetime,timezone,timedelta
from phase3.comprehensive_parlays import freeze_parlay
class ParlayTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,26,17,tzinfo=timezone.utc)
    def leg(self,game,player,lead=32):
        return dict(game_id=game,market='player',team='BUF',player_name=player,stat='receiving_yards',side='o',line=20.5,decimal=1.9,kickoff_at=(self.now+timedelta(minutes=lead)).isoformat(),captured_at=self.now.isoformat())
    def freeze(self,rows,kind='same'):
        return freeze_parlay(rows,kind=kind,generated_at=self.now,settings={},joint_probability=.4,model_version='synthetic')
    def test_same(self):
        rows=[self.leg('1','A'),self.leg('1','B')]
        result=self.freeze(rows)
        self.assertAlmostEqual(result['estimated_combined_decimal'],3.61)
        rows[0]['line']=99
        self.assertEqual(result['legs'][0]['line'],20.5)
    def test_multi(self):
        self.assertEqual(len(self.freeze([self.leg('1','A'),self.leg('2','B',180)],'multi')['legs']),2)
    def test_duplicate(self):
        with self.assertRaises(ValueError): self.freeze([self.leg('1','A'),self.leg('1','A')])
    def test_late(self):
        with self.assertRaises(ValueError): self.freeze([self.leg('1','A',29),self.leg('1','B',29)])
    def test_future_capture(self):
        rows=[self.leg('1','A'),self.leg('1','B')]
        rows[0]['captured_at']=(self.now+timedelta(seconds=1)).isoformat()
        with self.assertRaises(ValueError): self.freeze(rows)
if __name__=='__main__': unittest.main()
