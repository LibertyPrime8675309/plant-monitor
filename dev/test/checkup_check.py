"""Checks the health walk-through (prototype proto/health-walk): #/checkup chooses the plants, #/checkup/walk shows one at a
time, "Looks the same" logs care kind 'looked', a new rating is saved on the plant page, a change made elsewhere meanwhile is
caught, and the Today page links to it. Start the mock server with a fresh data folder, then:
python3 dev/test/checkup_check.py      Screenshots: dev/tmp/shots/checkup-*.png"""
import io, json, os, random, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
BASE = 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Walk Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
D = call('GET', '/api/checkup')
check(D['plants'] and all(p['due'] and p['last_looked'] is None for p in D['plants']), 'on a fresh install every plant is due (health ratings from upgrade batches do not count as a look)')
call('POST', '/api/care', {'plant': 'P-003', 'kind': 'looked', 'note': 'Looks the same'})
p3 = next(p for p in call('GET', '/api/checkup')['plants'] if p['code'] == 'P-003')
check(p3['days'] == 0 and not p3['due'], 'a "looked" entry makes the plant not due')
# how often: the usual number, Poor or Critical sooner, and a group's own number (the shortest wins)
cd = lambda code, d=None: next(p for p in (d or call('GET', '/api/checkup'))['plants'] if p['code'] == code)
check(D['due_days'] == 14 and D['poor_days'] == 7 and all(p['every'] == (7 if p['health'] in ('Poor', 'Critical') else 14) for p in D['plants']),
      'by default plants are due every 14 days, and every 7 when their health is Poor or Critical')
g1 = call('POST', '/api/groups', {'name': 'Walk test A', 'kind': 'picked', 'codes': ['P-003', 'P-010']})['id']
g2 = call('POST', '/api/groups', {'name': 'Walk test B', 'kind': 'picked', 'codes': ['P-003']})['id']
call('PUT', f'/api/checkup/groups/{g1}', {'days': 30}); call('PUT', f'/api/checkup/groups/{g2}', {'days': 21})
x = call('GET', '/api/checkup')
check(cd('P-010', x)['every'] in (30, 7) and cd('P-003', x)['every'] in (21, 7) and 'Walk test B' in (cd('P-003', x)['every_why'] if cd('P-003', x)['every'] == 21 else 'Walk test B'),
      "a group's own number applies to its plants, and a plant in two groups goes by the shorter")
check(next(g for g in x['groups'] if g['id'] == g1)['days'] == 30, 'the groups list carries each one\'s number')
call('PUT', f'/api/checkup/groups/{g1}', {'days': None})
check(cd('P-010')['every'] in (14, 7), 'emptying it goes back to the usual number')
x = call('PUT', '/api/checkup/settings', {'days': 10, 'poor_days': 3})
check(x['due_days'] == 10 and x['poor_days'] == 3, 'the usual numbers can be changed')
try: call('PUT', '/api/checkup/settings', {'days': 0, 'poor_days': 3}); bad = False
except urllib.error.HTTPError as e: bad = e.code == 400
check(bad, 'a number outside 1 to 365 is refused')
call('PUT', '/api/checkup/settings', {'days': 14, 'poor_days': 7})
indoor = [p for p in D['plants'] if p['site'] == 'Covered porch']
shot = lambda pg, name: pg.screenshot(path=os.path.join(OUT, f'checkup-{name}.png'), full_page=True)
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Walk Test');localStorage.removeItem('plantdb.checkup')")
    pg.goto(BASE + '/#/today'); pg.wait_for_timeout(3000)
    link = pg.locator('.ck-today a[href="#/checkup"]')
    check(link.count() == 1 and 'looked over' in pg.locator('.ck-today').inner_text(), 'Today has one line about the walk-through, with a link')
    link.click(); pg.wait_for_timeout(2000)
    check(pg.locator('h1').inner_text() == 'Health walk-through', 'the link opens the walk-through')
    total = len(D['plants']) - 1
    check(f'{total} plants are due' in pg.locator('.verdict-box').inner_text(), 'it says how many plants are due')
    check(pg.locator('#ck-count').inner_text() == f'This walk-through has {total} plants.', 'it says how many plants the walk will have')
    pg.locator('form[data-form=ckstart] label', has_text='Covered porch').click(); pg.wait_for_timeout(300)
    check(pg.locator('#ck-count').inner_text() == f'This walk-through has {len(indoor)} plants.', 'choosing Where updates the count')
    pg.locator('form[data-form=ckstart] label', has_text='By plant code').click()
    shot(pg, 'laptop-setup')
    pg.locator('form[data-form=ckstart] button[type=submit]').click(); pg.wait_for_timeout(1200)
    first = sorted(indoor, key=lambda p: p['code'])[0]
    check(f'Plant 1 of {len(indoor)}' in pg.locator('.ck-prog').inner_text(), 'the walk shows "Plant 1 of N"')
    check(first['code'] in pg.locator('#ck-name').inner_text(), 'plants come in the chosen order (by code)')
    check(pg.evaluate("document.activeElement && document.activeElement.id") == 'ck-name', 'the plant name has the keyboard focus, so a screen reader reads it')
    check(pg.locator('#ck-save').inner_text().startswith('Looks the same'), 'with the health unchanged, the button says "Looks the same"')
    shot(pg, 'laptop-card')
    pg.locator('#ck-save').click(); pg.wait_for_timeout(1500)
    log = [e for e in call('GET', f"/api/care?plant={first['code']}") if e['kind'] == 'looked']
    check(len(log) == 1 and log[0]['note'] == 'Looks the same', '"Looks the same" logs one "Looked over" entry')
    check('Plant 2 of' in pg.locator('.ck-prog').inner_text(), 'and moves on to the next plant')
    second = sorted(indoor, key=lambda p: p['code'])[1]
    new = 'Poor' if second['health'] != 'Poor' else 'Good'
    pg.locator('.ck-health label', has_text=new).click(); pg.wait_for_timeout(200)
    check(pg.locator('#ck-save').inner_text() == f'Save "{new}" and go on', 'choosing another rating changes the button to say so')
    pg.fill('form[data-form=cksave] textarea', 'Yellow lower leaves')
    n0 = len(call('GET', f"/api/plants/{second['code']}")['photos'])
    from PIL import Image
    im = Image.new('RGB', (900, 700)); rnd = random.Random(4)
    im.putdata([(rnd.randrange(60, 200), rnd.randrange(90, 220), rnd.randrange(40, 160)) for _ in range(900 * 700)])
    buf = io.BytesIO(); im.save(buf, 'JPEG', quality=90)
    pg.locator('input[data-act=ckphoto]').set_input_files({'name': 'walk.jpg', 'mimeType': 'image/jpeg', 'buffer': buf.getvalue()}); pg.wait_for_timeout(2500)
    if pg.locator('#dlg form.pchk').count() and pg.locator('#dlg form.pchk').is_visible(): pg.locator('#dlg button[value=all]').click(); pg.wait_for_timeout(2000)
    check(len(call('GET', f"/api/plants/{second['code']}")['photos']) == n0 + 1, 'Take a photo adds a photo to the plant')
    check('The photo you just took' in pg.locator('.ck-photo').inner_text(), 'and shows it on the card')
    check(pg.locator('form[data-form=cksave] textarea').input_value() == 'Yellow lower leaves' and pg.locator(f'.ck-health input[value="{new}"]').is_checked(),
          'taking a photo keeps the note and the rating chosen')
    shot(pg, 'laptop-photo')
    pg.locator('#ck-save').click(); pg.wait_for_timeout(1500)
    pp = call('GET', f"/api/plants/{second['code']}")
    check(pp['health_rating'] == new, 'a new rating is saved on the plant page')
    log = [e for e in call('GET', f"/api/care?plant={second['code']}") if e['kind'] == 'looked']
    check(log and log[0]['note'] == f"Health {second['health']} to {new}. Yellow lower leaves", 'and logged as "Looked over" with what changed and the note')
    check(pp['health_summary'].endswith(f"(health walk-through): {second['health']} to {new}. Yellow lower leaves.") and pp['health_summary'].startswith(second['summary'][:40]),
          'the note is added at the end of the Health summary, with the date and the change')
    third = sorted(indoor, key=lambda p: p['code'])[2]
    pg.locator('[data-act=ckskip]').click(); pg.wait_for_timeout(1000)
    check('Plant 4 of' in pg.locator('.ck-prog').inner_text() and not [e for e in call('GET', f"/api/care?plant={third['code']}") if e['kind'] == 'looked'], 'Skip moves on without logging anything')
    pg.locator('[data-act=ckback]').click(); pg.wait_for_timeout(1000)
    check(third['code'] in pg.locator('#ck-name').inner_text(), 'Back goes to the previous plant')
    # someone else changes this plant meanwhile: saving is refused, and the page shows what it is now
    cur = call('GET', f"/api/plants/{third['code']}")
    other = 'Critical' if cur['health_rating'] != 'Critical' else 'Fair'
    call('PUT', f"/api/plants/{third['code']}", {'base_version': cur['version'], 'fields': {'health_rating': other}})
    pick = 'Good' if other != 'Good' else 'Poor'
    pg.locator('.ck-health label', has_text=pick).click(); pg.locator('#ck-save').click(); pg.wait_for_timeout(1500)
    check(third['code'] in pg.locator('#ck-name').inner_text() and f'Health: {other}' in pg.locator('.ck-body').inner_text(),
          'a change made elsewhere since the walk started is caught: the plant stays, showing its new rating')
    check(call('GET', f"/api/plants/{third['code']}")['health_rating'] == other, 'and nothing was written over it')
    pg.locator('#ck-save').click(); pg.wait_for_timeout(1500)
    pg.locator('[data-act=ckstop]').click(); pg.wait_for_timeout(1000)
    txt = pg.locator('#app').inner_text()
    check(pg.locator('h1').inner_text() == 'Walk-through paused' and 'You looked over 3 plants, and 1 has a new health rating' in txt, 'Stop shows what was done')
    shot(pg, 'laptop-done')
    pg.locator('[data-act=ckresume]').first.click(); pg.wait_for_timeout(1000)
    check('Plant 4 of' in pg.locator('.ck-prog').inner_text(), 'Carry on goes back to where you stopped')
    plant_care = pg.goto(BASE + f"/#/plant/{second['code']}"); pg.wait_for_timeout(2500)
    check('Looked over' in pg.locator('.care-log').inner_text(), 'the plant page care log shows "Looked over"')
    pg.goto(BASE + f'/#/group/{g2}'); pg.wait_for_timeout(2500)
    gw = pg.locator('#g-walk')
    check(gw.count() == 1 and 'every 21 days' in gw.inner_text(), "a group page has a Health walk-through section with the group's number")
    gw.locator('input[name=days]').fill('5'); gw.locator('button[type=submit]').click(); pg.wait_for_timeout(2000)
    check('every 5 days' in pg.locator('#g-walk').inner_text() and next(g for g in call('GET', '/api/checkup')['groups'] if g['id'] == g2)['days'] == 5, 'the number can be changed there')
    pg.locator('#g-walk').scroll_into_view_if_needed(); pg.screenshot(path=os.path.join(OUT, 'checkup-laptop-group.png'))
    pg.goto(BASE + '/#/checkup'); pg.wait_for_timeout(2000)
    check('Walk test B: every 5 days' in pg.locator('#ck-how-often').inner_text(), 'the walk-through page lists the groups with their own number')
    pg.select_option('form[data-form=ckstart] select[name=group]', str(g2)); pg.wait_for_timeout(300)
    pg.locator('#ck-how-often').scroll_into_view_if_needed(); shot(pg, 'laptop-setup2')
    # phone, dark, large text
    for name, vp, prefs in (('phone-dark', {'width': 390, 'height': 844}, '{"theme":"dark","size":"190"}'), ('phone-light', {'width': 390, 'height': 844}, '{"size":"135"}')):
        ph = b.new_page(viewport=vp, device_scale_factor=2)
        ph.on('pageerror', lambda e: errs.append(str(e)))
        ph.add_init_script(f"localStorage.setItem('plantdb.editor','Walk Test');localStorage.setItem('plantdb.display','{prefs}')")
        ph.goto(BASE + '/#/checkup'); ph.wait_for_timeout(2500)
        check(ph.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'{name}: no sideways scrolling on the setup page')
        shot(ph, name + '-setup')
        ph.locator('form[data-form=ckstart] button[type=submit]').click(); ph.wait_for_timeout(1500)
        check(ph.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), f'{name}: no sideways scrolling on a plant')
        shot(ph, name + '-card')
        ph.goto(BASE + '/#/today'); ph.wait_for_timeout(3000)
        ph.locator('.ck-today').scroll_into_view_if_needed()
        ph.screenshot(path=os.path.join(OUT, f'checkup-{name}-today.png'))
        ph.close()
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs) if errs else ''))
print('\n' + ('All checks passed' if not fails else f'{len(fails)} failed'))
raise SystemExit(1 if fails else 0)
