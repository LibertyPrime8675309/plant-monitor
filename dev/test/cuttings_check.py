"""Checks the prototype "Cuttings" (proto/cuttings): taking cuttings, the weekly look, the stages (rooting, has roots, potted up,
given away, did not take), changing and removing a batch, viewers refused, the page in the Today row, the block on Today and the
line on a plant's page, at laptop and phone width, light and dark, with large text. Start the mock server with a fresh data
folder (MOCK_TS=1), then:  python3 dev/test/cuttings_check.py      Screenshots: dev/tmp/shots/cuttings-*.png"""
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
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Cut Test', **(h or {})}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def status(m, url, body=None, base=BASE, h=None):
    try: call(m, url, body, base, h); return 200
    except urllib.error.HTTPError as e: return e.code
R = lambda q='': call('GET', '/api/cuttings' + q)
plants = call('GET', '/api/plants')
a, b, c3 = plants[0]['code'], plants[1]['code'], plants[2]['code']
r0 = R(); today = date.fromisoformat(r0['today'])
check(r0['cuttings'] == [] and r0['counts']['due'] == 0, 'a fresh install has no cuttings (the table is made when first needed)')
ago = lambda n: (today - timedelta(days=n)).isoformat()
x1 = call('POST', '/api/cuttings', {'plant': a, 'method': 'Stem cuttings', 'medium': 'Water', 'how_many': 3, 'started_on': ago(9)})['id']
x2 = call('POST', '/api/cuttings', {'plant': b, 'method': 'Leaf cuttings', 'medium': 'Potting mix', 'how_many': 2, 'started_on': ago(3), 'notes': 'On the kitchen sill'})['id']
x3 = call('POST', '/api/cuttings', {'plant': c3, 'method': 'Division', 'how_many': 1, 'started_on': ago(20)})['id']
st = {x['id']: x for x in R()['cuttings']}
check(st[x1]['look_due'] and not st[x2]['look_due'] and st[x2]['next_look'] == ago(-4), 'taken 9 days ago: due a look; taken 3 days ago: next look in 4 days')
check(R()['counts'] == {'due': 2, 'rooting': 3, 'rooted': 0, 'done': 0, 'pieces': 6}, 'the counts: 2 due, 3 batches rooting, 6 pieces')
check([x['id'] for x in R('?plant=' + a)['cuttings']] == [x1], '?plant= gives just that plant\'s cuttings')
check(status('POST', '/api/cuttings', {'plant': a, 'method': 'Magic'}) == 400, 'an unknown way of taking cuttings is refused')
check(status('POST', '/api/cuttings', {'plant': a, 'method': 'Seed', 'started_on': ago(-1)}) == 400, 'a day still to come is refused')
check(status('POST', '/api/cuttings', {'plant': 'P-999', 'method': 'Seed'}) == 404, 'an unknown plant is refused')
call('PUT', f'/api/cuttings/{x1}', {'checked': True})
check(not {x['id']: x for x in R()['cuttings']}[x1]['look_due'], '"No roots yet" puts the next look a week away')
call('PUT', f'/api/cuttings/{x3}', {'stage': 'rooted'})
y = {x['id']: x for x in R()['cuttings']}[x3]
check(y['stage'] == 'rooted' and y['stage_on'] == today.isoformat() and y['rooted_after'] == 20 and not y['look_due'], 'Has roots records the day, and how long it took')
call('PUT', f'/api/cuttings/{x3}', {'stage': 'given', 'given_to': 'Grandma'})
y = {x['id']: x for x in R()['cuttings']}[x3]
check(y['stage'] == 'given' and y['given_to'] == 'Grandma' and not y['active'] and R()['counts']['done'] == 1, 'Given away to someone: finished, still listed')
audit = call('GET', '/api/audit?n=40')
check(any('given away (to Grandma)' in (e.get('note') or '') for e in audit) and any('Cuttings taken' in (e.get('note') or '') and e['plant_code'] == a for e in audit),
      'taking cuttings and changing their stage are in the audit log, under the plant they came from')
check(status('PUT', f'/api/cuttings/{x3}', {'stage': 'sold'}) == 400, 'an unknown stage is refused')
# viewers through Tailscale: the owner first, then a viewer
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
G = {'Tailscale-User-Login': 'sam@example.net', 'Tailscale-User-Name': 'Sam'}
try:
    call('GET', '/api/me', base=TS, h=E); call('GET', '/api/me', base=TS, h=G)
    check(status('GET', '/api/cuttings', base=TS, h=G) == 200 and status('POST', '/api/cuttings', {'plant': a, 'method': 'Seed'}, base=TS, h=G) == 403
          and status('PUT', f'/api/cuttings/{x1}', {'checked': True}, base=TS, h=G) == 403, 'a viewer can see cuttings but not add or change them')
except urllib.error.URLError: print('skip viewer test: port 8081 is not answering (start the mock server with MOCK_TS=1)')
x4 = call('POST', '/api/cuttings', {'plant': plants[3]['code'], 'method': 'Seed', 'medium': 'Potting mix', 'how_many': 12, 'started_on': ago(8)})['id']
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Cut Test')")
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#today-cut', timeout=15000)
    check(pg.inner_text('#today-cut h2') == 'Cuttings to look at (1)', 'Today has "Cuttings to look at" with the number due')
    jump = pg.locator('.td-jumps a[data-sec=today-cut]')
    check(jump.count() == 1 and jump.inner_text() == 'Cuttings (1)', 'and a jump button for it')
    pg.locator('#today-cut').screenshot(path=os.path.join(OUT, 'cuttings-1-today.png'))
    # the page in the Today row
    pg.goto(BASE + '/#/cuttings'); pg.wait_for_selector('#cut-due')
    check(pg.locator('#main-nav a[aria-current=page]').inner_text().strip().startswith('Today') and pg.locator('#sub-nav a[aria-current=page]').inner_text().strip() == 'Cuttings',
          'the page is in the Today row, as "Cuttings"')
    lab = pg.locator(f'[data-act=cutstage][data-id="{x2}"]').get_attribute('aria-label') or ''
    check('Has roots for the 2 leaf cuttings in potting mix from' in lab, f'buttons say which batch they are for: "{lab}"')
    pg.screenshot(path=os.path.join(OUT, 'cuttings-2-laptop.png'), full_page=True)
    # take cuttings from the page: the window asks for the plant
    pg.click('[data-act=cutadd]'); pg.wait_for_selector('dialog[open] select[name=plant]')
    check(all(pg.locator(f'dialog[open] label:has([name={n}])').count() == 1 for n in ('plant', 'method', 'medium', 'how_many', 'started_on', 'notes')), 'every field in the window has a real label')
    pg.screenshot(path=os.path.join(OUT, 'cuttings-3-add.png'))
    pg.select_option('dialog[open] select[name=plant]', a); pg.select_option('dialog[open] select[name=method]', 'Offsets or pups')
    pg.fill('dialog[open] [name=how_many]', '4'); pg.click('dialog[open] button[value=ok]'); pg.wait_for_timeout(1800)
    new = [x for x in R()['cuttings'] if x['method'] == 'Offsets or pups']
    check(len(new) == 1 and new[0]['how_many'] == 4 and new[0]['plant'] == a and new[0]['started_on'] == today.isoformat(), 'Save cuttings adds the batch, taken today')
    check(pg.locator(f'#cut-rooting [data-id="{new[0]["id"]}"]').count() >= 1, 'and it shows under Still rooting')
    # the weekly look and the stages, from the page
    pg.click(f'[data-act=cutstage][data-id="{x1}"]'); pg.wait_for_timeout(1800)
    check({x['id']: x for x in R()['cuttings']}[x1]['stage'] == 'rooted' and pg.locator(f'#cut-rooted [data-act=cutstage][data-stage=potted][data-id="{x1}"]').count() == 1,
          'Has roots moves the batch to "Has roots, waiting for a pot", with Potted up')
    check(pg.evaluate('document.activeElement.dataset.id') == str(x1), 'focus stays on the same batch after pressing a button')
    pg.click(f'[data-act=cutstage][data-stage=potted][data-id="{x1}"]'); pg.wait_for_timeout(1800)
    check({x['id']: x for x in R()['cuttings']}[x1]['stage'] == 'potted' and pg.locator(f'#cut-done [data-id="{x1}"]').count() >= 1, 'Potted up moves it to Finished')
    # change a batch: did not take
    pg.click(f'[data-act=cutedit][data-id="{x2}"]'); pg.wait_for_selector('dialog[open] select[name=stage]')
    pg.select_option('dialog[open] select[name=stage]', 'lost'); pg.click('dialog[open] button[value=ok]'); pg.wait_for_timeout(1800)
    check({x['id']: x for x in R()['cuttings']}[x2]['stage'] == 'lost', 'Change can set "Did not take"')
    # remove one, asking first
    nid = new[0]['id']
    pg.click(f'[data-act=cutedit][data-id="{nid}"]'); pg.wait_for_selector('dialog[open] button[value=remove]')
    pg.click('dialog[open] button[value=remove]'); pg.wait_for_selector('dialog[open] button.danger[value=ok]')
    check('Remove these cuttings from the record?' in pg.inner_text('dialog[open]'), 'Remove asks first')
    pg.click('dialog[open] button[value=ok]'); pg.wait_for_timeout(1800)
    check(all(x['id'] != nid for x in R()['cuttings']), 'and then takes the batch off the list')
    # a plant's own page
    pg.goto(BASE + f'/#/plant/{b}'); pg.wait_for_selector('#cut-plant', timeout=15000)
    check('Cuttings: none in progress.' in pg.inner_text('#cut-plant'), f'a plant whose cuttings are finished says none in progress: "{pg.inner_text("#cut-plant")[:60]}"')
    pg.click('#cut-plant [data-act=cutadd]'); pg.wait_for_selector('dialog[open] select[name=method]')
    check(pg.locator('dialog[open] select[name=plant]').count() == 0 and 'Take cuttings from' in pg.inner_text('dialog[open] h2'), 'from a plant\'s page the window knows the plant')
    pg.click('dialog[open] button[value=ok]'); pg.wait_for_timeout(2500)
    check('1 stem cutting, rooting (taken today)' in pg.inner_text('#cut-plant'), 'and the line then shows the new batch')
    check(pg.evaluate("document.activeElement.closest('#cut-plant') != null"), 'focus goes back to the cuttings line')
    pg.evaluate("document.querySelectorAll('#toasts > *').forEach(t => t.remove()); document.getElementById('cut-plant').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(200)
    pg.locator('.quick-btns >> xpath=..').screenshot(path=os.path.join(OUT, 'cuttings-4-plant.png'))
    pg.evaluate("document.documentElement.dataset.role = 'viewer'")
    check(pg.locator('[data-act^=cut]:visible').count() == 0, 'people who can only view do not see Take cuttings')
    pg.evaluate("document.documentElement.dataset.role = 'owner'")
    # phone, dark and large text
    x5 = call('POST', '/api/cuttings', {'plant': c3, 'method': 'Air layering', 'medium': 'Sphagnum moss', 'how_many': 1, 'started_on': ago(12)})['id']
    for name, disp in (('phone-light', {}), ('phone-dark-big', {'theme': 'dark', 'size': '160'})):
        ph = br.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        ph.on('pageerror', lambda e: errs.append(str(e)))
        ph.add_init_script("localStorage.setItem('plantdb.editor','Cut Test');localStorage.setItem('plantdb.display', JSON.stringify(%s))" % json.dumps(disp))
        ph.goto(BASE + '/#/cuttings'); ph.wait_for_selector('#cut-due'); ph.wait_for_timeout(800)
        over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 0, f'{name}: nothing scrolls sideways ({over}px)')
        ph.evaluate("window.scrollTo(0, document.querySelector('#app h1').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'cuttings-5-{name}.png'))
        ph.evaluate("window.scrollTo(0, document.getElementById('cut-rooting').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'cuttings-5-{name}-list.png'))
        ph.click('[data-act=cutadd]'); ph.wait_for_selector('dialog[open] select[name=plant]'); ph.wait_for_timeout(300)
        over = ph.evaluate("Math.max(document.querySelector('dialog[open]').scrollWidth - document.querySelector('dialog[open]').clientWidth, 0)")
        check(over <= 0, f'{name}: the window fits the phone ({over}px)')
        ph.screenshot(path=os.path.join(OUT, f'cuttings-6-{name}-add.png'))
        ph.keyboard.press('Escape')
        ph.goto(BASE + '/#/'); ph.wait_for_selector('#today-cut'); ph.wait_for_timeout(800)
        ph.evaluate("window.scrollTo(0, document.getElementById('today-cut').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'cuttings-7-today-{name}.png'))
        ph.close()
    br.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
