import unittest
from datetime import datetime, timezone, timedelta
from phase3.comprehensive_suggestion_bridge import assemble_suggestions

class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,26,17,tzinfo=timezone.utc)
        self.rows={k:dict(game_id='1',market='player',team='BUF',player_name=k,stat='receiving_yards',side='o',line=20.5,decimal=1.9,kickoff_at=(self.now+timedelta(minutes=32)).isoformat(),captured_at=self.now.isoformat()) for k in ['a','b']}
        self.c=dict(keys=['a','b'],count=2,kind='same',settings={},joint_probability=.4,estimated_decimal=3.61,category='best',correlated=True)
    def run_bridge(self, candidates):
        return assemble_suggestions(candidates,self.rows,self.now,'synthetic')
    def test_preservation(self):
        r=self.run_bridge([self.c])[0]
        self.assertEqual(r['category'],'best')
        self.assertEqual(r['joint_probability'],.4)
        self.rows['a']['line']=99
        self.assertEqual(r['legs'][0]['line'],20.5)
    def test_duplicate(self):
        self.assertEqual(len(self.run_bridge([self.c,{**self.c,'keys':['b','a']} ])),1)
    def test_odds_mismatch(self):
        with self.assertRaises(ValueError): self.run_bridge([{**self.c,'estimated_decimal':4}])
    def test_unknown_leg(self):
        with self.assertRaises(KeyError): self.run_bridge([{**self.c,'keys':['a','z']}])
    def test_wrong_count(self):
        with self.assertRaises(ValueError): self.run_bridge([{**self.c,'count':3}])
if __name__=='__main__': unittest.main()
