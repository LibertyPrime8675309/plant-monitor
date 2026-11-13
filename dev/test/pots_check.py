"""Checks 1.29.0: pots and catch trays as items, and editing in place. Each has a shape, sizes in inches, material, drainage (pots),
how many you have, a "3 / 5 in use" count with links to the plants, and photos; the square feet are worked out (a circle as the
square around it); the Grow lights page uses a plant's tray, else its pot; and fields on the light cards and a plant's own page
save when you leave them. Start the mock server with a fresh data folder (MOCK_TS=1), then:
python3 dev/test/pots_check.py      Screenshots: dev/tmp/shots/pots-*.png"""
import io, json, os, urllib.request, urllib.error
from PIL import Image
from playwright.sync_api import sync_playwright
from waits import until, redrawn             # 1.58.0: these wait for the thing itself; the fixed pauses here were too short once on GitHub
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Pots Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)
plant = lambda c: call('GET', '/api/plants/' + c)[1]

st, pot = call('POST', '/api/containers', {'kind': 'pot', 'name': '8 in terracotta', 'shape': 'circle', 'dia_in': 8, 'height_in': 7, 'drainage': True, 'material': 'Terracotta', 'qty': 5})
check(st == 201 and pot['sqft'] == round(64 / 144, 2) and pot['size'] == '8 in across, 7 in tall', 'a round pot counts as the square around it (8 x 8 in = 0.44 sq ft)')
st, tray = call('POST', '/api/containers', {'kind': 'tray', 'name': 'Big rectangle tray', 'shape': 'rectangle', 'len_in': 24, 'wid_in': 12, 'material': 'Thin plastic', 'qty': 2})
check(st == 201 and tray['sqft'] == 2.0 and tray['drainage'] is None, 'a 24 x 12 in tray covers 2 sq ft, and trays have no drainage field')
check(call('POST', '/api/containers', {'kind': 'pot', 'name': 'x', 'qty': 'lots'})[0] == 400, 'a quantity that is not a number is refused')
check(call('POST', '/api/containers', {'kind': 'pot', 'name': 'x'}, h=V, base=TS)[0] == 403, 'someone who can only view cannot add one')
for code in ('P-014', 'P-022', 'P-030'):
    pl = plant(code); call('PUT', f'/api/plants/{code}', {'base_version': pl['version'], 'fields': {'pot_id': pot['id']}})
pl = plant('P-030'); call('PUT', '/api/plants/P-030', {'base_version': pl['version'], 'fields': {'tray_id': tray['id']}})
x = [i for i in call('GET', '/api/containers')[1]['items'] if i['id'] == pot['id']][0]
check(x['in_use'] == 3 and x['free'] == 2 and {p['code'] for p in x['plants']} == {'P-014', 'P-022', 'P-030'}, 'the pot shows 3 of 5 in use, 2 free, with the plants that use it')
st, x2 = call('PUT', f'/api/containers/{pot["id"]}', {'qty': 2})
check(st == 200 and x2['free'] == -1 and x2['qty'] == 2, 'the quantity can be changed on its own; more in use than you have is allowed and shown')
check(call('DELETE', f'/api/containers/{pot["id"]}')[0] == 409, 'a pot in use cannot be removed')
check(call('PUT', '/api/plants/P-014', {'base_version': plant('P-014')['version'], 'fields': {'pot_id': 99999}})[0] == 400, 'a pot that is not in the list is refused')
# grow lights use the tray, else the pot
L = call('GET', '/api/lights')[1]
check(L['lights'], 'the Grow lights page still works')

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1920, 'height': 1080}, extra_http_headers=E)
    ctx.add_init_script("localStorage.setItem('plantdb.editor','Ethan');localStorage.setItem('plantdb.morefilters','1')")
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(TS + '/#/pots')
    CARD = f'#ct-{pot["id"]}'; text = lambda: pg.locator(CARD).inner_text()        # the card is drawn again after every save, so it is looked up each time
    item = lambda: [i for i in call('GET', '/api/containers')[1]['items'] if i['id'] == pot['id']][0]
    check(until(pg, lambda: '3 / 2 in use' in text() and 'more in use than you have' in text()), 'the card shows the in-use counter next to the quantity')
    pg.wait_for_timeout(1500)                                                      # a page shown from what was saved last time is checked once more just after: let that pass
    again = redrawn(pg, CARD); q = pg.locator(CARD + ' [data-k=qty]'); q.fill('6'); q.press('Enter')
    check(again() and until(pg, lambda: '3 / 6 in use' in text()), 'typing a new quantity saves it and updates the counter')
    again = redrawn(pg, CARD); pg.locator(CARD + ' [data-k=shape]').select_option('square')
    check(again() and until(pg, lambda: pg.locator(CARD + ' [data-k=len_in]').count() == 1), 'changing the shape to square asks for the side')
    again = redrawn(pg, CARD); side = pg.locator(CARD + ' [data-k=len_in]'); side.fill('12'); side.press('Tab')
    check(again() and until(pg, lambda: '1 sq ft' in text()), 'a 12 in square pot covers 1 sq ft')
    nm = pg.locator(CARD + ' [data-k=name]'); nm.fill('Changed name'); nm.press('Escape')
    check(until(pg, lambda: nm.input_value() == '8 in terracotta'), 'Escape puts back what was there')
    pg.locator(CARD + ' [data-f=ctmat]').select_option('__other')
    o = pg.locator(f'[data-other="{pot["id"]}"] input'); o.wait_for(); again = redrawn(pg, CARD); o.fill('Glazed ceramic'); o.press('Tab')
    check(again() and until(pg, lambda: item()['material'] == 'Glazed ceramic'), 'a material of your own can be typed')
    im = Image.new('RGB', (300, 300), (180, 90, 40)); fp = os.path.join(HERE, '..', 'tmp', 'pot.jpg'); im.save(fp)
    pg.locator(CARD + ' input[type=file]').set_input_files(fp)
    check(until(pg, lambda: pg.locator(CARD + ' .ct-photos img').count() == 1), 'a photo can be added')
    pg.screenshot(path=os.path.join(OUT, 'pots-1-page.png'), full_page=True)
    # light cards and plant pages, edited in place
    pg.goto(TS + '/#/lights')
    lid = L['lights'][0]['id']
    ed = pg.locator(f'[data-act=ltedit][data-id="{lid}"]'); ed.wait_for(); pg.wait_for_timeout(1500); ed.click()      # 1.39.1: the fields wait behind a button
    m = pg.locator(f'[data-ed=light][data-id="{lid}"][data-k=model]'); m.wait_for(); m.fill('TEST-MODEL-1'); m.press('Tab')
    check(until(pg, lambda: [l for l in call('GET', '/api/lights')[1]['lights'] if l['id'] == lid][0]['specs'].get('model') == 'TEST-MODEL-1'), 'a light\'s model saves when you leave the box')
    f0 = [l for l in call('GET', '/api/lights')[1]['lights'] if l['id'] == lid][0]
    check(f0['count'] == L['lights'][0]['count'] and f0['fixture'] == L['lights'][0]['fixture'], 'and nothing else on the light changes')
    pg.goto(TS + '/#/plant/P-022')
    check(until(pg, lambda: pg.locator('#pl-ed').is_hidden() and 'Change these details' in pg.inner_text('#details')), '1.56.5: a plant\'s details read as text until you press Change these details')
    pg.wait_for_timeout(1500); pg.click('[data-act=pledit]')
    ALIASES = '[data-ed=plant][data-k=aliases]'
    sel = pg.locator('[data-ed=plant][data-k=tray_id]'); sel.wait_for(); again = redrawn(pg, ALIASES); sel.select_option(str(tray['id']))      # a new tray draws the whole page again
    check(until(pg, lambda: plant('P-022')['tray_id'] == tray['id']) and again(), 'a plant\'s catch tray is chosen right on its page')
    al = pg.locator(ALIASES); al.fill('Test alias'); al.press('Tab')
    check(until(pg, lambda: plant('P-022')['aliases'] == 'Test alias'), 'and its other names are typed there too')
    pg.click('[data-act=pledit]')
    check(until(pg, lambda: pg.locator('#pl-ed').is_hidden() and 'Test alias' in pg.inner_text('#details')), 'Done changing shows the details as text again, with the change')
    pg.screenshot(path=os.path.join(OUT, 'pots-2-plant.png'))
    v = b.new_context(viewport={'width': 1280, 'height': 900}, extra_http_headers=V).new_page()
    v.goto(TS + '/#/pots')
    check(until(v, lambda: v.locator('[data-k=qty][readonly]').count() >= 1) and v.locator('[data-act=ctadd]').count() == 0, 'someone who can only view sees the items but cannot change them')
    ph = b.new_context(viewport={'width': 384, 'height': 740}, is_mobile=True, has_touch=True, service_workers='block', extra_http_headers=E)
    ph.add_init_script("localStorage.setItem('plantdb.editor','Ethan');localStorage.setItem('plantdb.morefilters','1');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    qq = ph.new_page(); qq.on('pageerror', lambda e: errs.append(str(e)))
    qq.goto(TS + '/#/pots'); until(qq, lambda: qq.locator(f'#ct-{pot["id"]}').count() == 1); qq.wait_for_timeout(1000)
    check(not qq.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'on a phone with the largest text nothing scrolls sideways')
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All pots checks passed' if not fails else f'{len(fails)} pots check(s) failed'))
raise SystemExit(1 if fails else 0)
