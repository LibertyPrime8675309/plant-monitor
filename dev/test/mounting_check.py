"""Checks lights that fit the room (PLAN.md step 8, 1.56.0; plantdb/fit.py, js/fit.js): how each light holds (batch C4) and
"How it holds"; a room's or shelf's measurements and photos; a plant's height (its page, the edit form, the health walk-through);
each light spot saying whether its light fits there before its light is counted, in sentences (the side table with nothing
above it, the tall brown shelf too narrow for the 2 ft T8 but right for a 1 ft T5, a plant too tall for the level, a sideways
light shading the plants behind a tall one, "Not checked" when a measurement is missing); the same in the spot's dialog as it
is set up; the setup card and "Set up and checked", which clears when the spot changes; Today's list of spots to check; the
"would suit" suggestion never pointing at a spot the plant cannot go; room photos on the sitter sheet; a viewer; phone width,
dark and large text. Start the mock server with a fresh data folder, then: python3 dev/test/mounting_check.py [http://127.0.0.1:8080]
Screenshots: dev/tmp/shots/mounting-*.png"""
import io, json, os, sys, tempfile, urllib.error, urllib.request
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = BASE.rsplit(':', 1)[0] + ':' + str(int(BASE.rsplit(':', 1)[1]) + 1)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, base=BASE, login=None):
    h = {'Content-Type': 'application/json', 'X-Editor': 'Fit Test'}
    if login: h.update({'Tailscale-User-Login': login, 'Tailscale-User-Name': login.split('@')[0].title()})
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None, headers=h, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def status(m, url, body=None, **kw):
    try: call(m, url, body, **kw); return 200
    except urllib.error.HTTPError as e: return e.code
def plant_set(code, fields):
    v = call('GET', '/api/plants/' + code)['version']
    return call('PUT', '/api/plants/' + code, {'base_version': v, 'fields': fields})
shot = lambda pg, name, **kw: pg.screenshot(path=os.path.join(OUT, f'mounting-{name}.png'), **kw)

# ---- 8a: how each light holds (batch C4)
LT = call('GET', '/api/lights')
key = {L['key']: L for L in LT['lights']}
check(all(L['mount'] for L in LT['lights']), f'every one of the {len(LT["lights"])} lights says how it holds (batch C4)')
check(key['sansi-t8']['mount'] == {'kind': 'under', 'points': 'down', 'length_in': 24} and 'at least 24 in long' in key['sansi-t8']['mount_words'], 'the 2 ft T8 screws under a surface at least 24 in long')
check(key['sansi-tripod']['mount']['points'] == 'angled' and 'not straight down' in key['sansi-tripod']['mount_words'], 'the tripod cannot point straight down')
check(key['barrina-standing']['mount']['kind'] == 'surface' and 'sideways' in key['barrina-standing']['mount_words'], 'the 2 ft standing light stands on a surface and lights sideways')
check('socket' in key['sansi-80w']['mount_words'] and key['sansi-pot-clip']['mount'].get('pot_rim'), 'the bulbs screw into a socket; the pot clip can clip onto a pot rim')
check(status('PUT', f'/api/lights/{key["gooingtop-clip"]["id"]}', {'mount': {'kind': 'bolted'}}) == 400, 'an unknown way of holding is refused')
# ---- 8b, 8c: the places, and the plants with heights
place = {p['label'].split(', ')[-1]: p['id'] for p in LT['places']}
side, tall = place['Side Table'], place['Tall Brown Shelf']
P = call('GET', f'/api/rooms/{side}')
check(P['sheet'].get('levels') == 1 and P['sheet'].get('top') == 'nothing' and 'nothing above the top' in P['words'], 'batch C4 says the side table is one level with nothing above it')
TB = call('GET', f'/api/rooms/{tall}')
check(TB['sheet'].get('gaps_in') == [23, 13, 27] and TB['sheet'].get('width_in') == 22 and 'Measurements to come' not in TB['sheet'].get('notes', ''),
      'batch C7: the tall brown shelf has its measurements, a height for each level (23, 13, 27 in from the bottom)')
call('PUT', f'/api/rooms/{tall}', {'sheet': {'levels': 4, 'gap_in': 13, 'width_in': 16, 'depth_in': 11, 'top': 'nothing', 'edge': 'yes', 'edge_in': 0.75, 'socket': 'yes'}})
check('4 levels, 13 in between them' in call('GET', f'/api/rooms/{tall}')['words'], 'the tall brown shelf takes its measurements: 4 levels, 13 in apart, 16 in wide')
check(status('PUT', f'/api/rooms/{tall}', {'sheet': {'levels': 0}}) == 400 and status('PUT', f'/api/rooms/{tall}', {'sheet': {'edge': 'maybe'}}) == 400, 'measurements out of range are refused')
cands = [c['code'] for c in LT['candidates']]
big, small, mid, other, b1, b2, b3 = cands[:7]          # a plant is in one spot at a time, so each spot has its own
for code, h in ((big, 16), (small, 8), (mid, 10), (b1, 8), (b2, 10), (b3, 16)): plant_set(code, {'height_in': str(h)})
check(call('GET', '/api/plants/' + big)['height_in'] == 16, f'{big} is 16 in tall with its pot (a plant field)')
check(status('PUT', '/api/plants/' + other, {'base_version': call('GET', '/api/plants/' + other)['version'], 'fields': {'height_in': '9000'}}) == 400, 'a height out of range is refused')
# ---- 8d: spots, each saying whether its light fits
def spot(name, light, place_id, plants, **kw):
    return call('POST', '/api/lights/spots', {'name': name, 'light': key[light]['id'], 'distance': kw.pop('distance', 12), 'hours': 12, 'place': place_id, 'plants': plants, **kw})['id']
s_t8side = spot('T8 over the side table', 'sansi-t8', side, [other])
s_t8tall = spot('T8 in the tall shelf', 'sansi-t8', tall, [big, small], level='lower', distance=6)
s_t5tall = spot('T5 in the tall shelf', 'barrina-t5', tall, [mid], level='lower', distance=3)
s_bar = spot('Barrina by the side table', 'barrina-standing', side, [b3, b1, b2], distance=8)
s_bulb = spot('Bulb on the side table', 'sansi-80w', side, [])
s_noplace = spot('Nowhere yet', 'sansi-10w', None, [])
check(status('POST', '/api/lights/spots', {'name': 'x', 'light': key['sansi-t8']['id'], 'distance': 6, 'hours': 12, 'level': 'middle'}) == 400, 'a level other than top or lower is refused')
F = {s['id']: s for s in call('GET', '/api/lights')['spots']}
f = lambda sid: F[sid]['fit']
txt = lambda sid: ' '.join(x['text'] for x in f(sid)['lines'])
check(f(s_t8side)['status'] == 'nofit' and 'The Side Table has nothing above it, so a strip has nowhere to be fixed' in txt(s_t8side), 'the T8 over the side table: does not fit, nothing above it to fix a strip to')
check('tripod' in txt(s_t8side).lower(), 'and it names a light of yours that would reach it (the tripod beside it, or a clamp)')
check(f(s_t8tall)['status'] == 'nofit' and f'levels are 16 in wide; the {key["sansi-t8"]["name"]} needs 24 in' in txt(s_t8tall) and 'Barrina 1 ft T5' in txt(s_t8tall),
      'the T8 in the tall brown shelf: the levels are 16 in wide, it needs 24, and the 1 ft T5 fits')
check(any(x['kind'] == 'tall' and big in x['text'] and '13 in clear' in x['text'] for x in f(s_t8tall)['lines']), f'{big} at 16 in is too tall for a level with 13 in clear')
check(not any(x['kind'] == 'tall' and small in x['text'] for x in f(s_t8tall)['lines']), f'{small} at 8 in fits under it')
check(f(s_t5tall)['status'] == 'fits' and 'It screws under the shelf above (16 in wide; it needs 12 in)' in txt(s_t5tall), 'the T5 in the tall brown shelf fits: it screws under the shelf above')
check(f(s_bar)['status'] == 'unchecked' and 'free surface' in txt(s_bar) and any(x['kind'] == 'shaded' for x in f(s_bar)['lines']),
      'the sideways Barrina: not checked until the free surface is known, and it warns that the 16 in plant shades the ones behind')
check('Put the shortest nearest the light' in txt(s_bar), 'and says to put the shortest nearest the light')
check(f(s_bulb)['status'] == 'unchecked' and 'screws into here' in txt(s_bulb), 'a bulb: not checked until the spot says what it screws into')
check(f(s_noplace)['status'] == 'unchecked' and 'Choose where this spot is' in txt(s_noplace), 'a spot with no place: not checked, choose where it is')
check(all(x['word'] and x['text'] and not x['text'].startswith(('Fits:', 'Not checked:')) for s in F.values() for x in s['fit']['lines']), 'every line has its own word and a sentence that does not repeat it')
# the dialog's live check (preview) and the "would suit" suggestion
pv = call('GET', f'/api/lights/preview?light={key["sansi-t8"]["id"]}&distance=12&hours=12&dim=100&units=1&plants={other}&place={side}')
check(pv['fit']['status'] == 'nofit', 'the spot dialog asks the same check while a spot is being set up')
low_need = [p for p in F[s_t5tall]['plants']]
# ---- 8e: set up and checked
check(F[s_t5tall]['checked'] is None, 'a new spot is not set up and checked yet')
U = call('GET', '/api/lights/unchecked')
check({x['id'] for x in U['spots']} == {s_t8side, s_t8tall, s_t5tall, s_bar}, "Today's list: the spots with plants in them that are not checked yet")
call('POST', f'/api/lights/spots/{s_t5tall}/checked', {'note': 'Fixed with the magnets'})
ch = {s['id']: s for s in call('GET', '/api/lights')['spots']}[s_t5tall]['checked']
check(ch and not ch['stale'] and ch['note'] == 'Fixed with the magnets' and ch['by'] == 'Fit Test', 'Set up and checked records who, when and what they found')
check(s_t5tall not in {x['id'] for x in call('GET', '/api/lights/unchecked')['spots']}, 'and it leaves the list')
call('POST', f'/api/lights/spots/{s_t5tall}/plants', {'add': [other]})
ch = {s['id']: s for s in call('GET', '/api/lights')['spots']}[s_t5tall]['checked']
check(ch and ch['stale'], 'adding a plant to the spot clears the tick: "changed since it was checked"')
check(next(x for x in call('GET', '/api/lights/unchecked')['spots'] if x['id'] == s_t5tall)['changed'], 'and Today says it was changed since')
call('POST', f'/api/lights/spots/{s_t5tall}/checked', {'note': ''})
# ---- the sitter sheet: room and shelf photos
from PIL import Image
tmpd = tempfile.mkdtemp()
pic = os.path.join(tmpd, 'shelf.jpg'); Image.new('RGB', (800, 600), (120, 90, 60)).save(pic, 'JPEG')
pic2 = os.path.join(tmpd, 'shelf2.jpg'); Image.new('RGB', (800, 600), (60, 90, 120)).save(pic2, 'JPEG')

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 1000})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Fit Test')")
    pg.goto(BASE + '/#/lights'); pg.wait_for_selector('#lt-spots', timeout=20000)
    summ = pg.inner_text('#lt-spots')
    check(summ.count('Does not fit') >= 2 and 'Fits' in summ and 'Not checked yet' in summ, 'each folded spot says Fits, Does not fit or Not checked yet in words')
    card = pg.locator(f'details.lt-spot-fold[data-id="{s_t8tall}"]')
    card.locator('summary').click(); pg.wait_for_timeout(300)
    t = card.inner_text()
    check('16 in wide' in t and 'Too tall for the level' in t and 'Not set up and checked yet' in t, 'opened, the spot shows each reason, and that it is not checked yet')
    card.screenshot(path=os.path.join(OUT, 'mounting-1-spot-nofit.png'))
    lc = pg.locator('article.lt-light', has_text=key['sansi-t8']['name']).first
    check('How it holds' in lc.inner_text() and 'at least 24 in long' in lc.inner_text(), "the light's card says how it holds")
    # How it holds, for the GooingTop (keyboard)
    pg.locator(f'[data-act=ltmount][data-id="{key["gooingtop-clip"]["id"]}"]').focus(); pg.keyboard.press('Enter')
    pg.wait_for_selector('form[data-mount]')
    check(pg.locator('form[data-mount] [name=grip_in]').is_visible() and not pg.locator('form[data-mount] [name=length_in]').is_visible(), 'How it holds shows only the numbers a clamp has')
    pg.fill('form[data-mount] [name=grip_in]', '1.5'); pg.fill('form[data-mount] [name=reach_in]', '10')
    pg.locator('form[data-mount]').screenshot(path=os.path.join(OUT, 'mounting-2-mount.png'))
    pg.click('form[data-mount] button[value=ok]'); pg.wait_for_selector('#lt-spots', timeout=10000); pg.wait_for_timeout(600)
    check('up to 1.5 in thick' in pg.locator('article.lt-light', has_text='GooingTop').inner_text(), 'saved: it clamps to an edge up to 1.5 in thick')
    # Measurements and photos, for the side table
    pg.locator(f'[data-act=ltplace][data-id="{side}"]').first.click(); pg.wait_for_selector('form[data-place]')
    pg.set_input_files('form[data-place] input[type=file]', [pic, pic2]); pg.wait_for_selector('#pd-photos figure:nth-child(2)', timeout=10000)
    check(pg.locator('#pd-photos figure').count() == 2 and 'Main photo' in pg.inner_text('#pd-photos'), 'two photos added from the dialog; the first is the main photo')
    pg.locator('#pd-photos [data-act=placephotomain]').first.click(); pg.wait_for_timeout(600)
    check(pg.locator('#pd-photos [data-act=placephotomain]').count() == 1, 'Make it the main photo swaps which is main')
    pg.fill('form[data-place] [name=free_in]', '7'); pg.select_option('form[data-place] [name=edge]', 'no')
    pg.locator('form[data-place]').screenshot(path=os.path.join(OUT, 'mounting-3-place.png'))
    pg.click('form[data-place] button[value=ok]'); pg.wait_for_selector('#lt-spots', timeout=10000); pg.wait_for_timeout(800)
    F = {s['id']: s for s in call('GET', '/api/lights')['spots']}
    check(F[s_bar]['fit']['status'] == 'fits' and '7 in free; its base needs 5 in' in ' '.join(x['text'] for x in F[s_bar]['fit']['lines']),
          'with 7 in free beside the plants, the Barrina fits on the side table (its base needs 5 in)')
    check(pg.locator(f'#lt-rooms img.fit-pthumb').count() >= 1, 'the side table shows its main photo under Rooms and shelves')
    # the spot dialog: the live check, and what a bulb screws into
    pg.locator(f'details.lt-spot-fold[data-id="{s_bulb}"] summary').click()
    pg.locator(f'[data-act=spotedit][data-id="{s_bulb}"]').click(); pg.wait_for_selector('#sp-fitbox .fit', timeout=10000)
    check(not pg.locator('#sp-holder-f').is_hidden() and 'Not checked' in pg.inner_text('#sp-fitbox'), 'for a bulb the dialog asks what it screws into, and says Not checked until it is chosen')
    pg.select_option('form[data-spot] [name=holder]', 'clamp'); pg.wait_for_timeout(900)
    check('no edge to clamp to' in pg.inner_text('#sp-fitbox'), 'a clamp lamp on the side table: it has no edge to clamp to')
    pg.select_option('form[data-spot] [name=holder]', 'base'); pg.wait_for_timeout(900)
    check('Fits' in pg.inner_text('#sp-fitbox') and 'A lamp with a base stands on the Side Table' in pg.inner_text('#sp-fitbox'), 'a lamp with a base fits beside the plants')
    pg.select_option('form[data-spot] [name=light]', str(key['barrina-t5']['id'])); pg.wait_for_timeout(900)
    check(pg.locator('#sp-holder-f').is_hidden() and 'nothing above it' in pg.inner_text('#sp-fitbox'), 'a strip light chosen instead: no socket question, and it does not fit over the side table')
    pg.locator('form[data-spot]').screenshot(path=os.path.join(OUT, 'mounting-4-dialog.png'))
    pg.click('form[data-spot] button[value=cancel]')
    # the setup card, and Set up and checked from it
    pg.goto(BASE + f'/#/lightcard/{s_bar}'); pg.wait_for_selector('.fit-card', timeout=10000)
    t = pg.inner_text('.fit-card')
    check('Setup card: Barrina by the side table' in t and 'nearest the light first' in t and 'Fits' in t, 'the setup card: the spot, where, how the light holds, the fit, and the plants nearest the light first')
    names = [x.split('\n')[0] for x in pg.locator('.fit-card-plants li').all_inner_texts()]
    hs = [call('GET', '/api/plants/' + c)['common_name'] for c in (b1, b2, b3)]
    check(all(n in names[i] for i, n in enumerate(hs)), 'the plants are listed shortest first (8, 10 then 16 in)')
    check(pg.locator('.fit-card img.fit-card-photo').count() == 1, 'with the side table\'s main photo')
    shot(pg, '5-card', full_page=True)
    pg.click('.fit-card [data-act=spotcheck]'); pg.fill('dialog form [name=note]', 'Base fits behind the pots'); pg.click('dialog form button[value=ok]')
    pg.wait_for_selector('.fit-card .fit-checked:has-text("Set up and checked")', timeout=10000); pg.wait_for_timeout(300)
    check('Base fits behind the pots' in pg.inner_text('.fit-card'), 'Set up and checked from the card, with what was found')
    pg.goto(BASE + f'/#/lightcard/{s_t5tall}'); pg.wait_for_selector('.fit-card', timeout=10000)
    # Today
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#fit-unchecked', timeout=20000)
    t = pg.inner_text('#fit-unchecked'); n = len(call('GET', '/api/lights/unchecked')['spots'])
    check(f'Light spots to set up and check ({n})' in t and 'T8 in the tall shelf' in t and 'Barrina' not in t, f'Today lists the {n} spot(s) with plants still to set up and check, not the ones ticked')
    check(pg.locator(f'text=Light spots ({n})').count() >= 1, 'with a jump button in the summary')
    pg.locator('#fit-unchecked').screenshot(path=os.path.join(OUT, 'mounting-6-today.png'))
    # a plant's height on its page, and the health walk-through
    pg.goto(BASE + f'/#/plant/{other}'); pg.wait_for_selector('[data-act=pledit]', timeout=20000); pg.click('[data-act=pledit]')   # 1.57.0: the details open to change
    pg.fill('[data-ed=plant][data-k=height_in]', '11'); pg.keyboard.press('Tab'); pg.wait_for_timeout(1200)
    check(call('GET', '/api/plants/' + other)['height_in'] == 11, 'the height is set on the plant page and saves when you leave the box')
    pg.goto(BASE + '/#/checkup'); pg.wait_for_selector('button.ck-big[type=submit]', timeout=20000)
    pg.locator('button.ck-big[type=submit]').first.click(); pg.wait_for_selector('form[data-form=cksave]', timeout=10000)
    check(pg.locator('form[data-form=cksave] [name=height]').count() == 1 and 'Taller than last time' in pg.inner_text('form[data-form=cksave]'), 'the health walk-through asks "Taller than last time?"')
    code = pg.locator('.ck-title a').inner_text().strip()
    pg.fill('form[data-form=cksave] [name=height]', '21'); pg.click('#ck-save'); pg.wait_for_timeout(1500)
    check(call('GET', '/api/plants/' + code)['height_in'] == 21, f'and saves the new height for {code}')
    br.close()

# the "would suit" suggestion never points at a spot the plant cannot go (unit tests cover the rule; here the data shape)
F = {s['id']: s for s in call('GET', '/api/lights')['spots']}
check(all('clear_in' in s['fit'] for s in F.values()), "each spot's check says how much clear height its level has, for the suggestion")
# the sitter sheet: a photo of each shelf or room the plants are on
sp_row = call('GET', '/api/where')['homes'][0]
st_spot = next(sp for a in sp_row['areas'] for sp in a['spots'] if sp['name'] == 'Side Table')
area_id = next(a['id'] for a in sp_row['areas'] if any(sp['id'] == st_spot['id'] for sp in a['spots']))
plant_set(b1, {'area_id': str(area_id), 'spot_id': str(st_spot['id'])})
d0 = date.today() + timedelta(days=1)
S = call('GET', f'/api/sitter?from={d0}&to={d0 + timedelta(days=6)}')
check(any(pl['label'].endswith('Side Table') and pl['photo'] for pl in S.get('places', [])) or not any(p['code'] == b1 for p in S['plants']),
      'the sitter sheet carries a photo of the side table, where one of its plants is')
# a viewer sees the fit but none of the buttons that change things
call('GET', '/api/me', base=TS, login='owner@example.com')
call('PUT', '/api/people', {'login': 'viewer@example.com', 'role': 'viewer'}, base=TS, login='owner@example.com')
check(status('POST', f'/api/lights/spots/{s_t8tall}/checked', {}, base=TS, login='viewer@example.com') == 403
      and status('PUT', f'/api/rooms/{side}', {'sheet': {}}, base=TS, login='viewer@example.com') == 403, 'a viewer cannot tick a spot or change measurements')
with sync_playwright() as p:
    br = p.chromium.launch()
    for name, vp, disp, base, login in (('viewer', {'width': 1280, 'height': 900}, {}, TS, 'viewer@example.com'),
                                         ('phone-dark-big', {'width': 390, 'height': 844}, {'theme': 'dark', 'size': '160'}, BASE, None)):
        ctx = br.new_context(viewport=vp, device_scale_factor=2 if 'phone' in name else 1,
                             extra_http_headers={'Tailscale-User-Login': login, 'Tailscale-User-Name': 'Vee'} if login else {})
        ph = ctx.new_page(); ph.on('pageerror', lambda e: errs.append(str(e)))
        ph.add_init_script("localStorage.setItem('plantdb.editor','Phone');localStorage.setItem('plantdb.display', JSON.stringify(%s))" % json.dumps(disp))
        ph.goto(base + '/#/lights'); ph.wait_for_selector('#lt-spots', timeout=20000); ph.wait_for_timeout(600)
        if name == 'viewer':
            check(all(ph.locator(f'[data-act={a}]').evaluate_all('els => els.every(e => !e.offsetParent)') for a in ('ltmount', 'ltplace', 'spotcheck')),
                  'a viewer sees no How it holds, Measurements and photos, or Set up and checked buttons')
            check('Does not fit' in ph.inner_text('#lt-spots'), 'but sees whether each light fits')
        else:
            ph.locator(f'details.lt-spot-fold[data-id="{s_t8tall}"] summary').click(); ph.wait_for_timeout(300)
            over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            check(over <= 0, f'{name}: the Grow lights page does not scroll sideways ({over}px)')
            ph.locator(f'details.lt-spot-fold[data-id="{s_t8tall}"]').screenshot(path=os.path.join(OUT, 'mounting-7-phone-spot.png'))
            ph.goto(BASE + f'/#/lightcard/{s_bar}'); ph.wait_for_selector('.fit-card', timeout=10000); ph.wait_for_timeout(500)
            over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            check(over <= 0, f'{name}: the setup card does not scroll sideways ({over}px)')
            ph.screenshot(path=os.path.join(OUT, 'mounting-8-phone-card.png'), full_page=True)
        ctx.close()
    br.close()
print(f'\n{len(fails)} FAIL, {len(errs)} page errors' + (': ' + '; '.join(errs[:4]) if errs else ''))
sys.exit(1 if fails or errs else 0)
