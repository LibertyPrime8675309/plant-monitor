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
]

def missing_of(r):
    """Pure: the keys of the details this plant row (a dict or sqlite Row) does not have yet."""
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
    by = {k[0]: [] for k in MISSING_DETAILS}
    plants_with = 0
    for r in rows:
        keys = missing_of(r)
        if not keys: continue
        plants_with += 1
        p = {'code': r['code'], 'name': r['common_name'], 'photo': photo(r['id']), 'version': r['version'], 'site': r['site'] or ''}
        for k in keys: by[k].append(p)
    details = [{'key': k, 'fields': list(f), 'title': t, 'why': w, 'how': how, 'options': ENUMS.get(k, []), 'plants': by[k]}
               for k, f, t, w, how in MISSING_DETAILS]
    return {'plants': len(rows), 'plants_with': plants_with, 'gaps': sum(len(d['plants']) for d in details), 'details': details}

@app.route('/api/missing')
def missing_api():
    """GET: the details each active plant at the place in use is missing, detail by detail. ?plant=CODE for one plant."""
    return jsonify(missing_report(db(), request.args.get('plant') or None))
