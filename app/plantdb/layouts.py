"""Layouts (1.58.0; prototype #131). A room, a porch, a patch of yard or one shelf unit, drawn to scale, with the plants, grow
lights, shelves and anything else in it as things to move about on the page before the real ones are moved (Ethan, November 14,
2026: "simulate 2D (maybe also 3D later) spaces ... dragging them around, snapping to and showing a grid, setting sizes for the
space and the items, indicating when things collide or may conflict").

Everything is a box. A layout is a space with a width (left to right), a depth (back to front) and a height (floor up), in inches
like every other length in the record. A thing on it has a place (x from the left, y from the back, z off the floor: its left,
back, bottom corner) and a size (w across, d back to front, h tall), and is a box or, seen from above, a circle ('round': a pot).
The top view shows x and y, the front view x and z. A corner view in three dimensions needs nothing more than is stored here.

The page does the moving, the snapping to the grid and the looking for things that overlap (js/layouts.js, lyFindings), because
those must answer while a thing is being dragged. The server keeps the layouts, checks what it is given, and adds what only the
record knows: what a layout of a place would start with (layout_start: a shelf's levels from its measurements, a room's shelves
as blocks), how much room each plant and light probably takes (layout_plant_size from its tray, pot and height; layout_light_size
from how the light holds), and which plants are at the place.

Tables, made on first use: layouts and layout_items. A layout may be of a room or area (area_id) or of a shelf (spot_id); a thing
may be one of the record's plants (plant_code), lights (light_id) or shelves (spot_id).

What a layout changes in the record (Ethan, November 15, 2026), and nothing else:
- A plant's height. A plant on a layout is as tall as its page says ("Height now, with its pot"); a height given to it on a layout
  is saved on its page (layout_item_one), so there is one height for a plant, changed in either place.
- Where a plant is, when the person says so. Moving a plant on a drawing changes nothing; "Move it here in the record" does
  (layout_record), for the plants drawn on a layout of a room, an area or a shelf.
Light from the drawing: a drawn light carries the hours it is on and its brightness, and its maker's figures go to the page with it,
so the page can say how much light each plant gets where it is drawn (js/layouts.js, lyLight), in the words Grow lights uses."""
from .core import *   # noqa: F401,F403
ORDER = 66            # calls into where.py and lights.py (50) and fit.py (60): rooms and shelves, a light's reach, a shelf's measurements

LAYOUT_KINDS = {'plant': 'Plant', 'light': 'Grow light', 'shelf': 'Shelf or furniture', 'window': 'Window', 'other': 'Something else', 'zone': 'Area to keep clear'}
# A window (1.58.0, Ethan: "Daylight from windows and the shade one plant casts on another"): which way it faces, and the daylight it
# gives at the glass on a usual day (mol/m² a day), to start with (a light meter's reading is better: type it on the layout).
# The numbers are a home's own (home_window_dli, places.py) or else WINDOW_DLI (core.py); a window can have its own (day_dli).
LAYOUT_FACING, LAYOUT_WINDOW_DLI = WINDOW_FACING, WINDOW_DLI
LAYOUT_WIN_FALL_IN = 24          # a window's daylight is half as much this far from the glass, a fifth at twice as far
# Shade (Ethan, November 17, 2026: "Pots will block 100% of light while plants will block ~50%. Having the ability to change these values
# myself would be nice."): how much of the light a pot in the way blocks, and how much a plant's leaves block, in percent. Each layout
# can say its own (pot_block, leaf_block). A plant's pot is the bottom part of its box, pot_h tall.
LAYOUT_POT_BLOCK, LAYOUT_LEAF_BLOCK = 100, 50
LAYOUT_POT_TALL = 0.85           # a pot with no height in Pots and trays is taken to be this much as tall as it is wide
LAYOUT_SHAPES = ('box', 'round')
LAYOUT_GRIDS = (0.5, 1, 2, 3, 6, 12)                 # the squares offered, in inches (the page offers round centimetres to a person who reads them)
LAYOUT_BOARD_IN = 0.75                               # a shelf board's thickness, when nothing says
LAYOUT_HEADROOM_IN = 24                              # room drawn above a shelf's top level, when its measurements give none
LAYOUT_ROOM_IN = (144, 120, 96)                      # a room whose own width and depth are not known: 12 by 10 ft, 8 ft high
LAYOUT_POT_IN = {'Small': 6.0, 'Medium': 10.0, 'Large': 16.0}        # across, from a plant's Pot size, when it has no pot or tray from Pots and trays
LAYOUT_SCHEMA = """
CREATE TABLE IF NOT EXISTS layouts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, home_id INTEGER, area_id INTEGER, spot_id INTEGER,
  width_in REAL NOT NULL, depth_in REAL NOT NULL, height_in REAL NOT NULL,
  grid_in REAL NOT NULL DEFAULT 1, snap INTEGER NOT NULL DEFAULT 1, clear_in REAL NOT NULL DEFAULT 1, notes TEXT NOT NULL DEFAULT '',
  pot_block INTEGER, leaf_block INTEGER,
  created_by TEXT, created_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS layout_items(
  id INTEGER PRIMARY KEY AUTOINCREMENT, layout_id INTEGER NOT NULL REFERENCES layouts(id) ON DELETE CASCADE,
  kind TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', shape TEXT NOT NULL DEFAULT 'box',
  plant_code TEXT, light_id INTEGER, spot_id INTEGER,
  x REAL NOT NULL DEFAULT 0, y REAL NOT NULL DEFAULT 0, z REAL NOT NULL DEFAULT 0, w REAL NOT NULL, d REAL NOT NULL, h REAL NOT NULL,
  locked INTEGER NOT NULL DEFAULT 0, notes TEXT NOT NULL DEFAULT '', sort INTEGER NOT NULL DEFAULT 0,
  hours REAL, dim_pct INTEGER, size_locked INTEGER NOT NULL DEFAULT 0, facing TEXT, day_dli REAL, pot_h REAL,
  created_by TEXT, created_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT);
CREATE INDEX IF NOT EXISTS layout_items_of ON layout_items(layout_id, sort);
"""
LAYOUT_HOURS, LAYOUT_DIM = 12.0, 100                 # a drawn light is on this long and this bright, until the person says
def layout_tables(c):
    """On first use, and for a record put back from a backup made before layouts. A light's hours and brightness came later than
    the first tables, so they are added to a table that was made without them. So is size_locked (Ethan, November 16, 2026: the
    size is locked apart from the place). Before it, locked held both, so a thing that was locked keeps its size locked too."""
    c.executescript(LAYOUT_SCHEMA)
    have = {r[1] for r in c.execute('PRAGMA table_info(layout_items)')}
    for col, kind in (('hours', 'REAL'), ('dim_pct', 'INTEGER'), ('facing', 'TEXT'), ('day_dli', 'REAL'), ('pot_h', 'REAL')):
        if col not in have: c.execute(f'ALTER TABLE layout_items ADD COLUMN {col} {kind}')
    if 'size_locked' not in have:
        c.execute('ALTER TABLE layout_items ADD COLUMN size_locked INTEGER NOT NULL DEFAULT 0')
        c.execute('UPDATE layout_items SET size_locked=locked')
    has = {r[1] for r in c.execute('PRAGMA table_info(layouts)')}             # how much a pot and leaves block (1.58.0)
    for col in ('pot_block', 'leaf_block'):
        if col not in has: c.execute(f'ALTER TABLE layouts ADD COLUMN {col} INTEGER')

# ---------------------------------------------------------------- what the record knows about sizes
def layout_plant_size(c, r):
    """How much room a plant takes on a layout: (w, d, h, shape, guessed). Across: its catch tray, else its pot (Pots and trays), else
    a guess from its Pot size. Tall: its "Height now, with its pot", else a guess. guessed names what was guessed ('width', 'height'),
    so the page can say so and the person can put the real size in."""
    w = d = None; shape = 'round'; guessed = []
    for k in ('tray_id', 'pot_id'):
        x = c.execute('SELECT * FROM containers WHERE id=?', (r[k],)).fetchone() if r[k] else None
        if x is None: continue
        if x['shape'] == 'circle' and x['dia_in']: w = d = x['dia_in']; break
        if x['shape'] == 'square' and x['len_in']: w = d = x['len_in']; shape = 'box'; break
        if x['shape'] == 'rectangle' and x['len_in'] and x['wid_in']: w, d, shape = x['len_in'], x['wid_in'], 'box'; break
    if w is None: w = d = LAYOUT_POT_IN.get((r['pot_size'] or '').split(':')[0], 8.0); guessed.append('width')
    h = r['height_in']
    if not h: h = 12.0; guessed.append('height')
    return round(float(w), 2), round(float(d), 2), round(float(h), 2), shape, guessed

def layout_pot_rec(c, p):
    """A plant's pot's height in Pots and trays, or None."""
    x = c.execute('SELECT height_in FROM containers WHERE id=?', (p['pot_id'],)).fetchone() if p is not None and p['pot_id'] else None
    return round(float(x['height_in']), 2) if x is not None and x['height_in'] else None

def layout_light_size(L):
    """A light's rough size from how it holds (fit.py: lights.data['mount']): (w, d, h, shape, hangs). A starting point to correct on
    the layout; hangs says it starts up under something rather than standing on something."""
    m = light_mount(L) or {}; k = m.get('kind')
    if k == 'under': return float(m.get('length_in') or 12), 2.0, 1.5, 'box', True                                   # a strip screwed under a shelf
    if k == 'floor': f = float(m.get('footprint_in') or 20); return f, f, float(m.get('height_hi') or 60), 'round', False
    if k == 'surface': f = float(m.get('footprint_in') or 6); return float(m.get('length_in') or f), f, float(m.get('height_hi') or 18), 'box', False
    if k == 'clamp': return 6.0, 6.0, 4.0, 'box', True
    if k == 'none': return 7.0, 7.0, 2.0, 'round', True
    return 5.0, 5.0, 6.0, 'round', True                                                                             # a bulb in a socket, a hanging light, or not said yet

def layout_boards(sheet):
    """A shelf unit's levels as boards, from its measurements (fit.py: spots.sheet): ([board, ...], the height of the unit) or ([], None)
    when the measurements do not give them. Level 1 is the bottom one and sits on the floor, since nothing says how high it stands;
    each level above is a board's thickness and that level's clear height higher (gaps_in, bottom first; else gap_in for all)."""
    n, w, d = int(sheet.get('levels') or 0), sheet.get('width_in'), sheet.get('depth_in')
    if n < 2 or not w or not d: return [], None
    gaps = sheet.get('gaps_in') or ([sheet['gap_in']] * (n - 1) if sheet.get('gap_in') else [])
    if len(gaps) != n - 1: return [], None
    out, z = [], 0.0
    for i in range(n):
        out.append({'kind': 'shelf', 'name': 'Level %d%s' % (i + 1, ' (bottom)' if i == 0 else ' (top)' if i == n - 1 else ''), 'shape': 'box',
                    'x': 0.0, 'y': 0.0, 'z': round(z, 2), 'w': float(w), 'd': float(d), 'h': LAYOUT_BOARD_IN, 'locked': True, 'size_locked': True})
        z += LAYOUT_BOARD_IN + (gaps[i] if i < n - 1 else 0)
    return out, round(z, 2)

def layout_levels(sheet):
    """The levels of one of the record's shelves, for a shelf drawn as one block on a room's layout: [{n, name, z, room}], the bottom
    one first. z is the height of that level's top above the foot of the shelf, and room the clear height above it (none for the top
    level). The page lets a plant stand on any of them (js/layouts.js, lySurf). [] when the measurements do not give the levels."""
    boards, _ = layout_boards(sheet)
    return [{'n': i + 1, 'name': b['name'], 'z': round(b['z'] + LAYOUT_BOARD_IN, 2),
             'room': round(boards[i + 1]['z'] - b['z'] - LAYOUT_BOARD_IN, 2) if i + 1 < len(boards) else None} for i, b in enumerate(boards)]

def layout_start(c, area, spot):
    """What a layout of a room or area (spot None) or of a shelf would start with: {width_in, depth_in, height_in, items, notes}.
    A shelf: its own width and depth, its levels as boards when its measurements give them, and room above the top level. A room:
    its ceiling height, a width and depth to correct (rooms have none in their measurements), and its shelves as blocks along the
    back wall."""
    notes = []
    if spot is not None:
        s = sheet_of(spot); boards, top = layout_boards(s)
        w, d = s.get('width_in'), s.get('depth_in')
        if not w or not d: notes.append('This shelf has no width and depth in its measurements yet, so the size here is a starting guess. Add them with "Measurements and photos" on Rooms and spots, or type the size below.')
        elif (s.get('levels') or 1) > 1 and not boards: notes.append('The clear height of each level is not in its measurements yet, so its levels are not drawn.')
        if boards: notes.append(f'Its {len(boards)} levels are drawn as boards {LAYOUT_BOARD_IN:g} in thick, the bottom one on the floor. Change any of them on the layout.')
        return {'width_in': float(w or 36), 'depth_in': float(d or 12), 'height_in': round((top or 0) + float(s.get('top_in') or LAYOUT_HEADROOM_IN), 2), 'items': boards, 'notes': notes}
    s = sheet_of(area)
    W, D, H = LAYOUT_ROOM_IN[0], LAYOUT_ROOM_IN[1], float(s.get('ceiling_in') or LAYOUT_ROOM_IN[2])
    notes.append('A room has no width and depth in its measurements, so 12 by 10 ft is a starting guess. Type its real size below.')
    items, x, y, row = [], 0.0, 0.0, 0.0
    for sp in c.execute('SELECT * FROM spots WHERE area_id=? ORDER BY sort, id', (area['id'],)).fetchall():
        ss = sheet_of(sp); _, top = layout_boards(ss)
        w, d, h = float(ss.get('width_in') or 30), float(ss.get('depth_in') or 12), float(top or 36)
        if x and x + w > W: x, y, row = 0.0, y + row + 24, 0.0          # the next row, two feet in front of the last
        items.append({'kind': 'shelf', 'name': sp['name'], 'shape': 'box', 'spot_id': sp['id'], 'x': x, 'y': y, 'z': 0.0, 'w': w, 'd': d, 'h': h, 'locked': False, 'size_locked': False})
        x += w + 6; row = max(row, d)
    if items: notes.append(f'Its {len(items)} {"spots are" if len(items) != 1 else "spot is"} drawn as blocks along the back wall, from their measurements where they have them. Move each to where it stands.')
    return {'width_in': float(W), 'depth_in': float(D), 'height_in': H, 'items': items, 'notes': notes}

# ---------------------------------------------------------------- reading a layout
def layout_home_name(c, hid):
    h = next((x for x in homes(c) if (x['id'] == hid if hid else x['is_home'])), None)
    return h['name'] if h else ''

def layout_pid(r):
    """The place a row is at, as one number: a shelf's id, or minus a room's or area's id (the numbers place_rows() reads)."""
    return r['spot_id'] if r['spot_id'] else (-r['area_id'] if r['area_id'] else None)

def layout_light_setting(c, L, light_id):
    """The hours and brightness a drawn light starts with: those of a Grow lights spot with this light at the layout's own place,
    else of your first spot with it, else 12 hours at full brightness."""
    rows = c.execute('SELECT hours, dim_pct, place_id FROM light_spots WHERE light_id=? ORDER BY id', (light_id,)).fetchall() if light_id else []
    pid = layout_pid(L)
    s = next((r for r in rows if pid is not None and r['place_id'] == pid), rows[0] if rows else None)
    return (float(s['hours']), int(s['dim_pct'])) if s is not None else (LAYOUT_HOURS, LAYOUT_DIM)

def layout_item_dict(c, it):
    """A thing on a layout. One of the record's plants, lights or shelves carries its name as the record has it now (and its photo);
    gone is set when the record no longer has it, and the name it had when it was drawn is kept.
    A plant also carries what its page says: its height (page_h; it is that tall here too), the daily light it needs (need) and
    where the record has it (rec, a place number, and rec_label). A light carries its maker's figures (pts: [inches, PAR, sq ft]),
    the brightness steps it has (dims), and the hours and brightness it is drawn with. A shelf carries its place's name (place),
    and its levels when its measurements give them (levels, layout_levels), so a plant can be put on one of them."""
    d = {k: it[k] for k in ('id', 'kind', 'name', 'shape', 'x', 'y', 'z', 'w', 'd', 'h', 'notes', 'sort')}
    d.update(locked=bool(it['locked']), size_locked=bool(it['size_locked']), plant=it['plant_code'], light_id=it['light_id'], spot_id=it['spot_id'], gone=False)
    if it['kind'] == 'light':
        d.update(hours=it['hours'] if it['hours'] is not None else LAYOUT_HOURS, dim_pct=it['dim_pct'] if it['dim_pct'] is not None else LAYOUT_DIM, pts=[], dims=[100])
    if it['kind'] == 'window':
        fc = it['facing'] if it['facing'] in LAYOUT_FACING else 'S'
        d.update(facing=fc, day_dli=it['day_dli'])          # its own daylight, or none: its home's for that way (window_dli, _ly_day)
    if it['kind'] == 'plant':
        # its pot, the bottom part of its box, which shades what is behind it: as tall as the layout says (pot_h), else as its pot in
        # Pots and trays (pot_rec), else a guess from its width (_ly_pot_h)
        d.update(pot_h=it['pot_h'], pot_rec=None)
    if it['plant_code']: part = layout_plant_part(c, c.execute("SELECT * FROM plants WHERE code=?", (it['plant_code'],)).fetchone())
    elif it['light_id']: part = layout_light_part(c.execute('SELECT * FROM lights WHERE id=?', (it['light_id'],)).fetchone())
    elif it['spot_id']: part = layout_shelf_part(c, c.execute('SELECT * FROM spots WHERE id=?', (it['spot_id'],)).fetchone(), it['layout_id'])
    else: part = {}
    d.update(part)
    if part.get('page_h'): d['h'] = part['page_h']
    return d

# What a thing on a layout carries from the record (layout_item_dict). The full layout offers each plant, light and shelf with it too
# (item), so the page can draw one put on with no connection as the server will (1.58.0, Ethan: "Would it be possible to have things
# be put on or off compatible with offline mode?").
def layout_plant_part(c, p):
    if p is None or p['status'] != 'active': return {'gone': True, 'pot_rec': None}
    pid = layout_pid(p)
    return {'name': p['common_name'], 'photo': plant_photo(c, p['id']), 'page_h': p['height_in'], 'need': plant_need(p), 'rec': pid, 'rec_label': place_label(c, pid), 'pot_rec': layout_pot_rec(c, p)}

def layout_light_part(L):
    if L is None: return {'gone': True}
    specs = light_specs(L); pts = light_points(specs)
    near, far = light_range(pts)
    return {'name': L['name'], 'near_in': near, 'far_in': far, 'owned': L['count'], 'pts': [list(p) for p in pts],
            'dims': sorted({int(x) for x in (specs.get('dimming') or [100]) if 0 < int(x) <= 100} | {100}, reverse=True)}

def layout_shelf_part(c, sp, lid):
    if sp is None: return {'gone': True}
    sh = sheet_of(sp)
    own = c.execute('SELECT id FROM layouts WHERE spot_id=? AND id<>? ORDER BY id LIMIT 1', (sp['id'], lid)).fetchone()
    return {'name': sp['name'], 'place': place_label(c, sp['id']), 'levels': layout_levels(sh), 'board_in': LAYOUT_BOARD_IN,
            'sheet': {k: sh.get(k) for k in ('width_in', 'depth_in', 'levels', 'gaps_in', 'gap_in', 'top_in')},      # its measurements, so a new size can be saved to them
            'layout_id': own[0] if own else None}                                                                 # this shelf's own layout, to open from here

def layout_dict(c, L, full=False):
    """A layout with the things on it. full adds what can be put on it: the plants at its home (those at its own place marked here),
    your lights, and your shelves, each with the size the record suggests."""
    pid = layout_pid(L)
    d = {k: L[k] for k in ('id', 'name', 'home_id', 'area_id', 'spot_id', 'width_in', 'depth_in', 'height_in', 'grid_in', 'clear_in', 'notes', 'updated_at', 'updated_by')}
    d.update(pot_block=L['pot_block'] if L['pot_block'] is not None else LAYOUT_POT_BLOCK, leaf_block=L['leaf_block'] if L['leaf_block'] is not None else LAYOUT_LEAF_BLOCK)
    if L['spot_id']:                                       # a shelf unit's own layout: the shelf's measurements, so its boards can be saved to them (1.58.0)
        sp = c.execute('SELECT * FROM spots WHERE id=?', (L['spot_id'],)).fetchone()
        sh = sheet_of(sp) if sp else {}
        d['sheet'] = {k: sh.get(k) for k in ('width_in', 'depth_in', 'levels', 'gaps_in', 'gap_in', 'top_in')} if sp else None
    hw = home_window_dli(c, L['home_id'])                  # the daylight at its home's windows, by the way they face
    d.update(window_dli=hw['dli'], window_own=hw['own'], window_home={'id': hw['home_id'], 'name': hw['home']})
    d.update(snap=bool(L['snap']), pid=pid, place=place_label(c, pid) if pid else None, home=layout_home_name(c, L['home_id']),
             items=[layout_item_dict(c, it) for it in c.execute('SELECT * FROM layout_items WHERE layout_id=? ORDER BY sort, id', (L['id'],)).fetchall()])
    if not full: return d
    H = home_place(c)['id']
    on = {it['plant'] for it in d['items'] if it['plant']}
    plants = []
    for r in c.execute("SELECT * FROM plants WHERE status='active' AND COALESCE(home_id, ?)=? ORDER BY code", (H, L['home_id'] or H)).fetchall():
        w, dd, h, shape, guessed = layout_plant_size(c, r)
        here = bool(L['spot_id'] and r['spot_id'] == L['spot_id']) or bool(L['area_id'] and not L['spot_id'] and r['area_id'] == L['area_id'] and not r['spot_id'])
        plants.append({'code': r['code'], 'name': r['common_name'], 'photo': plant_photo(c, r['id']), 'w': w, 'd': dd, 'h': h, 'shape': shape, 'guessed': guessed,
                       'here': here, 'on': r['code'] in on, 'item': layout_plant_part(c, r)})
    lights = []
    for x in c.execute("SELECT * FROM lights WHERE status='owned' AND count>0 ORDER BY sort, id").fetchall():
        w, dd, h, shape, hangs = layout_light_size(x)
        near, far = light_range(light_points(light_specs(x)))
        hours, dim = layout_light_setting(c, L, x['id'])
        lights.append({'id': x['id'], 'name': x['name'], 'count': x['count'], 'w': w, 'd': dd, 'h': h, 'shape': shape, 'hangs': hangs, 'near_in': near, 'far_in': far,
                       'hours': hours, 'dim_pct': dim, 'figures': bool(near), 'item': layout_light_part(x)})
    shelves = []
    for sp in c.execute('SELECT s.*, a.name AS area FROM spots s JOIN areas a ON a.id=s.area_id WHERE ' + ('a.home_id IS NULL' if not L['home_id'] else 'a.home_id=?') + ' ORDER BY a.sort, a.id, s.sort, s.id',
                        (() if not L['home_id'] else (L['home_id'],))).fetchall():
        if sp['id'] == L['spot_id']: continue
        s = sheet_of(sp); boards, top = layout_boards(s)
        shelves.append({'spot_id': sp['id'], 'name': sp['name'], 'label': sp['area'] + ', ' + sp['name'], 'w': float(s.get('width_in') or 30), 'd': float(s.get('depth_in') or 12),
                        'h': float(top or 36), 'guessed': not (s.get('width_in') and s.get('depth_in') and top), 'boards': boards, 'item': layout_shelf_part(c, sp, L['id'])})
    d.update(plants=plants, lights=lights, shelves=shelves, kinds=LAYOUT_KINDS, grids=list(LAYOUT_GRIDS), verdicts=LIGHT_VERDICT,
             facing=LAYOUT_FACING)
    return d

def layout_places(c):
    """Every room, area and shelf at every home, with what a layout of it would start with and the layout it already has."""
    have = {}
    for r in c.execute('SELECT id, area_id, spot_id FROM layouts ORDER BY id DESC'): have[r['spot_id'] if r['spot_id'] else (-r['area_id'] if r['area_id'] else 0)] = r['id']
    out = []
    for h in homes(c):
        hid = None if h['is_home'] else h['id']
        for a in c.execute('SELECT * FROM areas WHERE ' + ('home_id IS NULL' if hid is None else 'home_id=?') + ' ORDER BY side DESC, sort, id', (() if hid is None else (hid,))).fetchall():
            out.append({'pid': -a['id'], 'home': h['name'], 'label': a['name'], 'name': a['name'], 'kind': 'room' if a['side'] == 'in' else 'area', 'layout_id': have.get(-a['id']),
                        'words': sheet_words(sheet_of(a)), 'start': layout_start(c, a, None)})
            for sp in c.execute('SELECT * FROM spots WHERE area_id=? ORDER BY sort, id', (a['id'],)).fetchall():
                out.append({'pid': sp['id'], 'home': h['name'], 'label': a['name'] + ', ' + sp['name'], 'name': sp['name'], 'kind': 'shelf', 'layout_id': have.get(sp['id']),
                            'words': sheet_words(sheet_of(sp)), 'start': layout_start(c, a, sp)})
    return out

# ---------------------------------------------------------------- checking what the page sends
def layout_num(b, k, label, lo, hi, old=None):
    if k not in b: return old
    try: x = round(float(b[k]), 2)
    except (TypeError, ValueError): abort(400, f'{label} must be a number')
    if x != x or not lo <= x <= hi: abort(400, f'{label} must be between {lo:g} and {hi:g} inches')      # x != x: not a number at all
    return x

def layout_amount(b, k, label, lo, hi, old=None):
    """A number that is not a length (hours, a percentage)."""
    if k not in b or b[k] in (None, ''): return old
    try: x = round(float(b[k]), 2)
    except (TypeError, ValueError): abort(400, f'{label} must be a number')
    if x != x or not lo <= x <= hi: abort(400, f'{label} must be between {lo:g} and {hi:g}')
    return x

def layout_fields(b, old=None):
    """A layout's own values from a request, checked; old is its row when it is being changed."""
    o = dict(old) if old is not None else {}
    name = re.sub(r'\s+', ' ', str(b.get('name', o.get('name') or ''))).strip()[:80]
    if not name: abort(400, 'Give the layout a name, for example "Living room" or "Tall brown shelf"')
    f = {'name': name,
         'width_in': layout_num(b, 'width_in', 'The width', 1, 2400, o.get('width_in')), 'depth_in': layout_num(b, 'depth_in', 'The depth', 1, 2400, o.get('depth_in')),
         'height_in': layout_num(b, 'height_in', 'The height', 1, 600, o.get('height_in')),
         'grid_in': layout_num(b, 'grid_in', 'The size of a square', 0.1, 48, o.get('grid_in', 1)), 'clear_in': layout_num(b, 'clear_in', 'The room to leave around a plant', 0, 48, o.get('clear_in', 1)),
         'snap': (1 if b['snap'] else 0) if 'snap' in b else o.get('snap', 1), 'notes': str(b.get('notes', o.get('notes') or '')).strip()[:1000],
         'pot_block': layout_amount(b, 'pot_block', 'How much light a pot blocks (%)', 0, 100, o.get('pot_block')),
         'leaf_block': layout_amount(b, 'leaf_block', "How much light a plant's leaves block (%)", 0, 100, o.get('leaf_block'))}
    for k in ('pot_block', 'leaf_block'):
        if f[k] is not None: f[k] = int(round(f[k]))
    for k, label in (('width_in', 'width'), ('depth_in', 'depth'), ('height_in', 'height')):
        if f[k] is None: abort(400, f'Give the {label} of the space')
    return f

def layout_item_fields(c, L, b, old=None):
    """A thing on a layout from a request, checked: its kind and what it is in the record (only when it is added), then its name,
    shape, place and size."""
    o = dict(old) if old is not None else {}
    f = {}
    if old is None:
        kind = b.get('kind')
        if kind not in LAYOUT_KINDS: abort(400, 'Say what it is: ' + ', '.join(v.lower() for v in LAYOUT_KINDS.values()))
        f.update(kind=kind, plant_code=None, light_id=None, spot_id=None)
        if kind == 'plant' and b.get('plant'):
            r = plant_row(c, str(b['plant']).strip().upper())               # the home limit is checked here too
            if r['status'] != 'active': abort(400, f'{r["code"]} is archived')
            if c.execute('SELECT 1 FROM layout_items WHERE layout_id=? AND plant_code=?', (L['id'], r['code'])).fetchone(): abort(409, f'{r["common_name"]} ({r["code"]}) is already on this layout')
            f.update(plant_code=r['code'], name=r['common_name'])
        elif kind == 'light' and b.get('light_id'):
            x = c.execute('SELECT * FROM lights WHERE id=?', (int(b['light_id']),)).fetchone() if str(b['light_id']).isdigit() else None
            if x is None: abort(400, 'That light is not in your list any more')
            f.update(light_id=x['id'], name=x['name'])
        elif kind == 'shelf' and b.get('spot_id'):
            sp = c.execute('SELECT * FROM spots WHERE id=?', (int(b['spot_id']),)).fetchone() if str(b['spot_id']).isdigit() else None
            if sp is None: abort(400, 'That shelf is not in the list any more')
            f.update(spot_id=sp['id'], name=sp['name'])
    kind = f.get('kind') or o.get('kind')
    if 'name' not in f:
        f['name'] = re.sub(r'\s+', ' ', str(b.get('name', o.get('name') or ''))).strip()[:80]
        if not f['name']: abort(400, 'Give it a name')
    shape = b.get('shape', o.get('shape') or ('round' if kind == 'plant' else 'box'))
    if shape not in LAYOUT_SHAPES: abort(400, 'The shape must be a box or round')
    f['shape'] = 'box' if kind in ('shelf', 'zone') and old is None and 'shape' not in b else shape
    for k, label in (('x', 'How far it is from the left'), ('y', 'How far it is from the back'), ('z', 'How far it is off the floor')):
        f[k] = layout_num(b, k, label, -2400, 4800, o.get(k, 0.0))
    for k, label in (('w', 'Its width'), ('d', 'Its depth'), ('h', 'Its height')):
        f[k] = layout_num(b, k, label, 0.1, 2400, o.get(k))
        if f[k] is None: abort(400, f'{label} is missing')
    f['locked'] = (1 if b['locked'] else 0) if 'locked' in b else o.get('locked', 0)                 # its place: it is not moved
    f['size_locked'] = (1 if b['size_locked'] else 0) if 'size_locked' in b else o.get('size_locked', 0)   # its size: it is not made larger or smaller
    f['notes'] = str(b.get('notes', o.get('notes') or '')).strip()[:400]
    f['hours'] = f['dim_pct'] = f['facing'] = f['day_dli'] = f['pot_h'] = None
    if kind == 'plant':                                    # how tall its pot is: none goes back to its pot's height in Pots and trays, or the guess
        f['pot_h'] = None if 'pot_h' in b and b['pot_h'] in (None, '') else layout_num(b, 'pot_h', 'How tall its pot is', 0.1, 600, o.get('pot_h'))
    if kind == 'window':                                   # which way it faces, and the daylight at the glass
        fc = b.get('facing', o.get('facing') or 'S')
        if fc not in LAYOUT_FACING: abort(400, 'Say which way it faces: ' + ', '.join(LAYOUT_FACING.values()).lower())
        f['facing'] = fc
        # its own daylight; none follows its home's number for the way it faces. Turned another way, it follows its home again.
        day = o.get('day_dli') if old is not None and o.get('facing') == fc else None
        f['day_dli'] = None if 'day_dli' in b and b['day_dli'] in (None, '') else layout_amount(b, 'day_dli', 'Daylight at the glass', 0, 70, day)
    if kind == 'light':                                    # how long it is on and how bright: what the light on the page is worked out from
        hours, dim = (o.get('hours'), o.get('dim_pct')) if old is not None else layout_light_setting(c, L, f.get('light_id'))
        f['hours'] = layout_amount(b, 'hours', 'Hours a day', 0, 24, hours if hours is not None else LAYOUT_HOURS)
        f['dim_pct'] = int(layout_amount(b, 'dim_pct', 'Brightness (%)', 1, 100, dim if dim is not None else LAYOUT_DIM))
    return f

def layout_home_check(c, L):
    """An editor limited to some homes (people.edit_homes) changes the layouts of those homes only; a layout belongs to the home of
    its room or shelf, or the home in use when it was started."""
    allowed = home_limit()
    if not allowed: return
    h = int(L['home_id']) if L['home_id'] else home_place(c)['id']
    if h not in allowed:
        names = {x['id']: x['name'] for x in homes(c)}
        abort(403, f"You can change plants at {', '.join(names.get(x, str(x)) for x in allowed)} only, and this layout is of a place at {names.get(h, 'another home')}.")

def layout_row(c, lid, change=False):
    L = c.execute('SELECT * FROM layouts WHERE id=?', (lid,)).fetchone()
    if L is None: abort(404, 'That layout is not there any more')
    if change: layout_home_check(c, L)
    return L

def layout_size_words(w, d, h): return f'{w:g} by {d:g} by {h:g} in'
def layout_touch(c, lid, who): c.execute('UPDATE layouts SET updated_by=?, updated_at=? WHERE id=?', (who, now(), lid))

def layout_item_add(c, L, b, who):
    f = layout_item_fields(c, L, b)
    n = c.execute('SELECT COALESCE(MAX(sort),0)+1 FROM layout_items WHERE layout_id=?', (L['id'],)).fetchone()[0]
    c.execute('INSERT INTO layout_items(layout_id,kind,name,shape,plant_code,light_id,spot_id,x,y,z,w,d,h,locked,size_locked,notes,hours,dim_pct,facing,day_dli,pot_h,sort,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (L['id'], f['kind'], f['name'], f['shape'], f['plant_code'], f['light_id'], f['spot_id'], f['x'], f['y'], f['z'], f['w'], f['d'], f['h'], f['locked'], f['size_locked'], f['notes'],
               f['hours'], f['dim_pct'], f['facing'], f['day_dli'], f['pot_h'], n, who, now()))
    f['id'] = c.execute('SELECT last_insert_rowid()').fetchone()[0]
    return f

def layout_plant_height(c, L, it, b, h, who):
    """A plant's height was given on a layout: it goes on its page too ("Height now, with its pot"), with a line in the plant's
    History, so a plant has one height. b['page_h'], when the page sends it, is what the page is to say instead: Undo sends it,
    and none puts back a page that had no height. A plant that is archived or gone keeps only the height drawn here."""
    r = c.execute('SELECT * FROM plants WHERE code=?', (it['plant_code'],)).fetchone()
    if r is None or r['status'] != 'active': return
    r = plant_row(c, r['code'])                                # the home limit, where the plant is fetched for a change
    new = b['page_h'] if 'page_h' in b else h
    apply_changes(c, r, {'height_in': new}, who, 'update', f'Height {"set" if new not in (None, "") else "taken off"} on the layout "{L["name"]}"')

# ---------------------------------------------------------------- routes
@app.route('/api/layouts', methods=['GET', 'POST'])
def layouts_api():
    """GET: every layout with the things on it, and every room, area and shelf with what a layout of it would start with.
    ?plant=CODE gives only the layouts that plant is drawn on (for its own page).
    POST {name, width_in, depth_in, height_in, place (a shelf's id, or minus a room's or area's id; none for a space of your own),
    items: [...]} starts one (not for viewers)."""
    c = db(); layout_tables(c)
    if request.method == 'GET':
        code = request.args.get('plant')
        if code:
            return jsonify(on=[{'id': r['id'], 'name': r['name'], 'item': r['item']} for r in c.execute(
                'SELECT l.id, l.name, i.id AS item FROM layout_items i JOIN layouts l ON l.id=i.layout_id WHERE i.plant_code=? ORDER BY l.name', (code.strip().upper(),))])
        return jsonify(layouts=[layout_dict(c, L) for L in c.execute('SELECT * FROM layouts ORDER BY home_id IS NOT NULL, home_id, name COLLATE NOCASE, id').fetchall()],
                       places=layout_places(c), kinds=LAYOUT_KINDS, grids=list(LAYOUT_GRIDS), verdicts=LIGHT_VERDICT)      # verdicts: for Grow lights, which reads the layouts (js/layoutlights.js)
    b = request.get_json(silent=True) or {}; who = editor()
    f = layout_fields(b)
    area_id = spot_id = None
    try: pid = int(b['place']) if b.get('place') not in (None, '', 0, '0') else None
    except (TypeError, ValueError): abort(400, 'Choose a room, an area or a shelf from the list')
    if pid is not None:
        sp, area = place_rows(c, pid)
        if area is None: abort(400, 'That room or shelf is not in the list any more')
        area_id, spot_id, hid = area['id'], (sp['id'] if sp is not None else None), area['home_id']
    else: hid = area_home(c, location(c)['id'])
    layout_home_check(c, {'home_id': hid})
    items = b.get('items') or []
    if not isinstance(items, list) or len(items) > 200: abort(400, 'Too many things to start with')
    lid = c.execute('INSERT INTO layouts(name,home_id,area_id,spot_id,width_in,depth_in,height_in,grid_in,snap,clear_in,notes,created_by,created_at,updated_by,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (f['name'], hid, area_id, spot_id, f['width_in'], f['depth_in'], f['height_in'], f['grid_in'], f['snap'], f['clear_in'], f['notes'], who, now(), who, now())).lastrowid
    L = c.execute('SELECT * FROM layouts WHERE id=?', (lid,)).fetchone()
    for it in items: layout_item_add(c, L, it if isinstance(it, dict) else {}, who)
    audit_only(c, 'where', 'layout', None, f['name'], who, f'Layout added: {f["name"]} ({layout_size_words(f["width_in"], f["depth_in"], f["height_in"])}' + (f', {len(items)} things on it' if items else '') + ')')
    c.commit()
    return jsonify(layout_dict(c, L, True)), 201

@app.route('/api/layouts/<int:lid>', methods=['GET', 'PUT', 'DELETE'])
def layout_one(lid):
    """GET: the layout, the things on it, and what can be put on it. PUT changes its name, size, squares, snapping, the room to leave
    around a plant or its notes. DELETE removes it and the things drawn on it; the plants, lights and shelves themselves stay."""
    c = db(); layout_tables(c)
    L = layout_row(c, lid, request.method != 'GET')
    if request.method == 'GET': return jsonify(layout_dict(c, L, True))
    who = editor()
    if request.method == 'DELETE':
        n = c.execute('SELECT COUNT(*) FROM layout_items WHERE layout_id=?', (lid,)).fetchone()[0]
        c.execute('DELETE FROM layout_items WHERE layout_id=?', (lid,)); c.execute('DELETE FROM layouts WHERE id=?', (lid,))
        audit_only(c, 'where', 'layout', L['name'], None, who, f'Layout removed: {L["name"]}' + (f' ({n} thing{"s" if n != 1 else ""} were drawn on it)' if n else ''))
        c.commit(); return jsonify(ok=True)
    f = layout_fields(request.get_json(silent=True) or {}, L)
    ch = [k for k in f if (L[k] if L[k] is not None else '') != (f[k] if f[k] is not None else '')]
    if ch:
        c.execute('UPDATE layouts SET ' + ','.join(f'{k}=?' for k in ch) + ',updated_by=?,updated_at=? WHERE id=?', [f[k] for k in ch] + [who, now(), lid])
        size = any(k in ch for k in ('width_in', 'depth_in', 'height_in'))
        audit_only(c, 'where', 'layout', layout_size_words(L['width_in'], L['depth_in'], L['height_in']) if size else L['name'],
                   layout_size_words(f['width_in'], f['depth_in'], f['height_in']) if size else f['name'], who,
                   f'Layout "{f["name"]}" changed: ' + ', '.join({'width_in': 'width', 'depth_in': 'depth', 'height_in': 'height', 'grid_in': 'squares', 'clear_in': 'room around a plant', 'snap': 'snapping', 'pot_block': 'light a pot blocks', 'leaf_block': 'light leaves block'}.get(k, k) for k in ch))
        c.commit()
    return jsonify(layout_dict(c, c.execute('SELECT * FROM layouts WHERE id=?', (lid,)).fetchone(), True))

@app.route('/api/layouts/<int:lid>/items', methods=['POST'])
def layout_items_add(lid):
    """Puts things on a layout: one ({kind, name, plant | light_id | spot_id, shape, x, y, z, w, d, h, locked, size_locked}) or several ({items: [...]})."""
    c = db(); layout_tables(c)
    L = layout_row(c, lid, True); who = editor()
    b = request.get_json(silent=True) or {}
    items = b.get('items') if isinstance(b.get('items'), list) else [b]
    if not items or len(items) > 200: abort(400, 'Say what to put on the layout')
    if c.execute('SELECT COUNT(*) FROM layout_items WHERE layout_id=?', (lid,)).fetchone()[0] + len(items) > 400: abort(400, 'A layout holds 400 things at most')
    made = [layout_item_add(c, L, it if isinstance(it, dict) else {}, who) for it in items]
    names = [f['name'] for f in made]
    layout_touch(c, lid, who)
    audit_only(c, 'where', 'layout_item', None, ', '.join(names)[:400], who, f'Layout "{L["name"]}": ' + (f'{names[0]} put on it' if len(names) == 1 else f'{len(names)} things put on it'))
    c.commit()
    return jsonify(layout_dict(c, layout_row(c, lid), True) | {'added': [f['id'] for f in made]}), 201      # added: the new things' ids, in the order sent (offline.js follows a thing put on with no connection by it)

@app.route('/api/layouts/items/<int:iid>', methods=['PUT', 'DELETE'])
def layout_item_one(iid):
    """PUT moves or changes one thing ({x, y, z, w, d, h, name, shape, locked, size_locked, notes, hours, dim_pct}, any of them). DELETE takes it off
    the layout. History gets a line when a thing is put on a layout or taken off it, and not for each move: a drawing is moved about
    a great deal. A plant's height (h) is saved on its page too (layout_plant_height)."""
    c = db(); layout_tables(c)
    it = c.execute('SELECT * FROM layout_items WHERE id=?', (iid,)).fetchone()
    if it is None: abort(404, 'That is not on the layout any more')
    L = layout_row(c, it['layout_id'], True); who = editor()
    if request.method == 'DELETE':
        c.execute('DELETE FROM layout_items WHERE id=?', (iid,)); layout_touch(c, L['id'], who)
        audit_only(c, 'where', 'layout_item', it['name'], None, who, f'Layout "{L["name"]}": {it["name"]} taken off it'); c.commit()
        return jsonify(ok=True)
    b = request.get_json(silent=True) or {}
    f = layout_item_fields(c, L, b, it)
    if it['plant_code'] or it['light_id'] or it['spot_id']: f['name'] = it['name']          # its name is the record's
    ch = [k for k in f if it[k] != f[k]]
    if ch:
        c.execute('UPDATE layout_items SET ' + ','.join(f'{k}=?' for k in ch) + ',updated_by=?,updated_at=? WHERE id=?', [f[k] for k in ch] + [who, now(), iid])
        layout_touch(c, L['id'], who)      # who moved it last and when is kept on the thing and on the layout; History is not given a line for every move
    if it['plant_code'] and ('h' in b or 'page_h' in b): layout_plant_height(c, L, it, b, f['h'], who)
    if it['kind'] == 'light' and ('hours' in ch or 'dim_pct' in ch): layout_light_to_spots(c, L, iid, who)
    c.commit()
    return jsonify(item=layout_item_dict(c, c.execute('SELECT * FROM layout_items WHERE id=?', (iid,)).fetchone()))

@app.route('/api/layouts/<int:lid>/record', methods=['POST'])
def layout_record(lid):
    """Moves plants in the record: {moves: [{plant: code, place: a shelf's id, or minus a room's or area's id}]}. Each plant must be
    drawn on this layout. The page works out where the drawing puts each plant (lyRecord) and sends it here when the person says
    "Move it here in the record"; Undo sends the places they came from. Every move is checked before any is made, and each is a
    change to the plant like one made on its own page: a new version, a line in its History, and the home limit.
    Answers {moved: [{plant, name, from, from_label, to, to_label, changed}], layout}."""
    c = db(); layout_tables(c)
    L = layout_row(c, lid, True); who = editor()
    moves = (request.get_json(silent=True) or {}).get('moves')
    if not isinstance(moves, list) or not moves or len(moves) > 400: abort(400, 'Say which plants to move')
    drawn = {r[0] for r in c.execute('SELECT plant_code FROM layout_items WHERE layout_id=? AND plant_code IS NOT NULL', (lid,))}
    todo = []
    for m in moves:
        m = m if isinstance(m, dict) else {}
        code = str(m.get('plant') or '').strip().upper()
        if code not in drawn: abort(400, f'{code or "That plant"} is not on this layout')
        r = plant_row(c, code)
        if r['status'] != 'active': abort(400, f'{code} is archived')
        try: pid = int(m.get('place'))
        except (TypeError, ValueError): abort(400, 'Say which room or shelf to move it to')
        sp, area = place_rows(c, pid)
        if area is None: abort(400, 'That room or shelf is not in the list any more')
        home_check_new(c, area['home_id'])
        todo.append((r, pid, sp, area))
    out = []
    for r, pid, sp, area in todo:
        was = layout_pid(r); label = place_label(c, pid)
        _, changed = apply_changes(c, r, {'home_id': area['home_id'], 'area_id': area['id'], 'spot_id': sp['id'] if sp is not None else None}, who, 'update',
                                   f'Moved to {label} (from the layout "{L["name"]}")')
        out.append({'plant': r['code'], 'name': r['common_name'], 'from': was, 'from_label': place_label(c, was), 'to': pid, 'to_label': label, 'changed': changed})
    c.commit()
    return jsonify(moved=out, layout=layout_dict(c, layout_row(c, lid), True))

# ---------------------------------------------------------------- the light on a layout, for Grow lights
# The same sums as the page's lyLight() (js/layouts.js), so that Grow lights, which shows them, and the Layouts page agree to the
# tenth of a mol/m² a day; lightsread_check.py compares the two. Keep them in step.
LY_EPS = 0.01
def _ly_r1(x): return math.floor(x * 10 + 0.5) / 10          # as JavaScript's Math.round, not Python's round half to even
def _ly_clamp(v, lo, hi): return max(lo, min(hi, v))
def _ly_round(it): return it['shape'] == 'round' and abs(it['w'] - it['d']) < 0.05
def _ly_plan(a, b):
    ra, rb = _ly_round(a), _ly_round(b)
    if ra and rb: return math.hypot(a['x'] + a['w'] / 2 - b['x'] - b['w'] / 2, a['y'] + a['d'] / 2 - b['y'] - b['d'] / 2) - (a['w'] + b['w']) / 2
    if ra or rb:
        cc, q = (a, b) if ra else (b, a); r = cc['w'] / 2; cx, cy = cc['x'] + r, cc['y'] + r
        dist = math.hypot(cx - _ly_clamp(cx, q['x'], q['x'] + q['w']), cy - _ly_clamp(cy, q['y'], q['y'] + q['d']))
        return dist - r if dist > 0 else -(r + min(cx - q['x'], q['x'] + q['w'] - cx, cy - q['y'], q['y'] + q['d'] - cy))
    dx = max(a['x'] - b['x'] - b['w'], b['x'] - a['x'] - a['w']); dy = max(a['y'] - b['y'] - b['d'], b['y'] - a['y'] - a['d'])
    return math.hypot(max(dx, 0), max(dy, 0)) if dx > 0 or dy > 0 else max(dx, dy)
def _ly_levels(b): return [v for v in (b.get('levels') or []) if v['z'] <= b['h'] + 0.05] if b['kind'] == 'shelf' else []
def _ly_solids(b):
    lv, t = _ly_levels(b), b.get('board_in') or LAYOUT_BOARD_IN
    return [{'z': b['z'] + v['z'] - t, 'h': t} for v in lv] if lv else [{'z': b['z'], 'h': b['h']}]
def _ly_stands(items, a):
    """Is it standing on the floor or on something (and so not hanging)?"""
    if abs(a['z']) < 0.05: return True
    return any(b['id'] != a['id'] and b['kind'] not in ('zone', 'light', 'window') and _ly_plan(a, b) < -LY_EPS and any(abs(q['z'] + q['h'] - a['z']) < 0.05 for q in _ly_solids(b)) for b in items)
def _ly_in_plan(b, x, y):
    if _ly_round(b): return math.hypot(x - b['x'] - b['w'] / 2, y - b['y'] - b['d'] / 2) <= b['w'] / 2 + LY_EPS
    return b['x'] - LY_EPS <= x <= b['x'] + b['w'] + LY_EPS and b['y'] - LY_EPS <= y <= b['y'] + b['d'] + LY_EPS

def _ly_cross(q, parts, a, b):
    """Does the straight line from a to b ((x, y, z) each) go through one of q's parts ([{z, h}]), over the stretch of the line at
    that part's height (all of it, for a level line at that height)? Not counting its two ends."""
    for p in parts:
        z0, z1 = a[2], b[2]
        if abs(z1 - z0) < LY_EPS:
            if not (p['z'] - LY_EPS <= z0 <= p['z'] + p['h'] + LY_EPS): continue
            t0, t1 = 0.0, 1.0
        else:
            lo, hi = max(p['z'], min(z0, z1)), min(p['z'] + p['h'], max(z0, z1))
            if hi - lo < LY_EPS: continue
            t0, t1 = sorted(((lo - z0) / (z1 - z0), (hi - z0) / (z1 - z0)))
        t0, t1 = max(t0, 0.02), min(t1, 0.98)
        if t1 < t0: continue
        if _ly_seg_plan(q, a, b, t0, t1): return True
    return False

def _ly_seg_plan(q, a, b, t0, t1):
    """Does the stretch t0 to t1 of the line from a to b go over q, seen from above? Exactly, so a thin board is not missed (lySegPlan)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    if _ly_round(q):
        cx, cy = q['x'] + q['w'] / 2, q['y'] + q['d'] / 2; l2 = dx * dx + dy * dy
        t = min(t1, max(t0, ((cx - a[0]) * dx + (cy - a[1]) * dy) / l2 if l2 > 1e-12 else t0))
        return math.hypot(a[0] + dx * t - cx, a[1] + dy * t - cy) <= q['w'] / 2 + LY_EPS
    lo, hi = t0, t1
    for s0, d, mn, mx in ((a[0], dx, q['x'] - LY_EPS, q['x'] + q['w'] + LY_EPS), (a[1], dy, q['y'] - LY_EPS, q['y'] + q['d'] + LY_EPS)):
        if abs(d) < 1e-12:
            if s0 < mn or s0 > mx: return False
            continue
        u, v = (mn - s0) / d, (mx - s0) / d
        lo, hi = max(lo, min(u, v)), min(hi, max(u, v))
        if lo > hi: return False
    return True

def _ly_blk(L):
    """A layout's shade: (how much a pot blocks, how much leaves block), in percent."""
    g = L.get if isinstance(L, dict) else (lambda k, d=None: d)
    return (LAYOUT_POT_BLOCK if g('pot_block') is None else g('pot_block'), LAYOUT_LEAF_BLOCK if g('leaf_block') is None else g('leaf_block'))

def _ly_pot_h(q):
    """How tall a drawn plant's pot is (lyPotH): the layout's own height, else its pot's in Pots and trays, else LAYOUT_POT_TALL of its
    width to the nearest half inch. Never more than the plant."""
    v = q.get('pot_h') if q.get('pot_h') is not None else q.get('pot_rec')
    if v is None: v = max(0.5, math.floor(min(q['w'], q['d']) * LAYOUT_POT_TALL * 2 + 0.5) / 2)
    return min(v, q['h'])

def _ly_shade(items, skip, a, b, blk=(LAYOUT_POT_BLOCK, LAYOUT_LEAF_BLOCK)):
    """The plants the line from a to b goes through (lyShade): [{q, pot, k}]. A plant's pot is the bottom pot_h of its box and blocks
    blk[0] percent; its leaves are the rest and block blk[1]. A line through both counts the part that blocks more; k is the share
    of the light it lets through."""
    out = []
    for q in items:
        if q['kind'] != 'plant' or q.get('gone') or q['id'] == skip: continue
        ph = _ly_pot_h(q); hits = []
        if ph > LY_EPS and _ly_cross(q, [{'z': q['z'], 'h': ph}], a, b): hits.append((True, blk[0]))
        if q['h'] - ph > LY_EPS and _ly_cross(q, [{'z': q['z'] + ph, 'h': q['h'] - ph}], a, b): hits.append((False, blk[1]))
        if hits:
            pot, pct = hits[0]
            for x in hits[1:]:
                if x[1] > pct: pot, pct = x
            out.append({'q': q, 'pot': pot, 'k': 1 - pct / 100})
    return out

def _ly_through(shade):
    """The share of the light that gets past everything in shade (lyThrough)."""
    k = 1.0
    for x in shade: k *= x['k']
    return k

def _ly_shade_names(shade): return [x['q']['name'] + ("'s pot" if x['pot'] else '') for x in shade]

def _ly_win_wall(L, w):
    """The wall a window is in: the nearest (lyWinWall)."""
    ds = [('back', w['y']), ('left', w['x']), ('right', L['width_in'] - w['x'] - w['w']), ('front', L['depth_in'] - w['y'] - w['d'])]
    return min(ds, key=lambda x: x[1])[0]

def _ly_day(L, w):
    """A window's daylight at the glass (lyDay): its own, else its home's for the way it faces (window_dli)."""
    if w.get('day_dli') is not None: return w['day_dli']
    return ((L.get('window_dli') if isinstance(L, dict) else None) or LAYOUT_WINDOW_DLI).get(w.get('facing') or 'S', 0)

def layout_day_on(L, items, pl, w, blk=None):
    """What one window gives one plant's top (lyDayOn): its daylight at the glass, less with the angle and with the distance (half as much
    LAYOUT_WIN_FALL_IN away), none through a board or other solid thing, and less through each plant in the way. None when the plant
    is not in front of it."""
    cx, cy, top = pl['x'] + pl['w'] / 2, pl['y'] + pl['d'] / 2, pl['z'] + pl['h']
    wall = _ly_win_wall(L, w)
    if wall in ('back', 'front'): nx, ny, qx, qy = 0, (1 if wall == 'back' else -1), _ly_clamp(cx, w['x'], w['x'] + w['w']), (w['y'] + w['d'] if wall == 'back' else w['y'])
    else: nx, ny, qx, qy = (1 if wall == 'left' else -1), 0, (w['x'] + w['w'] if wall == 'left' else w['x']), _ly_clamp(cy, w['y'], w['y'] + w['d'])
    qz = _ly_clamp(top, w['z'], w['z'] + w['h'])
    dx, dy, dz = cx - qx, cy - qy, top - qz
    depth = dx * nx + dy * ny
    if depth <= LY_EPS: return None
    dist = math.sqrt(dx * dx + dy * dy + dz * dz); f = dist / LAYOUT_WIN_FALL_IN
    out = {'w': w, 'dist': round(dist, 2), 'dli': _ly_day(L, w) * (depth / dist) / (1 + f * f), 'by': None, 'shade': []}
    a, b = (qx, qy, qz), (cx, cy, top)
    out['by'] = next((q for q in items if q is not pl and q['kind'] in ('shelf', 'other') and _ly_cross(q, _ly_solids(q), a, b)), None)
    if not out['by']:
        out['shade'] = _ly_shade(items, pl.get('id'), a, b, blk or _ly_blk(L))
        out['dli'] *= _ly_through(out['shade'])
    return out

def layout_light_on(items, pl, li, blk=(LAYOUT_POT_BLOCK, LAYOUT_LEAF_BLOCK)):
    """What one drawn light gives one drawn plant (lyLightOn): {up, side, dli, by (something in the way), nofig}, or None when the
    light is not above the plant's top."""
    top = pl['z'] + pl['h']; src = li['z'] + li['h'] if _ly_stands(items, li) else li['z']; up = src - top
    if up <= LY_EPS: return None
    cx, cy = pl['x'] + pl['w'] / 2, pl['y'] + pl['d'] / 2
    if _ly_round(li):
        mx, my = li['x'] + li['w'] / 2, li['y'] + li['d'] / 2; off = math.hypot(cx - mx, cy - my); k = li['w'] / 2 / off if off > li['w'] / 2 else 1
        sx, sy = mx + (cx - mx) * k, my + (cy - my) * k
    else: sx, sy = _ly_clamp(cx, li['x'], li['x'] + li['w']), _ly_clamp(cy, li['y'], li['y'] + li['d'])
    side = math.hypot(cx - sx, cy - sy); dist = math.hypot(up, side)
    out = {'li': li, 'up': round(up, 2), 'side': round(side, 2), 'dli': 0.0, 'par': 0.0, 'by': None, 'nofig': False}
    if not li.get('pts'): return out | {'nofig': True}
    near = li.get('near_in') or 3
    par = (_loglog([(p[0], p[1]) for p in li['pts']], max(dist, near)) or 0) * (up / dist) ** 2
    out['par'] = par                                     # at full brightness, while it is on: Best setting varies the hours and brightness
    out['dli'] = par * (100 if li.get('dim_pct') is None else li['dim_pct']) / 100 * (12 if li.get('hours') is None else li['hours']) * 0.0036
    for b in items:
        if b is li or b is pl or b['kind'] not in ('shelf', 'other'): continue
        for q in _ly_solids(b):
            lo, hi = max(q['z'], top), min(q['z'] + q['h'], src)
            if hi - lo < LY_EPS: continue
            t = ((lo + hi) / 2 - top) / up
            if _ly_in_plan(b, cx + (sx - cx) * t, cy + (sy - cy) * t): out['by'] = b; break
        if out['by']: break
    out['shade'] = [] if out['by'] else _ly_shade(items, pl.get('id'), (sx, sy, src), (cx, cy, top), blk)      # 1.58.0: a plant or a pot in the way blocks some
    if out['shade']: k = _ly_through(out['shade']); out['par'] *= k; out['dli'] *= k
    return out

def layout_swap(L, light_id, Ln):
    """The layout with every drawn light `light_id` given light row Ln's figures instead (Compare lights: "Try it"), drawn the same
    size and in the same place, with its own hours, and its brightness or the next step up that Ln has. Returns (layout, notes)."""
    d = light_specs(Ln); pts = [[x, y, a] for x, y, a in light_points(d)]
    dims = sorted({int(x) for x in (d.get('dimming') or [100]) if 0 < int(x) <= 100} | {100})
    notes = set()
    def sw(it):
        if it['kind'] != 'light' or it.get('light_id') != light_id: return it
        dim = 100 if it.get('dim_pct') is None else it['dim_pct']
        if dim not in dims:
            new = min((x for x in dims if x >= dim), default=100); notes.add(f'It has no {dim}% setting, so this is at {new}%.'); dim = new
        return it | {'pts': pts, 'near_in': light_range(pts)[0] if pts else None, 'name': Ln['name'], 'dim_pct': dim}
    return L | {'items': [sw(it) for it in L['items']]}, sorted(notes)

def layout_try(c, lid, light_id, Ln):
    """Compare lights: each plant drawn on layout `lid`, with its light there now and with every drawn `light_id` swapped for Ln."""
    r = c.execute('SELECT * FROM layouts WHERE id=?', (lid,)).fetchone()
    if not r: return None
    L = layout_dict(c, r); now, _ = layout_light(L); Ls, notes = layout_swap(L, light_id, Ln); new, _ = layout_light(Ls)
    word = lambda x: LIGHT_VERDICT.get(x['verdict'], 'No light reaches it')
    rows = []
    for it in L['items']:
        if it['kind'] != 'plant' or not it['plant'] or it['gone'] or it['id'] not in now: continue
        a, b = now[it['id']], new[it['id']]
        if not (a['reached'] or b['reached']): continue
        n = it.get('need') or {}
        rows.append({'code': it['plant'], 'name': it['name'], 'item': it['id'], 'lo': n.get('lo'), 'hi': n.get('hi'),
                     'now_dli': a['dli'], 'now_verdict': a['verdict'], 'now_word': word(a), 'new_dli': b['dli'], 'new_verdict': b['verdict'], 'new_word': word(b)})
    return {'id': L['id'], 'name': L['name'], 'pid': L['pid'], 'place': L.get('place'), 'rows': rows, 'notes': notes,
            'drawn': sum(1 for it in L['items'] if it['kind'] == 'light' and it.get('light_id') == light_id and not it['gone'])}

def layout_light(L):
    """Each drawn plant's light on a layout (lyLight): {item id: {dli, verdict, reached, on: [...], parts, shut}}, and whether any
    drawn light has its maker's figures. parts: every drawn light that shines on it unblocked, with its light at full brightness
    (par), whatever its hours; shut: the names of lights something stands in the way of."""
    items = L['items']; lights = [b for b in items if b['kind'] == 'light' and not b.get('gone')]; out = {}
    wins = [b for b in items if b['kind'] == 'window']
    if not lights and not wins: return out, False
    blk = _ly_blk(L)
    for pl in items:
        if pl['kind'] != 'plant': continue
        alls = [x for x in (layout_light_on(items, pl, li, blk) for li in lights) if x]
        on = sorted((x for x in alls if not x['nofig'] and not x['by'] and x['dli'] >= 0.05), key=lambda x: -x['dli'])
        days = [x for x in (layout_day_on(L, items, pl, w, blk) for w in wins) if x]
        day = sum(x['dli'] for x in days if not x['by']); lsum = sum(x['dli'] for x in on)
        dli = _ly_r1(lsum + day); reached = _ly_r1(lsum) >= 1 or any(x['side'] < 0.05 for x in on); lit = reached or _ly_r1(day) >= 1; need = pl.get('need')
        shade = sorted({n for x in alls + days for n in _ly_shade_names(x.get('shade') or [])})
        out[pl['id']] = {'dli': dli, 'reached': reached, 'verdict': (light_verdict(dli, need['lo'], need['hi']) if need else 'unknown') if lit else 'none', 'on': on,
                         'day': _ly_r1(day), 'wins': [{'name': x['w']['name'], 'dli': _ly_r1(x['dli']), 'dist': x['dist']} for x in sorted(days, key=lambda x: -x['dli']) if not x['by'] and x['dli'] >= 0.05],
                         'shade': shade,
                         'parts': [{'light_id': x['li'].get('light_id'), 'item': x['li']['id'], 'par': x['par']} for x in alls if not x['nofig'] and not x['by']],
                         'shut': [x['li']['name'] for x in alls if x['by'] and not x['nofig']]}
    return out, any(li.get('pts') for li in lights)

def layout_reading(L, it, x):
    """What Grow lights is told about one drawn plant: its light there, the light that gives the most of it (with how far under
    it and to the side), and the parts Best setting needs."""
    on = [{'light_id': o['li'].get('light_id'), 'name': o['li']['name'], 'up': round(o['up'], 1), 'side': round(o['side'], 1), 'dli': _ly_r1(o['dli'])} for o in x['on']]
    return {'lid': L['id'], 'lname': L['name'], 'pid': L['pid'], 'item': it['id'], 'name': it['name'], 'here': it.get('rec') is not None and it.get('rec') == L['pid'],
            'dli': x['dli'], 'verdict': x['verdict'], 'reached': x['reached'], 'on': on, 'parts': x['parts'], 'shut': x['shut'], 'day': x.get('day', 0), 'wins': x.get('wins', []), 'shade': x.get('shade', [])}

def layout_lights_for_grow(c):
    """For Grow lights (LIGHTS_FROM_LAYOUTS): the lights drawn on a layout of a place (the first of each light on it), and each plant
    drawn on a layout whose lights have figures, with its light there."""
    if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='layout_items'").fetchone(): return {}
    layout_tables(c)
    lights, plants, seen, lit = [], {}, set(), []
    for r in c.execute('SELECT * FROM layouts ORDER BY id').fetchall():
        L = layout_dict(c, r); pid = L['pid']
        for it in L['items']:
            if it['kind'] == 'light' and it['light_id'] and not it['gone'] and pid is not None and (pid, it['light_id']) not in seen:
                seen.add((pid, it['light_id']))
                lights.append({'pid': pid, 'light_id': it['light_id'], 'hours': it['hours'], 'dim_pct': it['dim_pct'], 'lid': L['id'], 'lname': L['name'], 'item': it['id']})
        m, figs = layout_light(L)
        if not figs: continue
        lit.append({'id': L['id'], 'name': L['name'], 'pid': pid})
        for it in L['items']:
            x = m.get(it['id']) if it['kind'] == 'plant' and it['plant'] and not it['gone'] else None
            if x: plants.setdefault(it['plant'], []).append(layout_reading(L, it, x))
    return {'lights': lights, 'plants': plants, 'layouts': lit}
LIGHTS_FROM_LAYOUTS.append(layout_lights_for_grow)

def layout_light_to_spots(c, L, iid, who):
    """A drawn light's hours or brightness changed: the light spots of the layout's place with that light take them, for the layout
    is the one place they are set (Ethan, November 16, 2026). Only from the first of that light on the layout, the one Grow lights reads."""
    it = c.execute('SELECT * FROM layout_items WHERE id=?', (iid,)).fetchone(); pid = layout_pid(L)
    if it is None or not it['light_id'] or pid is None: return
    first = c.execute("SELECT id FROM layout_items WHERE layout_id=? AND kind='light' AND light_id=? ORDER BY sort, id LIMIT 1", (L['id'], it['light_id'])).fetchone()
    if not first or first[0] != iid: return
    for s in c.execute('SELECT * FROM light_spots WHERE light_id=? AND place_id=?', (it['light_id'], pid)).fetchall():
        if (s['hours'], s['dim_pct']) == (it['hours'], it['dim_pct']): continue
        c.execute('UPDATE light_spots SET hours=?, dim_pct=?, updated_by=?, updated_at=? WHERE id=?', (it['hours'], it['dim_pct'], who, now(), s['id']))
        audit_only(c, 'light', 'light_spot', f"{s['hours']:g} hours a day, {s['dim_pct']}%", f"{it['hours']:g} hours a day, {it['dim_pct']}%", who,
                   f'Grow light spot "{s["name"]}": hours and brightness set on the layout "{L["name"]}"')
