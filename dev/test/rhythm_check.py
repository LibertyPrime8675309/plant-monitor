"""Checks the prototype "How often you water" (proto/water-rhythm): the gaps between waterings in the care log against the watering
reminder, rain counted for plants out in the open, the button that makes the reminder match (with Undo), viewers refused, the page
under Care and the line on a plant's page, at laptop and phone width, light and dark, with large text.
Start the mock server with a fresh data folder (MOCK_TS=1), then:  python3 dev/test/rhythm_check.py
Screenshots: dev/tmp/shots/rhythm-*.png"""
import json, os, sys, urllib.error, urllib.request
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
BASE, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, base=BASE, h=None):
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Rhythm Test', **(h or {})}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def status(m, url, body=None, base=BASE, h=None):
    try: call(m, url, body, base, h); return 200
    except urllib.error.HTTPError as e: return e.code
R = lambda code=None: call('GET', '/api/rhythm' + (f'?plant={code}' if code else ''))
one = lambda code: R(code)['plants'][0]
plants = {p['code']: p for p in call('GET', '/api/plants')}
r0 = R()
check(r0['counts']['few'] == len(r0['plants']) and r0['plants'], f'a fresh install: all {len(r0["plants"])} plants have too few waterings to tell')
today = date.fromisoformat(r0['today'])
inside = sorted(c for c, p in plants.items() if p['site'] == 'Indoors' and p['status'] == 'active')
outside = sorted(c for c, p in plants.items() if p['site'] == 'Outdoors' and p['status'] == 'active')
ev = {p['code']: p['every'] for p in r0['plants']}
short = [c for c in inside if 5 <= ev.get(c, 99) <= 15]          # so three or four gaps of up to twice the reminder fit in the 120 days
a, b, m = short[:3]
inside = [c for c in inside if c not in (a, b, m)]
def water(code, gaps, kind='water'):
    d = today
    days = [d]
    for g in reversed(gaps): d = d - timedelta(days=g); days.append(d)
    for d in sorted(days): call('POST', '/api/care', {'plant': code, 'kind': kind, 'done_on': d.isoformat()})
# a: watered every 3 or 4 days (well before its reminder); b: every 2x its reminder, found moist twice; m: on time
water(a, [3, 4, 3, 4, 3])
water(b, [ev[b] * 2] * 3)
call('POST', '/api/care', {'plant': b, 'kind': 'check', 'done_on': (today - timedelta(days=3)).isoformat()})
call('POST', '/api/care', {'plant': b, 'kind': 'check', 'done_on': (today - timedelta(days=5)).isoformat()})
water(m, [ev[m]] * 4)
pa, pb, pm = one(a), one(b), one(m)
check(pa['state'] == 'often' and pa['gap'] == 3 and pa['waterings'] == 6 and pa['gaps'] == [3, 4, 3, 4, 3],
      f'watered every 3 or 4 days against a reminder of {ev[a]}: "sooner", about every 3 days, with the gaps listed')
check(pa['suggest'] and pa['suggest']['every'] == 3 and pa['suggest']['setting'] == 2,
      'it offers a 3-day reminder, which indoors means "Check for water every" 2 days (2 x 1.5 rounds to 3)')
check(pb['state'] == 'seldom' and pb['checks'] == 2, f'watered every {ev[b] * 2} days against {ev[b]}, found moist twice: "later", with the checks counted')
check(pm['state'] == 'matches' and pm['suggest'] is None, 'watered on time: "about right", nothing offered')
# a long gap (away, or not logged) is left out, not taken as the rhythm
c4 = inside[0]
water(c4, [5, 5, 60, 5, 5])
p4 = one(c4)
check(p4['left_out'] == 1 and p4['gap'] == 5, 'a 60-day gap is left out as a time nothing was logged')
# rain counts for a plant out in the open, once its own log has started
o = outside[0]
call('POST', '/api/care', {'plant': o, 'kind': 'water', 'done_on': (today - timedelta(days=30)).isoformat()})
po = one(o)
check(po['site'] == 'Outdoors' and po['rain_days'] >= 0 and po['waterings'] == 1, f'an outdoor plant: rain days counted as waterings ({po["rain_days"]})')
# make the reminder match, then undo it
v0 = call('GET', f'/api/plants/{a}')['water_every_days']
r = call('PUT', '/api/rhythm', {'plant': a, 'every': 3})['plants'][0]
check(call('GET', f'/api/plants/{a}')['water_every_days'] == 2 and r['every'] == 3 and r['state'] == 'matches',
      '"Remind me every 3 days" sets the field to 2 and the reminder is now every 3 days, about right')
check(any(x.get('plant_code') == a and 'How often you water' in (x.get('note') or '') for x in call('GET', '/api/audit?n=20')), 'the change is in the audit log')
call('PUT', '/api/rhythm', {'plant': a, 'setting': v0})
check(call('GET', f'/api/plants/{a}')['water_every_days'] == v0, 'Undo puts the field back as it was')
call('PUT', '/api/rhythm', {'plant': a, 'every': 3})
call('PUT', '/api/rhythm', {'plant': a, 'every': None})
check(call('GET', f'/api/plants/{a}')['water_every_days'] is None, '"Let the app work out the gap" empties the field')
check(status('PUT', '/api/rhythm', {'plant': a, 'every': 0}) == 400 and status('PUT', '/api/rhythm', {'plant': a, 'every': 'x'}) == 400, 'nonsense is refused')
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
G = {'Tailscale-User-Login': 'sam@example.net', 'Tailscale-User-Name': 'Sam'}
status('GET', '/api/me', base=TS, h=E); status('GET', '/api/me', base=TS, h=G)
check(status('PUT', '/api/rhythm', {'plant': a, 'every': 3}, base=TS, h=G) == 403 and status('GET', '/api/rhythm', base=TS, h=G) == 200,
      'a viewer can see the comparison but not change a reminder')
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Rhythm Test')")
    pg.goto(BASE + '/#/rhythm'); pg.wait_for_selector('#rh-often')
    check(pg.locator('nav a[href="#/rhythm"], #app a[href="#/rhythm"], header a[href="#/rhythm"]').count() >= 1 or 'How often you water' in pg.content(),
          'the page is in the Care section')
    C = R()['counts']
    check(pg.inner_text('#rh-often h2') == f'Watered sooner than the reminder ({C["often"]})' and pg.inner_text('#rh-seldom h2') == f'Watered later than the reminder ({C["seldom"]})'
          and pg.locator(f'#rh-often .job[data-code="{a}"]').count() == 1 and pg.locator(f'#rh-seldom .job[data-code="{b}"]').count() == 1,
          'the page lists the plants watered sooner and later, each in its part')
    check('Found still moist 2 times' in pg.inner_text(f'#rh-seldom .job[data-code="{b}"]'), 'the "later" plant says it was found still moist twice')
    pg.screenshot(path=os.path.join(OUT, 'rhythm-1-page.png'), full_page=True)
    pg.locator(f'#rh-often .job[data-code="{a}"] [data-act=rhset]').click(); pg.wait_for_timeout(1800)
    check(call('GET', f'/api/plants/{a}')['water_every_days'] == 2 and 'watering reminder now every 3 days' in pg.inner_text('#toasts'),
          'the button changes the reminder and says so, with Undo')
    check(pg.locator(f'#rh-match .job[data-code="{a}"]').count() == 1, 'the plant moves to About right')
    pg.locator('.undo-toast [data-undo=undo]').click(); pg.wait_for_timeout(1800)
    check(call('GET', f'/api/plants/{a}')['water_every_days'] is None, 'Undo on the page puts it back (empty, as it was)')
    # the plant's own page
    pg.goto(BASE + f'/#/plant/{a}'); pg.wait_for_selector('#rh-plant', timeout=15000)
    t = pg.inner_text('#rh-plant')
    check('Watered about every 3 days' in t and 'Recent gaps: 3, 4, 3, 4, 3 days' in t, 'the plant page says how often it was watered, with the gaps')
    check(pg.evaluate("!!document.querySelector('#care-plant .verdict-box #rh-plant')"), 'inside the Watering box')
    pg.locator('#rh-plant').screenshot(path=os.path.join(OUT, 'rhythm-2-plant.png'))
    pg.locator('#rh-plant [data-act=rhset]').click(); pg.wait_for_timeout(1800)
    check(pg.locator('#rh-plant [data-act=rhclear]').count() == 1 and pg.locator('#rh-plant [data-act=rhset]').count() == 0,
          'after it, the line offers "Let the app work out the gap" instead')
    check(pg.evaluate("document.activeElement && document.activeElement.id") == 'rh-plant', 'focus lands on the line, so a screen reader reads the new words')
    pg.locator('.undo-toast [data-undo=close]').click(); pg.wait_for_timeout(300)
    pg.locator('#rh-plant').screenshot(path=os.path.join(OUT, 'rhythm-2-plant-after.png'))
    pg.locator('#rh-plant [data-act=rhclear]').click(); pg.wait_for_timeout(1500)
    check(call('GET', f'/api/plants/{a}')['water_every_days'] is None, 'and that empties the field')
    pg.locator('.quick-btns [data-act=care][data-kind=check]').click(); pg.wait_for_timeout(1500)
    check('Found still moist 1 time' in pg.inner_text('#rh-plant'), 'the line draws again with the care part ("Checked: still moist" is counted at once)')
    pg.goto(BASE + f'/#/plant/{inside[-1]}'); pg.wait_for_selector('#care-plant .verdict-box'); pg.wait_for_timeout(1200)
    check(pg.locator('#rh-plant').count() == 0, 'a plant with no waterings logged gets no line')
    pg.goto(BASE + '/#/rhythm'); pg.wait_for_selector('#rh-often')
    pg.evaluate("document.documentElement.dataset.role = 'viewer'")
    check(pg.locator('[data-act=rhset]:visible, [data-act=rhclear]:visible').count() == 0, 'people who can only view do not see the buttons')
    for name, disp in (('phone-light', {}), ('phone-dark-big', {'theme': 'dark', 'size': '160'})):
        ph = br.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        ph.on('pageerror', lambda e: errs.append(str(e)))
        ph.add_init_script("localStorage.setItem('plantdb.editor','Rhythm Test');localStorage.setItem('plantdb.display', JSON.stringify(%s))" % json.dumps(disp))
        ph.goto(BASE + '/#/rhythm'); ph.wait_for_selector('#rh-often'); ph.wait_for_timeout(800)
        over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 0, f'{name}: nothing scrolls sideways on the page ({over}px)')
        ph.evaluate("window.scrollTo(0, document.querySelector('#app h1').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'rhythm-3-{name}.png'))
        ph.evaluate("window.scrollTo(0, document.getElementById('rh-often').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'rhythm-3-{name}-list.png'))
        ph.goto(BASE + f'/#/plant/{b}'); ph.wait_for_selector('#rh-plant', timeout=15000); ph.wait_for_timeout(500)
        over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 0, f'{name}: nothing scrolls sideways on a plant page ({over}px)')
        ph.evaluate("window.scrollTo(0, document.getElementById('rh-plant').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'rhythm-4-{name}-plant.png'))
        ph.close()
    br.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
