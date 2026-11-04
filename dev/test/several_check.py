"""Checks 1.28.0: adding several plants at once from photos. Photos taken close together become one plant; each plant's names
come from the picture checker; a plant that looks like one you already have is flagged and left unticked; photos can be moved
between plants or left out; nothing is added until "Add N plants", and then each plant gets its photos and its home.
Start the mock server with a fresh data folder, then:
python3 dev/test/several_check.py      Screenshots: dev/tmp/shots/several-*.png"""
import io, json, os, urllib.request
from PIL import Image
from playwright.sync_api import sync_playwright
LOCAL = 'http://127.0.0.1:8080'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
TMP = os.path.join(HERE, '..', 'tmp', 'several'); os.makedirs(TMP, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def get(u):
    with urllib.request.urlopen(LOCAL + u) as r: return json.loads(r.read())

def photo(name, rgb, when):
    im = Image.new('RGB', (640, 480), rgb)
    ex = Image.Exif(); ex[306] = when; ifd = ex.get_ifd(0x8769); ifd[36867] = when
    p = os.path.join(TMP, name); im.save(p, 'JPEG', exif=ex.tobytes()); return p
files = [photo('a1.jpg', (200, 30, 30), '2026:11:02 10:00:00'), photo('a2.jpg', (210, 40, 30), '2026:11:02 10:01:30'),
         photo('b1.jpg', (30, 190, 40), '2026:11:02 10:30:00'), photo('c1.jpg', (30, 40, 200), '2026:11:02 10:31:00')]
before = len(get('/api/plants?status=all'))
nc = [h for h in get('/api/meta')['homes'] if h['name'].startswith('Nevada')][0]['id']

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1920, 'height': 1080})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Several Test')")
    pg.goto(LOCAL + '/#/new'); pg.wait_for_timeout(2500)
    check(pg.locator('.add-mode a').count() == 2, 'Add a plant offers one plant or several plants from photos')
    pg.locator('.add-mode a', has_text='Several').click(); pg.wait_for_timeout(1500)
    pg.locator('select[data-f=sevset][data-k=home]').select_option(str(nc))
    pg.locator('form[data-form=sevgo] input[type=file]').set_input_files(files)
    pg.locator('form[data-form=sevgo] button[type=submit]').click()
    pg.locator('fieldset.sev-plant').first.wait_for(timeout=30000)
    n = pg.locator('fieldset.sev-plant').count()
    check(n == 2, f'4 photos become 2 plants: two taken a minute apart, and two taken half an hour later ({n})')
    p1 = pg.locator('#sev-p0')
    check(p1.locator('.sev-pics li').count() == 2, 'the first plant has its 2 photos')
    check('may be a plant you already have' in p1.inner_text() and not p1.locator('[data-f=sevadd]').is_checked(),
          'a plant that looks like one you have is flagged, and not ticked to be added')
    check(p1.locator('[data-f=sevfield][data-k=common_name]').input_value() != '' and p1.locator('[data-f=sevpick]').count() >= 2,
          'its names are filled in from the likeliest species, with the others to choose from')
    pg.screenshot(path=os.path.join(OUT, 'several-1-review.png'), full_page=True)
    # move the blue photo to a plant of its own, then pick another name for it and type a spot
    pg.locator('#sev-p1 [data-f=sevmove]').nth(1).select_option('new'); pg.wait_for_timeout(600)
    check(pg.locator('fieldset.sev-plant').count() == 3, 'a photo can be moved to a new plant of its own')
    p3 = pg.locator('#sev-p2')
    p3.locator('[data-f=sevpick]').nth(1).check(); pg.wait_for_timeout(400)
    p3 = pg.locator('#sev-p2')
    name3 = p3.locator('[data-f=sevfield][data-k=scientific_name]').input_value()
    p3.locator('[data-f=sevfield][data-k=location]').fill('Front porch, blue pot')
    p1 = pg.locator('#sev-p0'); p1.locator('[data-f=sevadd]').check()
    p1.locator('[data-f=sevfield][data-k=common_name]').fill('')
    btn = pg.locator('[data-act=sevsave]')
    check(btn.inner_text().strip() == 'Add 3 plants', 'the button says how many plants will be added')
    btn.click(); pg.wait_for_timeout(800)
    check('needs a common name' in pg.locator('#sev-err').inner_text() and len(get('/api/plants?status=all')) == before,
          'a plant with no common name stops the save, and nothing is added')
    pg.locator('#sev-p0 [data-f=sevfield][data-k=common_name]').fill('Red test plant')
    pg.locator('#sev-p0 [data-f=sevmove]').first.select_option('out'); pg.wait_for_timeout(600)
    btn = pg.locator('[data-act=sevsave]'); btn.click()
    pg.locator('#sev .notice.ok').wait_for(timeout=15000)
    allp = get('/api/plants?status=all')
    new = [x for x in allp if x['code'] not in {y['code'] for y in allp[:before]}]
    check(len(allp) == before + 3, f'3 plants are added ({len(allp) - before})')
    codes = sorted(x['code'] for x in allp)[-3:]
    got = [get('/api/plants/' + c) for c in codes]
    check([len(g['photos']) for g in got] == [1, 1, 1], 'each gets its own photos (the photo left out is not added)')
    check(all(g['home_id'] == nc for g in got), 'they are all at the home chosen (Nevada City)')
    check(got[0]['common_name'] == 'Red test plant', 'a name you typed is kept')
    check(any(g['scientific_name'] == name3 and g['location'] == 'Front porch, blue pot' for g in got), 'the name you picked and the spot you typed are saved')
    check(all(g['id_basis'].startswith('Suggested by the picture checker') for g in got if g['common_name'] != 'Red test plant'), 'each says where its name came from')
    pg.screenshot(path=os.path.join(OUT, 'several-2-done.png'))
    ph = b.new_context(viewport={'width': 384, 'height': 740}, is_mobile=True, has_touch=True, service_workers='block')
    ph.add_init_script("localStorage.setItem('plantdb.editor','Several Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    q = ph.new_page(); q.on('pageerror', lambda e: errs.append(str(e)))
    q.goto(LOCAL + '/#/new/several'); q.wait_for_timeout(2500)
    q.locator('form[data-form=sevgo] input[type=file]').set_input_files(files[:2]); q.locator('form[data-form=sevgo] button[type=submit]').click()
    q.locator('fieldset.sev-plant').first.wait_for(timeout=30000)
    check(not q.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'on a phone with the largest text the review screen does not scroll sideways')
    q.screenshot(path=os.path.join(OUT, 'several-3-phone.png'))
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All several-plants checks passed' if not fails else f'{len(fails)} several-plants check(s) failed'))
raise SystemExit(1 if fails else 0)
