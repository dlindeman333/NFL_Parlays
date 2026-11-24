import unittest
from phase3.comprehensive_capture import prepare_capture
class TeamMarketTests(unittest.TestCase):
    def test_team_touchdowns(self):
        rows=[dict(market='team_touchdowns',team='BUF',side=s,line=2.5,probability=p,probability_source='model',model_preferred=False,line_source='model_default') for s,p in [('o',.7),('u',.3)]]
        result=prepare_capture([],rows)
        self.assertEqual(len(result),2)
        self.assertTrue(all(not r['recommended'] and not r['legacy_player_top12'] for r in result))
    def test_unverified_total(self):
        self.assertEqual(prepare_capture([], [dict(market='team_total',team='BUF',side='o',line=24.5,probability=.7)]),[])
    def test_placeholder(self):
        result=prepare_capture([], [dict(market='spread',team='BUF',side='a',line=-3,probability=.5,probability_source='placeholder',line_convention='selected_team_signed',model_preferred=True)])
        self.assertEqual(len(result),1)
        self.assertFalse(result[0]['recommended'])
if __name__=='__main__': unittest.main()
