"""Offline real-browser verification; synthetic data only, no cloud requests."""
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent
with sync_playwright() as p:
    browser=p.chromium.launch()
    for width,height in [(1440,900),(390,844)]:
        page=browser.new_page(viewport={'width':width,'height':height})
        page.route('**/*',lambda route:route.abort())
        page.set_content('<main id="report" style="max-width:100%;overflow-wrap:anywhere"></main>')
        for name in ('comprehensive_dashboard_review.js','comprehensive_workbook_review.js','comprehensive_view_review.js'):
            page.add_script_tag(content=(ROOT/name).read_text())
        sheets=page.evaluate("""() => mountComprehensiveReview(document.querySelector('#report'),{
            schema_version:4,
            dashboard:{individual:[{category:'top12',market:'all',graded_decisions:4,hit_rate:.75,hit:3,miss:1},{category:'recommended',market:'all',graded_decisions:2,hit_rate:.5,hit:1,miss:1}],suggested_parlays:[]},
            workbook_tables:{'AI Performance':[{hit_rate:.75}],'Suggested Legs':[]}
        },[['Legacy',[['Original']]]])""")
        assert len(sheets)==3
        cards=page.locator('#report section')
        assert cards.count()==4
        assert cards.nth(0).locator('strong').inner_text()=='75.0%'
        assert cards.nth(0).locator('strong').evaluate('(e)=>getComputedStyle(e).color')=='rgb(36, 151, 91)'
        assert cards.nth(1).locator('strong').evaluate('(e)=>getComputedStyle(e).color')=='rgb(181, 139, 22)'
        assert cards.nth(2).locator('strong').inner_text()=='Not yet graded'
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        page.close()
        print(f'PASS: Chromium reporting fixture {width}x{height}')
    browser.close()

# Exercise the actual application entry point, with all external requests blocked.
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from functools import partial
from threading import Thread
server=ThreadingHTTPServer(('127.0.0.1',0),partial(SimpleHTTPRequestHandler,directory=str(ROOT.parent)))
Thread(target=server.serve_forever,daemon=True).start()
origin=f'http://127.0.0.1:{server.server_port}'
try:
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for width,height in [(1440,900),(390,844)]:
            page=browser.new_page(viewport={'width':width,'height':height},accept_downloads=True)
            page.route('**/*',lambda route:route.continue_() if route.request.url.startswith(origin+'/') else route.abort())
            page.goto(origin+'/index.html',wait_until='domcontentloaded')
            assert page.locator('#comprehensiveReviewPanel').is_hidden()
            assert page.evaluate('typeof window.mountOfflineComprehensiveReview')=='undefined'
            page.goto(origin+'/index.html?comprehensiveReview=1',wait_until='domcontentloaded')
            assert page.evaluate("""() => mountOfflineComprehensiveReview({schema_version:4,dashboard:{individual:[],suggested_parlays:[]},workbook_tables:{'AI Performance':[]}})""")==1
            assert page.locator('#advTrackingResults').count()==1
            page.evaluate("""() => {document.querySelector('#advPerformancePanel').hidden=false;document.querySelector('#comprehensiveReviewPanel').open=true}""")
            assert page.locator('#comprehensiveReviewReport section').count()==4
            with page.expect_download() as download:
                page.locator('#comprehensiveReviewExport').evaluate('(e)=>e.click()')
            assert download.value.suggested_filename=='SYNTHETIC_Comprehensive_Review.xlsx'
            page.close()
            print(f'PASS: actual application review gate and export {width}x{height}')
        browser.close()
finally:
    server.shutdown()
    server.server_close()
