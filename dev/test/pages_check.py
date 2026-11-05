"""Checks 1.34.0: Today as the page the app opens on (the summary line with its jump buttons, the cold-night section, Quiet today),
the shopping list for a store visit, dictation (with a stand-in for the browser's speech service), room and shelf labels with the
Plants page showing one place, and the summer heat zone next to the winter zone. Start the mock server with a fresh data folder
(MOCK_TS=1), then:  python3 dev/test/pages_check.py      Screenshots: dev/tmp/shots/pages-*.png"""
import json, os, sys, urllib.request, urllib.error
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
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Pages Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'gf@example.net', 'Tailscale-User-Name': 'Partner'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)        # the first sign-in is the owner; the second can only view

# ---- summer heat: the server side
h = call('GET', '/api/heat')[1]
check(h['zone'] is None and h['years'] == 0 and h['line'] == 86, 'with under 3 whole years of weather there is no heat zone yet')
call('POST', '/mock/history', {'years': 4})
h = call('GET', '/api/heat')[1]
check(h['years'] == 4 and 100 < h['over86'] < 130 and h['zone'] == 8 and h['hottest'] > 95 and h['months'][0]['month'] in ('May', 'Jun') and len(h['per_year']) == 5,
      f'4 years of Round Rock-like weather: about {h["over86"]} days above 86°F, heat zone {h["zone"]}, hottest {h["hottest"]}°F, hot days from {h["months"][0]["month"]}')
check(call('GET', '/api/meta')[1]['heat']['zone'] == 8, 'the meta answer carries the zone for plant pages')

# ---- shopping data for the list
call('PUT', '/api/wishlist', {'name': 'Pumice, 1/4 in', 'kind': 'amend', 'max_price': 1.2, 'price_per': 'unit', 'search_words': 'pumice'})
call('PUT', '/api/wishlist', {'name': '8 in terracotta pot', 'kind': 'pots', 'notes': 'Any size from 7 to 9 in will do.'})
call('PUT', '/api/wishlist', {'name': 'Monstera deliciosa', 'common_name': 'Swiss cheese plant'})
call('PUT', '/api/stores/roundrockgc/details', {'carries': ['amend', 'pots'], 'hours': 'Mon to Sat 9 am to 5 pm', 'phone': '512-555-0100', 'address': '901 Sam Bass Rd., Round Rock, TX 78681'})
# a request, so "Needed from you" has a row
r = call('GET', '/api/requests?open=1')[1]

FAKE_SPEECH = """
window.SpeechRecognition = window.webkitSpeechRecognition = class { constructor() { window.__rec = this; } start() { this.on = true; } stop() { this.on = false; if (this.onend) this.onend(); }
  say(parts) { const results = parts.map(([t, f]) => Object.assign([{ transcript: t }], { isFinal: f })); this.onresult({ resultIndex: 0, results }); } };
"""
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Pages Test');localStorage.removeItem('plantdb.filters');localStorage.removeItem('plantdb.shoplist');localStorage.removeItem('plantdb.frosthide');" + FAKE_SPEECH)

    # ---- Today is the page the app opens on
    pg.goto(LOCAL + '/'); pg.wait_for_timeout(3000)
    check(pg.locator('h1').first.inner_text() == 'Today' and pg.locator('#main-nav a[aria-current=page]').inner_text().strip() == 'Today', 'the app opens on Today')
    line = pg.locator('.verdict-box strong').first.inner_text()
    check('to water' in line and 'to feed' in line and 'needs from you' in line, f'one line says what needs you: "{line[:90]}"')
    jumps = pg.locator('.td-jumps a')
    check(jumps.count() >= 3 and jumps.first.inner_text().startswith('Cold night'), f'{jumps.count()} jump buttons, the cold night first')
    check(pg.locator('#today-cold h2').count() == 1 and pg.locator('#today-cold [data-act=frosthide]').count() == 0 and pg.locator('#app > .fz-banner').count() == 0,
          'the cold night is a section of the page (with a heading, no Hide button) and not also the banner')
    pg.locator('.td-jumps a[data-sec=today-needs]').click(); pg.wait_for_timeout(1800)
    check(pg.evaluate("document.activeElement && document.activeElement.closest('#today-needs') != null") and pg.evaluate("document.getElementById('today-needs').getBoundingClientRect().top < 300"), 'a jump button scrolls to its section and puts the focus there')
    check(pg.locator('#today-quiet').count() == 1 and 'ackup' in pg.locator('#today-quiet').inner_text(), 'Quiet today says about the stores, the backup and problems')
    check(pg.locator('#main-nav a[data-sec=plants]').get_attribute('href') == '#/plants', 'All plants lives at #/plants')
    pg.screenshot(path=f'{OUT}/pages-today.png', full_page=True)
    pg.goto(LOCAL + '/#/plants'); pg.wait_for_timeout(2500)
    check(pg.locator('#grid .sheet').count() > 10 and pg.locator('#sub-nav a[aria-current=page]').inner_text().strip() == 'All plants', 'and shows the plants')
    pg.goto(LOCAL + '/#/today'); pg.wait_for_timeout(2000)
    check(pg.locator('h1').first.inner_text() == 'Today', 'the old #/today address still works')

    # ---- summer heat on the Weather page and a plant page
    pg.goto(LOCAL + '/#/weather'); pg.wait_for_timeout(3500)
    t = pg.locator('#wx-climate').inner_text()
    check('AHS heat zone 8' in t and 'days above 86°F' in t and 'hardiness zone' in t and pg.locator('#wx-climate .heat-tbl tbody tr').count() == 4, 'the Weather page has a climate section: winter zone, summer heat zone and the hot days each year')
    pg.locator('#wx-climate').screenshot(path=f'{OUT}/pages-climate.png')
    pg.goto(LOCAL + '/#/plant/P-012'); pg.wait_for_timeout(3000)
    check('heat zone 8' in pg.inner_text('main'), 'a plant page says the summer heat zone next to the winter one')

    # ---- the shopping list
    pg.goto(LOCAL + '/#/shopping/list'); pg.wait_for_timeout(3000)
    sel = pg.locator('select[data-act=slstore]')
    check(sel.locator('option').count() >= 3 and 'carries' in sel.locator('option').first.inner_text(), 'the store list says how many of the items each store carries')
    pg.select_option('select[data-act=slstore]', 'roundrockgc'); pg.wait_for_timeout(2000)
    main = pg.locator('#sl-main')
    check(main.locator('h2').inner_text() == 'Round Rock Garden Center' and '901 Sam Bass' in main.inner_text() and 'Mon to Sat' in main.inner_text(), 'the store\'s name, address, phone and hours head the list')
    items = main.locator('.tick-list').first.locator('li')
    check(items.count() == 2 and 'Pumice' in items.first.inner_text() and '$1.20 a quart or less' in items.first.inner_text(), 'the items it carries come first, with what you are watching for')
    check('Not carried here' in main.inner_text() and 'Swiss cheese plant' in main.locator('.tick-list').nth(1).inner_text(), 'the rest are under "Not carried here"')
    pg.fill('form[data-form=sladd] input', 'Garden twine'); pg.click('form[data-form=sladd] button'); pg.wait_for_timeout(1500)
    check('Garden twine' in pg.locator('#sl-main').inner_text(), 'an extra line can be added')
    pg.locator('#sl-main .tick-list input').first.check(); pg.locator('#sl-main input[data-k="extra:Garden twine"]').check(); pg.wait_for_timeout(400)
    done = pg.locator('[data-act=sldone]')
    check(done.inner_text() == 'Done shopping: mark the 2 ticked as got' and not done.is_disabled(), 'ticks count towards Done shopping')
    pg.reload(); pg.wait_for_timeout(3000)
    check(pg.locator('#sl-main .tick-list input').first.is_checked(), 'the ticks survive a reload')
    pg.click('[data-act=slbig]'); pg.wait_for_timeout(300)
    check(pg.locator('#sl-main').evaluate("e => e.classList.contains('sl-big')") and pg.locator('[data-act=slbig]').get_attribute('aria-pressed') == 'true', 'Large print makes the list bigger')
    pg.screenshot(path=f'{OUT}/pages-shoplist.png', full_page=True)
    pg.click('[data-act=sldone]'); pg.wait_for_timeout(2500)
    w = {x['name']: x['status'] for x in call('GET', '/api/wishlist')[1]['wishlist']}
    check(w['Pumice, 1/4 in'] == 'got' and w['8 in terracotta pot'] == 'want' and 'Garden twine' not in pg.locator('#sl-main').inner_text(), 'Done shopping marks the ticked item as got and crosses off the extra line')
    # a phone
    ph = b.new_page(viewport={'width': 390, 'height': 800}, is_mobile=True, has_touch=True)
    ph.add_init_script("localStorage.setItem('plantdb.editor','Pages Test')")
    for path, tag in (('#/', 'today'), ('#/shopping/list', 'shoplist'), ('#/labels', 'labels')):
        ph.goto(LOCAL + '/' + path); ph.wait_for_timeout(2500)
        over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 2, f'phone, {path}: no sideways scrolling ({over}px)')
        ph.screenshot(path=f'{OUT}/pages-phone-{tag}.png', full_page=True)
    ph.close()

    # ---- dictation
    pg.goto(LOCAL + '/#/plant/P-012/edit'); pg.wait_for_timeout(3000)
    btn = pg.locator('label:has(textarea[name=notes]) + .spk-btn')
    check(btn.count() == 1 and btn.get_attribute('aria-label') == 'Speak into Notes' and not btn.is_visible(), 'a Speak button belongs to the Notes box, out of the way until the box is used')
    pg.fill('textarea[name=notes]', 'Old note.'); pg.focus('textarea[name=notes]'); pg.wait_for_timeout(300)
    check(btn.is_visible(), 'it shows when the box has the focus')
    btn.click(); pg.wait_for_timeout(300)
    check(btn.inner_text() == 'Listening… press to stop' and btn.get_attribute('aria-pressed') == 'true' and pg.evaluate('window.__rec.on'), 'pressing it starts listening')
    pg.evaluate("window.__rec.say([['the leaves look', false]])")
    check(pg.input_value('textarea[name=notes]') == 'Old note. The leaves look', 'words appear as they are recognised, after what was there')
    pg.evaluate("window.__rec.say([['the leaves look better today', true]])"); pg.evaluate("window.__rec.say([['new pot next week', true]])")
    check(pg.input_value('textarea[name=notes]') == 'Old note. The leaves look better today new pot next week', 'final words stay and the next ones follow')
    btn.click(); pg.wait_for_timeout(300)
    check(btn.inner_text() == 'Speak' and not pg.evaluate('window.__rec.on'), 'pressing it again stops')
    pg.focus('input[name=common_name]'); pg.wait_for_timeout(500)
    check(not btn.is_visible(), 'and it goes out of the way again')
    pg.click('form[data-form=edit] button[type=submit]'); pg.wait_for_timeout(2500)
    check(call('GET', '/api/plants/P-012')[1]['notes'].endswith('new pot next week'), 'what was said is saved with the plant')

    # ---- room and shelf labels
    pg.goto(LOCAL + '/#/labels'); pg.wait_for_timeout(3000)
    pl = pg.locator('#place-labels')
    check(pl.locator('.lbl').count() >= 10 and pl.locator('.lbl img').first.get_attribute('src').startswith('/api/where/qr.svg?area=1'), 'the Labels page has a label for every room, area and spot')
    yard = pl.locator('.lbl-open').first
    check(yard.get_attribute('href') == '#/plants?area=1', 'each opens the Plants page for that place')
    yard.click(); pg.wait_for_timeout(2500)
    chip, cnt = pg.locator('.place-chip').inner_text(), pg.locator('#count').inner_text()
    check(pg.evaluate('location.hash') == '#/plants' and chip.startswith('Showing the plants at Yard') and cnt.startswith('59 of 87'), f'the Plants page shows just that place: "{chip[:40]}", {cnt}')
    pg.click('[data-act=clearplace]'); pg.wait_for_timeout(1500)
    check(pg.locator('.place-chip').count() == 0 and pg.locator('#count').inner_text().startswith('87 of 87'), '"Show every place" clears it')
    pg.goto(LOCAL + '/#/plants?spot=1'); pg.wait_for_timeout(2500)
    check('Tall Black Shelf' in pg.locator('.place-chip').inner_text() and pg.locator('#count').inner_text().startswith('0 of 87'), 'a shelf label works the same way (an empty shelf shows none)')
    st, svg = urllib.request.urlopen(LOCAL + '/api/where/qr.svg?spot=1&base=http://plants.example').status, urllib.request.urlopen(LOCAL + '/api/where/qr.svg?spot=1&base=http://plants.example').read()
    check(st == 200 and b'<svg' in svg and call('GET', '/api/where/qr.svg?spot=999')[0] == 404, 'the code is an SVG; a spot that does not exist is a 404')

    # people who can only view
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    vw.goto(TS + '/#/shopping/list'); vw.wait_for_timeout(3000)
    check(vw.locator('[data-act=sldone]').count() == 1 and not vw.locator('[data-act=sldone]').is_visible() and vw.locator('.tick-list').count() >= 1, 'someone who can only view sees the list but not Done shopping')
    vw.close()
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
