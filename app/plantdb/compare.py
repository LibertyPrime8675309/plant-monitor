"""Compare lights (PLAN.md step 10, 1.56.0).

Ethan is buying more grow lights (November 10, 2026) and wants the ones he has and the ones he is considering side by side, in a
table he can search, sort and filter. Every light model already holds its maker's PPFD chart (lights.data['ppfd']), but makers
measure at different distances, so the table works each light out at one distance the person picks (compare_row), and says
"beyond the maker's chart" where a chart does not reach rather than stretching it. Where each light's numbers come from is a column
of its own ("Maker's figures", "Claude's estimate", or "Doubtful" with the reason), so a guess is never quietly ranked first.

A light has a status (lights.status): owned, considering, or no longer used. A light that is not owned has a count of 0, so it
is left out of the suggested layout and the spot dialog. "Add a light you are considering" takes what a listing gives, through the
same light record batches and "Add a light" write; "Bought it" turns it into an owned light without retyping; "Try it in a spot"
shows what each plant in one of your spots would get from it, against what it gets now and what it needs, and whether it fits there
(fit.py). Prices (with the date, since prices move) can go on any light."""
from .core import *   # noqa: F401,F403

ORDER = 64            # after lights.py and where.py (50) and fit.py (60)

LIGHT_STATUS = {'owned': 'Owned', 'considering': 'Considering', 'retired': 'No longer used'}
COMPARE_AT = (6, 12, 18, 24)              # inches; the page shows them in the person's units
COMPARE_HOURS = (8, 10, 12, 14, 16)
SQFT_M2 = 0.09290304
SLACK = 0.06                              # a distance this close to the ends of a chart counts as on it (rounding: 7.87 in is 20 cm)
DIRECTIONS = {'down': 'Down', 'side': 'Sideways', 'angled': 'At an angle'}

def chart_span(pts):
    return (pts[0][0], pts[-1][0]) if pts else (None, None)

def on_chart(pts, d):
    lo, hi = chart_span(pts)
    return lo is not None and lo * (1 - SLACK) <= d <= hi * (1 + SLACK)

def beyond_words(pts):
    if not pts: return 'No light figures'
    lo, hi = chart_span(pts)
    if len(pts) == 1: return f"Beyond the maker's chart: one figure, at {lo:g} in"
    return f"Beyond the maker's chart ({lo:g} to {hi:g} in)"

def first_num(x):
    """'97+', 'about 98', 'over 80' -> 97, 98, 80; for sorting by CRI."""
    m = re.search(r'\d+(?:\.\d+)?', str(x or ''))
    return float(m.group()) if m else None

def light_source(d):
    """('maker' | 'estimate' | 'doubtful', words)."""
    if d.get('doubtful'): return 'doubtful', 'Doubtful: ' + str(d['doubtful'])
    if d.get('estimated'): return 'estimate', "Claude's estimate"
    return 'maker', "Maker's figures" + (', area estimated' if d.get('area_estimated') else '')

def compare_row(L, used, at, hours):
    """One light worked out at `at` inches and `hours` a day. Pure apart from the row it is given."""
    d = light_specs(L)
    pts = light_points(d)
    here = on_chart(pts, at)
    p = ppfd_at(pts, at) if here else None
    has_area = any(a for _, _, a in pts)
    a = area_at(pts, at) if here and has_area else None
    ppf = p * a * SQFT_M2 if p and a else None                     # µmol/s landing in the lit area: rough
    watts = d.get('watts')
    price = d.get('price')
    src, src_words = light_source(d)
    sp = d.get('spectrum') or {}
    m = d.get('mount') or {}
    status = L['status'] if 'status' in L.keys() and L['status'] else 'owned'
    dims = sorted({int(x) for x in (d.get('dimming') or [100]) if 0 < int(x) <= 100} | {100})
    return {
        'id': L['id'], 'key': L['lkey'], 'name': L['name'], 'brand': d.get('brand') or '', 'kind': d.get('kind') or '', 'model': d.get('model') or '',
        'status': status, 'status_word': LIGHT_STATUS.get(status, status), 'count': L['count'], 'in_use': used,
        'watts': watts, 'lumens': d.get('lumens'),
        'ppfd': round(p) if p else None, 'area_sqft': round(a, 1) if a else None, 'dli': dli_of(p, hours) if p else None,
        'beyond': None if here else beyond_words(pts), 'chart': [[x, y] for x, y, _ in pts],
        'per_watt': round(ppf / watts, 2) if ppf and watts else None,
        'price': price, 'price_on': d.get('price_on') or '', 'url': d.get('url') or '',
        'per_light': round(price / ppf * 100, 2) if price and ppf else None,       # dollars for each 100 µmol/s at this distance
        'kelvin': d.get('kelvin'), 'cri': d.get('cri') or '', 'cri_num': first_num(d.get('cri')),
        'red': sp.get('red'), 'blue': sp.get('blue'),
        'direction': d.get('direction') or (m.get('points') if m else None) or '',
        'dimmable': len(dims) > 1, 'dimming': dims,
        'timer': d.get('timer') or '', 'timer_repeats': bool(d.get('timer_repeats')), 'timer_keeps': d.get('timer_keeps'),
        'needs_socket': bool(d.get('needs_socket')), 'size': d.get('size') or '',
        'mount_kind': m.get('kind') or '', 'mount_words': mount_words(m) if m else '',
        'source': src, 'source_words': src_words, 'photo': d.get('photo'), 'notes': L['notes'] or '',
    }

def compare_rows(c, at, hours):
    used = {}
    for lid, u in c.execute('SELECT light_id, SUM(units) FROM light_spots GROUP BY light_id'): used[lid] = u
    return [compare_row(L, used.get(L['id'], 0), at, hours) for L in c.execute('SELECT * FROM lights ORDER BY sort, id').fetchall()]

def light_status_set(c, L, status, who, count=None, on=None):
    """Owned, considering or no longer used. Not owned means a count of 0, so a light still in a spot cannot leave."""
    if status not in LIGHT_STATUS: abort(400, 'Choose owned, considering or no longer used')
    d = light_specs(L)
    if status != 'owned':
        n = c.execute('SELECT COUNT(*) FROM light_spots WHERE light_id=?', (L['id'],)).fetchone()[0]
        if n: abort(409, f'"{L["name"]}" is used by {n} spot{"s" if n != 1 else ""}. Change or remove those spots first.')
        count = 0
    elif count is None: count = max(1, L['count'])
    if status == 'owned' and L['status'] != 'owned':
        d['bought_on'] = on or local_today(c).isoformat()
    c.execute('UPDATE lights SET status=?, count=?, data=?, updated_by=?, updated_at=? WHERE id=?', (status, count, json.dumps(d), who, now(), L['id']))
    words = {'owned': f'Bought: {L["name"]} ({count})', 'considering': f'Considering: {L["name"]}', 'retired': f'No longer used: {L["name"]}'}[status]
    audit_only(c, 'light', 'light', LIGHT_STATUS.get(L['status'], L['status']), LIGHT_STATUS[status], who, 'Grow light ' + words[0].lower() + words[1:])

@app.route('/api/lights/compare')
def lights_compare():
    """Every light at one distance: ?at=12 (inches) &hours=12."""
    c = db()
    at = _num(request.args, 'at', 1, 120, 'Distance (inches)') or 12
    hours = _num(request.args, 'hours', 1, 24, 'Hours a day') or 12
    return jsonify(at=at, hours=hours, rows=compare_rows(c, at, hours), choices=list(COMPARE_AT), hours_choices=list(COMPARE_HOURS),
                   statuses=LIGHT_STATUS, directions=DIRECTIONS, mount_kinds=MOUNT_KINDS,
                   spots=[{'id': s['id'], 'name': s['name']} for s in c.execute('SELECT id, name FROM light_spots ORDER BY name COLLATE NOCASE')])

@app.route('/api/lights/<int:i>/status', methods=['POST'])
def light_status(i):
    """{status: owned|considering|retired, count?, on?}: "Bought it" is {status: 'owned', count, on}."""
    c = db()
    L = c.execute('SELECT * FROM lights WHERE id=?', (i,)).fetchone()
    if not L: abort(404, 'That light is not in your list')
    b = request.get_json(silent=True) or {}
    count = _num(b, 'count', 1, 100, 'How many you bought')
    on = str(b.get('on') or '')[:10] or None
    if on:
        try: on = date.fromisoformat(on)
        except ValueError: abort(400, 'The date it was bought must be a date')
        if on > local_today(c): abort(400, 'The date it was bought cannot be in the future')
        on = on.isoformat()
    light_status_set(c, L, str(b.get('status') or ''), editor(), int(count) if count else None, on)
    c.commit()
    return jsonify(ok=True)

@app.route('/api/lights/<int:i>/try')
def light_try(i):
    """?spot=ID: what each plant in that spot would get from light i, at the spot's distance, hours and brightness."""
    c = db()
    L = c.execute('SELECT * FROM lights WHERE id=?', (i,)).fetchone()
    if not L: abort(404, 'That light is not in your list')
    try: sid = int(request.args.get('spot') or 0)
    except ValueError: abort(400, 'Choose one of your spots')
    s = c.execute('SELECT * FROM light_spots WHERE id=?', (sid,)).fetchone()
    if not s: abort(404, 'That spot is not in your list')
    L0 = c.execute('SELECT * FROM lights WHERE id=?', (s['light_id'],)).fetchone()
    ps = [r for r in (c.execute('SELECT * FROM plants WHERE code=?', (x,)).fetchone() for (x,) in c.execute('SELECT plant_code FROM light_assign WHERE spot_id=? ORDER BY plant_code', (sid,))) if r]
    d = light_specs(L)
    pts = light_points(d)
    dims = sorted({int(x) for x in (d.get('dimming') or [100]) if 0 < int(x) <= 100} | {100})
    s2 = dict(s)
    notes = []
    if s['dim_pct'] not in dims:
        s2['dim_pct'] = min((x for x in dims if x >= s['dim_pct']), default=100)
        notes.append(f"It has no {s['dim_pct']}% setting, so this is at {s2['dim_pct']}%.")
    if pts and not on_chart(pts, s['distance_in']):
        notes.append(f"The spot is {s['distance_in']:g} in from the leaves, outside the maker's figures ({chart_span(pts)[0]:g} to {chart_span(pts)[1]:g} in), so its light there is stretched from the nearest ones: a rough guess.")
    if not pts: notes.append('It has no light figures yet, so its light cannot be worked out.')
    src, src_words = light_source(d)
    if src != 'maker': notes.append(f'Its figures: {src_words}.')
    if not d.get('mount') and L['status'] != 'owned':
        notes.append("How it holds is not known for a light you are considering, so whether it fits is not checked; the listing's photos usually show it.")
    now_ev = spot_eval(c, s, L0, ps) if L0 is not None else None
    new_ev = spot_eval(c, s2, L, ps)
    rows = []
    for k, p in enumerate(new_ev['plants']):
        n0 = now_ev['plants'][k] if now_ev else None
        rows.append({'code': p['code'], 'name': p['name'], 'lo': p['lo'], 'hi': p['hi'],
                     'now_verdict': n0['verdict'] if n0 else 'unknown', 'now_word': n0['verdict_word'] if n0 else LIGHT_VERDICT['unknown'],
                     'new_verdict': p['verdict'], 'new_word': p['verdict_word']})
    return jsonify(light={'id': L['id'], 'name': L['name'], 'status': L['status']},
                   spot={'id': s['id'], 'name': s['name'], 'light': L0['name'] if L0 else '', 'units': s['units'], 'distance_in': s['distance_in'],
                         'hours': s['hours'], 'dim_pct': s['dim_pct'], 'place': place_label(c, s['place_id'])},
                   now={'dli': now_ev['dli'] if now_ev else None, 'ppfd': now_ev['ppfd'] if now_ev else None, 'area_sqft': now_ev['area_sqft'] if now_ev else None},
                   new={'dli': new_ev['dli'], 'ppfd': new_ev['ppfd'], 'area_sqft': new_ev['area_sqft'], 'dim_pct': s2['dim_pct'], 'crowded': new_ev['crowded']},
                   plants=rows, fit=spot_fit(c, s2, L, ps), notes=notes)
