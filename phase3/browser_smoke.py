"""One desktop/mobile browser smoke check using synthetic data; no live writes."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

html=(Path(__file__).resolve().parents[1]/'index.html').read_text()
with sync_playwright() as p:
    # CI uses Playwright's installed Chromium; local reviewers may supply an
    # already-installed system Chromium without downloading another browser.
    executable=os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE')
    browser=p.chromium.launch(executable_path=executable) if executable else p.chromium.launch()
    for mobile in (False,True):
        context=browser.new_context(viewport={'width':390 if mobile else 1365,'height':844},is_mobile=mobile,has_touch=mobile,service_workers='block')
        errors=[]; writes=[]
        def route(request_route):
            request=request_route.request
            if request.url.startswith('https://dlindeman333.github.io/NFL_Parlays/'):
                return request_route.fulfill(body=html,content_type='text/html')
            if '.supabase.co/rest/v1/' in request.url:
                if request.method!='GET': writes.append(request.url)
                rows=[]
                if '/nfl_injury_reports_v2?' in request.url:
                    rows=[{'season':2026,'fetched_at':datetime.now(timezone.utc).isoformat(),'latest_week':10,'records':[
                        {'week':10,'team':'BUF','player':'Synthetic Player','status':'Out','injury':'Ankle','practice':'Did Not Participate'}]}]
                return request_route.fulfill(body=json.dumps(rows),content_type='application/json')
            return request_route.abort()
        context.route('**/*',route)
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        page.goto('https://dlindeman333.github.io/NFL_Parlays/index.html',wait_until='domcontentloaded')
        page.wait_for_function("window.phase3InjuryLabel && window.phase3InjuryLabel('Synthetic Player','BUF',10).includes('Out')")
        assert not errors,errors
        assert not writes,writes
        assert page.get_by_role('button',name='Track upcoming predictions in my account',include_hidden=True).count()==1
        assert page.evaluate("window.phase3InjuryLabel('Missing Player','BUF',10).includes('unconfirmed')")
        # This test deliberately has no authenticated account. Reveal the local
        # UI only for layout checks; it does NOT prove cloud sign-in or RLS.
        page.evaluate("document.body.classList.remove('phase3-privacy-locked')")
        # The Best risk-based parlays section sits AFTER Potential Plays, and
        # its shortcut lands at the leg/odds selectors (not halfway down picks).
        assert page.locator('#bestRiskParlayControls').count()==1
        assert page.evaluate("document.getElementById('uiPlaysSection').compareDocumentPosition(document.getElementById('uiRiskSection')) & Node.DOCUMENT_POSITION_FOLLOWING")
        if mobile: page.locator('#skipNavToggle').click()
        page.locator('#skipNavLinks a[href="#bestRiskParlayControls"]').click()
        page.wait_for_function("""() => {
          const box=document.getElementById('bestRiskParlayControls');
          const nav=document.getElementById('stickySkipNavigation');
          const expected=window.innerWidth>=701?nav.getBoundingClientRect().height+12:10;
          return box&&Math.abs(box.getBoundingClientRect().top-expected)<40;
        }""")
        before=page.locator('#ln').inner_text()
        page.locator('#riskParlayLegs').select_option('4')
        page.locator('#riskParlayFrom').fill('500')
        page.locator('#riskParlayThrough').fill('2000')
        page.locator('#riskParlayApply').click()
        assert 'Showing 4-leg options' in page.locator('#riskParlayStatus').inner_text()
        assert page.locator('#ln').inner_text()==before,'exploration must not change the active slip'
        assert page.locator('#filteredParlaySuggestions h3').inner_text().startswith('Best 4-leg')
        assert page.locator('#riskParlayComparison').count()==1
        for leg_count in (3,4,5,6):
            assert page.locator(f'[data-risk-comparison="{leg_count}"]').count()==1
        if mobile:
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2')
            assert page.evaluate("""() => [...document.querySelectorAll('#bestRiskParlayControls input,#bestRiskParlayControls select,#bestRiskParlayControls button')]
              .every(e => e.getBoundingClientRect().left>=-2&&e.getBoundingClientRect().right<=window.innerWidth+2)""")
        print(('Mobile' if mobile else 'Desktop')+' feature smoke passed; no runtime errors or live writes')
        context.close()
    browser.close()
