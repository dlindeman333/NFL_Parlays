import unittest
from datetime import datetime,timezone,timedelta
from comprehensive_pipeline_review import capture_from_page

class FakePage:
    def evaluate(self,source,event):
        rows=[dict(market='player',team='BUF',player_name='Synthetic '+str(i),
                   stat='receiving_yards',side='o',line=20.5,probability=.8)
              for i in range(15)]
        return dict(away_team='BUF',home_team='KC',advanced=rows,alternatives=[],
                    unavailable_markets=['team_total'])

class PipelineTests(unittest.TestCase):
    def test_capture(self):
        now=datetime(2026,11,26,17,tzinfo=timezone.utc)
        event=dict(id='123',week=12,a='BUF',h='KC',kickoff=(now+timedelta(minutes=32)).isoformat())
        result=capture_from_page(FakePage(),event,2026,[],now)
        self.assertEqual(len(result['snapshot']['picks']),15)
        self.assertEqual(sum(p['legacy_player_top12'] for p in result['snapshot']['picks']),12)
        self.assertNotIn('created_at',result['snapshot'])
        with self.assertRaises(ValueError):
            capture_from_page(FakePage(),event,2026,[],now+timedelta(minutes=3))
if __name__=='__main__': unittest.main()
