"""Checks 1.20.0: browsing a plant's photos on the Plants page (Previous / Next buttons, arrow keys and swipe, without opening the
plant), the card still opening the plant, and choosing the main photo on a plant page (shown in words, used by the Plants page and
the care cards; people who can only view cannot change it). Start the mock server with a fresh data folder (MOCK_TS=1), then:
python3 dev/test/photos_check.py      Screenshots: dev/tmp/shots/photos-*.png"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
get = lambda u, h=None, base=LOCAL: json.loads(urllib.request.urlopen(urllib.request.Request(base + u, headers=h or {})).read())
plants = get('/api/plants')
many = max(plants, key=lambda p: len(p['photos'])); one = next(p for p in plants if len(p['photos']) == 1)
code, n = many['code'], len(many['photos'])
check(n >= 3 and all('photos' in p for p in plants) and many['photos'][0] == many['photo'], f'the plant list carries every photo, main photo first ({code}: {n})')
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
get('/api/me', {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}, TS)   # the first person in is the owner
get('/api/me', V, TS)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Photo Test');localStorage.removeItem('plantdb.filters')")
    pg.goto(LOCAL + '/#/plants'); pg.wait_for_timeout(2500)
    card = pg.locator(f'#grid .sheet[data-code="{code}"]')
    img = lambda: card.locator('.mat img').get_attribute('src')
    check(card.locator('.ph-n').inner_text() == f'1 of {n}' and card.locator('.ph-btn').count() == 2, f'a plant with {n} photos has Previous and Next photo buttons and says "1 of {n}"')
    check(pg.locator(f'#grid .sheet[data-code="{one["code"]}"] .ph-btn').count() == 0, 'a plant with one photo has no photo buttons')
    check(card.locator('.ph-btn').first.get_attribute('aria-label').startswith('Previous photo of ') and card.locator('.ph-btn').last.get_attribute('aria-label').startswith('Next photo of '), 'the buttons say what they do, for screen readers')
    first = img()
    card.locator('.ph-btn[data-d="1"]').click(); pg.wait_for_timeout(300)
    check(card.locator('.ph-n').inner_text() == f'2 of {n}' and img() != first and many['photos'][1] in img(), 'Next shows the second photo')
    check(pg.evaluate('location.hash') == '#/plants', 'and stays on the Plants page')
    card.locator('.ph-btn[data-d="-1"]').click(); card.locator('.ph-btn[data-d="-1"]').click(); pg.wait_for_timeout(300)
    check(card.locator('.ph-n').inner_text() == f'{n} of {n}', 'Previous from the first photo goes round to the last')
    pg.screenshot(path=os.path.join(OUT, 'photos-1-card.png'), clip=card.bounding_box())
    card.locator('.ph-btn[data-d="1"]').focus(); pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(300)
    check(card.locator('.ph-n').inner_text() == f'1 of {n}' and pg.evaluate("document.activeElement.classList.contains('ph-btn')"), 'the arrow keys step through the photos too, and the keyboard stays on the button')
    # swipe on the photo (touch events, as a phone sends them)
    swipe = """([sel, dx]) => { const el = document.querySelector(sel), r = el.closest('.sheet').querySelector('.mat').getBoundingClientRect(), y = r.top + r.height / 2, x = r.left + r.width / 2;
        const t = (x2) => new Touch({ identifier: 1, target: el, clientX: x2, clientY: y });
        el.dispatchEvent(new TouchEvent('touchstart', { bubbles: true, touches: [t(x)], changedTouches: [t(x)] }));
        el.dispatchEvent(new TouchEvent('touchend', { bubbles: true, touches: [], changedTouches: [t(x + dx)] }));
        el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true })); }"""
    sel = f'#grid .sheet[data-code="{code}"] .sheet-link'
    pg.evaluate(swipe, [sel, -120]); pg.wait_for_timeout(400)
    check(card.locator('.ph-n').inner_text() == f'2 of {n}' and pg.evaluate('location.hash') == '#/plants', 'swiping left on the photo shows the next one, and does not open the plant')
    pg.evaluate(swipe, [sel, 120]); pg.wait_for_timeout(400)
    check(card.locator('.ph-n').inner_text() == f'1 of {n}', 'swiping right goes back')
    pg.fill('input[data-f=q]', many['common_name'][:6]); pg.wait_for_timeout(400); card.locator('.ph-btn[data-d="1"]').click(); pg.fill('input[data-f=q]', ''); pg.wait_for_timeout(400)
    check(card.locator('.ph-n').inner_text() == f'2 of {n}', 'the card keeps its photo when the filters redraw the page')
    pg.wait_for_timeout(700)
    card.scroll_into_view_if_needed(); bx = card.locator('.sci').bounding_box(); pg.mouse.click(bx['x'] + 10, bx['y'] + bx['height'] / 2); pg.wait_for_timeout(1500)   # a real click on the card's text
    check(pg.evaluate('location.hash') == f'#/plant/{code}', 'clicking anywhere else on the card still opens the plant')
    # the main photo, on the plant page
    t = pg.inner_text('#photopanel') if pg.locator('#photopanel').count() else pg.inner_text('main')
    check('This is the main photo' in t, 'the plant page says, in words, that the photo shown is the main photo')
    check(pg.locator('.thumbs .th-main').count() == 1 and 'main photo' in pg.locator('.thumbs button').first.get_attribute('aria-label'), 'its thumbnail is marked "Main", for screen readers too')
    pg.locator('.thumbs button[data-i="2"]').click(); pg.wait_for_timeout(500)
    btn = pg.locator('[data-act=mainphoto]')
    check(btn.count() == 1 and btn.inner_text() == 'Make this the main photo' and 'Plants page' in pg.inner_text('.main-note'), 'another photo has "Make this the main photo", with what that changes')
    chosen = many['photos'][2]
    pg.screenshot(path=os.path.join(OUT, 'photos-2-plant.png'))
    btn.click(); pg.wait_for_timeout(1800)
    check('This is the main photo' in pg.inner_text('.main-note') and chosen in pg.locator('.main-photo img').get_attribute('src'), 'after pressing it, that photo is shown and called the main photo')
    after = next(x for x in get('/api/plants') if x['code'] == code)
    check(after['photo'] == chosen and after['photos'][0] == chosen, 'the Plants page now uses it')
    pg.goto(LOCAL + f'/card.html?plant={code}'); pg.wait_for_selector('.pc-card'); pg.wait_for_timeout(500)
    check(chosen in (pg.locator('.pc-photo').get_attribute('src') or ''), 'and so does the care card')
    pg.goto(LOCAL + '/#/plants'); pg.wait_for_timeout(2000)
    check(chosen in pg.locator(f'#grid .sheet[data-code="{code}"] .mat img').get_attribute('src'), 'the Plants page card shows the new main photo first')
    # a viewer
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    vw.on('pageerror', lambda e: errs.append(str(e)))
    vw.goto(TS + f'/#/plant/{code}'); vw.wait_for_timeout(2000)
    vw.locator('.thumbs button[data-i="1"]').click(); vw.wait_for_timeout(400)
    check(not vw.locator('[data-act=mainphoto]').is_visible(), 'someone who can only view does not get "Make this the main photo"')
    vw.goto(TS + '/#/plants'); vw.wait_for_timeout(2000)
    check(vw.locator(f'#grid .sheet[data-code="{code}"] .ph-btn').first.is_visible(), 'but can browse the photos on the Plants page')
    # 1.21.0: wide photos on the cards, and sharper thumbnails
    pg.goto(LOCAL + '/#/plants'); pg.wait_for_timeout(2500)
    for _ in range(40):                     # scroll through the whole grid, so every lazy photo loads (the newest plants, at the end, are portrait shots)
        pg.mouse.wheel(0, 1500); pg.wait_for_timeout(150)
    pg.wait_for_timeout(1500); pg.evaluate("window.scrollTo(0, 0)")
    wide = pg.locator('#grid .mat img.wide')
    fit = lambda: wide.first.evaluate("e => getComputedStyle(e).objectFit")
    check(wide.count() >= 1 and fit() == 'contain', f'wide photos are shown whole by default ({wide.count()} wide photos)')
    pg.evaluate("window.PlantPrefs.set('photofit', 'fill')"); pg.wait_for_timeout(200)
    check(fit() == 'cover', 'Display setting "Fill the card" crops them to fill the card')
    pg.evaluate("window.PlantPrefs.set('photofit', 'auto')")
    from PIL import Image as _I
    import io as _io
    src = wide.first.get_attribute('src')
    tim = _I.open(_io.BytesIO(urllib.request.urlopen(LOCAL + src).read()))
    orig = _I.open(_io.BytesIO(urllib.request.urlopen(LOCAL + src.replace('/thumbs/', '/photos/')).read()))
    check(min(tim.size) >= min(640, min(orig.size)), f'thumbnails keep at least 640 pixels on the short side ({tim.size}, from {orig.size})')
    # phone with the largest text
    ph = b.new_page(viewport={'width': 390, 'height': 844})
    ph.add_init_script("localStorage.setItem('plantdb.editor','Photo Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    ph.goto(LOCAL + '/#/plants'); ph.wait_for_timeout(2500)
    check(ph.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'on a phone with the largest text there is no sideways scrolling')
    c2 = ph.locator(f'#grid .sheet[data-code="{code}"]'); c2.scroll_into_view_if_needed()
    bb = c2.locator('.ph-btn').first.bounding_box()
    check(bb and bb['width'] >= 44 and bb['height'] >= 44, f'the photo buttons are big enough to tap ({bb and round(bb["width"])} px)')
    ph.screenshot(path=os.path.join(OUT, 'photos-3-phone.png'), clip=c2.bounding_box())
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
