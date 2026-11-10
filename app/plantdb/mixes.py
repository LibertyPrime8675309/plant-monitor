"""What is in each pot (PLAN.md step 9, 1.57.0).

A plant's care sheet says what mix its species wants, and the care log says when it was repotted; until now nothing said what
went into the pot, or how the pot grows. Ethan has pots in soil mixes, pots in clay pebbles or perlite (semi-hydro) and, later,
plants in water only; he mixes by parts with a scoop and would like recipes (November 10, 2026).

- Amendments (table `amendments`): each with its grades, a role (a part of a mix, an additive, a semi-hydro medium) and its
  properties on a relative scale shown in words (holds water, lets air in, how long it lasts, feeds, pH effect, weight), with
  a source. Seeded by batch C5; editors can add and change them.
- Recipes (`mix_recipes`, `mix_parts`): parts by volume, with an estimated summary of the whole mix (mix_summary).
- Each pot (`pot_mixes`): the mix as it was the day it went in (a snapshot, so changing a recipe never rewrites history), with
  an optional top and bottom layer; the newest row is what the plant is in now. Plants have a growing kind (`grow_kind`: soil
  mix, semi-hydro, water only), what holds their water (`reservoir`) and the mix their species wants (`mix_wants`, also a fact).
- Care that fits: semi-hydro and water-only plants leave the watering countdown (care.water_report gives them a top-up or a
  water change instead), and get their own rhythms here: Flushed (semi-hydro, weekly to start), Checked the roots (water only).
- What it learns: days between waterings for each recipe, a warning when a pot's mix does not suit what the species wants,
  and the repotting plan bringing forward a pot whose mix breaks down sooner (repotting.py)."""
from .core import *   # noqa: F401,F403
from .care import CARE_KINDS

ORDER = 62
CARE_KINDS.update({'topup': 'Topped up the reservoir', 'flush': 'Flushed', 'waterchange': 'Changed the water', 'rootcheck': 'Checked the roots'})
AM_ROLES = {'part': 'A part of a mix', 'additive': 'An additive (a pinch)', 'medium': 'A semi-hydro medium'}
SCALE = ['low', 'some', 'medium', 'high', 'very high']            # holds water, lets air in: 1 to 5
FEEDS = ['none', 'a little', 'rich']                               # 0 to 2
PH = {-1: 'lowers it', 0: 'no change', 1: 'raises it'}
WEIGHT = ['light', 'medium', 'heavy']                              # 1 to 3
AMOUNT = ['little', 'some', 'a fair amount of', 'a lot of', 'a great deal of']     # the same 1 to 5 in a sentence
def am_low(name):
    """A name inside a sentence: 'Clay pebbles (LECA)' -> 'clay pebbles (LECA)', but 'LECA' stays as it is."""
    return name if name[:2].isupper() else name[:1].lower() + name[1:]
SEMI, WATER = 'Semi-hydro', 'Water only'
HYDRO_EVERY = {'topup': 7, 'flush': 7, 'waterchange': 7, 'rootcheck': 30}   # days; Ethan flushes weekly and changes water weekly (Nov 10)
HYDRO_KINDS = {'topup': SEMI, 'flush': SEMI, 'waterchange': WATER, 'rootcheck': WATER}

def hydro_every(c):
    try: d = json.loads(setting(c, 'hydro_every', '{}') or '{}')
    except ValueError: d = {}
    return {k: int(d[k]) if isinstance(d, dict) and str(d.get(k, '')).isdigit() and 1 <= int(d[k]) <= 90 else v for k, v in HYDRO_EVERY.items()}

def grow_kind(r):
    g = (r['grow_kind'] if 'grow_kind' in r.keys() else '') or ''
    if not g and (r['leaf_type'] if 'leaf_type' in r.keys() else '') == 'Grows in water': return WATER
    return g or 'Soil mix'

# ---------------------------------------------------------------- amendments
def am_dict(r):
    try: grades = json.loads(r['grades'] or '[]')
    except ValueError: grades = []
    d = {k: r[k] for k in ('id', 'key', 'name', 'role', 'holds_water', 'airy', 'lasts_months', 'feeds', 'ph', 'weight', 'source', 'notes', 'updated_by', 'updated_at')}
    d['grades'] = grades
    d['words'] = am_words(d)
    return d

def am_words(a):
    bits = []
    if a.get('holds_water'): bits.append(f"holds {AMOUNT[a['holds_water'] - 1]} water")
    if a.get('airy'): bits.append(f"lets in {AMOUNT[a['airy'] - 1]} air")
    if a.get('lasts_months') == 0: bits.append('does not break down')
    elif a.get('lasts_months'): bits.append(f"breaks down in about {months_words(a['lasts_months'])}")
    if a.get('feeds') is not None: bits.append('feeds the plant' if a['feeds'] == 2 else 'feeds a little' if a['feeds'] == 1 else 'no food in it')
    if a.get('ph'): bits.append(f"pH: {PH[a['ph']]}")
    if a.get('weight'): bits.append({1: 'light', 2: 'medium weight', 3: 'heavy'}[a['weight']])
    return ', '.join(bits)

def months_words(m):
    if m < 12: return f'{m} months'
    y = m / 12
    return ('a year' if y == 1 else f'{y:g} years') if m % 6 == 0 else f'{m} months'

def am_clean(b, partial=False):
    out = {}
    name = str(b.get('name') or '').strip()[:80]
    if not partial or 'name' in b:
        if not name: abort(400, 'Give the amendment a name')
        out['name'] = name
    if 'role' in b or not partial:
        role = b.get('role') or 'part'
        if role not in AM_ROLES: abort(400, 'Choose a part of a mix, an additive, or a semi-hydro medium')
        out['role'] = role
    for k, lo, hi in (('holds_water', 1, 5), ('airy', 1, 5), ('feeds', 0, 2), ('ph', -1, 1), ('weight', 1, 3), ('lasts_months', 0, 240)):
        if k not in b: continue
        v = b.get(k)
        if v in (None, ''): out[k] = None; continue
        try: x = int(v)
        except (TypeError, ValueError): abort(400, f'{k} must be a whole number')
        if not lo <= x <= hi: abort(400, f'{k} must be between {lo} and {hi}')
        out[k] = x
    if 'grades' in b:
        g = b.get('grades')
        if isinstance(g, str): g = [x.strip() for x in g.split(',')]
        out['grades'] = json.dumps([str(x).strip()[:40] for x in (g or []) if str(x).strip()][:12])
    for k, n in (('source', 300), ('notes', 600)):
        if k in b: out[k] = str(b.get(k) or '').strip()[:n]
    return out

# ---------------------------------------------------------------- a mix: parts, its summary, whether it suits the plant
def parts_rows(c, parts):
    """[{amendment_id, grade, parts, amount}] -> the same with each amendment's name and properties (from the table as it is now)."""
    ams = {r['id']: r for r in c.execute('SELECT * FROM amendments')}
    out = []
    for p in parts or []:
        a = ams.get(p.get('amendment_id'))
        out.append({'amendment_id': p.get('amendment_id'), 'name': (a['name'] if a else p.get('name')) or 'An amendment that was removed',
                    'grade': p.get('grade') or '', 'parts': p.get('parts'), 'amount': p.get('amount') or '',
                    'role': a['role'] if a else p.get('role', 'part'), 'holds_water': a['holds_water'] if a else None, 'airy': a['airy'] if a else None,
                    'lasts_months': a['lasts_months'] if a else None})
    return out

def mix_summary(rows):
    """An estimate for a whole mix from its parts by volume: holds water and lets air in (each 1 to 5, the share-weighted average
    of the parts that have a value), and how long until it wants freshening (the soonest-breaking part that is a fifth or more of
    it). Additives do not count. Pure."""
    body = [r for r in rows if r.get('role') != 'additive' and r.get('parts')]
    total = sum(float(r['parts']) for r in body)
    if not total: return {'known': False, 'shares': []}
    shares = [{'name': r['name'], 'grade': r.get('grade') or '', 'share': round(100 * float(r['parts']) / total)} for r in body]
    def avg(k):
        have = [(float(r['parts']), r[k]) for r in body if r.get(k)]
        w = sum(x for x, _ in have)
        return round(sum(x * v for x, v in have) / w, 1) if w and w >= total * 0.5 else None      # half the mix or more has a value
    water, air = avg('holds_water'), avg('airy')
    brk = sorted((r['lasts_months'], r['name']) for r in body if r.get('lasts_months') and float(r['parts']) / total >= 0.2)
    lasts = brk[0] if brk else None
    known_lasts = all(r.get('lasts_months') is not None for r in body if float(r['parts']) / total >= 0.2)
    word = lambda x: SCALE[min(4, max(0, round(x) - 1))] if x is not None else None
    out = {'known': water is not None or air is not None, 'shares': shares, 'water': water, 'air': air, 'water_word': word(water), 'air_word': word(air),
           'lasts_months': lasts[0] if lasts else (0 if known_lasts else None), 'lasts_by': lasts[1] if lasts else None}
    w = []
    amt = lambda x: AMOUNT[min(4, max(0, round(x) - 1))]
    if water is not None: w.append(f'holds {amt(water)} water')
    if air is not None: w.append(f'lets in {amt(air)} air')
    if lasts: w.append(f'wants freshening in about {months_words(lasts[0])} (the {am_low(lasts[1])} breaks down)')
    elif known_lasts: w.append('nothing in it breaks down soon')
    out['words'] = ('About: ' + ', '.join(w) + '. An estimate: fine bits fill the gaps between coarse ones, so a real mix does not add up exactly.') if w else ''
    return out

def mix_warning(summary, wants, kind):
    """A plain sentence when a soil mix does not suit what the species wants, or None. Pure."""
    if kind != 'Soil mix' or not wants or not summary or not summary.get('known'): return None
    wat, air = summary.get('water'), summary.get('air')
    if wants == 'Fast-draining' and ((wat is not None and wat >= 3.5) or (air is not None and air <= 2.4)):
        return 'Its species wants a fast-draining mix, and this one holds a lot of water. More bark, pumice or perlite would open it up.'
    if wants == 'Moisture-holding' and ((wat is not None and wat <= 2.2) or (air is not None and air >= 4.3)):
        return 'Its species wants a mix that stays moist, and this one dries fast. More coir, sphagnum or worm castings would hold water longer.'
    if wants == 'Balanced' and wat is not None and (wat >= 4.5 or wat <= 1.6):
        return 'Its species wants a balanced mix, and this one is at an extreme: ' + ('very wet.' if wat >= 4.5 else 'very dry.')
    return None

def mix_wants_of(c, r):
    """The mix the plant's species wants: the plant's own value, else the species fact. (value, where it came from)."""
    if r['mix_wants']: return r['mix_wants'], 'set on this plant'
    sci = r['scientific_name'] or ''
    if sci:
        F = facts_of(c, sci, r['code'])
        if F.get('mix_wants'): return fact_value_out('enum', F['mix_wants']['value']), F['mix_wants']['source']
    return None, None

def pot_dict(c, m):
    if m is None: return None
    try: parts = json.loads(m['parts'] or '[]')
    except ValueError: parts = []
    lay = lambda t: (json.loads(t) if t else None)
    rows = parts_rows(c, parts)
    rec = c.execute('SELECT name FROM mix_recipes WHERE id=?', (m['recipe_id'],)).fetchone() if m['recipe_id'] else None
    return {'id': m['id'], 'mixed_on': m['mixed_on'], 'care_id': m['care_id'], 'recipe_id': m['recipe_id'], 'recipe': rec[0] if rec else None,
            'parts': rows, 'top': lay(m['top']), 'bottom': lay(m['bottom']), 'notes': m['notes'], 'by': m['created_by'],
            'summary': mix_summary(rows), 'words': parts_words(rows)}

def parts_words(rows):
    def one(r):
        g = f" ({r['grade']})" if r.get('grade') else ''
        if r.get('role') == 'additive': return f"plus {am_low(r['name'])}{g}{' (' + r['amount'] + ')' if r.get('amount') else ''}"
        return f"{r['parts']:g} {am_low(r['name'])}{g}" if r.get('parts') else f"{r['name']}{g}"
    body = [r for r in rows if r.get('role') != 'additive' and r.get('parts')]
    if len(body) == 1:                                     # one part only: "all clay pebbles (LECA)", not "1 clay pebbles"
        b = body[0]; g = f" ({b['grade']})" if b.get('grade') else ''
        return ', '.join([f"all {am_low(b['name'])}{g}"] + [one(r) for r in rows if r is not b])
    return ', '.join(one(r) for r in rows)

def current_mix(c, code):
    return c.execute('SELECT * FROM pot_mixes WHERE plant_code=? ORDER BY mixed_on DESC, id DESC LIMIT 1', (code,)).fetchone()

# ---------------------------------------------------------------- what it learns: days between waterings for each recipe
def median(xs):
    xs = sorted(xs); n = len(xs)
    return None if not n else xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2

def recipe_interval(c, rid):
    """Days between waterings of the soil plants whose newest mix is this recipe, from the care log since each went in. Shown once at
    least three plants and six gaps are behind it: {days, plants, since} or {plants, gaps} (not enough yet)."""
    per, since, gaps = [], None, 0
    for m in c.execute('SELECT * FROM pot_mixes WHERE recipe_id=?', (rid,)).fetchall():
        cur = current_mix(c, m['plant_code'])
        if not cur or cur['id'] != m['id']: continue
        r = c.execute("SELECT * FROM plants WHERE code=? AND status='active'", (m['plant_code'],)).fetchone()
        if not r or grow_kind(r) != 'Soil mix': continue
        ds = [date.fromisoformat(d) for (d,) in c.execute("SELECT DISTINCT done_on FROM care_log WHERE plant_code=? AND kind='water' AND done_on>=? ORDER BY done_on", (m['plant_code'], m['mixed_on']))]
        g = [(b - a).days for a, b in zip(ds, ds[1:]) if (b - a).days > 0]
        if not g: continue
        per.append(median(g)); gaps += len(g)
        since = min(since or m['mixed_on'], m['mixed_on'])
    if len(per) >= 3 and gaps >= 6: return {'days': round(median(per)), 'plants': len(per), 'since': since}
    return {'plants': len(per), 'gaps': gaps}

def recipe_dict(c, r, with_plants=True):
    parts = [dict(p) for p in c.execute('SELECT * FROM mix_parts WHERE recipe_id=? ORDER BY sort, id', (r['id'],))]
    rows = parts_rows(c, parts)
    d = {'id': r['id'], 'name': r['name'], 'notes': r['notes'], 'parts': rows, 'summary': mix_summary(rows), 'words': parts_words(rows),
         'updated_by': r['updated_by'] or r['created_by'], 'updated_at': r['updated_at'] or r['created_at']}
    if with_plants:
        d['plants'] = [code for (code,) in c.execute('SELECT DISTINCT plant_code FROM pot_mixes WHERE recipe_id=?', (r['id'],))
                       if (current_mix(c, code) or {'recipe_id': None})['recipe_id'] == r['id']]
        d['interval'] = recipe_interval(c, r['id'])
    return d

def parts_clean(c, parts):
    ids = {r[0] for r in c.execute('SELECT id FROM amendments')}
    out = []
    for i, p in enumerate(parts or []):
        if not isinstance(p, dict): continue
        try: aid = int(p.get('amendment_id'))
        except (TypeError, ValueError): abort(400, 'Choose an amendment for each part')
        if aid not in ids: abort(400, 'One of the parts is not in the list of amendments')
        q = p.get('parts')
        if q in (None, ''): q = None
        else:
            try: q = round(float(q), 2)
            except (TypeError, ValueError): abort(400, 'Parts must be a number, like 2 or 0.5')
            if not 0 < q <= 100: abort(400, 'Parts must be between 0 and 100')
        out.append({'amendment_id': aid, 'grade': str(p.get('grade') or '').strip()[:40], 'parts': q, 'amount': str(p.get('amount') or '').strip()[:60], 'sort': i})
    return out

def layer_clean(c, L):
    if not L or not isinstance(L, dict) or not L.get('amendment_id'): return ''
    try: aid = int(L['amendment_id'])
    except (TypeError, ValueError): abort(400, 'Choose what the layer is')
    a = c.execute('SELECT name FROM amendments WHERE id=?', (aid,)).fetchone()
    if not a: abort(400, 'That layer is not in the list of amendments')
    d = L.get('depth_in')
    if d not in (None, ''):
        try: d = round(float(d), 1)
        except (TypeError, ValueError): abort(400, 'The depth of a layer must be a number')
        if not 0 < d <= 24: abort(400, 'The depth of a layer must be between 0 and 24 inches')
    else: d = None
    return json.dumps({'amendment_id': aid, 'name': a['name'], 'grade': str(L.get('grade') or '').strip()[:40], 'depth_in': d})

# ---------------------------------------------------------------- routes
@app.route('/api/mixes')
def mixes_all():
    c = db()
    return jsonify(amendments=[am_dict(r) for r in c.execute('SELECT * FROM amendments ORDER BY role, name')],
                   recipes=[recipe_dict(c, r) for r in c.execute('SELECT * FROM mix_recipes ORDER BY name')],
                   roles=AM_ROLES, scale=SCALE, feeds=FEEDS, ph={str(k): v for k, v in PH.items()}, weight=WEIGHT,
                   grow_kinds=GROW_KINDS, reservoirs=RESERVOIRS, mix_wants=MIX_WANTS, every=hydro_every(c))

@app.route('/api/mixes/amendments', methods=['POST'])
def mixes_am_add():
    c = db(); who = editor()
    b = am_clean(request.get_json(silent=True) or {})
    if c.execute('SELECT 1 FROM amendments WHERE lower(name)=lower(?)', (b['name'],)).fetchone(): abort(409, f'{b["name"]} is already in the list')
    cols = list(b)
    i = c.execute(f'INSERT INTO amendments({",".join(cols)},created_by,created_at) VALUES({",".join("?" * len(cols))},?,?)', [b[k] for k in cols] + [who, now()]).lastrowid
    audit_only(c, 'mixes', 'amendment', None, b['name'], who, f'Amendment added: {b["name"]}'); c.commit()
    return jsonify(am_dict(c.execute('SELECT * FROM amendments WHERE id=?', (i,)).fetchone())), 201

@app.route('/api/mixes/amendments/<int:i>', methods=['PUT', 'DELETE'])
def mixes_am_one(i):
    c = db(); who = editor()
    r = c.execute('SELECT * FROM amendments WHERE id=?', (i,)).fetchone()
    if not r: abort(404, 'That amendment is not in the list any more')
    if request.method == 'DELETE':
        used = c.execute('SELECT COUNT(*) FROM mix_parts WHERE amendment_id=?', (i,)).fetchone()[0]
        if used: abort(409, f'{r["name"]} is in {used} recipe{"s" if used != 1 else ""}. Take it out of them first.')
        c.execute('DELETE FROM amendments WHERE id=?', (i,))
        audit_only(c, 'mixes', 'amendment', r['name'], None, who, f'Amendment removed: {r["name"]}'); c.commit()
        return jsonify(ok=True)
    b = am_clean(request.get_json(silent=True) or {}, partial=True)
    if not b: return jsonify(am_dict(r))
    c.execute(f'UPDATE amendments SET {",".join(k + "=?" for k in b)}, updated_by=?, updated_at=? WHERE id=?', list(b.values()) + [who, now(), i])
    new = c.execute('SELECT * FROM amendments WHERE id=?', (i,)).fetchone()
    audit_only(c, 'mixes', 'amendment', am_words(am_dict(r)), am_words(am_dict(new)), who, f'Amendment changed: {new["name"]}'); c.commit()
    return jsonify(am_dict(new))

def recipe_save(c, rid, b, who):
    name = str(b.get('name') or '').strip()[:80]
    if not name: abort(400, 'Give the recipe a name')
    if c.execute('SELECT 1 FROM mix_recipes WHERE lower(name)=lower(?) AND id IS NOT ?', (name, rid)).fetchone(): abort(409, f'There is already a recipe called {name}')
    parts = parts_clean(c, b.get('parts'))
    if not any(p['parts'] for p in parts): abort(400, 'A recipe needs at least one part, like 2 parts orchid bark')
    notes = str(b.get('notes') or '').strip()[:600]
    if rid: c.execute('UPDATE mix_recipes SET name=?, notes=?, updated_by=?, updated_at=? WHERE id=?', (name, notes, who, now(), rid))
    else: rid = c.execute('INSERT INTO mix_recipes(name,notes,created_by,created_at) VALUES(?,?,?,?)', (name, notes, who, now())).lastrowid
    c.execute('DELETE FROM mix_parts WHERE recipe_id=?', (rid,))
    for p in parts: c.execute('INSERT INTO mix_parts(recipe_id,amendment_id,grade,parts,amount,sort) VALUES(?,?,?,?,?,?)', (rid, p['amendment_id'], p['grade'], p['parts'], p['amount'], p['sort']))
    return rid

@app.route('/api/mixes/recipes', methods=['POST'])
def mixes_recipe_add():
    c = db(); who = editor()
    rid = recipe_save(c, None, request.get_json(silent=True) or {}, who)
    d = recipe_dict(c, c.execute('SELECT * FROM mix_recipes WHERE id=?', (rid,)).fetchone())
    audit_only(c, 'mixes', 'recipe', None, d['words'], who, f'Recipe added: {d["name"]} ({d["words"]})'); c.commit()
    return jsonify(d), 201

@app.route('/api/mixes/recipes/<int:rid>', methods=['PUT', 'DELETE'])
def mixes_recipe_one(rid):
    c = db(); who = editor()
    r = c.execute('SELECT * FROM mix_recipes WHERE id=?', (rid,)).fetchone()
    if not r: abort(404, 'That recipe is not in the list any more')
    old = recipe_dict(c, r, False)
    if request.method == 'DELETE':
        c.execute('DELETE FROM mix_parts WHERE recipe_id=?', (rid,)); c.execute('DELETE FROM mix_recipes WHERE id=?', (rid,))
        c.execute('UPDATE pot_mixes SET recipe_id=NULL WHERE recipe_id=?', (rid,))       # the pots keep their parts as they were
        audit_only(c, 'mixes', 'recipe', old['words'], None, who, f'Recipe removed: {r["name"]} (pots made with it keep their parts)'); c.commit()
        return jsonify(ok=True)
    recipe_save(c, rid, request.get_json(silent=True) or {}, who)
    d = recipe_dict(c, c.execute('SELECT * FROM mix_recipes WHERE id=?', (rid,)).fetchone())
    audit_only(c, 'mixes', 'recipe', old['words'], d['words'], who, f'Recipe changed: {d["name"]}'); c.commit()
    return jsonify(d)

def plant_mix_state(c, r):
    kind = grow_kind(r)
    cur = pot_dict(c, current_mix(c, r['code']))
    wants, wants_src = mix_wants_of(c, r)
    hist = [pot_dict(c, m) for m in c.execute('SELECT * FROM pot_mixes WHERE plant_code=? ORDER BY mixed_on DESC, id DESC', (r['code'],)).fetchall()]
    return {'code': r['code'], 'grow_kind': kind, 'grow_kind_set': r['grow_kind'] or '', 'reservoir': r['reservoir'] or '', 'mix': cur, 'history': hist[1:],
            'mix_wants': wants, 'mix_wants_source': wants_src, 'warning': mix_warning(cur and cur['summary'], wants, kind) if cur else None,
            'hydro': hydro_state(c, r) if kind != 'Soil mix' else None, 'version': r['version']}

@app.route('/api/mixes/plant/<code>', methods=['GET', 'POST'])
def mixes_plant(code):
    """GET: what the plant is in. POST {mixed_on, recipe_id?, parts, top?, bottom?, notes?, repot?, save_as?}: what it is in now
    (repot: also log Repotted on that date; save_as: also save the parts as a new recipe of that name)."""
    c = db()
    r = c.execute('SELECT * FROM plants WHERE code=?', (code.upper(),)).fetchone()
    if not r: abort(404, 'No plant with that code')
    if request.method == 'GET': return jsonify(plant_mix_state(c, r))
    who = editor(); b = request.get_json(silent=True) or {}
    day = str(b.get('mixed_on') or local_today(c).isoformat())[:10]
    try: dd = date.fromisoformat(day)
    except ValueError: abort(400, 'The date must look like 2026-11-10')
    if dd > local_today(c): abort(400, 'The date cannot be in the future')
    rid = b.get('recipe_id') or None
    if rid and not c.execute('SELECT 1 FROM mix_recipes WHERE id=?', (rid,)).fetchone(): abort(400, 'That recipe is not in the list any more')
    if rid and not b.get('parts'):
        parts = [{'amendment_id': p['amendment_id'], 'grade': p['grade'], 'parts': p['parts'], 'amount': p['amount']} for p in c.execute('SELECT * FROM mix_parts WHERE recipe_id=? ORDER BY sort, id', (rid,))]
    else: parts = parts_clean(c, b.get('parts'))
    if not parts and not b.get('top'): abort(400, 'Say what it is in: choose a recipe, or add the parts')
    snap = [{k: p.get(k) for k in ('amendment_id', 'grade', 'parts', 'amount')} | {'name': x['name'], 'role': x['role']} for p, x in zip(parts, parts_rows(c, parts))]
    if b.get('save_as'):
        rid = recipe_save(c, None, {'name': b['save_as'], 'parts': parts, 'notes': f'Saved from {r["code"]} {r["common_name"]}'}, who)
    care_id = None
    if b.get('repot'):
        care_id = c.execute('INSERT INTO care_log(plant_code,kind,done_on,note,created_by,created_at) VALUES(?,?,?,?,?,?)',
                            (r['code'], 'repot', day, 'With the mix recorded on its page', who, now())).lastrowid
    mid = c.execute('INSERT INTO pot_mixes(plant_code,care_id,mixed_on,recipe_id,parts,top,bottom,notes,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (r['code'], care_id, day, rid, json.dumps(snap), layer_clean(c, b.get('top')), layer_clean(c, b.get('bottom')), str(b.get('notes') or '').strip()[:400], who, now())).lastrowid
    d = pot_dict(c, c.execute('SELECT * FROM pot_mixes WHERE id=?', (mid,)).fetchone())
    audit_only(c, 'mixes', 'pot_mix', None, d['words'], who, f'{"Repotted" if care_id else "What it is in"}: {d["words"] or "a layer only"}' + (f' ({d["recipe"]})' if d['recipe'] else ''), r['id'], r['code'])
    c.commit()
    return jsonify(plant_mix_state(c, r)), 201

@app.route('/api/mixes/pot/<int:i>', methods=['DELETE'])
def mixes_pot_del(i):
    c = db(); who = editor()
    m = c.execute('SELECT * FROM pot_mixes WHERE id=?', (i,)).fetchone()
    if not m: abort(404, 'That entry is not there any more')
    d = pot_dict(c, m)
    c.execute('DELETE FROM pot_mixes WHERE id=?', (i,))
    r = c.execute('SELECT * FROM plants WHERE code=?', (m['plant_code'],)).fetchone()
    audit_only(c, 'mixes', 'pot_mix', d['words'], None, who, f'Mix entry removed ({m["mixed_on"]})', r['id'] if r else None, m['plant_code']); c.commit()
    return jsonify(plant_mix_state(c, r) if r else {'ok': True})

@app.route('/api/mixes/every', methods=['PUT'])
def mixes_every():
    """How often to flush, top up, change the water and check the roots: {kind: days}."""
    c = db(); who = editor(); b = request.get_json(silent=True) or {}
    cur = hydro_every(c)
    for k, v in b.items():
        if k not in HYDRO_EVERY: abort(400, 'Unknown kind of care')
        try: x = int(v)
        except (TypeError, ValueError): abort(400, 'Days must be a whole number')
        if not 1 <= x <= 90: abort(400, 'Days must be between 1 and 90')
        cur[k] = x
    c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('hydro_every',?)", (json.dumps(cur),))
    audit_only(c, 'mixes', 'hydro_every', None, json.dumps(cur), who, 'How often for semi-hydro and water: ' + ', '.join(f'{CARE_KINDS[k].lower()} every {v} days' for k, v in cur.items()))
    c.commit()
    return jsonify(every=cur)

# ---------------------------------------------------------------- care that fits semi-hydro and water only
def hydro_state(c, r, today=None):
    """For a semi-hydro or water-only plant: each of its rhythms, when last done and when next due."""
    kind = grow_kind(r)
    every = hydro_every(c); today = today or local_today(c)
    out = []
    for k, gk in HYDRO_KINDS.items():
        if gk != kind: continue
        alias = {'topup': ('topup', 'flush', 'water'), 'waterchange': ('waterchange', 'water')}.get(k, (k,))
        last = c.execute('SELECT MAX(done_on) FROM care_log WHERE plant_code=? AND kind IN (%s)' % ','.join('?' * len(alias)), (r['code'],) + alias).fetchone()[0]
        nxt = (date.fromisoformat(last) + timedelta(days=every[k])) if last else None
        od = (today - nxt).days if nxt else None
        out.append({'kind': k, 'word': CARE_KINDS[k], 'every': every[k], 'last': last, 'next': nxt.isoformat() if nxt else None, 'overdue': od,
                    'state': 'unknown' if not last else 'due' if od >= 0 else 'soon' if od == -1 else 'ok'})
    return out

@app.route('/api/mixes/care')
def mixes_care():
    """For Today: the semi-hydro and water-only plants at the place in use with a flush or a root check due (top-ups and water
    changes are in the watering list, which already says "Top up" or "Change the water" for them)."""
    c = db(); out = []
    at, at_args = plants_at(c, location(c))
    for r in c.execute("SELECT * FROM plants WHERE status='active'" + at + ' ORDER BY code', at_args).fetchall():
        if grow_kind(r) == 'Soil mix': continue
        for h in hydro_state(c, r):
            if h['kind'] in ('flush', 'rootcheck') and h['state'] in ('due', 'unknown'):
                out.append({'code': r['code'], 'name': r['common_name'], 'grow_kind': grow_kind(r)} | h)
    return jsonify(items=out, every=hydro_every(c))
