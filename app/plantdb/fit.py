"""Lights that fit the room (PLAN.md step 8, 1.56.0).

Every grow light holds itself in the room in its own way (Ethan, November 9, 2026): bulbs screw into a socket on a lamp, a clamp
or a cord; the tripod stands on the floor and cannot point straight down; the 2 ft standing light lights sideways; clamp lights
need a horizontal edge; strips screw under a shelf, which a one-level table does not have. The Grow lights page knew the light's
PAR and the plants' needs, but not whether the light could be put where the plants are. Three small records fill that in:

- a light's *mount* (in lights.data['mount']): how it holds, with a few numbers (MOUNT_KINDS, mount_clean, mount_words);
- a room's or shelf's *place sheet* (areas.sheet, spots.sheet, JSON): what is above it, its width and depth, free room
  beside it, an edge to clamp to, an outlet; and its photos (place_photos);
- a plant's height now, pot included (plants.height_in, a plant field).

fit_check() compares them before the light is counted, and says in plain sentences whether the light fits there, what is
missing if not, which plants are too tall for the level, and which a sideways light would leave in shade. When something it
needs is not known it says "Not checked" with what to fill in, never a Fits it cannot back. Each spot then has a setup card to
print and a "Set up and checked" tick (light_spots.checked_*), which clears itself when the spot's light, place or plants change."""
import hashlib
from .core import *   # noqa: F401,F403

ORDER = 60

# ---------------------------------------------------------------- 8a. how a light holds
MOUNT_KINDS = {
    'socket': 'Screws into a bulb socket',
    'floor': 'Stands on the floor',
    'surface': 'Stands on a shelf or table',
    'clamp': 'Clamps to an edge',
    'under': 'Screws under a shelf',
    'hang': 'Hangs from something above',
    'none': 'Nothing to mount (a room light)',
}
POINTS = {'down': 'straight down', 'angled': 'at an angle, not straight down', 'side': 'sideways'}
# What a bulb screws into, chosen on the spot; each holds the bulb the way one of the kinds above does
HOLDERS = {'clamp': ('a clamp lamp', 'clamp'), 'base': ('a lamp with a base', 'surface'), 'cord': ('a socket on a cord, hung up', 'hang')}
MOUNT_NUMS = {'footprint_in': 'Base across', 'height_lo': 'Lowest height', 'height_hi': 'Highest height', 'grip_in': 'Thickest edge it grips',
              'reach_in': 'Arm reach', 'length_in': 'Length', 'width_in': 'Width'}

def mount_clean(m):
    """A mount from a form or a batch, checked: {kind, points, footprint_in, height_lo, height_hi, grip_in, reach_in, length_in, width_in, socket}."""
    if not m: return None
    if not isinstance(m, dict): abort(400, 'The mount must be a set of values')
    kind = m.get('kind') or ''
    if kind == '': return None
    if kind not in MOUNT_KINDS: abort(400, 'Choose how the light holds: ' + ', '.join(v.lower() for v in MOUNT_KINDS.values()))
    out = {'kind': kind}
    pts = m.get('points') or ('side' if kind == 'surface' else 'down')
    if pts not in POINTS: abort(400, 'Choose which way it points: straight down, at an angle, or sideways')
    out['points'] = pts
    for k, label in MOUNT_NUMS.items():
        v = m.get(k)
        if v in (None, ''): continue
        try: x = round(float(v), 1)
        except (TypeError, ValueError): abort(400, f'{label} must be a number of inches')
        if not 0 < x <= 240: abort(400, f'{label} must be between 0 and 240 inches')
        out[k] = x
    if kind == 'socket': out['socket'] = str(m.get('socket') or 'E26')[:12]
    if kind == 'clamp' and m.get('pot_rim') in (True, 1, '1', 'yes', 'true'): out['pot_rim'] = True      # the pot clip: also clips onto a pot's rim
    return out

def mount_words(m, u=None):
    """One sentence for a light's card: how it holds and where it can go."""
    if not m: return ''
    L = lambda x: len_text(x, u)
    k, p = m['kind'], POINTS.get(m.get('points') or 'down')
    if k == 'socket': return f"Screws into an {m.get('socket') or 'E26'} socket: a clamp lamp, a lamp with a base, or a socket on a cord. Each spot says which."
    if k == 'floor':
        hs = f", {L(m['height_lo'])} to {L(m['height_hi'])} tall" if m.get('height_lo') and m.get('height_hi') else (f", up to {L(m['height_hi'])} tall" if m.get('height_hi') else '')
        return f"Stands on the floor{', base ' + L(m['footprint_in']) + ' across' if m.get('footprint_in') else ''}{hs}; points {p}."
    if k == 'surface':
        return f"Stands on a shelf or table{', base ' + L(m['footprint_in']) + ' across' if m.get('footprint_in') else ''}{', ' + L(m['height_hi']) + ' tall' if m.get('height_hi') else ''}; lights {p}."
    if k == 'clamp':
        g = f" up to {L(m['grip_in'])} thick" if m.get('grip_in') else ''
        return f"Clamps to a horizontal edge{g}{', or the rim of a pot' if m.get('pot_rim') else ''}{'; its arm reaches about ' + L(m['reach_in']) if m.get('reach_in') else ''}. A clamp on an upright surface can slip."
    if k == 'under': return f"Screws under a shelf or other surface{' at least ' + L(m['length_in']) + ' long' if m.get('length_in') else ''}, pointing down."
    if k == 'hang': return 'Hangs from something above the plants: a shelf, a hook or the ceiling.'
    return 'A room light: nothing to mount.'

def light_mount(L):
    return (light_specs(L) or {}).get('mount') if L is not None else None

# ---------------------------------------------------------------- 8b. what a room or shelf offers
SHEET_NUMS = {'levels': ('Levels', 1, 20), 'gap_in': ('Clear height between levels', 1, 240), 'width_in': ('Width of a level', 1, 600),
              'depth_in': ('Depth of a level', 1, 240), 'top_in': ('Clear height above the top level', 1, 240), 'free_in': ('Free surface beside the plants', 0, 600),
              'floor_in': ('Free floor beside it', 0, 600), 'edge_in': ('Thickness of the edge', 0.1, 12), 'ceiling_in': ('Ceiling height', 24, 400)}
SHEET_CHOICES = {'top': ('nothing', 'ceiling', 'other'), 'edge': ('yes', 'no'), 'socket': ('yes', 'no')}

def sheet_clean(b):
    out = {}
    for k, (label, lo, hi) in SHEET_NUMS.items():
        v = b.get(k)
        if v in (None, ''): continue
        try: x = round(float(v), 1)
        except (TypeError, ValueError): abort(400, f'{label} must be a number')
        if not lo <= x <= hi: abort(400, f'{label} must be between {lo:g} and {hi:g}')
        out[k] = int(x) if k == 'levels' else x
    for k, opts in SHEET_CHOICES.items():
        v = b.get(k)
        if v in (None, ''): continue
        if v not in opts: abort(400, f'Choose one of: {", ".join(opts)}')
        out[k] = v
    g = b.get('gaps_in')                      # 1.56.0: a clear height for each lower level, from the bottom ("23, 13, 27")
    if g not in (None, '', []):
        nums = g if isinstance(g, list) else re.findall(r'\d+(?:\.\d+)?', str(g))
        try: gs = [round(float(x), 1) for x in nums]
        except (TypeError, ValueError): abort(400, 'The height of each level must be numbers')
        if any(not 1 <= x <= 240 for x in gs): abort(400, 'The height of each level must be between 1 and 240')
        lv = out.get('levels')
        if lv and len(gs) != lv - 1: abort(400, f'A shelf with {lv} levels has {lv - 1} under another level: give {lv - 1} heights, from the bottom (the top level has open space or the "Above the top level" choice)')
        if gs: out['gaps_in'] = gs
    n = str(b.get('notes') or '').strip()[:400]
    if n: out['notes'] = n
    return out

def level_word(lvl):
    """'top' / 'lower' / 'L2' -> 'the top level' / 'a lower level' / 'level 2 from the bottom'."""
    if lvl == 'top': return 'the top level'
    if lvl == 'lower': return 'a lower level'
    if re.fullmatch(r'L\d{1,2}', lvl or ''): return f'level {lvl[1:]} from the bottom'
    return ''

def level_gap(s, lvl):
    """Clear height over a lower level: its own (gaps_in, from the bottom) when known, else the shelf's one gap_in."""
    gs = s.get('gaps_in') or []
    if re.fullmatch(r'L\d{1,2}', lvl or ''):
        i = int(lvl[1:]) - 1
        if i < len(gs): return gs[i]
    return s.get('gap_in')

def sheet_of(row):
    try: d = json.loads(row['sheet'] or '{}') if row is not None and 'sheet' in row.keys() else {}
    except ValueError: d = {}
    return d if isinstance(d, dict) else {}

def place_rows(c, pid):
    """(the spot row or None, its room's row) for a light place id (a spot's id, or minus a room's id)."""
    if not pid: return None, None
    if pid < 0: return None, c.execute('SELECT * FROM areas WHERE id=?', (-pid,)).fetchone()
    sp = c.execute('SELECT * FROM spots WHERE id=?', (pid,)).fetchone()
    return sp, (c.execute('SELECT * FROM areas WHERE id=?', (sp['area_id'],)).fetchone() if sp else None)

def sheet_words(s, u=None):
    """The measurements in one line, for a card."""
    if not s: return ''
    L = lambda x: len_text(x, u); bits = []
    if s.get('levels'):
        gs = s.get('gaps_in') or []
        each = (', ' + ', '.join(L(x) for x in gs[:-1]) + ' and ' + L(gs[-1]) if len(gs) > 1 else ', ' + L(gs[0])) + ' clear from the bottom up' if gs else ''
        bits.append('one level' if s['levels'] == 1 else f"{s['levels']} levels" + (each or (f", {L(s['gap_in'])} between them" if s.get('gap_in') else '')))
    if s.get('width_in') or s.get('depth_in'): bits.append(' by '.join(L(x) for x in (s.get('width_in'), s.get('depth_in')) if x) + (' (width by depth)' if s.get('width_in') and s.get('depth_in') else ''))
    if s.get('top') == 'nothing': bits.append('nothing above the top')
    elif s.get('top') == 'ceiling': bits.append('the ceiling above the top' + (f", {L(s['top_in'])} clear" if s.get('top_in') else ''))
    elif s.get('top_in'): bits.append(f"{L(s['top_in'])} clear above the top")
    if s.get('ceiling_in'): bits.append(f"ceiling {L(s['ceiling_in'])} high")
    if s.get('free_in') is not None: bits.append(f"{L(s['free_in'])} free beside the plants")
    if s.get('floor_in') is not None: bits.append(f"{L(s['floor_in'])} of free floor beside it")
    if s.get('edge') == 'yes': bits.append('an edge to clamp to' + (f" ({L(s['edge_in'])} thick)" if s.get('edge_in') else ''))
    elif s.get('edge') == 'no': bits.append('no edge to clamp to')
    if s.get('socket') == 'yes': bits.append('an outlet within reach')
    elif s.get('socket') == 'no': bits.append('no outlet within reach')
    return '; '.join(bits)

def place_words(c, pid):
    sp, room = place_rows(c, pid)
    row = sp if sp is not None else room
    return sheet_words(sheet_of(row)) if row is not None else ''

# ---------------------------------------------------------------- 8d. fits or does not
FIT_WORD = {'fits': 'Fits', 'nofit': 'Does not fit', 'tall': 'Too tall for the level', 'shaded': 'Shaded', 'point': 'Cannot point straight down',
            'unchecked': 'Not checked', 'note': 'Note'}
FIT_STATUS = {'fits': 'Fits', 'nofit': 'Does not fit', 'unchecked': 'Not checked yet'}

def fit_check(mount, light_name, place, spot_sheet, room_sheet, level, holder, distance_in, plants, others=None, u=None):
    """Whether a light can be put where a spot is, before its light is counted.

    mount: the light's mount (or None); place: the place's name (or None when the spot has no place); spot_sheet / room_sheet:
    the shelf's and the room's measurements; level: 'top' | 'lower' | '' (on a shelf with several levels); holder: what a bulb
    screws into ('clamp' | 'base' | 'cord' | ''); plants: [{code, name, height_in}]; others: [(name, mount)] of your other
    lights, to name one that would fit. Returns {status: fits | nofit | unchecked, word, lines: [{kind, word, text}]}."""
    L = lambda x: len_text(x, u)
    lines = []
    add = lambda kind, text: lines.append({'kind': kind, 'word': FIT_WORD[kind], 'text': text})
    s = dict(room_sheet or {}); s.update({k: v for k, v in (spot_sheet or {}).items()})       # the shelf's own values first
    stack = (s.get('levels') or 1) > 1
    lvl = level if stack else 'top'
    if re.fullmatch(r'L\d{1,2}', lvl or '') and int(lvl[1:]) >= (s.get('levels') or 1): lvl = 'top'     # its highest level is the top
    uneven = len(set(s.get('gaps_in') or [])) > 1
    named = lvl in ('top', 'lower') or bool(re.fullmatch(r'L\d{1,2}', lvl or ''))
    there = ('the ' + place.split(', ', 1)[1]) if place and ', ' in place else (place or 'this spot')     # "the Side Table", or a room's own name
    There = there[:1].upper() + there[1:]

    def above():
        """('shelf' | 'ceiling' | None, clear inches or None, known): what is over the plants at this level."""
        if lvl == 'lower' or lvl.startswith('L'): return 'shelf', level_gap(s, lvl) or (min(s['gaps_in']) if s.get('gaps_in') else None), True
        if lvl == 'top':
            if s.get('top') == 'nothing': return None, None, True
            if s.get('top') == 'ceiling': return 'ceiling', s.get('top_in') or (room_sheet or {}).get('ceiling_in'), True
            if s.get('top') == 'other': return 'shelf', s.get('top_in'), True
            if s.get('top_in'): return 'shelf', s.get('top_in'), True
        return None, None, False

    if not mount: add('unchecked', f'Say how the {light_name} holds (on its card under Your lights, "How it holds").')
    elif not place: add('unchecked', 'Choose where this spot is, a room or a shelf, so the app can see whether the light fits there.')
    elif not any(k != 'notes' for k in s): add('unchecked', f'Add the measurements of {there} (Rooms and shelves on this page, "Measurements and photos").')
    elif stack and not named: add('unchecked', f'{There} has {s["levels"]} levels. Say which one this spot is on.')
    elif lvl == 'lower' and uneven: add('unchecked', f'The levels of {there} are not all the same height. Say which level this spot is on, counting from the bottom.')
    else:
        m = dict(mount); kind = m['kind']; how = ''
        if kind == 'socket':
            if holder not in HOLDERS: add('unchecked', f'Say what the {light_name} screws into here: a clamp lamp, a lamp with a base, or a socket on a cord.'); kind = None
            else: how, kind = HOLDERS[holder]; m['points'] = 'down'
        where_above, clear, known = above()
        if kind in ('under', 'hang'):
            what = 'a strip' if kind == 'under' else 'it'
            if not known: add('unchecked', f'Say what is above {there}{" on its top level" if stack else ""}.')
            elif where_above is None:
                alt = [n for n, om in (others or []) if om and om.get('kind') in ('floor', 'clamp')]
                add('nofit', f'{There} has nothing above {"its top level" if stack else "it"}, so {what} has nowhere to be fixed. '
                    f'A light that stands on the floor beside it or clamps to its edge would reach it{" (" + ", ".join(alt[:2]) + ")" if alt else ""}.')
            elif where_above == 'ceiling' and clear and clear > 36:
                add('nofit', f'The ceiling is {L(clear)} above {there}: {what} fixed there would be too far from the leaves. A shelf or a stand closer to them would do.')
            elif kind == 'under' and m.get('length_in') and s.get('width_in') and m['length_in'] > s['width_in'] + 0.5:
                alt = [n for n, om in (others or []) if om and om.get('kind') == 'under' and om.get('length_in') and om['length_in'] <= s['width_in'] + 0.5]
                add('nofit', f'{There}{"’s levels are" if stack else " is"} {L(s["width_in"])} wide; the {light_name} needs {L(m["length_in"])}.' + (f' The {alt[0]} fits.' if alt else ''))
            elif kind == 'under' and m.get('length_in') and not s.get('width_in'):
                add('unchecked', f'The {light_name} needs a surface {L(m["length_in"])} long; add the width of {there}.')
            else:
                add('fits', f'{"It screws under" if kind == "under" else ("The bulb in " + how + " hangs from" if how else "It hangs from")} the {"shelf above" if where_above == "shelf" else "ceiling"}'
                    + (f' ({L(s["width_in"])} wide; it needs {L(m["length_in"])})' if kind == 'under' and m.get('length_in') and s.get('width_in') else '') + '.')
        elif kind == 'clamp':
            if m.get('pot_rim') and s.get('edge') != 'yes':
                add('fits', f'It clips onto the rim of a pot (up to {L(m["grip_in"]) if m.get("grip_in") else "a thin rim"})' + (f'; its arm reaches about {L(m["reach_in"])}' if m.get('reach_in') else '') + '.')
            elif s.get('edge') == 'no': add('nofit', f'{There} has no edge to clamp to. A light that stands beside it, or one that screws under a shelf above, would suit it.')
            elif s.get('edge') != 'yes': add('unchecked', f'Say whether {there} has an edge to clamp to, and how thick it is.')
            elif m.get('grip_in') and s.get('edge_in') and s['edge_in'] > m['grip_in']:
                add('nofit', f'The edge of {there} is {L(s["edge_in"])} thick; the clamp {"of " + how + " " if how else ""}opens to {L(m["grip_in"])}.')
            else:
                add('fits', f'{("The bulb in " + how) if how else "It"} clamps to the edge of {there}' + (f'. Its arm reaches about {L(m["reach_in"])}, so keep the plants within that of the edge' if m.get('reach_in') else '') + '.')
        elif kind == 'floor':
            room = s.get('floor_in')
            if room is None: add('unchecked', f'Add how much free floor there is beside {there}' + (f' (its base is {L(m["footprint_in"])} across)' if m.get('footprint_in') else '') + '.')
            elif m.get('footprint_in') and room < m['footprint_in']: add('nofit', f'There is {L(room)} of free floor beside {there}; the base of the {light_name} needs {L(m["footprint_in"])}.')
            else: add('fits', f'It stands on the floor beside {there}' + (f' ({L(room)} free; its base needs {L(m["footprint_in"])})' if m.get('footprint_in') else '') + '.')
        elif kind == 'surface':
            room = s.get('free_in')
            if room is None: add('unchecked', f'Add how much free surface there is beside the plants on {there}' + (f' (its base is {L(m["footprint_in"])} across)' if m.get('footprint_in') else '') + '.')
            elif m.get('footprint_in') and room < m['footprint_in']: add('nofit', f'{There} has {L(room)} free beside the plants; the base of {how or "the " + light_name} needs {L(m["footprint_in"])}.')
            elif how and where_above == 'shelf' and clear and clear < 14: add('nofit', f'There is {L(clear)} between this level and the one above, too little for {how} with a bulb over the plants.')
            else: add('fits', f'{(how or "it")[:1].upper() + (how or "it")[1:]} stands on {there} beside the plants' + (f' ({L(room)} free; its base needs {L(m["footprint_in"])})' if m.get('footprint_in') else '') + '.')
        elif kind == 'none': add('fits', 'A room light lights the room as it is.')
        if kind and m.get('points') == 'angled':
            add('point', f'The {light_name} cannot point straight down, so stand it beside the plants and angle it in. Its chart is measured straight under it, so the light at the leaves will be a little less.')
        if kind and kind != 'none' and s.get('socket') == 'no': add('note', f'There is no outlet within reach of {there}: it will need an extension cord.')
        # plants against the level and against a sideways light
        known_h = [p for p in plants if p.get('height_in')]
        if where_above in ('shelf', 'ceiling') and clear:
            for p in known_h:
                if p['height_in'] >= clear: add('tall', f'{p["name"]} ({p["code"]}) is {L(p["height_in"])} tall with its pot; the level has {L(clear)} clear.')
                elif kind in ('under', 'hang') and clear - p['height_in'] < 3:
                    add('tall', f'{p["name"]} ({p["code"]}) is {L(p["height_in"])} tall: only {L(clear - p["height_in"])} between its top and the light.')
            if kind in ('under', 'hang') and known_h:
                est = clear - max(p['height_in'] for p in known_h)
                if est >= 3 and distance_in and abs(est - distance_in) > 3:
                    add('note', f'Under this {"shelf" if where_above == "shelf" else "ceiling"} the light will be about {L(est)} above the tallest plant; the spot says {L(distance_in)}. Change the spot to match, so its light is counted right.')
        if kind and (m.get('points') == 'side'):
            lh = m.get('height_hi') or m.get('height_lo')
            if lh and len(known_h) >= 1 and max(p['height_in'] for p in known_h) > lh / 2 and len(plants) > 1:
                tall_p = max(known_h, key=lambda p: p['height_in'])
                order = sorted(known_h, key=lambda p: p['height_in'])
                add('shaded', f'{tall_p["name"]} ({tall_p["code"]}) is {L(tall_p["height_in"])} tall, more than half the light’s {L(lh)}, so plants behind it get less. '
                    + 'Put the shortest nearest the light: ' + ', '.join(f'{p["name"]} ({L(p["height_in"])})' for p in order) + '.')
            elif lh:
                for p in known_h:
                    if p['height_in'] > lh: add('shaded', f'{p["name"]} ({p["code"]}) is taller than the light ({L(lh)}), so its top gets little light from it.')
        missing = [p for p in plants if not p.get('height_in')]
        if missing and (where_above in ('shelf', 'ceiling') or (kind and m.get('points') == 'side')):
            add('note', f'{len(missing)} plant{"s have" if len(missing) != 1 else " has"} no height yet ({", ".join(p["code"] for p in missing[:4])}{"…" if len(missing) > 4 else ""}), so '
                + ('the room under the shelf above' if where_above in ('shelf', 'ceiling') else 'the shade from the light') + ' is not checked for them. Add it on each plant’s page.')
    kinds = {x['kind'] for x in lines}
    status = 'nofit' if kinds & {'nofit', 'tall'} else 'unchecked' if 'unchecked' in kinds else 'fits'
    clear_in = None
    if mount and place and s and not (stack and not named):
        wa, cl, _ = above(); clear_in = cl if wa else None
    return {'status': status, 'word': FIT_STATUS[status], 'lines': lines, 'clear_in': clear_in}

def spot_fit(c, s, L, plants, others=None):
    """fit_check for a light_spots row (or a dict with the same keys) and its light row."""
    get = lambda k: s[k] if k in s.keys() else None
    pid = get('place_id')
    spot_row, room_row = place_rows(c, pid)
    ps = [{'code': r['code'], 'name': r['common_name'], 'height_in': r['height_in'] if 'height_in' in r.keys() else None} for r in plants]
    if others is None:
        others = [(o['name'], light_mount(o)) for o in c.execute('SELECT * FROM lights WHERE count>0 ORDER BY sort, id').fetchall() if L is None or o['id'] != L['id']]
    return fit_check(light_mount(L), L['name'] if L is not None else 'light', place_label(c, pid), sheet_of(spot_row) if spot_row else {},
                     sheet_of(room_row) if room_row else {}, get('level') or '', get('holder') or '', get('distance_in'), ps, others)

# ---------------------------------------------------------------- 8e. set up and checked
def spot_sig(c, s):
    """What the tick was given for: the light, how many, where, the level and holder, the distance and the plants. A change to any
    of them clears the tick (the hours and brightness do not: they change nothing about how it is put together)."""
    codes = sorted(x for (x,) in c.execute('SELECT plant_code FROM light_assign WHERE spot_id=?', (s['id'],)))
    key = json.dumps([s['light_id'], s['units'], s['place_id'], s['level'] or '', s['holder'] or '', float(s['distance_in']), codes])
    return hashlib.sha1(key.encode()).hexdigest()[:16]

def spot_checked(c, s):
    if not s['checked_at']: return None
    if s['checked_sig'] != spot_sig(c, s): return {'stale': True, 'at': s['checked_at'], 'by': s['checked_by'], 'note': s['checked_note'] or ''}
    return {'stale': False, 'at': s['checked_at'], 'by': s['checked_by'], 'note': s['checked_note'] or ''}

@app.route('/api/lights/spots/<int:i>/checked', methods=['POST', 'DELETE'])
def light_spot_checked(i):
    """Set up and checked: {note}. DELETE takes the tick off."""
    c = db()
    s = c.execute('SELECT * FROM light_spots WHERE id=?', (i,)).fetchone()
    if not s: abort(404, 'That spot is not set up any more')
    who = editor()
    if request.method == 'DELETE':
        c.execute('UPDATE light_spots SET checked_at=NULL, checked_by=NULL, checked_sig=NULL WHERE id=?', (i,))
        audit_only(c, 'light', 'light_spot', 'set up and checked', None, who, f'Grow light spot {s["name"]}: tick taken off')
        c.commit(); return jsonify(ok=True)
    note = str((request.get_json(silent=True) or {}).get('note') or '').strip()[:400]
    c.execute('UPDATE light_spots SET checked_at=?, checked_by=?, checked_note=?, checked_sig=? WHERE id=?', (now(), who, note, spot_sig(c, s), i))
    audit_only(c, 'light', 'light_spot', None, 'set up and checked' + (': ' + note if note else ''), who, f'Grow light spot {s["name"]}: set up and checked' + (f' ({note})' if note else ''))
    c.commit()
    return jsonify(ok=True, checked=spot_checked(c, c.execute('SELECT * FROM light_spots WHERE id=?', (i,)).fetchone()))

@app.route('/api/lights/unchecked')
def lights_unchecked():
    """For Today: spots with plants in them that have not been set up and checked (or were changed since)."""
    c = db(); out = []
    for s in c.execute('SELECT * FROM light_spots ORDER BY id').fetchall():
        if not c.execute('SELECT 1 FROM light_assign WHERE spot_id=? LIMIT 1', (s['id'],)).fetchone(): continue
        ch = spot_checked(c, s)
        if not ch or ch['stale']: out.append({'id': s['id'], 'name': s['name'], 'changed': bool(ch)})
    return jsonify(spots=out, total=c.execute('SELECT COUNT(*) FROM light_spots').fetchone()[0])

# ---------------------------------------------------------------- 8b. place sheets and photos (rooms and shelves)
def place_dict(c, pid):
    sp, room = place_rows(c, pid)
    row = sp if sp is not None else room
    if row is None: abort(404, 'That room or shelf is not in the list')
    col = 'spot_id' if sp is not None else 'area_id'
    photos = [{'id': p['id'], 'file': p['file'], 'caption': p['caption'], 'is_primary': bool(p['is_primary'])}
              for p in c.execute(f'SELECT * FROM place_photos WHERE {col}=? ORDER BY is_primary DESC, id', (row['id'],))]
    return {'id': pid, 'label': place_label(c, pid), 'is_room': sp is None, 'sheet': sheet_of(row), 'words': sheet_words(sheet_of(row)),
            'room_sheet': sheet_of(room) if sp is not None and room is not None else None, 'photos': photos}

def place_photo_map(c):
    """{place id: main photo file} for every room and shelf with a photo (a room's id is minus its id, as on the Grow lights page)."""
    out = {}
    for p in c.execute('SELECT area_id, spot_id, file FROM place_photos ORDER BY is_primary DESC, id DESC'):
        k = p['spot_id'] if p['spot_id'] else -p['area_id']
        out.setdefault(k, p['file'])
    return out

@app.route('/api/rooms/<int(signed=True):pid>', methods=['GET', 'PUT'])
def fit_place_one(pid):
    """A room (minus its id) or a shelf (its id): its measurements and photos. PUT {sheet: {...}} replaces the measurements."""
    c = db()
    if request.method == 'GET': return jsonify(place_dict(c, pid))
    sp, room = place_rows(c, pid)
    if (sp if pid > 0 else room) is None: abort(404, 'That room or shelf is not in the list')
    who = editor()
    new = sheet_clean((request.get_json(silent=True) or {}).get('sheet') or {})
    tbl, rid, old = ('spots', sp['id'], sheet_of(sp)) if pid > 0 else ('areas', room['id'], sheet_of(room))
    c.execute(f'UPDATE {tbl} SET sheet=? WHERE id=?', (json.dumps(new) if new else '', rid))
    if new != old: audit_only(c, 'where', 'place_sheet', sheet_words(old) or None, sheet_words(new) or None, who, f'Measurements of {place_label(c, pid)} changed')
    c.commit()
    return jsonify(place_dict(c, pid))

@app.route('/api/rooms/<int(signed=True):pid>/photos', methods=['POST'])
def fit_place_photos_add(pid):
    c = db(); who = editor()
    sp, room = place_rows(c, pid)
    if (sp if pid > 0 else room) is None: abort(404, 'That room or shelf is not in the list')
    files = request.files.getlist('files')
    if not files: abort(400, 'Choose a photo')
    aid, sid = (room['id'], sp['id']) if pid > 0 else (room['id'], None)
    has = c.execute('SELECT 1 FROM place_photos WHERE ' + ('spot_id=?' if sid else 'spot_id IS NULL AND area_id=?') + ' AND is_primary=1', (sid or aid,)).fetchone()
    cap = str(request.form.get('caption', '')).strip()[:200]
    for i, f in enumerate(files):
        name = save_image(f)
        c.execute('INSERT INTO place_photos(area_id,spot_id,file,caption,is_primary,added_by,added_at) VALUES(?,?,?,?,?,?,?)', (aid, sid, name, cap, 0 if has or i else 1, who, now()))
    audit_only(c, 'where', 'place_photo', None, f'{len(files)} photo(s)', who, f'Photo added to {place_label(c, pid)}'); c.commit()
    return jsonify(place_dict(c, pid)), 201

@app.route('/api/rooms/photos/<int:ph>', methods=['PUT', 'DELETE'])
def fit_place_photo_one(ph):
    """DELETE removes a photo; PUT {primary: true} makes it the main one."""
    c = db(); who = editor()
    p = c.execute('SELECT * FROM place_photos WHERE id=?', (ph,)).fetchone()
    if not p: abort(404, 'That photo is not there any more')
    pid = p['spot_id'] if p['spot_id'] else -p['area_id']
    same = ('spot_id=?', p['spot_id']) if p['spot_id'] else ('spot_id IS NULL AND area_id=?', p['area_id'])
    if request.method == 'PUT':
        c.execute(f'UPDATE place_photos SET is_primary=0 WHERE {same[0]}', (same[1],)); c.execute('UPDATE place_photos SET is_primary=1 WHERE id=?', (ph,))
        audit_only(c, 'where', 'place_photo', None, p['file'], who, f'Main photo of {place_label(c, pid)} changed'); c.commit()
        return jsonify(place_dict(c, pid))
    c.execute('DELETE FROM place_photos WHERE id=?', (ph,))
    try: os.remove(os.path.join(PHOTO_DIR, p['file']))
    except OSError: pass
    if p['is_primary']: c.execute(f'UPDATE place_photos SET is_primary=1 WHERE id=(SELECT MIN(id) FROM place_photos WHERE {same[0]})', (same[1],))
    audit_only(c, 'where', 'place_photo', p['file'], None, who, f'Photo removed from {place_label(c, pid)}'); c.commit()
    return jsonify(place_dict(c, pid))
