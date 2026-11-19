"""Offline proof that previously enabled statistics cannot activate new writers."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class ProductionFeatureGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stats = (ROOT / '.github/workflows/nfl-automation.yml').read_text()
        cls.pregame = (ROOT / '.github/workflows/nfl-pregame-capture.yml').read_text()
        cls.review = (ROOT / '.github/workflows/nfl-phase3-review.yml').read_text()

    def test_pregame_publishing_requires_separate_explicit_flag(self):
        self.assertIn("vars.NFL_AUTOMATION_ENABLED == 'true' && vars.NFL_PHASE3_PUBLISH_ENABLED == 'true' && vars.NFL_PHASE3_LAUNCH_APPROVED == 'true'", self.pregame)
        self.assertIn('python snapshot_predictions.py --check-window', self.pregame)

    def test_stats_continue_while_phase3_writers_are_disabled(self):
        self.assertIn('run: python export_automated.py', self.stats)
        self.assertIn("if: vars.NFL_PHASE3_PUBLISH_ENABLED == 'true' && vars.NFL_PHASE3_LAUNCH_APPROVED == 'true' && steps.preflight.outcome == 'success'", self.stats)
        self.assertIn("vars.NFL_PHASE3_PUBLISH_ENABLED == 'true' && vars.NFL_PHASE3_LAUNCH_APPROVED == 'true' && steps.preflight.outcome == 'success' && steps.stats.outcome == 'success'", self.stats)
        self.assertNotIn('run: python snapshot_predictions.py', self.stats)

    def test_read_only_release_checks_have_no_cloud_credentials_or_writes(self):
        self.assertIn('python phase3/browser_smoke.py', self.review)
        self.assertIn('python -m unittest discover -s phase3', self.review)
        for forbidden in ('SUPABASE_SERVICE_ROLE_KEY', 'SUPABASE_URL', 'python export_automated.py',
                          'python phase3/automation.py injuries', 'python snapshot_predictions.py\n'):
            self.assertNotIn(forbidden, self.review)


if __name__ == '__main__':
    unittest.main()
