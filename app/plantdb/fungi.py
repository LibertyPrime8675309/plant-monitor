"""Mushroom finds.
Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- 1.22.0: mushroom finds (a page of their own) and library notes
# A find is one mushroom (or a cluster of them) seen somewhere: the yard, one of your plant pots, or anywhere else. Its photos go in
# data/photos like the plants', but in their own table. The location can come from the phone ("Use my location") or from the
# GPS in a photo, read before the photo is saved without its EXIF data. Nothing here ever says a mushroom is safe to eat.
FUNGI_FIELDS = [
    ('name', 'text', 'Name'), ('scientific_name', 'text', 'Scientific name'), ('id_status', 'enum', 'How sure is the name?'),
    ('found_on', 'date', 'Found on'), ('place_kind', 'enum', 'Where'), ('plant_code', 'text', 'Which plant pot'),
    ('place', 'text', 'Where exactly'), ('lat', 'num', 'Latitude'), ('lon', 'num', 'Longitude'),
    ('substrate', 'enum', 'Growing on'), ('near', 'text', 'Trees or plants nearby'), ('abundance', 'enum', 'How many'),
    ('cap_size', 'text', 'Cap width'), ('cap_colour', 'text', 'Cap colour and surface'), ('underside', 'enum', 'Under the cap'),
    ('ring', 'enum', 'Ring on the stem'), ('volva', 'enum', 'Cup or sac at the base'), ('spore_print', 'text', 'Spore print colour'),
    ('bruising', 'text', 'Colour change when cut or bruised'), ('smell', 'text', 'Smell'), ('notes', 'long', 'Notes')]
FUNGI_ENUMS = {
    'id_status': ['Not identified yet', 'A guess', 'Fairly sure', 'Confirmed by an expert'],
    'place_kind': ['In the yard', 'In a plant pot', 'Somewhere else'],
    'substrate': ['Soil or grass', 'Mulch or wood chips', 'Dead wood or a stump', 'A living tree', 'Potting mix', 'Compost or dung', 'Leaf litter', 'Something else'],
    'abundance': ['Just one', 'A few', 'A cluster', 'A ring or arc', 'Many, scattered'],
    'underside': ['Gills', 'Pores (like a sponge)', 'Teeth or spines', 'Smooth or wrinkled', 'No cap (puffball, coral, crust, cup)', 'Not checked'],
    'ring': ['Yes', 'No', 'Not checked'], 'volva': ['Yes', 'No', 'Not checked (dig around the base to see)']}
FUNGI_NAMES = [f[0] for f in FUNGI_FIELDS]
FUNGI_LABEL = {f[0]: f[2] for f in FUNGI_FIELDS}
FUNGI_SCHEMA = """
CREATE TABLE IF NOT EXISTS fungi_finds(
  id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL UNIQUE, %s,
  status TEXT NOT NULL DEFAULT 'active', version INTEGER NOT NULL DEFAULT 1,
  created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS fungi_photos(
  id INTEGER PRIMARY KEY AUTOINCREMENT, find_id INTEGER NOT NULL, file TEXT NOT NULL, caption TEXT NOT NULL DEFAULT '',
  is_primary INTEGER NOT NULL DEFAULT 0, gps_lat REAL, gps_lon REAL, taken_at TEXT, added_by TEXT NOT NULL, added_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS species_notes(
  name TEXT PRIMARY KEY, notes TEXT NOT NULL DEFAULT '', tags TEXT NOT NULL DEFAULT '', updated_by TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS wishlist(
  name TEXT PRIMARY KEY, common_name TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', where_seen TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'want', added_by TEXT NOT NULL, added_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT);
""" % ',\n  '.join(f"{n} {'REAL' if k == 'num' else 'TEXT'}" for n, k, _ in FUNGI_FIELDS)

def fungi_norm(c, n, v):
    kind = dict((f[0], f[1]) for f in FUNGI_FIELDS)[n]
    if v is None: v = ''
    if kind == 'num':
        if v == '': return None
        try: x = round(float(v), 6)
        except (TypeError, ValueError): abort(400, f'{FUNGI_LABEL[n]} must be a number')
        if not (-90 <= x <= 90 if n == 'lat' else -180 <= x <= 180): abort(400, f'{FUNGI_LABEL[n]} is out of range')
        return x
    v = str(v).strip()[:4000 if kind == 'long' else 300]
    if kind == 'enum' and v and v not in FUNGI_ENUMS[n]: abort(400, f'{FUNGI_LABEL[n]}: choose one of the listed answers')
    if kind == 'date' and v:
        try: date.fromisoformat(v)
        except ValueError: abort(400, 'Found on must be a date like 2026-10-31')
    if n == 'plant_code' and v and not c.execute('SELECT 1 FROM plants WHERE code=?', (v,)).fetchone(): abort(400, f'There is no plant {v}')
    return v

def find_row(c, code):
    r = c.execute('SELECT * FROM fungi_finds WHERE code=?', (code,)).fetchone()
    if not r: abort(404, 'There is no mushroom find ' + code)
    return r

def find_photos(c, fid):
    return [dict(x) for x in c.execute('SELECT * FROM fungi_photos WHERE find_id=? ORDER BY is_primary DESC, id', (fid,))]

def find_dict(c, r, full=True):
    d = {k: r[k] for k in ['code'] + FUNGI_NAMES + ['status', 'version', 'created_by', 'created_at', 'updated_by', 'updated_at']}
    ph = find_photos(c, r['id'])
    d['photo'] = ph[0]['file'] if ph else None; d['photo_count'] = len(ph)
    if full:
        d['photos'] = ph
        d['plant'] = plant_brief(c, r['plant_code']) if r['plant_code'] else None
    return d

def exif_info(raw):
    """(lat, lon, taken_at) from a photo's EXIF data, or Nones. Read before the photo is saved, which drops EXIF."""
    try:
        im = Image.open(io.BytesIO(raw)); ex = im.getexif()
        when = ex.get(306) or ex.get_ifd(0x8769).get(36867)
        g = ex.get_ifd(0x8825)
        def deg(v): return float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
        lat = lon = None
        if g and 2 in g and 4 in g:
            lat = deg(g[2]) * (-1 if g.get(1) == 'S' else 1); lon = deg(g[4]) * (-1 if g.get(3) == 'W' else 1)
            if not (-90 <= lat <= 90 and -180 <= lon <= 180) or (lat == 0 and lon == 0): lat = lon = None
        t = None
        if when:
            try: t = datetime.strptime(str(when).strip(), '%Y:%m:%d %H:%M:%S').strftime('%Y-%m-%dT%H:%M')
            except ValueError: t = None
        return (round(lat, 6) if lat is not None else None, round(lon, 6) if lon is not None else None, t)
    except Exception:
        return None, None, None

class _Upload:                                    # save_image() wants something with .stream and .filename
    def __init__(self, raw, name): self.stream, self.filename = io.BytesIO(raw), name

@app.route('/api/fungi', methods=['GET', 'POST'])
def fungi_list():
    c = db()
    if request.method == 'POST':
        b = (request.get_json(silent=True) or {}).get('fields') or {}
        vals = {n: fungi_norm(c, n, b.get(n)) for n in FUNGI_NAMES}
        if not vals['found_on']: vals['found_on'] = local_today(c).isoformat()
        if not vals['id_status']: vals['id_status'] = 'Not identified yet'
        n = (c.execute("SELECT MAX(CAST(SUBSTR(code,3) AS INTEGER)) FROM fungi_finds").fetchone()[0] or 0) + 1
        code, who, t = f'F-{n:03d}', editor(), now()
        cols = ['code'] + FUNGI_NAMES + ['created_by', 'created_at', 'updated_by', 'updated_at']
        c.execute(f"INSERT INTO fungi_finds({','.join(cols)}) VALUES({','.join('?' * len(cols))})", [code] + [vals[k] for k in FUNGI_NAMES] + [who, t, who, t])
        audit_only(c, 'fungi', 'find', None, code, who, f"Mushroom find {code} added: {vals['name'] or 'not identified'}", None, code)
        c.commit()
        return jsonify(find_dict(c, find_row(c, code))), 201
    status = request.args.get('status', 'active')
    rows = c.execute('SELECT * FROM fungi_finds' + ('' if status == 'all' else ' WHERE status=?') + ' ORDER BY found_on DESC, id DESC',
                     () if status == 'all' else (status,)).fetchall()
    return jsonify(finds=[find_dict(c, r, False) for r in rows], enums=FUNGI_ENUMS, fields=[{'name': n, 'kind': k, 'label': l} for n, k, l in FUNGI_FIELDS])

@app.route('/api/fungi/<code>', methods=['GET', 'PUT'])
def fungi_one(code):
    c = db()
    r = find_row(c, code)
    if request.method == 'PUT':
        b = request.get_json(silent=True) or {}
        f, who, ch, nclash = b.get('fields') or {}, editor(), [], 0
        if int(b.get('base_version', r['version'])) != r['version']:
            if not isinstance(b.get('base_values'), dict):
                abort(409, f'Someone else changed {code} while you were editing. Reload the page to see their changes, then make yours again.')
            f, nclash = merge_fields(c, 'fungi', code, r, f, b['base_values'], lambda n: FUNGI_LABEL.get(n, n), lambda n, v: fungi_norm(c, n, v), (r['updated_by'], r['updated_at']))
        for n in FUNGI_NAMES:
            if n not in f: continue
            v = fungi_norm(c, n, f[n])
            if (r[n] if r[n] is not None else '') != (v if v is not None else ''): ch.append((n, r[n], v))
        if ch:
            c.execute(f"UPDATE fungi_finds SET {', '.join(n + '=?' for n, _, _ in ch)}, version=version+1, updated_by=?, updated_at=? WHERE id=?",
                      [v for _, _, v in ch] + [who, now(), r['id']])
            for n, o, v in ch:
                audit_only(c, 'fungi', n, None if o is None else str(o)[:500], None if v is None else str(v)[:500], who, f'{code}: {FUNGI_LABEL[n]} changed', None, code)
        if ch or nclash: c.commit()
        return jsonify(find_dict(c, find_row(c, code)) | {'changed': len(ch), 'conflicts': nclash})
    return jsonify(find_dict(c, r) | {'enums': FUNGI_ENUMS, 'fields': [{'name': n, 'kind': k, 'label': l} for n, k, l in FUNGI_FIELDS]})

@app.route('/api/fungi/<code>/status', methods=['POST'])
def fungi_status(code):
    c = db(); r = find_row(c, code)
    to = 'archived' if (request.get_json(silent=True) or {}).get('archived') else 'active'
    c.execute('UPDATE fungi_finds SET status=?, version=version+1, updated_by=?, updated_at=? WHERE id=?', (to, editor(), now(), r['id']))
    audit_only(c, 'fungi', 'status', r['status'], to, editor(), f'{code} ' + ('archived' if to == 'archived' else 'brought back'), None, code)
    c.commit()
    return jsonify(find_dict(c, find_row(c, code)))

@app.route('/api/fungi/<code>/photos', methods=['POST'])
def fungi_add_photos(code):
    c = db(); r = find_row(c, code)
    files = request.files.getlist('files')
    if not files: abort(400, 'Choose at least one photo')
    who, cap = editor(), request.form.get('caption', '').strip()[:200]
    has = c.execute('SELECT 1 FROM fungi_photos WHERE find_id=? AND is_primary=1', (r['id'],)).fetchone()
    added = []
    for i, f in enumerate(files):
        raw = f.read()
        lat, lon, taken = exif_info(raw)
        name = save_image(_Upload(raw, f.filename))
        pid = c.execute('INSERT INTO fungi_photos(find_id,file,caption,is_primary,gps_lat,gps_lon,taken_at,added_by,added_at) VALUES(?,?,?,?,?,?,?,?,?)',
                        (r['id'], name, cap, 0 if has or i else 1, lat, lon, taken, who, now())).lastrowid
        added.append({'id': pid, 'file': name, 'gps_lat': lat, 'gps_lon': lon, 'taken_at': taken})
    c.execute('UPDATE fungi_finds SET version=version+1, updated_by=?, updated_at=? WHERE id=?', (who, now(), r['id']))
    audit_only(c, 'fungi', 'photo', None, ', '.join(a['file'] for a in added), who, f'{code}: {len(added)} photo(s) added', None, code)
    gps = next((a for a in added if a['gps_lat'] is not None), None)
    located = False
    if gps and r['lat'] is None and request.form.get('use_location', '1') != '0':     # 1.24.0: the find gets the photo's location (also offline)
        c.execute('UPDATE fungi_finds SET lat=?, lon=?, version=version+1 WHERE id=?', (gps['gps_lat'], gps['gps_lon'], r['id']))
        audit_only(c, 'fungi', 'lat', None, f"{gps['gps_lat']}, {gps['gps_lon']}", who, f'{code}: location taken from a photo', None, code)
        located = True
    c.commit()
    return jsonify(find_dict(c, find_row(c, code)) | {'added': added, 'located': located}), 201

@app.route('/api/fungi/photos/<int:pid>', methods=['PATCH', 'DELETE'])
def fungi_photo(pid):
    c = db()
    ph = c.execute('SELECT * FROM fungi_photos WHERE id=?', (pid,)).fetchone()
    if not ph: abort(404, 'photo not found')
    r = c.execute('SELECT * FROM fungi_finds WHERE id=?', (ph['find_id'],)).fetchone()
    who = editor()
    if request.method == 'DELETE':
        c.execute('DELETE FROM fungi_photos WHERE id=?', (pid,))
        src = os.path.join(PHOTO_DIR, ph['file'])
        if os.path.exists(src): shutil.move(src, os.path.join(TRASH_DIR, ph['file']))
        if not c.execute('SELECT 1 FROM fungi_photos WHERE find_id=? AND is_primary=1', (r['id'],)).fetchone():
            c.execute('UPDATE fungi_photos SET is_primary=1 WHERE id=(SELECT MIN(id) FROM fungi_photos WHERE find_id=?)', (r['id'],))
        audit_only(c, 'fungi', 'photo', ph['file'], None, who, f"{r['code']}: photo removed (file kept in photos_deleted)", None, r['code'])
    else:
        b = request.get_json(silent=True) or {}
        if 'caption' in b:
            c.execute('UPDATE fungi_photos SET caption=? WHERE id=?', (str(b['caption']).strip()[:200], pid))
        if b.get('is_primary'):
            c.execute('UPDATE fungi_photos SET is_primary=0 WHERE find_id=?', (r['id'],)); c.execute('UPDATE fungi_photos SET is_primary=1 WHERE id=?', (pid,))
            audit_only(c, 'fungi', 'photo', None, ph['file'], who, f"{r['code']}: main photo changed", None, r['code'])
    c.execute('UPDATE fungi_finds SET version=version+1, updated_by=?, updated_at=? WHERE id=?', (who, now(), r['id']))
    c.commit()
    return jsonify(find_dict(c, find_row(c, r['code'])))
