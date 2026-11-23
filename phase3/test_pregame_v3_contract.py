"""Read-only contract: v3 migration and writer must preserve historical data."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VerifiedPregameV3(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sql = (ROOT/'phase3/migrations/2026-11-22_authentic_pregame_v3.sql').read_text()
        cls.capture = (ROOT/'snapshot_predictions.py').read_text()
        cls.automation = (ROOT/'phase3/automation.py').read_text()
        cls.html = (ROOT/'index.html').read_text()

    def test_additive_isolation_and_in_database_time_guard(self):
        self.assertIn('CREATE TABLE IF NOT EXISTS public.nfl_prediction_snapshots_v3',self.sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS public.nfl_prediction_grades_v3',self.sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS public.nfl_prediction_subscriptions_v3',self.sql)
        self.assertIn('NEW.created_at := clock_timestamp()',self.sql)
        self.assertIn("AND interval '35 minutes'",self.sql)
        self.assertIn('BEFORE INSERT OR UPDATE OR DELETE',self.sql)
        for old_table in ('nfl_prediction_snapshots_v2','nfl_prediction_grades_v2',
                          'nfl_prediction_subscriptions_v2','nfl_parlay_sync'):
            for verb in ('UPDATE','DELETE FROM','TRUNCATE','ALTER TABLE','DROP TABLE'):
                self.assertNotIn(f'{verb} public.{old_table}',self.sql)

    def test_writer_never_checks_legacy_v2_as_already_captured(self):
        self.assertIn('missing_captures(events, existing)',self.capture)
        self.assertIn('/rest/v1/nfl_prediction_snapshots_v3?',self.capture)
        self.assertNotIn('/rest/v1/nfl_prediction_snapshots_v2?',self.capture)
        self.assertIn('return=representation',self.capture)

    def test_app_reads_both_archives_without_joining_grades_across_sources(self):
        for version in ('v2','v3'):
            self.assertIn('nfl_prediction_snapshots_'+version,self.html)
            self.assertIn('nfl_prediction_grades_'+version,self.automation)
        self.assertIn("g.source===r.source",self.html)
        self.assertIn("grade.source+'|'",self.html)
        self.assertIn('nfl_prediction_subscriptions_v3',self.html)


if __name__=='__main__':
    unittest.main()
