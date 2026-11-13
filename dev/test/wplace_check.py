"""Checks Today's watering lists by room and spot (1.58.0, Ethan's choice of November 13, 2026: cards, one button per spot), the
order of rooms and spots that they follow (Move up and Move down on Rooms and spots), and the one-time questions about care that
was never logged (feeding; flushes and root checks).
Start the mock server with a fresh data folder, then: python3 dev/test/wplace_check.py [http://127.0.0.1:8080]
Screenshots: dev/tmp/shots/wplace-*.png"""
import json, os, sys, time, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from waits import until
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None, headers={'Content-Type': 'application/json', 'X-Editor': 'Place Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')

# the record: weather (so rain counts and plants come due), and every plant on a spot, as on Ethan's PC
call('POST', '/api/weather/refresh')
for _ in range(120):
    if not call('GET', '/api/jobs').get('running'): break
    time.sleep(0.5)
todo = call('GET', '/api/where/sort')['items']
call('POST', '/api/where/sort', {'items': [{'text': it['text'], 'from_area_id': it['area_id'], 'area_id': it['area_id'], 'name': (it.get('name') or it['text'] or 'Shelf')[:40]} for it in todo]})
plants = {p['code']: p for p in call('GET', '/api/plants')}
home = call('GET', '/api/where')['homes'][0]
spot_name = {(a['id'], s['id']): f"{a['name']}: {s['name']}" for a in home['areas'] for s in a['spots']}
order = [f"{a['name']}: {s['name']}" for a in home['areas'] for s in a['spots']]
due = [w for w in call('GET', '/api/water')['plants'] if w['state'] == 'due']
check(len(due) > 5 and all(plants[w['code']]['spot_id'] for w in due), f'{len(due)} plants are due for water and each is on a spot')

def heads(pg, sel='#today-water > .wpl'):
    return pg.eval_on_selector_all(sel + ' .wpl-head h3', 'els => els.map(e => e.textContent.replace(/\\s*\\(\\d+\\)\\s*$/, "").trim())')

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 1000})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Place Test')")
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#today-water .wpl-grp', timeout=30000)
    hs = heads(pg)
    check(len(hs) > 1 and hs == [o for o in order if o in hs], 'the plants to water are grouped by room and spot, in the order of Rooms and spots')
    ok = pg.evaluate("""() => [...document.querySelectorAll('#today-water > .wpl .wpl-grp')].every(g => g.querySelectorAll('.wpl-card').length === +g.querySelector('.wpl-n').textContent.replace(/\\D/g, ''))""")
    cards = pg.eval_on_selector_all('#today-water > .wpl .wpl-card', 'els => els.map(e => [e.dataset.code, e.closest(".wpl-grp").querySelector("h3").textContent.replace(/\\s*\\(\\d+\\)\\s*$/, "").trim()])')
    check(ok and len(cards) == len(due) and all(spot_name[(plants[c]['area_id'], plants[c]['spot_id'])] == h for c, h in cards), 'every due plant is a card under its own spot, and each heading counts its cards')
    c0 = pg.locator('#today-water > .wpl .wpl-card').first
    name0 = c0.locator('.nm').inner_text()
    check(c0.locator('a.wpl-open img').count() == 1 and c0.locator('a').count() == 1 and ('overdue' in c0.locator('.wpl-st').inner_text().lower() or 'due today' in c0.locator('.wpl-st').inner_text().lower()),
          'a card has the picture and the name in one link, and how late the plant is')
    check(c0.locator('button[data-kind=water]').get_attribute('aria-label') == 'Watered: ' + name0 and c0.locator('button[data-kind=check]').get_attribute('aria-label') == 'Still moist: ' + name0,
          'the buttons on a card say which plant they are for')
    c0.locator('details.wpl-why > summary').click()
    check(until(pg, lambda: 'Check about every' in c0.locator('details.wpl-why p').inner_text() or 'overdue' in c0.locator('details.wpl-why p').inner_text()), 'the reason is behind "Why"')
    pg.screenshot(path=os.path.join(OUT, 'wplace-today.png'))
    # go straight to a spot
    jump = pg.locator('#today-water .wpl-jump button')
    check(jump.count() == len(hs), 'with three spots or more, a row of buttons names each spot')
    jump.nth(len(hs) - 1).click()
    check(until(pg, lambda: pg.evaluate('document.activeElement && document.activeElement.id') == f'wpl-due-{len(hs) - 1}'), 'a spot\'s button puts the focus on that spot\'s heading')
    # one button for a whole spot
    g = pg.locator('#today-water > .wpl .wpl-grp', has=pg.locator('button[data-act=careall]')).first
    gname = g.locator('h3').inner_text(); n = int(''.join(ch for ch in g.locator('.wpl-n').inner_text() if ch.isdigit()))
    btn = g.locator('button[data-act=careall]')
    check(btn.inner_text() == f'Watered all {n} here' and btn.get_attribute('aria-label').startswith(f'Watered all {n} here: '), 'each spot with more than one plant has "Watered all N here", named for its spot')
    btn.click(); pg.locator('dialog[open] button', has_text='Mark as watered').click()
    check(until(pg, lambda: pg.locator('#today-water h2').inner_text().startswith(f'Water ({len(due) - n})'), 20000), f'pressing it waters the {n} plants of that spot and no others')
    check(gname.rsplit('(', 1)[0].strip() not in heads(pg), 'and the spot leaves the list')
    left = len(due) - n
    # the old order is one press away, and is remembered
    late = pg.locator('button[data-act=waterorder][data-order=late]')
    check(late.get_attribute('aria-pressed') == 'false' and pg.locator('button[data-act=waterorder][data-order=place]').get_attribute('aria-pressed') == 'true', 'By room and spot is the order to start with')
    late.click()
    check(until(pg, lambda: pg.locator('#today-water > ul.jobs > li.job').count() == left and pg.locator('#today-water .wpl-grp').count() == 0), 'Most overdue first is the list as it was: one row a plant, with its reason')
    check(pg.evaluate('document.activeElement && document.activeElement.dataset.order') == 'late' and pg.locator('button[data-act=waterorder][data-order=late]').get_attribute('aria-pressed') == 'true', 'the focus stays on the button that was pressed')
    pg.reload(); pg.wait_for_selector('#today-water ul.jobs', timeout=30000)
    check(pg.locator('#today-water .wpl-grp').count() == 0, 'the choice is remembered')
    pg.locator('button[data-act=waterorder][data-order=place]').click()
    check(until(pg, lambda: pg.locator('#today-water > .wpl .wpl-card').count() == left), 'and By room and spot brings the cards back')
    # the folded lists are grouped too
    if pg.locator('#today-unlogged').count():
        pg.evaluate("document.querySelector('#today-unlogged details').open = true")
        check(pg.locator('#today-unlogged .wpl-grp').count() > 0 and pg.locator('#today-unlogged .wpl-card details.wpl-why').count() == 0, 'No watering logged yet is grouped the same way (with no "Why": there is no reason to give)')
    # the order of rooms and spots
    area = next(a for a in home['areas'] if len(a['spots']) > 1)
    first, second = area['spots'][0], area['spots'][1]
    pg.goto(BASE + '/#/where'); pg.wait_for_selector('.wh-area', timeout=20000)
    check('Move up' in pg.locator('main').inner_text() and pg.locator(f'button[data-act=whmove][data-kind=spot][data-id="{first["id"]}"][data-dir=up]').count() == 0, 'Rooms and spots has Move up and Move down (the first spot has no Move up)')
    mv = pg.locator(f'button[data-act=whmove][data-kind=spot][data-id="{first["id"]}"][data-dir=down]')
    check(mv.get_attribute('aria-label') == 'Move down: ' + first['name'], 'each button says what it moves')
    mv.click()
    def spots_now(): return [s['id'] for a in call('GET', '/api/where')['homes'][0]['areas'] if a['id'] == area['id'] for s in a['spots']]
    check(until(pg, lambda: spots_now()[:2] == [second['id'], first['id']]), 'Move down puts a spot one place lower')
    check(until(pg, lambda: pg.evaluate('document.activeElement && document.activeElement.dataset.act') == 'whmove' and pg.evaluate('document.activeElement.dataset.id') == str(first['id'])), 'and the focus stays with the spot that moved')
    pg.screenshot(path=os.path.join(OUT, 'wplace-where.png'))
    a1 = [a for a in home['areas'] if a['side'] == 'out']
    if len(a1) > 1:
        pg.locator(f'button[data-act=whmove][data-kind=area][data-id="{a1[0]["id"]}"][data-dir=down]').click()
        check(until(pg, lambda: [a['id'] for a in call('GET', '/api/where')['homes'][0]['areas'] if a['side'] == 'out'][:2] == [a1[1]['id'], a1[0]['id']]), 'an area moves the same way')
    now = call('GET', '/api/where')['homes'][0]
    order2 = [f"{a['name']}: {s['name']}" for a in now['areas'] for s in a['spots']]
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#today-water .wpl-grp', timeout=30000)
    check(heads(pg) == [o for o in order2 if o in heads(pg)] and order2 != order, 'Today lists the spots in the new order')
    # the one-time questions
    q = pg.locator('#today-unfed')
    check(q.count() == 1 and q.locator('h2').inner_text().startswith('Feeding reminders') and 'Do you want Today to remind you' in q.inner_text(), 'plants never fed: Today asks whether reminders are wanted')
    check(q.locator('details.grp li.job').count() >= 1, 'with the plants it is about folded under the question')
    q.locator('button[data-answer=yes]').click()
    check(until(pg, lambda: pg.locator('#today-unfed').count() == 0 and (call('GET', '/api/asks')['feed'] or {}).get('answer') == 'yes'), 'Yes is saved and the question goes')
    check(pg.evaluate("askOn('feed', 0, todayStr()) && !askOn('feed', 5, todayStr())") and pg.evaluate("(ASKS.feed.on = '2026-01-01', askOn('feed', 30, todayStr()))"), 'a yes counts each plant from the day of the answer, not from before')
    pg.goto(BASE + '/#/fertilizer'); pg.wait_for_selector('#ask-feed', timeout=20000)
    check('are on' in pg.locator('#ask-feed').inner_text(), 'the Fertilizer page says the reminders are on')
    pg.locator('#ask-feed button').click()
    check(until(pg, lambda: (call('GET', '/api/asks')['feed'] or {}).get('answer') == 'no' and 'are off' in pg.locator('#ask-feed').inner_text()), 'and can turn them off')
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#today-water', timeout=30000); pg.wait_for_timeout(800)
    check(pg.locator('#today-unfed').count() == 0, 'answered no: Today says nothing about plants never fed')
    call('PUT', '/api/asks', {'kind': 'feed', 'answer': ''})
    pg.reload(); pg.wait_for_selector('#today-water', timeout=30000)
    check(until(pg, lambda: pg.locator('#today-unfed').count() == 1), 'with the answer cleared, Today asks again')
    fl = pg.locator('#mx-hydro-new')
    if fl.count():
        check('Flush and root-check reminders' in fl.locator('h2').inner_text(), 'semi-hydro plants with no flush logged: the same one-time question')
        fl.locator('button[data-answer=no]').click()
        check(until(pg, lambda: pg.locator('#mx-hydro-new').count() == 0 and (call('GET', '/api/asks')['flush'] or {}).get('answer') == 'no'), 'No is saved and the question goes')
        pg.goto(BASE + '/#/mixes'); pg.wait_for_selector('#ask-flush', timeout=20000)
        check('are off' in pg.locator('#ask-flush').inner_text(), 'the Potting mixes page says where it stands')
    # a phone
    ph = br.new_page(viewport={'width': 384, 'height': 740})
    ph.add_init_script("localStorage.setItem('plantdb.editor','Place Test')")
    ph.goto(BASE + '/#/'); ph.wait_for_selector('#today-water .wpl-card', timeout=30000)
    check(not ph.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'Today fits a phone with no sideways scrolling')
    xs = ph.eval_on_selector_all('#today-water > .wpl .wpl-grp:first-of-type .wpl-card', 'els => els.slice(0, 2).map(e => Math.round(e.getBoundingClientRect().left))')
    check(len(xs) < 2 or xs[0] != xs[1], 'two cards sit side by side on a phone')
    ph.locator('#today-water').scroll_into_view_if_needed(); ph.screenshot(path=os.path.join(OUT, 'wplace-phone.png'))
    br.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print(f"\n{'FAILED' if fails else 'passed'}: {len(fails)} of the checks failed" if fails else '\nAll watering-by-place checks passed')
sys.exit(1 if fails else 0)
