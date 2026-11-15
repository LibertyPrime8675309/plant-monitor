"""Prototype (proto/missing-details): missing details. Several pages need a detail about a plant to work for it: grow-light spacing
needs the pot size, the coming-inside checklist the leaf type, a shelf the height, the frost alert the coldest it can take, the
feeding calendar the months. A plant without it is quietly left out or gets a guess. This lists, detail by detail, the active plants
at the place in use that do not have it yet, and what each one is for, so they can be filled in one after another.

Nothing new is stored: filling a detail in is an ordinary page edit (PUT /api/plants/<code>), with its version, audit row and undo."""
from .core import *   # noqa: F401,F403

# key, the plant fields it covers, the title, what it is for (plain words), how it is filled in on the page ('enum', 'length',
# 'temp', 'days' inline; 'edit' opens the plant's Edit page)
MISSING_DETAILS = [
    ('pot_size', ('pot_size',), 'Pot size',
     'Grow lights work out how much room each pot takes from it, and the coming-inside checklist uses it to say whether a pot can be soaked.', 'enum'),
    ('leaf_type', ('leaf_type',), 'Leaf type',
     'The coming-inside checklist rates each way of cleaning off pests by it, and the repotting plan uses it.', 'enum'),
    ('height_in', ('height_in',), 'Height with its pot',
     'A shelf or a grow light spot uses it to say whether the plant fits under it.', 'length'),
    ('temp_damage_below', ('temp_damage_below',), 'Coldest it can take',
     'The frost alert and the cold-night checklist leave out a plant without it.', 'temp'),
    ('water', ('water_every_days', 'soil_moisture_low'), 'How often to check for water',
     'Without it, Water checks it every 7 days, the usual for a potted plant, and does not know whether it likes to dry out.', 'days'),
    ('feed', ('fert_from_month', 'fert_to_month', 'fert_every_days'), 'Feeding months',
     'The feeding calendar and Today\'s Feed list need the months to feed and how often.', 'edit'),
    ('pet_safety', ('pet_safety',), 'Safety for pets',
     'The pets filter on All plants and the Safety for pets line on its page use it.', 'enum'),
    # November 15, 2026 (his answer): two more. A date acquired is not one of them yet: no page has a field for it.
    ('light', ('light_summary',), 'Light',
     'Its page has no Light line without it, so nothing says how much sun or shade it wants.', 'text'),
    ('pot_mix', (), 'Potting mix',
     'What is in each pot works out how much water and air a pot holds from its mix. A pot with no mix written down is left out.', 'page'),
]
MISSING_LATER_DAYS = 30                 # "Not now" hides a plant from one list for this long

def missing_of(r, has_mix=True):
    """Pure: the keys of the details this plant row (a dict or sqlite Row) does not have yet. `has_mix`: a mix is written down for its pot."""
    get = lambda f: r[f] if f in r.keys() else None
    empty = lambda f: get(f) is None or str(get(f)).strip() == ''
    out = []
    for key, fields, _t, _w, _how in MISSING_DETAILS:
        if key == 'water':
            if (get('grow_kind') or '') in ('Semi-hydro', 'Water only'): continue      # those have their own rhythm (top up / fresh water)
            if empty('water_every_days') and empty('soil_moisture_low'): out.append(key)
        elif key == 'feed':
            if (get('fert_strength') or '') == 'None needed': continue
            if any(empty(f) for f in fields): out.append(key)
        elif key == 'pot_mix':
            if (get('grow_kind') or '') == 'Water only': continue                      # a plant in water has no mix
            if not has_mix: out.append(key)
        elif key == 'leaf_type':
            if (get('grow_kind') or '') == 'Water only': continue                      # a plant in water needs no leaf type for the checklist
            if empty(key): out.append(key)
        elif empty(fields[0]): out.append(key)
    return out

def missing_report(c, code=None):
    at, at_args = plants_at(c, location(c))
    if code: at, at_args = ' AND code=?', [code]
    rows = c.execute("SELECT * FROM plants WHERE status='active'" + at + ' ORDER BY code', at_args).fetchall()
    photo = lambda pid: (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (pid,)).fetchone() or [None])[0]
    by = {k[0]: [] for k in MISSING_DETAILS}; off = {k[0]: [] for k in MISSING_DETAILS}
    mixed = {x[0] for x in c.execute('SELECT DISTINCT plant_code FROM pot_mixes')}
    later, today = missing_later(c), local_today(c).isoformat()
    plants_with = 0
    for r in rows:
        keys = missing_of(r, r['code'] in mixed)
        now_keys = [k for k in keys if later.get(f"{r['code']}:{k}", '') <= today]          # the rest were put off with "Not now"
        for k in keys:
            if k not in now_keys: off[k].append(r['code'])
        if not now_keys: continue
        plants_with += 1
        p = {'code': r['code'], 'name': r['common_name'], 'photo': photo(r['id']), 'version': r['version'], 'site': r['site'] or ''}
        for k in now_keys: by[k].append(p)
    details = [{'key': k, 'fields': list(f), 'title': t, 'why': w, 'how': how, 'options': ENUMS.get(k, []), 'plants': by[k], 'later': len(off[k])}
               for k, f, t, w, how in MISSING_DETAILS]
    return {'plants': len(rows), 'plants_with': plants_with, 'gaps': sum(len(d['plants']) for d in details), 'details': details, 'later_days': MISSING_LATER_DAYS}

def missing_later(c):
    """{"P-006:height_in": "2026-12-15"}: the day each put-off detail comes back. Kept as one setting; days that have passed are dropped when it is next saved."""
    try: d = json.loads(setting(c, 'missing_later', '') or '{}')
    except ValueError: d = {}
    return d if isinstance(d, dict) else {}

@app.route('/api/missing')
def missing_api():
    """GET: the details each active plant at the place in use is missing, detail by detail. ?plant=CODE for one plant."""
    return jsonify(missing_report(db(), request.args.get('plant') or None))

@app.route('/api/missing/later', methods=['POST', 'DELETE'])
def missing_later_api():
    """POST {plant, key}: "Not now" - leave this plant off this detail's list for MISSING_LATER_DAYS days (you do not know it yet).
    DELETE {key}: show the ones put off for that detail again (at the place in use). Nothing on a plant's page changes."""
    c = db(); b = request.get_json(silent=True) or {}
    key = str(b.get('key') or '')
    if key not in {k[0] for k in MISSING_DETAILS}: abort(400, 'key must be one of the details on the list')
    d, today = missing_later(c), local_today(c)
    d = {k: v for k, v in d.items() if v > today.isoformat()}
    if request.method == 'POST':
        r = plant_row(c, str(b.get('plant') or ''))                  # also stops an editor limited to other homes
        d[f"{r['code']}:{key}"] = (today + timedelta(days=MISSING_LATER_DAYS)).isoformat()
    else:
        at, at_args = plants_at(c, location(c))
        for (code,) in c.execute("SELECT code FROM plants WHERE status='active'" + at, at_args).fetchall():
            if f'{code}:{key}' in d: home_check(c, code); d.pop(f'{code}:{key}')
    set_setting(c, 'missing_later', json.dumps(d, sort_keys=True)); c.commit()
    return jsonify(missing_report(c))
