import unittest
import io
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import automation
from automation import authentic_capture_window, grade, injury_rows, number
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

    def test_authentic_capture_window_inclusive_boundaries(self):
        kickoff=datetime(2026,11,27,20,0,tzinfo=timezone.utc)
        for minutes,expected in [(29.99,False),(30,True),(32,True),(35,True),(35.01,False),(8*24*60,False)]:
            row={'created_at':(kickoff-timedelta(minutes=minutes)).isoformat(),
                 'kickoff_at':kickoff.isoformat()}
            with self.subTest(minutes=minutes):
                self.assertEqual(authentic_capture_window(row),expected)
        for row in [{}, {'created_at':'bad','kickoff_at':kickoff.isoformat()},
                    {'created_at':'2026-11-27T19:28:00','kickoff_at':kickoff.isoformat()}]:
            self.assertFalse(authentic_capture_window(row))

    def test_grader_excludes_early_and_late_snapshots_without_writing(self):
        kickoff=datetime(2026,11,27,20,0,tzinfo=timezone.utc)
        snapshots=[]
        events=[]
        for name,minutes in [('early',8*24*60),('too-early',35.01),('start',35),
                             ('middle',32),('end',30),('too-late',29.99)]:
            snapshots.append({**self.snapshot,'game_id':name,
                'kickoff_at':kickoff.isoformat(),
                'created_at':(kickoff-timedelta(minutes=minutes)).isoformat(),
                'picks':[{'market':'ml','side':'a'}]})
            events.append({**self.event,'id':name})
        writes=[]
        def database(path,rows=None,conflict=None):
            if path.startswith('nfl_prediction_snapshots_v2?'):return snapshots
            if path.startswith('nfl_stat_exports?'):return [{'csv_text':'season,week,team\n'}]
            if path.startswith('nfl_prediction_grades_v2?on_conflict='):
                writes.extend(rows)
                return rows
            if path.startswith('nfl_prediction_grades_v2?'):return []
            raise AssertionError('Unexpected database route: '+path)
        # Mock both the feed and the database. Never touch production data.
        with patch.object(automation,'rest',side_effect=database), \
             patch.object(automation,'urlopen',return_value=io.BytesIO(json.dumps({'events':events}).encode())):
            automation.grade_all(2026)
        self.assertEqual({r['game_id'] for r in writes},{'start','middle','end'})

if __name__=='__main__':unittest.main()
