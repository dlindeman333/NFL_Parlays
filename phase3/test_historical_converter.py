"""Offline synthetic provenance/CSV boundary tests: no data access or writes."""
import unittest
from convert_player_week_csv import convert

HEAD = "player_id,player_display_name,team,position,week,targets,receptions,receiving_yards,passing_yards,rushing_yards,rushing_tds,receiving_tds,passing_tds\n"
ROW = "00-001,Player A,BUF,WR,5,4,3,-2,0,-3,1,0,4\n"
ARGS = dict(season=2026, snapshot_week=10, source_url="https://example.test/archived.csv", source_commit="1"*40)


class HistoricalCSVValidationTests(unittest.TestCase):
    def test_negative_yards_are_real_and_passing_touchdowns_not_anytime(self):
        rows, info = convert(HEAD+ROW, **ARGS)
        self.assertEqual(rows[0]['receiving_yards'], -2)
        self.assertEqual(rows[0]['rushing_yards'], -3)
        self.assertEqual(rows[0]['touchdowns'], 1)
        self.assertEqual(rows[0]['game_status'], 'COMPLETED')
        self.assertIn('derived', info['completed_status'])

    def test_future_rows_rejected(self):
        with self.assertRaisesRegex(ValueError, 'future week'):
            convert(HEAD+ROW.replace(',5,4,', ',10,4,'), **ARGS)

    def test_duplicate_player_id_week_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            convert(HEAD+ROW+ROW, **ARGS)

    def test_undocumented_source_rejected(self):
        with self.assertRaisesRegex(ValueError, 'source URL'):
            convert(HEAD+ROW, **{**ARGS, 'source_commit':'unknown'})

    def test_receptions_exceeding_targets_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Receptions exceed'):
            convert(HEAD+ROW.replace(',5,4,3,', ',5,2,3,'), **ARGS)


if __name__ == '__main__':
    unittest.main()
