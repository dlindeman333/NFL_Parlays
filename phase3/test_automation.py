import unittest
from automation import grade, injury_rows, number
from grade_contract import pick_key

class FeatureChecks(unittest.TestCase):
    def setUp(self):
        self.snapshot={'season':2026,'week':10,'away_team':'BUF','home_team':'MIA'}
        self.event={'status':{'type':{'completed':True}},'competitions':[{'competitors':[
            {'homeAway':'away','team':{'abbreviation':'BUF'},'score':'24'},
            {'homeAway':'home','team':{'abbreviation':'MIA'},'score':'17'}]}]}
        self.pick={'market':'player','player_name':'Player Example','team':'BUF','stat':'rushing_yards','side':'o','line':50}
        self.record={'season':'2026','week':'10','team':'BUF','opponent_team':'MIA','game_status':'COMPLETED','name':'Player Example','rushing_yards':'51'}
    def test_final_moneyline_and_tie_miss(self):
        self.assertEqual(grade({'market':'ml','side':'a'},self.snapshot,self.event,[]),('hit',24))
        self.event['competitions'][0]['competitors'][1]['score']='24'
        self.assertEqual(grade({'market':'ml','side':'a'},self.snapshot,self.event,[])[0],'miss')
    def test_unfinished_or_wrong_game_never_graded(self):
        self.event['status']['type']['completed']=False
        self.assertIsNone(grade(self.pick,self.snapshot,self.event,[self.record]))
        self.event['status']['type']['completed']=True
        self.event['competitions'][0]['competitors'][1]['team']['abbreviation']='NYJ'
        self.assertIsNone(grade(self.pick,self.snapshot,self.event,[self.record]))
    def test_exact_statistics_and_equality(self):
        self.assertEqual(grade(self.pick,self.snapshot,self.event,[self.record]),('hit',51))
        self.record['rushing_yards']='50'
        self.assertEqual(grade(self.pick,self.snapshot,self.event,[self.record]),('miss',50))
    def test_missing_ambiguous_wrong_week_and_blank_stats_pending(self):
        self.assertIsNone(grade(self.pick,self.snapshot,self.event,[]))
        self.assertIsNone(grade(self.pick,self.snapshot,self.event,[self.record,self.record]))
        for field,value in [('week','9'),('opponent_team','NYJ'),('rushing_yards',''),('rushing_yards','nan')]:
            r={**self.record,field:value}
            self.assertIsNone(grade(self.pick,self.snapshot,self.event,[r]))
    def test_under_and_touchdown(self):
        self.assertEqual(grade({**self.pick,'side':'u'},self.snapshot,self.event,[self.record])[0],'miss')
        self.assertEqual(grade({**self.pick,'stat':'touchdowns','line':0.5},self.snapshot,self.event,[{**self.record,'touchdowns':'1'}])[0],'hit')
    def test_injuries_exact_week_and_unknown_not_healthy(self):
        text='season,game_type,week,team,full_name,report_status\n2026,REG,10,JAC,Player Example,Out\n2026,REG,10,BUF,Other Player,\n2025,REG,10,BUF,Old Player,Out\n'
        rows=injury_rows(text,2026)
        self.assertEqual(len(rows),2);self.assertEqual(rows[0]['team'],'JAX')
        self.assertEqual(rows[1]['status'],'Not designated')
        with self.assertRaises(ValueError):injury_rows('bad,schema\n1,2',2026)
        with self.assertRaises(ValueError):injury_rows(text,2024)
    def test_stable_pick_identity(self):
        self.assertEqual(pick_key(self.pick,0),pick_key(dict(reversed(list(self.pick.items()))),0))
        self.assertNotEqual(pick_key(self.pick,0),pick_key({**self.pick,'line':51},0))
        self.assertIsNone(number('nan'));self.assertIsNone(number('inf'))

if __name__=='__main__':unittest.main()
