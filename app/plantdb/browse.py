"""Prototype (proto/browse-risk): which of the plants are likely to be eaten by rabbits, rats, mice, deer and other browsers.
Ethan's plants are being eaten (November 2026). This gives each plant a rough risk, with the reason in words, from the plant's
genus (and a few species), so it works for every plant and for plants added later. It stores nothing: the table below is
gardeners' and extension-service knowledge, not a test, and says so. Nothing here suggests harming an animal: a plant is called
"toxic" only to say animals usually leave it alone.

1.57.0 (Ethan's answers, November 11): the risk can be set per plant (the field browse_risk beats the usual for its kind), every sighting of a
plant being eaten is logged with the pest, the damage and pictures as evidence, and on a cool evening Today lists the plants to cover."""
from .core import *   # noqa: F401,F403

RISKS = BROWSE_RISKS                     # core.py: also the values of the plant field browse_risk
RISK_WORD = {'Low': 'Low risk: usually left alone', 'Moderate': 'Some risk: eaten when other food is short, or when young',
             'High': 'High risk: a favourite', 'Unknown': 'Not known yet'}

OX = 'Calcium oxalate crystals burn the mouth, so animals usually leave it alone.'
# key (lowercase genus, or "genus species") -> (risk, why). Longer keys are tried first.
BROWSE = {
    'dieffenbachia': ('Low', OX), 'alocasia': ('Low', OX), 'philodendron': ('Low', OX), 'monstera': ('Low', OX),
    'aglaonema': ('Low', OX), 'spathiphyllum': ('Low', OX), 'syngonium': ('Low', OX), 'rhaphidophora': ('Low', OX),
    'scindapsus': ('Low', OX), 'epipremnum': ('Low', OX),
    'zamioculcas': ('Low', 'Contains oxalates and has tough, glossy leaves; rarely eaten.'),
    'aloe': ('Low', 'Bitter latex under the skin; rarely eaten.'), 'aloiampelos': ('Low', 'Bitter latex, like aloe; rarely eaten.'),
    'haworthiopsis': ('Low', 'Tough, gritty leaves with little to eat; usually skipped, though mice may chew young ones.'),
    'haworthia': ('Low', 'Tough leaves with little to eat; usually skipped.'),
    'euphorbia': ('Low', 'Milky latex that irritates the mouth, and spines on crown of thorns; a strong deterrent.'),
    'adenium': ('Low', 'The sap is poisonous, so animals avoid it.'),
    'myrtillocactus': ('Low', 'Spiny. Rodents sometimes gnaw the base of a cactus, so keep it off the ground.'),
    'opuntia': ('Moderate', 'Spines put most animals off, but rabbits, rats and deer chew the pads in dry spells (chewed pads were seen).'),
    'bougainvillea': ('Low', 'Thorny stems. New soft shoots are sometimes nibbled.'),
    'ficus lyrata': ('Low', 'Milky sap irritates the mouth, so it is rarely eaten.'),
    'ficus carica': ('Moderate', 'The fruit and young leaves are eaten by birds, deer and rabbits, though the sap puts some off.'),
    'ravenea': ('Low', 'Tough fronds; seedlings are softer and can be nibbled.'), 'dypsis': ('Low', 'Tough fronds; seedlings are softer and can be nibbled.'),
    'nephrolepis': ('Low', 'Ferns are usually left alone by rabbits and deer.'),
    'rosa': ('Moderate', 'Thorns help, but rabbits eat young canes and buds, and deer eat the flowers.'),
    'vitis': ('High', 'Leaves, shoots and fruit are eaten by rabbits, deer, birds and raccoons.'),
    'ipomoea batatas': ('High', 'Sweet potato leaves are eaten by rabbits, rodents and deer.'),
    'ipomoea': ('Moderate', 'Morning glory leaves are mildly toxic, but seedlings are nibbled.'),
    'caesalpinia': ('Moderate', 'Soft feathery leaves on a legume; the seeds are poisonous, the leaves are sometimes browsed.'),
    'erythrostemon': ('Moderate', 'Soft feathery leaves on a legume; the seeds are poisonous, the leaves are sometimes browsed.'),
    'moringa': ('High', 'The leaves are food for people and livestock, so rabbits and deer will eat them.'),
    'senna': ('Moderate', 'Tender compound leaves on a legume; young plants are browsed.'),
    'begonia': ('High', 'Soft leaves with no defence; feeding holes were seen on yours.'),
    'plectranthus': ('High', 'Coleus is soft and tasty; rabbits and rodents go for it.'),
    'goeppertia': ('High', 'Soft tropical leaves, not toxic (ASPCA lists calatheas as pet-safe).'),
    'calathea': ('High', 'Soft tropical leaves, not toxic (ASPCA lists calatheas as pet-safe).'),
    'cosmos': ('Moderate', 'Rabbits eat young plants and deer nibble flowers; older plants are left more.'),
    'hibiscus': ('High', 'Tender leaves and buds; a well-known rabbit and deer favourite.'),
    'portulacaria': ('High', 'Elephant bush is edible and juicy; many animals eat it (elephants do).'),
    'tradescantia': ('Moderate', 'The sap can irritate skin, but the stems are soft and fast-growing, and are chewed.'),
    'graptopetalum': ('Moderate', 'Juicy leaves: rats and mice chew succulents, most in dry spells.'),
    'graptosedum': ('Moderate', 'Juicy leaves: rats and mice chew succulents, most in dry spells.'),
    'aeonium': ('Moderate', 'Juicy leaves: rats, mice and rabbits chew succulents, most in dry spells.'),
    'echeveria': ('Moderate', 'Juicy leaves: rats and mice chew succulents, most in dry spells.'),
    'kalanchoe': ('Low', 'Mildly toxic; usually left alone.'),
    'sedum': ('Moderate', 'Juicy leaves: rats and mice chew succulents, most in dry spells.'),
    'cucurbita': ('High', 'Squash and gourd leaves and fruit are eaten by rabbits, rodents and deer.'),
    'cucurbitaceae': ('High', 'Squash, melon and gourd leaves and fruit are eaten by rabbits, rodents and deer (bite holes seen).'),
    'cucumis': ('High', 'Melon leaves and fruit are eaten by rabbits, rodents and deer.'),
    'phalaenopsis': ('Moderate', 'Mice and rats chew flower spikes and root tips, and slugs eat the leaves.'),
    'pachira': ('Moderate', 'Not toxic, but the leaves are tough. Young plants can be nibbled.'),
}
COMMON = [('squash', 'cucurbita'), ('gourd', 'cucurbita'), ('melon', 'cucurbita'), ('coleus', 'plectranthus'), ('hibiscus', 'hibiscus'),
          ('elephant bush', 'portulacaria'), ('purple heart', 'tradescantia'), ('begonia', 'begonia'), ('philodendron', 'philodendron'),
          ('aloe', 'aloe'), ('prickly pear', 'opuntia'), ('crown of thorns', 'euphorbia'), ('calathea', 'calathea'), ('arrowhead', 'syngonium'),
          ('dieffenbachia', 'dieffenbachia'), ('alocasia', 'alocasia'), ('fiddle', 'ficus lyrata'), ('rose', 'rosa')]

def browse_for(scientific, common=''):
    """(risk, why) for a plant from its scientific name (genus or species), else its common name; ('Unknown', '') when not known."""
    words = re.sub(r"[^a-z ]", ' ', str(scientific or '').lower().replace('×', ' ').replace(' x ', ' ')).split()
    words = [w for w in words if w not in ('sp', 'spp', 'cv', 'cultivar', 'possibly', 'probable', 'unconfirmed', 'or')]
    words = [w[1:] if w.startswith('x') and w[1:] in BROWSE else w for w in words]       # xGraptosedum: a hybrid genus
    for n in (2, 1):                                  # genus + species first, then genus; a leading "x" (hybrid) is dropped
        for i in range(0, max(1, len(words) - n + 1)):
            key = ' '.join(words[i:i + n])
            if key in BROWSE: return BROWSE[key]
    low = str(common or '').lower()
    for word, key in COMMON:
        if word in low: return BROWSE[key]
    return ('Unknown', '')

BROWSE_PESTS = ['Rabbit', 'Rat', 'Mouse', 'Squirrel', 'Deer', 'Bird', 'Snail or slug', 'Insect', 'Other', 'Not sure']
BROWSE_DAMAGE = ['Leaves eaten', 'Stem chewed or gnawed', 'Flowers or fruit eaten', 'Dug up or knocked over', 'Droppings or tracks only', 'Other']
SEEN_DAYS = 60                              # sightings counted on the page and the plant's line
TONIGHT_FROM_HOUR = 16                      # "evening" on Today starts at 4 pm, the home's time
BROWSE_SCHEMA = """
CREATE TABLE IF NOT EXISTS pest_sightings(
  id INTEGER PRIMARY KEY AUTOINCREMENT, plant_code TEXT NOT NULL, seen_on TEXT NOT NULL, pest TEXT NOT NULL DEFAULT 'Not sure',
  damage TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '', photos TEXT NOT NULL DEFAULT '[]', created_by TEXT, created_at TEXT);
CREATE INDEX IF NOT EXISTS pest_sightings_plant ON pest_sightings(plant_code, seen_on);
"""

def browse_tables(c): c.executescript(BROWSE_SCHEMA)       # init_db() runs this too; here for a database opened by an older mock

def sighting_dict(r):
    try: ph = json.loads(r['photos'] or '[]')
    except ValueError: ph = []
    return {'id': r['id'], 'plant': r['plant_code'], 'seen_on': r['seen_on'], 'pest': r['pest'], 'damage': r['damage'], 'note': r['note'],
            'photos': [f for f in ph if isinstance(f, str)], 'by': r['created_by'], 'at': r['created_at']}

def sightings(c, plant=None, days=SEEN_DAYS):
    browse_tables(c)
    since = (local_today(c) - timedelta(days=days)).isoformat()
    q, a = 'SELECT * FROM pest_sightings WHERE seen_on>=?', [since]
    if plant: q += ' AND plant_code=?'; a.append(plant)
    return [sighting_dict(r) for r in c.execute(q + ' ORDER BY seen_on DESC, id DESC', a)]

RAISE_TO_MODERATE = 1                       # eaten this many times in the last 60 days: at least "Some risk"
RAISE_TO_HIGH = 3                           # eaten this many times: "High". Worked out each time, so it falls back when the sightings age out

def raised_risk(base, n):
    """(risk, raised): the risk once sightings are counted. Sightings only ever raise it, even over one set by hand."""
    want = 'High' if n >= RAISE_TO_HIGH else 'Moderate' if n >= RAISE_TO_MODERATE else None
    if want and (RISKS.index(want) > RISKS.index(base) if base in RISKS else True): return want, True
    return base, False

def browse_row(r, seen=()):
    """The risk of a plant: the one set by hand if there is one, else the usual for its kind, raised by what was seen eating it.
    `seen` is its sightings in the last 60 days."""
    usual, why = browse_for(r['scientific_name'], r['common_name'])
    own = r['browse_risk'] if r['browse_risk'] in RISKS else ''
    base = own or usual
    risk, raised = raised_risk(base, len(seen))
    pests = sorted({x['pest'] for x in seen if x['pest'] != 'Not sure'})
    return {'code': r['code'], 'name': r['common_name'], 'sci': r['scientific_name'] or '', 'risk': risk, 'word': RISK_WORD[risk], 'why': why,
            'own': own, 'usual': usual, 'base': base, 'raised': raised, 'source': 'you' if own else 'kind', 'site': r['site'] or 'Outdoors',
            'seen': {'count': len(seen), 'last': seen[0]['seen_on'] if seen else None, 'pests': pests}}

def push_cover(c, hour=None):
    """From 4 pm, once a day for each home: the plants outside to cover tonight (the same list as on Today). Sent to everyone who wants
    "Cover plants at night" notifications at that home. `hour` is for tests."""
    for H in homes(c):
        local = datetime.now(tzinfo(H['tz']))
        if (local.hour if hour is None else hour) < TONIGHT_FROM_HOUR: continue
        with place_for(H['id']):
            B = browse_report(c, tonight=True)
        if not B['tonight']: continue
        if not push_once(c, f'cover:{H["id"]}:{local.date().isoformat()}', 2): continue
        names = [p['name'].split(' (')[0] for p in B['tonight']]
        n = len(names)
        push_send(c, 'cover', f'Tonight: cover {n} plant{"s" if n != 1 else ""} at {H["name"].split(",")[0]}',
                  ', '.join(names[:5]) + ('…' if n > 5 else '') + '. Rabbits, rats and mice feed at night.', '#/', H['id'], tag='cover')

def evening_now(c):
    return datetime.now(tzinfo(location(c)['tz'])).hour >= TONIGHT_FROM_HOUR

def browse_report(c, code=None, tonight=False):
    at, at_args = plants_at(c, location(c))
    if code: at, at_args = ' AND code=?', [code]
    rows = c.execute("SELECT * FROM plants WHERE status='active'" + at + ' ORDER BY code', at_args).fetchall()
    allseen = sightings(c, code)
    by = {}
    for x in allseen: by.setdefault(x['plant'], []).append(x)
    ps = []
    for r in rows:
        x = browse_row(r, by.get(r['code'], ()))
        x['photo'] = (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (r['id'],)).fetchone() or [None])[0]
        ps.append(x)
    counts = {k: sum(1 for p in ps if p['risk'] == k) for k in RISKS + ['Unknown']}
    out = {'plants': ps, 'counts': counts, 'risks': RISKS, 'words': RISK_WORD, 'pests': BROWSE_PESTS, 'damage': BROWSE_DAMAGE, 'days': SEEN_DAYS,
           'today': local_today(c).isoformat(), 'evening': evening_now(c)}
    if not code:
        names = {p['code']: p['name'] for p in ps}
        out['sightings'] = [dict(x, name=names.get(x['plant'], x['plant'])) for x in allseen if x['plant'] in names]
        out['by_pest'] = {k: sum(1 for x in out['sightings'] if x['pest'] == k) for k in BROWSE_PESTS if any(x['pest'] == k for x in out['sightings'])}
    if tonight:
        # what to cover tonight: plants outside that are high risk (set by hand or usual), or were eaten in the last two weeks
        two = (local_today(c) - timedelta(days=14)).isoformat()
        out['tonight'] = [p for p in ps if p['site'] in ('Outdoors', 'Covered porch') and (p['risk'] == 'High' or (p['seen']['last'] or '') >= two)]
    return out

@app.route('/api/browse')
def browse():
    """The browse risk of every active plant here (?plant=CODE for one; ?tonight=1 adds the plants to cover tonight), the pests seen
    eating them in the last 60 days, and the choices for logging one. Read-only, so viewers may use it."""
    return jsonify(browse_report(db(), request.args.get('plant') or None, request.args.get('tonight') == '1'))

def photo_names(c, code, names):
    """The picture files of a sighting: a picture of the plant already in the record, or one sent through /api/browse/photo (which
    saves it as up_<hex>.jpg). Anything else is refused."""
    out = []
    mine = {r[0] for r in c.execute('SELECT file FROM photos')}
    for f in (names or [])[:12]:
        f = str(f)
        if f in out: continue
        if f not in mine and not re.fullmatch(r'up_[0-9a-f]{16}\.jpg', f): abort(400, 'One of the pictures is not one this plant record knows')
        if not os.path.isfile(os.path.join(PHOTO_DIR, f)): abort(400, 'One of the pictures is missing')
        out.append(f)
    return out

@app.route('/api/browse/photo', methods=['POST'])
def browse_photo():
    """One picture to use as evidence in a sighting. It is kept like any photo but is not added to the plant's own pictures."""
    f = request.files.get('file')
    if not f: abort(400, 'no file')
    return jsonify(file=save_image(f)), 201

@app.route('/api/browse/sightings', methods=['GET', 'POST'])
def browse_sightings():
    """GET ?plant=CODE&days=60: sightings, newest first. POST {plant, seen_on, pest, damage, note, photos}: log one (not for viewers)."""
    c = db(); browse_tables(c)
    if request.method == 'GET':
        return jsonify(sightings(c, request.args.get('plant') or None, max(1, min(int(request.args.get('days', SEEN_DAYS)), 3650))))
    b = request.get_json(silent=True) or {}
    r = plant_row(c, str(b.get('plant') or ''))
    day = str(b.get('seen_on') or local_today(c).isoformat())
    try: date.fromisoformat(day)
    except ValueError: abort(400, 'The date must look like 2026-11-11')
    if day > local_today(c).isoformat(): abort(400, 'That date is in the future')
    pest = str(b.get('pest') or 'Not sure')
    if pest not in BROWSE_PESTS: abort(400, 'The pest must be one of: ' + ', '.join(BROWSE_PESTS))
    damage = str(b.get('damage') or '')
    if damage and damage not in BROWSE_DAMAGE: abort(400, 'The damage must be one of: ' + ', '.join(BROWSE_DAMAGE))
    note = str(b.get('note') or '').strip()[:500]
    files = photo_names(c, r['code'], b.get('photos'))
    who = editor()
    sid = c.execute('INSERT INTO pest_sightings(plant_code,seen_on,pest,damage,note,photos,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)',
                    (r['code'], day, pest, damage, note, json.dumps(files), who, now())).lastrowid
    audit_only(c, 'pest_seen', 'pest_sightings', None, f'{pest}: {damage or "no damage given"} on {day}', who,
               f'Seen eating: {pest}' + (f', {damage.lower()}' if damage else '') + (f' ({len(files)} picture(s))' if files else ''), r['id'], r['code'])
    c.commit()
    return jsonify(sighting_dict(c.execute('SELECT * FROM pest_sightings WHERE id=?', (sid,)).fetchone())), 201

@app.route('/api/browse/sightings/<int:sid>', methods=['DELETE'])
def browse_sighting_delete(sid):
    c = db(); browse_tables(c)
    x = c.execute('SELECT * FROM pest_sightings WHERE id=?', (sid,)).fetchone()
    if not x: abort(404, 'No such sighting')
    r = plant_row(c, x['plant_code'])
    c.execute('DELETE FROM pest_sightings WHERE id=?', (sid,))
    audit_only(c, 'pest_seen_removed', 'pest_sightings', f'{x["pest"]} on {x["seen_on"]}', None, editor(), 'Sighting removed', r['id'], r['code'])
    c.commit()
    return jsonify(ok=True)
