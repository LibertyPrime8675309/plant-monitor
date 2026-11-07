"""Checks the prototype "Repotting" (proto/repotting): how often each plant is due (from its growth rate, or chosen by hand),
"When was it repotted?" for one plant and "Save for all", Repotted today, the page under Care, the line on a plant's page and the
section on Today in repotting season, at laptop and phone width, light and dark, with large text. Start the mock server with a
fresh data folder, then: python3 dev/test/repotting_check.py      Screenshots: dev/tmp/shots/repotting-*.png"""
import json, os, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
BASE = 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Repot Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def status(m, url, body=None):
    try: call(m, url, body); return 200
    except urllib.error.HTTPError as e: return e.code
R = lambda: call('GET', '/api/repotting')
r0 = R(); st0 = {p['code']: p for p in r0['plants']}
year = int(r0['today'][:4])
check(r0['counts']['never'] == len(r0['plants']) and r0['plants'], f'a fresh install has {len(r0["plants"])} plants on the plan, none recorded yet')
check(all(p['months'] in (12, 18, 24, 36) for p in r0['plants']), 'each is due every 12, 18, 24 or 36 months')
check(any(p['why'].startswith('Grows in water') for p in r0['left_out']), 'plants that grow in water are left out')
fast = next(c for c, p in st0.items() if p['months'] == 12)
slow = next(c for c, p in st0.items() if p['months'] == 36)
mid = sorted(c for c, p in st0.items() if p['months'] in (18, 24))
call('POST', '/api/care', {'plant': fast, 'kind': 'repot', 'done_on': f'{year - 1}-04-15'})
call('POST', '/api/care', {'plant': slow, 'kind': 'repot', 'done_on': f'{year - 1}-04-15'})
st = {p['code']: p for p in R()['plants']}
nxt = R()['season']['year']
check(st[fast]['state'] == 'due' and st[slow]['state'] == 'later' and st[slow]['spring'] == year + 2,
      f'repotted last spring: a fast grower is due in spring {nxt}, a slow grower not until {year + 2}')
check(any(e['kind'] == 'repot' for e in call('GET', f'/api/care?plant={fast}')), 'a repotting is a care log entry of kind "repot"')
one = call('GET', f'/api/repotting?plant={slow}')
check([p['code'] for p in one['plants']] == [slow], '?plant= gives just that plant, for its own page')
call('PUT', '/api/repotting', {'plant': slow, 'every': 12})
check(next(p for p in R()['plants'] if p['code'] == slow)['state'] == 'due', 'every 12 months chosen by hand: the slow grower is due too')
check(status('PUT', '/api/repotting', {'plant': slow, 'every': 5}) == 400, 'only 12, 18, 24 or 36 months can be chosen')
call('PUT', '/api/repotting', {'plant': slow, 'every': 'off'})
check(any(p['code'] == slow and p['why'] == 'Switched off by hand' for p in R()['left_out']), 'No reminders moves a plant to Left out')
call('PUT', '/api/repotting', {'plant': slow, 'every': 'auto'})
check(next(p for p in R()['plants'] if p['code'] == slow)['choice'] is None, 'back to the usual: no choice kept')
check(any('Repotting: no reminders for this plant' in (x.get('note') or '') for x in call('GET', '/api/audit?n=50')), 'changes to how often are in the audit log')
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Repot Test')")
    pg.goto(BASE + '/#/repotting'); pg.wait_for_selector('#rp-due')
    check(pg.locator('#main-nav a[aria-current=page]').inner_text().strip().startswith('Care') and pg.locator('#sub-nav a[aria-current=page]').inner_text().strip() == 'Repotting',
          'the page is under Care, as "Repotting"')
    check(f'Due in spring {nxt}' in pg.inner_text('#rp-due h2') and pg.locator(f'#rp-due .job[data-code="{fast}"]').count() == 1, 'the fast grower is under "Due in spring"')
    check(pg.locator('#rp-bulk-year, form.rp-bulk label:has(select[name=year])').count() >= 1, 'the year for "Save for all" has a real label')
    pg.screenshot(path=os.path.join(OUT, 'repotting-1-laptop.png'), full_page=True)
    pg.locator('#rp-due').screenshot(path=os.path.join(OUT, 'repotting-1-due.png'))
    pg.evaluate("window.scrollTo(0, document.getElementById('rp-never').getBoundingClientRect().top + window.scrollY - 8)")
    pg.screenshot(path=os.path.join(OUT, 'repotting-1-never.png'))
    # one plant: When was it repotted?
    a = mid[0]
    pg.locator(f'#rp-never .job[data-code="{a}"] [data-act=repotset]').click(); pg.wait_for_selector('dialog[open]')
    check('When was it last repotted?' in pg.inner_text('dialog[open] legend'), 'its window asks when it was last repotted')
    pg.locator('dialog[open]').screenshot(path=os.path.join(OUT, 'repotting-2-dialog.png'))
    pg.check(f'dialog[open] input[name=when][value="{year - 2}"]'); pg.click('dialog[open] button[value=ok]'); pg.wait_for_timeout(1800)
    e = [x for x in call('GET', f'/api/care?plant={a}') if x['kind'] == 'repot']
    check(len(e) == 1 and e[0]['done_on'] == f'{year - 2}-04-15' and 'estimated' in e[0]['note'], f'choosing {year - 2} saves a repotting on April 15, {year - 2}, marked as an estimate')
    check('repotting saved' in pg.inner_text('#toasts'), 'and says so, with Undo')
    check(pg.locator(f'#rp-never .job[data-code="{a}"]').count() == 0, 'the plant leaves "Not recorded yet"')
    # an exact date, and how often, in one go
    b = mid[1]
    pg.locator(f'#rp-never .job[data-code="{b}"] [data-act=repotset]').click(); pg.wait_for_selector('dialog[open]')
    pg.check('dialog[open] input[name=when][value=day]'); pg.fill('dialog[open] input[name=day]', f'{year - 1}-03-20')
    pg.select_option('dialog[open] select[name=every]', '36'); pg.click('dialog[open] button[value=ok]'); pg.wait_for_timeout(1800)
    pb = next(x for x in R()['plants'] if x['code'] == b)
    check(pb['last'] == f'{year - 1}-03-20' and pb['months'] == 36 and pb['choice'] == 36, 'an exact date and "every 36 months" are both saved')
    # Save for all
    n_never = R()['counts']['never']
    pg.locator('form.rp-bulk select[name=year]').select_option(str(year - 1))
    check(R()['counts']['never'] == n_never, 'choosing a year in the list saves nothing by itself')
    pg.locator('form.rp-bulk button[type=submit]').click(); pg.wait_for_selector('dialog[open]')
    check(f'for {n_never} plants?' in pg.inner_text('dialog[open]'), 'Save for all asks first')
    pg.click('dialog[open] button[value=ok]'); pg.wait_for_timeout(2500)
    check(R()['counts']['never'] == 0, 'and then saves the year for every plant not recorded yet')
    pg.locator('.undo-toast [data-undo=undo]').click(); pg.wait_for_timeout(2500)
    check(R()['counts']['never'] == n_never, 'Undo takes all of them back')
    # Repotted today
    pg.locator(f'#rp-due .job[data-code="{fast}"] [data-act=repotted]').click(); pg.wait_for_timeout(1800)
    pf = next(x for x in R()['plants'] if x['code'] == fast)
    check(pf['last'] == r0['today'] and pf['state'] == 'later', 'Repotted today moves it from Due to Later')
    check(pg.evaluate("document.activeElement && document.activeElement.closest('.job') ? document.activeElement.closest('.job').dataset.code : ''") == fast, 'focus stays on that plant')
    # the plant's own page
    pg.goto(BASE + f'/#/plant/{fast}'); pg.wait_for_selector('#rp-plant', timeout=15000)
    check('next due in spring' in pg.inner_text('#rp-plant') and 'Last repotted' in pg.inner_text('#rp-plant'), "a plant's page says when it was last repotted and when it is next due")
    check('Repotted' in pg.inner_text('.care-log'), 'the repotting is in its care log')
    pg.evaluate("document.querySelectorAll('#toasts > *').forEach(t => t.remove())")      # the Undo message, for a clean picture
    pg.evaluate("document.querySelector('#rp-plant').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(200)
    pg.locator('.quick').screenshot(path=os.path.join(OUT, 'repotting-3-plant.png'))
    pg.locator('#rp-plant [data-act=repotset]').click(); pg.wait_for_selector('dialog[open]')
    check('Add a repotting?' in pg.inner_text('dialog[open] legend'), 'Change there opens the same window')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    pg.evaluate("document.documentElement.dataset.role = 'viewer'")
    check(pg.locator('#rp-plant [data-act=repotset]:visible').count() == 0, 'people who can only view do not see Change')
    pg.evaluate("document.documentElement.dataset.role = 'owner'")
    # Today, in repotting season (the server's date is today's, so its answer is changed on the way to the page)
    def spring(route):
        r = route.fetch(); d = r.json(); d['season']['now'] = True; d['season']['year'] = int(d['season']['from'][:4])
        route.fulfill(response=r, body=json.dumps(d), headers=dict(r.headers, **{'content-type': 'application/json'}))
    cx = br.new_context(viewport={'width': 1280, 'height': 900}, service_workers='block')    # so the changed answer is not served from the worker
    sp = cx.new_page(); sp.on('pageerror', lambda e: errs.append(str(e)))
    sp.add_init_script("localStorage.setItem('plantdb.editor','Repot Test')")
    sp.route('**/api/repotting', spring)
    sp.goto(BASE + '/#/'); sp.wait_for_selector('#today-repot', timeout=15000)
    n_due = R()['counts']['due']
    check(sp.inner_text('#today-repot h2') == f'Repot this spring ({n_due})', 'in season, Today has "Repot this spring" with the number due')
    check(sp.locator('.td-jumps a[data-sec=today-repot]').inner_text() == f'Repot ({n_due})', 'and a jump button for it')
    sp.locator('#today-repot').screenshot(path=os.path.join(OUT, 'repotting-4-today.png'))
    cx.close()
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#today-needs'); pg.wait_for_timeout(1500)
    check(pg.locator('#today-repot').count() == 0, 'out of season (now, November), Today has no repotting section')
    # phone, dark and large text
    for name, disp in (('phone-light', {}), ('phone-dark-big', {'theme': 'dark', 'size': '160'})):
        ph = br.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        ph.on('pageerror', lambda e: errs.append(str(e)))
        ph.add_init_script("localStorage.setItem('plantdb.editor','Repot Test');localStorage.setItem('plantdb.display', JSON.stringify(%s))" % json.dumps(disp))
        ph.goto(BASE + '/#/repotting'); ph.wait_for_selector('#rp-due'); ph.wait_for_timeout(800)
        over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 0, f'{name}: nothing scrolls sideways ({over}px)')
        ph.evaluate("window.scrollTo(0, document.querySelector('#app h1').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'repotting-5-{name}.png'))
        ph.evaluate("window.scrollTo(0, document.getElementById('rp-never').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'repotting-5-{name}-never.png'))
        ph.locator('#rp-never .job [data-act=repotset]').first.click(); ph.wait_for_selector('dialog[open]'); ph.wait_for_timeout(300)
        over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 0, f'{name}: the window fits too')
        ph.screenshot(path=os.path.join(OUT, f'repotting-5-{name}-dialog.png'))
        ph.close()
    pg.goto(BASE + '/#/repotting'); pg.wait_for_selector('#rp-due')
    pg.evaluate("document.documentElement.dataset.role = 'viewer'")
    check(pg.locator('[data-act=repotted]:visible, [data-act=repotset]:visible, form.rp-bulk:visible').count() == 0, 'people who can only view do not see the buttons')
    br.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
