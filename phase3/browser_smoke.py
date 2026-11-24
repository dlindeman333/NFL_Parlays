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
        profile=dict(p.devices['iPhone 13']) if mobile else {'viewport':{'width':1365,'height':844}}
        profile.pop('default_browser_type',None)
        context=browser.new_context(**profile,service_workers='block')
        # Pin the historical model season in this throwaway browser context;
        # otherwise next year's CI would disable the 2026-only model by design.
        context.add_init_script("localStorage.setItem('nflp-production-isolated-v1:nflp-selected-season-v1','2026')")
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
        # The packaged app contains only Week 9/10 schedules. This test blocks
        # all outside network access, so Week 11 must initially show the honest
        # missing-schedule guard. Supply isolated, future-dated SYNTHETIC Week
        # 11 games before asking the app to generate any risk recommendations.
        # No live schedule or user/cloud data is injected or saved.
        page.evaluate("setWk(11)")
        assert 'No verified schedule loaded for Week 11' in page.locator('#bestRiskParlayResults').inner_text()
        page.evaluate("""() => {
          if(!Array.isArray(WKS[10])||WKS[10].length<6)throw Error('Bundled fixtures missing');
          const kickoff=new Date(Date.now()+48*60*60*1000).toISOString();
          WKS[11]=WKS[10].slice(0,8).map((game,index)=>({
            ...game,id:'synthetic-w11-'+index,week:11,date:kickoff,sc:null
          }));
          setWk(11);
        }""")
        assert page.evaluate("WKS[11].length===8 && WKS[11].every(g => !g.sc && Date.parse(g.date)>Date.now())")
        assert page.locator('#filteredParlaySuggestions h3').inner_text().startswith('Best 3-leg')
        assert page.locator('#riskParlayComparison').count()==1
        # The Best risk-based parlays section sits AFTER Potential Plays, and
        # its shortcut lands at the leg/odds selectors (not halfway down picks).
        assert page.locator('#bestRiskParlayControls').count()==1
        assert page.evaluate("document.getElementById('uiPlaysSection').compareDocumentPosition(document.getElementById('uiRiskSection')) & Node.DOCUMENT_POSITION_FOLLOWING")
        if mobile:
            account=page.locator('#topAccountPanel')
            toggle=page.locator('#skipNavToggle')
            drawer=page.locator('#stickySkipNavigation')
            assert page.evaluate("matchMedia('(max-width:700px)').matches"), 'Expected mobile CSS breakpoint'
            print('Mobile overflow diagnostics:', json.dumps(page.evaluate("""() => {
              const w=document.documentElement.clientWidth;
              return {clientWidth:w,scrollWidth:document.documentElement.scrollWidth,
                innerWidth,innerHeight,visualWidth:visualViewport.width,
                visualHeight:visualViewport.height,
                offenders:[...document.querySelectorAll('body *')].map(e=>{
                  const r=e.getBoundingClientRect();
                  return {tag:e.tagName,id:e.id,cls:String(e.className).slice(0,120),
                    left:r.left,right:r.right,width:r.width,position:getComputedStyle(e).position};
                }).filter(r=>r.width>0&&(r.right>w+2||r.left< -2))
                  .sort((a,b)=>b.right-a.right).slice(0,25)};
            }""")),flush=True)
            def tap_skip():
                try:
                    toggle.tap(timeout=8000)
                except Exception:
                    print('Mobile hit-test diagnostics:',json.dumps(page.evaluate('''() => {
                      const e=document.getElementById('skipNavToggle'), r=e.getBoundingClientRect();
                      const chain=[]; for(let n=e;n;n=n.parentElement){const s=getComputedStyle(n);chain.push({id:n.id,tag:n.tagName,position:s.position,zIndex:s.zIndex,pointerEvents:s.pointerEvents,transform:s.transform,rect:n.getBoundingClientRect().toJSON()});}
                      return {width:innerWidth,height:innerHeight,scrollY,visualViewport:visualViewport&&{width:visualViewport.width,height:visualViewport.height,scale:visualViewport.scale},hit:document.elementsFromPoint(r.x+r.width/2,r.y+r.height/2).slice(0,8).map(n=>({tag:n.tagName,id:n.id})),chain};
                    }''')),flush=True)
                    raise
            for expanded in (True,False):
                if (account.get_attribute('open') is not None)!=expanded:
                    account.locator(':scope > summary').tap()
                assert (account.get_attribute('open') is not None)==expanded
                tap_skip()
                assert drawer.get_attribute('open') is not None
                tap_skip()
                assert drawer.get_attribute('open') is None
            tap_skip()
        shortcut=page.locator('#skipNavLinks a[href="#bestRiskParlayControls"]')
        if mobile: shortcut.tap()
        else: shortcut.click()
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
        assert 'Active whole-parlay odds range: 500 through 2000' in page.locator('#riskParlayComparison').inner_text()
        assert not page.locator('#riskParlayHideBelowBreakEven').is_checked()
        page.locator('#riskParlayHideBelowBreakEven').check()
        assert 'Experimental break-even filter ON' in page.locator('#riskParlayComparison').inner_text()
        assert page.locator('#ln').inner_text()==before,'value filter must not change the active slip'
        page.locator('#riskParlayHideBelowBreakEven').uncheck()
        assert 'Show all qualifying odds results' in page.locator('#riskParlayComparison').inner_text()
        if mobile:
            assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+2')
            assert page.evaluate("""() => [...document.querySelectorAll('#bestRiskParlayControls input,#bestRiskParlayControls select,#bestRiskParlayControls button')]
              .every(e => e.getBoundingClientRect().left>=-2&&e.getBoundingClientRect().right<=window.innerWidth+2)""")
        assert not errors,errors
        assert not writes,'browser smoke must never write to a production backend'
        print(('Mobile' if mobile else 'Desktop')+' feature smoke passed; no runtime errors or live writes')
        context.close()
    browser.close()
