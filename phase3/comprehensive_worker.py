"""TEST-only v4 capture, final grading and shared report publication."""
import argparse
import csv
import io
import json
import os
from datetime import datetime, timezone, timedelta
from itertools import groupby
from urllib.request import Request, urlopen

from comprehensive_pipeline_review import attach_suggestions, capture_from_page
from snapshot_predictions import MODEL_SEASON, ROOT, SEASON, authentic_snapshot, fetch, schedule, within_capture_window
from .automation import grade, injury_rows, team
from .comprehensive_grade_batch import grade_snapshot
from .comprehensive_parlay_grading import settle_suggestion
from .comprehensive_view_bundle import build_view_bundle
from .grade_contract import canonical_pick, pick_key

TEST_URL = 'https://luxezjthznupdghmexyh.supabase.co'
ESPN = 'https://site.api.espn.com/apis/site/v2/sports/football/nfl'
PAGE_SIZE = 50
SNAPSHOTS = 'nfl_prediction_snapshots_v4'
GRADES = 'nfl_prediction_grades_v4'
REPORTS = 'nfl_prediction_reports_v4'


def utcnow():
    return datetime.now(timezone.utc)


def timestamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


class TestDatabase:
    def __init__(self):
        if os.environ.get('NFL_V4_SUPABASE_URL', '').rstrip('/') != TEST_URL:
            raise ValueError('V4 worker requires the isolated TEST project')
        self.key = os.environ['NFL_V4_SERVICE_ROLE_KEY']

    def request(self, path, rows=None, resolution='ignore-duplicates'):
        headers = {'apikey': self.key, 'Authorization': 'Bearer ' + self.key}
        data = None
        if rows is not None:
            data = json.dumps(rows, allow_nan=False).encode()
            headers.update({'Content-Type': 'application/json',
                            'Prefer': (f'resolution={resolution},' if resolution else '') + 'return=representation'})
        with urlopen(Request(TEST_URL + '/rest/v1/' + path, data=data, headers=headers), timeout=45) as response:
            return json.load(response)

    def pages(self, table, order, filters=''):
        offset = 0
        while True:
            rows = self.request(f'{table}?season=eq.{SEASON}&order={order}&limit={PAGE_SIZE}&offset={offset}{filters}')
            yield from rows
            if not rows:
                break
            offset += len(rows)


def latest_inputs(db, table, field, time_field, hours):
    rows = db.request(f'{table}?season=eq.{SEASON}&select={field},{time_field}&order={time_field}.desc&limit=1')
    if not rows or not rows[0].get(field):
        raise RuntimeError(f'{table} input unavailable')
    age = utcnow() - timestamp(rows[0][time_field])
    if not timedelta() <= age <= timedelta(hours=hours):
        raise RuntimeError(f'{table} input freshness check failed')
    return rows[0][field]


def freeze_cohort(page, events, injuries, now):
    captures = [capture_from_page(page, event, SEASON, injuries, now) for event in events]
    snapshots = [capture['snapshot'] for capture in captures]
    pools = page.evaluate((ROOT / 'phase3/comprehensive_candidate_pool.js').read_text(), snapshots)
    run_generator = (ROOT / 'phase3/comprehensive_parlay_generator_review.js').read_text()
    for snapshot, pool in zip(snapshots, pools):
        odds_by_index = {int(row['key'].rsplit(':', 1)[1]): row['decimal'] for row in pool}
        for index, pick in enumerate(snapshot['picks']):
            pick['estimated_decimal'] = odds_by_index.get(index)
            pick['odds_source'] = 'model_estimate' if index in odds_by_index else None
    frozen = {}
    for snapshot, rows in zip(snapshots, pools):
        for row in rows:
            index = int(row['key'].rsplit(':', 1)[1])
            pick = snapshot['picks'][index]
            frozen[row['key']] = {**pick, 'season': snapshot['season'], 'week': snapshot['week'],
                                  'game_id': snapshot['game_id'], 'kickoff_at': snapshot['kickoff_at'],
                                  'captured_at': now.isoformat(), 'decimal': row['decimal'],
                                  'pick_key': pick_key(pick, index)}
    for index, rows in enumerate(pools):
        scope = [{'kind': 'same', 'rows': rows}]
        # The first game anchors multi-game suggestions for the cohort.
        if index == 0 and len(pools) > 1:
            scope.append({'kind': 'multi', 'rows': [row for pool in pools for row in pool]})
        generated = page.evaluate(run_generator, {'pools': scope})
        snapshots[index] = attach_suggestions(captures[index], generated, frozen, now)['snapshot']
    return snapshots


def publish_capture(db, events):
    if not events:
        return
    if SEASON != MODEL_SEASON:
        raise RuntimeError('Season is outside the validated model contract')
    existing = {(r['week'], r['game_id']): r for r in db.pages(SNAPSHOTS, 'week,game_id')}
    groups = sorted(events, key=lambda e: (e['kickoff'], e['id']))
    pending = []
    for kickoff, cohort in groupby(groups, key=lambda e: e['kickoff']):
        missing = []
        for event in cohort:
            row = existing.get((event['week'], event['id']))
            if row is None:
                missing.append(event)
            elif not authentic_snapshot(row) or timestamp(row['kickoff_at']) != timestamp(kickoff):
                raise RuntimeError('Conflicting frozen snapshot; manual inspection required')
        if missing:
            pending.append(missing)
    if not pending:
        return
    stats = latest_inputs(db, 'nfl_stat_exports', 'csv_text', 'generated_at', 48)
    injuries = latest_inputs(db, 'nfl_prediction_injuries_v4', 'records', 'fetched_at', 24)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        executable = os.getenv('NFL_V4_CHROMIUM_EXECUTABLE')
        browser = playwright.chromium.launch(executable_path=executable)
        page = browser.new_page()
        page.route('**/*', lambda route: route.continue_() if route.request.url.startswith('file:') else route.abort())
        page.goto((ROOT / 'index.html').as_uri(), wait_until='domcontentloaded')
        page.evaluate('(csv) => loadCSV(csv, {persist:false})', stats)
        for cohort in pending:
            kickoff = timestamp(cohort[0]['kickoff'])
            if not within_capture_window(kickoff, utcnow()):
                continue
            frozen = freeze_cohort(page, cohort, injuries, utcnow())
            if not within_capture_window(kickoff, utcnow()):
                raise RuntimeError('Capture window closed during generation')
            # A duplicate makes the entire cohort fail atomically. A retry only
            # considers missing identities and never overwrites the original.
            saved = db.request(SNAPSHOTS + '?on_conflict=season,week,game_id', frozen, resolution='')
            if len(saved) != len(frozen) or not all(authentic_snapshot(row) for row in saved):
                raise RuntimeError('Frozen snapshot readback failed')
            print(f'Captured {len(saved)} authentic game(s) in TEST')
        browser.close()


def nfl_events(week):
    query = f'dates={SEASON}&seasontype=2&week={week}&limit=100'
    return {str(event['id']): event for event in fetch(f'{ESPN}/scoreboard?{query}').get('events', [])}


def final_game(event, game_id, needs_touchdowns):
    if not event.get('status', {}).get('type', {}).get('completed'):
        return {'completed': False}
    competitors = (event.get('competitions') or [{}])[0].get('competitors', [])
    sides = {row['homeAway']: row for row in competitors}
    if set(sides) != {'away', 'home'}:
        return {'completed': False}
    final = {'completed': True, 'game_id': game_id}
    for side, row in sides.items():
        final[f'{side}_team'] = team(row['team']['abbreviation'])
        final[f'{side}_score'] = row.get('score')
    if needs_touchdowns:
        from urllib.error import URLError
        try:
            summary = fetch(f'{ESPN}/summary?event={game_id}')
            final['touchdowns'] = touchdowns_from_scoring(summary, final, game_id)
        except (URLError, TimeoutError, ValueError):
            print(f'Touchdown feed unavailable for {game_id}; touchdown selections remain pending')
    return final


def touchdowns_from_scoring(summary, final, game_id):
    # Scoring plays include defensive and return scores. Reconcile every
    # scoring point against the official final before settling either team.
    plays = summary.get('scoringPlays')
    if str(summary.get('header', {}).get('id')) != game_id or not isinstance(plays, list):
        return None
    teams = {final['away_team']: 0, final['home_team']: 0}
    points = {'away': 0, 'home': 0}
    ids = set()
    try:
        for play in plays:
            name = team(play['team']['abbreviation'])
            side = next((s for s in points if final[f'{s}_team'] == name), None)
            scores = {s: int(play[f'{s}Score']) for s in points}
            code = play['scoringType']['abbreviation']
            if side is None or play['id'] in ids or code not in ('TD', 'FG', 'SF', 'XP', '2PT'):
                return None
            delta = scores[side] - points[side]
            if delta <= 0 or any(scores[s] != points[s] for s in points if s != side):
                return None
            if code == 'TD' and delta not in (6, 7, 8):
                return None
            ids.add(play['id'])
            teams[name] += code == 'TD'
            points = scores
        if all(points[s] == int(final[f'{s}_score']) for s in points):
            return teams
    except (KeyError, TypeError, ValueError):
        pass
    return None


def report_rows(snapshots, grades):
    def identity(row, key):
        return (row['season'], row['week'], row['game_id'], key)

    indexed = {identity(row, row['pick_key']): row for row in grades}
    picks, suggestions, original = [], [], set()
    for snapshot in snapshots:
        for index, pick in enumerate(snapshot['picks']):
            key = pick_key(pick, index)
            ident = identity(snapshot, key)
            original.add(ident)
            grade_row = indexed.get(ident, {})
            picks.append({**pick, 'season': snapshot['season'], 'week': snapshot['week'],
                          'game_id': snapshot['game_id'], 'pick_key': key,
                          'kickoff_at': snapshot['kickoff_at'], 'captured_at': snapshot['created_at'],
                          'outcome': grade_row.get('outcome', 'pending'), 'actual_value': grade_row.get('actual_value')})
    for snapshot in snapshots:
        for index, suggestion in enumerate(snapshot['suggested_parlays']):
            leg_grades = {}
            for leg in suggestion['legs']:
                ident = identity(leg, leg['pick_key'])
                if ident not in original:
                    raise ValueError('Suggested leg is missing its frozen capture')
                if ident in indexed:
                    leg_grades[canonical_pick(leg)] = indexed[ident]
            settled = settle_suggestion(suggestion, leg_grades)
            suggestions.append({**suggestion, **settled, 'season': snapshot['season'], 'week': snapshot['week'],
                                'snapshot_id': f"{snapshot['season']}:{snapshot['week']}:{snapshot['game_id']}:{index}"})
    return picks, suggestions


def grade_and_report(db):
    snapshots = list(db.pages(SNAPSHOTS, 'week,game_id'))
    if not all(authentic_snapshot(row) for row in snapshots):
        raise RuntimeError('Non-authentic v4 rows require review')
    if not snapshots:
        return
    stats = db.request(f'nfl_stat_exports?select=csv_text&season=eq.{SEASON}&limit=1')
    records = list(csv.DictReader(io.StringIO(stats[0]['csv_text']))) if stats else []
    grades = list(db.pages(GRADES, 'week,game_id,pick_key'))
    keys = {}
    for row in grades:
        keys.setdefault((row['week'], row['game_id']), []).append(row['pick_key'])
    weeks = sorted({row['week'] for row in snapshots})
    for week in weeks:
        events = nfl_events(week)
        weekly_records = [row for row in records if row.get('week') == str(week)]
        for snapshot in (row for row in snapshots if row['week'] == week):
            game_id = snapshot['game_id']
            event = events.get(game_id, {})
            existing = set(keys.get((week, game_id), ()))
            if len(existing) == len(snapshot['picks']):
                continue
            needs_td = any(p['market'] == 'team_touchdowns' and pick_key(p, i) not in existing
                           for i, p in enumerate(snapshot['picks']))
            final = final_game(event, game_id, needs_td)
            pending = grade_snapshot(snapshot, final, lambda p, s, _: grade(p, s, event, weekly_records),
                                     existing)
            if pending:
                grades.extend(db.request(GRADES + '?on_conflict=season,week,game_id,pick_key', pending))
    publish_reports(db, snapshots, grades)


def publish_reports(db, snapshots, grades):
    if not snapshots:
        return
    picks, suggestions = report_rows(snapshots, grades)
    weeks = sorted({row['week'] for row in snapshots})
    for week in [0, *weeks]:
        bundle = build_view_bundle([p for p in picks if not week or p['week'] == week],
                                   [p for p in suggestions if not week or p['week'] == week])
        db.request(REPORTS + '?on_conflict=season,week',
                   [{'season': SEASON, 'week': week, 'generated_at': utcnow().isoformat(), 'bundle': bundle}],
                   resolution='merge-duplicates')
    print(f'Published TEST reports for {len(snapshots)} games ({len(grades)} final selections)')


def refresh_injuries(db):
    source = f'https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{SEASON}.csv'
    with urlopen(Request(source, headers={'User-Agent': 'NFLParlayAutomation/4.0'}), timeout=60) as response:
        records = injury_rows(response.read().decode('utf-8-sig'), SEASON)
    db.request('nfl_prediction_injuries_v4?on_conflict=season',
               [{'season': SEASON, 'fetched_at': utcnow().isoformat(), 'records': records}],
               resolution='merge-duplicates')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('task', choices=['capture', 'grade', 'injuries'])
    task = parser.parse_args().task
    db = TestDatabase()
    if task == 'capture':
        events = schedule()
        if events:
            publish_capture(db, events)
            snapshots = list(db.pages(SNAPSHOTS, 'week,game_id'))
            publish_reports(db, snapshots, list(db.pages(GRADES, 'week,game_id,pick_key')))
    elif task == 'grade':
        grade_and_report(db)
    else:
        refresh_injuries(db)
