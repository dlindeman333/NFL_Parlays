"""Exercise identical authenticated TEST report reads on desktop and mobile."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from phase3.comprehensive_worker import freeze_cohort

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://dlindeman333.github.io/NFL_Parlays_Test/'
TEST_URL = 'https://luxezjthznupdghmexyh.supabase.co/'
IDENTITY = '00000000-0000-4000-8000-000000000001'
ACCOUNT = {'id': IDENTITY, 'email': 'synthetic@example.invalid'}
BUNDLE = {
    'schema_version': 4,
    'dashboard': {'individual': [{'category': 'top12', 'market': 'all',
        'graded_decisions': 1, 'hit_rate': 1, 'hit': 1, 'miss': 0}], 'suggested_parlays': []},
    'workbook_tables': {'AI Performance': [], 'AI Prediction Details': [
        {'week': 12, 'label': 'Synthetic pick', 'outcome': 'hit', 'actual_value': 10}]},
}


def route(request_route):
    request = request_route.request
    if request.url.startswith(ORIGIN):
        path = request.url.removeprefix(ORIGIN).split('?', 1)[0]
        request_route.fulfill(path=ROOT / path)
    elif request.url.startswith(TEST_URL):
        headers = {'access-control-allow-origin': '*',
                   'access-control-allow-headers': 'apikey, authorization, content-type'}
        if request.method == 'OPTIONS':
            request_route.fulfill(status=204, headers=headers)
            return
        assert request.method == 'GET'
        body = []
        if '/auth/v1/user' in request.url:
            body = ACCOUNT
        if '/nfl_prediction_reports_v4?' in request.url:
            assert request.headers.get('authorization') == 'Bearer synthetic-access'
            week = 0 if 'week=eq.0' in request.url else 12
            body = [{'season': 2026, 'week': week, 'generated_at': '2026-11-26T14:00:00Z', 'bundle': BUNDLE}]
        request_route.fulfill(status=200, headers=headers, content_type='application/json', body=json.dumps(body))
    else:
        request_route.abort()



def verify_browser_capture(page):
    teams = [('BUF', 'KC'), ('DET', 'PHI')]
    fields = ['season','week','name','team','pos','game_status','opponent_team',
              'passing_yards','passing_attempts','rushing_yards','rushing_attempts',
              'receiving_yards','receptions','targets','touchdowns','snap_share']
    lines = [','.join(fields)]
    for a, h in teams:
        for t, opp in [(a, h), (h, a)]:
            for index, pos in enumerate(['QB','RB','WR','WR','TE']):
                for week in (8, 9, 10, 11):
                    row = [2026,week,f'Synthetic {t} Player {index}',t,pos,'COMPLETED',opp,
                           220+week if pos=='QB' else 0,28 if pos=='QB' else 0,
                           55+week if pos=='RB' else 0,15 if pos=='RB' else 0,
                           40+week if pos!='QB' else 0,5,8,1,0.75]
                    lines.append(','.join(map(str, row)))
    page.evaluate('(csv) => loadCSV(csv, {persist:false})', '\n'.join(lines))
    now = datetime(2026, 11, 26, 16, tzinfo=timezone.utc)
    kickoff = (now + timedelta(minutes=32)).isoformat()
    events = [dict(a=a,h=h,id=str(index+1),week=12,kickoff=kickoff)
              for index,(a,h) in enumerate(teams)]
    snapshots = freeze_cohort(page, events, [], now)
    assert len(snapshots) == 2
    for snapshot in snapshots:
        assert sum(pick['legacy_player_top12'] for pick in snapshot['picks']) == 12
        assert any(parlay['kind'] == 'same' for parlay in snapshot['suggested_parlays'])
    multi = [p for p in snapshots[0]['suggested_parlays'] if p['kind'] == 'multi']
    assert multi and not any(p['kind'] == 'multi' for p in snapshots[1]['suggested_parlays'])
    assert {leg['game_id'] for leg in multi[0]['legs']} == {'1', '2'}
    print('PASS: actual browser model freezes Top 12, same-game and same-kickoff multi-game selections')


def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for width, height in [(1440, 900), (390, 844)]:
            context = browser.new_context(viewport={'width': width, 'height': height}, accept_downloads=True)
            context.route('**/*', route)
            context.add_init_script("""(() => {
                if(!location.href.startsWith('https://dlindeman333.github.io/NFL_Parlays_Test/'))return;
                const p='nflp-v4-test-isolated-v1:';
                localStorage.setItem(p+'nflp-v4-test-auth-auth',JSON.stringify({
                  access_token:'synthetic-access',refresh_token:'synthetic-refresh',expiresAt:Date.now()+3600000}));
                localStorage.setItem(p+'nflp-phase3-prod-storage-owner-v1','"""+IDENTITY+"""');
                localStorage.setItem(p+'nflp-selected-season-v1','2026');
            })();""")
            page = context.new_page()
            page.goto(ORIGIN + 'index.html', wait_until='domcontentloaded')
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.wait_for_function('window.phase3VerifiedSuggestionAccountId?.()', timeout=10000)
            page.evaluate("""() => {
                wk=12;
                document.body.classList.remove('phase3-privacy-locked');
                document.getElementById('advTabPerformance').click();
                document.getElementById('comprehensiveCloudPanel').open=true;
            }""")
            page.locator('#comprehensiveCloudStatus').filter(has_text='Week 12 · Cloud report updated').wait_for()
            assert page.locator('#comprehensiveCloudReport strong').first.text_content() == '100.0%'
            page.locator('#comprehensiveCloudScope').select_option('season')
            page.locator('#comprehensiveCloudStatus').filter(has_text='Season 2026 · Cloud report updated').wait_for()
            with page.expect_download() as download:
                page.locator('#comprehensiveCloudExport').evaluate('(button)=>button.click()')
            assert download.value.suggested_filename == 'NFL_AI_Predictions_2026.xlsx'
            page.evaluate("document.dispatchEvent(new Event('phase3-account-signed-out'))")
            assert page.locator('#comprehensiveCloudExport').is_disabled()
            assert not errors, errors
            if width == 1440:
                verify_browser_capture(page)
            context.close()
        browser.close()
    print('PASS: authenticated report, scope, export and sign-out at desktop and iPhone widths')


if __name__ == '__main__':
    main()
