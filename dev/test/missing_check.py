"""Checks the prototype "Missing details" (proto/missing-details): /api/missing lists, detail by detail, the active plants that do not
have a detail other pages need; filling one in on #/missing saves it to the plant's page (with its version and audit row), in the
person's units; the link on All plants; at laptop and phone width, light and dark, with large text. Start the mock server with a
fresh data folder, then:  python3 dev/test/missing_check.py      Screenshots: dev/tmp/shots/missing-*.png"""
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
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Missing Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
M = lambda q='': call('GET', '/api/missing' + q)
D = lambda m, k: next(d for d in m['details'] if d['key'] == k)
codes = lambda m, k: [p['code'] for p in D(m, k)['plants']]
def put(code, fields):
    p = call('GET', '/api/plants/' + code)
    return call('PUT', '/api/plants/' + code, {'base_version': p['version'], 'fields': fields})

m0 = M()
check([d['key'] for d in m0['details']] == ['pot_size', 'leaf_type', 'height_in', 'temp_damage_below', 'water', 'feed', 'pet_safety'],
      'seven details, in a fixed order')
check(all(d['why'] and d['title'] for d in m0['details']), 'each says what it is for')
plants = [p for p in call('GET', '/api/plants') if p.get('status', 'active') == 'active' and not p.get('home_id')]
check(set(codes(m0, 'height_in')) == {p['code'] for p in plants if call('GET', '/api/plants/' + p['code']).get('height_in') in (None, '')}, 'Height lists exactly the plants with no height')
check(set(codes(m0, 'pot_size')) == {p['code'] for p in plants if not p.get('pot_size')}, 'Pot size lists exactly the plants with no pot size')
check(m0['plants_with'] == len({c for d in m0['details'] for c in [p['code'] for p in d['plants']]}) and m0['gaps'] == sum(len(d['plants']) for d in m0['details']),
      'the counts add up')
# make some gaps the fresh install does not have
a, b, c3, e = sorted(codes(m0, 'height_in'))[:4]
put(a, {'temp_damage_below': ''})
put(b, {'water_every_days': '', 'soil_moisture_low': ''})
put(c3, {'fert_from_month': ''})
put(e, {'pet_safety': '', 'leaf_type': ''})
m1 = M()
check(a in codes(m1, 'temp_damage_below') and b in codes(m1, 'water') and c3 in codes(m1, 'feed') and e in codes(m1, 'pet_safety') and e in codes(m1, 'leaf_type'),
      'a plant with no cold limit, no watering rhythm, part of its feeding months, no pet safety or leaf type is listed under each')
put(c3, {'fert_strength': 'None needed'})
check(c3 not in codes(M(), 'feed'), 'a plant that needs no feeding is not asked for feeding months')
put(b, {'grow_kind': 'Semi-hydro'})
check(b not in codes(M(), 'water'), 'a semi-hydro plant is not asked how often to check for water')
put(b, {'grow_kind': ''})
one = M('?plant=' + a)
check(one['plants'] == 1 and all(set(p['code'] for p in d['plants']) <= {a} for d in one['details']) and a in codes(one, 'temp_damage_below'),
      '?plant= gives just that plant')
call('POST', f'/api/plants/{e}/status', {'archived': True})
check(e not in codes(M(), 'pet_safety'), 'archived plants are left out')
call('POST', f'/api/plants/{e}/status', {'archived': False})

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda x: errs.append(str(x)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Missing Test')")
    pg.goto(BASE + '/#/plants'); pg.wait_for_selector('#ms-link', timeout=15000)
    check(f"{M()['plants_with']} plants are missing details" in pg.inner_text('#ms-link'), 'All plants says how many plants are missing details, with a link')
    pg.click('#ms-link a'); pg.wait_for_selector('#ms-pot_size')
    check(pg.inner_text('main h1') == 'Missing details' and 'Missing details' in pg.title(), 'the link opens Missing details')
    check(pg.locator('#main-nav a[data-sec=plants][aria-current=page]').count() == 1, 'the page counts as part of Plants in the top bar')
    check(pg.locator('#sub-nav a[aria-current=page]').count() == 0, 'and does not mark All plants as the page you are on')
    m = M()
    for d in m['details']:
        n = len(d['plants'])
        if n: check(pg.inner_text(f"#ms-{d['key']} h2") == f"{d['title']} ({n})" and pg.locator(f"#ms-{d['key']} .job").count() == n, f"{d['title']}: heading and {n} rows")
    check(pg.locator('.ms-jumps a').count() == sum(1 for d in m['details'] if d['plants']), 'a jump button for each detail with gaps')
    pg.screenshot(path=os.path.join(OUT, 'missing-1-top.png'))
    labels_ok = pg.evaluate("""[...document.querySelectorAll('.ms-form select, .ms-form input')].every(x => x.labels.length && x.getAttribute('aria-label').startsWith(x.labels[0].textContent.replace(/ \\(.*\\)$/, '')))""")
    check(labels_ok, 'every box has a visible label, and its spoken name starts with it and names the plant')
    # pot size from the list
    first = codes(m, 'pot_size')[0]; nxt = codes(m, 'pot_size')[1]
    v0 = call('GET', '/api/plants/' + first)['version']
    row = pg.locator(f'#ms-pot_size .job[data-code="{first}"]')
    row.locator('select').select_option('Medium: fits in a big tub'); row.locator('button[type=submit]').click(); pg.wait_for_timeout(1500)
    got = call('GET', '/api/plants/' + first)
    check(got['pot_size'] == 'Medium: fits in a big tub' and got['version'] == v0 + 1, 'Save sets the pot size on the plant page, as a new page version')
    check(first not in codes(M(), 'pot_size') and pg.locator(f'#ms-pot_size .job[data-code="{first}"]').count() == 0, 'and the plant leaves the list')
    check('Saved: Pot size for' in pg.inner_text('#toasts'), 'a message says what was saved')
    check(pg.evaluate(f"document.activeElement && document.activeElement.closest('.job') && document.activeElement.closest('.job').dataset.code") == nxt,
          'focus moves to the next plant in the same list')
    aud = call('GET', f'/api/audit?n=20')
    check(any(x.get('plant_code') == first and 'Filled in on Missing details' in (x.get('note') or '') for x in aud), 'the change is in the audit log')
    # an empty box is not saved
    row = pg.locator(f'#ms-pot_size .job[data-code="{nxt}"]'); row.locator('button[type=submit]').click(); pg.wait_for_timeout(600)
    check(not call('GET', '/api/plants/' + nxt)['pot_size'], 'Save with nothing chosen saves nothing')
    # height and the cold limit, in the person's units (centimetres and Celsius)
    pg.evaluate("localStorage.setItem('plantdb.units', JSON.stringify({region: 'metric'}))"); pg.reload(); pg.wait_for_selector('#ms-height_in')
    h = codes(M(), 'height_in')[0]
    row = pg.locator(f'#ms-height_in .job[data-code="{h}"]')
    check('(cm)' in row.locator('label').inner_text(), 'Height asks in centimetres when that is the unit')
    row.locator('input').fill('38'); row.locator('input').press('Enter'); pg.wait_for_timeout(1500)
    check(abs(float(call('GET', '/api/plants/' + h)['height_in']) - 15.0) < 0.06, '38 cm is saved as 15 inches; Enter saves too')
    row = pg.locator(f'#ms-temp_damage_below .job[data-code="{a}"]')
    check('(°C)' in row.locator('label').inner_text(), 'the cold limit asks in °C when that is the unit')
    row.locator('input').fill('-1'); row.locator('button[type=submit]').click(); pg.wait_for_timeout(1500)
    check(call('GET', '/api/plants/' + a)['temp_damage_below'] == 30, '-1 °C is saved as 30 °F')
    pg.evaluate("localStorage.removeItem('plantdb.units')")
    call('PUT', '/api/me/prefs', {'units': None})          # the units are kept for the person on the server too
    pg.reload(); pg.wait_for_selector('#ms-water')
    row = pg.locator(f'#ms-water .job[data-code="{b}"]'); row.locator('input').fill('9'); row.locator('button[type=submit]').click(); pg.wait_for_timeout(1500)
    check(call('GET', '/api/plants/' + b)['water_every_days'] == 9, 'How often to check for water sets "Check for water every (days)"')
    check(pg.locator(f'#ms-feed .job[data-code="{c3}"]').count() == 0, '(the plant that needs no feeding is not under Feeding months)')
    put(c3, {'fert_strength': ''}); pg.reload(); pg.wait_for_selector('#ms-feed')
    lk = pg.locator(f'#ms-feed .job[data-code="{c3}"] a.btn')
    check(lk.inner_text() == 'Open Edit' and lk.get_attribute('href') == f'#/plant/{c3}/edit', 'Feeding months opens the plant\'s Edit page')
    # someone else changed the plant in between: nothing is overwritten
    t = codes(M(), 'pot_size')[0]
    put(t, {'notes': 'changed elsewhere'})
    row = pg.locator(f'#ms-pot_size .job[data-code="{t}"]'); row.locator('select').select_option('Small: fits in a bucket'); row.locator('button[type=submit]').click(); pg.wait_for_timeout(1500)
    check(not call('GET', '/api/plants/' + t)['pot_size'] and 'changed by someone else' in pg.inner_text('#toasts'), 'a plant changed elsewhere since the list loaded is not overwritten, and it says so')
    # viewers
    pg.evaluate("document.documentElement.dataset.role = 'viewer'")
    check(pg.locator('.ms-form:visible').count() == 0, 'people who can only view see the list but not the boxes')
    pg.evaluate("document.documentElement.dataset.role = 'owner'")
    # one plant
    pg.goto(BASE + f'/#/missing?plant={e}'); pg.wait_for_selector(f'a[href="#/plant/{e}"]'); pg.wait_for_timeout(500)
    check(pg.locator('.job').count() == sum(1 for d in M('?plant=' + e)['details'] for _ in d['plants']) and 'Back to ' + e in pg.inner_text('main'), '#/missing?plant= shows one plant, with a link back to it')
    # phone, dark and large text
    for name, disp in (('phone-light', {}), ('phone-dark-big', {'theme': 'dark', 'size': '160'})):
        ph = br.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        ph.on('pageerror', lambda x: errs.append(str(x)))
        ph.add_init_script("localStorage.setItem('plantdb.editor','Missing Test');localStorage.setItem('plantdb.units', JSON.stringify({region: 'us'}));localStorage.setItem('plantdb.display', JSON.stringify(%s))" % json.dumps(disp))
        ph.goto(BASE + '/#/missing'); ph.wait_for_selector('#ms-pot_size'); ph.wait_for_timeout(800)
        over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 0, f'{name}: nothing scrolls sideways ({over}px)')
        ph.evaluate("window.scrollTo(0, document.querySelector('#app h1').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'missing-2-{name}.png'))
        ph.evaluate("window.scrollTo(0, document.getElementById('ms-height_in').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'missing-3-{name}-rows.png'))
        ph.close()
    br.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
