"""Checks Layouts (prototype, proto/layouts; plantdb/layouts.py, js/layouts.js): what counts as overlapping, sticking out, tight,
in the air, close to a light or in an area to keep clear (lyFindings, asked directly); a layout started from a shelf's own
button on Rooms and spots, with its levels drawn from its measurements; the plants that are there put on it, each on a level
where it fits; a thing chosen and moved by the arrow keys (said aloud, saved once the keys pause, the keyboard kept), by typing,
by "Stands on", and by dragging (snapped to the grid, or freely with snapping off); landing on a shelf when going up in the front
view; the marks on things that overlap, in both drawings and in words; resizing by the corner handle and by the size boxes; Lock
in place; a light hung under the chosen shelf and a plant too close under it; an area to keep clear; Delete and Undo; the top
view showing the chosen thing's level; the list of layouts and the way in from a plant's page; a viewer; a phone with the dark
theme and large text (one view at a time, no sideways scrolling, a first touch chooses and does not move).
Start the mock server with a fresh data folder, then: python3 dev/test/layouts_check.py [http://127.0.0.1:8080]
Screenshots: dev/tmp/shots/layouts-*.png"""
import json, os, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from waits import until
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = BASE.rsplit(':', 1)[0] + ':' + str(int(BASE.rsplit(':', 1)[1]) + 1)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, base=BASE, login=None):
    h = {'Content-Type': 'application/json', 'X-Editor': 'Layout Test'}
    if login: h.update({'Tailscale-User-Login': login, 'Tailscale-User-Name': login.split('@')[0].title()})
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None, headers=h, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def status(m, url, body=None, **kw):
    try: call(m, url, body, **kw); return 200
    except urllib.error.HTTPError as e: return e.code
over = lambda pg: pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
shot = lambda pg, name: pg.screenshot(path=os.path.join(OUT, f'layouts-{name}.png'))

# three plants stand on the Tall Brown Shelf, whose measurements came with batch C7 (4 levels, 23, 13 and 27 in clear, 22 by 11 in)
W = call('GET', '/api/where')
spot = [s for h in W['homes'] for a in h['areas'] for s in a['spots'] if s['name'] == 'Tall Brown Shelf'][0]
codes = [p['code'] for p in call('GET', '/api/plants')[:3]]
for c in codes:
    call('PUT', f'/api/plants/{c}', {'base_version': call('GET', f'/api/plants/{c}')['version'], 'fields': {'spot_id': spot['id']}})

# things for lyFindings: a 40 by 20 by 30 in space, a board 10 in up, and what is named in each case
THING = "(id, kind, x, y, z, w, d, h, more) => Object.assign({ id, sort: id, name: kind + ' ' + id, kind, shape: 'box', x, y, z, w, d, h }, more || {})"
FIND = "(items, clear) => lyFindings({ width_in: 40, depth_in: 20, height_in: 30, clear_in: clear === undefined ? 1 : clear, items }).map(f => f.kind + (f.hard ? '!' : '') + ':' + f.ids.join('+'))"
def find(pg, items, clear=None):
    return pg.evaluate(f"([spec, clear]) => {{ const T = {THING}, F = {FIND}; return F(spec.map(a => T(...a)), clear === null ? undefined : clear); }}", [items, clear])
def it(pg, iid): return pg.evaluate("i => { const t = LY.d.items.find(x => x.id === i); return t ? { x: t.x, y: t.y, z: t.z, w: t.w, d: t.d, h: t.h, locked: t.locked } : null; }", iid)
def saved(lid, iid): return next((x for x in call('GET', f'/api/layouts/{lid}')['items'] if x['id'] == iid), None)
def centre(pg, view, iid, sel='g.ly-it'):
    return pg.evaluate("""([v, i, s]) => { const g = document.querySelector(`svg.ly-svg[data-view="${v}"] ${s}[data-id="${i}"]`); g.scrollIntoView({ block: 'center' });
      const r = (g.querySelector('.ly-handle') && s !== 'g.ly-it' ? g.querySelector('.ly-handle') : g.querySelector('.ly-shape')).getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }""", [view, iid, sel])
def drag(pg, at, dx, dy):
    pg.mouse.move(at[0], at[1]); pg.mouse.down()
    for k in range(1, 9): pg.mouse.move(at[0] + dx * k / 8, at[1] + dy * k / 8)
    pg.wait_for_timeout(80); pg.mouse.up()                      # the drawing follows the pointer on the next frame
focus_id = lambda pg: pg.evaluate("(() => { const g = document.activeElement && document.activeElement.closest ? document.activeElement.closest('g.ly-it') : null; return g ? +g.dataset.id : null; })()")

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 1000})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and 'Failed to load resource' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Layout Test')")
    pg.goto(BASE + '/#/layouts'); pg.wait_for_selector('main h1', timeout=20000)
    check(until(pg, lambda: 'No layouts yet' in pg.inner_text('#app')) and pg.locator('[data-act=lynew]').count() == 1, 'the Layouts page says there are none yet and offers to start one')
    check(pg.locator('#sub-nav a[href="#/layouts"]').count() == 1, 'Layouts is in the Plants row of the top bar')

    # ---- what counts as a problem (the page's own function, asked directly)
    B = [1, 'shelf', 0, 0, 10, 40, 20, 1]                                        # a board 10 in up, its top at 11 in
    check(find(pg, [[1, 'plant', 0, 0, 0, 8, 8, 6], [2, 'plant', 6, 0, 0, 8, 8, 6]]) == ['overlap!:1+2'], 'two things that take up the same room overlap')
    check(find(pg, [[1, 'plant', 0, 0, 0, 8, 8, 6, {'shape': 'round'}], [2, 'plant', 7, 7, 0, 8, 8, 6, {'shape': 'round'}]]) == [], 'two round pots whose corners would cross do not: they are circles from above')
    check(find(pg, [[1, 'other', 0, 0, 0, 8, 8, 6], [2, 'plant', 0, 0, 6, 8, 8, 6]]) == [], 'a plant standing on something does not overlap it')
    check(find(pg, [B, [2, 'plant', 2, 2, 11, 6, 6, 8]]) == [] and find(pg, [B, [2, 'plant', 2, 2, 10.5, 6, 6, 8]]) == ['overlap!:1+2'], 'a pot on a board fits; one sunk into it overlaps')
    check(find(pg, [B, [2, 'plant', 2, 2, 12, 6, 6, 8]]) == ['floating:2'] and find(pg, [[2, 'light', 2, 2, 12, 6, 6, 2]]) == [], 'a pot in the air is marked; a light in the air is not')
    check(find(pg, [[1, 'plant', 36, 0, 0, 8, 8, 6]]) == ['outside!:1'] and find(pg, [[1, 'plant', 0, 0, 26, 8, 8, 6]])[0] == 'outside!:1', 'a thing past the side or the top of the space sticks out')
    check(find(pg, [[1, 'plant', 0, 0, 0, 8, 8, 6], [2, 'plant', 8.5, 0, 0, 8, 8, 6]]) == ['tight:1+2'] and find(pg, [[1, 'plant', 0, 0, 0, 8, 8, 6], [2, 'plant', 8.5, 0, 0, 8, 8, 6]], 0) == []
          and find(pg, [[1, 'shelf', 0, 0, 0, 8, 8, 6], [2, 'other', 8.5, 0, 0, 8, 8, 6]]) == [], 'a plant closer than the room to leave is tight; with no room asked for, or with no plant, nothing is')
    check(find(pg, [B, [2, 'plant', 2, 2, 0, 6, 6, 9.5]]) == ['tight:2+1'], 'a plant with half an inch under the shelf above it is tight')
    check(find(pg, [[1, 'zone', 0, 0, 0, 20, 20, 30], [2, 'plant', 2, 2, 0, 6, 6, 8], [3, 'zone', 12, 5, 0, 20, 10, 30]]) == ['zone:2+1'], 'a thing in an area to keep clear is marked; two such areas may cross')
    check(find(pg, [[1, 'plant', 2, 2, 0, 6, 6, 8], [2, 'light', 2, 2, 10, 6, 6, 2, {'near_in': 5}]]) == ['nearlight:1+2'] and find(pg, [[1, 'plant', 2, 2, 0, 6, 6, 8], [2, 'light', 2, 2, 14, 6, 6, 2, {'near_in': 5}]]) == [],
          'a plant 2 in under a light whose figures start at 5 in is close to it; 6 in under is not')
    check(find(pg, [[1, 'light', 0, 0, 20, 4, 4, 2, {'light_id': 7, 'owned': 1}], [2, 'light', 10, 0, 20, 4, 4, 2, {'light_id': 7, 'owned': 1}]]) == ['count:1+2'], 'two of a light drawn when one is owned is said')
    put = pg.evaluate(f"""() => {{ const T = {THING}, L = {{ width_in: 40, depth_in: 20, height_in: 30, clear_in: 1, grid_in: 1, items: [T(1, 'shelf', 0, 0, 10, 40, 20, 1), T(2, 'plant', 0, 0, 0, 30, 20, 8)] }};
      const a = lyPlace(L, T(3, 'plant', 0, 0, 0, 6, 6, 8), null), b = lyPlace(L, T(4, 'plant', 0, 0, 0, 6, 6, 12), null), c = lyPlace(L, T(5, 'light', 0, 0, 0, 12, 2, 1.5), L.items[0], true);
      return [[a.x, a.y, a.z], [b.x, b.y, b.z], [c.x, c.y, c.z]]; }}""")
    check(put[0][2] == 0 and put[0][0] >= 31 and put[1] == [0, 0, 11] and put[2][2] == 8.5, f'a new thing goes where it fits: beside the big pot on the floor, on the board when it is too tall for under it, a light up under the chosen board ({put})')

    # ---- a shelf's own button on Rooms and spots starts its layout from its measurements
    pg.goto(BASE + '/#/where'); pg.wait_for_selector('#ly-wherelink', timeout=20000)
    link = pg.locator(f'a.ly-wh[href="#/layouts?place={spot["id"]}"]')
    check(link.count() == 1 and link.inner_text() == 'Lay it out' and link.get_attribute('aria-label') == 'Lay it out: Tall Brown Shelf', 'Rooms and spots: the shelf has a "Lay it out" button whose spoken name starts with those words and names the shelf')
    link.click(); pg.wait_for_selector('dialog[open] form[data-lystart]', timeout=20000)
    v = lambda n: pg.input_value(f'dialog[open] [name={n}]')
    check(v('name') == 'Tall Brown Shelf' and [v('width_in'), v('depth_in'), v('height_in')] == ['22', '11', '90'] and '4 levels' in pg.inner_text('#ly-st-items'),
          f'the window is filled in from the shelf: its name, 22 by 11 in, 90 in high, its 4 levels ({v("width_in")} {v("depth_in")} {v("height_in")})')
    shot(pg, '1-start')
    pg.click('dialog[open] button[value=ok]'); pg.wait_for_selector('#ly-draw svg.ly-svg', timeout=20000)
    check(until(pg, lambda: pg.evaluate('LY.d.items.length') == 4) and pg.evaluate("LY.d.items.every(i => i.kind === 'shelf' && i.locked)") and pg.evaluate("LY.d.items.map(i => i.z)") == [0, 23.75, 37.5, 65.25],
          'the layout opens with four locked boards at the heights its measurements give')
    lid = pg.evaluate('LY.d.id')
    check(pg.locator('svg.ly-svg[data-live]').count() == 2 and pg.locator('#ly-v-both').is_checked(), 'a shelf opens with the top view and the front view together')
    check(pg.locator('#ly-tray').is_visible() and pg.locator('#ly-tray .ly-row').count() == 3, 'the three plants that stand there are listed as not drawn yet')
    pg.click('[data-act=lytray][data-all]')
    check(until(pg, lambda: pg.evaluate('LY.d.items.length') == 7), 'Put all 3 on the layout puts them on')
    plants = pg.evaluate("LY.d.items.filter(i => i.kind === 'plant').map(i => i.id)"); a, b, c3 = plants
    check(pg.evaluate("LY.d.items.filter(i => i.kind === 'plant').every(i => { const u = lyUnder(LY.d, i); return u && u !== 'floor' && u.kind === 'shelf'; })") and pg.evaluate('LY.F.length') == 0
          and 'Everything fits' in pg.inner_text('#ly-status'), 'each stands on a level, nothing overlaps, and the page says everything fits')
    check(focus_id(pg) == c3 and pg.evaluate('LY.sel') == c3 and not pg.locator('#ly-tray').is_visible(), 'the last one put on is chosen and has the keyboard; the list of plants not drawn is gone')
    g = pg.locator(f'svg.ly-svg[data-view=front] g.ly-it[data-id="{a}"]')
    check(g.get_attribute('role') == 'button' and 'from the left' in g.get_attribute('aria-label') and 'on Level' in g.get_attribute('aria-label'),
          'a thing on the drawing is a control with words: what it is, its size, where it is and what it stands on')
    stops = pg.evaluate("[...document.querySelectorAll('svg.ly-svg[data-live]')].map(s => [...s.querySelectorAll('g.ly-it[tabindex=\"0\"]')].map(g => +g.dataset.id))")
    check(stops == [[c3], [c3]], f'each drawing is one stop for the Tab key, on the chosen thing ({stops})')
    pg.keyboard.press('PageDown')
    first = pg.evaluate('LY.d.items[0].id')
    check(until(pg, lambda: pg.evaluate('LY.sel') == first and focus_id(pg) == first) and 'Level 1' in pg.inner_text('#ly-say'), 'Page Down goes to the next thing (after the last, the first), chooses it and says where it is')
    pg.keyboard.press('PageUp')
    check(until(pg, lambda: pg.evaluate('LY.sel') == c3 and focus_id(pg) == c3), 'Page Up goes back to the one before')
    pg.wait_for_timeout(500); shot(pg, '2-shelf')

    # ---- the arrow keys (the plant alone on level 2, so that nothing is in its way)
    clean = lambda: until(pg, lambda: pg.evaluate('LY.F.length') == 0, 4000)
    pick = lambda i: (pg.click(f'.ly-list .ly-row[data-id="{i}"] [data-act=lypick]'), until(pg, lambda: pg.evaluate('LY.sel') == i and focus_id(pg) == i))[1]
    check(pick(c3) and pg.evaluate("document.activeElement.closest('svg').dataset.view") == 'top', 'Choose beside a thing in the list chooses it and puts the keyboard on it in the drawing')
    x0 = it(pg, c3)['x']
    pg.keyboard.press('ArrowRight')
    check(until(pg, lambda: it(pg, c3)['x'] == x0 + 1) and 'from the left' in pg.inner_text('#ly-say') and pg.evaluate('LY.sel') == c3, 'Right arrow moves the thing one square and says where it is')
    pg.keyboard.press('Shift+ArrowRight'); pg.keyboard.press('ArrowDown')
    check(until(pg, lambda: (it(pg, c3)['x'], it(pg, c3)['y']) == (x0 + 6, 1)), 'Shift with an arrow moves five squares; Down arrow in the top view brings it toward the front')
    check(until(pg, lambda: (saved(lid, c3)['x'], saved(lid, c3)['y']) == (x0 + 6, 1)) and focus_id(pg) == c3, 'the moves are saved once the keys pause, and the thing keeps the keyboard')
    check('moved' in pg.inner_text('#ly-undo') and clean(), 'Undo says what it would take back')

    # ---- typing a place; things that overlap are marked in both drawings and said
    pick(a); tb = it(pg, b); was = it(pg, a); undos = pg.evaluate('LY.undo.length')
    for k, val in (('x', tb['x'] - 1), ('y', 1)): pg.fill(f'#ly-f-{k}', str(val)); pg.press(f'#ly-f-{k}', 'Tab')
    check(until(pg, lambda: pg.evaluate('LY.F.map(f => f.kind)') == ['overlap']) and (it(pg, a)['x'], it(pg, a)['y']) == (tb['x'] - 1, 1), 'typed nearly onto the place of another plant, the two overlap')
    check(all(pg.locator(f'svg.ly-svg[data-view={vw}] g.ly-it.is-hard').count() == 2 for vw in ('top', 'front')) and pg.locator('#ly-find-body .ly-f-hard').count() == 1 and 'Overlap' in pg.inner_text('#ly-find-body')
          and '1 problem' in pg.inner_text('#ly-status') and pg.locator('.ly-list .ly-row.is-hard').count() == 2, 'both are marked in both drawings, in the list, in "To look at" and at the top of the page')
    check(pg.evaluate("getComputedStyle(document.querySelector('svg.ly-svg[data-view=top] g.ly-it.is-hard .ly-hatch-h')).display") != 'none'
          and pg.evaluate("getComputedStyle(document.querySelector('svg.ly-svg[data-view=top] g.ly-lab.is-hard .ly-flag')).display") != 'none', 'the mark is bars across the thing and a cross, not only a colour')
    shot(pg, '3-overlap')
    typed = pg.evaluate('LY.undo.length') - undos
    for k in range(typed): pg.click('#ly-undo'); until(pg, lambda: pg.evaluate('LY.undo.length') == undos + typed - k - 1)
    check(typed == 2 and clean() and it(pg, a) == was and until(pg, lambda: (saved(lid, a)['x'], saved(lid, a)['y']) == (was['x'], was['y'])), 'Undo, once for each box typed in, takes the typing back, here and on the server')

    # ---- up and down in the front view: it lands on a shelf
    pg.evaluate("i => lyFocusIt(i, 'front')", a); z0 = it(pg, a)['z']
    pg.keyboard.press('ArrowDown')
    low = it(pg, a)['z']
    for _ in range(40):
        pg.keyboard.press('ArrowUp')
        if it(pg, a)['z'] in (24.5, 38.25, 66) and it(pg, a)['z'] > z0: break
    check(low <= z0 and it(pg, a)['z'] in (24.5, 38.25, 66), f'Up arrow in the front view raises it and it stops on the next shelf exactly ({z0} to {it(pg, a)["z"]})')
    pg.keyboard.press('Control+z')
    check(until(pg, lambda: it(pg, a)['z'] == z0) and clean(), 'Ctrl+Z on the drawing takes the move back')

    # ---- dragging: snapped to the grid, then freely
    pick(c3); S = pg.evaluate('LY.Sv.top'); xa = it(pg, c3)['x']
    drag(pg, centre(pg, 'top', c3), 3.4 * S, 0)
    check(until(pg, lambda: it(pg, c3)['x'] == xa + 3) and until(pg, lambda: saved(lid, c3)['x'] == xa + 3), 'dragged 3.4 squares to the right, it goes 3: it snaps to the grid, and is saved')
    check(focus_id(pg) == c3, 'the thing dragged keeps the keyboard')
    pg.click('#ly-more'); pg.wait_for_selector('#ly-snap')
    pg.uncheck('#ly-snap')
    check(until(pg, lambda: pg.evaluate('LY.d.snap') is False) and 'snapping off' in pg.inner_text('#ly-more'), 'Snap to the grid can be turned off, and its button says so')
    drag(pg, centre(pg, 'top', c3), -1.5 * S, 0)
    check(until(pg, lambda: abs(it(pg, c3)['x'] - (xa + 1.5)) < 0.2 and it(pg, c3)['x'] != round(it(pg, c3)['x'])), f'with snapping off it stops where it is let go ({it(pg, c3)["x"]})')
    pg.check('#ly-snap'); until(pg, lambda: pg.evaluate('LY.d.snap') is True)
    pg.select_option('#ly-step', '2')
    check(until(pg, lambda: pg.evaluate('LY.d.grid_in') == 2), 'the squares can be made 2 in')
    pick(c3); pg.keyboard.press('ArrowRight')
    check(until(pg, lambda: it(pg, c3)['x'] % 2 == 0), 'and the next arrow press takes it to a 2 in line')
    pg.uncheck('#ly-gridshow'); none = pg.locator('svg.ly-svg[data-live] .ly-gridfill').count()
    pg.check('#ly-gridshow')
    check(none == 0 and pg.locator('svg.ly-svg[data-live] .ly-gridfill').count() == 4, 'Show the grid hides and shows the lines')
    pg.select_option('#ly-step', '1'); until(pg, lambda: pg.evaluate('LY.d.grid_in') == 1)

    # ---- size: the corner handle, and the boxes; a plant too tall for its level
    w0 = it(pg, c3)['w']
    drag(pg, centre(pg, 'top', c3, '.ly-selmark'), 2.2 * S, 2.2 * S)
    check(until(pg, lambda: it(pg, c3)['w'] == w0 + 2 and it(pg, c3)['d'] == w0 + 2), 'dragging the corner handle makes a round pot 2 in wider, still round')
    pg.fill('#ly-f-h', '20'); pg.press('#ly-f-h', 'Tab')
    check(until(pg, lambda: it(pg, c3)['h'] == 20 and saved(lid, c3)['h'] == 20) and 'resized' in pg.inner_text('#ly-undo'), 'typing a height resizes it')
    check(until(pg, lambda: pg.evaluate('LY.F.map(f => f.kind)') == ['overlap']) and 'Level 3' in pg.inner_text('#ly-p-find') and pg.locator(f'svg.ly-svg[data-view=front] g.ly-it[data-id="{c3}"].is-hard').count() == 1,
          'a plant 20 in tall where 13 in is clear overlaps the shelf above it, and is told so beside its boxes')
    pg.fill('#ly-f-h', '12.5'); pg.press('#ly-f-h', 'Tab')
    check(until(pg, lambda: pg.evaluate('LY.F.map(f => f.kind)') == ['tight']) and 'between the top of' in pg.inner_text('#ly-p-find') and pg.locator(f'svg.ly-svg[data-view=front] g.ly-it[data-id="{c3}"].is-soft').count() == 1,
          'at 12.5 in, with half an inch above it, it is "Tight"')
    pg.fill('#ly-f-h', '10'); pg.press('#ly-f-h', 'Tab')
    check(clean() and until(pg, lambda: saved(lid, c3)['h'] == 10), 'at 10 in it fits')

    # ---- Lock in place
    pg.check('#ly-f-locked'); until(pg, lambda: it(pg, c3)['locked'])
    xl = it(pg, c3)['x']; pick(c3); pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(200)
    check(it(pg, c3)['x'] == xl and 'is locked in place' in pg.inner_text('#toasts') and pg.locator('#ly-f-x').is_disabled(), 'a locked thing does not move, says why, and its boxes are off')
    pg.uncheck('#ly-f-locked'); until(pg, lambda: not it(pg, c3)['locked'])

    # ---- a light under the chosen shelf, and a plant too close under it
    lv2 = pg.evaluate("LY.d.items.find(i => i.name === 'Level 2').id")
    check(pick(lv2), 'a shelf level is chosen from the list')
    pg.click('#ly-add'); pg.wait_for_selector('dialog[open] form[data-lyadd]')
    check([x.strip() for x in pg.locator('dialog[open] fieldset.ly-kind .opts span').all_inner_texts()] == ['Plant', 'Grow light', 'Shelf or furniture', 'Something else', 'Area to keep clear'], 'the Add window asks what it is, plant first')
    pg.check('dialog[open] input[name=kind][value=light]', force=True)
    t8 = pg.evaluate("LY.d.lights.find(x => /T8/.test(x.name)).id")
    pg.select_option('dialog[open] select[name=light]', str(t8)); shot(pg, '4-add')
    pg.click('dialog[open] button[value=ok]')
    check(until(pg, lambda: pg.evaluate("LY.d.items.some(i => i.kind === 'light')")), 'a light is added from your lights')
    li = pg.evaluate("(() => { const l = LY.d.items.find(i => i.kind === 'light'), s = LY.d.items.find(i => i.name === 'Level 2'); return { id: l.id, top: l.z + l.h, under: s.z, w: l.w, near: l.near_in }; })()")
    check(abs(li['top'] - li['under']) < 0.01 and li['w'] == 24 and 'under Level 2' in pg.locator(f'svg.ly-svg[data-view=front] g.ly-it[data-id="{li["id"]}"]').get_attribute('aria-label'),
          'the 2 ft strip hangs up under the chosen shelf, at its length from its mounting')
    check(pg.evaluate('LY.F.map(f => f.kind)') == ['outside'] and 'sticks out past the right side by 2 in' in pg.inner_text('#ly-find-body') and pg.locator(f'svg.ly-svg[data-view=front] g.ly-it[data-id="{li["id"]}"].is-hard').count() == 1,
          'a 24 in strip on a 22 in shelf is said to stick out, by how much and on which side')
    pg.fill('#ly-f-w', '22'); pg.press('#ly-f-w', 'Tab')
    check(clean() and until(pg, lambda: saved(lid, li['id'])['w'] == 22), 'typing its real length, 22 in, makes it fit')
    lv1 = pg.evaluate("LY.d.items.find(i => i.name.startsWith('Level 1')).id")
    pg.click(f'.ly-list .ly-row[data-id="{a}"] [data-act=lypick]'); until(pg, lambda: pg.evaluate('LY.sel') == a)
    for k, val in (('x', '0'), ('y', '0')): pg.fill(f'#ly-f-{k}', val); pg.press(f'#ly-f-{k}', 'Tab')
    pg.select_option('#ly-f-on', str(lv1)); until(pg, lambda: it(pg, a)['z'] == 0.75)
    pg.fill('#ly-f-h', '19.5'); pg.press('#ly-f-h', 'Tab')
    check(until(pg, lambda: any(f == 'nearlight' for f in pg.evaluate('LY.F.map(f => f.kind)'))) and pg.locator(f'svg.ly-svg[data-view=front] g.ly-it[data-id="{a}"].is-soft').count() == 1
          and 'Close to a light' in pg.inner_text('#ly-find-body') and 'warning' in pg.inner_text('#ly-status'), f'a plant whose top is 2 in under the strip is "Close to a light" (its figures start at {li["near"]} in)')
    check('is 2 in above its top' in pg.inner_text('#ly-p-light') and 'figures cover 9 in to' in pg.inner_text('#ly-p-light'), "the plant's own boxes say which light is over it, how far up, and how far that light's figures go")
    shot(pg, '5-light')
    pg.fill('#ly-f-h', '12'); pg.press('#ly-f-h', 'Tab')
    check(clean() and until(pg, lambda: 'is 9.5 in above its top' in pg.inner_text('#ly-p-light')), 'at 12 in tall, with 9.5 in under the strip, it is not')
    pg.click('#ly-marks summary'); pg.click('#ly-keyhelp summary')
    check(pg.locator('#ly-marks li').count() == 5 and pg.locator('#ly-marks li').first.is_visible() and 'Page Down' in pg.inner_text('#ly-keyhelp'), 'What the marks mean and Keys for the drawing open lists, in words')
    pg.click('#ly-marks summary'); pg.click('#ly-keyhelp summary')

    # ---- an area to keep clear, something else, a copy, a quarter turn
    pg.click('#ly-add'); pg.wait_for_selector('dialog[open] form[data-lyadd]')
    pg.check('dialog[open] input[name=kind][value=zone]', force=True)
    for k, val in (('zw', '10'), ('zd', '11'), ('zh', '20')): pg.fill(f'dialog[open] input[name={k}]', val)
    pg.click('dialog[open] button[value=ok]')
    check(until(pg, lambda: pg.evaluate("LY.d.items.some(i => i.kind === 'zone')")) and pg.evaluate("(() => { const z = LY.d.items.find(i => i.kind === 'zone'); return LY.sel === z.id && z.z === 0 && z.w === 10 && z.h === 20; })()"),
          'an area to keep clear is added at the size typed, on the floor, and is the chosen thing')
    zid = pg.evaluate("LY.d.items.find(i => i.kind === 'zone').id")
    for k, val in (('x', '0'), ('y', '0')): pg.fill(f'#ly-f-{k}', val); pg.press(f'#ly-f-{k}', 'Tab')
    check(until(pg, lambda: pg.evaluate(f"LY.F.some(f => f.kind === 'zone' && f.ids[0] === {a} && f.ids[1] === {zid})")) and pg.locator(f'svg.ly-svg[data-view=front] g.ly-it[data-id="{a}"].is-soft').count() == 1
          and pg.locator(f'svg.ly-svg[data-view=front] g.ly-it[data-id="{zid}"].is-soft').count() == 0 and 'In an area to keep clear' in pg.inner_text('#ly-find-body') and pg.evaluate('LY.F.every(f => !f.hard)'),
          'moved over a plant, the plant is marked "In an area to keep clear"; the area itself is not, and nothing counts as overlapping')
    put = pg.evaluate("(() => { const L = LY.d, t = lyPlace(L, { kind: 'plant', name: 'New', shape: 'round', w: 4, d: 4, h: 4, x: 0, y: 0, z: 0 }, LY.d.items.find(i => i.name.startsWith('Level 1')), false); return lyFindings({ ...L, items: L.items.concat([{ ...t, id: -9, sort: 99 }]) }).filter(f => f.ids.includes(-9)).length; })()")
    check(put == 0, 'a new thing is not put in an area to keep clear')
    pick(zid); pg.keyboard.press('Delete')
    check(until(pg, lambda: not pg.evaluate("LY.d.items.some(i => i.kind === 'zone')")) and saved(lid, zid) is None, 'Delete takes the chosen thing off the layout')
    pg.click('#ly-undo')
    check(until(pg, lambda: pg.evaluate("LY.d.items.some(i => i.kind === 'zone')")), 'and Undo puts it back')
    pg.click(f'.ly-list .ly-row[data-id="{pg.evaluate("LY.d.items.find(i => i.kind === 'zone').id")}"] [data-act=lypick]'); pg.wait_for_selector('#ly-rm'); pg.click('#ly-rm')
    until(pg, lambda: not pg.evaluate("LY.d.items.some(i => i.kind === 'zone')"))
    pg.click('#ly-add'); pg.wait_for_selector('dialog[open] form[data-lyadd]')
    pg.check('dialog[open] input[name=kind][value=other]', force=True); pg.fill('dialog[open] input[name=othername]', 'Humidifier')
    for k, val in (('ow', '10'), ('od', '4'), ('oh', '6')): pg.fill(f'dialog[open] input[name={k}]', val)
    pg.click('dialog[open] button[value=ok]')
    check(until(pg, lambda: pg.evaluate("LY.d.items.some(i => i.name === 'Humidifier')")), 'something else is added by name and size')
    hid = pg.evaluate("LY.d.items.find(i => i.name === 'Humidifier').id")
    pg.click('#ly-turn')
    check(until(pg, lambda: (it(pg, hid)['w'], it(pg, hid)['d']) == (4, 10)) and clean(), 'Turn a quarter swaps its width and depth, and keeps it inside the space')
    pg.click('#ly-copy')
    check(until(pg, lambda: pg.evaluate("LY.d.items.filter(i => i.name.startsWith('Humidifier')).length") == 2) and pg.evaluate('LY.F.filter(f => f.hard).length') == 0
          and pg.evaluate("(() => { const [p, q] = LY.d.items.filter(i => i.name.startsWith('Humidifier')); return p.z === q.z && (p.x !== q.x || p.y !== q.y) && q.name === 'Humidifier (copy)' && LY.sel === q.id; })()"),
          'Make a copy puts a second one beside the first, on what the first stands on, and chooses it')

    # ---- the top view follows the chosen thing's level
    pg.click(f'.ly-list .ly-row[data-id="{a}"] [data-act=lypick]'); until(pg, lambda: pg.evaluate('LY.sel') == a)
    dim = pg.locator('svg.ly-svg[data-view=top] g.ly-it.is-dim').count()
    check(dim >= 3 and 'Showing Level 1' in pg.inner_text('.ly-fig[data-view=top] figcaption') and pg.locator(f'svg.ly-svg[data-view=top] g.ly-it[data-id="{a}"].is-dim').count() == 0,
          f'with a plant on level 1 chosen, the top view shows that level and the others are faint ({dim} faint)')
    pg.select_option('#ly-level', '0')
    check(pg.locator('svg.ly-svg[data-view=top] g.ly-it.is-dim').count() == 0 and pg.locator('svg.ly-svg[data-view=top].ly-through').count() == 1, '"Every level" shows them all, the boards see-through')
    pg.select_option('#ly-level', 'auto'); shot(pg, '6-level')

    # ---- size and name
    pg.click('#ly-space'); pg.wait_for_selector('dialog[open] form[data-lyspace]')
    pg.fill('dialog[open] input[name=name]', 'Tall brown shelf, winter'); pg.fill('dialog[open] input[name=height_in]', '96')
    pg.click('dialog[open] button[value=ok]')
    check(until(pg, lambda: pg.evaluate('LY.d.height_in') == 96 and pg.inner_text('#ly-title') == 'Tall brown shelf, winter'), 'Size and name changes the space and its title')

    # ---- a change that cannot be saved is said, and the page goes back to what is saved
    pick(a); xs = it(pg, a)['x']
    pg.route('**/api/layouts/items/*', lambda r: r.abort() if r.request.method == 'PUT' else r.continue_())
    pg.keyboard.press('ArrowRight')
    check(until(pg, lambda: 'Cannot reach the plant server' in pg.inner_text('#toasts')) and until(pg, lambda: it(pg, a)['x'] == xs) and saved(lid, a)['x'] == xs and pg.locator('.ly-stale').count() == 0,
          'a move that could not be saved is said, and the thing goes back to where it is saved')
    pg.unroute('**/api/layouts/items/*')
    # the page's own request function is made to fail for layouts (a saved copy from the service worker would answer a stopped request)
    pg.evaluate("(() => { window.lyRealApi = api; api = async (m, u, ...more) => { if (u.startsWith('/api/layouts')) throw new Error('Cannot reach the plant server. Check that the container is running.'); return lyRealApi(m, u, ...more); }; })()")
    pick(a); pg.keyboard.press('ArrowRight')
    check(until(pg, lambda: pg.locator('.ly-stale').count() == 1) and pg.locator('#ly-add').count() == 0 and pg.locator('#ly-f-x').is_disabled(),
          'if the layout cannot be read again either, the page says its changes are not being saved, and takes no more')
    pg.evaluate('(() => { api = lyRealApi; })()')
    pg.click('[data-act=lyreload]')
    check(until(pg, lambda: pg.locator('.ly-stale').count() == 0 and pg.locator('#ly-add').count() == 1) and it(pg, a)['x'] == xs, 'Read it again brings the saved layout back, and it can be changed again')
    errs[:] = [e for e in errs if 'net::ERR_FAILED' not in e and 'Failed to fetch' not in e]      # the two requests this part stopped on purpose

    # ---- the list, and the ways in
    pg.goto(BASE + '/#/layouts'); pg.wait_for_selector('.ly-cards .ly-card', timeout=20000)
    card = pg.locator('.ly-card').first
    check(pg.locator('.ly-card').count() == 1 and card.locator('svg.ly-svg').count() == 1 and 'things on it' in card.inner_text() and 'Everything fits' in card.inner_text(), 'the list shows the layout as a card with a small drawing and how it stands')
    shot(pg, '7-list')
    pg.goto(BASE + '/#/where'); pg.wait_for_selector('#ly-wherelink', timeout=20000)
    link = pg.locator(f'a.ly-wh[href="#/layouts?place={spot["id"]}"]')
    check(link.inner_text() == 'Open its layout' and link.get_attribute('aria-label') == 'Open its layout: Tall Brown Shelf', 'on Rooms and spots the shelf now says "Open its layout"')
    link.click()
    check(until(pg, lambda: pg.url.endswith(f'#/layouts/{lid}')) and pg.locator('#ly-draw svg.ly-svg').count() >= 1, 'and that opens it')
    pcode = pg.evaluate("i => LY.d.items.find(x => x.id === i).plant", a)
    pg.goto(BASE + f'/#/plant/{pcode}'); pg.wait_for_selector('#ly-plant a', timeout=20000)
    check('Tall brown shelf, winter' in pg.inner_text('#ly-plant'), "the plant's own page says which layout it is drawn on")
    pg.click('#ly-plant a'); pg.wait_for_selector('#ly-draw svg.ly-svg', timeout=20000)
    check(until(pg, lambda: pg.evaluate('LY.sel') == a) and pg.locator('#ly-f-x').count() == 1, 'and its link opens the layout with that plant chosen')
    check(call('GET', f'/api/plants/{pcode}')['spot_id'] == spot['id'], 'moving a plant on a layout did not change where its page says it is')
    br.close()

# ---- a viewer looks but cannot change; a phone
call('PUT', '/api/people', {'login': 'viewer@example.com', 'role': 'viewer'}, base=TS, login='owner@example.com')
L = call('GET', f'/api/layouts/{lid}'); plant = [i for i in L['items'] if i['kind'] == 'plant'][0]
check(status('PUT', f"/api/layouts/items/{plant['id']}", {'x': 3}, base=TS, login='viewer@example.com') == 403 and status('POST', '/api/layouts', {'name': 'V', 'width_in': 10, 'depth_in': 10, 'height_in': 10}, base=TS, login='viewer@example.com') == 403
      and status('DELETE', f'/api/layouts/{lid}', base=TS, login='viewer@example.com') == 403, 'a viewer cannot move a thing, start a layout or remove one')
with sync_playwright() as p:
    br = p.chromium.launch()
    v = br.new_context(viewport={'width': 1280, 'height': 900}, extra_http_headers={'Tailscale-User-Login': 'viewer@example.com', 'Tailscale-User-Name': 'Vee'}).new_page()
    v.on('pageerror', lambda e: errs.append(str(e)))
    v.goto(TS + f'/#/layouts/{lid}'); v.wait_for_selector('#ly-draw svg.ly-svg', timeout=20000)
    vis = lambda sel: v.locator(sel).count() and v.locator(sel).first.is_visible()
    check(not vis('#ly-add') and not vis('#ly-undo') and not vis('#ly-space') and not vis('.ly-handle') and v.locator('#ly-snap').is_disabled(), 'a viewer sees the drawing without Add, Undo, Size and name or a handle')
    v.evaluate("i => lyFocusIt(i, 'front')", plant['id']); v.keyboard.press('ArrowRight'); v.wait_for_timeout(300)
    check(it(v, plant['id'])['x'] == plant['x'] and v.evaluate('LY.sel') is None, 'and the arrow keys move nothing')
    v.keyboard.press('Enter')
    check(until(v, lambda: v.evaluate('LY.sel') == plant['id']) and v.locator('#ly-f-x').is_disabled(), 'but a thing can be chosen, to read its place and size')
    ph = br.new_context(viewport={'width': 390, 'height': 844}, device_scale_factor=2, has_touch=True).new_page()
    ph.on('pageerror', lambda e: errs.append(str(e)))
    ph.add_init_script("localStorage.setItem('plantdb.editor','Phone');localStorage.setItem('plantdb.display', JSON.stringify({theme:'dark', size:'190'}))")
    ph.goto(BASE + f'/#/layouts/{lid}'); ph.wait_for_selector('#ly-draw svg.ly-svg', timeout=20000); ph.wait_for_timeout(500)
    check(ph.locator('svg.ly-svg[data-live]').count() == 1 and ph.locator('input[name=lyview]').count() == 2 and over(ph) <= 0, f'phone, dark, the largest text: one view at a time, and no sideways scrolling ({over(ph)}px)')
    ph.click('#ly-more'); ph.wait_for_selector('#ly-level'); ph.wait_for_timeout(200)
    check(over(ph) <= 0, f'nor with Grid and settings open ({over(ph)}px)')
    ph.click('#ly-more')
    ph.check('#ly-v-front', force=True); ph.wait_for_selector('svg.ly-svg[data-view=front]')
    at = centre(ph, 'front', plant['id']); was = it(ph, plant['id'])
    check(ph.evaluate("i => getComputedStyle(document.querySelector(`svg.ly-svg g.ly-it[data-id='${i}']`)).touchAction", plant['id']) == 'auto', 'a thing not chosen lets a finger scroll the page')
    ph.touchscreen.tap(at[0], at[1])
    check(until(ph, lambda: ph.evaluate('LY.sel') == plant['id']) and it(ph, plant['id']) == was
          and ph.evaluate("i => getComputedStyle(document.querySelector(`svg.ly-svg g.ly-it[data-id='${i}']`)).touchAction", plant['id']) == 'none', 'a first touch chooses it without moving it; chosen, it drags under a finger')
    # at the largest text a name must go under its picture, not break inside a word: walk each name's letters and count the lines that start mid-word
    broken = ph.evaluate("""() => { let n = 0;
      document.querySelectorAll('.ly-row-txt strong, .ly-who strong, #ly-title').forEach(el => { const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let node;
        while ((node = tw.nextNode())) { const t = node.textContent; let last = null;
          for (let i = 0; i < t.length; i++) { const r = document.createRange(); r.setStart(node, i); r.setEnd(node, i + 1); const b = r.getClientRects()[0]; if (!b) continue;
            if (last !== null && b.top > last + 2 && /[A-Za-z]/.test(t[i - 1]) && /[A-Za-z]/.test(t[i])) n++;
            last = b.top; } } });
      return n; }""")
    check(broken == 0 and over(ph) <= 0, f'with a plant chosen, no name is broken inside a word ({broken}), and still nothing scrolls sideways')
    ph.evaluate("document.getElementById('ly-draw').scrollIntoView()"); ph.wait_for_timeout(200); shot(ph, '8-phone')
    ph.click('#ly-add'); ph.wait_for_selector('dialog[open] form[data-lyadd]'); ph.wait_for_timeout(300)
    check(ph.evaluate("(() => { const d = document.querySelector('dialog[open]'); return d.scrollWidth - d.clientWidth; })()") <= 0, 'the Add window fits the phone')
    shot(ph, '9-phone-add')
    br.close()

# ---- removing the layout leaves the plants and the shelf as they were
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 1000})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Layout Test')")
    pg.goto(BASE + '/#/layouts'); pg.wait_for_selector('.ly-card [data-act=lydel]', timeout=20000)
    pg.click('.ly-card [data-act=lydel]'); pg.wait_for_selector('dialog[open] button[value=ok]'); pg.click('dialog[open] button[value=ok]')
    check(until(pg, lambda: 'No layouts yet' in pg.inner_text('#app')) and call('GET', '/api/layouts')['layouts'] == [] and len([s for h in call('GET', '/api/where')['homes'] for a in h['areas'] for s in a['spots'] if s['id'] == spot['id'] and s['plants'] == 3]) == 1,
          'Remove on a card, once confirmed, removes the layout; the shelf and its three plants stay')
    br.close()
print(f'\n{len(fails)} FAIL, {len(errs)} page errors' + (': ' + '; '.join(errs[:4]) if errs else ''))
sys.exit(1 if fails or errs else 0)
