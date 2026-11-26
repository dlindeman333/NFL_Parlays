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
        # Signed-out status must not expose another account's last sync time.
        indicator=page.locator('#guardedSyncIndicator')
        indicator.wait_for(state='attached')
        assert indicator.inner_text()=='Cloud sync: sign-in verification required'
        assert 'Last verified:' not in indicator.inner_text()
        print('Signed-out synchronization status privacy passed',flush=True)
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
          populateWeeks();
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
          const expected=(window.innerWidth>=701?nav.getBoundingClientRect().height:0)+document.getElementById('quickFiltersBar').getBoundingClientRect().height+12;
          return box&&Math.abs(box.getBoundingClientRect().top-expected)<40;
        }""")
        weather_button=page.get_by_role('button',name='Weather',exact=True).first
        weather_game=weather_button.get_attribute('data-weather-game')
        weather_button=page.locator(f'[data-weather-game="{weather_game}"]')
        if mobile: weather_button.tap()
        else: weather_button.click()
        weather=page.get_by_role('dialog',name='Game weather')
        assert weather.is_visible()
        matchup=page.evaluate("id => {const g=games.find(x=>String(x.id)===id);return g.a+' @ '+g.h}",weather_game)
        assert weather.locator('#gameWeatherMatchup').inner_text()==matchup
        condition=weather.get_by_label('Wind',exact=True)
        precipitation=weather.get_by_label('Heavy precipitation')
        assert weather.locator('.game-weather-precipitation').evaluate("""label => {
          const wind=label.previousElementSibling.getBoundingClientRect();
          const row=label.getBoundingClientRect();
          const checkbox=label.querySelector('input').getBoundingClientRect();
          const text=label.querySelector('span').getBoundingClientRect();
          return row.top>=wind.bottom && Math.abs(row.left-wind.left)<2 &&
            checkbox.right<=text.left && checkbox.top<text.bottom && text.top<checkbox.bottom;
        }""")
        assert condition.input_value()=='none'
        condition.select_option('wind')
        precipitation.check()
        apply_weather=weather.get_by_role('button',name='Apply to recommendations')
        apply_weather.click()
        assert 'applied' in weather.get_by_role('status').inner_text()
        assert weather_button.inner_text()=='Weather applied'
        assert page.get_by_role('button',name='Weather applied',exact=True).count()==1
        weather.get_by_role('button',name='Close',exact=True).click()
        assert page.evaluate("""id => {
          const select=document.getElementById('phase4WeatherGame');
          select.value=id;
          select.dispatchEvent(new Event('change'));
          return document.getElementById('phase4WeatherCondition').value==='wind' && document.getElementById('phase4WeatherWet').checked;
        }""",weather_game)
        weather_button.click()
        assert condition.input_value()=='wind'
        assert precipitation.is_checked()
        precipitation.uncheck()
        condition.select_option('none')
        apply_weather.click()
        assert 'cleared' in weather.get_by_role('status').inner_text()
        assert weather_button.inner_text()=='Weather'
        assert page.locator('#phase4WeatherCondition').input_value()=='none'
        assert not page.locator('#phase4WeatherWet').is_checked()
        weather.get_by_role('button',name='Close',exact=True).click()
        print('Game card weather checks passed',flush=True)
        game_button=page.locator('[id^="more-picks-button-"]').first
        game_id=game_button.get_attribute('id').removeprefix('more-picks-button-')
        game_button.click()
        panel=page.locator('[id="more-picks-'+game_id+'"]')
        assert panel.is_visible()
        rows=panel.locator('.more-pick-row')
        total=rows.count()
        assert total>0
        assert page.evaluate("id => sortedMorePicks(games.find(g=>String(g.id)===id)).filter(x=>!x.player||!phase3PlayerOut(x.player)).length",game_id)==total
        for label in ('Market','Position','Team'):
            control=panel.get_by_role('combobox',name=label,exact=True)
            assert control.count()==1
            options=control.locator('option').all()
            if len(options)>1:
                control.select_option(options[1].get_attribute('value'))
                assert rows.count()<=total
                panel.get_by_role('button',name='Reset Filters',exact=True).click()
                assert rows.count()==total
        panel.get_by_role('button',name='Collapse All',exact=True).click()
        assert rows.count()==0
        panel.get_by_role('button',name='Expand All',exact=True).click()
        assert rows.count()==total
        if mobile:
            assert page.evaluate("id => [...document.getElementById('more-picks-'+id).querySelectorAll('select,button')].every(e=>{const r=e.getBoundingClientRect();return !r.width||(r.left>=-2&&r.right<=document.documentElement.clientWidth+2)})",game_id)
        assert page.evaluate("""id => {
          const g=games.find(x=>String(x.id)===id);
          const best=new Set(gameBestPickRows(g).slice(0,8).map(x=>x.mk+'|'+x.sd));
          const suggested=new Set(phase4Top12GameCandidates(g).slice(0,12).filter(x=>!x.manual).map(x=>'p'+x.p.i+'|'+advancedPickSide(x)));
          const rows=[...document.getElementById('more-picks-'+id).querySelectorAll('.more-pick-row')];
          return rows.every(row=>{
            const key=row.dataset.pickKey.split('|').slice(1).join('|');
            return row.textContent.includes('Suggested Pick')===(best.has(key)||suggested.has(key));
          });
        }""",game_id)
        slip_before=page.locator('#ln').inner_text()
        for label in ('Market','Position','Team'):
            control=panel.get_by_role('combobox',name=label,exact=True)
            options=control.locator('option').all()
            if len(options)>1:
                control.select_option(options[1].get_attribute('value'))
        assert page.evaluate("""id => {
          const g=games.find(x=>String(x.id)===id),f=allPickFilters.get(gamePicksKey(id))||{};
          const expected=sortedMorePicks(g).filter(x=>(!x.player||!phase3PlayerOut(x.player))&&(!f.market||allPickMarket(x)===f.market)&&(!f.position||x.position===f.position)&&(!f.team||allPickTeam(x)===f.team)).map(x=>x.key).sort();
          const actual=[...document.getElementById('more-picks-'+id).querySelectorAll('.more-pick-row')].map(x=>x.dataset.pickKey).sort();
          return JSON.stringify(expected)===JSON.stringify(actual);
        }""",game_id)
        assert page.locator('#ln').inner_text()==slip_before
        panel.get_by_role('button',name='Reset Filters',exact=True).click()
        assert rows.count()==total
        game_button.click()
        assert panel.count()==0
        print('All Picks acceptance checks passed',flush=True)
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
        # Four completed team weeks, with one receiver missing the latest game.
        page.evaluate("""id => {
          const g=games.find(game=>String(game.id)===id);
          const header='player,team,week,season,game_status,position,targets,receptions,receiving_yards,snap_share';
          const rows=[header];
          for(const week of [7,8,9,10]){
            rows.push(['Fixture Current',g.a,week,2026,'COMPLETED','WR',6,4,45,.65].join(','));
            if(week!==10)rows.push(['Fixture Recent Absence',g.a,week,2026,'COMPLETED','WR',6,4,45,.65].join(','));
            if(week>=9)rows.push(['Fixture Thin',g.a,week,2026,'COMPLETED','WR',6,4,45,.65].join(','));
          }
          loadCSV(rows.join(String.fromCharCode(10)),{persist:false});
          const current=PLY.find(p=>p.n==='Fixture Current'&&p.k==='rec');
          const absent=PLY.find(p=>p.n==='Fixture Recent Absence'&&p.k==='rec');
          const thin=PLY.find(p=>p.n==='Fixture Thin'&&p.k==='rec');
          if(!reliablePlayerUsage(current,'u')||!reliablePlayerUsage(absent,'o')||
             reliablePlayerUsage(absent,'u')||reliablePlayerUsage(thin,'o'))throw Error('Participation/UNDER policy');
          if(!phase4Top12GameCandidates(g).some(x=>x.p===current))throw Error('Capture uses the same eligible player pool');
          window.captureFixture=phase4Top12GameCandidates(g).map(x=>[x.p.i,x.line,advancedPickSide(x)]);
        }""",game_id)
        if page.locator('#qfCollapse').get_attribute('open') is None:
            page.locator('#qfCollapseToggle').click()
        page.locator('#qfSportsbook').select_option('DraftKings')
        assert page.evaluate("id => gamePickCandidates(games.find(g=>g.id===id)).length===0",game_id)
        game_button.click()
        editor=page.locator('#verify-book-'+game_id)
        selected=editor.locator('select[name=selection] option').filter(has_text='Fixture Current Over').first
        selection=selected.get_attribute('value')
        editor.locator('select[name=selection]').select_option(selection)
        editor.get_by_role('button',name='Confirm exact selection').click()
        assert 'confirmation saved' in editor.get_by_role('status').inner_text()
        assert page.evaluate("""id => {
          const game=games.find(g=>g.id===id);
          const [pick]=gamePickCandidates(game);
          if(!pick||gamePickCandidates(game).length!==1||!pick.player||pick.side!=='o')return false;
          const line=pstat(pick.player,game).line;
          return !sportsbookAllows(game,pick.mkt,'u',line)&&!sportsbookAllows(game,pick.mkt,'o',line+1)&&
            !sportsbookAllows({...game,date:new Date(Date.parse(game.date)+60000).toISOString()},pick.mkt,'o',line)&&
            !currentBookLine(Date.now()-BOOK_LINE_MAX_AGE)&&
            JSON.stringify(phase4Top12GameCandidates(game).map(x=>[x.p.i,x.line,advancedPickSide(x)]))===JSON.stringify(window.captureFixture);
        }""",game_id)
        page.locator('#qfSportsbook').select_option('FanDuel')
        assert page.evaluate("id => gamePickCandidates(games.find(g=>g.id===id)).length===0",game_id)
        page.locator('#qfSportsbook').select_option('DraftKings')
        if not mobile:
            assert page.evaluate('document.getElementById("quickFiltersBar").getBoundingClientRect().top>=document.getElementById("stickySkipNavigation").getBoundingClientRect().bottom-1')
        shots=os.environ.get('NFL_GUIDE_SCREENSHOTS')
        if shots:
            page.locator('#quickFiltersBar').screenshot(path=f'{shots}/filters-{"iphone" if mobile else "desktop"}.png')
            editor.locator('select[name=selection]').select_option(selection)
            editor.screenshot(path=f'{shots}/verify-{"iphone" if mobile else "desktop"}.png',
                              style='#floatingBackToTop,#stickySkipNavigation,#phase3MobileSlipToggle,#quickFiltersBar { visibility:hidden !important; }')
        page.locator('#qfCollapseToggle').click()
        editor.locator('select[name=selection]').select_option(selection)
        editor.get_by_role('button',name='Remove confirmation').click()
        page.locator('#qfCollapseToggle').click()
        assert page.evaluate("id => gamePickCandidates(games.find(g=>g.id===id)).length===0",game_id)
        page.locator('#qfUnder').uncheck()
        assert page.evaluate("reliablePlayerUsage(PLY.find(p=>p.n==='Fixture Recent Absence'&&p.k==='rec'),'u')")
        page.locator('#qfAdvancedButton').click()
        page.wait_for_function("phase3LocalStorage.getItem('nflp-quick-filter-advanced-v1')==='expanded'")
        page.locator('#qfPresetName').fill('DraftKings test')
        page.locator('#qfSavePreset').click()
        page.locator('#qfClear').click()
        assert page.locator('#qfUnder').is_checked()
        page.locator('#qfLoadPreset').click()
        assert page.locator('#qfSportsbook').input_value()=='DraftKings'
        assert not page.locator('#qfUnder').is_checked()
        page.reload(wait_until='domcontentloaded')
        assert page.locator('#qfCollapse').get_attribute('open') is not None
        assert page.locator('#qfAdvanced').get_attribute('open') is not None
        assert page.locator('#qfSportsbook').input_value()=='DraftKings'
        assert not page.locator('#qfUnder').is_checked()
        print('Participation, sportsbook evidence, capture isolation and persistent filters passed',flush=True)
        assert not errors,errors
        assert not writes,'browser smoke must never write to a production backend'
        print(('Mobile' if mobile else 'Desktop')+' feature smoke passed; no runtime errors or live writes')
        context.close()
    browser.close()
