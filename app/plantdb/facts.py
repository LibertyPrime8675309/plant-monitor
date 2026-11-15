"""Knowledge with provenance (1.53.0, PLAN.md step 6a): one row per fact about a species, with where it came from.

Before this, what the app knows about a species lived in three places with one origin each: the care fields of each plant (set
by the first plant list and the upgrade batches, or edited by hand), the species_facts blob (uses, partners, propagation,
written by Claude), and the care sheets in data/library/care (Claude, asked from the Library). A fact could not be corrected on
its own and nobody but Claude could add one. The `facts` table holds one row per fact: the species key (facts_keys(), 'aloe vera'
or a genus), the field, the value, the source (a batch, a book, a link, a person's own observation), its kind, who noted it,
when, how sure (certain, likely, unsure) and a status (accepted, proposed, retired). A field's accepted row is what pages show;
retired rows are its history.

Loaded once, in place (facts_migrate): every species_facts section, every care sheet section, and every care field on which all
of a species' plants agree, each with the source it can be traced to (the batch that set it, the first plant list, or "edited in
the app"). Nothing anyone typed changes: plant fields stay as they are, and a plant's own value always wins over the species'.
A plant's page reads the species' accepted facts for fields the plant leaves empty (species_fill), marked as such.

Step 6b (1.54.0): editors propose a fact or a correction from a species page (a 'proposed' row); any other editor, or the owner,
accepts it (it becomes the accepted row and retires the old one) or rejects it, from the page or the "Facts to review" queue;
nobody but the owner accepts their own. The audit log keeps who did what. Mushroom species facts are the same rows with kind
'fungus': the field list has no "edible" field and a proposal that says so is refused (FACTS_FUNGUS_NO). Import (the export's
JSON) adds proposed rows only, never accepted ones."""
import csv, io, json, os, re
from .core import *   # noqa: F401,F403
from .library import care_get, CARE_DIR
from .speciesfacts import facts_keys, FACTS_FUNGUS_NO

KNOWLEDGE_SCHEMA = """
CREATE TABLE IF NOT EXISTS facts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'plant', field TEXT NOT NULL, value TEXT NOT NULL,
  source TEXT NOT NULL DEFAULT '', source_kind TEXT NOT NULL DEFAULT 'reference', noted_by TEXT NOT NULL DEFAULT '', noted_at TEXT NOT NULL,
  confidence TEXT NOT NULL DEFAULT 'likely', status TEXT NOT NULL DEFAULT 'accepted', replaces INTEGER, note TEXT NOT NULL DEFAULT '');
CREATE INDEX IF NOT EXISTS facts_key ON facts(key, field, status);
"""
SOURCE_KINDS = ('reference', 'trial', 'grower', 'observation', 'claude', 'batch')
CONFIDENCE = ('certain', 'likely', 'unsure')
STATUS = ('accepted', 'proposed', 'retired', 'rejected')

# The fields a species can have facts for: (field, kind, label, group). Plant fields (FIELDS) that describe the species rather than
# one pot; then the sections of the species_facts blob (about_*) and of a Claude care sheet (sheet_*). Values are text; lists and
# dicts are JSON text (kind 'json').
FACT_FIELDS = [
    ('temp_ideal_low', 'int', 'Ideal temperature, low (°F)', 'Temperature'), ('temp_ideal_high', 'int', 'Ideal temperature, high (°F)', 'Temperature'),
    ('temp_damage_below', 'int', 'Damage below (°F)', 'Temperature'), ('temp_lethal_below', 'int', 'Dies below (°F)', 'Temperature'),
    ('temp_damage_above', 'int', 'Heat damage above (°F)', 'Temperature'), ('temp_notes', 'long', 'Temperature notes', 'Temperature'),
    ('humidity_low', 'int', 'Ideal humidity, low (%)', 'Humidity and air'), ('humidity_high', 'int', 'Ideal humidity, high (%)', 'Humidity and air'),
    ('humidity_notes', 'long', 'Humidity notes', 'Humidity and air'), ('vpd_low', 'num', 'Ideal VPD, low (kPa)', 'Humidity and air'), ('vpd_high', 'num', 'Ideal VPD, high (kPa)', 'Humidity and air'),
    ('light_summary', 'text', 'Light', 'Light'), ('light_hours', 'text', 'Hours of light', 'Light'), ('light_notes', 'long', 'Light notes', 'Light'),
    ('par_low', 'int', 'Light, low (PAR)', 'Light'), ('par_high', 'int', 'Light, high (PAR)', 'Light'), ('dli_low', 'num', 'Daily light, low (DLI)', 'Light'), ('dli_high', 'num', 'Daily light, high (DLI)', 'Light'),
    ('water_notes', 'long', 'Watering', 'Water'), ('soil_moisture_low', 'int', 'Soil moisture, low (%)', 'Water'), ('soil_moisture_high', 'int', 'Soil moisture, high (%)', 'Water'),
    ('soil_medium', 'long', 'Soil or potting mix', 'Soil'), ('mix_wants', 'enum', 'Mix it wants', 'Soil'),     # 1.56.0 (PLAN.md step 9) ('soil_ph_low', 'num', 'Soil pH, low', 'Soil'), ('soil_ph_high', 'num', 'Soil pH, high', 'Soil'),
    ('soil_temp_low', 'int', 'Soil temperature, low (°F)', 'Soil'), ('soil_temp_high', 'int', 'Soil temperature, high (°F)', 'Soil'),
    ('fertilizer', 'text', 'Fertilizer', 'Feeding'), ('nutrients', 'long', 'Nutrients', 'Feeding'), ('npk_ratio', 'text', 'N-P-K ratio', 'Feeding'), ('fert_strength', 'enum', 'Fertilizer strength', 'Feeding'),
    ('fert_from_month', 'int', 'Feeding from (month)', 'Feeding'), ('fert_to_month', 'int', 'Feeding until (month)', 'Feeding'),
    ('growth_habit', 'text', 'Growth habit', 'Size and growth'), ('growth_rate', 'text', 'Growth rate', 'Size and growth'), ('lifespan', 'text', 'Lifespan', 'Size and growth'),
    ('height_ground', 'text', 'Height in the ground', 'Size and growth'), ('width_ground', 'text', 'Width in the ground', 'Size and growth'), ('leaf_type', 'enum', 'Leaf type', 'Size and growth'),
    ('bloom', 'long', 'Flowers', 'Size and growth'), ('fruit', 'long', 'Fruit', 'Size and growth'),
    ('zone_low', 'text', 'USDA zone, low', 'Hardiness'), ('zone_high', 'text', 'USDA zone, high', 'Hardiness'), ('zone_notes', 'long', 'Hardiness notes', 'Hardiness'),
    ('heat_zone_low', 'int', 'AHS heat zone, low', 'Hardiness'), ('heat_zone_high', 'int', 'AHS heat zone, high', 'Hardiness'),
    ('native_range', 'long', 'Native range', 'Origin and safety'), ('conservation_status', 'long', 'Conservation status', 'Origin and safety'), ('invasive', 'long', 'Invasive where', 'Origin and safety'),
    ('danger_humans', 'long', 'Danger to people', 'Origin and safety'), ('danger_animals', 'long', 'Danger to animals', 'Origin and safety'), ('pet_safety', 'enum', 'Pet safety', 'Origin and safety'),
    ('pests_watch', 'json', 'Pests to watch for', 'Pests'), ('pest_steps', 'json', 'What to do about pests', 'Pests'),
    ('propagation', 'json', 'Propagation (steps)', 'Propagation'),
    ('about_summary', 'long', 'In short', 'Uses and partners'), ('about_uses', 'json', 'Uses', 'Uses and partners'),
    ('about_partners_good', 'json', 'Good partners', 'Uses and partners'), ('about_partners_bad', 'json', 'Keep apart from', 'Uses and partners'),
    ('about_deters', 'json', 'Keeps away', 'Uses and partners'), ('about_attracts', 'json', 'Brings in', 'Uses and partners'),
    ('about_propagation', 'json', 'Propagation (ways)', 'Propagation'), ('about_compost', 'json', 'In the compost', 'Uses and partners'),
    ('about_breeding', 'json', 'Breeding', 'Uses and partners'), ('about_sources', 'json', 'Read more', 'Uses and partners'),
    ('sheet_summary', 'long', 'Care sheet: in short', 'Care sheet'), ('sheet_light', 'long', 'Care sheet: light', 'Care sheet'), ('sheet_water', 'long', 'Care sheet: water', 'Care sheet'),
    ('sheet_soil', 'long', 'Care sheet: soil', 'Care sheet'), ('sheet_temperature', 'long', 'Care sheet: temperature', 'Care sheet'), ('sheet_humidity', 'long', 'Care sheet: humidity', 'Care sheet'),
    ('sheet_feeding', 'long', 'Care sheet: feeding', 'Care sheet'), ('sheet_pruning', 'long', 'Care sheet: pruning', 'Care sheet'), ('sheet_propagation', 'long', 'Care sheet: propagation', 'Care sheet'),
    ('sheet_pests', 'long', 'Care sheet: pests and problems', 'Care sheet'), ('sheet_containers', 'long', 'Care sheet: in a pot', 'Care sheet'), ('sheet_outdoors_here', 'long', 'Care sheet: outdoors here', 'Care sheet'),
    ('sheet_zone_low', 'text', 'Care sheet: USDA zone, low', 'Care sheet'), ('sheet_zone_high', 'text', 'Care sheet: USDA zone, high', 'Care sheet'), ('sheet_min_temp_f', 'int', 'Care sheet: survives down to (°F)', 'Care sheet'),
]
FACT_BY_NAME = {f[0]: f for f in FACT_FIELDS}
PLANT_FACT_FIELDS = [f for f in FACT_FIELDS if not f[0].startswith(('about_', 'sheet_'))]      # these are plant columns too
GROUPS = []
for _f in FACT_FIELDS:
    if _f[3] not in GROUPS: GROUPS.append(_f[3])

def fact_value_text(kind, v):
    """A field's value as the text kept in the row ('' when empty)."""
    if v is None: return ''
    if kind == 'json':
        if isinstance(v, str):
            try: v = json.loads(v)
            except ValueError: return v.strip()
        return json.dumps(v, ensure_ascii=False) if v not in ('', [], {}, None) else ''
    if kind in ('int', 'num'):
        try: f = float(v); return str(int(f)) if f == int(f) else ('%g' % f)
        except (TypeError, ValueError): return str(v).strip()
    return re.sub(r'\s+', ' ', str(v)).strip() if kind in ('text', 'enum') else str(v).strip()

def fact_value_out(kind, s):
    """The row's text back as a value for the page (numbers as numbers, json as data)."""
    if kind == 'int':
        try: return int(float(s))
        except ValueError: return s
    if kind == 'num':
        try: return float(s)
        except ValueError: return s
    if kind == 'json':
        try: return json.loads(s)
        except ValueError: return s
    return s

def species_key(sci):
    """The key a species' facts are filed under: the binomial when the name has one, else the genus, else None."""
    ks = facts_keys(sci)
    return ks[0] if ks else None

def facts_of(c, sci_or_key, code=None):
    """{field: accepted row} for a species (a plant's facts_link key first, 1.27.0)."""
    keys = []
    if code:
        lk = c.execute('SELECT key FROM facts_link WHERE code=?', (code,)).fetchone()
        if lk: keys.append(lk[0])
    for k in (facts_keys(sci_or_key) if sci_or_key and sci_or_key[0].isupper() else [sci_or_key]):
        if k and k not in keys: keys.append(k)
    out = {}
    for k in keys:                                                                   # the most exact key wins per field
        for r in c.execute("SELECT * FROM facts WHERE key=? AND status='accepted'", (k,)):
            if r['field'] not in out: out[r['field']] = r
    return out

def fact_add(c, key, kind, field, value, source, source_kind, noted_by, noted_at=None, confidence='likely', status='accepted', note='', replaces=None):
    """One row; an accepted row retires the field's previous accepted row for that key. Returns the id, or None when the value is empty
    or the same accepted value is already there."""
    f = FACT_BY_NAME.get(field)
    if not f or not key: return None
    text = fact_value_text(f[1], value)
    if not text: return None
    if status == 'accepted':
        old = c.execute("SELECT id, value FROM facts WHERE key=? AND field=? AND status='accepted'", (key, field)).fetchone()
        if old and old['value'] == text: return None
        if old:
            c.execute("UPDATE facts SET status='retired' WHERE id=?", (old['id'],)); replaces = replaces or old['id']
    cur = c.execute('INSERT INTO facts(key,kind,field,value,source,source_kind,noted_by,noted_at,confidence,status,replaces,note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                    (key, kind if kind in ('plant', 'fungus') else 'plant', field, text, str(source or '')[:300], source_kind if source_kind in SOURCE_KINDS else 'reference',
                     str(noted_by or '')[:80], noted_at or now(), confidence if confidence in CONFIDENCE else 'likely', status if status in STATUS else 'accepted', replaces, str(note or '')[:500]))
    return cur.lastrowid

# ---------------------------------------------------------------- where a plant's field value came from
def batch_sources():
    """[(label, when, who, {code: {field: value}})] in the order they were applied: the first plant list, then every batch."""
    out = []
    seed_file = os.path.join(SEED_DIR, 'seed.json')
    if os.path.exists(seed_file):
        try:
            seed = json.load(open(seed_file, encoding='utf-8'))
            out.append(('The first plant list (October 19, 2026)', '2026-10-19T22:30:00Z', seed.get('author', 'Claude'), {p['code']: {k: p.get(k) for k in FIELD_NAMES} for p in seed.get('plants', [])}, {}))
        except (OSError, ValueError, KeyError): pass
    bdir = os.path.join(SEED_DIR, 'batches')
    if os.path.isdir(bdir):
        for fn in sorted(os.listdir(bdir)):
            if not fn.endswith('.json'): continue
            try: b = json.load(open(os.path.join(bdir, fn), encoding='utf-8'))
            except (OSError, ValueError): continue
            vals, notes = {}, {}
            for p in b.get('plants', []):                                               # a new plant gets its code when the batch applies: keyed by its names
                if isinstance(p, dict) and p.get('common_name'): vals[('new', p.get('common_name'), p.get('scientific_name'))] = {k: p.get(k) for k in FIELD_NAMES if p.get(k) not in (None, '', [])}
            for u in b.get('updates', []):
                if not isinstance(u, dict) or not u.get('code'): continue
                for k, pair in (u.get('set') or {}).items():
                    if isinstance(pair, list) and len(pair) == 2 and k in FIELD_NAMES:
                        vals.setdefault(u['code'], {})[k] = pair[1]
                        if u.get('note'): notes[(u['code'], k)] = u['note']
            out.append((f'Upgrade batch {b.get("id", fn)}', b.get('created') or '', b.get('author', 'Claude'), vals, notes))
    return out

def value_source(sources, p, field, value):
    """The latest list or batch that set this value for this plant (a row), or None (edited in the app, or set another way)."""
    f = FACT_BY_NAME[field]; want = fact_value_text(f[1], value); code = p['code']
    hit = None
    for label, when_, who, vals, notes in sources:
        row = vals.get(code) or vals.get(('new', p['common_name'], p['scientific_name'])) or {}
        v = row.get(field)
        if v is None: continue
        if fact_value_text(f[1], v) == want: hit = (label + (f' ({notes[(code, field)]})' if (code, field) in notes else ''), when_, who)
        else: hit = None                                                            # a later batch changed it away; a hand edit may have brought it back
    return hit

# ---------------------------------------------------------------- the one-time load
def facts_migrate(c):
    """Loads the facts table from what the record already knows, once (settings facts_loaded). Safe to call on every start."""
    if setting(c, 'facts_loaded', '') == '1': return 0
    n = 0
    # 1. the species_facts blobs (1.27.0): one row per section
    for r in c.execute('SELECT * FROM species_facts'):
        try: d = json.loads(r['data'])
        except ValueError: continue
        src = 'Researched for your plants by Claude (an upgrade batch)' if r['origin'] == 'researched' else f'Written by Claude when {r["written_by"] or "someone"} asked, from the Library'
        for sec in ('summary', 'uses', 'partners_good', 'partners_bad', 'deters', 'attracts', 'propagation', 'compost', 'breeding', 'sources'):
            v = d.get(sec)
            if sec == 'compost' and isinstance(v, dict) and not v.get('verdict'): v = None
            if sec == 'breeding' and isinstance(v, dict) and not v.get('text') and not v.get('patent'): v = None
            if fact_add(c, r['key'], r['kind'], 'about_' + sec, v, src, 'claude', r['written_by'] or 'Claude', r['written_at'] or now(), 'likely', 'accepted'): n += 1
    # 2. the care sheets in data/library/care (Claude, asked from the Library)
    try:
        for fn in os.listdir(CARE_DIR):
            if not fn.endswith('.json'): continue
            sh = care_get(fn[:-5]);
            if not sh or not isinstance(sh.get('sheet'), dict): continue
            key = species_key(sh.get('name') or '')
            if not key: continue
            src = f'Care sheet written by Claude ({sh.get("model") or "Claude"}), asked by {sh.get("asked_by") or "someone"} for {sh.get("place") or "your place"}'
            for sec, v in sh['sheet'].items():
                if fact_add(c, key, 'plant', 'sheet_' + sec, v, src, 'claude', sh.get('asked_by') or 'Claude', sh.get('written_at') or now(), 'likely', 'accepted'): n += 1
    except OSError: pass
    # 3. the plants' own care fields, where every plant of a species agrees
    sources = batch_sources()
    by_key = {}
    for p in c.execute("SELECT * FROM plants WHERE status='active'"):
        k = species_key(p['scientific_name'] or '')
        if k and ' ' in k: by_key.setdefault(k, []).append(p)                      # species only: a genus-wide fact from one pot would be a guess
    for key, plants in by_key.items():
        for field, kind, label, group in PLANT_FACT_FIELDS:
            vals = {fact_value_text(kind, p[field]) for p in plants if fact_value_text(kind, p[field])}
            if len(vals) != 1: continue
            text = vals.pop(); p = next(p for p in plants if fact_value_text(kind, p[field]) == text)
            hit = value_source(sources, p, field, p[field])
            if hit: src, when_, who, skind, conf = hit[0], hit[1] or p['updated_at'], hit[2], 'batch', 'likely'
            elif (p['updated_by'] or '').startswith('Claude'):            # a batch set it, but under names that have since changed (re-identified)
                src, when_, who, skind, conf = f'An upgrade batch, on {p["code"]} ({p["updated_by"]}); which one could not be traced', p['updated_at'], p['updated_by'], 'batch', 'likely'
            else: src, when_, who, skind, conf = f'Edited in the app on {p["code"]}' + (f' by {p["updated_by"]}' if p['updated_by'] else ''), p['updated_at'], p['updated_by'] or '', 'observation', 'likely'
            if fact_add(c, key, 'plant', field, p[field], src, skind, who, when_, conf, 'accepted', f'From {len(plants)} plant{"s" if len(plants) > 1 else ""} of this species'): n += 1
    c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('facts_loaded','1')")
    c.commit()
    if n: print(f'[facts] loaded {n} facts from the record', flush=True)
    return n

def facts_from_batch(c, b, who, ts):
    """A batch's `facts_add`: [{name, kind, field, value, source, source_kind, confidence, note}] (1.53.0); accepted rows."""
    n = 0
    for f in b.get('facts_add', []) or []:
        if not isinstance(f, dict): continue
        key = species_key(f.get('name') or '') or (f.get('key') or '').strip().lower()
        if fact_add(c, key, f.get('kind', 'plant'), f.get('field', ''), f.get('value'), f.get('source') or f'Upgrade batch {b.get("id", "")}', f.get('source_kind', 'batch'),
                    f.get('noted_by') or who, f.get('noted_at') or ts, f.get('confidence', 'likely'), 'accepted', f.get('note', '')): n += 1
    return n

# ---------------------------------------------------------------- a plant reads the species' facts for what it leaves empty
def species_fill(c, p):
    """For a plant dict: fills empty care fields from the species' accepted facts and lists them in p['from_species'] = {field: source}."""
    sci = p.get('scientific_name') or ''
    if not sci: return p
    F = facts_of(c, sci, p.get('code'))
    filled = {}
    for field, kind, label, group in PLANT_FACT_FIELDS:
        if fact_value_text(kind, p.get(field)): continue
        r = F.get(field)
        if r: p[field] = fact_value_out(kind, r['value']); filled[field] = {'source': r['source'], 'confidence': r['confidence'], 'label': label}
    p['from_species'] = filled
    return p

# ---------------------------------------------------------------- routes (read-only in 6a)
def fact_dict(r):
    f = FACT_BY_NAME.get(r['field'], (r['field'], 'text', r['field'], ''))
    return {'id': r['id'], 'key': r['key'], 'kind': r['kind'], 'field': r['field'], 'label': f[2], 'group': f[3], 'value': fact_value_out(f[1], r['value']), 'value_kind': f[1],
            'source': r['source'], 'source_kind': r['source_kind'], 'noted_by': r['noted_by'], 'noted_at': r['noted_at'], 'confidence': r['confidence'], 'status': r['status'],
            'replaces': r['replaces'], 'note': r['note']}

@app.route('/api/facts/rows')
def facts_rows():
    """?name=<scientific name> or ?code=P-001: the species' facts by group, each field with its accepted row and its history."""
    c = db()
    code = request.args.get('code') or None; sci = request.args.get('name') or ''
    if code and not sci:
        r = c.execute('SELECT scientific_name FROM plants WHERE code=?', (code,)).fetchone(); sci = r[0] if r else ''
    keys = facts_keys(sci)
    if code:
        lk = c.execute('SELECT key FROM facts_link WHERE code=?', (code,)).fetchone()
        if lk and lk[0] not in keys: keys.insert(0, lk[0])
    if not keys: return jsonify(keys=[], groups=[], total=0)
    rows = [fact_dict(r) for k in keys for r in c.execute('SELECT * FROM facts WHERE key=? ORDER BY field, id DESC', (k,))]
    groups = []
    for g in GROUPS:
        fields = []
        for field, kind, label, group in FACT_FIELDS:
            if group != g: continue
            mine = [r for r in rows if r['field'] == field]
            if not mine: continue
            acc = next((r for r in mine if r['status'] == 'accepted'), None)
            fields.append({'field': field, 'label': label, 'kind': kind, 'accepted': acc, 'history': [r for r in mine if r is not acc]})
        if fields: groups.append({'group': g, 'fields': fields})
    role, who = me_role()
    for gr in groups:
        for fl in gr['fields']:
            for h in fl['history']: h['mine'] = h['noted_by'] == who; h['can_accept'] = h['status'] == 'proposed' and role in ('owner', 'editor') and (role == 'owner' or not h['mine'])
    return jsonify(keys=keys, groups=groups, total=len(rows), accepted=sum(1 for r in rows if r['status'] == 'accepted'), proposed=sum(1 for r in rows if r['status'] == 'proposed'),
                   fields=[{'field': f[0], 'kind': f[1], 'label': f[2], 'group': f[3]} for f in FACT_FIELDS], source_kinds=SOURCE_KINDS, role=role)

def _csv_cell(v): return json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else ('' if v is None else str(v))

@app.route('/api/facts/export')
@app.route('/api/facts/export.csv')
def facts_export():
    """Every row, JSON (default) or CSV, so the knowledge can move to another install or be checked in a spreadsheet."""
    c = db()
    rows = [fact_dict(r) for r in c.execute('SELECT * FROM facts ORDER BY key, field, id')]
    if request.path.endswith('.csv'):
        out = io.StringIO(); w = csv.writer(out)
        cols = ['id', 'key', 'kind', 'field', 'label', 'group', 'value', 'source', 'source_kind', 'noted_by', 'noted_at', 'confidence', 'status', 'replaces', 'note']
        w.writerow(cols)
        for r in rows: w.writerow([_csv_cell(r[k]) for k in cols])
        return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=plant-facts.csv'})
    return jsonify(version=APP_VERSION, exported_at=now(), facts=rows)

# ---------------------------------------------------------------- 6b (1.54.0): proposing and reviewing
def me_role():
    u = getattr(g, 'user', None) or {}
    return u.get('role') or 'owner', editor()

def fact_key_for(b):
    """The key a proposal is for: ?name=<scientific name> (a plant's facts_link key when ?code= is given) or a key as is."""
    key = species_key(str(b.get('name') or ''))
    if b.get('code'):
        lk = db().execute('SELECT key FROM facts_link WHERE code=?', (b['code'],)).fetchone()
        if lk: key = lk[0]
    if not key and b.get('key'): key = str(b['key']).strip().lower()[:120]
    return key

@app.route('/api/facts/rows', methods=['POST'])
def facts_propose():
    """{name|key, code?, kind?, field, value, source, source_kind, confidence, note}: a proposed row (editors and the owner)."""
    c = db(); b = request.get_json(silent=True) or {}
    key = fact_key_for(b)
    if not key: abort(400, 'Which species? Give its scientific name.')
    field = str(b.get('field') or '')
    f = FACT_BY_NAME.get(field)
    if not f: abort(400, 'That is not a fact the record keeps.')
    kind = 'fungus' if b.get('kind') == 'fungus' else 'plant'
    if kind == 'fungus' and not field.startswith(('about_', 'sheet_')) and field not in ('native_range', 'danger_humans', 'danger_animals', 'conservation_status', 'invasive'):
        abort(400, 'A mushroom\'s facts are its description, where it grows and what it does; not care values.')
    text = fact_value_text(f[1], b.get('value'))
    if not text: abort(400, 'What is the value?')
    if kind == 'fungus' and FACTS_FUNGUS_NO.search(text): abort(400, 'Nothing in the record may say or suggest that a mushroom is edible, safe, tasty or medicinal.')
    if f[1] in ('int', 'num'):
        try: float(text)
        except ValueError: abort(400, f'{f[2]} needs a number.')
    source = str(b.get('source') or '').strip()
    if not source: abort(400, 'Where does this come from? A link, a book, a grower, or your own observation.')
    cur = c.execute("SELECT * FROM facts WHERE key=? AND field=? AND status='accepted'", (key, field)).fetchone()
    if cur and cur['value'] == text: abort(409, 'That is already the accepted value.')
    if c.execute("SELECT 1 FROM facts WHERE key=? AND field=? AND status='proposed' AND value=?", (key, field, text)).fetchone(): abort(409, 'That value is already proposed and waiting for review.')
    role, who = me_role()
    rid = fact_add(c, key, kind, field, text, source, b.get('source_kind', 'reference'), who, None, b.get('confidence', 'likely'), 'proposed', b.get('note', ''))
    audit_only(c, 'fact', field, cur['value'] if cur else None, text, who, f'Proposed for {key}: {f[2]} = {text[:80]} ({source[:60]})')
    c.commit()
    return jsonify(ok=True, id=rid, status='proposed', queue=queue_count(c)), 201

def queue_count(c): return c.execute("SELECT COUNT(*) FROM facts WHERE status='proposed'").fetchone()[0]

@app.route('/api/facts/rows/<int:rid>/accept', methods=['POST'])
def facts_accept(rid):
    """Another editor, or the owner, accepts a proposal: it becomes the field's accepted row and the old one is retired."""
    c = db()
    r = c.execute('SELECT * FROM facts WHERE id=?', (rid,)).fetchone()
    if not r or r['status'] != 'proposed': abort(404, 'That proposal is not waiting for review.')
    role, who = me_role()
    if role != 'owner' and r['noted_by'] == who: abort(403, 'Someone else has to accept your own proposal.')
    old = c.execute("SELECT id, value FROM facts WHERE key=? AND field=? AND status='accepted'", (r['key'], r['field'])).fetchone()
    if old: c.execute("UPDATE facts SET status='retired' WHERE id=?", (old['id'],))
    note = (request.get_json(silent=True) or {}).get('note', '')
    c.execute("UPDATE facts SET status='accepted', replaces=?, note=CASE WHEN ?<>'' THEN ? ELSE note END WHERE id=?", (old['id'] if old else None, str(note or ''), f"{r['note']} Accepted by {who}: {str(note or '')[:200]}".strip(), rid))
    audit_only(c, 'fact', r['field'], old['value'] if old else None, r['value'], who, f'Accepted for {r["key"]}: {FACT_BY_NAME[r["field"]][2]} (proposed by {r["noted_by"]})')
    c.commit()
    return jsonify(ok=True, id=rid, status='accepted', queue=queue_count(c))

@app.route('/api/facts/rows/<int:rid>/reject', methods=['POST'])
def facts_reject(rid):
    c = db()
    r = c.execute('SELECT * FROM facts WHERE id=?', (rid,)).fetchone()
    if not r or r['status'] != 'proposed': abort(404, 'That proposal is not waiting for review.')
    role, who = me_role()
    note = str((request.get_json(silent=True) or {}).get('note') or '')[:300]
    c.execute("UPDATE facts SET status='rejected', note=? WHERE id=?", (f"{r['note']} Rejected by {who}: {note}".strip(), rid))
    audit_only(c, 'fact', r['field'], None, r['value'], who, f'Rejected for {r["key"]}: {FACT_BY_NAME[r["field"]][2]} (proposed by {r["noted_by"]}){": " + note if note else ""}')
    c.commit()
    return jsonify(ok=True, id=rid, status='rejected', queue=queue_count(c))

@app.route('/api/facts/queue')
def facts_queue():
    """Every proposal waiting for review, newest first, with the value it would replace and whether this person may accept it."""
    c = db(); role, who = me_role()
    out = []
    for r in c.execute("SELECT * FROM facts WHERE status='proposed' ORDER BY id DESC LIMIT 200"):
        d = fact_dict(r)
        cur = None                                                                 # the value it would replace: the species' own, else the genus's
        for k in [r['key']] + ([r['key'].split(' ')[0]] if ' ' in r['key'] else []):
            cur = c.execute("SELECT * FROM facts WHERE key=? AND field=? AND status='accepted'", (k, r['field'])).fetchone()
            if cur: break
        d['current'] = fact_dict(cur) if cur else None
        d['mine'] = r['noted_by'] == who
        d['can_accept'] = role in ('owner', 'editor') and (role == 'owner' or not d['mine'])
        out.append(d)
    return jsonify(queue=out, count=len(out), role=role)

@app.route('/api/facts/import', methods=['POST'])
def facts_import():
    """The export's JSON ({facts: [...]}) or a list of rows: each becomes a proposed row for review, never an accepted one; rows whose
    value is already accepted or proposed for that field are skipped. Editors and the owner."""
    c = db(); b = request.get_json(silent=True) or {}
    rows = b.get('facts') if isinstance(b, dict) else b
    if not isinstance(rows, list): abort(400, 'Send the JSON from /api/facts/export.')
    role, who = me_role(); added = skipped = 0
    for x in rows[:5000]:
        if not isinstance(x, dict): continue
        key = str(x.get('key') or '').strip().lower() or species_key(str(x.get('name') or ''))
        f = FACT_BY_NAME.get(str(x.get('field') or ''))
        if not key or not f: skipped += 1; continue
        kind = 'fungus' if x.get('kind') == 'fungus' else 'plant'
        text = fact_value_text(f[1], x.get('value'))
        if not text or (kind == 'fungus' and FACTS_FUNGUS_NO.search(text)): skipped += 1; continue
        if c.execute("SELECT 1 FROM facts WHERE key=? AND field=? AND value=? AND status IN ('accepted','proposed')", (key, f[0], text)).fetchone(): skipped += 1; continue
        src = str(x.get('source') or '').strip() or f'Imported by {who}'
        if fact_add(c, key, kind, f[0], text, src, x.get('source_kind', 'reference'), x.get('noted_by') or who, None, x.get('confidence', 'likely'), 'proposed',
                    f'Imported by {who}' + (f'; noted by {x["noted_by"]} on {x["noted_at"]}' if x.get('noted_by') else '')): added += 1
        else: skipped += 1
    if added: audit_only(c, 'fact', 'import', None, str(added), who, f'Imported {added} facts for review ({skipped} skipped)')
    c.commit()
    return jsonify(ok=True, added=added, skipped=skipped, queue=queue_count(c))
