"""Checks the prototype plant-sitter sheet (proto/sitter-sheet): the link on Today and on group pages, the day-by-day plan,
the choices (dates, group, note, plant list, photos; remembered), errors in plain words, no sideways scrolling, and the printout
(black on white, large print, the choices left off).
Start the mock server with a fresh data folder (MOCK_BASE_F=40 gives cold nights), then:  python3 dev/test/sitter_check.py [base]
Screenshots and a printed PDF: dev/tmp/shots/sitter-*"""
import json, os, sys, urllib.request, urllib.error
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails = []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Sitter Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')

# some plants watered a few days ago, so the plan has a spread of days
today = date.fromisoformat(call('GET', '/api/water')['today'])
for i, code in enumerate(['P-001', 'P-006', 'P-029', 'P-010', 'P-012', 'P-020']):
    call('POST', '/api/care', {'kind': 'water', 'plant': code, 'done_on': (today - timedelta(days=i % 4)).isoformat()})
call('POST', '/api/care', {'kind': 'water', 'plants': [f'P-{n:03d}' for n in range(30, 60)], 'done_on': (today - timedelta(days=2)).isoformat()})
gid = call('POST', '/api/groups', {'name': 'Sitter test group', 'kind': 'picked'})['id']
call('POST', f'/api/groups/{gid}/members', {'add': ['P-001', 'P-006', 'P-029']})

# the API on its own
d = call('GET', f'/api/sitter?from={(today + timedelta(days=1)).isoformat()}&to={(today + timedelta(days=10)).isoformat()}')
check(len(d['days']) == 10, 'the API gives one entry for each of the 10 days')
p6 = next(p for p in d['plants'] if p['code'] == 'P-006')
check(all((date.fromisoformat(b) - date.fromisoformat(a)).days == p6['every'] for a, b in zip(p6['visits'], p6['visits'][1:])), 'a plant comes back every N days')
check(all(c in [x['code'] for x in d['plants']] for day in d['days'] for c in day['plants']), 'every plant on a day is in the plant list')
for q, words in ((f'from={(today - timedelta(days=2)).isoformat()}', 'already gone'), (f'from={today.isoformat()}&to={(today + timedelta(days=60)).isoformat()}', '6 weeks')):
    try: call('GET', '/api/sitter?' + q); check(False, f'the API refuses {q}')
    except urllib.error.HTTPError as e: check(e.code == 400 and words in json.loads(e.read())['error'], f'the API refuses {q} in plain words')
g = call('GET', f'/api/sitter?group={gid}')
check(sorted(p['code'] for p in g['plants']) == ['P-001', 'P-006', 'P-029'] and g['group']['name'] == 'Sitter test group', 'a group limits the sheet to its plants')

with sync_playwright() as p:
    b = p.chromium.launch()
    for theme in ('light', 'dark'):
        for size, (w, h, text) in {'laptop': (1280, 800, ''), 'phone': (390, 844, ''), 'phone-bigtext': (390, 844, '190')}.items():
            pg = b.new_page(viewport={'width': w, 'height': h}); errs = []
            pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and '404' not in m.text and errs.append(m.text))   # the dev data folder lacks some seed photos
            pg.add_init_script("localStorage.setItem('plantdb.editor','Sitter Test');localStorage.setItem('plantdb.display',JSON.stringify(%s));localStorage.removeItem('plantdb.sitter')"
                               % json.dumps({'theme': theme, **({'size': text} if text else {})}))
            name = f'{size}-{theme}'
            pg.goto(BASE + '/#/today'); pg.wait_for_timeout(1500)
            link = pg.locator('.ps-link a')
            check(link.count() == 1 and link.inner_text() == 'Going away? Make a plant-sitter sheet', f'{name}: Today has one plant-sitter link')
            if size == 'phone' and theme == 'light': pg.screenshot(path=os.path.join(OUT, f'sitter-{name}-today.png'))
            link.click(); pg.wait_for_selector('.ps-doc'); pg.wait_for_timeout(500)
            check(pg.url.endswith('/sitter.html'), f'{name}: the link opens the sheet')
            check(pg.locator('.ps-day').count() >= 7, f'{name}: a week, day by day')
            over = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            check(over <= 2, f'{name}: no sideways scrolling ({over}px)')
            unlabeled = pg.evaluate("[...document.querySelectorAll('#ps-opts input, #ps-opts select, #ps-opts textarea')].filter(e => !e.labels || !e.labels.length).length")
            check(unlabeled == 0, f'{name}: every choice has a label')
            pg.screenshot(path=os.path.join(OUT, f'sitter-{name}.png'), full_page=size != 'laptop')
            pg.goto(BASE + f'/#/group/{gid}'); pg.wait_for_timeout(1500)
            gl = pg.locator('.ps-link a')
            check(gl.count() == 1 and gl.inner_text() == 'Plant-sitter sheet for this group', f'{name}: a group page has a plant-sitter link')
            gl.click(); pg.wait_for_selector('.ps-doc'); pg.wait_for_timeout(500)
            check(pg.locator('#ps-group').input_value() == str(gid) and pg.locator('.ps-card').count() == 3, f'{name}: from a group page, the sheet has just its 3 plants')
            for e in errs: check(False, f'{name}: {e}')
            pg.close()

    # choices: dates, note, plant list, photos; remembered
    pg = b.new_page(viewport={'width': 1280, 'height': 900}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(BASE + '/sitter.html'); pg.wait_for_selector('.ps-doc')
    pg.evaluate("localStorage.removeItem('plantdb.sitter')"); pg.reload(); pg.wait_for_selector('.ps-doc')
    pg.get_by_label('Which plants').select_option('')
    a, z = (today + timedelta(days=2)).isoformat(), (today + timedelta(days=15)).isoformat()
    pg.get_by_label('Last day').fill(z); pg.get_by_label('First day').fill(a); pg.wait_for_timeout(800)
    check(pg.locator('#ps-days-h ~ .ps-day').count() == 14, 'two weeks give 14 days')
    check(pg.locator('.ps-before').count() == 1 and 'not printed' in pg.locator('.ps-before').inner_text(), '"Before you go" lists plants to water before leaving')
    pg.get_by_label('Printed at the top', exact=False).fill('Call Ethan: 555-0100. The watering can is by the back door.'); pg.wait_for_timeout(800)
    check('555-0100' in pg.locator('.ps-msg').inner_text(), 'the note for the sitter is on the sheet')
    pg.get_by_label('A photo of each plant', exact=False).uncheck(); pg.wait_for_timeout(500)
    check(pg.locator('.ps-photo').count() == 0, 'photos can be left out')
    pg.reload(); pg.wait_for_selector('.ps-doc'); pg.wait_for_timeout(400)
    check(pg.get_by_label('First day').input_value() == a and pg.get_by_label('Last day').input_value() == z and '555-0100' in pg.locator('.ps-msg').inner_text()
          and pg.locator('.ps-photo').count() == 0, 'the choices are remembered')
    pg.get_by_label('The plant list at the end', exact=False).uncheck(); pg.wait_for_timeout(500)
    check(pg.locator('.ps-plants').count() == 0 and pg.get_by_label('A photo of each plant', exact=False).is_disabled(), 'the plant list can be left out (and the photo choice goes grey)')
    pg.get_by_label('The plant list at the end', exact=False).check(); pg.get_by_label('A photo of each plant', exact=False).check(); pg.wait_for_timeout(500)
    pg.get_by_label('Last day').fill((today + timedelta(days=60)).isoformat()); pg.wait_for_timeout(800)
    check('6 weeks' in pg.locator('#ps-sheet [role=alert]').inner_text(), 'too long a stay is refused in plain words')
    pg.get_by_label('Last day').fill((today + timedelta(days=8)).isoformat()); pg.wait_for_timeout(800)
    pg.screenshot(path=os.path.join(OUT, 'sitter-laptop-choices.png'), full_page=True)
    # the printout
    pg.emulate_media(media='print'); pg.wait_for_timeout(300)
    check(not pg.locator('#ps-opts').is_visible() and not pg.locator('.ps-before').is_visible(), 'the printout leaves off the choices and "Before you go"')
    st = pg.evaluate('''(() => { const d = document.querySelector('.ps-doc'), cs = getComputedStyle(d), sizes = [];
        d.querySelectorAll('*').forEach(e => { if (e.childNodes.length && [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim())) sizes.push(parseFloat(getComputedStyle(e).fontSize)); });
        return { color: cs.color, bg: getComputedStyle(document.body).backgroundColor, min: Math.min(...sizes) }; })()''')
    check(st['color'] == 'rgb(0, 0, 0)' and st['bg'] == 'rgb(255, 255, 255)', f'the printout is black on white ({st["color"]} on {st["bg"]})')
    check(st['min'] >= 20.5, f'nothing in the printout is smaller than about 15.5 point ({st["min"]:.1f}px)')
    pg.pdf(path=os.path.join(OUT, 'sitter-print.pdf'), format='Letter', print_background=True)
    pg.screenshot(path=os.path.join(OUT, 'sitter-print.png'), full_page=True)
    for e in errs: check(False, f'choices: {e}')
    b.close()
print('\n' + ('All sitter-sheet checks passed.' if not fails else f'{len(fails)} failed:\n' + '\n'.join(fails)))
sys.exit(1 if fails else 0)
