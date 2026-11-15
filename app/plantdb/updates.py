"""1.58.0 (November 12 review, item 12; Ethan's choices of November 13 and 14, 2026): updates from Claude that arrive as a file.

A correction to a plant's page used to travel in an upgrade batch inside a release: 39 of them so far, each waiting for a release
and each putting his plants' details in the public code. Now Claude saves one small file on his computer and the page
"Updates from Claude" shows every change in it (what the page says now, what it would say, and why) to accept or leave.
Nothing is changed until the owner presses the button, and a file is brought in once.

The file is `plant-updates-<date>-<time>.json`, or a `.zip` holding `updates.json` and `photos/<name>` when a new page comes with
pictures:

    {"format": "plant-updates-1", "made": "2026-11-14", "about": "What this file is, in a sentence or two.",
     "changes": [
       {"kind": "set", "code": "P-009", "name": "Peace lily", "field": "health_rating", "from": "Fair", "to": "Good", "why": "..."},
       {"kind": "archive", "code": "P-005", "name": "Sweet potato vine", "why": "..."},
       {"kind": "ask", "code": "P-014", "name": "Aloe vera", "text": "Is it still in the black pot?", "why": "..."},
       {"kind": "photos", "code": "P-094", "name": "Monstera cutting", "photos": [{"file": "jar-1.jpg", "caption": "November 11: in its jar"}], "why": "..."},
       {"kind": "new", "home": "Baraboo, WI", "fields": {"common_name": "Hardy aloe, second pot", "scientific_name": "Aloiampelos striatula", "site": "Outdoors"},
        "photos": [{"file": "aloe-1.jpg", "caption": "By the steps"}], "why": "..."}]}

- A change names its plant by the code it has in this record **and** its name, as a batch entry does: with the code alone, a
  record numbered differently would get the change on the plant next door. With the name alone, the one plant of that name is meant.
- `set` says the value it expects to replace (`from`). If the page says something else by now, it may be a change the owner made:
  it "needs your decision" and stays as it is unless he chooses Claude's.
- `photos` adds pictures to a page that exists (the file is then a .zip). They are added the way Add photos adds them: written
  again, so no location or camera details stay in them. The page's main picture stays as it is; a page with none takes the first.
- A new page is made at the main home unless it names another (`home`: the home's name as Homes and places has it; never a row
  number). A home the record does not have leaves the page out and says so: the first new page that travelled in a batch for a
  second home would have landed in a room of the main one.
- An accepted change goes through apply_changes() and bump(), like an edit: it is in the plant's page history and the Audit log,
  signed "Claude (<file name>)", and Page history can take it back.

Where a file comes from: the folder `plant-updates` beside `data` in the app's folder (docker-compose mounts it read-only at
/plant-updates; PLANTDB_PLANT_UPDATES_DIR names another), where Today can see that one is waiting; or the file chooser on the page,
which keeps its copy in data/plant-updates until the file is brought in or set aside. (PLANTDB_UPDATES is something else: whether the
app asks GitHub for a newer release.) Only the owner sees or uses any of this (OWNER_ONLY_PATHS)."""
import hashlib, zipfile
from flask import send_file
from werkzeug.exceptions import HTTPException
from .core import *   # noqa: F401,F403

UPDATES_SCHEMA = """
CREATE TABLE IF NOT EXISTS update_files(
  id TEXT PRIMARY KEY, name TEXT NOT NULL, made TEXT, about TEXT NOT NULL DEFAULT '', state TEXT NOT NULL,
  at TEXT NOT NULL, by TEXT NOT NULL, result TEXT NOT NULL DEFAULT '[]');
"""
UPD_FOLDER = os.environ.get('PLANTDB_PLANT_UPDATES_DIR') or ('/plant-updates' if os.path.isdir('/plant-updates') else '')   # where Claude saves a file; the app only reads it
UPD_INBOX = os.path.join(DATA_DIR, 'plant-updates')                 # files chosen on the page, until they are brought in or set aside
UPD_MAX = 30 * 1024 * 1024                                    # a file saved to his computer from a chat is under 30 MB
UPD_NAME = re.compile(r'^plant-updates[\w.\-]*\.(json|zip)$', re.I)
UPD_KINDS = ('set', 'archive', 'ask', 'new', 'photos')
UPD_PHOTO = re.compile(r'^[\w][\w.\- ]{0,80}\.(jpe?g|png|webp)$', re.I)
UPD_CACHE = {}                                                # path -> (mtime, size, what upd_read gave), so Today does not open every file each time

def updates_tables(c): c.executescript(UPDATES_SCHEMA)        # init_db() runs this too; here for a database opened by an older mock

def upd_clip(v, n): return str(v if v is not None else '').strip()[:n]

def upd_pics(lst, have, bad):
    """The photos a change names -> [{'file', 'caption'}]. Each must be one of the photos in the file; `bad` is what to say if not."""
    if lst is not None and not isinstance(lst, list): raise ValueError(bad)
    out = []
    for p in (lst or [])[:60]:
        if not isinstance(p, dict) or upd_clip(p.get('file'), 100) not in have: raise ValueError(bad)
        out.append({'file': upd_clip(p.get('file'), 100), 'caption': upd_clip(p.get('caption'), 200)})
    return out

def upd_parse(raw, name):
    """The bytes of an update file -> {'id', 'name', 'made', 'about', 'changes', 'photos': [names in the zip]}. ValueError says, in
    plain words, what is wrong with a file that cannot be used. The id is the file's own fingerprint, so the same file is the
    same update whatever it is called, and a file edited afterwards is another one."""
    if len(raw) > UPD_MAX: raise ValueError('The file is larger than 30 MB.')
    photos = []
    if raw[:2] == b'PK':
        try: z = zipfile.ZipFile(io.BytesIO(raw))
        except zipfile.BadZipFile: raise ValueError('The zip file is damaged.')
        infos = [i for i in z.infolist() if not i.is_dir()]
        if len(infos) > 400 or sum(i.file_size for i in infos) > 200 * 1024 * 1024: raise ValueError('The zip file holds too much to be an update file.')
        names = {i.filename for i in infos}
        if 'updates.json' not in names: raise ValueError('The zip file has no updates.json in it.')
        if any(i.file_size > (4 if i.filename == 'updates.json' else 25) * 1024 * 1024 for i in infos): raise ValueError('The zip file holds a list of changes or a photo that is too large to be part of an update file.')
        for n in names - {'updates.json'}:
            if not (n.startswith('photos/') and UPD_PHOTO.match(n[7:])): raise ValueError(f'The zip file holds something that is not a photo of the update: {n[:60]}')
            photos.append(n[7:])
        text = z.read('updates.json')
    else: text = raw
    if len(text) > 4 * 1024 * 1024: raise ValueError('The list of changes is too long to be an update file.')
    try: d = json.loads(text.decode('utf-8-sig'))
    except (ValueError, UnicodeDecodeError): raise ValueError('The file is not an update file (it is not JSON).')
    if not isinstance(d, dict) or d.get('format') != 'plant-updates-1' or not isinstance(d.get('changes'), list):
        raise ValueError('The file is not an update file for this app (its format is not "plant-updates-1").')
    if len(d['changes']) > 2000: raise ValueError('The file holds more than 2,000 changes.')
    made = upd_clip(d.get('made'), 10)
    changes = []
    for x in d['changes']:
        if not isinstance(x, dict) or x.get('kind') not in UPD_KINDS: raise ValueError('The file holds a change of a kind this version does not know. A newer version of the app may be needed.')
        ch = {'kind': x['kind'], 'why': upd_clip(x.get('why'), 600)}
        if x['kind'] != 'new':
            ch['code'], ch['name'] = upd_clip(x.get('code'), 20), upd_clip(x.get('name'), 200)
            if not ch['name'] or (not ch['code'] and x['kind'] != 'ask'): raise ValueError('A change in the file does not say which plant it is for (its code and its name).')
        if x['kind'] == 'set':
            ch['field'] = upd_clip(x.get('field'), 60)
            if 'to' not in x: raise ValueError('A change in the file does not say what to change the page to.')
            ch['from'], ch['to'] = x.get('from'), x.get('to')
            if any(isinstance(v, (dict, list)) for v in (ch['from'], ch['to'])): raise ValueError('A change in the file gives a list where one value belongs.')
        elif x['kind'] == 'ask':
            ch['text'] = upd_clip(x.get('text'), 1000)
            if not ch['text']: raise ValueError('A question in the file has no words.')
        elif x['kind'] == 'new':
            f = x.get('fields')
            if not isinstance(f, dict) or not upd_clip(f.get('common_name'), 200): raise ValueError('A new page in the file has no common name.')
            if any(isinstance(v, (dict, list)) for v in f.values()): raise ValueError('A new page in the file gives a list where one value belongs.')
            ch['fields'] = {str(k)[:60]: v for k, v in f.items()}
            ch['home'] = upd_clip(x.get('home'), 120)                                # the home it is at, by name; none: the main home
            ch['photos'] = upd_pics(x.get('photos'), photos, 'A new page in the file names a photo that is not in the file.')
        elif x['kind'] == 'photos':
            ch['photos'] = upd_pics(x.get('photos'), photos, 'A change in the file adds a photo that is not in the file.')
            if not ch['photos']: raise ValueError('A change in the file adds photos to a page, and names none.')
        changes.append(ch)
    return {'id': hashlib.sha256(raw).hexdigest()[:16], 'name': os.path.basename(name)[:120], 'made': made if re.match(r'^\d{4}-\d\d-\d\d$', made) else '',
            'about': upd_clip(d.get('about'), 2000), 'changes': changes, 'photos': photos}

def upd_read(path, name=None):
    """A file on disk, read once and remembered until it changes: {'path', ...upd_parse} or {'path', 'name', 'bad': words}."""
    try: st = os.stat(path)
    except OSError: return None
    got = UPD_CACHE.get(path)
    if got and got[0] == st.st_mtime and got[1] == st.st_size: return got[2]
    name = name or os.path.basename(path)
    try:
        if st.st_size > UPD_MAX: raise ValueError('The file is larger than 30 MB.')
        with open(path, 'rb') as f: u = upd_parse(f.read(), name)
    except ValueError as e: u = {'id': '', 'name': name, 'bad': str(e), 'changes': [], 'photos': []}
    except OSError: return None
    u['path'] = path
    UPD_CACHE[path] = (st.st_mtime, st.st_size, u)
    return u

def upd_files():
    """Every update file the app can see: Claude's folder first, then the ones chosen on the page. [{..., 'where': 'folder' | 'page'}]"""
    out = []
    for where, d in (('folder', UPD_FOLDER), ('page', UPD_INBOX)):
        if not d or not os.path.isdir(d): continue
        for fn in sorted(os.listdir(d)):
            shown = fn.split('__', 1)[1] if where == 'page' and '__' in fn else fn       # a file from the page is kept as <id>__<its name>
            if not UPD_NAME.match(shown) and where == 'folder': continue                 # the folder may hold other things (a README)
            u = upd_read(os.path.join(d, fn), shown)
            if u: out.append({**u, 'where': where})
    return out

def upd_done(c):
    updates_tables(c)
    return {r['id']: r for r in c.execute('SELECT * FROM update_files')}

def upd_find(c, fid):
    if not re.match(r'^[0-9a-f]{16}$', fid or ''): abort(404, 'That update file is not here.')
    u = next((u for u in upd_files() if u['id'] == fid), None)
    if not u: abort(404, 'That update file is not here any more. Choose it again, or ask Claude to save it again.')
    return u

def upd_plant(c, code, name):
    """The plant a change is for -> (row or None, a note). The code and the name must agree; the one plant of that name is meant when
    the code is another plant's here (a record numbered differently) or is not given."""
    r = c.execute('SELECT * FROM plants WHERE code=?', (code,)).fetchone() if code else None
    if r and r['common_name'] == name: return r, ''
    rows = c.execute('SELECT * FROM plants WHERE common_name=?', (name,)).fetchall()
    if len(rows) == 1: return rows[0], (f'The file calls it {code}; in your record it is {rows[0]["code"]}.' if code else '')
    if r: return None, f'The file calls {code} "{name}". In your record {code} is "{r["common_name"]}", so this was left out.'
    return None, f'No plant in your record is {code + ", " if code else ""}"{name}", so this was left out.'

def upd_home(c, name):
    """The home a new page is for -> (the home as homes() gives it, or None; a note). No name means the main home. A file names a
    home by its name, as it names a plant by its code and name: a row number means another home in another record."""
    hs = homes(c)
    if not name: return next((h for h in hs if h['is_home']), None), ''
    m = [h for h in hs if str(h['name']).strip().casefold() == name.strip().casefold()]
    if len(m) == 1: return m[0], ''
    return None, f'The file puts this page at "{name}". Your record has {"more than one home" if m else "no home"} of that name, so this was left out.'

def upd_value(field, v):
    """A value as the record would hold it -> (value, '') or (None, why it cannot be used)."""
    try: return norm(field, v), ''
    except HTTPException as e: return None, str(e.description)

def upd_same(a, b): return str(a if a is not None else '').strip() == str(b if b is not None else '').strip()

def upd_photos_ok(u, names):
    """Can every photo of a new page be opened as a picture? (Looked at when the file is shown, so a broken one is said then and not at the last step.)"""
    try:
        with zipfile.ZipFile(u['path']) as z:
            for n in names: Image.open(io.BytesIO(z.read('photos/' + n))).verify()
        return True
    except Exception: return False

def upd_photo_of(c, pid):
    r = c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC, id LIMIT 1', (pid,)).fetchone()
    return r[0] if r else ''

def upd_review(c, u):
    """Each change of a file against the record as it is now. state: 'ready' (can be made), 'conflict' (the page no longer says what
    the file expected: the owner decides), 'same' (nothing to do: the page already says it), 'out' (cannot be made; `note` says why)."""
    out = []
    for i, x in enumerate(u['changes']):
        k = x['kind']; d = {'i': i, 'kind': k, 'why': x['why'], 'state': 'ready', 'note': ''}
        if k == 'new':
            f = x['fields']; bad = [n for n in f if n not in FIELD_KIND or n in BATCH_ROW_IDS]
            hm, hnote = upd_home(c, x.get('home') or '')
            d.update(name=upd_clip(f.get('common_name'), 200), sci=upd_clip(f.get('scientific_name'), 200), site=upd_clip(f.get('site'), 40) or 'Outdoors',
                     home=hm['name'] if hm and (x.get('home') or len(homes(c)) > 1) else '',      # said where there is more than one home, or the file names one
                     photos=[p['file'] for p in x['photos']], captions=[p['caption'] for p in x['photos']],
                     fields=[[FIELD_LABEL[n], str(v)] for n, v in f.items() if n in FIELD_LABEL and n not in ('common_name', 'scientific_name', 'site') and v not in (None, '')][:12])
            for n, v in f.items():
                if n in bad: continue
                _, why = upd_value(n, v)
                if why: d.update(state='out', note=why); break
            if bad: d.update(state='out', note='The file sets something a new page cannot be given: ' + ', '.join(bad[:4]) + '.')
            elif d['state'] == 'ready' and hnote: d.update(state='out', note=hnote)
            elif d['state'] == 'ready' and d['photos'] and not upd_photos_ok(u, d['photos']): d.update(state='out', note='A photo that comes with this page cannot be read.')
            elif d['state'] == 'ready':
                twin = c.execute("SELECT code FROM plants WHERE common_name=? AND status='active' LIMIT 1", (d['name'],)).fetchone()
                if twin: d.update(state='conflict', note=f'A plant with this name is already in your record ({twin[0]}).')
            out.append(d); continue
        r, note = upd_plant(c, x['code'], x['name'])
        d.update(code=r['code'] if r else x['code'], name=r['common_name'] if r else x['name'], photo=upd_photo_of(c, r['id']) if r else '', note=note)
        if k == 'set': d.update(field=x['field'], label=FIELD_LABEL.get(x['field'], x['field']), now=None, to=x['to']); d['from'] = x['from']
        if k == 'ask': d['text'] = x['text']
        if k == 'photos': d.update(photos=[p['file'] for p in x['photos']], captions=[p['caption'] for p in x['photos']])
        if not r: d['state'] = 'out'
        elif k == 'set':
            f = x['field']; d['now'] = r[f] if f in FIELD_KIND else None
            if f not in FIELD_KIND or f in BATCH_ROW_IDS or FIELD_KIND[f] in ('area', 'spot', 'pot', 'tray'):
                d.update(state='out', note='This is not something an update file can change.')
            else:
                to, why = upd_value(f, x['to']); old, _ = upd_value(f, x['from'])
                if why: d.update(state='out', note=why)
                elif f == 'common_name' and not upd_clip(to, 200): d.update(state='out', note='A plant must keep a common name.')
                elif upd_same(r[f], to): d.update(state='same', note='The page already says this.')
                elif not upd_same(r[f], old): d['state'] = 'conflict'
                d['to'] = to if not why else x['to']
        elif k == 'archive':
            if r['status'] == 'archived': d.update(state='same', note='It is in the archive already.')
        elif k == 'ask':
            if c.execute('SELECT 1 FROM requests WHERE plant_code=? AND text=? AND done=0', (r['code'], x['text'])).fetchone(): d.update(state='same', note='This question is already on its page.')
        elif k == 'photos':
            if not upd_photos_ok(u, d['photos']): d.update(state='out', note='A photo that comes with this cannot be read.')
        out.append(d)
    return out

def upd_summary(u, where=None):
    plants = {x.get('code') or x.get('name') or ('new%d' % i) for i, x in enumerate(u['changes'])}
    return {'id': u['id'], 'name': u['name'], 'made': u.get('made', ''), 'about': u.get('about', ''), 'changes': len(u['changes']), 'plants': len(plants),
            'bad': u.get('bad', ''), 'where': where or u.get('where', '')}

def upd_before(r):
    try: res = json.loads(r['result'] or '[]')
    except ValueError: res = []
    return {'id': r['id'], 'name': r['name'], 'made': r['made'] or '', 'about': r['about'], 'state': r['state'], 'at': r['at'], 'by': r['by'],
            'made_n': sum(1 for x in res if x.get('did') == 'made'), 'left_n': sum(1 for x in res if x.get('did') != 'made'), 'result': res}

@app.route('/api/updates')
def updates_list():
    """{folder: is Claude's folder there, waiting: [files not brought in yet], before: [what was brought in or set aside, newest first]}"""
    c = db(); done = upd_done(c); seen = set(); waiting = []
    for u in upd_files():
        if u.get('bad'): waiting.append(upd_summary(u)); continue
        if u['id'] in done or u['id'] in seen: continue
        seen.add(u['id']); waiting.append(upd_summary(u))
    here = {u['id'] for u in upd_files() if u.get('id')}
    return jsonify(folder=bool(UPD_FOLDER and os.path.isdir(UPD_FOLDER)), folder_path=UPD_FOLDER, waiting=waiting,
                   before=[upd_before(r) | {'here': r['id'] in here} for r in sorted(done.values(), key=lambda r: r['at'], reverse=True)][:50])

@app.route('/api/updates/upload', methods=['POST'])
def updates_upload():
    """A file chosen on the page: checked, then kept in data/plant-updates until it is brought in or set aside."""
    f = request.files.get('file')
    if not f or not f.filename: abort(400, 'Choose the update file first.')
    raw = f.stream.read(UPD_MAX + 1)
    name = re.sub(r'[^\w.\- ]', '', os.path.basename(f.filename.replace('\\', '/'))).lstrip('. ')[:100] or 'plant-updates.json'      # its own name, with nothing of a path left in it
    try: u = upd_parse(raw, name)
    except ValueError as e: abort(400, str(e))
    c = db(); was = upd_done(c).get(u['id'])
    if was and was['state'] == 'done': return jsonify(error=f'This file was brought in already, on {was["at"][:10]}.', before=upd_before(was)), 409
    if was: c.execute('DELETE FROM update_files WHERE id=?', (u['id'],)); c.commit()           # set aside before: chosen again, it is looked at again
    if not any(x['id'] == u['id'] for x in upd_files()):
        os.makedirs(UPD_INBOX, exist_ok=True)
        with open(os.path.join(UPD_INBOX, f'{u["id"]}__{name}'), 'wb') as out: out.write(raw)
    return jsonify(upd_summary(u, 'page')), 201

@app.route('/api/updates/<fid>')
def updates_one(fid):
    """A file's changes against the record as it is now, or what it did if it was brought in before."""
    c = db(); was = upd_done(c).get(fid)
    if was and was['state'] == 'done': return jsonify(before=upd_before(was))
    u = upd_find(c, fid)
    if u.get('bad'): abort(400, u['bad'])
    return jsonify(upd_summary(u) | {'items': upd_review(c, u), 'aside': bool(was)})

@app.route('/api/updates/<fid>/photo/<name>')
def updates_photo(fid, name):
    """A photo that comes with a new page, to look at before the page is made (made smaller; the file itself is not served)."""
    u = upd_find(db(), fid)
    if name not in u.get('photos', []): abort(404)
    try:
        with zipfile.ZipFile(u['path']) as z: im = ImageOps.exif_transpose(Image.open(io.BytesIO(z.read('photos/' + name)))).convert('RGB')
    except Exception: abort(400, 'That photo cannot be read.')
    im.thumbnail((640, 640)); b = io.BytesIO(); im.save(b, 'JPEG', quality=80); b.seek(0)
    return send_file(b, mimetype='image/jpeg', max_age=600)

def upd_forget(u):
    """A file chosen on the page has done its work: its copy in data/plant-updates goes. Claude's folder is read-only and is left alone."""
    if u.get('path', '').startswith(UPD_INBOX + os.sep):
        try: os.remove(u['path'])
        except OSError: pass
        UPD_CACHE.pop(u['path'], None)

@app.route('/api/updates/<fid>/aside', methods=['POST'])
def updates_aside(fid):
    """{on: true} sets a file aside (nothing changed; Today stops naming it); {on: false} brings it back to be looked at."""
    c = db(); on = (request.get_json(silent=True) or {}).get('on', True); was = upd_done(c).get(fid)
    if was and was['state'] == 'done': abort(409, 'This file was brought in already.')
    if not on:
        c.execute("DELETE FROM update_files WHERE id=? AND state='aside'", (fid,)); c.commit()
        return jsonify(ok=True)
    u = upd_find(c, fid)
    c.execute('INSERT OR REPLACE INTO update_files(id,name,made,about,state,at,by,result) VALUES(?,?,?,?,?,?,?,?)', (fid, u['name'], u.get('made') or None, u.get('about', ''), 'aside', now(), editor(), '[]'))
    audit_only(c, 'setting', 'update_file', None, u['name'], editor(), f'Update file set aside, nothing changed: {u["name"]}')
    c.commit(); upd_forget(u)
    return jsonify(ok=True)

def upd_save_photos(c, u, pics, pid, who, ts, written):
    """The photos of a change, added to a plant's page the way Add photos adds them -> their new names. Each is written again, so no
    location or camera details stay in it, and is added to `written` as it is saved, so that the caller can take them away again if
    the changes are not kept. The page's main picture stays; a page with none takes the first."""
    names = []
    if not pics: return names
    has = c.execute('SELECT 1 FROM photos WHERE plant_id=? AND is_primary=1', (pid,)).fetchone()
    with zipfile.ZipFile(u['path']) as z:
        for p in pics:
            try: im = ImageOps.exif_transpose(Image.open(io.BytesIO(z.read('photos/' + p['file'])))).convert('RGB')
            except Exception: abort(400, f'The photo {p["file"]} in the file cannot be read, so nothing was changed.')
            im.thumbnail((1600, 1600)); name = f'up_{uuid.uuid4().hex[:16]}.jpg'
            im.save(os.path.join(PHOTO_DIR, name), 'JPEG', quality=84, optimize=True); written.append(name)
            c.execute('INSERT INTO photos(plant_id,file,caption,kind,is_primary,source_name,added_by,added_at) VALUES(?,?,?,?,?,?,?,?)',
                      (pid, name, p['caption'] or p['file'][:80], 'plant', 0 if (has or names) else 1, p['file'], who, ts))
            names.append(name)
    return names

def upd_new_plant(c, u, x, who, ts, note, written):
    """A new page from an update file, made the way Add plants makes one, at the home the file names (the main home if it names
    none), with the photos that came in the file -> its code."""
    f = dict(x['fields'])
    hm, _ = upd_home(c, x.get('home') or '')
    if hm and not hm['is_home']: f['home_id'] = hm['id']                    # the main home is "no home given", as on every other page
    f['winter_plan'] = f.get('winter_plan') or 'Move indoors'; f['health_rating'] = f.get('health_rating') or 'Fair'; f['site'] = f.get('site') or 'Outdoors'
    f = place_sync(c, None, f)
    vals = {k: norm(k, f.get(k)) for k in FIELD_NAMES}
    n = c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(code,3) AS INTEGER)),0)+1 FROM plants").fetchone()[0]
    code = f'P-{n:03d}'
    cols = ['code'] + FIELD_NAMES + ['version', 'status', 'created_at', 'created_by', 'updated_at', 'updated_by']
    pid = c.execute(f"INSERT INTO plants({','.join(cols)}) VALUES({','.join('?' * len(cols))})", [code] + [vals[k] for k in FIELD_NAMES] + [1, 'active', ts, who, ts, who]).lastrowid
    upd_save_photos(c, u, x['photos'], pid, who, ts, written)
    c.execute('INSERT INTO plant_versions(plant_id,version,snapshot,changed_by,changed_at,summary) VALUES(?,?,?,?,?,?)', (pid, 1, json.dumps(snapshot(c, pid)), who, ts, note))
    c.execute('INSERT INTO audit_log(plant_id,plant_code,version,action,field,old_value,new_value,changed_by,changed_at,note) VALUES(?,?,?,?,?,?,?,?,?,?)', (pid, code, 1, 'create', None, None, None, who, ts, note))
    return code

@app.route('/api/updates/<fid>/apply', methods=['POST'])
def updates_apply(fid):
    """{accept: [the numbers of the changes to make], take: [the numbers of the ones that need a decision where Claude's is chosen]}.
    Every change is checked again against the record as it is at this moment, all of them are made together or none is, and the
    file is then marked as brought in. -> what was done with each change."""
    c = db()
    if upd_done(c).get(fid, {'state': ''})['state'] == 'done': abort(409, 'This file was brought in already.')
    u = upd_find(c, fid)
    if u.get('bad'): abort(400, u['bad'])
    b = request.get_json(silent=True) or {}
    accept = {int(i) for i in b.get('accept') or [] if str(i).lstrip('-').isdigit()}; take = {int(i) for i in b.get('take') or [] if str(i).lstrip('-').isdigit()}
    who, by, ts = f'Claude ({u["name"]})'[:80], editor(), now()
    result, made_files = [], []
    try:
        for d in upd_review(c, u):
            x = u['changes'][d['i']]; i = d['i']
            res = {'i': i, 'kind': d['kind'], 'code': d.get('code') or '', 'name': d.get('name') or '', 'label': d.get('label') or '', 'did': 'left', 'note': d['note']}
            if d['kind'] in ('photos', 'new'): res['n'] = len(x['photos'])       # how many photos came with it, for the page that says what was done
            go = (d['state'] == 'ready' and i in accept) or (d['state'] == 'conflict' and i in take)
            if d['state'] == 'same': res['did'] = 'same'
            elif d['state'] == 'out': res['did'] = 'out'
            elif go:
                note = ((x['why'] + ' ') if x['why'] else '') + f'(Update from Claude, {u["name"]}; accepted by {by})'
                if d['kind'] == 'set':
                    r = c.execute('SELECT * FROM plants WHERE code=?', (d['code'],)).fetchone()
                    apply_changes(c, r, {d['field']: d['to']}, who, 'edit', note[:600])
                    res.update(old='' if d['now'] is None else str(d['now'])[:200], new='' if d['to'] is None else str(d['to'])[:200])
                elif d['kind'] == 'archive':
                    r = c.execute('SELECT * FROM plants WHERE code=?', (d['code'],)).fetchone()
                    c.execute("UPDATE plants SET status='archived' WHERE id=?", (r['id'],))
                    bump(c, r['id'], r['code'], who, 'archive', note[:600], [('status', r['status'], 'archived')])
                elif d['kind'] == 'ask':
                    c.execute('INSERT OR IGNORE INTO requests(rkey,plant_code,kind,text,created_by,created_at) VALUES(?,?,?,?,?,?)', (f'upd:{fid}:{i}', d['code'], 'question', x['text'], who, ts))
                    audit_only(c, 'request', 'request', None, x['text'], who, f'Request added (update from Claude, {u["name"]}; accepted by {by})', None, d['code'])
                elif d['kind'] == 'photos':
                    r = c.execute('SELECT * FROM plants WHERE code=?', (d['code'],)).fetchone()
                    names = upd_save_photos(c, u, x['photos'], r['id'], who, ts, made_files)
                    bump(c, r['id'], r['code'], who, 'photo_add', (f'Added {len(names)} photo(s). ' + note)[:600], [('photo', None, nm) for nm in names])
                elif d['kind'] == 'new':
                    res['code'] = upd_new_plant(c, u, x, who, ts, f'Record created from an update file ({u["name"]}; accepted by {by})', made_files)
                res['did'] = 'made'
            result.append(res)
        c.execute('INSERT OR REPLACE INTO update_files(id,name,made,about,state,at,by,result) VALUES(?,?,?,?,?,?,?,?)', (fid, u['name'], u.get('made') or None, u.get('about', ''), 'done', ts, by, json.dumps(result)))
        n = sum(1 for x in result if x['did'] == 'made')
        audit_only(c, 'setting', 'update_file', None, u['name'], by, f'Update file brought in: {u["name"]}. {n} of its {len(result)} changes made.')
        c.commit()
    except Exception:
        c.rollback()
        for f in made_files:                                     # photos already written for a page that was not made after all
            try: os.remove(os.path.join(PHOTO_DIR, f))
            except OSError: pass
        raise
    upd_forget(u)
    return jsonify(before=upd_before(c.execute('SELECT * FROM update_files WHERE id=?', (fid,)).fetchone()))
