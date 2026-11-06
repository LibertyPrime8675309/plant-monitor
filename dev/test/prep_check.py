"""Checks "Getting ready to come inside": the ratings, the choices on a plant page, the tick boxes (1.41.1), the second
spray round on the Today page, moving inside, the Coming inside page, the Edit page and phone width.
Start the mock server with a fresh data folder first, then:  python3 dev/test/prep_check.py [base-url]
Screenshots: dev/tmp/shots/prep-*.png"""
import json, os, sys, urllib.request
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'X-Editor': 'Prep Test', 'Content-Type': 'application/json'}, method=m)
    return json.load(urllib.request.urlopen(req))
rating = lambda d, k: next(m['rating'] for m in d['methods'] if m['key'] == k)

# the ratings themselves, straight from the server
d = call('GET', '/api/plants/P-016/prep')
check(d['leaf_type'] == 'Succulent or cactus' and rating(d, 'rinse') == 'Not for this plant' and rating(d, 'soak') == 'Not for this plant'
      and rating(d, 'oil') == 'Not for this plant', 'succulent (P-016): no rinsing, soaking or oil')
d = call('GET', '/api/plants/P-024/prep')
check(rating(d, 'rinse') == 'Best' and rating(d, 'oil') == 'Not for this plant' and rating(d, 'wipe') == 'Not for this plant', 'fern (P-024): water only')
d = call('GET', '/api/plants/P-017/prep')
check(rating(d, 'rinse') == 'Best' and 'spider mites' in d['methods'][2]['reason'], 'palm (P-017): rinsing is best, for spider mites')
d = call('GET', '/api/plants/P-034/prep')
check(rating(d, 'repot') == 'Not needed' and 'struggling' in next(m['reason'] for m in d['methods'] if m['key'] == 'repot'), 'struggling peace lily (P-034): no repotting')
steps = ' '.join(s for m in d['methods'] for s in m['steps']).lower()
check('bleach' in steps and 'without bleach' in steps and steps.count('bleach') == 1, 'no bleach in any steps (only "without bleach")')
check(call('GET', '/api/plants/P-050')['status'] == 'archived', 'the water hyacinth page is archived')
p = call('GET', '/api/prep')
check(len(p['plants']) >= 30 and all(x['winter_plan'] == 'Move indoors' for x in p['plants']), f"{len(p['plants'])} plants coming inside")

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900}); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Prep Test');localStorage.setItem('plantdb.display',JSON.stringify({layout:'single',navopen:'0'}))")
    pg.goto(f'{BASE}/#/plant/P-065'); pg.wait_for_timeout(2500)
    check(pg.locator('#inside h2').inner_text().startswith('Getting ready to come inside'), 'plant page has the section')
    check(pg.locator('select[data-act=preptrait][data-k=leaf_type]').input_value() == 'Large leaves', 'leaf type filled in (Large leaves)')
    check(pg.locator('#prep-box .pm').count() == 10, 'all 10 methods are there')
    v0 = call('GET', '/api/plants/P-065')['version']
    pg.select_option('select[data-act=preptrait][data-k=pot_size]', 'Large: too big to soak'); pg.wait_for_timeout(900)
    check('Use with care' in pg.locator('#pm-soak .pr-badge').inner_text(), 'large pot: soaking becomes "Use with care"')
    check(pg.evaluate("document.activeElement && document.activeElement.dataset.k") == 'pot_size', 'focus stays on the pot size menu')
    pg.locator('input[data-act=preppest][value=Scale]').check(); pg.wait_for_timeout(900)
    pg.locator('input[data-act=preppest][value=Mealybugs]').check(); pg.wait_for_timeout(900)
    check(pg.evaluate("document.activeElement && document.activeElement.value") == 'Mealybugs', 'focus stays on the tick box')
    d = call('GET', '/api/plants/P-065/prep')
    check(d['pests_found'] == ['Mealybugs', 'Scale'] and rating(d, 'soap') == 'Best' and rating(d, 'oil') == 'Best', 'scale and mealybugs: soap and oil become Best')
    check(call('GET', '/api/plants/P-065')['version'] == v0 + 3, 'each choice is saved as a page version')
    pg.screenshot(path=f'{OUT}/prep-choices.png')
    # 1.40.1: Start the checklist, beside the status
    st = pg.locator('#prep-box .pr-top [data-act=prepstart]')
    check(st.count() == 1 and 'Not started' in pg.locator('#prep-box .pr-status').inner_text(), 'a plant not started has a Start the checklist button')
    st.click(); pg.wait_for_timeout(1200)
    check('In progress' in pg.locator('#prep-box .pr-status').inner_text() and pg.evaluate("document.activeElement.id") == 'pm-inspect-tick',
          'Start: In progress, and focus moves to the first tick box')
    pg.locator('#prep-box .pr-top [data-act=prepundo][data-k=start]').click(); pg.wait_for_timeout(1200)
    check('Not started' in pg.locator('#prep-box .pr-status').inner_text(), 'Undo the start puts it back')
    # 1.41.1: every step is a tick box; the ones not recommended are marked but can be ticked
    check(pg.locator('#prep-box input[data-act=preptick]').count() == 10 and pg.locator('#prep-box details.pm-rest').count() == 0, 'all 10 steps have a tick box, none hidden away')
    nr = pg.locator('#prep-box li.mi-not')
    check(nr.count() >= 1 and all('Not recommended' in nr.nth(i).inner_text() for i in range(nr.count())), f'{nr.count()} steps marked Not recommended, in words')
    pg.locator('#pm-inspect-tick').check(); pg.wait_for_timeout(1200)
    check('Done today' in pg.locator('#pm-inspect .pm-done').inner_text() and pg.locator('#pm-inspect-tick').is_checked(), 'ticking a step marks it done today')
    check('In progress' in pg.locator('#prep-box .pr-status').inner_text(), 'status becomes In progress')
    check('Inspected for pests' in pg.locator('.care-log').inner_text(), 'it shows in the care log')
    check(pg.evaluate("document.activeElement.id") == 'pm-inspect-tick', 'focus stays on the tick box')
    pg.locator('#pm-inspect-tick').uncheck(); pg.wait_for_timeout(1200)
    check(pg.locator('#pm-inspect .pm-done').count() == 0 and not pg.locator('#pm-inspect-tick').is_checked(), 'unticking takes it back off')
    pg.locator('#pm-inspect-tick').check(); pg.wait_for_timeout(1200)
    pg.locator('#pm-soap-tick').check(); pg.wait_for_timeout(1200)
    check('Round 2 is due' in pg.locator('#pm-soap .pm-done').inner_text() and pg.locator('#pm-soap [data-act=prepdone]').count() == 1, 'one soap round: round 2 is due, with its own button')
    nk = nr.first.get_attribute('id').replace('pm-', '')
    pg.locator(f'#pm-{nk}-tick').check(); pg.wait_for_timeout(1200)
    check(any(m['key'] == nk and m['done'] for m in call('GET', '/api/plants/P-065/prep')['methods']), f'a step not recommended ({nk}) can still be ticked')
    pg.locator(f'#pm-{nk}-tick').uncheck(); pg.wait_for_timeout(1200)
    pg.close()
    # a soap round 6 days ago on another plant: the Today page asks for round 2
    old = (date.today() - timedelta(days=6)).isoformat()
    call('POST', '/api/plants/P-020/prep-traits', {'pests_found': ['Spider mites']})
    call('POST', '/api/care', {'plant': 'P-020', 'kind': 'prep_soap', 'done_on': old})
    t = b.new_page(viewport={'width': 1280, 'height': 900}); t.on('pageerror', lambda e: errs.append(str(e)))
    t.add_init_script("localStorage.setItem('plantdb.editor','Prep Test')")
    t.goto(f'{BASE}/#/today'); t.wait_for_timeout(2500)
    job = t.locator('#today-inside li.job[data-code="P-020"]')
    check(job.count() == 1 and 'round 2' in job.inner_text(), 'Today page: P-020 soap round 2 is due')
    t.screenshot(path=f'{OUT}/prep-today.png')
    job.locator('button[data-act=prepdone]').click(); t.wait_for_timeout(1500)
    check(t.locator('#today-inside li.job[data-code="P-020"]').count() == 0, 'Done today takes it off the Today page')
    # the Coming inside page
    t.goto(f'{BASE}/#/inside'); t.wait_for_timeout(2000)
    check(t.locator('h1').inner_text() == 'Getting plants ready to come inside', 'Coming inside page opens')
    check(t.locator('#in-doing details.mi-fold[data-code="P-065"]').count() == 1, 'P-065 is listed as In progress')
    check(t.locator('#in-methods details').count() == 10, 'it explains all 10 methods')
    # 1.41.1: each plant folds open to its tick boxes
    folds = t.locator('details.mi-fold')
    check(folds.count() == len(call('GET', '/api/prep')['plants']) and t.locator('details.mi-fold[open]').count() == 0, 'every plant is folded shut to start with')
    t.click('[data-act=prepfold][data-open="1"]'); t.wait_for_timeout(300)
    check(t.locator('details.mi-fold[open]').count() == folds.count(), 'Open every plant')
    t.click('[data-act=prepfold][data-open="0"]'); t.wait_for_timeout(300)
    check(t.locator('details.mi-fold[open]').count() == 0, 'Close every plant')
    row = t.locator('#in-todo details.mi-fold').first; code = row.get_attribute('data-code')
    row.locator(':scope > summary').click(); t.wait_for_timeout(300)
    check(row.locator('input[data-act=preptick]').count() == 10 and row.locator('details.pm-steps').count() >= 8, f'{code} opens to its 10 tick boxes, with how to do each')
    row.locator('[data-act=prepstart]').click(); t.wait_for_timeout(1800)
    fd = t.locator(f'#in-doing details.mi-fold[data-code="{code}"]')
    check(fd.count() == 1 and fd.evaluate('d => d.open') and t.evaluate("document.activeElement.id") == f'mi-{code}-inspect-tick', f'Start moves {code} to In progress, still open, focus on its first tick box')
    t.locator(f'#mi-{code}-inspect-tick').check(); t.wait_for_timeout(1800)
    check(call('GET', f'/api/plants/{code}/prep')['methods'][0]['done'] != [] and t.locator(f'#mi-{code}-inspect-tick').is_checked(), 'ticking there logs the inspection')
    check('1 of' in fd.locator(':scope > summary').inner_text(), 'and the fold says how many recommended steps are done')
    settled = [x['code'] for x in call('GET', '/api/prep')['plants'] if x['status'] == 'settled']
    if settled:     # a plant already inside (a new one from a store) can go through it too, and is kept apart for 3 weeks from the start
        sf = t.locator(f'#in-settled details.mi-fold[data-code="{settled[0]}"]'); sf.locator(':scope > summary').click(); t.wait_for_timeout(300)
        sf.locator('[data-act=prepstart]').click(); t.wait_for_timeout(1800)
        d = call('GET', f'/api/plants/{settled[0]}/prep')
        check(d['status'] == 'doing' and d['started'] and d['keep_until'] == (date.fromisoformat(d['started']) + timedelta(days=21)).isoformat(), f'{settled[0]} (already inside): started, kept apart until {d["keep_until"]}')
    else: check(False, 'a plant already inside to start')
    t.screenshot(path=f'{OUT}/prep-page.png')
    pf = t.locator('#in-doing details.mi-fold[data-code="P-065"]'); pf.locator(':scope > summary').click(); t.wait_for_timeout(300)
    pf.locator('button[data-act=openprep]').click(); t.wait_for_timeout(3500)
    top = t.evaluate("(() => { const s = document.getElementById('inside').getBoundingClientRect().top, p = document.getElementById('inside').closest('.pane'); return s - (p ? Math.max(p.getBoundingClientRect().top, 0) : 0); })()")
    check(t.url.endswith('/plant/P-065') and -5 <= top < 120, f'"Open its plan" opens the plant at this section ({top:.0f}px below the top of its half)')
    # moving inside
    call('POST', '/api/plants/P-065/site', {'site': 'Indoors'})
    d = call('GET', '/api/plants/P-065/prep')
    keep = date.fromisoformat(d['keep_until'])
    check(d['status'] == 'apart' and keep >= date.today() + timedelta(days=13), f"moved indoors: kept apart until {d['keep_until']}")
    # the Edit page
    t.goto(f'{BASE}/#/plant/P-031/edit'); t.wait_for_timeout(1800)
    opts = t.locator('select[name=leaf_type] option').all_inner_texts()
    check(opts[0] == 'Not set' and 'Fern fronds' in opts, 'Edit page: leaf type menu with Not set')
    t.close()
    # phone, largest text
    q = b.new_page(viewport={'width': 390, 'height': 844}); q.on('pageerror', lambda e: errs.append(str(e)))
    q.add_init_script("localStorage.setItem('plantdb.display',JSON.stringify({theme:'dark',size:'190'}))")
    for u in ('#/plant/P-065', '#/inside', '#/today'):
        q.goto(f'{BASE}/{u}'); q.wait_for_timeout(2400)
        over = q.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 2, f'phone, largest text, {u}: no sideways scrolling ({over}px)')
    q.goto(f'{BASE}/#/plant/P-065'); q.wait_for_timeout(2400)
    q.evaluate("window.scrollTo(0, document.getElementById('inside').getBoundingClientRect().top + scrollY)"); q.wait_for_timeout(300)
    q.screenshot(path=f'{OUT}/prep-phone-dark.png')
    q.close(); b.close()
for e in errs: print('JS error:', e)
sys.exit(1 if fails or errs else 0)
