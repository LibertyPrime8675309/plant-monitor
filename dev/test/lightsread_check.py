"""Checks Grow lights reading a layout (prototype, proto/lights-read-layouts; js/layoutlights.js): a shelf with a strip light drawn
on its layout and a light spot on Grow lights for the same shelf. Each plant of the spot that is drawn gets its own daily light
from the drawing (the number layouts.js works out), with a link to the layout that opens it with the plant chosen; its mark in
the spot is the layout's; a plant above the light is told no light reaches it; a plant that is not drawn keeps what its spot
gives; the spot's summary counts by those marks; the spot says how far under the light its plants are on the drawing and where
the light's hours and brightness are the layout's (the spot takes them, follows a change made there, and keeps them when saved
on Grow lights); a plant under a light on a layout but in no spot is listed and counts as having a light (the summary and the
suggested layout); the server's sums agree with the page's; a plant's own page; nothing is added when no layout has a light; a
phone at the largest text and with the reading settings at their strongest; the dark theme at 7 to 1.
Start the mock server with a fresh data folder, then: python3 dev/test/lightsread_check.py [http://127.0.0.1:8080]
Screenshots: dev/tmp/shots/lightsread-*.png"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from waits import until
from contrast_js import CONTRAST
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None, headers={'Content-Type': 'application/json', 'X-Editor': 'Lights Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
shot = lambda pg, name: pg.screenshot(path=os.path.join(OUT, f'lightsread-{name}.png'))

# a shelf, a strip light under its second board, and plants at different heights under it; one above it; one in no spot
W = call('GET', '/api/where')
spot = [s for h in W['homes'] for a in h['areas'] for s in a['spots'] if s['name'] == 'Tall Brown Shelf'][0]
P = {'cal': 'P-031', 'phil': 'P-009', 'haw': 'P-016', 'fern': 'P-024', 'beg': 'P-025', 'ever': 'P-028'}
for c in P.values(): call('PUT', f'/api/plants/{c}', {'base_version': call('GET', f'/api/plants/{c}')['version'], 'fields': {'spot_id': spot['id']}})
tb = next(p for p in call('GET', '/api/layouts')['places'] if p['pid'] == spot['id'])
lid = call('POST', '/api/layouts', {'name': 'Tall Brown Shelf', 'place': tb['pid'], 'width_in': 22, 'depth_in': 11, 'height_in': 90, 'items': tb['start']['items']})['id']
t5 = next(x for x in call('GET', f'/api/layouts/{lid}')['lights'] if 'T5' in x['name'])
pl = lambda code, x, y, z, w, h: {'kind': 'plant', 'plant': code, 'shape': 'round', 'x': x, 'y': y, 'z': z, 'w': w, 'd': w, 'h': h}
call('POST', f'/api/layouts/{lid}/items', {'items': [pl(P['haw'], 0, 3, 0.75, 4, 5), pl(P['cal'], 5, 2.5, 0.75, 5, 14), pl(P['phil'], 11, 2.5, 0.75, 5, 11), pl(P['ever'], 17, 2.5, 0.75, 5, 12), pl(P['fern'], 6, 2, 24.5, 7, 10),
    {'kind': 'light', 'light_id': t5['id'], 'shape': 'box', 'x': 5, 'y': 4.5, 'z': 22.25, 'w': 12, 'd': 2, 'h': 1.5, 'hours': 14}]})
sid = call('POST', '/api/lights/spots', {'name': 'Tall Brown Shelf, bottom level', 'light': t5['id'], 'units': 1, 'distance': 8, 'hours': 12, 'dim': 100, 'place': spot['id'], 'level': 'L1',
                                         'plants': [P['cal'], P['phil'], P['haw'], P['fern'], P['beg']]})['id']
L = call('GET', f'/api/layouts/{lid}'); item = {i['plant']: i['id'] for i in L['items'] if i['kind'] == 'plant'}; strip = next(i['id'] for i in L['items'] if i['kind'] == 'light')
check(call('GET', '/api/layouts')['verdicts']['dim'] == 'A bit dim', "the list of layouts carries the words for a plant's light, for Grow lights")

row = lambda pg, code: pg.locator(f'#lt-spots details.lt-spot-fold[data-id="{sid}"] ul.lt-plants > li', has=pg.locator(f'a.nm[href="#/plant/{code}"]'))
def opened(pg, opt=None, more=''):
    pg.add_init_script("localStorage.setItem('plantdb.editor','Lights Test');localStorage.setItem('plantdb.ltspots','[\"%s\"]');%s" % (sid, more))
    pg.goto(BASE + '/#/lights'); pg.wait_for_selector('#lt-spots', timeout=20000)

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 1000})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    opened(pg)
    check(until(pg, lambda: pg.locator('#lg-note').count() == 1 and pg.locator('#lt-spots li.lg-read').count() == 4) and '4 of the plants in the spots below' in pg.inner_text('#lg-note') and 'Tall Brown Shelf' in pg.inner_text('#lg-note'),
          'Grow lights says that it reads the layout, and how many of the plants in its spots are drawn there')
    mine = pg.evaluate(f"(async () => {{ const L = await api('GET', '/api/layouts/{lid}'), m = lyLight(L), o = {{}}; for (const it of L.items) if (it.kind === 'plant') o[it.plant] = [m.get(it.id).dli, m.get(it.id).verdict, m.get(it.id).reached]; return o; }})()")
    check([mine[P[k]][1] for k in ('cal', 'phil', 'haw', 'fern')] == ['good', 'dim', 'too_dim', 'none'] and not mine[P['fern']][2], f'(the layout itself gives the four drawn plants of the spot: good, a bit dim, too dim, and no light for the one above the strip: {mine})')
    num = lambda code: ('%.1f' % mine[code][0]).rstrip('0').rstrip('.')
    ok = all(f'about {num(P[k])} mol/m² a day' in row(pg, P[k]).locator('.lg-line').inner_text() and row(pg, P[k]).locator(f'.lg-line a[href="#/layouts/{lid}?sel={item[P[k]]}"]').count() == 1 for k in ('cal', 'phil', 'haw'))
    check(ok and 'under the Barrina' in row(pg, P['cal']).locator('.lg-line').inner_text() and 'to the side' in row(pg, P['haw']).locator('.lg-line').inner_text(),
          "each drawn plant has a line with the layout's own number for it, how far under the light it is (and to the side), and a link to the layout with it chosen")
    check(row(pg, P['cal']).locator(':scope > .lv-good').count() == 1 and row(pg, P['phil']).locator(':scope > .lv-dim').count() == 1 and row(pg, P['haw']).locator(':scope > .lv-too_dim').count() == 1
          and row(pg, P['fern']).locator(':scope > .lg-none').count() == 1 and 'No light reaches it' in row(pg, P['fern']).inner_text() and 'no light drawn there reaches it' in row(pg, P['fern']).locator('.lg-line').inner_text(),
          "the plant's mark in its spot is the layout's: good, a bit dim, too dim; the plant above the strip is told no light reaches it")
    sp = pg.evaluate(f"LT.spots.find(s => s.id === {sid})"); was = {p['code']: p for p in sp['plants']}
    check(sp['hours'] == 14 and sp['layout']['id'] == lid and call('GET', '/api/lights')['spots'][0]['hours'] == 14, "the spot's hours are the drawn light's (14 a day on the layout, though the spot was set up with 12)")
    check(all((f"The spot's one setting gives {was[P[k]]['verdict'] and sp['dli']} ({was[P[k]]['verdict_word']})" in row(pg, P[k]).inner_text()) == (was[P[k]]['verdict'] != mine[P[k]][1]) for k in ('cal', 'phil', 'haw')),
          f"where the spot's one setting would have said something else, the line says what ({sp['dli']}, {[(k, was[P[k]]['verdict']) for k in ('cal', 'phil', 'haw')]})")
    srv = pg.evaluate('LT.readings')
    check(all(srv[P[k]][0]['dli'] == mine[P[k]][0] and srv[P[k]][0]['verdict'] == mine[P[k]][1] for k in ('cal', 'phil', 'haw', 'fern', 'ever')),
          f"the server works out the same light for each drawn plant as the page does ({[(k, srv[P[k]][0]['dli'], mine[P[k]][0]) for k in ('cal', 'phil', 'haw', 'fern', 'ever')]})")
    check(row(pg, P['beg']).locator('.lg-line').count() == 0 and row(pg, P['beg']).locator(':scope > .lv-good').count() == 1 and 'lg-read' not in (row(pg, P['beg']).get_attribute('class') or ''), 'a plant of the spot that is not drawn keeps what its spot gives')
    sm = pg.inner_text(f'#lt-spots details.lt-spot-fold[data-id="{sid}"] summary')
    check('Plants: 5 (3 not in their range)' in sm and '4 of 5 read from a layout' in sm, f'the spot says how many are read from a layout, and counts the plants out of their range by those marks ({sm!r})')
    sl = pg.inner_text(f'#lt-spots details.lt-spot-fold[data-id="{sid}"] .lg-spot')
    check('4 of its 5 plants are drawn' in sl and 'Their tops are 7.5 in to 16.5 in under this light; this spot says 8 in from the leaves' in sl and 'Its hours (14 a day) and brightness (100%) are set on the layout' in sl,
          f'the spot says how far under the light its plants are on the drawing against its own one distance, and that its hours and brightness are set on the layout ({sl!r})')
    pg.click('#lg-note .lg-fold summary')
    check('no light spot (1)' in pg.inner_text('#lg-note .lg-fold summary') and pg.locator(f'#lg-note .lg-fold a.nm[href="#/plant/{P["ever"]}"]').is_visible() and 'mol/m² a day' in pg.inner_text('#lg-note .lg-fold'),
          'a plant under the light on the layout that is in no spot is listed, with its number')
    lt = pg.evaluate('({ drawn: LT.drawn, plan: LT.plan.flatMap(p => p.codes), cand: LT.candidates.map(c => c.code) })')
    head = pg.evaluate("[...document.querySelectorAll('.lt-sum-tbl th')].map(t => t.textContent)")
    check(P['ever'] in lt['drawn'] and P['ever'] not in lt['plan'] and (P['ever'] not in lt['cand'] or ('Under a light on a layout' in head and 'No light yet' in head)) and 'count as having a light' in pg.inner_text('#lg-note .lg-fold'),
          f'it counts as having a light: the suggested layout leaves it out, and the summary counts it apart ({head} {P["ever"] in lt["drawn"]} {P["ever"] in lt["plan"]} {P["ever"] in lt["cand"]} {pg.inner_text("#lg-note .lg-fold")[:200]!r})')
    check(pg.evaluate(CONTRAST) in (None, []) or not [x for x in pg.evaluate(CONTRAST) if 'lg-' in x], 'the new lines are at 7 to 1')
    shot(pg, '1-decides')
    row(pg, P['phil']).locator('.lg-line a').click()
    check(until(pg, lambda: pg.evaluate('!!LY && LY.d.id') == lid and pg.evaluate('LY.sel') == item[P['phil']]), 'the link opens the layout with that plant chosen')

    # ---- the layout changes: the spot and Grow lights follow; saved on Grow lights, the spot keeps the layout's hours
    pg.evaluate(f"api('PUT', '/api/layouts/items/{strip}', {{ hours: 10, dim_pct: 100 }})")      # through the page, as the Layouts page does it: the page's saved answers are dropped
    pg.goto(BASE + '/#/lights'); until(pg, lambda: pg.locator('#lt-spots li.lg-read').count() == 4 and 'Its hours (10 a day)' in pg.inner_text('.lg-spot'))
    check(call('GET', '/api/lights')['spots'][0]['hours'] == 10 and 'Its hours (10 a day)' in pg.inner_text('.lg-spot') and f'about {num(P["cal"])} mol' not in row(pg, P['cal']).locator('.lg-line').inner_text(),
          "the drawn light's hours changed on the layout: the spot takes them, and the plants' numbers follow")
    pg.click(f'#lt-spots details.lt-spot-fold[data-id="{sid}"] [data-act=spotedit]'); pg.wait_for_selector('dialog[open] form[data-spot]')
    hrs = pg.locator('dialog[open] input[name=hours]')
    shown = lambda: [hrs.get_attribute('readonly') is not None, hrs.input_value(), pg.locator('dialog[open] select[name=dim]').is_disabled(), 'set on the layout' in pg.inner_text('dialog[open] label:has(input[name=hours])'),
                     pg.locator(f'dialog[open] .sp-layout a[href="#/layouts/{lid}?sel={strip}"]').count()]
    check(until(pg, lambda: shown() == [True, '10', True, True, 1]), f"Change this spot shows the hours and brightness as set on the layout, with a link to it ({shown()})")
    pg.click('dialog[open] button[value=ok]'); pg.wait_for_selector('dialog[open]', state='detached')
    check(until(pg, lambda: call('GET', '/api/lights')['spots'][0]['hours'] == 10), 'saved, the spot keeps the layout\'s hours')
    call('PUT', f'/api/layouts/items/{strip}', {'hours': 14})

    # ---- a plant's own page
    pg.goto(f"{BASE}/#/plant/{P['phil']}")
    check(until(pg, lambda: pg.locator('#lg-plant').count() == 1) and f'about {num(P["phil"])} mol/m² a day' in pg.inner_text('#lg-plant') and pg.locator('#lg-plant .lv-dim').count() == 1
          and pg.locator(f'#lg-plant a[href="#/layouts/{lid}?sel={item[P["phil"]]}"]').count() == 1, "a drawn plant's own page says its light on the layout, with the mark and a link")
    shot(pg, '2-plant')
    pg.goto(f"{BASE}/#/plant/{P['beg']}"); pg.wait_for_selector('#pl-grow', state='attached'); pg.wait_for_timeout(1500)
    check(pg.locator('#lg-plant').count() == 0, 'the page of a plant that is not drawn says nothing about a layout')
    pg.close()

    # ---- a phone at the largest text, and with the reading settings at their strongest
    for name, prefs in (('largest text, dark', {'size': '190', 'theme': 'dark'}), ('reading settings at their strongest', {'font': 'dyslexic', 'plain': '1', 'space': 'widest', 'size': '190', 'theme': 'cream'})):
        ctx = br.new_context(viewport={'width': 384, 'height': 760}, is_mobile=True, has_touch=True, device_scale_factor=2, service_workers='block'); ph = ctx.new_page(); ph.on('pageerror', lambda e: errs.append(str(e)))
        opened(ph, None, "localStorage.setItem('plantdb.display', %s);" % json.dumps(json.dumps(prefs)))
        ok = until(ph, lambda: ph.locator('#lt-spots li.lg-read').count() == 4)
        over = ph.evaluate('document.documentElement.scrollWidth - innerWidth'); low = [x for x in (ph.evaluate(CONTRAST) or []) if 'lg-' in x or 'lv' in x]
        check(ok and over <= 1 and not low, f'a phone, {name}: the lines are there, nothing scrolls sideways ({over}), and they are at 7 to 1 ({low[:2]})')
        ph.evaluate("document.querySelector('#lt-spots li.lg-read').scrollIntoView({ block: 'center' })"); ph.wait_for_timeout(200); shot(ph, '4-phone-' + ('dark' if 'dark' in name else 'reading')); ctx.close()

    # ---- no layout has a light: Grow lights is as it was
    call('DELETE', f'/api/layouts/items/{strip}')
    pg = br.new_page(viewport={'width': 1280, 'height': 1000}); pg.on('pageerror', lambda e: errs.append(str(e)))
    opened(pg); pg.wait_for_selector(f'#lt-spots details.lt-spot-fold[data-id="{sid}"] ul.lt-plants > li'); pg.wait_for_timeout(1500)
    sp = pg.evaluate(f"LT.spots.find(s => s.id === {sid})"); off = sum(1 for p in sp['plants'] if p['verdict'] not in ('good', 'unknown'))
    check(pg.locator('#lg-note').count() == 0 and pg.locator('.lg-line').count() == 0 and pg.locator('.lg-spot').count() == 0 and sp['layout'] is None and not pg.evaluate('Object.keys(LT.drawn).length')
          and row(pg, P['haw']).locator(f":scope > .lv-{was[P['haw']]['verdict']}").count() == 1
          and (f'Plants: 5 ({off} not in their range)' if off else 'Plants: 5') in pg.inner_text(f'#lt-spots details.lt-spot-fold[data-id="{sid}"] summary'), 'with no grow light drawn on any layout, Grow lights is as it was, and the spot sets its own hours again')
    br.close()

call('DELETE', f'/api/lights/spots/{sid}'); call('DELETE', f'/api/layouts/{lid}')
print(f'\n{len(fails)} FAIL, {len(errs)} page errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
sys.exit(1 if fails or errs else 0)
