import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from phase3.comprehensive_worker import TestDatabase, publish_reports, report_rows, touchdowns_from_scoring
from phase3.grade_contract import pick_key


class ComprehensiveWorkerTest(unittest.TestCase):
    def test_backend_refuses_production(self):
        with patch.dict('os.environ', {'NFL_V4_SUPABASE_URL': 'https://wpvuunwtyxycqfjwuzkn.supabase.co'}):
            with self.assertRaisesRegex(ValueError, 'isolated TEST'):
                TestDatabase()

    def test_actual_touchdowns_include_scores_with_conversion(self):
        final = dict(away_team='BUF', home_team='KC', away_score='7', home_score='3')
        plays = [
            dict(id='a', team={'abbreviation': 'BUF'}, awayScore=7, homeScore=0,
                 scoringType={'abbreviation': 'TD'}),
            dict(id='b', team={'abbreviation': 'KC'}, awayScore=7, homeScore=3,
                 scoringType={'abbreviation': 'FG'}),
        ]
        summary = dict(header={'id': '1'}, scoringPlays=plays)
        self.assertEqual(touchdowns_from_scoring(summary, final, '1'), {'BUF': 1, 'KC': 0})
        self.assertIsNone(touchdowns_from_scoring(summary, {**final, 'home_score': '6'}, '1'))
        self.assertIsNone(touchdowns_from_scoring(summary, final, '2'))

    def test_same_cloud_rows_drive_parlay_results_and_workbook(self):
        created = datetime(2026, 11, 26, 17, tzinfo=timezone.utc)
        kickoff = created + timedelta(minutes=32)
        pick = dict(market='ml', side='a', line=None, legacy_player_top12=False, recommended=True)
        key = pick_key(pick, 0)
        captures = [
            dict(season=2026, week=12, game_id=gid, picks=[pick], suggested_parlays=[],
                 kickoff_at=kickoff.isoformat(), created_at=created.isoformat())
            for gid in ('11', '22')
        ]
        legs = [{**pick, 'season': 2026, 'week': 12, 'game_id': gid, 'pick_key': key} for gid in ('11', '22')]
        captures[0]['suggested_parlays'] = [dict(kind='multi', legs=legs, category='best')]
        grades = [dict(season=2026, week=12, game_id='11', pick_key=key, outcome='miss', actual_value=13)]
        picks, parlays = report_rows(captures, grades)
        self.assertEqual([p['outcome'] for p in picks], ['miss', 'pending'])
        self.assertEqual(parlays[0]['outcome'], 'miss')
        self.assertEqual([l['outcome'] for l in parlays[0]['legs']], ['miss', 'pending'])
        with patch('phase3.comprehensive_worker.TestDatabase') as db:
            publish_reports(db, captures, grades)
            self.assertEqual(db.request.call_count, 2)
            for call, week in zip(db.request.call_args_list, [0, 12]):
                row = call.args[1][0]
                self.assertEqual(row['week'], week)
                tables = row['bundle']['workbook_tables']
                self.assertEqual(tables['Suggested Parlays'][0]['outcome'], 'miss')
                self.assertEqual(tables['AI Prediction Details'][1]['outcome'], 'pending')
        with self.assertRaisesRegex(ValueError, 'missing its frozen capture'):
            report_rows(captures[:1], grades)
