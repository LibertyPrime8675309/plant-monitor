"""Checks the prototype large-print care cards (proto/care-card): the link on plant and group pages, the card for one plant and for a
group, the options (remembered), print layout (each plant on its own page, black on white, large print), and no sideways scrolling on a phone.
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
    check(pg.evaluate("getComputedStyle(document.getElementById('pc-tools')).display") == 'none', 'the options are not printed')
    col = pg.evaluate("getComputedStyle(document.querySelector('.pc-card')).color")
    check(col == 'rgb(0, 0, 0)', f'cards print in black ({col})')
    pg.pdf(path=os.path.join(OUT, 'card-print.pdf'), format='Letter')
    pg.close(); b.close()
from pypdf import PdfReader  # noqa: E402
pages = [pg.extract_text() for pg in PdfReader(os.path.join(OUT, 'card-print.pdf')).pages]
sizes = {}
def _v(text, cm, tm, fd, fs):
    if text.strip(): sizes[round(fs * (tm[3] or 1) * (cm[3] or 1), 1)] = sizes.get(round(fs * (tm[3] or 1) * (cm[3] or 1), 1), 0) + len(text.strip())
PdfReader(os.path.join(OUT, 'card-print.pdf')).pages[0].extract_text(visitor_text=_v)
big = sum(n for f, n in sizes.items() if f >= 16) / max(1, sum(sizes.values()))
check(big >= 0.9 and max(sizes) >= 28, f'the printout is large print: {big:.0%} of the text is 16 point or more, the name {max(sizes)} point')
first = [next((i for i, t in enumerate(pages) if t.lstrip().startswith(n)), -1) for n in ('Dieffenbachia', 'Sweet potato vine', "Philodendron 'Pink")]
check(-1 not in first and first == sorted(first), f'each plant starts at the top of its own page (pages {first})')
check(len(pages) <= 4, f'3 plants print on at most 4 pages: most fit on one ({len(pages)} pages)')
call('DELETE', f'/api/groups/{gid}')
print('\n'.join(['', 'FAILED:'] + fails) if fails else '\ncare card check passed')
sys.exit(1 if fails else 0)
