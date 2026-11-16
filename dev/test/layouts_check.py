"""Checks Layouts (prototype, proto/layouts; plantdb/layouts.py, js/layouts.js): what counts as overlapping, sticking out, tight,
in the air, close to a light or in an area to keep clear (lyFindings, asked directly); a layout started from a shelf's own
button on Rooms and spots, with its levels drawn from its measurements; the plants that are there put on it, each on a level
where it fits; a thing chosen and moved by the arrow keys (said aloud, saved once the keys pause, the keyboard kept), by typing,
by "Stands on", and by dragging (snapped to the grid, or freely with snapping off); landing on a shelf when going up in the front
view; the marks on things that overlap, in both drawings and in words; resizing by the corner handle and by the size boxes; Lock
in place; a light hung under the chosen shelf and a plant too close under it; an area to keep clear; Delete and Undo; the top
view showing the chosen thing's level; the list of layouts and the way in from a plant's page; a viewer; a phone with the dark
theme and large text (one view at a time, no sideways scrolling, a first touch chooses and does not move).
What reaches the record, and the light (November 15, 2026): the light a plant gets where it is drawn (lyLight, asked directly:
straight under, off to the side, a board between, a lamp that stands, hours and brightness, two lights), the same number as Grow
lights gives for that light at that distance, "Too dim" as a mark and in words, a light's hours changed; a plant's height typed
on a layout saved on its page and taken back by Undo, and "Save this height on its page"; where the drawing puts a plant in the
record (lyRecTo, asked directly), "Move it in the record" for one plant and for all of them, and Undo.
Later on November 15: a shelf drawn as a block with its levels (asked directly: standing on a level, too tall for it, tight under
the next, in the air inside it, a light through the open side and shut out by a board; lyLand, where a moved thing comes to
rest); on a room's layout a plant dropped onto a shelf stands on it, "Stands on" lists every shelf and each level and moves the
plant there, and a plant dragged off goes to the floor; Redo with its button and Ctrl+Y, for a move, a thing taken off and put
back, and emptied by a new change; a bit dim and a bit bright as marks, and the light's sign on the drawing and in the list.
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
def it(pg, iid): return pg.evaluate("i => { const t = LY.d.items.find(x => x.id === i); return t ? { x: t.x, y: t.y, z: t.z, w: t.w, d: t.d, h: t.h, locked: t.locked, size_locked: t.size_locked } : null; }", iid)
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

    # ---- the light a plant gets where it is drawn (lyLight, asked directly). The light's figures: 400 at 6 in, 100 at 12 in, 25 at 24 in
    # (so a quarter at twice the distance); it is on 10 hours a day, when 100 gives 3.6 mol/m2 a day. The plant's top is 8 in up.
    LIT = {'pts': [[6, 400, None], [12, 100, None], [24, 25, None]], 'hours': 10, 'dim_pct': 100, 'near_in': 4, 'far_in': 30}
    def lit(items):
        return pg.evaluate(f"""spec => {{ const T = {THING}, L = {{ width_in: 60, depth_in: 40, height_in: 60, clear_in: 0, items: spec.map(a => T(...a)) }}, F = lyFindings(L), x = F.light.get(1);
          return {{ dli: x.dli, verdict: x.verdict, reached: x.reached, on: x.on.map(o => o.li.id), shut: x.shut.map(o => [o.li.id, o.by.id]), nofig: x.nofig.map(o => o.li.id), any: F.light.any,
                    marks: F.filter(f => lyIsLv(f.kind)).map(f => f.kind + ':' + f.ids.join('+')) }}; }}""", items)
    P = lambda need=None, h=8: [1, 'plant', 10, 10, 0, 6, 6, h, {'need': need}]
    over12 = [2, 'light', 10, 10, 20, 6, 6, 2, LIT]                              # its underside 12 in above the plant's top
    x = lit([P(), over12])
    check((x['dli'], x['verdict'], x['reached'], x['on'], x['marks']) == (3.6, 'unknown', True, [2], []), f'a plant 12 in straight under the light gets what its figures give at 12 in: 3.6 ({x})')
    x = [lit([P(n), over12]) for n in ({'lo': 6, 'hi': 12}, {'lo': 4, 'hi': 8}, {'lo': 3, 'hi': 5}, {'lo': 1, 'hi': 3}, {'lo': 1, 'hi': 2})]
    check([(v['verdict'], v['marks']) for v in x] == [('too_dim', ['toodim:1']), ('dim', ['dim:1']), ('good', []), ('bright', ['bright:1']), ('too_bright', ['toobright:1'])],
          'against what the plant needs it is too dim, a bit dim, good, a bit bright or too bright, as Grow lights says it; each but good is a mark of its own kind')
    x = lit([P({'lo': 6, 'hi': 12}), [2, 'light', 25, 10, 20, 6, 6, 2, LIT]])
    check((x['dli'], x['reached'], x['verdict'], x['marks']) == (0.9, False, 'none', []), f'12 in to the side as well as 12 in below, it gets half of what that distance gives (0.9); under 1, the light does not reach it and it is not called dim ({x})')
    x = lit([P(), over12, [3, 'shelf', 0, 0, 14, 40, 20, 1]]); y = lit([P(), over12, [3, 'shelf', 30, 0, 14, 20, 20, 1]])
    check((x['dli'], x['on'], x['shut']) == (0, [], [[2, 3]]) and y['dli'] == 3.6, f'a board between the light and the plant shuts the light out; a board beside them does not ({x})')
    x = [lit([P(), [2, 'light', 10, 10, 20, 6, 6, 2, {**LIT, **m}]])['dli'] for m in ({'hours': 5}, {'dim_pct': 50}, {'hours': 0})]
    check(x == [1.8, 1.8, 0], f'half the hours or half the brightness gives half; switched off gives none ({x})')
    x = lit([P(), over12, [4, 'light', 10, 10, 32, 6, 6, 2, LIT]])
    check((x['dli'], sorted(x['on'])) == (4.5, [2, 4]), f'two lights over it add up: 3.6 and, from 24 in, 0.9 ({x})')
    x = lit([P(), [2, 'light', 20, 10, 0, 6, 6, 20, LIT]]); y = lit([P(h=22), over12])
    check((x['dli'], x['on']) == (2.0, [2]) and y['on'] == [], f'a lamp that stands lights from its top (7 in to the side, its top 12 in above the plant: 2.0); a plant taller than a light gets none from it ({x})')
    x = lit([P(), [2, 'light', 10, 10, 20, 6, 6, 2, {'hours': 12, 'dim_pct': 100}]])
    check((x['dli'], x['nofig'], x['any'], x['marks']) == (0, [2], False, []), 'a light with no figures is not counted, and nothing is said about light')
    check(lit([P(h=18), [2, 'light', 10, 10, 20, 6, 6, 2, LIT]])['dli'] == 32.4, 'closer than its figures go, it is counted at the nearest distance they can be trusted for (4 in: 900)')
    # ---- a shelf drawn as one block that has its levels: boards 0.75 in thick with their tops at 0.75, 20.5 and 40 in; 19 and 18.75 in of room
    LV = {'board_in': 0.75, 'levels': [{'n': 1, 'name': 'Level 1 (bottom)', 'z': 0.75, 'room': 19}, {'n': 2, 'name': 'Level 2', 'z': 20.5, 'room': 18.75}, {'n': 3, 'name': 'Level 3 (top)', 'z': 40, 'room': None}]}
    B = [1, 'shelf', 0, 0, 0, 30, 12, 40, LV]
    words = lambda items, clear=None: pg.evaluate(f"([spec, clear]) => {{ const T = {THING}; return lyFindings({{ width_in: 60, depth_in: 40, height_in: 60, clear_in: clear === null ? 0 : clear, items: spec.map(a => T(...a)) }}).map(f => f.kind + ': ' + f.text); }}", [items, clear])
    check(words([B, [2, 'plant', 2, 2, 20.5, 6, 6, 10]]) == [] and words([B, [2, 'plant', 2, 2, 40, 6, 6, 10]]) == [] and len(words([[1, 'shelf', 0, 0, 0, 30, 12, 40], [2, 'plant', 2, 2, 20.5, 6, 6, 10]])) == 1,
          "a plant on a level of a shelf that has levels, or on its top, is in nothing's way; in a block with no levels it would overlap")
    x = words([B, [2, 'plant', 2, 2, 0.75, 6, 6, 22]])
    check(len(x) == 1 and x[0].startswith('overlap: ') and 'is too tall for Level 1 (bottom) of shelf 1 (1) by 3 in' in x[0], f'a plant taller than the room over its level is said to be too tall for that level, and by how much ({x})')
    x = words([B, [2, 'plant', 2, 2, 0.75, 6, 6, 18]], 2); y = words([B, [2, 'plant', 2, 2, 5, 6, 6, 8]])
    check(x == ['tight: There is 1 in between the top of plant 2 (2) and Level 2 of shelf 1 (1).'] and y == ['floating: plant 2 (2) has nothing under it: it is 4.3 in above shelf 1 (1).'], f'with 1 in under the next level it is tight; inside the shelf and on no level it has nothing under it ({x} {y})')
    x = [lit([[1, 'plant', 10, 8, 20.5, 6, 6, 8], [2, 'light', 10, 8, 41, 6, 6, 2, LIT], [3, 'shelf', 5, 5, 0, 30, 12, 40, LV]])['shut'],          # the top board is between them
         lit([[1, 'plant', 28, 8, 20.5, 6, 6, 8], [2, 'light', 36, 8, 0, 6, 6, 39, LIT], [3, 'shelf', 5, 5, 0, 30, 12, 40, LV]])]                  # a lamp standing beside the shelf, its top under the top board
    check(x[0] == [[2, 3]] and x[1]['on'] == [2] and x[1]['shut'] == [], f'a light over the shelf is shut out by its boards; a lamp beside it lights a plant on a level through the open side ({x})')
    land = pg.evaluate(f"""() => {{ const T = {THING}, LV = {json.dumps(LV)}, L = {{ width_in: 80, depth_in: 40, height_in: 90, clear_in: 0, items: [T(1, 'shelf', 0, 0, 0, 30, 12, 40, LV), T(2, 'plant', 50, 20, 0, 6, 6, 10), T(3, 'plant', 2, 2, 0.75, 8, 8, 10),
        T(4, 'other', 40, 0, 0, 20, 10, 15), T(5, 'light', 50, 20, 60, 6, 6, 2)] }}, p = L.items[1];
      const go = (it, x, y, more) => {{ const was = {{ ...it }}; Object.assign(it, more || {{}}, {{ x, y }}); lyLand(L, it, was); return [it.z, lyWhere(L, it).split(', ').pop()]; }};
      return [go(p, 20, 3), go(p, 22, 3), go(p, 2, 2), go(p, 45, 2), go(p, 60, 30), go(p, 20, 3, {{ h: 30 }}), go(p, 60, 30, {{ h: 10 }}), go(L.items[4], 10, 3),
              lyStandOpts(L, p).map(o => o.w), lyPutOn(L, p, lySurf(L.items[0])[1]), lyPutOn(L, {{ ...p, x: 20, y: 3 }}, lySurf(L.items[0])[2]).z]; }}""")
    check(land[0] == [0.75, 'on Level 1 (bottom) of shelf 1 (1)'] and land[1] == [0.75, 'on Level 1 (bottom) of shelf 1 (1)'], f'a plant moved over a shelf with levels lands on its lowest level, and stays on that level as it moves along it ({land[:2]})')
    check(land[2][0] == 0.75 and land[3] == [15, 'on other 4 (4)'] and land[4] == [0, 'on the floor'], f'moved from the shelf onto another thing it stands on that, and moved off everything it is on the floor ({land[2:5]})')
    check(land[5] == [40, 'on Level 3 (top) of shelf 1 (1)'] and land[7][0] == 60, f'too tall for the levels it lands on the top; a light hanging in the air keeps its height when moved ({land[5]}, {land[7]})')
    check(land[8] == ['The floor', 'Level 1 (bottom) of shelf 1 (1)', 'Level 2 of shelf 1 (1)', 'Level 3 (top) of shelf 1 (1)'] and (land[9]['x'], land[9]['y'], land[9]['z']) == (0, 0, 20.5) and land[10] == 40,
          f'"Stands on" offers the floor and each level of each shelf; choosing a level of a shelf it is not over puts it in the first free place there, and one it is over only changes its height ({land[8:]})')
    lower = pg.evaluate(f"""() => {{ const T = {THING}, LV = {json.dumps(LV)}, L = {{ width_in: 80, depth_in: 40, height_in: 90, clear_in: 0, items: [T(1, 'shelf', 0, 0, 0, 30, 12, 40, LV), T(2, 'plant', 50, 20, 0, 6, 6, 10), T(3, 'plant', 2, 2, 0.75, 8, 8, 10)] }}, p = L.items[1], was = {{ ...p }};
      p.x = 3; p.y = 3; lyLand(L, p, was); return p.z; }}""")
    check(lower == 20.5, f'where another plant stands on the lowest level, it lands on the next one up ({lower})')

    rec = pg.evaluate(f"""() => {{ const T = {THING}, L = {{ pid: -5, place: 'Room', spot_id: null, items: [T(1, 'shelf', 0, 0, 0, 20, 10, 30, {{ spot_id: 7, place: 'Room, Shelf' }}), T(2, 'plant', 5, 2, 30, 6, 6, 8, {{ plant: 'P-1', rec: 3 }}),
        T(3, 'plant', 40, 2, 0, 6, 6, 8, {{ plant: 'P-2', rec: -5 }}), T(4, 'plant', 40, 20, 0, 6, 6, 8, {{ plant: 'P-3', rec: 7, gone: true }}), T(5, 'shelf', 30, 30, 0, 20, 10, 30)] }};
      return [lyRecTo(L, L.items[1]), lyRecTo(L, L.items[2]), lyRecTo(L, L.items[3]), lyRecList(L).map(x => x.it.id), lyRecTo({{ ...L, pid: null }}, L.items[1]), lyRecTo({{ ...L, spot_id: 9, pid: 9, place: 'Room, Other' }}, L.items[2])]; }}""")
    check(rec == [{'pid': 7, 'label': 'Room, Shelf'}, {'pid': -5, 'label': 'Room'}, None, [2], None, {'pid': 9, 'label': 'Room, Other'}],
          f"on a room's layout a plant on one of the record's shelves is at that shelf, one on the floor is in the room; on a shelf's own layout every plant is at that shelf; a space of your own is nowhere in the record ({rec})")
    put = pg.evaluate(f"""() => {{ const T = {THING}, L = {{ width_in: 40, depth_in: 20, height_in: 30, clear_in: 1, grid_in: 1, items: [T(1, 'shelf', 0, 0, 10, 40, 20, 1), T(2, 'plant', 0, 0, 0, 30, 20, 8)] }};
      const a = lyPlace(L, T(3, 'plant', 0, 0, 0, 6, 6, 8), null), b = lyPlace(L, T(4, 'plant', 0, 0, 0, 6, 6, 12), null), c = lyPlace(L, T(5, 'light', 0, 0, 0, 12, 2, 1.5), L.items[0], true);
      return [[a.x, a.y, a.z], [b.x, b.y, b.z], [c.x, c.y, c.z]]; }}""")
    check(put[0][2] == 0 and put[0][0] >= 31 and put[1] == [0, 0, 11] and put[2][2] == 8.5, f'a new thing goes where it fits: beside the big pot on the floor, on the board when it is too tall for under it, a light up under the chosen board ({put})')

    # ---- what a thing carries when it is moved, and which walls a thing is at (asked directly)
    car = pg.evaluate(f"""() => {{ const T = {THING}, lv = [{{ n: 1, name: 'Level 1 (bottom)', z: 0.75, room: 20 }}, {{ n: 2, name: 'Level 2', z: 21.5, room: 30 }}, {{ n: 3, name: 'Level 3 (top)', z: 60, room: null }}];
      const L = {{ width_in: 100, depth_in: 80, height_in: 90, clear_in: 1, grid_in: 1, items: [T(1, 'shelf', 10, 0, 0, 30, 12, 60, {{ levels: lv, board_in: 0.75 }}),
        T(2, 'plant', 12, 2, 0.75, 6, 6, 8), T(3, 'plant', 20, 2, 21.5, 6, 6, 8), T(4, 'light', 10, 4, 19.25, 30, 2, 1.5),          // on its level 1, on its level 2, a strip up under level 2's board
        T(5, 'other', 60, 44, 0, 20, 20, 30), T(6, 'other', 62, 46, 30, 8, 8, 10), T(7, 'plant', 63, 47, 40, 4, 4, 6),               // a table, a box on it, a plant on the box
        T(8, 'plant', 72, 50, 30, 6, 6, 8, {{ locked: true }}), T(9, 'plant', 2, 30, 0, 6, 6, 10), T(10, 'zone', 58, 42, 0, 30, 30, 40), T(11, 'other', 0, 0, 0, 8, 8, 20), T(12, 'plant', 40, 30, 0, 10, 10, 12)] }};
      const ids = a => a.map(t => t.id).sort((x, y) => x - y), I = n => L.items[n - 1];
      const rs = lyCarryStart(L, I(1)), was = {{ ...I(1) }}; I(1).x += 5; I(1).z += 2; lyCarryMove(I(1), was, rs); const moved = [2, 3, 4].map(n => [I(n).x, I(n).z]); Object.assign(I(1), was); rs.forEach(r => Object.assign(r.it, r.was));
      const st = lyStandOpts(L, I(5)).map(o => o.w);
      return {{ shelf: ids(lyRiders(L, I(1))), table: ids(lyRiders(L, I(5))), plant: ids(lyRiders(L, I(9))), zone: ids(lyRiders(L, I(10))), moved, onbox: st.some(w => w.startsWith('other 6')),
        walls: [1, 3, 4, 5, 7, 9, 11, 12].map(n => lyWallsOf(L, I(n)).join('+')), back: [...lyWallSet(L, 'back')].sort((x, y) => x - y), mid: [...lyWallSet(L, 'mid')], all: lyWallSet(L, 'all'),
        across: ['back', 'right', 'front', 'left'].map(f => [lyAc(L, I(1), f), lyAw(I(1), f), lyAcrossW(L, f)]), near: ['back', 'right', 'front', 'left'].map(f => lyNear(L, I(1), f)) }}; }}""")
    check(car['shelf'] == [2, 3, 4] and car['table'] == [6, 7] and car['plant'] == [] and car['zone'] == [] and car['moved'] == [[17, 2.75], [25, 23.5], [15, 21.25]] and not car['onbox'],
          f"a shelf carries what stands on its levels and the strip under one of its boards; a table carries the box on it and the plant on the box, and not a thing locked in place; each goes as far as the shelf goes; \"Stands on\" does not offer what the thing itself carries ({car['shelf']} {car['table']} {car['moved']})")
    check(car['walls'] == ['back+left', 'back+left', 'back+left', 'right+front', 'right+front', 'left', 'back+left', 'mid'] and car['back'] == [1, 2, 3, 4, 11] and car['mid'] == [12] and car['all'] is None,
          f"a thing is at each wall it is within 2 ft of; what stands on a thing or hangs under it is at that thing's walls; a thing more than 2 ft from every wall is at none, and is in the view of the things away from the walls ({car['walls']} {car['back']} {car['mid']})")
    check(car['across'] == [[10, 30, 100], [0, 12, 80], [60, 30, 100], [68, 12, 80]] and car['near'] == [12, 90, 80, 40],
          f"looking at each wall, a thing is drawn from your left as you face it: the back wall as the top view has it, the right wall from back to front, the front wall from right to left, the left wall from front to back ({car['across']})")

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
    check(pg.locator('svg.ly-svg[data-live]').count() == 2 and pg.locator('#ly-v-both').is_checked() and pg.locator('#ly-wall').count() == 0 and pg.locator('.ly-lvb').count() == 0,
          "a shelf opens with the top view and the front view together; its front view is the whole shelf (no wall to choose), and with no light drawn nothing carries a light sign")
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
    # (the two overlap as soon as the first box is taken; the second box waits for the first one's save. So this waits for the place
    #  and the mark together: waiting for the mark alone, and then looking at the place, failed whenever that save was slow.)
    check(until(pg, lambda: (it(pg, a)['x'], it(pg, a)['y']) == (tb['x'] - 1, 1) and pg.evaluate('LY.F.map(f => f.kind)') == ['overlap']), f'typed nearly onto the place of another plant, the two overlap ({pg.evaluate("LY.F.map(f => f.kind + " " + f.text)")} {it(pg, a)} {tb})')
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

    # ---- the two locks: its place, and apart from it its size (Ethan, November 16, 2026)
    check(pg.locator('fieldset.ly-locks legend').inner_text() == 'Locks' and pg.locator('#ly-f-locked').is_visible() and pg.locator('#ly-f-size_locked').is_visible(), 'the chosen thing has two locks, Lock its place and Lock its size')
    pg.check('#ly-f-locked'); until(pg, lambda: it(pg, c3)['locked'] and saved(lid, c3)['locked'])
    xl = it(pg, c3)['x']; pick(c3); pg.keyboard.press('ArrowRight'); pg.wait_for_timeout(200)
    check(it(pg, c3)['x'] == xl and 'is locked in place' in pg.inner_text('#toasts') and pg.locator('#ly-f-x').is_disabled() and not pg.locator('#ly-f-h').is_disabled()
          and pg.locator(f'svg.ly-svg[data-view=front] .ly-selmark[data-id="{c3}"] .ly-handle').count() == 1 and not saved(lid, c3)['size_locked'],
          'with its place locked it does not move and its place boxes are off, and its size can still be changed (its size boxes and the corner handle)')
    pg.uncheck('#ly-f-locked'); until(pg, lambda: not it(pg, c3)['locked'])
    pg.check('#ly-f-size_locked'); until(pg, lambda: it(pg, c3)['size_locked'] and saved(lid, c3)['size_locked'])
    sz = (it(pg, c3)['w'], it(pg, c3)['h'])
    check(pg.locator('#ly-f-h').is_disabled() and pg.locator('#ly-f-w').is_disabled() and not pg.locator('#ly-f-x').is_disabled() and pg.locator('.ly-handle').count() == 0 and pg.locator('#ly-turn').count() == 0
          and not saved(lid, c3)['locked'] and pg.inner_text('label:has(#ly-f-h)').startswith('Height (in), locked') and 'locked' not in pg.inner_text('label:has(#ly-f-x)') and 'Its size is locked' in pg.locator(f'svg.ly-svg[data-view=front] g.ly-it[data-id="{c3}"]').get_attribute('aria-label'),
          'with its size locked its size boxes are off, there is no corner handle and no Turn a quarter, its place boxes still work, and the drawing says so')
    x0 = it(pg, c3)['x']; pick(c3); pg.keyboard.press('ArrowRight')
    check(until(pg, lambda: it(pg, c3)['x'] == x0 + 1) and (it(pg, c3)['w'], it(pg, c3)['h']) == sz, 'and it still moves, keeping its size')
    a0 = centre(pg, 'front', c3); drag(pg, a0, -2 * pg.evaluate('LY.Sv.front'), 0)
    check(until(pg, lambda: it(pg, c3)['x'] == x0 - 1) and (it(pg, c3)['w'], it(pg, c3)['h']) == sz, f'dragged by its middle it moves, and its size stays ({it(pg, c3)})')
    pg.click('#ly-undo'); until(pg, lambda: it(pg, c3)['x'] == x0 + 1); pg.click('#ly-undo'); until(pg, lambda: it(pg, c3)['x'] == x0)
    pg.uncheck('#ly-f-size_locked'); until(pg, lambda: not it(pg, c3)['size_locked'] and not saved(lid, c3)['size_locked'])
    check(pg.locator(f'.ly-selmark[data-id="{c3}"] .ly-handle').count() >= 1 and not pg.locator('#ly-f-h').is_disabled(), 'unlocked, the corner handle and the size boxes are back')

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
    clean = lambda: until(pg, lambda: pg.evaluate("LY.F.filter(f => !lyIsLv(f.kind)).length") == 0, 4000)      # from here on a plant under the strip is also "Too dim": the strip is a weak one
    check(pg.evaluate("LY.F.map(f => f.kind).filter(k => !lyIsLv(k))") == ['outside'] and 'sticks out past the right side by 2 in' in pg.inner_text('#ly-find-body') and pg.locator(f'svg.ly-svg[data-view=front] g.ly-it[data-id="{li["id"]}"].is-hard').count() == 1,
          'a 24 in strip on a 22 in shelf is said to stick out, by how much and on which side')
    pg.fill('#ly-f-w', '22'); pg.press('#ly-f-w', 'Tab')
    check(clean() and until(pg, lambda: saved(lid, li['id'])['w'] == 22), 'typing its real length, 22 in, makes it fit')
    ad = it(pg, a)['d']; pg.fill('#ly-f-y', str(ad / 2 - 1)); pg.press('#ly-f-y', 'Tab'); until(pg, lambda: saved(lid, li['id'])['y'] == ad / 2 - 1)      # over the middle of where the plant will stand, so the plant is straight under it
    lv1 = pg.evaluate("LY.d.items.find(i => i.name.startsWith('Level 1')).id")
    pg.click(f'.ly-list .ly-row[data-id="{a}"] [data-act=lypick]'); until(pg, lambda: pg.evaluate('LY.sel') == a)
    for k, val in (('x', '0'), ('y', '0')): pg.fill(f'#ly-f-{k}', val); pg.press(f'#ly-f-{k}', 'Tab')
    pg.select_option('#ly-f-on', f'{lv1}:0'); until(pg, lambda: it(pg, a)['z'] == 0.75)
    acode = pg.evaluate("i => LY.d.items.find(x => x.id === i).plant", a); h0 = call('GET', f'/api/plants/{acode}')['height_in']; v0 = call('GET', f'/api/plants/{acode}')['version']
    pg.fill('#ly-f-h', '19.5'); pg.press('#ly-f-h', 'Tab')
    check(until(pg, lambda: call('GET', f'/api/plants/{acode}')['height_in'] == 19.5) and call('GET', f'/api/plants/{acode}')['version'] == v0 + 1 and 'here and on its page' in pg.inner_text('#ly-say')
          and 'Saved on its page: 19.5 in tall' in pg.inner_text('#ly-p-tall') and 'Its height is the one on its page' in pg.inner_text('#ly-p-tall'), "a plant's height typed on the layout is saved on its page, and the page says so under the box and aloud")
    check(until(pg, lambda: any(f == 'nearlight' for f in pg.evaluate('LY.F.map(f => f.kind)'))) and pg.locator(f'svg.ly-svg[data-view=front] g.ly-it[data-id="{a}"].is-soft').count() == 1
          and 'Close to a light' in pg.inner_text('#ly-find-body') and 'warning' in pg.inner_text('#ly-status'), f'a plant whose top is 2 in under the strip is "Close to a light" (its figures start at {li["near"]} in)')
    words = pg.inner_text('#ly-p-light')
    check('Light here: about' in words and 'mol/m² a day' in words and '2 in above its top, 12 hours a day' in words and 'Closer than its figures go' in words and 'Daylight is not counted' in words,
          "the plant's own boxes say how much light it gets here, from which light, how far above its top and for how many hours")
    check(pg.locator('#ly-p-light .lv-too_dim').count() == 1 and 'Too dim' in pg.inner_text('#ly-p-light .lv') and 'It needs' in words and 'Too dim' in pg.inner_text('#ly-find-body')
          and pg.locator(f'.ly-list .ly-row[data-id="{a}"] .lv-too_dim').count() == 1 and 'too dim' in pg.inner_text(f'.ly-list .ly-row[data-id="{a}"]'),
          'under the weak strip it is "Too dim", in the words and the sign Grow lights uses, beside its boxes, in "To look at" and in the list')
    check(pg.locator(f'svg.ly-svg[data-view=front] g.ly-lab[data-id="{a}"] .ly-lvb-too_dim').count() == 1 and pg.locator(f'svg.ly-svg[data-view=front] g.ly-lab[data-id="{a}"] .ly-lvb').text_content().strip() == '▼▼'
          and pg.locator(f'svg.ly-svg[data-view=front] g.ly-lab[data-id="{c3}"] .ly-lvb-none').text_content().strip() == '–' and 'No light reaches it' in pg.inner_text(f'.ly-list .ly-row[data-id="{c3}"] .ly-lv-none'),
          "on the drawing the plant carries the light's sign beside its mark; a plant the strip does not reach carries a grey dash, and its line in the list says no light reaches it")
    shot(pg, '5-light')
    pg.fill('#ly-f-h', '12'); pg.press('#ly-f-h', 'Tab')
    check(clean() and until(pg, lambda: '9.5 in above its top' in pg.inner_text('#ly-p-light') and 'Closer than' not in pg.inner_text('#ly-p-light')), 'at 12 in tall, with 9.5 in under the strip, it is not too close')
    glow = lambda hours: call('GET', f'/api/lights/preview?light={t8}&distance=9.5&hours={hours}&dim=100&units=1')['dli']
    mine = lambda: pg.evaluate("i => LY.F.light.get(i).dli", a)
    check(mine() == glow(12) and mine() > 0, f'the light it gets straight under the strip is the number Grow lights gives for that strip at 9.5 in on 12 hours ({mine()})')
    check(pg.evaluate("i => { const x = LY.F.light.get(i); return !x.reached && x.dli === 0; }", c3) and 'none drawn here reaches it' in pg.inner_text(f'.ly-list .ly-row[data-id="{c3}"]'),
          'a plant on the level above the strip gets none of its light, and its line in the list says so')
    pick(li['id'])
    check(pg.locator('#ly-f-hours').input_value() == '12' and pg.locator('#ly-f-dim_pct option').count() >= 2 and 'It lights' in pg.inner_text('#ly-p-light') and 'underside' in pg.inner_text('#ly-p-light'),
          'a light has its hours a day and its brightness to set, and says which plants it lights')
    pg.fill('#ly-f-hours', '16'); pg.press('#ly-f-hours', 'Tab')
    check(until(pg, lambda: saved(lid, li['id'])['hours'] == 16) and mine() == glow(16) and 'hours changed' in pg.inner_text('#ly-undo'), f'on 16 hours the plant under it gets what Grow lights gives for 16 ({mine()}), and the hours are saved')
    pg.click('#ly-undo')
    check(until(pg, lambda: saved(lid, li['id'])['hours'] == 12) and mine() == glow(12), 'Undo puts its hours back')
    # the height saved on the page is taken back by Undo; a page with no height is given the one drawn by its own button
    pick(a); pg.fill('#ly-f-h', '14'); pg.press('#ly-f-h', 'Tab')
    until(pg, lambda: call('GET', f'/api/plants/{acode}')['height_in'] == 14)
    pg.click('#ly-undo')
    check(until(pg, lambda: call('GET', f'/api/plants/{acode}')['height_in'] == 12 and it(pg, a)['h'] == 12), 'Undo of a height puts it back on the layout and on the page')
    bcode = pg.evaluate("i => LY.d.items.find(x => x.id === i).plant", b); pick(b)
    check(call('GET', f'/api/plants/{bcode}')['height_in'] is None and 'Its page has no height yet' in pg.inner_text('#ly-p-tall') and pg.locator('#ly-tallsave').count() == 1, 'a plant with no height on its page says so')
    pg.click('#ly-tallsave')
    check(until(pg, lambda: call('GET', f'/api/plants/{bcode}')['height_in'] == it(pg, b)['h']) and until(pg, lambda: pg.locator('#ly-tallsave').count() == 0) and 'height saved' in pg.inner_text('#ly-undo'),
          '"Save this height on its page" puts the height drawn on its page')
    pg.click('#ly-undo')
    check(until(pg, lambda: call('GET', f'/api/plants/{bcode}')['height_in'] is None) and until(pg, lambda: pg.locator('#ly-tallsave').count() == 1), 'and Undo takes it off the page again')
    pg.click('#ly-marks summary'); pg.click('#ly-keyhelp summary')
    check(pg.locator('#ly-marks > ul > li').count() == 7 and 'A sign for its light' in pg.inner_text('#ly-marks') and 'A grey dash' in pg.inner_text('#ly-marks') and 'A heavy edge' in pg.inner_text('#ly-marks') and pg.locator('#ly-marks li').first.is_visible() and 'Too dim' in pg.inner_text('#ly-marks') and 'Page Down' in pg.inner_text('#ly-keyhelp') and 'Ctrl+Y' in pg.inner_text('#ly-keyhelp'), 'What the marks mean and Keys for the drawing open lists, in words')
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

    # ---- the record: two plants are drawn here that the record has somewhere else
    check(not pg.locator('#ly-rec').is_visible() and 'In your record it is here' in pg.inner_text('#ly-p-rec'), 'with every plant drawn where the record has it, nothing is said about moving, and the plant says it is here')
    away = [p for p in call('GET', '/api/plants') if p['code'] not in codes and p['spot_id'] != spot['id']][:2]; was_at = {p['code']: (p['area_id'], p['spot_id']) for p in away}
    call('POST', f'/api/layouts/{lid}/items', {'items': [{'kind': 'plant', 'plant': p['code'], 'shape': 'round', 'w': 4, 'd': 4, 'h': 6, 'x': 1 + 5 * n, 'y': 6, 'z': 66} for n, p in enumerate(away)]})
    pg.evaluate('lyReload()'); until(pg, lambda: pg.locator('#ly-rec .ly-row').count() == 2)
    ids = pg.evaluate("codes => codes.map(c => LY.d.items.find(i => i.plant === c).id)", [p['code'] for p in away])
    check(pg.locator('#ly-rec').is_visible() and 'These 2 plants are drawn here' in pg.inner_text('#ly-rec-body') and 'On this layout: ' in pg.inner_text('#ly-rec-body') and 'Tall Brown Shelf' in pg.inner_text('#ly-rec-body')
          and pg.locator('#ly-recall').inner_text() == 'Move both in the record', 'two plants drawn here that the record has elsewhere are listed, with where the record has each and where the layout does')
    btn = pg.locator(f'#ly-rec [data-act=lyrec][data-id="{ids[0]}"]')
    check(btn.inner_text() == 'Move it in the record' and btn.get_attribute('aria-label') == f"Move it in the record: {away[0]['common_name']}", "each has its own button, named for the plant")
    place = lambda code: (lambda p: (p['area_id'], p['spot_id']))(call('GET', f'/api/plants/{code}'))
    btn.click()
    check(until(pg, lambda: place(away[0]['code'])[1] == spot['id']) and until(pg, lambda: pg.locator('#ly-rec .ly-row').count() == 1) and 'Moved in your record' in pg.inner_text('#toasts')
          and 'moved in the record' in pg.inner_text('#ly-undo') and place(away[1]['code']) == was_at[away[1]['code']], "Move it in the record puts that plant on this shelf in the record, and only that one")
    note = call('GET', f"/api/plants/{away[0]['code']}/history")['audit'][0]['note']
    check(note.startswith('Moved to ') and 'Tall Brown Shelf' in note and 'layout' in note, f"its page's History says it was moved from the layout ({note})")
    pick(ids[0])
    check('In your record it is here' in pg.inner_text('#ly-p-rec') and pg.locator('#ly-recone').count() == 0, 'chosen, it now says the record has it here')
    pg.click('#ly-undo')
    check(until(pg, lambda: place(away[0]['code']) == was_at[away[0]['code']]) and until(pg, lambda: pg.locator('#ly-rec .ly-row').count() == 2) and pg.locator('#ly-recone').count() == 1, 'Undo puts it back where the record had it')
    pg.click('#ly-recall'); pg.wait_for_selector('dialog[open] button[value=ok]')
    check('Move both plants in your record?' in pg.inner_text('dialog[open]') and 'Tall Brown Shelf' in pg.inner_text('dialog[open]'), 'moving them all asks first, and says where to')
    pg.click('dialog[open] button[value=ok]')
    check(until(pg, lambda: all(place(p['code'])[1] == spot['id'] for p in away)) and until(pg, lambda: not pg.locator('#ly-rec').is_visible()) and pg.evaluate("document.activeElement.id") == 'ly-undo', 'once confirmed both are on the shelf in the record, and the list is gone')
    pg.click('#ly-undo')
    check(until(pg, lambda: all(place(p['code']) == was_at[p['code']] for p in away)) and until(pg, lambda: pg.locator('#ly-rec .ly-row').count() == 2), 'one Undo puts both back')
    shot(pg, '6b-record')

    # ---- a room's layout: a plant is dropped onto a shelf, moved between its levels and to another shelf, and dragged off again
    area = next(a for h in W['homes'] for a in h['areas'] if any(x['id'] == spot['id'] for x in a['spots']))
    start = next(p for p in call('GET', '/api/layouts')['places'] if p['pid'] == -area['id'])['start']
    rid = call('POST', '/api/layouts', {'name': 'Room for the check', 'place': -area['id'], **{k: start[k] for k in ('width_in', 'depth_in', 'height_in', 'items')}})['id']
    call('POST', f'/api/layouts/{rid}/items', {'kind': 'plant', 'plant': away[0]['code'], 'shape': 'round', 'w': 6, 'd': 6, 'h': 10, 'x': 60, 'y': 70, 'z': 0})
    R = call('GET', f'/api/layouts/{rid}'); block = next(i for i in R['items'] if i['spot_id'] == spot['id']); table = next(i for i in R['items'] if i['kind'] == 'shelf' and not i['levels']); rp = next(i for i in R['items'] if i['kind'] == 'plant')['id']
    pg.goto(f'{BASE}/#/layouts/{rid}'); until(pg, lambda: pg.evaluate('!!LY && LY.d.id') == rid and pg.locator('svg.ly-svg[data-view=top] g.ly-it').count() >= 3)
    check([v['z'] for v in block['levels']] == [0.75, 24.5, 38.25, 66] and pg.locator(f'svg.ly-svg[data-view=top] g.ly-it.ly-open[data-id="{block["id"]}"]').count() == 1, 'in a room the Tall Brown Shelf is one block that knows its four levels')
    pick(rp)
    opts = pg.evaluate("[...document.querySelectorAll('#ly-f-on option')].map(o => o.textContent)")
    check(opts[0] == 'The floor' and f"Level 2 of {block['name']} ({block['sort']})" in opts and f"{table['name']} ({table['sort']})" in opts and len(opts) >= 6, f'"Stands on" lists the floor, every shelf in the room and each level of a shelf that has them ({len(opts)} places)')
    mid = lambda i: pg.evaluate("i => { const r = document.querySelector(`svg.ly-svg[data-view=top] g.ly-it[data-id='${i}'] .ly-shape`).getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }", i)
    pg.evaluate("(() => { const r = document.querySelector('svg.ly-svg[data-view=top]').getBoundingClientRect(); window.scrollBy(0, r.top - 190); })()"); pg.wait_for_timeout(150)
    a0, b0 = mid(rp), mid(block['id'])
    check(190 < b0[1] < a0[1] < pg.viewport_size['height'] - 10, f'(the shelf and the plant are both on screen for the drag: {b0}, {a0})')
    drag(pg, a0, b0[0] - a0[0], b0[1] - a0[1])
    check(until(pg, lambda: it(pg, rp)['z'] == 0.75) and until(pg, lambda: saved(rid, rp)['z'] == 0.75) and pg.evaluate('LY.F.length') == 0 and 'on Level 1 (bottom) of Tall Brown Shelf' in pg.inner_text('#ly-say')
          and pg.evaluate("document.querySelector('#ly-f-on').selectedOptions[0].textContent").startswith('Level 1 (bottom) of Tall Brown Shelf'),
          'dropped onto the shelf in the top view, the plant stands on its lowest level, nothing overlaps, and "Stands on" says so')
    check('Tall Brown Shelf' in pg.inner_text('#ly-p-rec') and pg.locator('#ly-recone').count() == 1, 'and the layout now has it at that shelf, to move it there in the record')
    was = it(pg, rp)
    pg.select_option('#ly-f-on', f"{block['id']}:3")
    check(until(pg, lambda: it(pg, rp)['z'] == 38.25) and (it(pg, rp)['x'], it(pg, rp)['y']) == (was['x'], was['y']) and until(pg, lambda: saved(rid, rp)['z'] == 38.25), 'choosing Level 3 under "Stands on" lifts it to that level, where it is')
    pg.fill('#ly-f-h', '30'); pg.press('#ly-f-h', 'Tab')
    check(until(pg, lambda: 'is too tall for Level 3 of Tall Brown Shelf' in pg.inner_text('#ly-find-body') and 'by 3 in' in pg.inner_text('#ly-find-body')), 'made 30 in tall where the level has 27 in, it is said to be too tall for that level by 3 in')
    pg.click('#ly-undo'); until(pg, lambda: it(pg, rp)['h'] == 10 and pg.evaluate('LY.F.length') == 0)
    pg.click('#ly-v-both', force=True); until(pg, lambda: pg.locator('svg.ly-svg[data-view=front]').count() == 1)
    check(pg.locator(f'svg.ly-svg[data-view=front] g.ly-it[data-id="{block["id"]}"] .ly-board').count() == 4, 'from the front the shelf shows its four boards, open between them')
    pg.click('#ly-v-top', force=True); until(pg, lambda: pg.locator('svg.ly-svg[data-view=front]').count() == 0)
    pick(rp); pg.select_option('#ly-f-on', f"{table['id']}:0")
    check(until(pg, lambda: it(pg, rp)['z'] == table['h']) and table['x'] <= it(pg, rp)['x'] <= table['x'] + table['w'] and table['y'] <= it(pg, rp)['y'] <= table['y'] + table['d'], 'choosing another shelf under "Stands on" moves the plant onto it')
    a0 = centre(pg, 'top', rp); drag(pg, a0, 0, 110 if table['y'] < 60 else -110)
    check(until(pg, lambda: it(pg, rp)['z'] == 0) and 'on the floor' in pg.inner_text('#ly-say'), 'dragged off the shelf, it goes down to the floor')
    # Redo: its button and Ctrl+Y do again what Undo took back, and a new change empties it
    check(pg.locator('#ly-redo').is_disabled() and pg.locator('#ly-redo').inner_text() == 'Redo', 'with nothing taken back, Redo has nothing to do')
    pg.click('#ly-undo')
    check(until(pg, lambda: it(pg, rp)['z'] == table['h']) and pg.locator('#ly-redo').inner_text() == 'Redo: moved' and pg.locator('#ly-redo').get_attribute('aria-label').startswith('Redo: moved. '), 'after Undo, Redo says what it would do again')
    pg.click('#ly-redo')
    check(until(pg, lambda: it(pg, rp)['z'] == 0 and saved(rid, rp)['z'] == 0) and pg.locator('#ly-redo').is_disabled() and 'Done again' in pg.inner_text('#toasts'), 'Redo puts the plant back on the floor, in the record of the layout too')
    pg.click('#ly-undo'); until(pg, lambda: it(pg, rp)['z'] == table['h']); pg.click('#ly-undo'); until(pg, lambda: it(pg, rp)['z'] == 38.25)
    pg.locator('#ly-status').click(); pg.keyboard.press('Control+y')
    check(until(pg, lambda: it(pg, rp)['z'] == table['h']), 'Ctrl+Y does the same from anywhere on the page')
    pg.keyboard.press('Control+z'); until(pg, lambda: it(pg, rp)['z'] == 38.25)
    pg.fill('#ly-f-h', '9'); pg.press('#ly-f-h', 'Tab'); pg.locator('#ly-f-h').focus(); pg.keyboard.press('Control+y')
    check(until(pg, lambda: it(pg, rp)['h'] == 9) and pg.locator('#ly-redo').is_disabled() and it(pg, rp)['z'] == 38.25, 'a new change empties Redo, and Ctrl+Y in a box being typed in is left to the box')
    focus = lambda: pg.locator(f'svg.ly-svg[data-view=top] g.ly-it[data-id="{pg.evaluate("LY.sel")}"]').focus()
    focus(); pg.keyboard.press('Delete'); until(pg, lambda: pg.evaluate("LY.d.items.filter(i => i.kind === 'plant').length") == 0)
    pg.keyboard.press('Control+z'); until(pg, lambda: pg.evaluate("LY.d.items.filter(i => i.kind === 'plant').length") == 1)
    rp2 = pg.evaluate("LY.d.items.find(i => i.kind === 'plant').id")
    pg.keyboard.press('Control+y')
    check(rp2 != rp and until(pg, lambda: pg.evaluate("LY.d.items.filter(i => i.kind === 'plant').length") == 0) and len([i for i in call('GET', f'/api/layouts/{rid}')['items'] if i['kind'] == 'plant']) == 0, 'a thing taken off, put back by Undo, is taken off again by Redo')
    pg.keyboard.press('Control+z'); until(pg, lambda: pg.evaluate("LY.d.items.filter(i => i.kind === 'plant').length") == 1)
    rp3 = pg.evaluate("LY.d.items.find(i => i.kind === 'plant').id"); pg.keyboard.press('Control+z')
    check(until(pg, lambda: it(pg, rp3)['h'] == 10), 'and an older change is still taken back on the thing that was put back')
    # ---- a shelf carries what stands on it: by the arrow keys, by dragging, and back with Undo
    sb, sp = it(pg, block['id']), it(pg, rp3)
    pick(block['id']); pg.locator(f'svg.ly-svg[data-view=top] g.ly-it[data-id="{block["id"]}"]').focus(); pg.keyboard.press('ArrowRight'); pg.keyboard.press('ArrowDown')
    both = lambda dx, dy: (it(pg, block['id'])['x'], it(pg, block['id'])['y'], it(pg, rp3)['x'], it(pg, rp3)['y'], it(pg, rp3)['z']) == (sb['x'] + dx, sb['y'] + dy, sp['x'] + dx, sp['y'] + dy, sp['z'])
    check(until(pg, lambda: both(1, 1)) and until(pg, lambda: (saved(rid, rp3)['x'], saved(rid, block['id'])['x']) == (sp['x'] + 1, sb['x'] + 1)) and 'moved with it' in pg.inner_text('#ly-say')
          and 'on Level 3 of Tall Brown Shelf' in pg.evaluate(f'lyWhere(LY.d, lyItem({rp3}))') and pg.evaluate('LY.F.length') == 0,
          f"""the shelf moved by the arrow keys carries the plant on its third level with it, on the page and in the record of the layout ({it(pg, block["id"])} {it(pg, rp3)} {pg.inner_text('#ly-say')} {pg.evaluate('LY.F.map(f => f.text)')})""")
    check('it carries' in pg.locator('#ly-undo').get_attribute('aria-label'), 'Undo says that it would put back the shelf and what it carries')
    pg.click('#ly-undo')
    check(until(pg, lambda: both(0, 0)) and until(pg, lambda: (saved(rid, rp3)['x'], saved(rid, block['id'])['x']) == (sp['x'], sb['x'])), 'Undo puts the shelf and the plant back together')
    pg.click('#ly-redo')
    check(until(pg, lambda: both(1, 1)) and until(pg, lambda: saved(rid, rp3)['y'] == sp['y'] + 1), 'and Redo moves them together again')
    pg.click('#ly-undo'); until(pg, lambda: both(0, 0))
    pg.evaluate("(() => { const r = document.querySelector('svg.ly-svg[data-view=top]').getBoundingClientRect(); window.scrollBy(0, r.top - 190); })()"); pg.wait_for_timeout(150)
    edge = pg.evaluate("i => { const r = document.querySelector(`svg.ly-svg[data-view=top] g.ly-it[data-id='${i}'] .ly-shape`).getBoundingClientRect(); return [r.x + 7, r.y + r.height / 2]; }", block['id'])
    S = pg.evaluate('LY.Sv.top'); drag(pg, edge, 6 * S, 10 * S)
    check(until(pg, lambda: both(6, 10)) and until(pg, lambda: (saved(rid, rp3)['x'], saved(rid, rp3)['y']) == (sp['x'] + 6, sp['y'] + 10)), f'dragged, the shelf carries the plant too ({it(pg, block["id"])} {it(pg, rp3)})')
    pg.click('#ly-undo'); until(pg, lambda: both(0, 0))

    # ---- the front view of a room looks at one wall, and draws only what is at that wall
    pg.click('#ly-v-both', force=True); until(pg, lambda: pg.locator('svg.ly-svg[data-view=front]').count() == 1)
    front = lambda sel='g.ly-it': pg.locator(f'svg.ly-svg[data-view=front] {sel}')
    total = pg.evaluate('LY.d.items.length'); nb = pg.evaluate("lyWallSet(LY.d, 'back').size")
    check(pg.input_value('#ly-wall') == 'back' and 'the back wall' in pg.inner_text('figure[data-view=front] figcaption') and pg.evaluate("document.getElementById('ly-wall').selectedOptions[0].textContent") == 'Back wall' and f'{nb} of the {total} things are here' in pg.inner_text('figure[data-view=front] figcaption') 
          and front().count() == nb < total and pg.locator('svg.ly-svg[data-view=top] .ly-wallmark').count() == 1 and pg.evaluate("[...document.querySelectorAll('#ly-wall option')].map(o => o.value)") == ['back', 'left', 'right', 'front', 'mid', 'all'],
          f'in a room the front view starts at the back wall and draws the {nb} of {total} things that are there; the top view marks that wall with a heavy edge; a list offers the four walls, the things away from the walls, and everything at once')
    pick(rp3); pg.select_option('#ly-f-on', 'floor'); until(pg, lambda: it(pg, rp3)['z'] == 0)
    for k, val in (('y', 60), ('x', pg.evaluate('LY.d.width_in') - 8)): pg.fill(f'#ly-f-{k}', str(val)); pg.press(f'#ly-f-{k}', 'Tab')
    check(until(pg, lambda: (it(pg, rp3)['x'], it(pg, rp3)['y']) == (pg.evaluate('LY.d.width_in') - 8, 60) and pg.input_value('#ly-wall') == 'right') and front(f'g.ly-it[data-id="{rp3}"]').count() == 1
          and 'the right wall' in pg.inner_text('figure[data-view=front] figcaption') and front().count() == pg.evaluate("lyWallSet(LY.d, 'right').size") and front('.ly-selmark').count() == 1,
          'the chosen plant moved over to the right wall: the front view goes to that wall with it')
    front(f'g.ly-it[data-id="{rp3}"]').focus(); pg.keyboard.press('ArrowRight')
    check(until(pg, lambda: (it(pg, rp3)['x'], it(pg, rp3)['y']) == (pg.evaluate('LY.d.width_in') - 8, 61)) and 'Back' in pg.inner_text('figure[data-view=front] .ly-edge-row'), 'facing the right wall, Right arrow takes it toward the front of the room, which is on your right there')
    pg.keyboard.press('ArrowLeft'); until(pg, lambda: it(pg, rp3)['y'] == 60)
    c0 = pg.evaluate("i => { const g = document.querySelector(`svg.ly-svg[data-view=front] g.ly-it[data-id='${i}']`); g.scrollIntoView({ block: 'center' }); const r = g.querySelector('.ly-shape').getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }", rp3)
    drag(pg, c0, -5 * pg.evaluate('LY.Sv.front'), 0)
    check(until(pg, lambda: (it(pg, rp3)['x'], it(pg, rp3)['y'], it(pg, rp3)['z']) == (pg.evaluate('LY.d.width_in') - 8, 55, 0)), f'dragged to the left in that view, it goes toward the back of the room and stays on the floor ({it(pg, rp3)})')
    pg.select_option('#ly-wall', 'left')
    lefts = pg.evaluate("[...lyWallSet(LY.d, 'left')]")
    check(until(pg, lambda: 'the left wall' in pg.inner_text('figure[data-view=front] figcaption')) and front().count() == len(lefts) and front(f'g.ly-it[data-id="{rp3}"]').count() == 0 and front('.ly-selmark').count() == 0
          and pg.evaluate('LY.sel') == rp3 and 'left wall' in pg.inner_text('#ly-say'), 'another wall chosen from the list: its things are drawn, the chosen plant stays chosen and is not in that view, and the change is said')
    if lefts:
        lw = lefts[0]; y0 = it(pg, lw)['y']; front(f'g.ly-it[data-id="{lw}"]').focus(); pg.keyboard.press('ArrowLeft')
        check(until(pg, lambda: it(pg, lw)['y'] == y0 + 1), 'facing the left wall, Left arrow takes a thing toward the front of the room, which is on your left there')
        pg.keyboard.press('ArrowRight'); until(pg, lambda: it(pg, lw)['y'] == y0)
    pick(rp3)
    check(until(pg, lambda: pg.input_value('#ly-wall') == 'right') and front(f'g.ly-it[data-id="{rp3}"]').count() == 1, 'choosing the plant again brings the front view back to its wall')
    # a thing far from every wall is in no wall's view: it has a view of its own
    for k, val in (('x', 60), ('y', 50)): pg.fill(f'#ly-f-{k}', str(val)); pg.press(f'#ly-f-{k}', 'Tab')
    check(until(pg, lambda: (it(pg, rp3)['x'], it(pg, rp3)['y']) == (60, 50) and pg.input_value('#ly-wall') == 'mid') and front(f'g.ly-it[data-id="{rp3}"]').count() == 1 and front().count() == pg.evaluate("lyWallSet(LY.d, 'mid').size")
          and 'away from the walls' in pg.inner_text('figure[data-view=front] figcaption') and pg.locator('svg.ly-svg[data-view=top] .ly-wallmark').count() == 0
          and pg.evaluate(f"['back', 'left', 'right', 'front'].every(w => !lyWallSet(LY.d, w).has({rp3}))"),
          'moved to the middle of the room, more than 2 ft from every wall, the plant is in no wall\'s view: the front view turns to the things away from the walls')
    pg.select_option('#ly-wall', 'back')
    check(until(pg, lambda: 'the back wall' in pg.inner_text('figure[data-view=front] figcaption')) and front(f'g.ly-it[data-id="{rp3}"]').count() == 0, 'and the back wall\'s view does not draw it')
    pg.select_option('#ly-wall', 'all')
    check(until(pg, lambda: front().count() == total) and pg.locator('svg.ly-svg[data-view=top] .ly-wallmark').count() == 0 and 'wall' not in pg.inner_text('figure[data-view=front] figcaption strong'), 'Everything draws every thing at once, as before')
    shot(pg, '6d-walls')
    pg.select_option('#ly-wall', 'back'); pg.click('#ly-v-top', force=True); until(pg, lambda: pg.locator('svg.ly-svg[data-view=front]').count() == 0)
    check(pg.locator('#ly-wall').count() == 0, 'with the top view alone there is no wall to choose')

    # boxes typed one after another while an earlier save is still on its way are each kept as typed (each box is read when it is
    # left: read after the wait, a box could by then have been filled in again from the thing as it was)
    pg.evaluate("(() => { window.lyRealApi = api; api = async (m, u, ...more) => { if (m === 'PUT' && u.startsWith('/api/layouts/items/')) await new Promise(r => setTimeout(r, 400)); return lyRealApi(m, u, ...more); }; })()")
    pick(rp3); p0 = it(pg, rp3)
    for k, val in (('x', p0['x'] + 1), ('y', p0['y'] + 2), ('x', p0['x'] + 3)): pg.fill(f'#ly-f-{k}', str(val)); pg.press(f'#ly-f-{k}', 'Tab')
    check(until(pg, lambda: (saved(rid, rp3)['x'], saved(rid, rp3)['y']) == (p0['x'] + 3, p0['y'] + 2), 8000) and (it(pg, rp3)['x'], it(pg, rp3)['y']) == (p0['x'] + 3, p0['y'] + 2),
          f"three boxes typed while saves are slow: each is kept as typed, on the page and in the record ({it(pg, rp3)}, {saved(rid, rp3)['x']}, {saved(rid, rp3)['y']})")
    pg.evaluate('(async () => { await LY.q; api = lyRealApi; })()')
    shot(pg, '6c-room')
    call('PUT', f"/api/plants/{away[0]['code']}", {'base_version': call('GET', f"/api/plants/{away[0]['code']}")['version'], 'fields': {'height_in': None}})
    call('DELETE', f'/api/layouts/{rid}')

    # ---- the list, and the ways in
    pg.goto(BASE + '/#/layouts'); pg.wait_for_selector('.ly-cards .ly-card', timeout=20000)
    card = pg.locator('.ly-card').first
    check(pg.locator('.ly-card').count() == 1 and card.locator('svg.ly-svg').count() == 1 and 'things on it' in card.inner_text() and 'warning' in card.inner_text(), 'the list shows the layout as a card with a small drawing and how it stands')
    shot(pg, '7-list')
    pg.goto(BASE + '/#/where'); pg.wait_for_selector('#ly-wherelink', timeout=20000)
    link = pg.locator(f'a.ly-wh[href="#/layouts?place={spot["id"]}"]')
    check(link.inner_text() == 'Open its layout' and link.get_attribute('aria-label') == 'Open its layout: Tall Brown Shelf', 'on Rooms and spots the shelf now says "Open its layout"')
    link.click()
    check(until(pg, lambda: pg.url.endswith(f'#/layouts/{lid}') and pg.locator('#ly-draw svg.ly-svg').count() >= 1 and pg.evaluate('!!LY && LY.d.id') == lid), 'and that opens it')
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
    check(not vis('#ly-rec') and v.locator('[data-act=lyrec]').count() == 0 and status('POST', f'/api/layouts/{lid}/record', {'moves': [{'plant': plant['plant'], 'place': -1}]}, base=TS, login='viewer@example.com') == 403
          and status('PUT', f"/api/layouts/items/{plant['id']}", {'h': 30}, base=TS, login='viewer@example.com') == 403, 'nor a way to move a plant in the record or to change its height')
    v.evaluate("i => lyFocusIt(i, 'front')", plant['id']); v.keyboard.press('ArrowRight'); v.wait_for_timeout(300)
    check(it(v, plant['id'])['x'] == plant['x'] and v.evaluate('LY.sel') is None, 'and the arrow keys move nothing')
    v.keyboard.press('Enter')
    check(until(v, lambda: v.evaluate('LY.sel') == plant['id']) and v.locator('#ly-f-x').is_disabled() and 'Light here' in v.inner_text('#ly-p-light') and 'In your record' in v.inner_text('#ly-p-rec')
          and v.locator('#ly-recone').count() == 0 and v.locator('#ly-tallsave').count() == 0, 'but a thing can be chosen, to read its place, its size, its light and where the record has it')
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
    check(ph.locator('#ly-rec').is_visible() and ph.locator('#ly-rec [data-act=lyrec]').count() == 3 and ph.locator('#ly-p-light').is_visible() and over(ph) <= 0, 'the plants to move in the record and the light of the chosen plant fit the phone too')
    ph.evaluate("document.getElementById('ly-rec').scrollIntoView()"); ph.wait_for_timeout(200); shot(ph, '8b-phone-record')
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
