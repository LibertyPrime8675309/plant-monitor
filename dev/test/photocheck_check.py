"""Checks the photo check that runs before photos are added. Start the mock server first, then:
  python3 dev/test/photocheck_check.py [base-url]          Screenshots: dev/tmp/shots/photocheck-*.png
1. Runs the browser's check on every photo in dev/photos-raw (Ethan's real photos): none may be flagged.
2. Runs it on blurred, darkened, washed-out and tiny copies of some of them: each must be flagged for the right reason.
3. Adds photos on a plant page and on the Photos page and checks each choice in the dialog."""
import glob, json, os, sys, urllib.request
from PIL import Image, ImageEnhance, ImageFilter
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..', '..')
OUT = os.path.join(HERE, '..', 'tmp', 'shots'); TMP = os.path.join(HERE, '..', 'tmp', 'photocheck'); os.makedirs(OUT, exist_ok=True); os.makedirs(TMP, exist_ok=True)
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def photos_of(code): return len(json.load(urllib.request.urlopen(f'{BASE}/api/plants/{code}'))['photos'])
def loose(): return len(json.load(urllib.request.urlopen(f'{BASE}/api/photos/unassigned')))

real = sorted(glob.glob(os.path.join(ROOT, 'dev', 'photos-raw', '*', '*.jpg')))
made = {}                                        # name -> expected problem
for i, f in enumerate(real[::25]):
    im = Image.open(f).convert('RGB'); r = max(im.size) / 512
    for kind, img, want in (('blurry', im.filter(ImageFilter.GaussianBlur(radius=2.2 * r)), 'Blurry'),
                            ('dark', ImageEnhance.Brightness(im).enhance(0.25), 'Too dark'),
                            ('bright', ImageEnhance.Brightness(im).enhance(230 / max(1, sum(im.convert('L').getdata()) / (im.size[0] * im.size[1]))), 'Too bright (washed out)'),
                            ('tiny', im.resize((im.size[0] * 300 // max(im.size), im.size[1] * 300 // max(im.size))), 'Very small picture')):
        name = f'{kind}-{i}.jpg'; img.save(os.path.join(TMP, name), quality=88); made[name] = want
good = real[0]

with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900}); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Photo Test');localStorage.setItem('plantdb.display',JSON.stringify({layout:'single',navopen:'0'}))")
    def serve(route):                            # hands the test photos to the page without adding them to the app
        rel = route.request.url.split('/pctest/', 1)[1]
        path = os.path.join(TMP, rel) if rel in made else os.path.join(ROOT, 'dev', 'photos-raw', rel)
        route.fulfill(path=path, content_type='image/jpeg')
    pg.route('**/pctest/**', serve)
    pg.goto(f'{BASE}/#/plant/P-024'); pg.wait_for_timeout(2000)
    run = """async names => { const out = {}; for (const n of names) { const r = await fetch('/pctest/' + n), f = new File([await r.blob()], n, { type: 'image/jpeg' });
      const C = window.PlantPhotoCheck, s = await C.stats(f); out[n] = s ? C.problems(s).map(p => p[0]) : null; } return out; }"""
    rels = [os.path.relpath(f, os.path.join(ROOT, 'dev', 'photos-raw')) for f in real]
    res = pg.evaluate(run, rels)
    flagged = {k: v for k, v in res.items() if v}
    check(len(res) == len(real) and not flagged, f'none of the {len(real)} real photos is flagged' + (f': {flagged}' if flagged else ''))
    res = pg.evaluate(run, list(made))
    wrong = {k: v for k, v in res.items() if not v or made[k] not in v}
    check(not wrong, f'all {len(made)} spoiled copies are flagged for the right reason' + (f': {wrong}' if wrong else ''))

    # adding photos on a plant page
    inp = 'input[data-act=addphotos]'
    n0 = photos_of('P-024')
    pg.set_input_files(inp, [good]); pg.wait_for_timeout(2500)
    check(pg.locator('dialog[open]').count() == 0 and photos_of('P-024') == n0 + 1, 'a good photo is added without asking')
    n0 = photos_of('P-024')
    pg.set_input_files(inp, [good, os.path.join(TMP, 'blurry-0.jpg')]); pg.wait_for_timeout(1500)
    dlg = pg.locator('dialog[open]')
    check(dlg.count() == 1 and 'Check 1 of these 2 photos' in dlg.inner_text() and 'Blurry.' in dlg.inner_text(), 'one good and one blurry: the dialog names the blurry one')
    check(pg.evaluate('document.activeElement && document.activeElement.value') == 'again', 'focus starts on "Take a new one"')
    pg.screenshot(path=f'{OUT}/photocheck-dialog.png')
    pg.locator('dialog[open] button[value=good]').click(); pg.wait_for_timeout(2500)
    check(photos_of('P-024') == n0 + 1, '"Add only the 1 good one" adds just that one')
    n0 = photos_of('P-024')
    pg.set_input_files(inp, [os.path.join(TMP, 'dark-0.jpg')]); pg.wait_for_timeout(1500)
    check('Too dark.' in pg.locator('dialog[open]').inner_text(), 'a dark photo: the dialog says so')
    with pg.expect_file_chooser() as fc:
        pg.locator('dialog[open] button[value=again]').click()
    check(fc.value is not None and photos_of('P-024') == n0, '"Take a new one" opens the camera or file picker again and adds nothing')
    pg.set_input_files(inp, [os.path.join(TMP, 'bright-0.jpg')]); pg.wait_for_timeout(1500)
    pg.locator('dialog[open] button[value=cancel]').click(); pg.wait_for_timeout(1200)
    check(photos_of('P-024') == n0, 'Cancel adds nothing')
    pg.set_input_files(inp, [os.path.join(TMP, 'tiny-0.jpg')]); pg.wait_for_timeout(1500)
    pg.locator('dialog[open] button[value=all]').click(); pg.wait_for_timeout(2500)
    check(photos_of('P-024') == n0 + 1, '"Add it anyway" adds it')
    # the Photos page
    pg.goto(f'{BASE}/#/photos'); pg.wait_for_timeout(1800)
    l0 = loose()
    pg.set_input_files('input[data-act=addloose]', [os.path.join(TMP, 'blurry-1.jpg')]); pg.wait_for_timeout(1500)
    check(pg.locator('dialog[open]').count() == 1, 'the Photos page checks photos too')
    pg.locator('dialog[open] button[value=all]').click(); pg.wait_for_timeout(2500)
    check(loose() == l0 + 1, 'and adds it when asked')
    pg.close()
    # phone, largest text
    q = b.new_page(viewport={'width': 390, 'height': 844}); q.on('pageerror', lambda e: errs.append(str(e)))
    q.add_init_script("localStorage.setItem('plantdb.editor','Photo Test');localStorage.setItem('plantdb.display',JSON.stringify({theme:'dark',size:'190'}))")
    q.goto(f'{BASE}/#/plant/P-024'); q.wait_for_timeout(2000)
    q.set_input_files(inp, [good, os.path.join(TMP, 'blurry-0.jpg'), os.path.join(TMP, 'dark-1.jpg')]); q.wait_for_timeout(1800)
    q.evaluate("document.getElementById('dlg').scrollTop = 0"); q.wait_for_timeout(200)
    q.screenshot(path=f'{OUT}/photocheck-phone-dark.png')
    over = q.evaluate('document.getElementById("dlg").scrollWidth - document.getElementById("dlg").clientWidth')
    check(over <= 2, f'phone, largest text: nothing in the dialog scrolls sideways ({over}px)')
    q.locator('dialog[open] button[value=cancel]').click()
    q.close(); b.close()
for e in errs: print('JS error:', e)
sys.exit(1 if fails or errs else 0)
