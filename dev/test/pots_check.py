"""Checks 1.29.0: pots and catch trays as items, and editing in place. Each has a shape, sizes in inches, material, drainage (pots),
how many you have, a "3 / 5 in use" count with links to the plants, and photos; the square feet are worked out (a circle as the
square around it); the Grow lights page uses a plant's tray, else its pot; and fields on the light cards and a plant's own page
save when you leave them. Start the mock server with a fresh data folder (MOCK_TS=1), then:
python3 dev/test/pots_check.py      Screenshots: dev/tmp/shots/pots-*.png"""
import io, json, os, urllib.request, urllib.error
from PIL import Image
from playwright.sync_api import sync_playwright
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
    pg.goto(TS + '/#/pots'); pg.wait_for_timeout(3000)
    card = pg.locator(f'#ct-{pot["id"]}')
    check('3 / 2 in use' in card.inner_text() and 'more in use than you have' in card.inner_text(), 'the card shows the in-use counter next to the quantity')
    q = card.locator('[data-k=qty]'); q.fill('6'); q.press('Enter'); pg.wait_for_timeout(1500)
    check('3 / 6 in use' in pg.locator(f'#ct-{pot["id"]}').inner_text(), 'typing a new quantity saves it and updates the counter')
    sh = pg.locator(f'#ct-{pot["id"]} [data-k=shape]'); sh.select_option('square'); pg.wait_for_timeout(1500)
    check(pg.locator(f'#ct-{pot["id"]} [data-k=len_in]').count() == 1, 'changing the shape to square asks for the side')
    side = pg.locator(f'#ct-{pot["id"]} [data-k=len_in]'); side.fill('12'); side.press('Tab'); pg.wait_for_timeout(1500)
    check('1 sq ft' in pg.locator(f'#ct-{pot["id"]}').inner_text(), 'a 12 in square pot covers 1 sq ft')
    nm = pg.locator(f'#ct-{pot["id"]} [data-k=name]'); nm.fill('Changed name'); nm.press('Escape'); pg.wait_for_timeout(400)
    check(nm.input_value() == '8 in terracotta', 'Escape puts back what was there')
    pg.locator(f'#ct-{pot["id"]} [data-f=ctmat]').select_option('__other'); pg.wait_for_timeout(300)
    o = pg.locator(f'[data-other="{pot["id"]}"] input'); o.fill('Glazed ceramic'); o.press('Tab'); pg.wait_for_timeout(1500)
    check([i for i in call('GET', '/api/containers')[1]['items'] if i['id'] == pot['id']][0]['material'] == 'Glazed ceramic', 'a material of your own can be typed')
    im = Image.new('RGB', (300, 300), (180, 90, 40)); fp = os.path.join(HERE, '..', 'tmp', 'pot.jpg'); im.save(fp)
    pg.locator(f'#ct-{pot["id"]} input[type=file]').set_input_files(fp); pg.wait_for_timeout(2000)
    check(pg.locator(f'#ct-{pot["id"]} .ct-photos img').count() == 1, 'a photo can be added')
    pg.screenshot(path=os.path.join(OUT, 'pots-1-page.png'), full_page=True)
    # light cards and plant pages, edited in place
    pg.goto(TS + '/#/lights'); pg.wait_for_timeout(3000)
    lid = L['lights'][0]['id']
    pg.locator(f'[data-act=ltedit][data-id="{lid}"]').click(); pg.wait_for_timeout(300)      # 1.39.1: the fields wait behind a button
    m = pg.locator(f'[data-ed=light][data-id="{lid}"][data-k=model]'); m.fill('TEST-MODEL-1'); m.press('Tab'); pg.wait_for_timeout(1500)
    check([l for l in call('GET', '/api/lights')[1]['lights'] if l['id'] == lid][0]['specs']['model'] == 'TEST-MODEL-1', 'a light\'s model saves when you leave the box')
    f0 = [l for l in call('GET', '/api/lights')[1]['lights'] if l['id'] == lid][0]
    check(f0['count'] == L['lights'][0]['count'] and f0['fixture'] == L['lights'][0]['fixture'], 'and nothing else on the light changes')
    pg.goto(TS + '/#/plant/P-022'); pg.wait_for_timeout(3000)
    check(pg.locator('#pl-ed').is_hidden() and 'Change these details' in pg.inner_text('#details'), '1.56.5: a plant\'s details read as text until you press Change these details')
    pg.click('[data-act=pledit]'); pg.wait_for_timeout(300)
    sel = pg.locator('[data-ed=plant][data-k=tray_id]'); sel.select_option(str(tray['id'])); pg.wait_for_timeout(2500)
    check(plant('P-022')['tray_id'] == tray['id'], 'a plant\'s catch tray is chosen right on its page')
    al = pg.locator('[data-ed=plant][data-k=aliases]'); al.fill('Test alias'); al.press('Tab'); pg.wait_for_timeout(1500)
    check(plant('P-022')['aliases'] == 'Test alias', 'and its other names are typed there too')
    pg.click('[data-act=pledit]'); pg.wait_for_timeout(2000)
    check(pg.locator('#pl-ed').is_hidden() and 'Test alias' in pg.inner_text('#details'), 'Done changing shows the details as text again, with the change')
    pg.screenshot(path=os.path.join(OUT, 'pots-2-plant.png'))
    v = b.new_context(viewport={'width': 1280, 'height': 900}, extra_http_headers=V).new_page()
    v.goto(TS + '/#/pots'); v.wait_for_timeout(3000)
    check(v.locator('[data-act=ctadd]').count() == 0 and v.locator('[data-k=qty][readonly]').count() >= 1, 'someone who can only view sees the items but cannot change them')
    ph = b.new_context(viewport={'width': 384, 'height': 740}, is_mobile=True, has_touch=True, service_workers='block', extra_http_headers=E)
    ph.add_init_script("localStorage.setItem('plantdb.editor','Ethan');localStorage.setItem('plantdb.morefilters','1');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    qq = ph.new_page(); qq.on('pageerror', lambda e: errs.append(str(e)))
    qq.goto(TS + '/#/pots'); qq.wait_for_timeout(3000)
    check(not qq.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'on a phone with the largest text nothing scrolls sideways')
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All pots checks passed' if not fails else f'{len(fails)} pots check(s) failed'))
raise SystemExit(1 if fails else 0)
