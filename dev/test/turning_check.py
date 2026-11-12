"""Checks the prototype "Turn the pots" (proto/turn-pots): which plants are on the list (Indoors and the covered porch, not under a
grow light from above, switched on or off by hand), how often (7 to 30 days), turns logged as care, the page under Care and the
section on Today, at laptop and phone width, light and dark, with large text. Start the mock server with a fresh data folder, then:
python3 dev/test/turning_check.py      Screenshots: dev/tmp/shots/turning-*.png"""
import json, os, sys, urllib.error, urllib.request
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
BASE = 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Turn Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def status(m, url, body=None):
    try: call(m, url, body); return 200
    except urllib.error.HTTPError as e: return e.code
T = lambda: call('GET', '/api/turning')
plants = {p['code']: p for p in call('GET', '/api/plants')}
t0 = T(); listed = {p['code'] for p in t0['plants']}
inside = {c for c, p in plants.items() if p['site'] in ('Indoors', 'Covered porch') and not p.get('home_id')}      # not the Baraboo orchid (batch C9)
check(t0['every'] == 14 and listed == inside and all(p['state'] == 'never' for p in t0['plants']),
      f'a fresh install lists the {len(inside)} plants indoors or on the covered porch, every 14 days, none turned yet')
check(not listed & {c for c, p in plants.items() if p['site'] == 'Outdoors'}, 'plants out in the open are not on the list')
a, b2, c3, d4 = sorted(listed)[:4]
today = date.fromisoformat(t0['today'])
call('POST', '/api/care', {'plant': a, 'kind': 'turn'})
call('POST', '/api/care', {'plant': b2, 'kind': 'turn', 'done_on': (today - timedelta(days=15)).isoformat()})
call('POST', '/api/care', {'plant': c3, 'kind': 'turn', 'done_on': (today - timedelta(days=13)).isoformat()})
st = {p['code']: p for p in T()['plants']}
check(st[a]['state'] == 'ok' and st[a]['due_on'] == (today + timedelta(days=14)).isoformat(), 'a pot turned today is next due in 14 days')
check(st[b2]['state'] == 'due' and st[c3]['state'] == 'soon', 'one turned 15 days ago is due; one turned 13 days ago is due tomorrow')
check(any(e['kind'] == 'turn' for e in call('GET', f'/api/care?plant={a}')), 'a turn is a care log entry of kind "turn"')
one = call('GET', f'/api/turning?plant={a}')
check([p['code'] for p in one['plants']] == [a] and one['plants'][0]['state'] == st[a]['state'], '?plant= gives just that plant, for its own page')
call('PUT', '/api/turning', {'every': 7})
st = {p['code']: p for p in T()['plants']}
check(T()['every'] == 7 and st[c3]['state'] == 'due', 'every 7 days: the one turned 13 days ago is now due too')
check(status('PUT', '/api/turning', {'every': 5}) == 400, 'only 7, 10, 14, 21 or 30 days can be chosen')
call('PUT', '/api/turning', {'plant': d4, 'on': False})
r = T()
check(d4 not in {p['code'] for p in r['plants']} and any(p['code'] == d4 and p['why'] == 'Switched off by hand' for p in r['left_out']), 'a plant switched off moves to Left out')
call('PUT', '/api/turning', {'plant': d4, 'on': True})
check(any(p['code'] == d4 and p['choice'] is None for p in T()['plants']), 'switched back on, it is on the list again, by the usual rule (no choice kept)')
out = next(c for c, p in plants.items() if p['site'] == 'Outdoors')
call('PUT', '/api/turning', {'plant': out, 'on': True})
check(any(p['code'] == out and p['why'] == 'Switched on by hand' for p in T()['plants']), 'an outdoor plant can be switched on by hand')
call('PUT', '/api/turning', {'plant': out, 'on': False})
# under a grow light from above
L = call('GET', '/api/lights')['lights']
down = next(l for l in L if (l.get('specs') or {}).get('direction') == 'down')
e5 = sorted(listed)[5]
call('POST', '/api/lights/spots', {'name': 'Turn test shelf', 'light': down['id'], 'units': 1, 'distance': 18, 'hours': 14, 'dim': 100, 'plants': [e5]})
r = T()
check(e5 not in {p['code'] for p in r['plants']} and any(p['code'] == e5 and p['why'].startswith('Under a grow light from above') for p in r['left_out']),
      'a plant under a grow light that shines down is left out, with the reason')
audit = call('GET', '/api/audit?n=50')
check(any('Turn the pots: remind every 7 days' in (x.get('note') or '') for x in audit), 'changing how often is in the audit log')
due_n = T()['counts']['due']
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Turn Test')")
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#today-turn', timeout=15000)
    check(pg.inner_text('#today-turn h2') == f'Turn the pots ({due_n})', 'Today has a "Turn the pots" section with the number due')
    jump = pg.locator('.td-jumps a[data-sec=today-turn]')
    check(jump.count() == 1 and jump.inner_text() == f'Turn ({due_n})', 'and a jump button for it beside the others')
    check(pg.evaluate("[...document.querySelectorAll('main section.blk')].map(s => s.id).indexOf('today-turn') == [...document.querySelectorAll('main section.blk')].map(s => s.id).indexOf('today-needs') - 1"),
          'it comes just before Needed from you')
    pg.locator('#today-turn').screenshot(path=os.path.join(OUT, 'turning-1-today.png'))
    pg.locator(f'#today-turn .job[data-code="{b2}"] [data-act=turned]').click(); pg.wait_for_timeout(1800)
    check(T()['counts']['due'] == due_n - 1 and 'Turned:' in pg.inner_text('#toasts'), 'Turned on Today logs the turn and says so, with Undo')
    pg.locator('.undo-toast [data-undo=undo]').click(); pg.wait_for_timeout(1800)
    check(T()['counts']['due'] == due_n, 'Undo takes the turn back')
    # the page under Care
    pg.goto(BASE + '/#/turning'); pg.wait_for_selector('#turn-due')
    check(pg.locator('#main-nav a[aria-current=page]').inner_text().strip().startswith('Care') and pg.locator('#sub-nav a[aria-current=page]').inner_text().strip() == 'Turn the pots',
          'the page is under Care, as "Turn the pots"')
    check(pg.locator('label:has(select[data-act=turnevery])').count() == 1, 'the how-often choice has a real label')
    pg.evaluate("document.querySelectorAll('#toasts > *').forEach(t => t.remove())")      # the Undo message from Today, for a clean picture
    pg.screenshot(path=os.path.join(OUT, 'turning-2-laptop.png'), full_page=True)
    pg.select_option('select[data-act=turnevery]', '10'); pg.wait_for_timeout(1500)
    check(T()['every'] == 10 and pg.locator('select[data-act=turnevery]').input_value() == '10', 'choosing 10 days saves it')
    nv = pg.locator('.tn-never [data-act=turnedall]')
    # 1.56.3 (Ethan, November 10): a group that folds by its title bar shows Show/Hide at the right of the bar too. 1.56.4: only the
    # bar is a control (no button inside it), so screen readers hear one control that says open or closed
    fb = pg.locator('.tn-never > summary .det-fold')
    check(fb.count() == 1 and 'Show' in fb.inner_text() and pg.locator('.tn-never > summary button').count() == 0
          and fb.locator('xpath=ancestor::*[@aria-hidden="true"]').count() == 1, 'the folded group shows Show, and the bar is the one control')
    x0 = fb.bounding_box()['x']; fb.click(); pg.wait_for_timeout(200)
    check(pg.locator('.tn-never').evaluate('d => d.open') and 'Hide' in fb.inner_text() and abs(fb.bounding_box()['x'] - x0) < 1,
          'pressing it opens the group, it says Hide, and it stays where it was')
    n_never = T()['counts']['never']
    nv.click(); pg.wait_for_selector('dialog[open]')
    check(f'Mark {n_never} pots as turned today?' in pg.inner_text('dialog[open]'), 'I turned all ... asks first')
    pg.click('dialog[open] button[value=ok]'); pg.wait_for_timeout(2000)
    check(T()['counts']['never'] == 0, 'and then logs a turn for every pot not turned yet')
    pg.locator(f'#turn-later .job[data-code="{a}"] [data-act=turnset]').click(); pg.wait_for_timeout(1500)
    check(any(x['code'] == a for x in T()['left_out']), 'No reminders moves a plant to Left out')
    pg.locator(f'#turn-out .job[data-code="{a}"] [data-act=turnset]').click(); pg.wait_for_timeout(1500)
    check(any(x['code'] == a for x in T()['plants']), 'and Remind me brings it back')
    # Log other care offers it too
    pg.goto(BASE + f'/#/plant/{a}'); pg.wait_for_timeout(2500)
    btn = pg.locator('[data-act=careother]').first
    if btn.count():
        btn.click(); pg.wait_for_selector('dialog[open]')
        check(pg.locator('dialog[open] select[name=kind] option[value=turn]').count() == 1, 'Log other care offers "Turned the pot"')
        pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    # Ethan, November 6: "Turned today" on the plant's own page, next to Watered today
    tb = pg.locator('.quick-btns #tn-plant-btn')
    order = pg.evaluate("[...document.querySelectorAll('.quick-btns > *')].map(b => b.id || b.dataset.kind || '').slice(0, 2)")
    check(tb.count() == 1 and order == ['water', 'tn-plant-btn'] and 'Turn the pot:' in pg.inner_text('#tn-plant'), 'a plant on the list has "Turned today" next to Watered today, and a line saying when it is due')
    if tb.is_disabled():                       # turned already on this run (I turned all ...): take today's turn back first
        for e in call('GET', f'/api/care?plant={a}'):
            if e['kind'] == 'turn' and e['done_on'] == t0['today']: call('DELETE', f"/api/care/{e['id']}")
        pg.reload(); pg.wait_for_timeout(2500)
    n0 = sum(1 for e in call('GET', f'/api/care?plant={a}') if e['kind'] == 'turn')
    pg.locator('.quick-btns #tn-plant-btn').click(); pg.wait_for_timeout(1800)
    check(sum(1 for e in call('GET', f'/api/care?plant={a}') if e['kind'] == 'turn') == n0 + 1 and pg.locator('#tn-plant-btn').is_disabled()
          and 'Turned today' in pg.inner_text('#tn-plant-btn') and 'Turned:' in pg.inner_text('#toasts'), 'pressing it logs the turn, says so with Undo, and shows it as done')
    check(pg.evaluate("document.activeElement.id") == 'tn-plant' and 'turned today' in pg.inner_text('#tn-plant'), 'focus moves to the line saying it was turned and when next (not back to Watered today)')
    check('Turned the pot' in pg.inner_text('.care-log'), 'the turn shows in the care log on the page')
    pg.locator('.undo-toast [data-undo=undo]').click(); pg.wait_for_timeout(1800)
    check(sum(1 for e in call('GET', f'/api/care?plant={a}') if e['kind'] == 'turn') == n0 and not pg.locator('#tn-plant-btn').is_disabled(), 'Undo takes it back and the button is ready again')
    call('PUT', '/api/turning', {'plant': a, 'on': False}); pg.reload(); pg.wait_for_timeout(2500)
    check(pg.locator('#tn-plant-btn').count() == 0 and 'Switched off by hand' in pg.inner_text('#tn-plant') and pg.locator('#tn-plant [data-act=turnset]').count() == 1,
          'a plant left out has no button, but says why, with Remind me')
    pg.locator('#tn-plant [data-act=turnset]').click(); pg.wait_for_timeout(2000)
    check(pg.locator('#tn-plant-btn').count() == 1 and any(x['code'] == a for x in T()['plants']), 'Remind me there puts the button back')
    out_code = next((c for c, p in plants.items() if p['site'] == 'Outdoors'), None)
    if out_code:
        pg.goto(BASE + f'/#/plant/{out_code}'); pg.wait_for_timeout(2500)
        check(pg.locator('#tn-plant-btn').count() == 0 and pg.locator('#tn-plant').count() == 0, f'a plant out in the open ({out_code}) gets nothing about turning')
    pg.goto(BASE + f'/#/plant/{a}'); pg.wait_for_timeout(2500)
    pg.evaluate("document.querySelector('.quick').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(200)
    pg.locator('.quick').screenshot(path=os.path.join(OUT, 'turning-5-plant.png'))
    pg.evaluate("document.documentElement.dataset.role = 'viewer'")
    check(pg.locator('#tn-plant-btn:visible').count() == 0, 'people who can only view do not see Turned today')
    pg.evaluate("document.documentElement.dataset.role = 'owner'")
    # phone, dark and large text
    for name, disp in (('phone-light', {}), ('phone-dark-big', {'theme': 'dark', 'size': '160'})):
        ph = br.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        ph.on('pageerror', lambda e: errs.append(str(e)))
        ph.add_init_script("localStorage.setItem('plantdb.editor','Turn Test');localStorage.setItem('plantdb.display', JSON.stringify(%s))" % json.dumps(disp))
        call('POST', '/api/care', {'plant': b2, 'kind': 'turn', 'done_on': (today - timedelta(days=20)).isoformat()})
        ph.goto(BASE + '/#/turning'); ph.wait_for_selector('#turn-due'); ph.wait_for_timeout(800)
        over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 0, f'{name}: nothing scrolls sideways ({over}px)')
        ph.evaluate("window.scrollTo(0, document.querySelector('#app h1').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'turning-3-{name}.png'))
        ph.evaluate("window.scrollTo(0, document.getElementById('turn-due').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'turning-3-{name}-due.png'))
        ph.goto(BASE + '/#/'); ph.wait_for_selector('#today-turn'); ph.wait_for_timeout(800)
        ph.evaluate("window.scrollTo(0, document.getElementById('today-turn').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'turning-4-today-{name}.png'))
        ph.close()
    # viewers do not see the buttons
    pg.goto(BASE + '/#/turning'); pg.wait_for_selector('#turn-due')
    pg.evaluate("document.documentElement.dataset.role = 'viewer'")
    check(pg.locator('[data-act=turned]:visible, [data-act=turnset]:visible, select[data-act=turnevery]:visible').count() == 0, 'people who can only view do not see the buttons')
    br.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
