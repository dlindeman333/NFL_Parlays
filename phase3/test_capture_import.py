"""Exercise capture and grading imports without network access."""

from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CaptureImportTests(unittest.TestCase):
    def test_top12_from_repository_root(self):
        subprocess.run(
            [sys.executable, "-E", "-c", """
from snapshot_predictions import select_top12

pick = {
    'market': 'player', 'stat': 'receiving_yards', 'side': 'o',
    'player_name': 'Sample Player', 'team': 'LA',
    'line': 49.5, 'probability': 0.6,
}
report = {'week': 12, 'team': 'LAR', 'player': 'Sample Player', 'status': 'Out'}
assert select_top12([pick], [report], 12) == []
selected = select_top12([pick, pick], [], 12)
assert len(selected) == 1
assert selected[0]['injury_report_week'] == 12
"""],
            cwd=ROOT,
            check=True,
        )

    def test_grading_script_runs_directly(self):
        subprocess.run(
            [sys.executable, "-E", "phase3/automation.py", "--help"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
