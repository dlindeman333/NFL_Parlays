"""Offline checks for forward-only capture gating; never read or write live data."""
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import snapshot_predictions as snapshots


class CaptureWindowChecks(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 19, 15, 0, tzinfo=timezone.utc)

    def event(self, name, minutes, state='pre'):
        return {'id': name, 'date': (self.now + timedelta(minutes=minutes)).isoformat(),
                'status': {'type': {'state': state}},
                'competitions': [{'competitors': [
                    {'homeAway': 'away', 'team': {'abbreviation': 'BUF'}},
                    {'homeAway': 'home', 'team': {'abbreviation': 'MIA'}}]}]}

    def test_only_pregame_games_thirty_to_thirty_five_minutes_away(self):
        events = [self.event('early', 29.9), self.event('start', 30),
                  self.event('middle', 32), self.event('end', 35),
                  self.event('too-soon', 35.1), self.event('days-ahead', 8 * 24 * 60),
                  self.event('already-live', 32, 'in')]
        def schedule_feed(url, **kwargs):
            return {'events': events if 'week=10' in url else []}
        with patch.object(snapshots, 'fetch', side_effect=schedule_feed) as feed:
            found = snapshots.schedule(self.now)
        self.assertEqual([e['id'] for e in found], ['start', 'middle', 'end'])
        self.assertEqual(feed.call_count, 18)
        self.assertTrue(all(e['a'] == 'BUF' and e['h'] == 'MIA' for e in found))

    def test_preparation_early_but_capture_still_strict(self):
        events = [self.event('preparing', 90), self.event('too-early', 101),
                  self.event('ready', 34), self.event('too-late', 29),
                  self.event('in-progress', 45, 'in')]
        def feed(url, **kwargs):
            return {'events': events if 'week=11' in url else []}
        with patch.object(snapshots, 'fetch', side_effect=feed):
            self.assertEqual([e['id'] for e in snapshots.schedule(self.now)], ['ready'])
            self.assertEqual([e['id'] for e in snapshots.schedule(self.now, max_lead=snapshots.PREP_MAX)],
                             ['preparing', 'ready'])
        self.assertTrue(snapshots.within_capture_window(self.now+timedelta(minutes=35), self.now))
        self.assertTrue(snapshots.within_capture_window(self.now+timedelta(minutes=30), self.now))
        self.assertFalse(snapshots.within_capture_window(self.now+timedelta(minutes=45), self.now))
        self.assertFalse(snapshots.within_capture_window(self.now+timedelta(minutes=29), self.now))

    def test_read_only_wait_starts_preparation_early_and_rechecks(self):
        current = [self.now]
        wakeups = []
        def advance(seconds):
            wakeups.append(seconds)
            current[0] += timedelta(seconds=seconds)
        def feed(url, **kwargs):
            return {'events': [self.event('ready', 45)] if 'week=11' in url else []}
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {'GITHUB_OUTPUT': str(Path(directory)/'github_output')}, clear=True), \
             patch.object(snapshots, 'fetch', side_effect=feed), \
             patch.object(snapshots, 'credentials', side_effect=AssertionError('cloud access')):
            self.assertTrue(snapshots.wait_for_window(clock=lambda: current[0], sleeper=advance))
            self.assertEqual((Path(directory)/'github_output').read_text(), 'eligible=true\n')
        self.assertGreater(len(wakeups), 1)
        self.assertLessEqual(max(wakeups), 30)
        self.assertTrue(snapshots.within_capture_window(self.now + timedelta(minutes=45), current[0]))

    def test_window_wait_fails_closed_if_event_changes_state(self):
        event = {'id': 'event', 'kickoff': (self.now + timedelta(minutes=45)).isoformat()}
        current = [self.now]
        def advance(seconds):
            current[0] += timedelta(seconds=seconds)
        with patch.object(snapshots, 'schedule', side_effect=[[event], []]) as schedule, \
             patch.object(snapshots, 'credentials', side_effect=AssertionError('cloud access')):
            self.assertFalse(snapshots.wait_for_window(clock=lambda: current[0], sleeper=advance))
        self.assertEqual(schedule.call_count, 2)

    def test_wait_budget_fails_closed_if_clock_stops(self):
        event = {'id': 'event', 'kickoff': (self.now + timedelta(minutes=45)).isoformat()}
        delays = []
        with patch.object(snapshots, 'schedule', return_value=[event]) as schedule:
            self.assertFalse(snapshots.wait_for_window(clock=lambda: self.now, sleeper=delays.append))
        self.assertEqual(sum(delays), snapshots.MAX_WAIT_SECONDS)
        self.assertEqual(schedule.call_count, 1)

    def test_preparation_flag_uses_only_read_only_schedule(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'github_output'
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}, clear=True), \
                 patch.object(snapshots, 'schedule', return_value=[{'id': 'game'}]) as schedule, \
                 patch.object(snapshots, 'credentials', side_effect=AssertionError('cloud access')):
                self.assertTrue(snapshots.check_window(preparation=True))
                schedule.assert_called_once_with(max_lead=snapshots.PREP_MAX)
            self.assertEqual(output.read_text(), 'eligible=true\n')

    def test_check_window_needs_no_database_credential_or_browser(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'github_output'
            output.touch()
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}, clear=True), \
                 patch.object(snapshots, 'schedule', return_value=[{'id': '123'}]):
                self.assertTrue(snapshots.check_window())
            self.assertEqual(output.read_text(), 'eligible=true\n')
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}, clear=True), \
                 patch.object(snapshots, 'schedule', return_value=[]):
                self.assertFalse(snapshots.check_window())
            self.assertTrue(output.read_text().endswith('eligible=false\n'))

    def test_network_failure_does_not_mark_capture_eligible(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'github_output'
            output.touch()
            with patch.dict(os.environ, {'GITHUB_OUTPUT': str(output)}, clear=True), \
                 patch.object(snapshots, 'schedule', side_effect=TimeoutError('ESPN offline')):
                with self.assertRaises(TimeoutError):
                    snapshots.check_window()
            self.assertEqual(output.read_text(), '')

    def test_nonproduction_backend_and_missing_secret_are_blocked(self):
        with patch.dict(os.environ, {'SUPABASE_URL': 'https://test.supabase.co',
                                     'SUPABASE_SERVICE_ROLE_KEY': 'synthetic'}, clear=True):
            with self.assertRaisesRegex(ValueError, 'mismatch'):
                snapshots.credentials()
        with patch.dict(os.environ, {'SUPABASE_URL': snapshots.PRODUCTION}, clear=True):
            with self.assertRaisesRegex(ValueError, 'Missing service'):
                snapshots.credentials()

    def test_capture_outside_window_has_no_cloud_access(self):
        with patch.object(snapshots, 'schedule', return_value=[]), \
             patch.object(snapshots, 'credentials', side_effect=AssertionError('cloud accessed')):
            self.assertIsNone(snapshots.main())

    def test_existing_immutable_snapshot_is_never_replaced(self):
        event={'week':11,'id':'123','a':'BUF','h':'MIA','kickoff':self.now.isoformat()}
        record={'week':11,'game_id':'123','kickoff_at':event['kickoff'],
                'created_at':(self.now-timedelta(minutes=32)).isoformat()}
        with patch.object(snapshots,'schedule',return_value=[event]), \
             patch.object(snapshots,'credentials',return_value=(snapshots.PRODUCTION,'synthetic')), \
             patch.object(snapshots,'fetch',return_value=[record]) as fetch:
            self.assertIsNone(snapshots.main())
            self.assertEqual(fetch.call_count,1)  # No data or writer invoked.
            self.assertIn('/nfl_prediction_snapshots_v3?',fetch.call_args.args[0])

    def test_week_11_old_v2_snapshot_does_not_block_new_v3_capture(self):
        game={'week':11,'id':'1122','kickoff':'2026-11-22T18:00:00+00:00'}
        # The 11/14 v2 record is irrelevant: the new writer only reads v3.
        self.assertEqual(snapshots.missing_captures([game], []),[game])
        self.assertFalse(snapshots.authentic_snapshot({
            'created_at':'2026-11-14T22:13:23+00:00','kickoff_at':game['kickoff']}))
        valid={'week':11,'game_id':'1122','created_at':'2026-11-22T17:27:00+00:00',
               'kickoff_at':game['kickoff']}
        self.assertTrue(snapshots.authentic_snapshot(valid))
        self.assertEqual(snapshots.missing_captures([game],[valid]),[])

    def test_invalid_or_duplicate_v3_row_fails_closed_without_overwrite(self):
        game={'week':11,'id':'1122','kickoff':'2026-11-22T18:00:00+00:00'}
        early={'week':11,'game_id':'1122','created_at':'2026-11-14T22:13:23Z',
               'kickoff_at':game['kickoff']}
        with self.assertRaisesRegex(RuntimeError,'Immutable rows must never be overwritten'):
            snapshots.missing_captures([game],[early])
        wrong={'week':11,'game_id':'1122','created_at':'2026-11-22T17:27:00Z',
               'kickoff_at':'2026-11-22T18:01:00+00:00'}
        with self.assertRaisesRegex(RuntimeError,'manual review required'):
            snapshots.missing_captures([game],[wrong])

    def test_time_limits_are_strict_and_timezone_aware(self):
        kickoff='2026-11-22T18:00:00+00:00'
        for minutes,expected in ((29.99,False),(30,True),(32.5,True),(35,True),(35.01,False)):
            row={'created_at':(datetime.fromisoformat(kickoff)-timedelta(minutes=minutes)).isoformat(),
                 'kickoff_at':kickoff}
            self.assertEqual(snapshots.authentic_snapshot(row),expected)
        self.assertFalse(snapshots.authentic_snapshot({'created_at':'not-a-date','kickoff_at':kickoff}))

    def test_top12_filters_injuries_before_cap_and_preserves_rank(self):
        candidates=[{'market':'player','stat':'receptions','side':'o','line':4.5,
                     'probability':.75,'player_name':f'Player {i}','team':'BUF'} for i in range(15)]
        reports=[{'week':11,'team':'BUF','player':'Player 0','status':'Out'},
                 {'week':10,'team':'BUF','player':'Player 1','status':'Out'},
                 {'week':11,'team':'BUF','player':'Player 2','status':'Doubtful'}]
        selected=snapshots.select_top12(candidates,reports,11)
        self.assertEqual(len(selected),12)
        self.assertEqual([r['player_name'] for r in selected],
                         ['Player 1']+[f'Player {i}' for i in range(3,14)])
        self.assertEqual(selected[0]['injury_status'],'unknown / no matching weekly report')
        self.assertEqual(selected[0]['injury_report_week'],11)
        self.assertEqual(len(candidates),15)  # Frozen source input remains unchanged.

    def test_top12_rejects_duplicate_or_unsupported_selections(self):
        candidate={'market':'player','stat':'receiving_yards','side':'u','line':59.5,
                   'probability':.65,'player_name':'Receiver','team':'MIA'}
        rows=[candidate,candidate.copy(),{**candidate,'market':'ml'},
              {**candidate,'stat':'unsupported'},{**candidate,'line':None}]
        selected=snapshots.select_top12(rows,[],11)
        self.assertEqual(len(selected),1)
        self.assertEqual(selected[0]['player_name'],'Receiver')
        self.assertEqual(len(rows),5)


if __name__ == '__main__':
    unittest.main()
