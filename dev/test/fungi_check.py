"""Checks 1.22.0: mushroom finds on a page of their own (#/fungi). Adding a find with photos (the location in a photo's EXIF data is
saved with the find), the find's page, editing (with a warning when someone else changed it first), Identify against the fungi list
(dev/test/mock_vision.py), "Use this name (as a guess)", filters, archiving, the safety notes, fungi in the library with
"Record a find of this", people who can only view, and a phone with the largest text. Start the mock server with a fresh data
folder (MOCK_TS=1), then:
python3 dev/test/fungi_check.py      Screenshots: dev/tmp/shots/fungi-*.png"""
import io, json, os, sys, urllib.request, urllib.error
from PIL import Image
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
TMP = os.path.join(HERE, '..', 'tmp'); fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Fungi Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)   # the first person in is the owner

def photo(path, rgb, gps=None, taken=None):
    im = Image.new('RGB', (1200, 900), rgb); ex = Image.Exif()
    if taken: ex[306] = taken
    if gps: ex[0x8825] = gps
    im.save(path, 'JPEG', exif=ex)
    return path
p_gps = photo(os.path.join(TMP, 'find-gps.jpg'), (150, 120, 90), {1: 'N', 2: (30.0, 30.0, 36.0), 3: 'W', 4: (97.0, 40.0, 12.0)}, '2026:10:30 09:15:00')
p_plain = photo(os.path.join(TMP, 'find-plain.jpg'), (60, 60, 200))

# the API
st, d = call('GET', '/api/fungi')
check(st == 200 and d['finds'] == [] and 'Gills' in d['enums']['underside'], 'an empty list of finds, with the answers to choose from')
st, _ = call('POST', '/api/fungi', {'fields': {'name': 'x'}}, V, TS)
check(st == 403, 'someone who can only view cannot add a find')
st, _ = call('POST', '/api/fungi', {'fields': {'id_status': 'Edible!'}})
check(st == 400, 'only the listed answers are taken')
st, _ = call('POST', '/api/fungi', {'fields': {'place_kind': 'In a plant pot', 'plant_code': 'P-999'}})
check(st == 400, 'a plant pot that does not exist is refused')

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and '404' not in m.text and '409' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Fungi Test')")
    pg.goto(LOCAL + '/#/plants'); pg.wait_for_timeout(1500); pg.evaluate("localStorage.removeItem('plantdb.fungi')")
    if pg.locator('#pages-btn').is_visible(): pg.click('#pages-btn')       # 1.26.0: with less room the links fold behind Pages
    pg.click('#sub-nav a[data-nav=fungi]'); pg.wait_for_timeout(1500)
    check(pg.evaluate('location.hash') == '#/fungi' and pg.locator('h1').inner_text() == 'Mushroom finds', 'the menu has "Mushrooms", which opens the page of finds')
    check(pg.locator('#sub-nav a[data-nav=fungi][aria-current=page]').count() == 1, 'and marks it as the current page')
    t = pg.inner_text('main')
    check('Never eat a wild mushroom because of an app' in t and 'No finds yet' in t, 'a safety note, and an empty page that says what to do')
    for lab in ('Search', 'Name', 'Where', 'Year', 'Show'):
        check(pg.locator('.mu-filters label', has_text=lab).count() >= 1, f'filter "{lab}" has a label')
    # add a find
    pg.click('a:has-text("Add a find")'); pg.wait_for_timeout(1500)
    check(pg.evaluate('location.hash') == '#/fungi/new', '"Add a find" opens the form')
    for lab in ('Photos of the cap', 'Name', 'How sure is the name?', 'Found on', 'Where', 'Growing on', 'Under the cap', 'Cup or sac at the base', 'Spore print colour'):
        check(pg.locator('form label', has_text=lab).count() >= 1, f'the form has "{lab}"')
    check(pg.locator('#mu-plant_code').is_hidden(), 'the plant pot list is hidden until "In a plant pot" is chosen')
    pg.select_option('#mu-place_kind', 'In a plant pot'); pg.wait_for_timeout(200)
    check(pg.locator('#mu-plant_code').is_visible(), 'and shows when it is')
    pg.select_option('#mu-plant_code', 'P-001')
    pg.fill('#mu-name', 'Little yellow ones'); pg.select_option('#mu-substrate', 'Potting mix'); pg.select_option('#mu-underside', 'Gills')
    pg.fill('#mu-cap_colour', 'Bright yellow, powdery')
    pg.set_input_files('form[data-form=musave] input[name=photos]', [p_gps, p_plain])
    pg.screenshot(path=os.path.join(OUT, 'fungi-1-form.png'), full_page=True)
    pg.click('form[data-form=musave] button[type=submit]'); pg.wait_for_timeout(3000)
    check(pg.evaluate('location.hash') == '#/fungi/F-001', 'saving opens the new find, F-001')
    t = pg.inner_text('main')
    check('Little yellow ones' in t and 'P-001' in t and 'Potting mix' in t and 'Bright yellow, powdery' in t, 'its page shows what was entered, with a link to the plant')
    check('30.51000, -97.67000' in t and pg.locator('a[href*="openstreetmap.org"]').count() == 1, 'the location in the photo was saved with the find, with a map link')
    check('2 of 2' in pg.inner_text('#mu-gallery') or '1 of 2' in pg.inner_text('#mu-gallery'), 'both photos are there')
    check('Taken' in pg.inner_text('#mu-gallery') and 'Has a location' in pg.inner_text('#mu-gallery'), 'the photo says when it was taken and that it has a location')
    pg.screenshot(path=os.path.join(OUT, 'fungi-2-find.png'), full_page=True)
    # photos
    pg.click('[data-act=mustep][data-d="1"]'); pg.wait_for_timeout(300)
    check('2 of 2' in pg.inner_text('#mu-gallery') and pg.evaluate("document.activeElement.dataset.act") == 'mustep', 'Next photo steps on, and keeps the keyboard on the button')
    pg.click('[data-act=mumain]'); pg.wait_for_timeout(1500)
    f = call('GET', '/api/fungi/F-001')[1]
    check(f['photos'][0]['gps_lat'] is None and f['photos'][0]['is_primary'] == 1, '"Make this the main photo" works')
    # identify against the fungi list
    pg.click('[data-act=muident]'); pg.wait_for_selector('#mu-ident .id-sps', timeout=15000)
    t = pg.inner_text('#mu-ident')
    check('Leucocoprinus birnbaumii' in t, 'Identify the photo shown compares it with the fungi')
    pg.locator('[data-act=muusename]').first.click(); pg.wait_for_timeout(1500)
    f = call('GET', '/api/fungi/F-001')[1]
    check(f['scientific_name'] == 'Leucocoprinus birnbaumii' and f['id_status'] == 'A guess' and f['name'] == 'Little yellow ones', '"Use this name (as a guess)" saves the scientific name as a guess and keeps your own name')
    check('Name is a guess' in pg.inner_text('main'), 'the page says the name is a guess')
    # edit, and someone else changing it first
    pg.click('a:has-text("Edit this find")'); pg.wait_for_timeout(1500)
    check(pg.locator('#mu-name').input_value() == 'Little yellow ones' and pg.locator('#mu-plant_code').is_visible(), 'the edit form is filled in')
    call('PUT', '/api/fungi/F-001', {'base_version': f['version'], 'fields': {'smell': 'Earthy'}})
    pg.fill('#mu-smell', 'None'); pg.click('form[data-form=musave] button[type=submit]'); pg.wait_for_timeout(1500)
    check('Someone else changed F-001' in pg.inner_text('#form-err'), 'if someone else saved first, it says so and saves nothing')
    pg.reload(); pg.wait_for_timeout(1500)
    pg.fill('#mu-notes', 'Came up after the rain.\nGone two days later.'); pg.click('form[data-form=musave] button[type=submit]'); pg.wait_for_timeout(1500)
    check('Came up after the rain.' in pg.inner_text('main') and 'Earthy' in pg.inner_text('main'), 'after reloading, the change saves and keeps theirs')
    # a second find, by API, and the filters
    st, d2 = call('POST', '/api/fungi', {'fields': {'name': 'Big white one', 'found_on': '2025-06-01', 'place_kind': 'In the yard', 'id_status': 'Not identified yet'}})
    check(st == 201 and d2['code'] == 'F-002', 'a second find is F-002')
    pg.goto(LOCAL + '/#/fungi'); pg.wait_for_timeout(1500)
    cards = lambda: pg.locator('#mu-grid .mu-card').count()
    check(cards() == 2 and '2 of 2 finds shown' in pg.inner_text('#mu-count'), 'the page lists both finds')
    check(pg.locator('#mu-grid .mu-card[data-code="F-001"] .mat img').count() == 1 and pg.locator('#mu-grid .mu-card[data-code="F-002"] .nophoto').count() == 1, 'with their main photo, or "No photo yet"')
    pg.fill('input[data-f=muq]', 'yellow'); pg.wait_for_timeout(400)
    check(cards() == 1, 'search narrows as you type')
    pg.fill('input[data-f=muq]', ''); pg.select_option('select[data-f=muplace]', 'In the yard'); pg.wait_for_timeout(400)
    check(cards() == 1 and 'Big white one' in pg.inner_text('#mu-grid'), 'Where: In the yard')
    pg.select_option('select[data-f=muplace]', ''); pg.select_option('select[data-f=muyear]', '2025'); pg.wait_for_timeout(400)
    check(cards() == 1 and 'Big white one' in pg.inner_text('#mu-grid'), 'Year: 2025')
    pg.select_option('select[data-f=muyear]', ''); pg.select_option('select[data-f=muid]', 'A guess'); pg.wait_for_timeout(400)
    check(cards() == 1 and 'Little yellow ones' in pg.inner_text('#mu-grid'), 'Name: A guess')
    pg.reload(); pg.wait_for_timeout(1500)
    check(cards() == 1 and pg.locator('select[data-f=muid]').input_value() == 'A guess', 'the filters are remembered')
    pg.select_option('select[data-f=muid]', ''); pg.wait_for_timeout(300)
    pg.screenshot(path=os.path.join(OUT, 'fungi-3-list.png'), full_page=True)
    # archive
    pg.goto(LOCAL + '/#/fungi/F-002'); pg.wait_for_timeout(1500)
    pg.click('[data-act=muarch]'); pg.wait_for_timeout(1500)
    check('Archived' in pg.inner_text('.sp-head .tags'), 'Archive this find')
    pg.goto(LOCAL + '/#/fungi'); pg.wait_for_timeout(1500)
    check(cards() == 1, 'archived finds leave the list')
    pg.select_option('select[data-f=mustatus]', 'all'); pg.wait_for_timeout(1500)
    check(cards() == 2, '"Current and archived" shows them again')
    pg.select_option('select[data-f=mustatus]', 'active'); pg.wait_for_timeout(1000)
    # safety page
    pg.goto(LOCAL + '/#/fungi/safety'); pg.wait_for_timeout(1000)
    t = pg.inner_text('main')
    check('(888) 426-4435' in t and '1-800-222-1222' in t and 'volva' in t, 'the safety page has the poison lines for pets and people, and how to photograph a find')
    check('edible' not in t.lower().replace('edible ones', '').replace('edible one', ''), 'and never calls any mushroom edible')
    # fungi in the library and on the Identify page
    pg.goto(LOCAL + '/#/library?scope=fungi'); pg.wait_for_timeout(2500)
    check(pg.locator('select[data-f=libscope]').input_value() == 'fungi' and pg.locator('.lib-filters label', has_text='Kind of fungus').count() == 1, 'the library can look in "Fungi worldwide", with kinds of fungi')
    check(pg.locator('#lib-res .lib-card').count() == 5 and 'Mushroom' in pg.inner_text('#lib-res'), 'and lists them')
    pg.goto(LOCAL + '/#/species/Leucocoprinus%20birnbaumii'); pg.wait_for_timeout(2500)
    t = pg.inner_text('main')
    check('Never eat a wild mushroom' in t and 'F-001' in t and 'plants and lichens, not other fungi' in t, 'a fungus page has the safety note, your finds of it, and says the USDA lists have no range for it')
    check(pg.locator('[data-act=spnew]').count() == 0 and pg.locator('[data-act=munewfrom]').count() == 1, 'it offers "Record a find of this" instead of "Add to my plants"')
    pg.screenshot(path=os.path.join(OUT, 'fungi-4-species.png'), full_page=True)
    pg.click('[data-act=munewfrom]'); pg.wait_for_timeout(1500)
    check(pg.evaluate('location.hash') == '#/fungi/new' and pg.locator('#mu-scientific_name').input_value() == 'Leucocoprinus birnbaumii' and pg.locator('#mu-id_status').input_value() == 'A guess', '"Record a find of this" starts a find with the name filled in, as a guess')
    pg.goto(LOCAL + '/#/fungi'); pg.wait_for_timeout(1000); pg.goto(LOCAL + '/#/fungi/new'); pg.wait_for_timeout(1200)
    check(pg.locator('#mu-scientific_name').input_value() == '', 'and a later new find starts empty')
    pg.goto(LOCAL + '/#/identify'); pg.wait_for_timeout(1500)
    check(pg.locator('select[data-f=idscope] option[value=fungi]').count() == 1, 'Identify can look in the fungi list')
    # audit log
    st, a = call('GET', '/api/audit?kind=fungi')
    check(st == 200 and any(x['plant_code'] == 'F-001' and x['action_word'] == 'Mushroom find' for x in a), 'changes to finds are in the Audit log under "Mushroom finds"')
    # a viewer
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    vw.on('pageerror', lambda e: errs.append(str(e)))
    vw.goto(TS + '/#/fungi'); vw.wait_for_timeout(2000)
    check(vw.locator('#mu-grid .mu-card').count() == 1 and not vw.locator('a:has-text("Add a find")').is_visible(), 'someone who can only view sees the finds, without "Add a find"')
    vw.goto(TS + '/#/fungi/F-001'); vw.wait_for_timeout(2000)
    hidden = all(not vw.locator(s).first.is_visible() for s in ('a:has-text("Edit this find")', '[data-act=muarch]', '[data-act=mucap]', '[data-act=murmphoto]', '.mu-add'))
    check(hidden and vw.locator('[data-act=muident]').is_visible(), 'nor the buttons that change it, but can still use Identify')
    # a phone with the largest text
    ph = b.new_page(viewport={'width': 390, 'height': 844})
    ph.on('pageerror', lambda e: errs.append(str(e)))
    ph.add_init_script("localStorage.setItem('plantdb.editor','Fungi Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    for u in ('/#/fungi', '/#/fungi/F-001', '/#/fungi/new', '/#/fungi/safety'):
        ph.goto(LOCAL + u); ph.wait_for_timeout(2000)
        check(ph.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'{u}: no sideways scrolling on a phone with the largest text')
    ph.goto(LOCAL + '/#/fungi/F-001'); ph.wait_for_timeout(2000)
    ph.screenshot(path=os.path.join(OUT, 'fungi-5-phone.png'))
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
