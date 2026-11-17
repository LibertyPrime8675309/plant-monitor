"""Checks what Layouts gained on November 17, 2026 (1.58.0; js/layouts.js, plantdb/layouts.py), at Ethan's asking: "3D View; Light
drawn as a picture; Daylight from windows and the shade one plant casts on another; Resizing a shelf's boards doesn't change that
shelf's measurements in the record; Choosing several things at once and lining them up; Changing a layout with no connection".
- The sums, asked directly: a window's daylight is half as much 2 ft from the glass and none behind its wall; a board between shuts
  it out; a plant in the way lets half of a light or a window through.
- A room's layout with a window, a grow light and plants: the server's readings (Grow lights) and the page's agree, shade included;
  a window's way and daylight changed in its boxes, and Undo.
- The light map on the top view: shaded squares, numbers, a key in words; at another height.
- The 3D view: drawn, turned, looked at from higher, a thing chosen by pressing it and moved with the arrow keys, Start view.
- Choosing several: Shift with a press, and the list's "With the chosen thing"; lined up by their left edges, spread out evenly,
  moved together by the arrow keys, one Undo for each; Escape chooses one again.
- A shelf's boards moved on its own layout, and a shelf's block resized on a room's layout: saved to its measurements, and Undo.
- Without a connection: what the waiting change is called, and the offline copy keeps the layouts.
- A phone in the dark theme at the largest text: the 3D view and the light map, no sideways scrolling.
Start the mock server with a fresh data folder, then: python3 dev/test/layoutsmore_check.py [http://127.0.0.1:8080]
Screenshots: dev/tmp/shots/layoutsmore-*.png"""
import json, os, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from waits import until
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []

def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None, headers={'Content-Type': 'application/json', 'X-Editor': 'Layout Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
over = lambda pg: pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
shot = lambda pg, name: pg.screenshot(path=os.path.join(OUT, f'layoutsmore-{name}.png'), full_page=True)
def it(pg, iid): return pg.evaluate("i => { const t = LY.d.items.find(x => x.id === i); return t ? { x: t.x, y: t.y, z: t.z, w: t.w, d: t.d, h: t.h, facing: t.facing, day_dli: t.day_dli } : null; }", iid)
def saved(lid, iid): return next((x for x in call('GET', f'/api/layouts/{lid}')['items'] if x['id'] == iid), None)
def centre(pg, view, iid):
    return pg.evaluate("""([v, i]) => { const g = document.querySelector(`svg.ly-svg[data-view="${v}"] g.ly-it[data-id="${i}"]`); g.scrollIntoView({ block: 'center' });
      const r = g.querySelector('.ly-shape').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }""", [view, iid])
def press(pg, sel):
    for n in range(4):
        until(pg, lambda: pg.locator(sel).first.is_visible() and pg.locator(sel).first.is_enabled())
        try: pg.locator(sel).first.click(timeout=5000); return
        except Exception:
            if n == 3: raise
            pg.wait_for_timeout(150)
def pick(pg, iid):
    pg.locator(f'#ly-things-body [data-act=lypick][data-id="{iid}"]').click()
    return until(pg, lambda: pg.evaluate('LY.sel') == iid)
def opened(pg, lid, n=1):
    if pg.url.endswith(f'#/layouts/{lid}'): pg.goto(f'{BASE}/#/layouts'); until(pg, lambda: pg.locator('h1').first.inner_text().startswith('Layouts'))
    pg.goto(f'{BASE}/#/layouts/{lid}')
    return until(pg, lambda: pg.evaluate('typeof LY !== "undefined" && !!LY && !!LY.d && LY.d.id') == lid and pg.locator('svg.ly-svg[data-live]').count() >= 1 and pg.locator('svg.ly-svg[data-live] g.ly-it').count() >= n)

W = call('GET', '/api/where')
spot = [s for h in W['homes'] for a in h['areas'] for s in a['spots'] if s['name'] == 'Tall Brown Shelf'][0]
area = next(a for h in W['homes'] for a in h['areas'] if any(x['id'] == spot['id'] for x in a['spots']))
plants = call('GET', '/api/plants')[:6]

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_context(viewport={'width': 1440, 'height': 1000}).new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Layout Test')")

    # ---- the sums, asked directly on the page
    places = call('GET', '/api/layouts')['places']
    start = next(x for x in places if x['pid'] == -area['id'])['start']
    rid = call('POST', '/api/layouts', {'name': 'Room with a window', 'place': -area['id'], 'width_in': 120, 'depth_in': 100, 'height_in': 96, 'items': []})['id']
    check(opened(pg, rid, 0), 'a room layout with nothing on it opens')
    sums = pg.evaluate("""() => {
      const T = (id, kind, x, y, z, w, d, h, more) => Object.assign({ id, sort: id, name: kind + ' ' + id, kind, shape: 'box', x, y, z, w, d, h }, more || {});
      const L = items => ({ width_in: 120, depth_in: 100, height_in: 96, items });
      const win = T(1, 'window', 40, 0, 30, 36, 4, 48, { facing: 'S', day_dli: 12 });
      const at = (y, items) => { const pl = T(2, 'plant', 54, y - 4, 0, 8, 8, 40); const o = lyDayOn(L([win, pl].concat(items || [])), pl, win); return o ? { dli: o.dli, by: !!o.by, shade: o.shade.length } : null; };
      const strip = T(5, 'light', 40, 40, 60, 24, 2, 1.5, { pts: [[6, 400, 4], [12, 200, 6], [24, 80, 10]], near_in: 6, far_in: 24, hours: 12, dim_pct: 100 });
      const under = T(6, 'plant', 48, 37, 0, 8, 8, 30), top = T(7, 'plant', 46, 35, 20, 12, 12, 30);
      const one = lyLight(L([strip, under])).get(6).dli, shaded = lyLight(L([strip, under, T(8, 'plant', 46, 35, 40, 12, 12, 12)])).get(6);
      return { near: at(4 + 24), behind: lyDayOn(L([win]), T(3, 'plant', 54, -20, 0, 8, 8, 40), win), board: at(48, [T(4, 'shelf', 30, 20, 0, 60, 2, 90)]),
               shade: at(60, [T(9, 'plant', 50, 30, 0, 16, 16, 60)]), clear: at(60), one, shaded: shaded.dli, sname: shaded.shade };
    }""")
    check(sums['near'] and abs(sums['near']['dli'] - 6) < 0.01, f"a window's daylight is half as much 2 ft straight out from the glass ({sums['near']})")
    check(sums['behind'] is None, 'a plant behind the window\'s wall gets none of its daylight')
    check(sums['board'] and sums['board']['by'], f"a board between the window and the plant shuts it out ({sums['board']})")
    check(sums['shade'] and sums['shade']['shade'] == 1 and abs(sums['shade']['dli'] - sums['clear']['dli'] / 2) < 0.01, f"a plant in the way lets half of a window's daylight through ({sums['shade']}, {sums['clear']})")
    check(abs(sums['shaded'] - round(sums['one'] / 2 * 10) / 10) <= 0.1 and sums['sname'] == ['plant 8'], f"a plant in the way lets half of a light through, and is named ({sums['one']}, {sums['shaded']}, {sums['sname']})")

    # ---- a room with a window, a grow light and plants: the server's readings and the page's agree
    full = call('GET', f'/api/layouts/{rid}')
    t5 = next(x for x in full['lights'] if x['figures'])
    A, B, C = plants[0]['code'], plants[1]['code'], plants[2]['code']
    call('POST', f'/api/layouts/{rid}/items', {'items': [
        {'kind': 'window', 'name': 'South window', 'shape': 'box', 'x': 40, 'y': 0, 'z': 30, 'w': 36, 'd': 4, 'h': 48, 'facing': 'S'},
        {'kind': 'plant', 'plant': A, 'shape': 'round', 'w': 8, 'd': 8, 'h': 30, 'x': 54, 'y': 20, 'z': 0},
        {'kind': 'plant', 'plant': B, 'shape': 'round', 'w': 8, 'd': 8, 'h': 12, 'x': 54, 'y': 50, 'z': 0},
        {'kind': 'plant', 'plant': C, 'shape': 'round', 'w': 8, 'd': 8, 'h': 12, 'x': 90, 'y': 60, 'z': 0},
        {'kind': 'light', 'light_id': t5['id'], 'name': t5['name'], 'shape': t5['shape'], 'w': t5['w'], 'd': t5['d'], 'h': t5['h'], 'x': 80, 'y': 60, 'z': 40}]})
    R = call('GET', f'/api/layouts/{rid}')
    for code, h in ((A, 30), (B, 12), (C, 12)):                  # their pages may give other heights: make them these
        iid = next(i['id'] for i in R['items'] if i['plant'] == code); call('PUT', f'/api/layouts/items/{iid}', {'h': h})
    R = call('GET', f'/api/layouts/{rid}'); ids = {i['plant']: i['id'] for i in R['items'] if i['plant']}
    win = next(i for i in R['items'] if i['kind'] == 'window')
    check(win['facing'] == 'S' and win['day_dli'] == 12 and set(R['facing']) >= {'N', 'S', 'E', 'W'}, f"a window is saved with the way it faces and its usual daylight ({win.get('facing')}, {win.get('day_dli')})")
    check(opened(pg, rid, 5), 'the room opens with its window, light and plants')
    page = pg.evaluate("() => Object.fromEntries([...LY.F.light].map(([id, x]) => [id, { dli: x.dli, day: x.day, shade: x.shade, verdict: x.verdict }]))")
    rd = call('GET', '/api/lights')['readings']
    srv = {code: next(r for r in rd.get(code, []) if r['lid'] == rid) for code in (A, B, C) if any(r['lid'] == rid for r in rd.get(code, []))}
    check(len(srv) == 3 and all(srv[c]['dli'] == page[str(ids[c])]['dli'] and srv[c]['day'] == page[str(ids[c])]['day'] and srv[c]['verdict'] == page[str(ids[c])]['verdict'] for c in srv),
          f"the server's readings (Grow lights) and the page's agree for each plant, daylight included ({[(c, srv[c]['dli'], page[str(ids[c])]['dli']) for c in srv]})")
    an = next(i['name'] for i in R['items'] if i['plant'] == A)
    check(page[str(ids[B])]['shade'] == [an] and srv[B]['shade'] == [an] and page[str(ids[A])]['day'] > page[str(ids[B])]['day'] > 0,
          f"{an} shades the plant behind it from the window, on the page and on the server ({page[str(ids[B])]}, {srv[B].get('shade')})")
    pick(pg, ids[B])
    words = pg.inner_text('#ly-p-light')
    check('South window' in words and 'from the glass' in words and f'In the shade of {an}' in words and 'Daylight is from the windows drawn here' in words,
          f"the chosen plant's boxes say its daylight, from which window and how far, and what shades it ({words[:240]!r})")
    pick(pg, win['id'])
    check(pg.locator('#ly-f-facing').input_value() == 'S' and pg.locator('#ly-f-day_dli').input_value() == '12' and 'In the back wall' in pg.inner_text('#ly-panel'),
          'a window\'s boxes: the way it faces, its daylight at the glass, and the wall it is in')
    pg.select_option('#ly-f-facing', 'N')
    check(until(pg, lambda: it(pg, win['id'])['day_dli'] == 4 and saved(rid, win['id'])['facing'] == 'N' and saved(rid, win['id'])['day_dli'] == 4),
          'turned to face north, it takes a north window\'s usual daylight, saved')
    pg.fill('#ly-f-day_dli', '7.5'); pg.press('#ly-f-day_dli', 'Enter')
    check(until(pg, lambda: saved(rid, win['id'])['day_dli'] == 7.5), 'a daylight reading typed in is saved')
    press(pg, '#ly-undo'); press(pg, '#ly-undo')
    check(until(pg, lambda: saved(rid, win['id'])['facing'] == 'S' and saved(rid, win['id'])['day_dli'] == 12), 'Undo twice puts back its way and its daylight')

    # ---- the light map
    pg.check('#ly-lmap')
    check(until(pg, lambda: pg.locator('svg.ly-svg[data-view=top] rect.ly-lm').count() > 100) and pg.locator('svg.ly-svg[data-view=top] text.ly-lmn').count() >= 6
          and 'Deeper yellow is more light' in pg.inner_text('.ly-lmkey') and pg.locator('.ly-lmbands li').count() == 6,
          f"the light map: shaded squares, numbers on them and a key in words ({pg.locator('svg.ly-svg[data-view=top] rect.ly-lm').count()} squares)")
    near = pg.evaluate("lyLightAt(LY.d, 58, 10, 12)"); far = pg.evaluate("lyLightAt(LY.d, 10, 95, 12)")
    check(near > far and pg.evaluate("lyLband(lyLightAt(LY.d, 58, 10, 12))") > pg.evaluate("lyLband(lyLightAt(LY.d, 10, 95, 12))"), f'near the window the map is deeper than in the far corner ({near:.1f}, {far:.1f})')
    shot(pg, '1-lightmap')
    pg.click('#ly-more'); pg.select_option('#ly-lmapz', '48')
    check(until(pg, lambda: '4 ft off the floor' in pg.inner_text('.ly-lmkey') or '48 in off the floor' in pg.inner_text('.ly-lmkey')), f"at another height, the key says which ({pg.inner_text('.ly-lmkey')[:120]!r})")
    pg.select_option('#ly-lmapz', 'auto'); pg.uncheck('#ly-lmap')
    check(until(pg, lambda: pg.locator('rect.ly-lm').count() == 0), 'unticked, the light map goes')

    # ---- the 3D view
    pg.check('#ly-v-3d')
    check(until(pg, lambda: pg.locator('svg.ly-svg[data-view="3d"] g.ly-it').count() >= 5) and pg.locator('svg.ly-svg[data-view="3d"] polygon.ly-3wall').count() == 2
          and 'Seen from the front left' in pg.inner_text('figure[data-view="3d"] figcaption'), '3D view: the things, the floor and the two walls behind, seen from the front left')
    before = pg.inner_text('figure[data-view="3d"] figcaption')
    press(pg, '#ly-3right'); press(pg, '#ly-3right')
    check(until(pg, lambda: 'Seen from the front right' in pg.inner_text('figure[data-view="3d"] figcaption')) and pg.evaluate('LY.az') == 25, f"Turn right twice: seen from the front right ({pg.evaluate('LY.az')})")
    for _ in range(3): press(pg, '#ly-3up')
    check(until(pg, lambda: pg.locator('#ly-3up').is_disabled()) and 'high above' in pg.inner_text('figure[data-view="3d"] figcaption'), 'Look from higher, as far as it goes')
    shot(pg, '2-3d')
    at = centre(pg, '3d', ids[C]); pg.mouse.click(at[0], at[1])
    check(until(pg, lambda: pg.evaluate('LY.sel') == ids[C]) and pg.locator(f'svg.ly-svg[data-view="3d"] g.ly-it.is-sel[data-id="{ids[C]}"]').count() >= 1, 'a plant is chosen by pressing it in the 3D view')
    x0 = it(pg, ids[C]); pg.evaluate("i => lyFocusIt(i, '3d')", ids[C]); pg.keyboard.press('ArrowRight')
    check(until(pg, lambda: (saved(rid, ids[C])['x'], saved(rid, ids[C])['y']) != (x0['x'], x0['y'])), 'the arrow keys move it in the 3D view, and the move is saved')
    check(pg.evaluate('document.activeElement && document.activeElement.closest && document.activeElement.closest("g.ly-it") ? +document.activeElement.closest("g.ly-it").dataset.id : null') == ids[C], 'the keyboard stays on it as the 3D view is drawn again')
    press(pg, '#ly-3reset')
    check(until(pg, lambda: pg.evaluate('[LY.az, LY.el]') == [-35, 35]), 'Start view turns it back')
    press(pg, '#ly-undo')
    check(until(pg, lambda: (saved(rid, ids[C])['x'], saved(rid, ids[C])['y']) == (x0['x'], x0['y'])), 'Undo takes the move back')

    # ---- choosing several things, and lining them up
    pg.check('#ly-v-top')
    until(pg, lambda: pg.locator('svg.ly-svg[data-view=top] g.ly-it').count() >= 5)
    pick(pg, ids[A])
    at = centre(pg, 'top', ids[C]); pg.mouse.move(at[0], at[1]); pg.keyboard.down('Shift'); pg.mouse.down(); pg.mouse.up(); pg.keyboard.up('Shift')
    check(until(pg, lambda: pg.evaluate('[...LY.many]') == [ids[C]] and pg.evaluate('LY.sel') == ids[A]) and '2 things chosen' in pg.inner_text('#ly-group'),
          'Shift with a press adds a thing to the group, and the panel says how many are chosen')
    pg.locator(f'#ly-things-body input[data-act=lywith][data-id="{ids[B]}"]').check()
    check(until(pg, lambda: sorted(pg.evaluate('[...LY.many]')) == sorted([ids[C], ids[B]])) and '3 things chosen' in pg.inner_text('#ly-group'), '"With the chosen thing" in the list adds another')
    ax = it(pg, ids[A])['x']
    pg.locator('#ly-group [data-act=lyline][data-how=left]').click()
    check(until(pg, lambda: saved(rid, ids[C])['x'] == ax and saved(rid, ids[B])['x'] == ax) and 'lined up' in pg.locator('#ly-undo').inner_text(), 'Left edges: each lines up with the first, saved, one Undo')
    press(pg, '#ly-undo')
    check(until(pg, lambda: saved(rid, ids[C])['x'] == 90 and saved(rid, ids[B])['x'] == 54), 'Undo puts them all back')
    pg.locator('#ly-group [data-act=lyline][data-how=spready]').click()
    def gaps():
        ts = sorted((saved(rid, ids[k]) for k in (A, B, C)), key=lambda t: t['y'])
        return [round(ts[i + 1]['y'] - ts[i]['y'] - ts[i]['d'], 2) for i in range(2)]
    check(until(pg, lambda: len(set(gaps())) == 1), f'Spread them out back to front: the same space between each ({gaps()})')
    press(pg, '#ly-undo')
    ys = {k: saved(rid, ids[k])['y'] for k in (A, B, C)}
    pg.evaluate("i => lyFocusIt(i, 'top')", ids[A]); pg.keyboard.press('ArrowDown')
    check(until(pg, lambda: all(saved(rid, ids[k])['y'] > ys[k] for k in (A, B, C))), 'the arrow keys move the whole group')
    press(pg, '#ly-undo')
    check(until(pg, lambda: all(saved(rid, ids[k])['y'] == ys[k] for k in (A, B, C))), 'one Undo takes the whole group back')
    pg.evaluate("i => lyFocusIt(i, 'top')", ids[A]); pg.keyboard.press('Escape')
    check(until(pg, lambda: pg.evaluate('LY.many.size') == 0 and pg.evaluate('LY.sel') == ids[A]) and pg.locator('#ly-group').count() == 0, 'Escape chooses only the one thing again')
    shot(pg, '3-group')

    # ---- a shelf's boards and size saved to its measurements
    sheet0 = call('GET', f"/api/rooms/{spot['id']}")['sheet']
    sstart = next(x for x in places if x['pid'] == spot['id'])['start']
    sid = call('POST', '/api/layouts', {'name': 'Shelf for the check', 'place': spot['id'], **{k: sstart[k] for k in ('width_in', 'depth_in', 'height_in', 'items')}})['id']
    S = call('GET', f'/api/layouts/{sid}'); lv2 = next(i for i in S['items'] if i['name'].startswith('Level 2'))
    check(S['sheet'] and S['sheet']['levels'] == 4, f"a shelf's own layout carries its measurements ({S.get('sheet')})")
    opened(pg, sid, 4)
    check(pg.locator('#ly-sheet').is_hidden(), 'with its boards as its measurements say, nothing is said about them')
    pick(pg, lv2['id']); pg.uncheck('#ly-f-locked'); until(pg, lambda: not pg.locator('#ly-f-z').is_disabled())
    pg.fill('#ly-f-z', str(lv2['z'] + 2)); pg.press('#ly-f-z', 'Enter')
    check(until(pg, lambda: pg.locator('#ly-sheet').is_visible() and 'the clear height of each level' in pg.inner_text('#ly-sheet')), f"a board moved 2 in up: the page says the clear heights now differ ({pg.inner_text('#ly-sheet')[:200]!r})")
    g0 = sheet0.get('gaps_in') or []
    pg.locator('#ly-sheet [data-act=lysheet]').first.click()
    s1 = {}
    def got():
        s1.update(call('GET', f"/api/rooms/{spot['id']}")['sheet']); return s1.get('gaps_in') == [round(g0[0] + 2, 1), round(g0[1] - 2, 1), g0[2]]
    check(until(pg, got) and all(s1.get(k) == sheet0.get(k) for k in sheet0 if k not in ('gaps_in', 'gap_in', 'levels', 'width_in', 'depth_in', 'top_in')),
          f"Save these: the shelf's measurements take the new clear heights, and keep the rest ({sheet0.get('gaps_in')} to {s1.get('gaps_in')})")
    check(until(pg, lambda: pg.locator('#ly-sheet').is_hidden()), 'once saved, the layout and the measurements agree')
    press(pg, '#ly-undo')
    check(until(pg, lambda: call('GET', f"/api/rooms/{spot['id']}")['sheet'].get('gaps_in') == g0), 'Undo puts back what the measurements said')
    opened(pg, rid, 5)
    call('POST', f'/api/layouts/{rid}/items', {'kind': 'shelf', 'spot_id': spot['id'], 'name': spot['name'], 'shape': 'box', 'w': sheet0['width_in'], 'd': sheet0['depth_in'], 'h': 60, 'x': 0, 'y': 80, 'z': 0})
    opened(pg, rid, 6)
    blk = pg.evaluate("sp => LY.d.items.find(i => i.spot_id === sp).id", spot['id'])
    pick(pg, blk); pg.fill('#ly-f-w', '30'); pg.press('#ly-f-w', 'Enter')
    check(until(pg, lambda: pg.locator('#ly-sheet').is_visible() and '30 in wide' in pg.inner_text('#ly-sheet')), "a shelf's block made wider on a room's layout: the page offers its width")
    pg.locator('#ly-sheet [data-act=lysheet]').first.click()
    check(until(pg, lambda: call('GET', f"/api/rooms/{spot['id']}")['sheet'].get('width_in') == 30), 'saved: the shelf is 30 in wide in its measurements')

    # ---- without a connection
    check(pg.evaluate("offWords({ method: 'PUT', url: '/api/layouts/items/5', body: { x: 4, _what: 'Fig' } })") == 'A layout: Fig moved', 'a change waiting on this device is called by what moved')
    urls = call('GET', '/api/offline/manifest')['urls']
    check('/api/layouts' in urls and f'/api/layouts/{rid}' in urls and f'/api/layouts/{sid}' in urls, 'the copy kept on a device for offline use has the layouts')

    # ---- a phone, dark, the largest text
    ph = br.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, has_touch=True).new_page()
    ph.on('pageerror', lambda e: errs.append(str(e)))
    ph.add_init_script("localStorage.setItem('plantdb.editor','Phone');localStorage.setItem('plantdb.display', JSON.stringify({theme:'dark', size:'190'}))")
    ph.goto(f'{BASE}/#/layouts/{rid}'); ph.wait_for_selector('#ly-draw svg.ly-svg', timeout=20000)
    ph.check('#ly-v-3d'); until(ph, lambda: ph.locator('svg.ly-svg[data-view="3d"]').count() == 1)
    check(over(ph) <= 0, f'phone, dark, the largest text: the 3D view with no sideways scrolling ({over(ph)}px)')
    ph.screenshot(path=os.path.join(OUT, 'layoutsmore-4-phone-3d.png'), full_page=True)
    ph.check('#ly-v-top'); ph.check('#ly-lmap'); until(ph, lambda: ph.locator('rect.ly-lm').count() > 0)
    check(over(ph) <= 0 and ph.locator('.ly-lmkey').is_visible(), f'and the light map with its key, no sideways scrolling ({over(ph)}px)')
    ph.screenshot(path=os.path.join(OUT, 'layoutsmore-5-phone-map.png'), full_page=True)
    br.close()

print('page errors:', errs)
print(f'{len(fails)} FAIL, {len(errs)} page errors')
sys.exit(1 if fails or errs else 0)
