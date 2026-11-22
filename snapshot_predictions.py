"""Capture original pregame predictions only in the 30–35 minute kickoff window.

``--check-window`` is read-only and needs neither credentials nor Playwright.
The capture mode requires a production-only service credential and Chromium.
"""
import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

SEASON = int(os.getenv('NFL_SEASON', str(datetime.now(timezone.utc).year)))
MODEL_SEASON = 2026
PRODUCTION = 'https://wpvuunwtyxycqfjwuzkn.supabase.co'
WINDOW_MIN = timedelta(minutes=30)
WINDOW_MAX = timedelta(minutes=35)
# Warm the ephemeral CI runner before the five-minute capture window starts.
# This does not broaden the permitted time of a database INSERT.
PREP_MAX = timedelta(minutes=50)
MAX_WAIT_SECONDS = 20 * 60
ROOT = Path(__file__).resolve().parent
TOP_N = 12
SUPPORTED_STATS = {'passing_yards', 'rushing_yards', 'receiving_yards', 'receptions', 'touchdowns'}
EXCLUDED_INJURIES = {'out', 'doubtful', 'injured reserve', 'ir', 'suspended'}


def credentials():
    """Never use a service credential with a TEST or unexpected backend."""
    base = os.environ.get('SUPABASE_URL', '').rstrip('/')
    if base != PRODUCTION:
        raise ValueError('Production backend mismatch; no records written')
    key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
    if not key:
        raise ValueError('Missing service credential; no records written')
    return base, key


def fetch(url, *, service=False):
    headers = {'User-Agent': 'NFLParlayAutomation/1.0'}
    if service:
        _, key = credentials()
        headers.update({'apikey': key, 'Authorization': 'Bearer ' + key})
    with urlopen(Request(url, headers=headers), timeout=40) as r:
        return json.load(r)


def within_capture_window(kickoff, now):
    """Use the same inclusive bounds at discovery and immediately before POST."""
    if kickoff.tzinfo is None or now.tzinfo is None:
        return False
    return WINDOW_MIN <= kickoff - now <= WINDOW_MAX


def schedule(now=None, *, max_lead=WINDOW_MAX):
    now = now if now is not None else datetime.now(timezone.utc)
    if not WINDOW_MIN <= max_lead <= PREP_MAX:
        raise ValueError('Unexpected pregame preparation window')

    def fetch_week(week):
        url = f'https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?dates={SEASON}&seasontype=2&week={week}&limit=100'
        return week, fetch(url)

    result = []
    # Four workers minimize 18-week ESPN lookup latency without a burst of 18
    # requests. If any request fails, the preflight fails closed.
    with ThreadPoolExecutor(max_workers=4) as pool:
        for week, data in pool.map(fetch_week, range(1, 19)):
            for e in data.get('events', []):
                comp = (e.get('competitions') or [{}])[0]
                teams = {x.get('homeAway'): x.get('team', {}).get('abbreviation') for x in comp.get('competitors', [])}
                kickoff = datetime.fromisoformat(e['date'].replace('Z', '+00:00'))
                if not WINDOW_MIN <= kickoff - now <= max_lead:
                    continue
                if e.get('status', {}).get('type', {}).get('state') != 'pre':
                    continue
                result.append({'week': week, 'id': str(e['id']), 'a': teams.get('away'), 'h': teams.get('home'), 'kickoff': kickoff.isoformat()})
    return result


def emit_eligibility(eligible):
    output = os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output, 'a', encoding='utf-8') as fp:
            fp.write('eligible=' + str(eligible).lower() + '\n')


def check_window(*, preparation=False):
    """Output the GitHub Actions eligibility flag without reading cloud data."""
    if SEASON != MODEL_SEASON:
        raise RuntimeError(f'Pregame capture is disabled for season {SEASON}; model inputs require validation')
    events = schedule(max_lead=PREP_MAX) if preparation else schedule()
    eligible = bool(events)
    emit_eligibility(eligible)
    window = '30–50 minute preparation' if preparation else '30–35 minute capture'
    print(f'{window} window: {len(events)} eligible game(s); '
          + ('runner may prepare' if preparation and eligible else
             'capture may proceed' if eligible else 'no eligible game'))
    return eligible


def wait_for_window(*, clock=None, sleeper=None):
    """Read-only preparation; revalidate the *strict* window after warming CI."""
    if SEASON != MODEL_SEASON:
        raise RuntimeError(f'Pregame capture disabled for unvalidated season {SEASON}')
    clock = clock or (lambda: datetime.now(timezone.utc))
    sleeper = sleeper or time.sleep
    now = clock()
    upcoming = schedule(now, max_lead=PREP_MAX)
    if not upcoming:
        emit_eligibility(False)
        print('No pregame event remains in the preparation window.')
        return False
    # The earliest qualifying game determines when this run may first capture.
    kickoffs = [datetime.fromisoformat(e['kickoff']) for e in upcoming]
    target = min(kickoffs) - WINDOW_MAX + timedelta(seconds=1)
    remaining = max(0, (target - now).total_seconds())
    if remaining > MAX_WAIT_SECONDS:
        emit_eligibility(False)
        print('Preparation would exceed the bounded wait; no capture attempted.')
        return False
    wait_budget = MAX_WAIT_SECONDS
    while remaining > 0:
        # Wall clocks can jump. A separate sleep budget guarantees a bound even
        # if time stops advancing or is moved backward during preparation.
        if wait_budget <= 0:
            emit_eligibility(False)
            print('Preparation wait exhausted; no capture attempted.')
            return False
        delay = min(remaining, 30, wait_budget)
        sleeper(delay)
        wait_budget -= delay
        remaining = max(0, (target - clock()).total_seconds())
    eligible = bool(schedule(clock()))
    emit_eligibility(eligible)
    print('Strict pregame recheck:', 'eligible for guarded capture' if eligible else 'no eligible games; skip capture')
    return eligible


def select_top12(candidates, reports, week):
    """Freeze ranked, unique, supported picks; filter injuries before Top 12 cap."""
    from phase3.automation import team
    if not isinstance(reports, list):
        raise ValueError('Injury records unavailable; no capture')
    selected, seen = [], set()
    for pick in candidates:
        if pick.get('market') != 'player' or pick.get('stat') not in SUPPORTED_STATS:
            continue
        if pick.get('side') not in ('o', 'u') or not str(pick.get('player_name') or '').strip():
            continue
        if not isinstance(pick.get('line'), (int, float)) or not isinstance(pick.get('probability'), (int, float)):
            continue
        if not 0 <= pick['probability'] <= 1:
            continue
        identity = (team(pick.get('team')), str(pick['player_name']).casefold(),
                    pick['stat'], pick['side'], pick['line'])
        if identity in seen:
            continue
        matching = [r for r in reports if str(r.get('week')) == str(week)
                    and team(r.get('team')) == team(pick.get('team'))
                    and str(r.get('player', '')).casefold() == str(pick['player_name']).casefold()]
        statuses = {str(r.get('status', '')).strip().casefold() for r in matching}
        if statuses & EXCLUDED_INJURIES:
            continue
        seen.add(identity)
        selected.append({**pick,
                         'injury_status': ', '.join(sorted(statuses)) if statuses else 'unknown / no matching weekly report',
                         'injury_report_week': week})
        if len(selected) == TOP_N:
            break
    return selected


def main():
    if SEASON != MODEL_SEASON:
        raise RuntimeError(f"Pregame snapshots disabled for {SEASON}: browser model inputs are still based on {MODEL_SEASON}. Update and validate the model before archiving forecasts.")
    events = schedule()
    if not events:
        print('No games 30–35 minutes from kickoff; nothing to capture.')
        return
    base, key = credentials()
    existing = fetch(base + f'/rest/v1/nfl_prediction_snapshots_v2?select=week,game_id&season=eq.{SEASON}', service=True)
    seen = {(int(x['week']), x['game_id']) for x in existing}
    pending = [e for e in events if (e['week'], e['id']) not in seen]
    if not pending:
        print('All eligible games already have immutable snapshots.')
        return
    stats = fetch(base + f'/rest/v1/nfl_stat_exports?select=csv_text,generated_at&season=eq.{SEASON}&limit=1', service=True)
    if not stats or not stats[0].get('csv_text'):
        raise RuntimeError('No cloud NFL statistics available. Run export_automated.py first.')
    generated = datetime.fromisoformat(stats[0]['generated_at'].replace('Z', '+00:00'))
    if (datetime.now(timezone.utc)-generated).total_seconds() > 48*3600:
        raise RuntimeError('Stats export is stale; no snapshots published')
    injury_data = fetch(base + f'/rest/v1/nfl_injury_reports_v2?select=*&season=eq.{SEASON}', service=True)
    if not injury_data:
        raise RuntimeError('Run injury refresh before capturing forecasts')
    reports = injury_data[0]
    if (datetime.now(timezone.utc)-datetime.fromisoformat(reports['fetched_at'].replace('Z','+00:00'))).total_seconds() > 24*3600:
        raise RuntimeError('Injury refresh is stale; no snapshots published')
    html = ROOT / 'index.html'
    if not html.exists():
        raise RuntimeError('Place the updated app in the repository as index.html')
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(html.as_uri(), wait_until='domcontentloaded', timeout=60000)
        page.evaluate('(csv) => loadCSV(csv, {persist:false})', stats[0]['csv_text'])
        for e in pending:
            if not e['a'] or not e['h']:
                continue
            result = page.evaluate('''e => {
              const a=normalizeTeam(e.a),h=normalizeTeam(e.h);
              if(!T[a]||!T[h])return null;
              const g=build([['espn'+e.id,a,h,'Scheduled',null]])[0];
              const candidates=window.phase4Top12GameCandidates(g);
              const stats={ps:'passing_yards',ru:'rushing_yards',rec:'receiving_yards',
                rcp:'receptions',td:'touchdowns'};
              const picks=candidates.map(x=>{
                const p=x.p,side=advancedPickSide(x),probability=side==='u'?1-x.prob:x.prob;
                return {away_team:a,home_team:h,market:'player',side,
                  probability,model_line:x.line,
                  label:p.n+' '+(side==='u'?'Under ':'Over ')+x.line+' '+stats[p.k],
                  player_name:p.n,team:p.tm,stat:stats[p.k],
                  line:p.k==='td'?0.5:Number(x.line)};
              });
              return {away_team:a,home_team:h,picks};
            }''', e)
            if not result or not result['picks']:
                continue
            # Filter excluded injuries BEFORE the limit, filling from next-ranked picks.
            filtered=select_top12(result['picks'], reports['records'], e['week'])
            if not filtered: continue
            # Browser startup and model evaluation can take several minutes.
            # The database independently enforces the 30-minute minimum.
            kickoff = datetime.fromisoformat(e['kickoff'])
            if not within_capture_window(kickoff, datetime.now(timezone.utc)):
                print('Skipped', e['id'], ': capture window elapsed during processing')
                continue
            row = {'season': SEASON, 'week': e['week'], 'game_id': e['id'],
                   'away_team': result['away_team'], 'home_team': result['home_team'],
                   'kickoff_at': e['kickoff'], 'model_version': 'browser-model-2026-phase3-top12-v1',
                   'picks': filtered}
            request = Request(base + '/rest/v1/nfl_prediction_snapshots_v2?on_conflict=season,week,game_id',
                              data=json.dumps(row).encode(), method='POST',
                              headers={'apikey': key, 'Authorization': 'Bearer '+key,
                                       'Content-Type': 'application/json',
                                       'Prefer': 'resolution=ignore-duplicates,return=minimal'})
            try:
                with urlopen(request, timeout=40) as r:
                    print('Archived Top 12 week', e['week'], result['away_team'], '@', result['home_team'],
                          len(filtered), 'picks; HTTP', r.status)
            except HTTPError as err:
                raise RuntimeError(f'Prediction snapshot upload HTTP {err.code}: {err.read().decode()[:500]}') from err
        browser.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check-window', action='store_true',
                        help='Read-only kickoff-window check for scheduled capture')
    parser.add_argument('--check-prep-window', action='store_true',
                        help='Read-only 30–50 minute runner preparation check')
    parser.add_argument('--wait-for-window', action='store_true',
                        help='Wait at most 20 minutes then recheck 30–35 minute window')
    args = parser.parse_args()
    if sum((args.check_window, args.check_prep_window, args.wait_for_window)) > 1:
        parser.error('Select only one read-only window mode')
    if args.check_window:
        check_window()
    elif args.check_prep_window:
        check_window(preparation=True)
    elif args.wait_for_window:
        wait_for_window()
    else:
        main()
