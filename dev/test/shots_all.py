"""Screenshots of every page, on each of Ethan's devices, with chosen Display settings (1.26.0, for the layout review).
python3 dev/test/shots_all.py OUTDIR [devices] [combos] [pages]
  devices: comma list of names from DEVICES (default all); combos: comma list from COMBOS (default all); pages: comma list (default all)
Fills the mock data with groups, a mushroom find and a wishlist entry first. Writes OUTDIR/<page>__<device>__<combo>.jpg and index.json."""
import io, json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
from PIL import Image
L = os.environ.get('SHOTS_URL', 'http://127.0.0.1:8080')
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
DEVICES = {   # name: (label, css width, css height of the page area, device pixel ratio, touch)
    'pc1080': ('1920 x 1080 monitor (100%)', 1920, 960, 1, False),
    'pc1440': ('2560 x 1440 monitor (150%)', 1707, 850, 1.5, False),
    's21u': ('Galaxy S21 Ultra', 384, 740, 3.75, True),
    'iphone11': ('iPhone 11', 414, 715, 2, True),
    'ipad6p': ('iPad 6th gen, upright', 768, 954, 2, True),
    'ipad6l': ('iPad 6th gen, sideways', 1024, 698, 2, True),
    'firep': ('Fire HD 10, upright', 800, 1200, 1.5, True),
    'firel': ('Fire HD 10, sideways', 1280, 720, 1.5, True),
}
USUAL = {'size': '100', 'space': 'normal', 'contrast': 'high', 'theme': 'light', 'navside': 'right', 'navopen': '0', 'width': 'wide', 'lines': 'full'}
COMBOS = {
    'usual': ('Your usual settings', USUAL),
    'largest': ('Largest text', dict(USUAL, size='190')),
    'stress': ('Largest, Roomy, High contrast, Dark', dict(USUAL, size='190', space='roomy', contrast='high', theme='dark')),
}
PAGES = [('today', 'Today', '#/'), ('plants', 'Plants', '#/plants'), ('plant', 'A plant page', '#/plant/P-012'), ('plantedit', 'Editing a plant', '#/plant/P-012/edit'),
         ('groups', 'Groups', '#/groups'), ('group', 'A group', '#/group/1'), ('today', 'Today', '#/today'), ('winter', 'Winter plan', '#/winter'),
         ('frost', 'Cold-night checklist', '#/frost'), ('inside', 'Getting plants ready to come inside', '#/inside'), ('outside', 'Back outside', '#/outside'),
         ('weather', 'Weather', '#/weather'), ('fertilizer', 'Fertilizer', '#/fertilizer'), ('lights', 'Grow lights', '#/lights'),
         ('identify', 'Identify', '#/identify'), ('library', 'Library', '#/library'), ('species', 'A species page', '#/species/Monstera%20deliciosa'),
         ('around', 'Around home', '#/around'), ('wishlist', 'Wishlist', '#/wishlist'), ('fungi', 'Mushrooms', '#/fungi'), ('find', 'A mushroom find', '#/fungi/F-001'),
         ('findnew', 'Adding a find', '#/fungi/new'), ('photos', 'Photos', '#/photos'), ('labels', 'Labels', '#/labels'), ('history', 'Audit log', '#/history'),
         ('backups', 'Backups', '#/backups'), ('offline', 'Offline use', '#/offline'), ('settings', 'Settings', '#/settings'), ('display', 'Display settings window', '#/?display')]
MAX_SCREENS = int(os.environ.get('SHOTS_SCREENS', '4'))          # long pages are cut after this many screens
def call(method, u, body=None):
    req = urllib.request.Request(L + u, data=None if body is None else json.dumps(body).encode(), method=method, headers={'Content-Type': 'application/json', 'X-Editor': 'Shots'})
    try:
        with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'{}')
    except urllib.error.HTTPError: return {}
def seed():
    if not call('GET', '/api/groups').get('groups'):
        call('POST', '/api/groups', {'name': 'Porch shelf', 'kind': 'picked', 'codes': ['P-%03d' % i for i in range(1, 13)]})
        call('POST', '/api/groups', {'name': 'Kitchen window', 'kind': 'picked', 'codes': ['P-%03d' % i for i in range(20, 26)]})
    if not call('GET', '/api/fungi').get('finds'):
        f = call('POST', '/api/fungi', {'fields': {'name': 'Yellow flowerpot parasol', 'scientific_name': 'Leucocoprinus birnbaumii', 'id_status': 'A guess', 'place_kind': 'In a plant pot',
                                                   'plant_code': 'P-012', 'substrate': 'Potting mix', 'underside': 'Gills', 'cap_colour': 'Bright yellow, powdery', 'notes': 'Came up after watering.'}})
    call('PUT', '/api/wishlist', {'name': 'Lupinus texensis', 'common_name': 'Texas bluebonnet', 'where_seen': 'Wildseed Farms'})
def want(arg, allk): return allk if not arg else [x for x in arg.split(',') if x]
devs = want(sys.argv[2] if len(sys.argv) > 2 else '', list(DEVICES)); combos = want(sys.argv[3] if len(sys.argv) > 3 else '', list(COMBOS))
pages = want(sys.argv[4] if len(sys.argv) > 4 else '', [p[0] for p in PAGES])
seed()
idx_path = os.path.join(OUT, 'index.json')
index = json.load(open(idx_path)) if os.path.exists(idx_path) else {'devices': {}, 'combos': {}, 'pages': {}, 'shots': {}}
index['devices'].update({k: v[0] for k, v in DEVICES.items()}); index['combos'].update({k: v[0] for k, v in COMBOS.items()}); index['pages'].update({p[0]: p[1] for p in PAGES})
with sync_playwright() as p:
    b = p.chromium.launch()
    for dk in devs:
        label, w, h, dpr, touch = DEVICES[dk]
        for ck in combos:
            prefs = COMBOS[ck][1]
            ctx = b.new_context(viewport={'width': w, 'height': h}, device_scale_factor=dpr, is_mobile=touch, has_touch=touch, service_workers='block')
            ctx.add_init_script(f"localStorage.setItem('plantdb.editor','Ethan');localStorage.setItem('plantdb.display',JSON.stringify({json.dumps(prefs)}));localStorage.removeItem('plantdb.filters')")
            pg = ctx.new_page()
            for key, title, h_ in PAGES:
                if key not in pages: continue
                disp = h_.endswith('?display')
                pg.goto(L + '/' + (h_.split('?')[0] if disp else h_)); pg.wait_for_timeout(2600)
                if disp: pg.evaluate("document.getElementById('display-btn').click()"); pg.wait_for_timeout(500)
                pg.evaluate("window.scrollTo(0,0)"); pg.wait_for_timeout(200)
                full = pg.evaluate("Math.min(document.documentElement.scrollHeight, innerHeight * %d)" % MAX_SCREENS)
                raw = pg.screenshot(full_page=False, clip=None) if disp else pg.screenshot(full_page=True, clip={'x': 0, 'y': 0, 'width': w, 'height': full})
                im = Image.open(io.BytesIO(raw)).convert('RGB')
                cap = (900 if w >= 700 else 700) if touch else 1400
                if im.width > cap: im = im.resize((cap, round(im.height * cap / im.width)))
                k = im.width / w                      # a dashed line where each screenful ends, so the pictures show how much fits before scrolling
                if not disp:
                    from PIL import ImageDraw
                    dr = ImageDraw.Draw(im)
                    for i in range(1, int(full / h) + 1):
                        y = round(i * h * k)
                        if y >= im.height - 2: break
                        for x in range(0, im.width, 24): dr.line([(x, y), (x + 13, y)], fill=(255, 0, 170), width=max(3, round(3 * k)))
                name = f'{key}__{dk}__{ck}.jpg'
                im.save(os.path.join(OUT, name), 'JPEG', quality=72, optimize=True)
                sw = pg.evaluate('document.documentElement.scrollWidth > innerWidth + 1')
                index['shots'][name] = {'page': key, 'device': dk, 'combo': ck, 'sideways': sw, 'screens': round(pg.evaluate('document.documentElement.scrollHeight / innerHeight'), 1)}
                json.dump(index, open(idx_path, 'w'), indent=0)
            ctx.close()
    b.close()
print('ok', len(index['shots']))
