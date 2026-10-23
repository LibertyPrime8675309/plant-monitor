"""Checks the plant timeline and photo comparison. Start the mock server first (a data folder that has been through a
few upgrades shows more history), then:  python3 dev/test/timeline_check.py [base-url] [plant-code]
Screenshots: dev/tmp/shots/timeline-*.png"""
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
CODE = sys.argv[2] if len(sys.argv) > 2 else 'P-024'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900}); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Timeline Test');localStorage.setItem('plantdb.display',JSON.stringify({layout:'single',navopen:'0'}))")
    pg.goto(f'{BASE}/#/plant/{CODE}'); pg.wait_for_timeout(2500)
    check(pg.locator('#tl-box .tl-item').count() > 0, f"{pg.locator('#tl-box .tl-item').count()} timeline entries")
    check(pg.locator('.jump button[data-id=timeline]').count() == 1, 'Timeline is in the jump buttons')
    trend = pg.locator('.tl-trend').inner_text() if pg.locator('.tl-trend').count() else ''
    check('Health' in trend, 'health trend shown: ' + trend.replace('\n', ' | '))
    figs = pg.locator('.tl-cmp figure').count(); check(figs == 2, 'two photos side by side')
    pg.locator('#timeline').scroll_into_view_if_needed(); pg.screenshot(path=f'{OUT}/timeline-top.png')
    n0 = pg.locator('.tl-photo').count()
    pg.locator('input[data-act=tlkind][value=photo]').uncheck(); pg.wait_for_timeout(300)
    check(pg.locator('.tl-photo').count() == 0 and n0 > 0, f'unticking Photos hides the {n0} photo entries')
    focused = pg.evaluate("document.activeElement && document.activeElement.value")
    check(focused == 'photo', 'focus stays on the checkbox')
    pg.locator('input[data-act=tlkind][value=photo]').check(); pg.wait_for_timeout(300)
    f = pg.locator('.tl-thumb').first.get_attribute('data-file')
    pg.locator('.tl-thumb').first.click(); pg.wait_for_timeout(500)
    check(pg.locator('select[data-act=tlsel][data-side=b]').input_value() == f, 'Compare on a photo puts it on the right')
    opts = pg.locator('select[data-act=tlsel][data-side=a] option').all()
    if len(opts) > 2:
        v = opts[1].get_attribute('value'); pg.select_option('select[data-act=tlsel][data-side=a]', v); pg.wait_for_timeout(300)
        check(v in pg.locator('.tl-cmp figure').first.locator('img').get_attribute('src'), 'choosing the left photo changes it')
    pg.locator('.tl-cmp').scroll_into_view_if_needed(); pg.screenshot(path=f'{OUT}/timeline-compare.png')
    pg.locator('h3:text("Everything that has happened")').scroll_into_view_if_needed(); pg.screenshot(path=f'{OUT}/timeline-list.png')
    pg.close()
    q = b.new_page(viewport={'width': 390, 'height': 844}); q.on('pageerror', lambda e: errs.append(str(e)))
    q.add_init_script("localStorage.setItem('plantdb.display',JSON.stringify({theme:'dark'}))")
    q.goto(f'{BASE}/#/plant/{CODE}'); q.wait_for_timeout(2500)
    q.locator('#timeline').scroll_into_view_if_needed(); q.wait_for_timeout(300); q.screenshot(path=f'{OUT}/timeline-phone-dark.png')
    over = q.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth'); check(over <= 2, f'phone: no sideways scrolling ({over}px)')
    q.close()
    # answered requests come from the requests table, so ones settled by an upgrade batch show too
    ans = [r for r in __import__('json').loads(__import__('urllib.request').request.urlopen(BASE + '/api/requests').read()) if r['done'] and r['plant_code']]
    if ans:
        code2 = ans[0]['plant_code']
        a = b.new_page(viewport={'width': 1280, 'height': 900}); a.on('pageerror', lambda e: errs.append(str(e)))
        a.add_init_script("localStorage.setItem('plantdb.display',JSON.stringify({layout:'single',navopen:'0'}))")
        a.goto(f'{BASE}/#/plant/{code2}'); a.wait_for_timeout(2500)
        n = a.locator('.tl-request').count(); check(n > 0, f'{code2}: {n} answered or finished request(s) in the timeline')
        a.locator('input[data-act=tlkind][value=request]').uncheck(); a.wait_for_timeout(300)
        check(a.locator('.tl-request').count() == 0, 'unticking Answers hides them')
        a.close()
    b.close()
for e in errs: print('JS error:', e)
sys.exit(1 if fails or errs else 0)
