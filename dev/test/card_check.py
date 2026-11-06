"""Checks the large-print care cards (1.19.0; 1.20.0: 4 x 6 inch cards by default, dangers shown by default, the smallest text as big
as the rest, and "Print care cards for all plants" on the Labels page): the link on plant and group pages, the card for one plant and
for a group, the options (remembered), print layout (each plant on its own page or card, black on white, large print), and no
sideways scrolling on a phone.
Start the mock server with a fresh data folder, then:  python3 dev/test/card_check.py [base]
Screenshots and a printed PDF: dev/tmp/shots/card-*"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails = []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Card Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
gid = call('POST', '/api/groups', {'name': 'Card test group', 'kind': 'picked'})['id']
call('POST', f'/api/groups/{gid}/members', {'add': ['P-001', 'P-006', 'P-029']})
with sync_playwright() as p:
    b = p.chromium.launch()
    for theme in ('light', 'dark'):
        for size, (w, h, text) in {'laptop': (1280, 800, ''), 'phone': (390, 844, ''), 'phone-bigtext': (390, 844, '190')}.items():
            pg = b.new_page(viewport={'width': w, 'height': h}); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
            pg.add_init_script("localStorage.setItem('plantdb.editor','Card Test');localStorage.setItem('plantdb.display',JSON.stringify(%s))"
                               % json.dumps({'theme': theme, **({'size': text} if text else {})}))
            name = f'{size}-{theme}'
            pg.goto(BASE + '/#/plant/P-006'); pg.wait_for_timeout(1500)
            link = pg.locator('a.pc-link')
            check(link.count() == 1 and link.inner_text() == 'Large-print care card', f'{name}: the plant page has one "Large-print care card" link')
            link.click(); pg.wait_for_load_state(); pg.wait_for_selector('.pc-card'); pg.wait_for_timeout(600)
            check('card.html?plant=P-006' in pg.url, f'{name}: the link opens the card for P-006')
            over = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            check(over <= 2, f'{name}: no sideways scrolling on the card page ({over}px)')
            if size == 'laptop' and theme == 'light':
                check(pg.get_by_label('4 × 6 inch card', exact=False).is_checked() and pg.get_by_label('Dangers to pets and people').is_checked() and pg.locator('.pc-46').count() == 1,
                      'by default the card is 4 x 6 inch, with the dangers to pets and people')
                check(pg.locator('.pc-46 .pc-care').count() == 1 and 'Pets:' in pg.locator('.pc-46').inner_text(), 'the Careful row says what it means for pets')
                check(pg.locator('#pc-notes').is_hidden(), 'the 4 x 6 card has no notes choice (it holds the main facts only)')
            txt = pg.locator('.pc-card').inner_text()
            check('Sweet potato vine' in txt and 'Check about every' in txt and 'Best at 65 to 95°F' in txt and 'Harmed below 32°F' in txt, f'{name}: the card shows the name, watering, and temperatures')
            pg.screenshot(path=os.path.join(OUT, f'card-{name}-plant.png'), full_page=True)
            check(pg.locator('a#pc-back').get_attribute('href') == '/#/plant/P-006', f'{name}: "Back" returns to the plant page')
            pg.goto(BASE + f'/#/group/{gid}'); pg.wait_for_timeout(1500)
            glink = pg.locator('a.pc-link')
            check(glink.count() == 1 and 'cards' in glink.inner_text(), f'{name}: the group page has a "Large-print care cards" link')
            glink.click(); pg.wait_for_selector('.pc-card'); pg.wait_for_timeout(600)
            check(pg.locator('.pc-card').count() == 3, f'{name}: the group gives one card for each of its 3 plants')
            if size == 'laptop':
                pg.screenshot(path=os.path.join(OUT, f'card-{name}-group.png'))
            for e in errs: check(False, f'{name}: {e}')
            pg.close()
    # options: notes, photo, two per page, remembered; and the printout
    pg = b.new_page(viewport={'width': 1280, 'height': 800})
    pg.goto(BASE + '/card.html?plant=P-006'); pg.wait_for_selector('.pc-card')
    pg.get_by_label('Full page (Letter)', exact=False).check(); pg.wait_for_timeout(200)
    check(pg.locator('.pc-46').count() == 0 and pg.locator('#pc-notes').is_visible(), 'Full page gives the full card, with the notes choice')
    short = len(pg.locator('.pc-card').inner_text())
    pg.get_by_label('Full: every note in full').check(); pg.wait_for_timeout(200)
    check(len(pg.locator('.pc-card').inner_text()) > short, 'Full notes make the card longer')
    pg.get_by_label("The plant's main photo").uncheck(); pg.wait_for_timeout(200)
    check(pg.locator('.pc-photo').count() == 0, 'the photo can be left out')
    pg.reload(); pg.wait_for_selector('.pc-card')
    check(pg.get_by_label('Full: every note in full').is_checked() and pg.locator('.pc-photo').count() == 0, 'the choices are remembered')
    pg.get_by_label('Short: the first sentence of each note').check(); pg.get_by_label("The plant's main photo").check()
    pg.goto(BASE + f'/card.html?group={gid}'); pg.wait_for_selector('.pc-card'); pg.wait_for_timeout(800)
    pg.emulate_media(media='print')
    small = pg.evaluate("[parseFloat(getComputedStyle(document.querySelector('.pc-printed')).fontSize), parseFloat(getComputedStyle(document.querySelector('.pc-scan figcaption')).fontSize), parseFloat(getComputedStyle(document.querySelector('.pc-box p:not(.pc-main-fact)')).fontSize)]")
    check(small[0] >= small[2] - 0.1 and small[1] >= small[2] - 0.1, f'printed full page: the "Printed" line and "Scan for the full page" are as big as the notes ({small})')
    check(pg.evaluate("getComputedStyle(document.getElementById('pc-tools')).display") == 'none', 'the options are not printed')
    col = pg.evaluate("getComputedStyle(document.querySelector('.pc-card')).color")
    check(col == 'rgb(0, 0, 0)', f'cards print in black ({col})')
    pg.pdf(path=os.path.join(OUT, 'card-print.pdf'), format='Letter')
    # the 4 x 6 card: its own paper size, each plant on its own card, nothing under 16 point
    pg.emulate_media(media='screen'); pg.get_by_label('4 × 6 inch card', exact=False).check(); pg.wait_for_timeout(300)
    pg.emulate_media(media='print'); pg.pdf(path=os.path.join(OUT, 'card-46.pdf'), prefer_css_page_size=True)
    lab = b.new_page(viewport={'width': 1280, 'height': 900})
    lab.add_init_script("localStorage.setItem('plantdb.editor','Card Test')")
    lab.goto(BASE + '/#/labels'); lab.wait_for_timeout(1500)
    al = lab.locator('a[href="/card.html?all=1"]')
    check(al.count() == 1 and al.inner_text() == 'Print care cards for all plants', 'the Labels page has "Print care cards for all plants"')
    al.click(); lab.wait_for_selector('.pc-card'); lab.wait_for_timeout(1500)
    nact = len(call('GET', '/api/plants'))
    check(lab.locator('.pc-card').count() == nact and 'for all plants' in lab.locator('h1').inner_text(), f'it makes one card for each of the {nact} active plants')
    check(lab.locator('#pc-back').get_attribute('href') == '/#/labels', '"Back" returns to the Labels page')
    lab.emulate_media(media='print'); lab.pdf(path=os.path.join(OUT, 'card-46-all.pdf'), prefer_css_page_size=True)
    pg.close(); lab.close(); b.close()
from pypdf import PdfReader  # noqa: E402
import re  # noqa: E402
r46 = PdfReader(os.path.join(OUT, 'card-46.pdf'))
w, h = float(r46.pages[0].mediabox.width) / 72, float(r46.pages[0].mediabox.height) / 72
check(abs(w - 6) < .05 and abs(h - 4) < .05, f'the 4 x 6 card prints on 6 x 4 inch paper ({w:.2f} x {h:.2f})')
p46 = [x.extract_text() for x in r46.pages]
check(len(p46) == 3 and all(re.search(r'P-\d{3}', t[:200]) for t in p46), f'the 3 plants print on 3 cards, one each ({len(p46)} cards)')
s46 = {}
def _v46(text, cm, tm, fd, fs):
    k = abs(round(fs * (tm[3] or 1) * (cm[3] or 1), 1))
    if text.strip() and k: s46[k] = s46.get(k, 0) + len(text.strip())
for pgx in r46.pages: pgx.extract_text(visitor_text=_v46)
check(min(s46) >= 15.9 and max(s46) >= 20, f'on the 4 x 6 card nothing is under 16 point, and the name is the biggest ({min(s46)} to {max(s46)} point)')
rall = [x.extract_text() for x in PdfReader(os.path.join(OUT, 'card-46-all.pdf')).pages]
one = sum(1 for i, t in enumerate(rall) if re.search(r'P-\d{3}', t[:200]) and (i + 1 == len(rall) or re.search(r'P-\d{3}', rall[i + 1][:200])))
check(one >= 0.9 * nact, f'nearly every plant fits on one 4 x 6 card ({one} of {nact})')
pages = [pg.extract_text() for pg in PdfReader(os.path.join(OUT, 'card-print.pdf')).pages]
sizes = {}
def _v(text, cm, tm, fd, fs):
    if text.strip(): sizes[round(fs * (tm[3] or 1) * (cm[3] or 1), 1)] = sizes.get(round(fs * (tm[3] or 1) * (cm[3] or 1), 1), 0) + len(text.strip())
PdfReader(os.path.join(OUT, 'card-print.pdf')).pages[0].extract_text(visitor_text=_v)
big = sum(n for f, n in sizes.items() if f >= 16) / max(1, sum(sizes.values()))
check(big >= 0.9 and max(sizes) >= 28, f'the printout is large print: {big:.0%} of the text is 16 point or more, the name {max(sizes)} point')
first = [next((i for i, t in enumerate(pages) if t.lstrip().startswith(n)), -1) for n in ('Dieffenbachia', 'Sweet potato vine', "Philodendron 'Pink")]
check(-1 not in first and first == sorted(first), f'each plant starts at the top of its own page (pages {first})')
check(len(pages) <= 6, f'full page with notes and dangers: 3 plants print on at most 2 pages each ({len(pages)} pages)')
call('DELETE', f'/api/groups/{gid}')
print('\n'.join(['', 'FAILED:'] + fails) if fails else '\ncare card check passed')
sys.exit(1 if fails else 0)
