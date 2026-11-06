"""Groups of plants.
Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- groups of plants (1.16.0)
# A group is either hand-picked (a list of plants in group_members) or smart (a rule kept in plant_groups.rule, so plants that
# fit join by themselves). Archived plants are never shown as members. Anyone who can edit can make and change groups.
# Changes to every plant in a group go through apply_changes (so each plant's page history and the audit log show them) and
# are kept in bulk_changes, so one press can undo them: a field goes back only if it still holds what the change put there.
RULE_FIELDS = [   # key, label, how the value is compared ('pick': choose from the values plants have, 'text': contains)
    ('name', 'Name (common, scientific or other names)', 'text'), ('genus', 'Genus', 'pick'), ('family', 'Family', 'pick'),
    ('taxon_order', 'Order', 'pick'), ('growth_habit', 'Type of plant', 'text'), ('plant_type', 'Plant type', 'pick'),
    ('site', 'Location', 'pick'), ('location', 'Spot', 'text'), ('winter_plan', 'Winter plan', 'pick'), ('health_rating', 'Health', 'pick'),
    ('leaf_type', 'Leaf type', 'pick'), ('pot_size', 'Pot size', 'pick'), ('light_spot', 'Grow light spot', 'pick')]
RULE_LABEL = {k: l for k, l, _ in RULE_FIELDS}
RULE_OPS = {'is': 'is', 'is_not': 'is not', 'contains': 'contains', 'not_contains': 'does not contain'}
BULK_FIELDS = ['site', 'location', 'container', 'temp_ideal_low', 'temp_ideal_high', 'temp_damage_below', 'temp_lethal_below', 'temp_damage_above', 'temp_notes',
               'humidity_low', 'humidity_high', 'vpd_low', 'vpd_high', 'humidity_notes', 'light_summary', 'light_hours', 'par_low', 'par_high', 'dli_low', 'dli_high',
               'light_notes', 'water_every_days', 'water_notes', 'soil_medium', 'soil_ph_low', 'soil_ph_high', 'soil_moisture_low', 'soil_moisture_high',
               'soil_temp_low', 'soil_temp_high', 'fertilizer', 'npk_ratio', 'fert_strength', 'nutrients', 'fert_from_month', 'fert_to_month', 'fert_every_days',
               'winter_plan', 'winter_summary', 'winter_triggers', 'winter_steps', 'indoor_setup', 'pests_watch', 'pest_steps', 'leaf_type', 'pot_size']
FIT_MEASURES = [('temp', 'Comfortable temperature', 'temp_ideal_low', 'temp_ideal_high', '°F'), ('hum', 'Comfortable humidity', 'humidity_low', 'humidity_high', '%'),
                ('par', 'Light at the leaves (PAR)', 'par_low', 'par_high', ''), ('dli', 'Daily light (mol/m² a day)', 'dli_low', 'dli_high', ''),
                ('ph', 'Soil pH', 'soil_ph_low', 'soil_ph_high', ''), ('moist', 'Soil moisture (probe)', 'soil_moisture_low', 'soil_moisture_high', '%')]

def group_rule(raw):
    """A rule as stored: {"match": "all"|"any", "conds": [{"field", "op", "value"}]}, cleaned; errors in plain words."""
    r = raw if isinstance(raw, dict) else {}
    conds = []
    for x in (r.get('conds') or [])[:8]:
        f, op, v = str(x.get('field', '')), str(x.get('op', 'is')), re.sub(r'\s+', ' ', str(x.get('value', ''))).strip()[:120]
        if f not in RULE_LABEL: abort(400, 'Choose what to look at for each part of the rule')
        if op not in RULE_OPS: abort(400, 'Choose how to compare for each part of the rule')
        if not v: abort(400, f'Type or choose a value for "{RULE_LABEL[f]}"')
        conds.append({'field': f, 'op': op, 'value': v})
    if not conds: abort(400, 'A smart group needs at least one part to its rule, for example "Genus is Philodendron"')
    return {'match': 'any' if r.get('match') == 'any' else 'all', 'conds': conds}

def rule_words(rule):
    if not rule: return ''
    parts = ['%s %s "%s"' % (RULE_LABEL.get(x['field'], x['field']), RULE_OPS.get(x['op'], x['op']), x['value']) for x in rule.get('conds', [])]
    return (' or ' if rule.get('match') == 'any' else ' and ').join(parts)

def plant_spots(c):
    return {code: name for code, name in c.execute('SELECT a.plant_code, s.name FROM light_assign a JOIN light_spots s ON s.id=a.spot_id')}

def rule_value(r, field, spots):
    if field == 'name': return ' '.join(str(r[n] or '') for n in ('common_name', 'scientific_name', 'aliases'))
    if field == 'light_spot': return spots.get(r['code'], '')
    if field == 'site': return r['site'] or 'Outdoors'
    return str(r[field] or '')

def rule_match(rule, r, spots):
    res = []
    for x in rule['conds']:
        have, want = rule_value(r, x['field'], spots).strip().lower(), x['value'].lower()
        res.append({'is': have == want, 'is_not': have != want, 'contains': want in have, 'not_contains': want not in have}[x['op']])
    return any(res) if rule['match'] == 'any' else all(res)

def group_codes(c, g, rows=None, spots=None):
    """The active plants in a group, in code order."""
    if g['kind'] == 'smart':
        rule = json.loads(g['rule'] or '{}')
        if not rule.get('conds'): return []
        rows = rows if rows is not None else c.execute("SELECT * FROM plants WHERE status='active' ORDER BY code").fetchall()
        spots = spots if spots is not None else plant_spots(c)
        return [r['code'] for r in rows if rule_match(rule, r, spots)]
    return [x for (x,) in c.execute("SELECT p.code FROM group_members m JOIN plants p ON p.id=m.plant_id WHERE m.group_id=? AND p.status='active' ORDER BY p.code", (g['id'],))]

def group_brief(c, g, rows=None, spots=None):
    rule = json.loads(g['rule'] or '{}') if g['kind'] == 'smart' else None
    codes = group_codes(c, g, rows, spots)
    return {'id': g['id'], 'name': g['name'], 'kind': g['kind'], 'rule': rule, 'rule_words': rule_words(rule), 'notes': g['notes'], 'codes': codes, 'count': len(codes),
            'created_by': g['created_by'], 'created_at': g['created_at'], 'updated_by': g['updated_by'], 'updated_at': g['updated_at']}

def groups_of(c, code):
    """The groups one plant is in (for its page)."""
    r = c.execute('SELECT * FROM plants WHERE code=?', (code,)).fetchone()
    if not r or r['status'] != 'active': return []
    spots, out = plant_spots(c), []
    for g in c.execute('SELECT * FROM plant_groups ORDER BY name COLLATE NOCASE'):
        if g['kind'] == 'smart':
            rule = json.loads(g['rule'] or '{}')
            if rule.get('conds') and rule_match(rule, r, spots): out.append({'id': g['id'], 'name': g['name'], 'kind': 'smart'})
        elif c.execute('SELECT 1 FROM group_members WHERE group_id=? AND plant_id=?', (g['id'], r['id'])).fetchone():
            out.append({'id': g['id'], 'name': g['name'], 'kind': 'picked'})
    return out

GENUS_NAMES = {'Rosa': 'Roses', 'Ravenea': 'Majesty palms', 'Ficus': 'Figs and rubber trees', 'Haworthiopsis': 'Zebra haworthias', 'Spathiphyllum': 'Peace lilies',
               'Syngonium': 'Arrowhead plants', 'Zamioculcas': 'ZZ plants', 'Ipomoea': 'Morning glories and sweet potato vines', 'Coleus': 'Coleus',
               'Tradescantia': 'Tradescantias', 'Opuntia': 'Prickly pears', 'Goeppertia': 'Calatheas', 'Phalaenopsis': 'Moth orchids'}
FAMILY_NAMES = {'Marantaceae': 'Prayer plants', 'Araceae': 'Aroids', 'Cactaceae': 'Cacti', 'Asphodelaceae': 'Aloes and haworthias', 'Crassulaceae': 'Stonecrop family succulents', 'Moraceae': 'Fig family',
                'Asteraceae': 'Daisy family', 'Lamiaceae': 'Mint family', 'Orchidaceae': 'Orchids', 'Rosaceae': 'Rose family', 'Malvaceae': 'Mallow family',
                'Convolvulaceae': 'Morning glory family', 'Commelinaceae': 'Spiderwort family', 'Arecaceae': 'Palms', 'Amaranthaceae': 'Amaranth family'}

CARE_FAMILIES = {'Araceae', 'Cactaceae', 'Asphodelaceae', 'Crassulaceae', 'Orchidaceae', 'Arecaceae', 'Marantaceae'}   # families whose plants share care

def suggestion_name(f, v):
    if f == 'genus':
        g = re.sub(r'\s*\(.*\)', '', v).strip()
        return GENUS_NAMES.get(g) or (g + ('' if g.endswith('s') else 's'))
    if f == 'family': return FAMILY_NAMES.get(v) or (v + ' family')
    return 'Under ' + v

def group_suggestions(c, rows, spots, have):
    """Smart groups worth having that do not exist yet: each genus with 2 or more plants, each family with plants of 2 or more
    genera (such as the aroids, which share a potting mix), and each grow light spot with 2 or more plants."""
    have_rules = {json.dumps(json.loads(g['rule'] or '{}').get('conds'), sort_keys=True) for g in have if g['kind'] == 'smart'}
    names = {g['name'].lower() for g in have}
    out, count = [], {}
    genera = {}
    for r in rows:
        if r['genus']: count.setdefault(('genus', r['genus']), []).append(r['code'])
        if r['family'] and r['genus']: count.setdefault(('family', r['family']), []).append(r['code']); genera.setdefault(r['family'], set()).add(r['genus'])
        if spots.get(r['code']): count.setdefault(('light_spot', spots[r['code']]), []).append(r['code'])
    order = {'family': 0, 'genus': 1, 'light_spot': 2}
    for (f, v), codes in sorted(count.items(), key=lambda kv: (order[kv[0][0]], -len(kv[1]), kv[0])):
        if len(codes) < 2 or 'not identified' in v.lower() or (f == 'family' and (v not in CARE_FAMILIES or len(genera.get(v, ())) < 2)): continue
        conds = [{'field': f, 'op': 'is', 'value': v}]
        name = suggestion_name(f, v)
        if json.dumps(conds, sort_keys=True) in have_rules or name.lower() in names: continue
        out.append({'name': name, 'rule': {'match': 'all', 'conds': conds}, 'rule_words': rule_words({'match': 'all', 'conds': conds}), 'codes': codes, 'count': len(codes)})
    return out[:30]

def rule_values(c, rows, spots):
    vals = {}
    for k, _, how in RULE_FIELDS:
        if how != 'pick': continue
        if k in ENUMS: v = set(ENUMS[k])
        elif k == 'light_spot': v = {x for (x,) in c.execute('SELECT name FROM light_spots')}
        else: v = {str(r[k]).strip() for r in rows if r[k]}
        vals[k] = sorted(v, key=str.lower)
    return vals

def group_name_ok(c, name, gid=None):
    name = re.sub(r'\s+', ' ', str(name or '')).strip()[:60]
    if not name: abort(400, 'Give the group a name, for example "Philodendrons" or "Tall Black Shelf"')
    clash = c.execute('SELECT id FROM plant_groups WHERE name=? COLLATE NOCASE', (name,)).fetchone()
    if clash and clash[0] != gid: abort(409, f'There is already a group called "{name}"')
    return name

def set_members(c, gid, gname, codes, who, add=True):
    done = []
    for code in dict.fromkeys(str(x) for x in codes):
        r = c.execute('SELECT id, code FROM plants WHERE code=?', (code,)).fetchone()
        if not r: abort(400, f'There is no plant {code}')
        there = c.execute('SELECT 1 FROM group_members WHERE group_id=? AND plant_id=?', (gid, r['id'])).fetchone()
        if add and not there:
            c.execute('INSERT INTO group_members(group_id,plant_id,added_by,added_at) VALUES(?,?,?,?)', (gid, r['id'], who, now()))
            audit_only(c, 'group', 'group', None, gname, who, f'Added to the group {gname}', r['id'], code); done.append(code)
        elif not add and there:
            c.execute('DELETE FROM group_members WHERE group_id=? AND plant_id=?', (gid, r['id']))
            audit_only(c, 'group', 'group', gname, None, who, f'Taken out of the group {gname}', r['id'], code); done.append(code)
    return done

def group_or_404(c, gid):
    g = c.execute('SELECT * FROM plant_groups WHERE id=?', (gid,)).fetchone()
    if not g: abort(404, 'That group is not there any more')
    return g

def best_band(items):
    """items: [(code, name, lo, hi)]. The range that suits the most plants: the point inside the most ranges, then the overlap
    of the ranges that contain it. Plants whose range misses it are the odd ones out."""
    if not items: return None
    pts = sorted({x[2] for x in items} | {x[3] for x in items})
    best = max(pts, key=lambda p: (sum(1 for x in items if x[2] <= p <= x[3]), -p))
    inn = [x for x in items if x[2] <= best <= x[3]]
    out = [x for x in items if x not in inn]
    return {'lo': max(x[2] for x in inn), 'hi': min(x[3] for x in inn), 'fits': len(inn), 'n': len(items),
            'odd': [{'code': x[0], 'name': x[1], 'lo': x[2], 'hi': x[3]} for x in out]}

def group_fit(rows):
    fit = []
    for key, label, a, b, unit in FIT_MEASURES:
        items = [(r['code'], r['common_name'], r[a], r[b]) for r in rows if r[a] is not None and r[b] is not None and r[a] <= r[b]]
        band = best_band(items)
        if band: fit.append({'key': key, 'label': label, 'unit': unit, **band, 'missing': len(rows) - len(items)})
    cold = [(r['code'], r['common_name'], r['temp_damage_below']) for r in rows if r['temp_damage_below'] is not None]
    if cold:
        worst = max(x[2] for x in cold)
        fit.append({'key': 'cold', 'label': 'Keep warmer than', 'unit': '°F', 'value': worst, 'by': [{'code': x[0], 'name': x[1]} for x in cold if x[2] == worst], 'n': len(cold)})
    water = [r['water_every_days'] for r in rows if r['water_every_days']]
    if water: fit.append({'key': 'water', 'label': 'Water every', 'unit': 'days', 'lo': min(water), 'hi': max(water), 'n': len(water), 'spread': True})
    for key, label, f in (('plan', 'Winter plan', 'winter_plan'), ('npk', 'Fertilizer ratio', 'npk_ratio'), ('soil', 'Soil or potting mix', 'soil_medium')):
        vals = {}
        for r in rows:
            if r[f]: vals.setdefault(r[f], []).append(r['code'])
        if vals: fit.append({'key': key, 'label': label, 'values': [{'value': v, 'codes': cs} for v, cs in sorted(vals.items(), key=lambda kv: -len(kv[1]))], 'n': sum(len(cs) for cs in vals.values())})
    return fit

@app.route('/api/groups', methods=['GET', 'POST'])
def groups_list():
    c = db()
    rows = c.execute("SELECT * FROM plants WHERE status='active' ORDER BY code").fetchall()
    spots = plant_spots(c)
    if request.method == 'GET':
        gs = c.execute('SELECT * FROM plant_groups ORDER BY name COLLATE NOCASE').fetchall()
        return jsonify(groups=[group_brief(c, g, rows, spots) for g in gs], suggestions=group_suggestions(c, rows, spots, gs),
                       fields=[{'key': k, 'label': l, 'how': h} for k, l, h in RULE_FIELDS], ops=RULE_OPS, values=rule_values(c, rows, spots),
                       bulk_fields=BULK_FIELDS)
    b = request.get_json(silent=True) or {}
    who, name = editor(), group_name_ok(c, b.get('name'))
    kind = 'smart' if b.get('kind') == 'smart' else 'picked'
    rule = group_rule(b.get('rule')) if kind == 'smart' else None
    gid = c.execute('INSERT INTO plant_groups(name,kind,rule,notes,created_by,created_at) VALUES(?,?,?,?,?,?)',
                    (name, kind, json.dumps(rule) if rule else '', str(b.get('notes', '')).strip()[:500], who, now())).lastrowid
    audit_only(c, 'group', 'group', None, name, who, f'Group made: {name} (' + ('smart: ' + rule_words(rule) if rule else 'hand-picked') + ')')
    if kind == 'picked' and b.get('codes'): set_members(c, gid, name, b['codes'], who)
    c.commit()
    return jsonify(group_brief(c, group_or_404(c, gid))), 201

@app.route('/api/groups/match', methods=['POST'])
def group_match():
    """The plants a rule would take in, for the window where a smart group is made. Nothing is saved."""
    c = db()
    rule = group_rule((request.get_json(silent=True) or {}).get('rule'))
    rows, spots = c.execute("SELECT * FROM plants WHERE status='active' ORDER BY code").fetchall(), plant_spots(c)
    return jsonify(codes=[r['code'] for r in rows if rule_match(rule, r, spots)], words=rule_words(rule))

@app.route('/api/groups/<int:gid>', methods=['GET', 'PUT', 'DELETE'])
def group_one(gid):
    c = db()
    g = group_or_404(c, gid)
    who = editor()
    if request.method == 'GET':
        d = group_brief(c, g)
        rows = [c.execute('SELECT * FROM plants WHERE code=?', (x,)).fetchone() for x in d['codes']]
        spots = plant_spots(c)
        d['members'] = [{'code': r['code'], 'common_name': r['common_name'], 'scientific_name': r['scientific_name'], 'site': r['site'] or 'Outdoors',
                         'location': r['location'], 'light_spot': spots.get(r['code']),
                         'photo': (lambda p: p[0] if p else None)(c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (r['id'],)).fetchone())}
                        for r in rows]
        d['fit'] = group_fit(rows)
        d['recent'] = [{'id': x['id'], 'what': x['what'], 'done_by': x['done_by'], 'done_at': x['done_at'], 'undone_at': x['undone_at'], 'undone_by': x['undone_by'],
                        'count': len(json.loads(x['changes']))} for x in c.execute('SELECT * FROM bulk_changes WHERE group_id=? ORDER BY id DESC LIMIT 8', (gid,))]
        return jsonify(d)
    if request.method == 'DELETE':
        c.execute('DELETE FROM group_members WHERE group_id=?', (gid,))
        c.execute('DELETE FROM plant_groups WHERE id=?', (gid,))
        audit_only(c, 'group', 'group', g['name'], None, who, f'Group removed: {g["name"]} (the plants themselves are not changed)')
        c.commit()
        return jsonify(ok=True)
    b = request.get_json(silent=True) or {}
    name = group_name_ok(c, b.get('name', g['name']), gid)
    rule = group_rule(b['rule']) if g['kind'] == 'smart' and 'rule' in b else (json.loads(g['rule']) if g['rule'] else None)
    notes = str(b.get('notes', g['notes'])).strip()[:500]
    c.execute('UPDATE plant_groups SET name=?, rule=?, notes=?, updated_by=?, updated_at=? WHERE id=?', (name, json.dumps(rule) if rule else '', notes, who, now(), gid))
    said = []
    if name != g['name']: said.append(f'renamed from {g["name"]}')
    if rule and json.dumps(rule) != g['rule']: said.append('rule now: ' + rule_words(rule))
    if notes != g['notes']: said.append('notes changed')
    if said: audit_only(c, 'group', 'group', g['name'], name, who, f'Group {name}: ' + '; '.join(said))
    c.commit()
    return jsonify(group_brief(c, group_or_404(c, gid)))

@app.route('/api/groups/<int:gid>/members', methods=['POST'])
def group_members_change(gid):
    """Hand-picked groups only: {add: [codes]} and/or {remove: [codes]}."""
    c = db()
    g = group_or_404(c, gid)
    if g['kind'] != 'picked': abort(400, 'Plants join a smart group by its rule. Change the rule, or make a hand-picked group')
    b, who = request.get_json(silent=True) or {}, editor()
    added = set_members(c, gid, g['name'], b.get('add') or [], who, True)
    removed = set_members(c, gid, g['name'], b.get('remove') or [], who, False)
    c.commit()
    return jsonify(added=added, removed=removed, group=group_brief(c, g))

@app.route('/api/plants/<code>/groups', methods=['GET', 'POST'])
def plant_groups_route(code):
    """The groups a plant is in; POST {picked: [group ids]} sets which hand-picked groups it is in."""
    c = db()
    r = plant_row(c, code)
    if request.method == 'POST':
        want, who = {int(x) for x in ((request.get_json(silent=True) or {}).get('picked') or [])}, editor()
        for g in c.execute("SELECT * FROM plant_groups WHERE kind='picked'").fetchall():
            set_members(c, g['id'], g['name'], [r['code']], who, g['id'] in want)
        c.commit()
    return jsonify(groups_of(c, r['code']), )

def bulk_rows(c, g, codes):
    inside = set(group_codes(c, g))
    codes = [str(x) for x in codes or []]
    bad = [x for x in codes if x not in inside]
    if bad: abort(400, 'These plants are not in the group: ' + ', '.join(bad))
    if not codes: abort(400, 'Tick at least one plant')
    return [c.execute('SELECT * FROM plants WHERE code=?', (x,)).fetchone() for x in codes]

def bulk_set(b):
    st = b.get('set') or {}
    if not isinstance(st, dict) or not st: abort(400, 'Choose what to change')
    for f in st:
        if f not in BULK_FIELDS: abort(400, f'{FIELD_LABEL.get(f, f)} cannot be changed for a whole group')
    return {f: norm(f, v) for f, v in st.items()}

@app.route('/api/groups/<int:gid>/preview', methods=['POST'])
def group_preview(gid):
    """What a change would do to each plant: {set: {field: value}, codes?}. Nothing is saved."""
    c = db()
    g = group_or_404(c, gid)
    b = request.get_json(silent=True) or {}
    st = bulk_set(b)
    rows = bulk_rows(c, g, b.get('codes') or group_codes(c, g))
    out = []
    for r in rows:
        cur = {f: r[f] for f in st}
        out.append({'code': r['code'], 'common_name': r['common_name'], 'current': cur, 'same': all((cur[f] if cur[f] is not None else '') == (v if v is not None else '') for f, v in st.items())})
    common = {}
    for f in st:                       # the value most of them have now: plants that differ from it are pointed out
        vals = [str(x['current'][f] if x['current'][f] is not None else '') for x in out]
        common[f] = max(set(vals), key=vals.count) if vals else ''
    for x in out: x['differs'] = [f for f in st if str(x['current'][f] if x['current'][f] is not None else '') != common[f]]
    return jsonify(set=st, labels={f: FIELD_LABEL[f] for f in st}, rows=out, common=common)

@app.route('/api/groups/<int:gid>/apply', methods=['POST'])
def group_apply(gid):
    """Change fields on ticked plants: {set: {field: value}, codes: [...], expect: {code: {field: value shown in the preview}}}.
    A plant whose value changed since the preview is skipped, so nothing is overwritten unseen."""
    c = db()
    g = group_or_404(c, gid)
    b, who = request.get_json(silent=True) or {}, editor()
    st = bulk_set(b)
    rows = bulk_rows(c, g, b.get('codes'))
    expect = b.get('expect') or {}
    labels = ', '.join(FIELD_LABEL[f] for f in st)
    what = f'{labels} changed for the group {g["name"]}'
    changes, skipped = [], []
    for r in rows:
        exp = expect.get(r['code'])
        if isinstance(exp, dict) and any(str(r[f] if r[f] is not None else '') != str(exp.get(f) if exp.get(f) is not None else '') for f in st):
            skipped.append(r['code']); continue
        before = {f: r[f] for f in st}
        _, changed = apply_changes(c, r, st, who, 'edit', what)
        if changed:
            after = c.execute('SELECT * FROM plants WHERE id=?', (r['id'],)).fetchone()
            changes.append({'code': r['code'], 'fields': {f: [before[f], after[f]] for f in st if (before[f] or '') != (after[f] or '')}})
    bid = None
    if changes:
        bid = c.execute('INSERT INTO bulk_changes(group_id,what,changes,done_by,done_at) VALUES(?,?,?,?,?)', (gid, what, json.dumps(changes), who, now())).lastrowid
        audit_only(c, 'group', 'bulk', None, f'{len(changes)} plants', who, f'{what}: {len(changes)} plants changed' + (f', {len(skipped)} skipped' if skipped else ''))
    c.commit()
    return jsonify(bulk_id=bid, changed=[x['code'] for x in changes], skipped=skipped, same=[r['code'] for r in rows if r['code'] not in skipped and r['code'] not in {x['code'] for x in changes}])

@app.route('/api/groups/<int:gid>/spot', methods=['POST'])
def group_spot(gid):
    """Put ticked plants under one grow light spot: {spot: id, codes: [...]}, or take them out of their spots with spot null."""
    c = db()
    g = group_or_404(c, gid)
    b, who = request.get_json(silent=True) or {}, editor()
    rows = bulk_rows(c, g, b.get('codes'))
    codes = [r['code'] for r in rows]
    if b.get('spot') in (None, '', 'none'):
        for sid, name in c.execute('SELECT DISTINCT s.id, s.name FROM light_assign a JOIN light_spots s ON s.id=a.spot_id WHERE a.plant_code IN (%s)' % ','.join('?' * len(codes)), codes).fetchall():
            keep = [x for (x,) in c.execute('SELECT plant_code FROM light_assign WHERE spot_id=?', (sid,)) if x not in codes]
            set_spot_plants(c, sid, name, keep, who)
        where = 'out of their grow light spots'
    else:
        sp = c.execute('SELECT * FROM light_spots WHERE id=?', (int(b['spot']),)).fetchone()
        if not sp: abort(400, 'That grow light spot is not set up any more')
        have = [x for (x,) in c.execute('SELECT plant_code FROM light_assign WHERE spot_id=?', (sp['id'],))]
        set_spot_plants(c, sp['id'], sp['name'], list(dict.fromkeys(have + codes)), who)
        where = 'under the grow light spot ' + sp['name']
    audit_only(c, 'group', 'bulk', None, f'{len(codes)} plants', who, f'{len(codes)} plants from the group {g["name"]} put {where}')
    c.commit()
    return jsonify(ok=True, codes=codes)

@app.route('/api/bulk/<int:bid>/undo', methods=['POST'])
def bulk_undo(bid):
    c = db()
    x = c.execute('SELECT * FROM bulk_changes WHERE id=?', (bid,)).fetchone()
    if not x: abort(404, 'That change is not in the list any more')
    if x['undone_at']: abort(409, 'That change was already undone')
    who, back, kept = editor(), [], []
    for ch in json.loads(x['changes']):
        r = c.execute('SELECT * FROM plants WHERE code=?', (ch['code'],)).fetchone()
        if not r: continue
        todo = {f: old for f, (old, new) in ch['fields'].items() if (r[f] if r[f] is not None else '') == (new if new is not None else '')}
        if len(todo) < len(ch['fields']): kept.append(ch['code'])
        if todo:
            apply_changes(c, r, {f: ('' if v is None else v) for f, v in todo.items()}, who, 'edit', 'Undone: ' + x['what'])
            back.append(ch['code'])
    c.execute('UPDATE bulk_changes SET undone_by=?, undone_at=? WHERE id=?', (who, now(), bid))
    audit_only(c, 'group', 'bulk', f'{len(back)} plants', None, who, f'Undone: {x["what"]}' + (f' ({len(kept)} left as they were, changed again since)' if kept else ''))
    c.commit()
    return jsonify(undone=back, kept=kept)
