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
        if mobile: assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2')
        print(('Mobile' if mobile else 'Desktop')+' feature smoke passed; no runtime errors or live writes')
        context.close()
    browser.close()
