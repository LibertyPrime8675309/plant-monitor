"""Plant Database - small Flask + SQLite app.

Everything lives in DATA_DIR (default /data): plants.db, photos/, cache/.
Edits are versioned: every save bumps the plant's page version, writes a full snapshot
to plant_versions and one row per changed field to audit_log (what / before / after / who / when).
"""
import csv, hmac, io, json, math, os, re, secrets, shutil, sqlite3, threading, time, urllib.error, urllib.parse, urllib.request, uuid
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

from flask import Flask, Response, abort, g, jsonify, request, send_from_directory
from PIL import Image, ImageOps
import segno

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('DATA_DIR', '/data')
DB_PATH = os.path.join(DATA_DIR, 'plants.db')
PHOTO_DIR = os.path.join(DATA_DIR, 'photos')
TRASH_DIR = os.path.join(DATA_DIR, 'photos_deleted')
THUMB_DIR = os.path.join(DATA_DIR, 'cache', 'thumbs')
SEED_DIR = os.path.join(APP_DIR, 'seed')
PASSWORD = os.environ.get('PLANTDB_PASSWORD', '')
# Backups go to /backups when that folder is mounted (docker-compose maps ./backups there), otherwise data/backups.
BACKUP_DIR = os.environ.get('PLANTDB_BACKUP_DIR') or ('/backups' if os.path.isdir('/backups') else os.path.join(DATA_DIR, 'backups'))

for d in (DATA_DIR, PHOTO_DIR, TRASH_DIR, THUMB_DIR, BACKUP_DIR):
    os.makedirs(d, exist_ok=True)

app = Flask(__name__, static_folder=os.path.join(APP_DIR, 'static'), static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 60 * 1024 * 1024

WINTER_PLANS = ['Move indoors', 'Protect outside', 'Hardy outside', 'Seasonal die-back', 'Annual']
HEALTH = ['Good', 'Fair', 'Poor', 'Critical']
# where the plant is now (added in 1.7.0); plants at an "inside" place are left off the outdoor winter lists and frost warnings
SITES = ['Outdoors', 'Covered porch', 'Indoors', 'Garage or shed']
INSIDE_SITES = ['Indoors', 'Garage or shed']

# (name, kind, label)
FIELDS = [
    ('common_name', 'text', 'Common name'), ('scientific_name', 'text', 'Scientific name'),
    ('aliases', 'text', 'Other names / cultivar'), ('plant_type', 'text', 'Plant type'),
    ('location', 'text', 'Spot (where exactly)'), ('container', 'text', 'Container'),
    ('id_confidence', 'int', 'ID confidence (%)'), ('id_basis', 'long', 'Why Claude thinks so'),
    ('id_alternatives', 'list', 'Other possibilities'), ('id_improve', 'list', 'What would raise confidence'),
    ('temp_ideal_low', 'int', 'Ideal temp low (F)'), ('temp_ideal_high', 'int', 'Ideal temp high (F)'),
    ('temp_damage_below', 'int', 'Damage below (F)'), ('temp_lethal_below', 'int', 'Lethal below (F)'),
    ('temp_notes', 'long', 'Temperature notes'),
    ('humidity_low', 'int', 'Ideal humidity low (%)'), ('humidity_high', 'int', 'Ideal humidity high (%)'),
    ('humidity_notes', 'long', 'Humidity notes'),
    ('light_summary', 'text', 'Light'), ('light_hours', 'text', 'Hours of light'), ('light_notes', 'long', 'Light notes'),
    ('winter_plan', 'enum', 'Winter plan'), ('winter_summary', 'long', 'Winter summary'),
    ('winter_triggers', 'long', 'When to act'), ('winter_steps', 'list', 'Winter steps'),
    ('indoor_setup', 'list', 'Indoor / comfort setup'),
    ('health_rating', 'enum', 'Health rating'), ('health_summary', 'long', 'Health summary'),
    ('health_observations', 'list', 'What was observed'), ('health_steps', 'list', 'Steps to improve'),
    ('notes', 'long', 'Notes'),
    # ---- added in 1.2.0: finer environment values for sensors, soil, nutrients and pests
    ('temp_damage_above', 'int', 'Heat damage above (F)'),
    ('vpd_low', 'num', 'Ideal VPD low (kPa)'), ('vpd_high', 'num', 'Ideal VPD high (kPa)'),
    ('par_low', 'int', 'Light low (PAR, umol/m2/s)'), ('par_high', 'int', 'Light high (PAR, umol/m2/s)'),
    ('dli_low', 'num', 'Daily light low (DLI, mol/m2/day)'), ('dli_high', 'num', 'Daily light high (DLI, mol/m2/day)'),
    ('water_notes', 'long', 'Watering'), ('soil_medium', 'long', 'Soil / potting mix'),
    ('soil_ph_low', 'num', 'Soil pH low'), ('soil_ph_high', 'num', 'Soil pH high'),
    ('soil_moisture_low', 'int', 'Soil moisture low (%)'), ('soil_moisture_high', 'int', 'Soil moisture high (%)'),
    ('soil_temp_low', 'int', 'Root-zone temp low (F)'), ('soil_temp_high', 'int', 'Root-zone temp high (F)'),
    ('fertilizer', 'text', 'Fertilizer'), ('nutrients', 'long', 'Nutrients and feeding'),
    ('fert_from_month', 'int', 'Feed from month (1-12)'), ('fert_to_month', 'int', 'Feed through month (1-12)'),
    ('fert_every_days', 'int', 'Feed every (days)'),
    ('pests_watch', 'list', 'Pests and diseases to watch for'), ('pest_steps', 'list', 'Pest prevention and treatment'),
    ('pests_current', 'long', 'Pests seen now'),
    # ---- added in 1.7.0
    ('site', 'enum', 'Location'),
    # ---- added in 1.8.0
    ('water_every_days', 'int', 'Check for water every (days)'),
]
FIELD_NAMES = [f[0] for f in FIELDS]
FIELD_KIND = {f[0]: f[1] for f in FIELDS}
FIELD_LABEL = {f[0]: f[2] for f in FIELDS}
FIELD_LABEL['fertilizer_log'] = 'Fertilizer entry'
INT_RANGES = {'id_confidence': (0, 100), 'temp_ideal_low': (-60, 150), 'temp_ideal_high': (-60, 150),
              'temp_damage_below': (-60, 150), 'temp_lethal_below': (-60, 150),
              'humidity_low': (0, 100), 'humidity_high': (0, 100),
              'temp_damage_above': (0, 200), 'par_low': (0, 4000), 'par_high': (0, 4000),
              'soil_moisture_low': (0, 100), 'soil_moisture_high': (0, 100), 'soil_temp_low': (-40, 150), 'soil_temp_high': (-40, 150),
              'fert_from_month': (1, 12), 'fert_to_month': (1, 12), 'fert_every_days': (1, 365),
              'water_every_days': (1, 60)}
NUM_RANGES = {'vpd_low': (0, 6), 'vpd_high': (0, 6), 'dli_low': (0, 80), 'dli_high': (0, 80), 'soil_ph_low': (0, 14), 'soil_ph_high': (0, 14)}

def now():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

# ---------------------------------------------------------------- database
def db():
    if 'db' not in g:
        c = sqlite3.connect(DB_PATH, timeout=30)
        c.row_factory = sqlite3.Row
        c.execute('PRAGMA foreign_keys=ON')
        c.execute('PRAGMA cache_size=-32768')        # 32 MB of page cache: the weather history is large
        g.db = c
    return g.db

@app.teardown_appcontext
def close_db(_):
    c = g.pop('db', None)
    if c: c.close()

SQLTYPE = {'int': 'INTEGER', 'num': 'REAL'}
SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS plants(
  id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL,
  %s,
  version INTEGER NOT NULL DEFAULT 1, status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT NOT NULL, created_by TEXT NOT NULL, updated_at TEXT NOT NULL, updated_by TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS plant_versions(
  id INTEGER PRIMARY KEY AUTOINCREMENT, plant_id INTEGER NOT NULL REFERENCES plants(id) ON DELETE CASCADE,
  version INTEGER NOT NULL, snapshot TEXT NOT NULL, changed_by TEXT NOT NULL, changed_at TEXT NOT NULL, summary TEXT,
  UNIQUE(plant_id, version));
CREATE TABLE IF NOT EXISTS audit_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, plant_id INTEGER, plant_code TEXT, version INTEGER,
  action TEXT NOT NULL, field TEXT, old_value TEXT, new_value TEXT, changed_by TEXT NOT NULL, changed_at TEXT NOT NULL, note TEXT);
CREATE INDEX IF NOT EXISTS audit_plant ON audit_log(plant_id, id);
CREATE TABLE IF NOT EXISTS photos(
  id INTEGER PRIMARY KEY AUTOINCREMENT, plant_id INTEGER REFERENCES plants(id) ON DELETE SET NULL,
  file TEXT NOT NULL, caption TEXT NOT NULL DEFAULT '', kind TEXT NOT NULL DEFAULT 'plant',
  is_primary INTEGER NOT NULL DEFAULT 0, source_name TEXT, added_by TEXT NOT NULL, added_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS readings(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, source TEXT NOT NULL, device TEXT NOT NULL DEFAULT '',
  temp_f REAL, humidity REAL, par REAL, lux REAL, soil_moisture REAL, soil_temp_f REAL, soil_ph REAL, note TEXT, extra TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS readings_uq ON readings(source, device, ts);
CREATE INDEX IF NOT EXISTS readings_ts ON readings(ts);
CREATE INDEX IF NOT EXISTS readings_src_ts ON readings(source, ts);
CREATE TABLE IF NOT EXISTS locations(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, lat REAL NOT NULL, lon REAL NOT NULL, tz TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1, is_home INTEGER NOT NULL DEFAULT 0, device TEXT UNIQUE, forecast TEXT, status TEXT,
  detail_since TEXT, note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS weather_daily(
  loc_id INTEGER NOT NULL DEFAULT 1, date TEXT NOT NULL, data TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'observed', updated_at TEXT NOT NULL,
  PRIMARY KEY(loc_id, date));
CREATE TABLE IF NOT EXISTS weather_runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ran_at TEXT NOT NULL, trigger TEXT NOT NULL, kind TEXT NOT NULL, api TEXT,
  range_start TEXT, range_end TEXT, hourly_rows INTEGER NOT NULL DEFAULT 0, hourly_new INTEGER NOT NULL DEFAULT 0,
  daily_days INTEGER NOT NULL DEFAULT 0, daily_new INTEGER NOT NULL DEFAULT 0, vars_ok INTEGER NOT NULL DEFAULT 0,
  vars_missing TEXT, ok INTEGER NOT NULL DEFAULT 1, error TEXT, seconds REAL, note TEXT, loc_id INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS fertilizer_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, plant_code TEXT NOT NULL, applied_on TEXT NOT NULL, product TEXT NOT NULL,
  form TEXT NOT NULL DEFAULT 'liquid', n REAL, p REAL, k REAL, amount REAL, amount_unit TEXT, water_amount REAL, water_unit TEXT,
  method TEXT NOT NULL DEFAULT 'water in', ppm_n REAL, ppm_p2o5 REAL, ppm_k2o REAL, n_grams REAL, note TEXT NOT NULL DEFAULT '',
  batch_id TEXT, created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT);
CREATE INDEX IF NOT EXISTS fert_plant ON fertilizer_log(plant_code, applied_on);
CREATE INDEX IF NOT EXISTS fert_day ON fertilizer_log(applied_on);
CREATE TABLE IF NOT EXISTS care_log(
  id INTEGER PRIMARY KEY AUTOINCREMENT, plant_code TEXT NOT NULL, kind TEXT NOT NULL, done_on TEXT NOT NULL, note TEXT NOT NULL DEFAULT '',
  created_by TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS care_plant ON care_log(plant_code, kind, done_on);
CREATE TABLE IF NOT EXISTS requests(
  id INTEGER PRIMARY KEY AUTOINCREMENT, rkey TEXT UNIQUE, plant_code TEXT, kind TEXT NOT NULL DEFAULT 'question', text TEXT NOT NULL,
  created_by TEXT NOT NULL, created_at TEXT NOT NULL, done INTEGER NOT NULL DEFAULT 0, answer TEXT, done_by TEXT, done_at TEXT);
CREATE INDEX IF NOT EXISTS requests_plant ON requests(plant_code, done);
CREATE TABLE IF NOT EXISTS to_photograph(
  id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', done INTEGER NOT NULL DEFAULT 0);
""" % ',\n  '.join(f"{n} {SQLTYPE.get(k, 'TEXT')}" for n, k, _ in FIELDS)

def init_db():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    # WAL can misbehave on Windows bind mounts; the default rollback journal is safe everywhere for a single-process home app.
    c.execute('PRAGMA journal_mode=' + os.environ.get('PLANTDB_JOURNAL', 'DELETE'))
    c.executescript(SCHEMA)
    have = {r[1] for r in c.execute('PRAGMA table_info(plants)')}
    for n, k, _ in FIELDS:                      # upgrade an older database: add any column this version needs
        if n not in have: c.execute(f"ALTER TABLE plants ADD COLUMN {n} {SQLTYPE.get(k, 'TEXT')}")
    if 'extra' not in {r[1] for r in c.execute('PRAGMA table_info(readings)')}: c.execute('ALTER TABLE readings ADD COLUMN extra TEXT')
    migrate_places(c)
    if not c.execute('SELECT 1 FROM weather_runs LIMIT 1').fetchone():       # readings gathered before runs were logged (version 1.2)
        w = c.execute("SELECT MIN(ts),MAX(ts),COUNT(*) FROM readings WHERE source='weather'").fetchone()
        if w[2]:
            try: at = json.loads((c.execute("SELECT value FROM settings WHERE key='weather_status'").fetchone() or ['{}'])[0]).get('at')
            except ValueError: at = None
            c.execute("INSERT INTO weather_runs(ran_at,trigger,kind,api,range_start,range_end,hourly_rows,hourly_new,vars_ok,vars_missing,ok,note) VALUES(?,?,?,?,?,?,?,?,?,?,1,?)",
                      (at or w[1], 'earlier', 'earlier', 'mixed', w[0][:10], w[1][:10], w[2], w[2], 3, '[]',
                       'Collected before runs were logged (versions up to 1.2). Only temperature, humidity and sunlight were kept; press Load history to fill in the rest.'))
    if not c.execute("SELECT 1 FROM settings WHERE key='ingest_token'").fetchone():
        c.execute("INSERT INTO settings(key,value) VALUES('ingest_token',?)", (secrets.token_urlsafe(18),))
    c.commit()
    seeded = c.execute("SELECT value FROM settings WHERE key='seeded'").fetchone()
    seed_file = os.path.join(SEED_DIR, 'seed.json')
    if not seeded and os.path.exists(seed_file):
        seed = json.load(open(seed_file, encoding='utf-8'))
        ts, who = '2026-10-19T22:30:00Z', seed.get('author', 'Claude (initial analysis from photos)')
        for p in seed['plants']:
            cols = ['code'] + FIELD_NAMES + ['version', 'status', 'created_at', 'created_by', 'updated_at', 'updated_by']
            vals = [p['code']] + [p.get(n) for n in FIELD_NAMES] + [1, 'active', ts, who, ts, who]
            cur = c.execute(f"INSERT INTO plants({','.join(cols)}) VALUES({','.join('?' * len(cols))})", vals)
            pid = cur.lastrowid
            for ph in p['photos']:
                copy_seed_photo(ph['file'])
                c.execute("INSERT INTO photos(plant_id,file,caption,kind,is_primary,source_name,added_by,added_at) VALUES(?,?,?,?,?,?,?,?)",
                          (pid, ph['file'], ph['caption'], 'plant', 1 if ph['primary'] else 0, ph.get('source'), who, ts))
            snap = snapshot(c, pid)
            c.execute("INSERT INTO plant_versions(plant_id,version,snapshot,changed_by,changed_at,summary) VALUES(?,?,?,?,?,?)",
                      (pid, 1, json.dumps(snap), who, ts, 'Initial record from photo analysis'))
            c.execute("INSERT INTO audit_log(plant_id,plant_code,version,action,field,old_value,new_value,changed_by,changed_at,note) VALUES(?,?,?,?,?,?,?,?,?,?)",
                      (pid, p['code'], 1, 'create', None, None, None, who, ts, 'Initial record created from photos taken Oct 19, 2026'))
        for u in seed.get('unassigned_photos', []):
            copy_seed_photo(u['file'])
            c.execute("INSERT INTO photos(plant_id,file,caption,kind,is_primary,source_name,added_by,added_at) VALUES(NULL,?,?,?,0,?,?,?)",
                      (u['file'], u['caption'], u['kind'], u.get('source'), who, ts))
            c.execute("INSERT INTO audit_log(plant_id,plant_code,version,action,field,old_value,new_value,changed_by,changed_at,note) VALUES(NULL,NULL,NULL,'photo_add','photo',NULL,?,?,?,?)",
                      (u['file'], who, ts, 'Unassigned photo imported: ' + u['caption']))
        for t in seed.get('to_photograph', []):
            c.execute("INSERT INTO to_photograph(label,note) VALUES(?,?)", (t['label'], t['note']))
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('reference',?)", (json.dumps(seed.get('reference', {})),))
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('seeded',?)", (ts,))
        c.commit()
    c.execute("UPDATE plants SET site='Outdoors' WHERE site IS NULL OR site=''")   # before the batches too, so a batch can expect 'Outdoors'
    c.commit()
    apply_batches(c)
    c.execute("UPDATE plants SET site='Outdoors' WHERE site IS NULL OR site=''")   # 1.7.0: every existing plant starts out as Outdoors
    c.commit()
    repair_seed_photos(c)
    c.close()

def find_plant(c, u):
    """Find the plant an update is meant for. Photos are the most stable clue (codes shift if you added plants yourself);
    otherwise the code must also still carry the expected name."""
    files = u.get('photos') or []
    if files:
        ids = None
        for f in files:
            got = {x[0] for x in c.execute('SELECT plant_id FROM photos WHERE file=? AND plant_id IS NOT NULL', (f,))}
            ids = got if ids is None else ids & got
        if ids and len(ids) == 1:
            return c.execute('SELECT * FROM plants WHERE id=?', (ids.pop(),)).fetchone()
        if not u.get('name'): return None
    r = c.execute('SELECT * FROM plants WHERE code=?', (u['code'],)).fetchone() if u.get('code') else None
    if r and (not u.get('name') or r['common_name'] == u['name']): return r
    return None

def apply_batches(c):
    """Apply seed/batches/*.json once each, so an existing database can receive new plants after an upgrade.
    Safe to run on every start: a batch is recorded in settings as batch_applied:<id> and never repeats.
    User edits are never overwritten: a field update only applies if the field still holds the value the batch expects."""
    bdir = os.path.join(SEED_DIR, 'batches')
    if not os.path.isdir(bdir): return
    for fn in sorted(os.listdir(bdir)):
        if not fn.endswith('.json'): continue
        b = json.load(open(os.path.join(bdir, fn), encoding='utf-8'))
        key = 'batch_applied:' + b['id']
        if c.execute('SELECT 1 FROM settings WHERE key=?', (key,)).fetchone(): continue
        who, ts = b.get('author', 'Claude (batch)'), now()
        label = b['id']
        try:
            c.execute('BEGIN')
            for p in b.get('plants', []):
                n = c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(code,3) AS INTEGER)),0)+1 FROM plants").fetchone()[0]
                code = f'P-{n:03d}'
                cols = ['code'] + FIELD_NAMES + ['version', 'status', 'created_at', 'created_by', 'updated_at', 'updated_by']
                p = {**p, 'site': p.get('site') or 'Outdoors'}          # so later batches in the same start-up can expect it
                vals = [code] + [p.get(k) for k in FIELD_NAMES] + [1, 'active', ts, who, ts, who]
                pid = c.execute(f"INSERT INTO plants({','.join(cols)}) VALUES({','.join('?' * len(cols))})", vals).lastrowid
                for ph in p.get('photos', []):
                    copy_seed_photo(ph['file'])
                    c.execute("INSERT INTO photos(plant_id,file,caption,kind,is_primary,source_name,added_by,added_at) VALUES(?,?,?,?,?,?,?,?)",
                              (pid, ph['file'], ph['caption'], 'plant', 1 if ph['primary'] else 0, ph.get('source'), who, ts))
                # photos already in the database that belong to this new plant (they were on the wrong page): move them here
                for mv in p.get('take_photos', []):
                    old = c.execute('SELECT ph.id, ph.plant_id, p.code FROM photos ph JOIN plants p ON p.id=ph.plant_id WHERE ph.file=? AND p.code=?', (mv['file'], mv['from'])).fetchone()
                    if not old: continue
                    has = c.execute('SELECT 1 FROM photos WHERE plant_id=? AND is_primary=1', (pid,)).fetchone()
                    c.execute('UPDATE photos SET plant_id=?, is_primary=?, caption=COALESCE(?, caption) WHERE id=?', (pid, 0 if has else 1, mv.get('caption'), old[0]))
                    if not c.execute('SELECT 1 FROM photos WHERE plant_id=? AND is_primary=1', (old[1],)).fetchone():
                        c.execute('UPDATE photos SET is_primary=1 WHERE id=(SELECT MIN(id) FROM photos WHERE plant_id=?)', (old[1],))
                    bump(c, old[1], old[2], who, 'photo_move', 'Photo moved to %s, a different plant (%s)' % (code, label), [('photo', mv['file'], None)])
                c.execute('INSERT INTO plant_versions(plant_id,version,snapshot,changed_by,changed_at,summary) VALUES(?,?,?,?,?,?)',
                          (pid, 1, json.dumps(snapshot(c, pid)), who, ts, 'Initial record from photo analysis (%s)' % label))
                c.execute("INSERT INTO audit_log(plant_id,plant_code,version,action,field,old_value,new_value,changed_by,changed_at,note) VALUES(?,?,?,?,?,?,?,?,?,?)",
                          (pid, code, 1, 'create', None, None, None, who, ts, 'Record created from photos (%s)' % label))
            # photos for plants that already exist
            for ph in b.get('existing_photos', []):
                r = c.execute('SELECT * FROM plants WHERE code=?', (ph['code'],)).fetchone()
                if not r: continue
                copy_seed_photo(ph['file'])
                if ph.get('primary'): c.execute('UPDATE photos SET is_primary=0 WHERE plant_id=?', (r['id'],))
                has = c.execute('SELECT 1 FROM photos WHERE plant_id=? AND is_primary=1', (r['id'],)).fetchone()
                c.execute("INSERT INTO photos(plant_id,file,caption,kind,is_primary,source_name,added_by,added_at) VALUES(?,?,?,?,?,?,?,?)",
                          (r['id'], ph['file'], ph['caption'], 'plant', 1 if (ph.get('primary') or not has) else 0, ph.get('source'), who, ts))
                bump(c, r['id'], r['code'], who, 'photo_add', 'Photo added (%s): %s' % (label, ph['caption']), [('photo', None, ph['file'])])
            # guarded field updates
            for u in b.get('updates', []):
                r = find_plant(c, u)
                if not r:
                    audit_only(c, 'note', None, None, None, who, 'Batch %s could not find %s (%s), so it was skipped' % (label, u.get('name') or u.get('code'), u.get('code')))
                    continue
                todo, skipped = {}, []
                for f, (old, new) in u['set'].items():
                    cur = r[f] if r[f] is not None else ''
                    if str(cur) == str(old if old is not None else ''): todo[f] = new
                    else: skipped.append(f)
                if todo: apply_changes(c, r, todo, who, 'edit', u.get('note') or 'Batch update (%s)' % label)
                for f in skipped:
                    audit_only(c, 'note', f, None, None, who, 'Batch %s left this field alone because it was edited after install' % label, r['id'], r['code'])
            for q in b.get('requests_add', []):
                code = None
                if q.get('code'):
                    r = find_plant(c, {'code': q['code'], 'name': q.get('name'), 'photos': q.get('photos') or []})
                    if not r:
                        audit_only(c, 'note', None, None, None, who, 'Batch %s could not find %s for a request, so it was skipped' % (label, q['code']))
                        continue
                    code = r['code']
                c.execute('INSERT OR IGNORE INTO requests(rkey,plant_code,kind,text,created_by,created_at) VALUES(?,?,?,?,?,?)',
                          (q['key'], code, q.get('kind', 'question'), q['text'], who, ts))
            # records found to be duplicates of another page: archived (hidden, nothing deleted; Move back to the main list undoes it)
            for a in b.get('archive', []):
                r = find_plant(c, a)
                if not r or r['status'] == 'archived': continue
                c.execute("UPDATE plants SET status='archived' WHERE id=?", (r['id'],))
                bump(c, r['id'], r['code'], who, 'archive', a.get('note') or 'Archived (%s)' % label, [('status', r['status'], 'archived')])
            for k in b.get('requests_done', []):   # a key, or {"key": ..., "answer": ...}
                k, ans = (k['key'], k.get('answer')) if isinstance(k, dict) else (k, None)
                c.execute("UPDATE requests SET done=1, done_by=?, done_at=?, answer=COALESCE(answer,?,'Settled by a later update') WHERE rkey=? AND done=0", (who, ts, ans, k))
            for pre in b.get('to_photograph_done', []):
                c.execute('UPDATE to_photograph SET done=1 WHERE done=0 AND label LIKE ?', (pre.replace('%', '') + '%',))
            for t in b.get('to_photograph_add', []):
                if not c.execute('SELECT 1 FROM to_photograph WHERE label=?', (t['label'],)).fetchone():
                    c.execute('INSERT INTO to_photograph(label,note) VALUES(?,?)', (t['label'], t.get('note', '')))
            c.execute('INSERT INTO settings(key,value) VALUES(?,?)', (key, ts))
            c.commit()
        except Exception:
            c.rollback()
            raise

def repair_seed_photos(c):
    """From 1.8.0 plant photos can arrive in separate photo-pack zips, possibly after the batch that uses them was
    applied. Copy any photo the database lists but the photos folder lacks, if the seed folder has it now."""
    fixed = 0
    for (f,) in c.execute('SELECT DISTINCT file FROM photos'):
        if f and not os.path.exists(os.path.join(PHOTO_DIR, f)) and os.path.exists(os.path.join(SEED_DIR, 'photos', f)):
            copy_seed_photo(f); fixed += 1
    if fixed: print(f'Added {fixed} plant photos that arrived in a photo pack', flush=True)
    return fixed

def copy_seed_photo(name):
    src, dst = os.path.join(SEED_DIR, 'photos', name), os.path.join(PHOTO_DIR, name)
    if os.path.exists(src) and not os.path.exists(dst):
        shutil.copyfile(src, dst)

# ---------------------------------------------------------------- helpers
def editor():
    n = re.sub(r'[^\w .\-@]', '', request.headers.get('X-Editor', '').strip())[:40]
    return n or 'Unknown'

def plant_row(c, code):
    r = c.execute('SELECT * FROM plants WHERE code=?', (code,)).fetchone()
    if not r: abort(404, 'plant not found')
    return r

def photos_for(c, pid):
    return [dict(r) for r in c.execute('SELECT id,file,caption,is_primary,added_by,added_at FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id', (pid,))]

def plant_dict(c, r, with_photos=True):
    d = {k: r[k] for k in ['id', 'code'] + FIELD_NAMES + ['version', 'status', 'created_at', 'created_by', 'updated_at', 'updated_by']}
    if with_photos: d['photos'] = photos_for(c, r['id'])
    return d

def snapshot(c, pid):
    r = c.execute('SELECT * FROM plants WHERE id=?', (pid,)).fetchone()
    return {'fields': {n: r[n] for n in FIELD_NAMES}, 'photos': photos_for(c, pid)}

def norm(name, v):
    kind = FIELD_KIND[name]
    if kind == 'int':
        if v in (None, ''): return None
        try: i = int(v)
        except (TypeError, ValueError): abort(400, f'{FIELD_LABEL[name]} must be a whole number')
        lo, hi = INT_RANGES[name]
        if not lo <= i <= hi: abort(400, f'{FIELD_LABEL[name]} must be between {lo} and {hi}')
        return i
    if kind == 'num':
        if v in (None, ''): return None
        try: x = round(float(v), 2)
        except (TypeError, ValueError): abort(400, f'{FIELD_LABEL[name]} must be a number')
        lo, hi = NUM_RANGES[name]
        if not lo <= x <= hi: abort(400, f'{FIELD_LABEL[name]} must be between {lo} and {hi}')
        return x
    s = '' if v is None else str(v).replace('\r\n', '\n').strip()
    if len(s) > 8000: abort(400, f'{FIELD_LABEL[name]} is too long')
    if kind == 'enum':
        allowed = {'winter_plan': WINTER_PLANS, 'site': SITES}.get(name, HEALTH)
        if s not in allowed: abort(400, f'{FIELD_LABEL[name]} must be one of: ' + ', '.join(allowed))
    if kind == 'list': s = '\n'.join(x.strip() for x in s.split('\n') if x.strip())
    return s

def bump(c, pid, code, who, action, summary, changes=None):
    """Increment page version, write snapshot and audit rows. changes = [(field, old, new)]"""
    c.execute('UPDATE plants SET version=version+1, updated_at=?, updated_by=? WHERE id=?', (now(), who, pid))
    ver = c.execute('SELECT version FROM plants WHERE id=?', (pid,)).fetchone()[0]
    c.execute('INSERT INTO plant_versions(plant_id,version,snapshot,changed_by,changed_at,summary) VALUES(?,?,?,?,?,?)',
              (pid, ver, json.dumps(snapshot(c, pid)), who, now(), summary))
    for f, old, new in (changes or [(None, None, None)]):
        c.execute('INSERT INTO audit_log(plant_id,plant_code,version,action,field,old_value,new_value,changed_by,changed_at,note) VALUES(?,?,?,?,?,?,?,?,?,?)',
                  (pid, code, ver, action, f, None if old is None else str(old), None if new is None else str(new), who, now(), summary))
    return ver

def audit_only(c, action, field, old, new, who, note, pid=None, code=None):
    c.execute('INSERT INTO audit_log(plant_id,plant_code,version,action,field,old_value,new_value,changed_by,changed_at,note) VALUES(?,?,?,?,?,?,?,?,?,?)',
              (pid, code, None, action, field, old, new, who, now(), note))

def apply_changes(c, r, new_fields, who, action, note):
    ch = []
    for n, v in new_fields.items():
        if n not in FIELD_KIND: continue
        nv = norm(n, v)
        if (r[n] if r[n] is not None else '') != (nv if nv is not None else ''):
            ch.append((n, r[n], nv))
    if not ch: return r['version'], False
    sets = ','.join(f'{n}=?' for n, _, _ in ch)
    c.execute(f'UPDATE plants SET {sets} WHERE id=?', [nv for _, _, nv in ch] + [r['id']])
    summary = note or ('Edited: ' + ', '.join(FIELD_LABEL[n] for n, _, _ in ch))
    return bump(c, r['id'], r['code'], who, action, summary, ch), True

# ---------------------------------------------------------------- security
@app.before_request
def guard():
    if request.path == '/healthz': return None
    if request.path == '/api/readings' and request.method == 'POST':
        # sensors cannot type a password or send a browser header, so this one route is checked by a secret token instead
        tok = setting(db(), 'ingest_token', '')
        if not tok or not hmac.compare_digest(request.headers.get('X-Ingest-Token', ''), tok): abort(403, 'missing or wrong X-Ingest-Token')
        return None
    if PASSWORD:
        a = request.authorization
        if not (a and hmac.compare_digest(a.password or '', PASSWORD)):
            return Response('Password required', 401, {'WWW-Authenticate': 'Basic realm="Plant database"'})
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        # CSRF guard: custom header cannot be sent cross-site without a CORS preflight (which we never allow)
        if not request.headers.get('X-Editor'): abort(403, 'missing X-Editor header')
        o = request.headers.get('Origin')
        if o and urlparse(o).netloc != request.host: abort(403, 'cross-origin request refused')

@app.after_request
def headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['Referrer-Policy'] = 'no-referrer'
    resp.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'"
    return resp

@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(409)
@app.errorhandler(413)
def err(e):
    return jsonify(error=getattr(e, 'description', str(e))), e.code

def read_version():
    """The release number: VERSION next to server.py (copied in by the Dockerfile), or PLANTDB_VERSION."""
    for f in (os.path.join(os.path.dirname(os.path.abspath(__file__)), 'VERSION'), os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'VERSION')):
        try:
            v = open(f, encoding='utf-8').read().strip()
            if v: return v
        except OSError: pass
    return os.environ.get('PLANTDB_VERSION', 'unknown')
APP_VERSION = read_version()

@app.route('/healthz')
def healthz(): return 'ok ' + APP_VERSION

# ---------------------------------------------------------------- care log and watering (added in 1.8.0)
CARE_KINDS = {'water': 'Watered', 'check': 'Checked: still moist', 'repot': 'Repotted', 'prune': 'Pruned', 'pests': 'Treated for pests', 'note': 'Note'}
RAIN_COUNTS_IN = 0.25          # a day with at least this much rain counts as a watering for plants in the open

def water_base_days(r):
    """How often to check a plant for water in mild weather, from its own setting or its soil moisture range."""
    if r['water_every_days']: return int(r['water_every_days']), 'set on this page'
    lo = r['soil_moisture_low']
    if lo is None: return 7, 'a typical potted plant'
    for limit, days, why in ((10, 14, 'likes to dry out completely'), (20, 10, 'likes to dry out between waterings'), (30, 7, 'likes the top of the mix to dry'),
                             (40, 5, 'likes evenly moist mix'), (101, 4, 'likes constantly moist mix')):
        if lo <= limit: return days, why
    return 7, 'a typical potted plant'

def water_weather(c, today):
    """Recent highs and rain at the home place: (average high of the last 3 days or None, {date: inches of rain})."""
    L = location(c)
    rows = c.execute('SELECT date, data FROM weather_daily WHERE loc_id=? AND date>=? AND date<? ORDER BY date',
                     (L['id'], (today - timedelta(days=21)).isoformat(), today.isoformat())).fetchall()
    highs, rain = [], {}
    for d, data in rows:
        try: x = json.loads(data)
        except ValueError: continue
        if x.get('temperature_2m_max') is not None: highs.append((d, x['temperature_2m_max']))
        pr = x.get('precipitation_sum', x.get('rain_sum'))
        if pr is not None and pr >= RAIN_COUNTS_IN: rain[d] = round(pr, 2)
    hs = [h for _, h in highs[-3:]]
    return (round(sum(hs) / len(hs)) if hs else None), rain

def water_factor(avg_high, inside):
    if inside: return 1.5, 'indoors, where the mix dries more slowly'
    if avg_high is None: return 1.0, 'no recent weather'
    for limit, f, why in ((95, .6, 'very hot'), (85, .8, 'hot'), (70, 1.0, 'warm'), (55, 1.3, 'cool'), (-99, 1.6, 'cold')):
        if avg_high >= limit: return f, f'{why} lately (highs about {avg_high}°F)'
    return 1.0, ''

def water_report(c, codes=None):
    today = local_today(c)
    avg_high, rain = water_weather(c, today)
    q = "SELECT * FROM plants WHERE status='active'" + (' AND code IN (%s)' % ','.join('?' * len(codes)) if codes else '') + ' ORDER BY code'
    plants = c.execute(q, codes or []).fetchall()
    last = {}
    for code, kind, d in c.execute("SELECT plant_code, kind, MAX(done_on) FROM care_log WHERE kind IN ('water','check') GROUP BY plant_code, kind"):
        last.setdefault(code, {})[kind] = d
    out = []
    for r in plants:
        site = r['site'] or 'Outdoors'
        inside, open_sky = site in INSIDE_SITES, site == 'Outdoors'
        base, base_why = water_base_days(r)
        f, f_why = water_factor(avg_high, inside)
        every = max(1, round(base * f))
        lw, lc = last.get(r['code'], {}).get('water'), last.get(r['code'], {}).get('check')
        lr = max((d for d in rain if open_sky and (not lw or d > lw)), default=None)
        start = max(x for x in (lw, lr) if x) if (lw or lr) else None
        st = {'code': r['code'], 'every': every, 'base': base, 'why': base_why, 'weather': f_why, 'site': site,
              'last_water': lw, 'last_rain': lr, 'rain_in': rain.get(lr) if lr else None, 'last_check': lc}
        if not start:
            st.update(state='unknown', next=None, overdue=None)
        else:
            nxt = date.fromisoformat(start) + timedelta(days=every)
            if lc and lc >= start:                                   # checked and still moist: look again in a third of the gap
                nxt = max(nxt, date.fromisoformat(lc) + timedelta(days=max(1, round(every / 3))))
            od = (today - nxt).days
            st.update(next=nxt.isoformat(), overdue=od, state='due' if od >= 0 else 'soon' if od == -1 else 'ok')
        out.append(st)
    return {'today': today.isoformat(), 'avg_high': avg_high, 'rain': rain, 'rain_counts_in': RAIN_COUNTS_IN, 'plants': out}

@app.route('/api/water')
def water_api():
    return jsonify(water_report(db()))

def day_words(d):
    """'2026-10-23' -> 'Friday, Oct 23', for the change log."""
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return f'{d:%A}, {d:%b} {d.day}'

@app.route('/api/care', methods=['GET', 'POST'])
def care():
    c = db()
    if request.method == 'GET':
        q, a = 'SELECT * FROM care_log WHERE 1=1', []
        if request.args.get('plant'): q += ' AND plant_code=?'; a.append(request.args['plant'])
        n = max(1, min(int(request.args.get('n', 200)), 2000))
        return jsonify([dict(x) for x in c.execute(q + ' ORDER BY done_on DESC, id DESC LIMIT ?', a + [n])])
    b = request.get_json(silent=True) or {}
    kind = b.get('kind')
    if kind not in CARE_KINDS: abort(400, 'kind must be one of: ' + ', '.join(CARE_KINDS))
    codes = b.get('plants') or ([b['plant']] if b.get('plant') else [])
    if not isinstance(codes, list) or not codes: abort(400, 'Choose at least one plant')
    codes = list(dict.fromkeys(str(x) for x in codes))[:300]
    day = str(b.get('done_on') or local_today(c).isoformat())
    try: date.fromisoformat(day)
    except ValueError: abort(400, 'done_on must look like 2026-10-23')
    if day > local_today(c).isoformat(): abort(400, 'That date is in the future')
    note = str(b.get('note') or '').strip()[:500]
    if kind == 'note' and not note: abort(400, 'Write the note')
    who, ids = editor(), []
    for code in codes:
        r = plant_row(c, code)
        ids.append(c.execute('INSERT INTO care_log(plant_code,kind,done_on,note,created_by,created_at) VALUES(?,?,?,?,?,?)',
                             (r['code'], kind, day, note, who, now())).lastrowid)
        audit_only(c, 'care', 'care_log', None, f'{CARE_KINDS[kind]} {day}' + (f': {note}' if note else ''), who,
                   CARE_KINDS[kind] + (f': {note}' if note else '') + ('' if day == local_today(c).isoformat() else f' (for {day_words(day)})'), r['id'], r['code'])
    c.commit()
    return jsonify(ids=ids, water=water_report(c, codes)['plants']), 201

@app.route('/api/care/<int:i>', methods=['DELETE'])
def care_one(i):
    c = db()
    old = c.execute('SELECT * FROM care_log WHERE id=?', (i,)).fetchone()
    if not old: abort(404, 'entry not found')
    c.execute('DELETE FROM care_log WHERE id=?', (i,))
    r = c.execute('SELECT id FROM plants WHERE code=?', (old['plant_code'],)).fetchone()
    audit_only(c, 'care', 'care_log', f"{CARE_KINDS.get(old['kind'], old['kind'])} {old['done_on']}", None, editor(),
               'Removed from the care log: ' + CARE_KINDS.get(old['kind'], old['kind']) + ', ' + day_words(old['done_on']), r['id'] if r else None, old['plant_code'])
    c.commit()
    return jsonify(ok=True)

@app.route('/api/version')
def version(): return jsonify(version=APP_VERSION)

# ---------------------------------------------------------------- api: meta/reference
@app.route('/api/meta')
def meta():
    c = db()
    return jsonify(fields=[{'name': n, 'kind': k, 'label': l} for n, k, l in FIELDS], winter_plans=WINTER_PLANS, health=HEALTH, sites=SITES, inside_sites=INSIDE_SITES,
                   counts={'plants': c.execute("SELECT COUNT(*) FROM plants WHERE status='active'").fetchone()[0],
                           'photos': c.execute('SELECT COUNT(*) FROM photos').fetchone()[0]},
                   password_protected=bool(PASSWORD), int_ranges=INT_RANGES, num_ranges=NUM_RANGES, version=APP_VERSION)

@app.route('/api/reference')
def reference():
    r = db().execute("SELECT value FROM settings WHERE key='reference'").fetchone()
    return jsonify(json.loads(r[0]) if r else {})

@app.route('/api/settings', methods=['GET', 'PUT'])
def settings():
    c = db()
    if request.method == 'PUT':
        base = str((request.get_json(silent=True) or {}).get('base_url', '')).strip().rstrip('/')
        if base and not re.match(r'^https?://[\w.\-]+(:\d+)?$', base): abort(400, 'Base URL must look like http://192.168.1.20:8080')
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('base_url',?)", (base,))
        audit_only(c, 'setting', 'base_url', None, base, editor(), 'Label QR base URL changed')
        c.commit()
    r = c.execute("SELECT value FROM settings WHERE key='base_url'").fetchone()
    return jsonify(base_url=r[0] if r else '')

# ---------------------------------------------------------------- api: plants
@app.route('/api/plants')
def list_plants():
    c = db()
    q = request.args.get('q', '').strip().lower()
    status = request.args.get('status', 'active')
    rows = c.execute('SELECT * FROM plants WHERE status=? ORDER BY code', (status,)).fetchall()
    open_req = {k: n for k, n in c.execute('SELECT plant_code, COUNT(*) FROM requests WHERE done=0 AND plant_code IS NOT NULL GROUP BY plant_code')}
    out = []
    for r in rows:
        hay = ' '.join(str(r[n] or '') for n in ('code', 'common_name', 'scientific_name', 'aliases', 'location', 'container', 'plant_type', 'notes')).lower()
        if q and q not in hay: continue
        p = c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (r['id'],)).fetchone()
        out.append({'code': r['code'], 'common_name': r['common_name'], 'scientific_name': r['scientific_name'], 'plant_type': r['plant_type'],
                    'location': r['location'], 'aliases': r['aliases'], 'id_confidence': r['id_confidence'], 'winter_plan': r['winter_plan'], 'health_rating': r['health_rating'],
                    'site': r['site'] or 'Outdoors', 'version': r['version'], 'updated_at': r['updated_at'], 'updated_by': r['updated_by'], 'photo': p['file'] if p else None,
                    'temp_damage_below': r['temp_damage_below'], 'temp_ideal_low': r['temp_ideal_low'], 'temp_ideal_high': r['temp_ideal_high'],
                    'fert_from_month': r['fert_from_month'], 'fert_to_month': r['fert_to_month'], 'fert_every_days': r['fert_every_days'], 'fertilizer': r['fertilizer'],
                    'requests_open': open_req.get(r['code'], 0)})
    return jsonify(out)

@app.route('/api/plants/<code>')
def get_plant(code):
    c = db()
    r = plant_row(c, code)
    return jsonify(plant_dict(c, r) | {'requests': [dict(x) for x in c.execute('SELECT * FROM requests WHERE plant_code=? ORDER BY done, id', (r['code'],))]})

# ---------------------------------------------------------------- requests: what Claude needs from you
REQUEST_KINDS = ('check', 'question', 'photo', 'info')

@app.route('/api/requests', methods=['GET', 'POST'])
def requests_list():
    c = db()
    if request.method == 'POST':
        b = request.get_json(silent=True) or {}
        text = str(b.get('text', '')).strip()[:1000]
        if not text: abort(400, 'Write what is needed')
        code = (b.get('plant_code') or '').strip() or None
        if code: plant_row(c, code)
        kind = b.get('kind') if b.get('kind') in REQUEST_KINDS else 'question'
        rid = c.execute('INSERT INTO requests(plant_code,kind,text,created_by,created_at) VALUES(?,?,?,?,?)', (code, kind, text, editor(), now())).lastrowid
        audit_only(c, 'request', 'request', None, text, editor(), 'Request added', None, code)
        c.commit()
        return jsonify(dict(c.execute('SELECT * FROM requests WHERE id=?', (rid,)).fetchone())), 201
    q, a = 'SELECT * FROM requests', []
    if request.args.get('open') == '1': q += ' WHERE done=0'
    return jsonify([dict(r) for r in c.execute(q + ' ORDER BY done, plant_code IS NULL, plant_code, id', a)])

@app.route('/api/requests/<int:rid>', methods=['PUT'])
def request_one(rid):
    c = db()
    r = c.execute('SELECT * FROM requests WHERE id=?', (rid,)).fetchone()
    if not r: abort(404, 'request not found')
    b = request.get_json(silent=True) or {}
    done = 1 if b.get('done', True) else 0
    answer = str(b.get('answer', '') or '').strip()[:2000] or None
    c.execute('UPDATE requests SET done=?, answer=COALESCE(?, answer), done_by=?, done_at=? WHERE id=?',
              (done, answer, editor() if done else None, now() if done else None, rid))
    pr = c.execute('SELECT id FROM plants WHERE code=?', (r['plant_code'],)).fetchone() if r['plant_code'] else None
    audit_only(c, 'request', 'request', r['text'], (answer or 'Done') if done else 'Reopened', editor(),
               ('Request answered' if answer else 'Request marked done') if done else 'Request reopened', pr['id'] if pr else None, r['plant_code'])
    c.commit()
    return jsonify(dict(c.execute('SELECT * FROM requests WHERE id=?', (rid,)).fetchone()))

@app.route('/api/plants', methods=['POST'])
def create_plant():
    c = db()
    body = request.get_json(silent=True) or {}
    f = body.get('fields', {})
    if not str(f.get('common_name', '')).strip(): abort(400, 'Common name is required')
    n = c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(code,3) AS INTEGER)),0)+1 FROM plants").fetchone()[0]
    code, who, ts = f'P-{n:03d}', editor(), now()
    f = dict(f)
    f['winter_plan'] = f.get('winter_plan') or 'Move indoors'
    f['health_rating'] = f.get('health_rating') or 'Fair'
    f['site'] = f.get('site') or 'Outdoors'
    vals = {k: norm(k, f.get(k)) for k in FIELD_NAMES}
    cols = ['code'] + FIELD_NAMES + ['version', 'status', 'created_at', 'created_by', 'updated_at', 'updated_by']
    cur = c.execute(f"INSERT INTO plants({','.join(cols)}) VALUES({','.join('?' * len(cols))})",
                    [code] + [vals[k] for k in FIELD_NAMES] + [1, 'active', ts, who, ts, who])
    pid = cur.lastrowid
    c.execute('INSERT INTO plant_versions(plant_id,version,snapshot,changed_by,changed_at,summary) VALUES(?,?,?,?,?,?)',
              (pid, 1, json.dumps(snapshot(c, pid)), who, ts, 'Record created'))
    audit_only(c, 'create', None, None, None, who, 'Record created', pid, code)
    c.execute('UPDATE audit_log SET version=1 WHERE plant_id=? AND action=?', (pid, 'create'))
    c.commit()
    return jsonify(plant_dict(c, plant_row(c, code))), 201

@app.route('/api/plants/<code>', methods=['PUT'])
def update_plant(code):
    c = db()
    r = plant_row(c, code)
    body = request.get_json(silent=True) or {}
    if int(body.get('base_version', -1)) != r['version']:
        return jsonify(error='This page was changed by someone else since you opened it. Reload to see version %d.' % r['version'],
                       current=plant_dict(c, r)), 409
    if 'common_name' in body.get('fields', {}) and not str(body['fields']['common_name']).strip(): abort(400, 'Common name is required')
    ver, changed = apply_changes(c, r, body.get('fields', {}), editor(), 'update', (body.get('note') or '').strip()[:300])
    c.commit()
    return jsonify(plant_dict(c, plant_row(c, code)) | {'changed': changed})

@app.route('/api/plants/<code>/site', methods=['POST'])
def plant_site(code):
    """Change only where the plant is (Outdoors, Indoors...). No version check: one field, chosen from a list."""
    c = db()
    r = plant_row(c, code)
    site = str((request.get_json(silent=True) or {}).get('site', ''))
    if site not in SITES: abort(400, 'Location must be one of: ' + ', '.join(SITES))
    apply_changes(c, r, {'site': site}, editor(), 'update', ('Moved ' + site.lower()) if site in ('Indoors', 'Outdoors') else 'Moved to ' + site.lower())
    c.commit()
    return jsonify(plant_dict(c, plant_row(c, code)))

@app.route('/api/plants/<code>/status', methods=['POST'])
def plant_status(code):
    c = db()
    r = plant_row(c, code)
    new = 'archived' if (request.get_json(silent=True) or {}).get('archived') else 'active'
    if new != r['status']:
        c.execute('UPDATE plants SET status=? WHERE id=?', (new, r['id']))
        bump(c, r['id'], code, editor(), 'archive' if new == 'archived' else 'unarchive', 'Record ' + new, [('status', r['status'], new)])
        c.commit()
    return jsonify(plant_dict(c, plant_row(c, code)))

# ---------------------------------------------------------------- plant timeline (added in 1.8.0)
TL_KEY_FIELDS = ('common_name', 'health_rating', 'id_confidence', 'site', 'winter_plan')
TL_KIND = {'create': 'created', 'update': 'change', 'edit': 'change', 'restore': 'change', 'archive': 'change', 'unarchive': 'change',
           'photo_add': 'photo', 'photo_assign': 'photo', 'photo_remove': 'photo', 'photo_move': 'photo',
           'fertilizer': 'care', 'care': 'care', 'frost': 'care'}

def tl_title(a):
    """A plain title for one change-log row."""
    act, note = a['action'], a['note'] or ''
    if act == 'photo_assign':
        src = (a['old_value'] or '').replace('from ', '', 1)
        return 'Photo moved here from ' + src if src.startswith('P-') else 'Photo added from the Photos page'
    if act == 'photo_move' and note.endswith('moved away'):
        dst = (a['new_value'] or '').replace('moved to ', '', 1)
        return 'Photo moved to ' + dst if dst.startswith('P-') else 'Photo moved to the Photos page'
    return note or FIELD_LABEL.get(a['field'], a['field'] or 'Changed')

@app.route('/api/plants/<code>/timeline')
def plant_timeline(code):
    """One dated list for a plant, built from its change log and its answered requests: page changes (with the ones
    that matter picked out), photos, feedings and other care. Several fields saved together are one event."""
    c = db()
    r = plant_row(c, code)
    photos = {x['file']: dict(x) for x in c.execute('SELECT id, file, caption, added_at, is_primary FROM photos WHERE plant_id=?', (r['id'],))}
    events, by_key = [], {}
    for a in c.execute('SELECT * FROM audit_log WHERE plant_id=? ORDER BY id', (r['id'],)):
        kind = TL_KIND.get(a['action'])
        if not kind: continue
        key = (a['changed_at'], 'photos' if a['action'] == 'photo_add' else a['note'] or '', a['action'])
        e = by_key.get(key)
        if not e:
            e = {'at': a['changed_at'], 'kind': kind, 'action': a['action'], 'title': tl_title(a), 'by': a['changed_by'], 'changes': [], 'other': 0, 'photos': []}
            by_key[key] = e; events.append(e)
        if kind == 'photo':
            f = a['new_value'] or a['old_value']
            if f in photos and photos[f] not in e['photos']: e['photos'].append(photos[f])
        elif a['field'] in TL_KEY_FIELDS:
            e['changes'].append({'field': a['field'], 'label': FIELD_LABEL.get(a['field'], a['field']), 'old': a['old_value'], 'new': a['new_value']})
        elif kind == 'change' and a['field']:
            e['other'] += 1
    for q in c.execute('SELECT * FROM requests WHERE plant_code=? AND done=1 AND done_at IS NOT NULL', (r['code'],)):
        said = q['answer'] if q['answer'] and q['answer'] != 'Done' else None   # answered here or settled by an update
        events.append({'at': q['done_at'], 'kind': 'request', 'action': 'request', 'title': 'Request answered' if said else 'Request marked done',
                       'by': q['done_by'] or '', 'changes': [], 'other': 0, 'photos': [], 'question': q['text'], 'answer': said})
    events.sort(key=lambda e: e['at'] or '')
    for e in events:                                  # several photos added together read as one entry
        if e['action'] == 'photo_add' and len(e['photos']) > 1: e['title'] = f"{len(e['photos'])} photos added"
    seen = {x['file'] for e in events for x in e['photos']}
    rest = [x for x in photos.values() if x['file'] not in seen]
    if rest:                                          # photos that came with the page when it was created
        first = next((e for e in events if e['kind'] == 'created'), None)
        if first: first['photos'] = sorted(rest, key=lambda x: x['id'])
    health = [{'at': e['at'], 'old': ch['old'], 'new': ch['new']} for e in events for ch in e['changes'] if ch['field'] == 'health_rating']
    conf = [{'at': e['at'], 'old': ch['old'], 'new': ch['new']} for e in events for ch in e['changes'] if ch['field'] == 'id_confidence']
    events.reverse()
    return jsonify(code=r['code'], events=events, health=health, confidence=conf, current={'health': r['health_rating'], 'id_confidence': r['id_confidence']},
                   photos=sorted(photos.values(), key=lambda x: (x['added_at'] or '', x['id'])))

@app.route('/api/plants/<code>/history')
def history(code):
    c = db()
    r = plant_row(c, code)
    audit = [dict(x) for x in c.execute('SELECT * FROM audit_log WHERE plant_id=? ORDER BY id DESC', (r['id'],))]
    vers = [dict(x) for x in c.execute('SELECT version,changed_by,changed_at,summary FROM plant_versions WHERE plant_id=? ORDER BY version DESC', (r['id'],))]
    for a in audit: a['label'] = FIELD_LABEL.get(a['field'], a['field'])
    return jsonify(audit=audit, versions=vers, current=r['version'])

@app.route('/api/plants/<code>/versions/<int:n>')
def get_version(code, n):
    c = db()
    r = plant_row(c, code)
    v = c.execute('SELECT * FROM plant_versions WHERE plant_id=? AND version=?', (r['id'], n)).fetchone()
    if not v: abort(404, 'version not found')
    return jsonify(version=n, changed_by=v['changed_by'], changed_at=v['changed_at'], summary=v['summary'], snapshot=json.loads(v['snapshot']))

@app.route('/api/plants/<code>/restore/<int:n>', methods=['POST'])
def restore(code, n):
    c = db()
    r = plant_row(c, code)
    v = c.execute('SELECT snapshot FROM plant_versions WHERE plant_id=? AND version=?', (r['id'], n)).fetchone()
    if not v: abort(404, 'version not found')
    fields = json.loads(v['snapshot'])['fields']
    ver, changed = apply_changes(c, r, fields, editor(), 'restore', f'Restored text fields from version {n} (photos are not changed)')
    c.commit()
    return jsonify(plant_dict(c, plant_row(c, code)) | {'changed': changed})

@app.route('/api/audit')
def audit():
    c = db()
    limit = min(int(request.args.get('limit', 200)), 2000)
    rows = [dict(x) for x in c.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT ?', (limit,))]
    for a in rows: a['label'] = FIELD_LABEL.get(a['field'], a['field'])
    return jsonify(rows)

# ---------------------------------------------------------------- photos
def save_image(file_storage):
    try:
        im = Image.open(file_storage.stream)
        im = ImageOps.exif_transpose(im).convert('RGB')        # re-encode: strips EXIF incl. GPS
    except Exception:
        abort(400, f'{file_storage.filename or "file"} is not a supported image (use JPG or PNG)')
    im.thumbnail((1600, 1600))
    name = f'up_{uuid.uuid4().hex[:16]}.jpg'
    im.save(os.path.join(PHOTO_DIR, name), 'JPEG', quality=84, optimize=True)
    return name

@app.route('/api/plants/<code>/photos', methods=['POST'])
def add_photos(code):
    c = db()
    r = plant_row(c, code)
    files = request.files.getlist('files')
    if not files: abort(400, 'no files')
    who, cap = editor(), request.form.get('caption', '').strip()[:200]
    has_primary = c.execute('SELECT 1 FROM photos WHERE plant_id=? AND is_primary=1', (r['id'],)).fetchone()
    changes = []
    for i, f in enumerate(files):
        name = save_image(f)
        prim = 0 if has_primary or i else 1
        c.execute('INSERT INTO photos(plant_id,file,caption,kind,is_primary,source_name,added_by,added_at) VALUES(?,?,?,?,?,?,?,?)',
                  (r['id'], name, cap or (f.filename or '')[:80], 'plant', prim, f.filename, who, now()))
        changes.append(('photo', None, name))
    bump(c, r['id'], code, who, 'photo_add', f'Added {len(files)} photo(s)', changes)
    c.commit()
    return jsonify(plant_dict(c, plant_row(c, code))), 201

@app.route('/api/photos', methods=['POST'])
def add_unassigned():
    c = db()
    files = request.files.getlist('files')
    if not files: abort(400, 'no files')
    who, cap = editor(), request.form.get('caption', '').strip()[:200]
    for f in files:
        name = save_image(f)
        c.execute('INSERT INTO photos(plant_id,file,caption,kind,is_primary,source_name,added_by,added_at) VALUES(NULL,?,?,?,0,?,?,?)',
                  (name, cap or (f.filename or '')[:80], 'other', f.filename, who, now()))
        audit_only(c, 'photo_add', 'photo', None, name, who, 'Unassigned photo uploaded')
    c.commit()
    return jsonify(ok=True), 201

@app.route('/api/photos/unassigned')
def unassigned():
    return jsonify([dict(r) for r in db().execute('SELECT id,file,caption,kind,added_by,added_at FROM photos WHERE plant_id IS NULL ORDER BY id')])

@app.route('/api/photos/<int:pid>', methods=['PATCH'])
def patch_photo(pid):
    c = db()
    ph = c.execute('SELECT * FROM photos WHERE id=?', (pid,)).fetchone()
    if not ph: abort(404, 'photo not found')
    body, who = request.get_json(silent=True) or {}, editor()
    owner = c.execute('SELECT * FROM plants WHERE id=?', (ph['plant_id'],)).fetchone() if ph['plant_id'] else None
    if 'plant_code' in body:                                   # assign / move
        tgt = c.execute('SELECT * FROM plants WHERE code=?', (body['plant_code'],)).fetchone() if body['plant_code'] else None
        if body['plant_code'] and not tgt: abort(404, 'target plant not found')
        old_code = owner['code'] if owner else None
        c.execute('UPDATE photos SET plant_id=?, is_primary=0, kind=? WHERE id=?', (tgt['id'] if tgt else None, 'plant' if tgt else 'other', pid))
        if owner: _fix_primary(c, owner['id']); bump(c, owner['id'], owner['code'], who, 'photo_move', f'Photo {ph["file"]} moved away', [('photo', ph['file'], f'moved to {body["plant_code"] or "unassigned"}')])
        if tgt: _fix_primary(c, tgt['id']); bump(c, tgt['id'], tgt['code'], who, 'photo_assign', f'Photo {ph["file"]} assigned', [('photo', f'from {old_code or "unassigned"}', ph['file'])])
        if not owner and not tgt: pass
    if 'caption' in body and str(body['caption']) != ph['caption']:
        c.execute('UPDATE photos SET caption=? WHERE id=?', (str(body['caption'])[:200], pid))
        if owner: bump(c, owner['id'], owner['code'], who, 'photo_caption', 'Photo caption edited', [('photo caption', ph['caption'], str(body['caption'])[:200])])
        else: audit_only(c, 'photo_caption', 'photo caption', ph['caption'], str(body['caption'])[:200], who, 'Unassigned photo caption edited')
    if body.get('is_primary') and owner:
        c.execute('UPDATE photos SET is_primary=0 WHERE plant_id=?', (owner['id'],))
        c.execute('UPDATE photos SET is_primary=1 WHERE id=?', (pid,))
        bump(c, owner['id'], owner['code'], who, 'photo_primary', 'Main photo changed', [('main photo', None, ph['file'])])
    c.commit()
    return jsonify(ok=True)

def _fix_primary(c, plant_id):
    if not c.execute('SELECT 1 FROM photos WHERE plant_id=? AND is_primary=1', (plant_id,)).fetchone():
        c.execute('UPDATE photos SET is_primary=1 WHERE id=(SELECT id FROM photos WHERE plant_id=? ORDER BY id LIMIT 1)', (plant_id,))

@app.route('/api/photos/<int:pid>', methods=['DELETE'])
def delete_photo(pid):
    c = db()
    ph = c.execute('SELECT * FROM photos WHERE id=?', (pid,)).fetchone()
    if not ph: abort(404, 'photo not found')
    who = editor()
    c.execute('DELETE FROM photos WHERE id=?', (pid,))
    if not c.execute('SELECT 1 FROM photos WHERE file=?', (ph['file'],)).fetchone():       # keep file if another record shares it
        src = os.path.join(PHOTO_DIR, ph['file'])
        if os.path.exists(src): shutil.move(src, os.path.join(TRASH_DIR, ph['file']))
    if ph['plant_id']:
        o = c.execute('SELECT * FROM plants WHERE id=?', (ph['plant_id'],)).fetchone()
        _fix_primary(c, o['id'])
        bump(c, o['id'], o['code'], who, 'photo_remove', 'Photo removed (file kept in photos_deleted)', [('photo', ph['file'], None)])
    else:
        audit_only(c, 'photo_remove', 'photo', ph['file'], None, who, 'Unassigned photo removed')
    c.commit()
    return jsonify(ok=True)

@app.route('/photos/<path:name>')
def photo(name):
    return send_from_directory(PHOTO_DIR, name, max_age=3600)

@app.route('/thumbs/<path:name>')
def thumb(name):
    safe = os.path.basename(name)
    src, dst = os.path.join(PHOTO_DIR, safe), os.path.join(THUMB_DIR, safe)
    if not os.path.exists(src): abort(404)
    if not os.path.exists(dst):
        im = Image.open(src); im.thumbnail((520, 520)); im.save(dst, 'JPEG', quality=80)
    return send_from_directory(THUMB_DIR, safe, max_age=3600)

# ---------------------------------------------------------------- to-photograph list
@app.route('/api/to-photograph', methods=['GET', 'POST'])
def to_photograph():
    c = db()
    if request.method == 'POST':
        b = request.get_json(silent=True) or {}
        if not str(b.get('label', '')).strip(): abort(400, 'label required')
        c.execute('INSERT INTO to_photograph(label,note) VALUES(?,?)', (str(b['label']).strip()[:200], str(b.get('note', '') or '').strip()[:1000]))
        c.commit()
    return jsonify([dict(r) for r in c.execute('SELECT * FROM to_photograph ORDER BY done, id')])

@app.route('/api/to-photograph/<int:i>', methods=['PATCH', 'DELETE'])
def to_photograph_item(i):
    c = db()
    if request.method == 'DELETE': c.execute('DELETE FROM to_photograph WHERE id=?', (i,))
    else:
        b = request.get_json(silent=True) or {}
        if 'done' in b: c.execute('UPDATE to_photograph SET done=? WHERE id=?', (1 if b.get('done') else 0, i))
        if 'label' in b:
            if not str(b['label']).strip(): abort(400, 'label required')
            c.execute('UPDATE to_photograph SET label=? WHERE id=?', (str(b['label']).strip()[:200], i))
        if 'note' in b: c.execute('UPDATE to_photograph SET note=? WHERE id=?', (str(b['note'] or '').strip()[:1000], i))
    c.commit()
    return jsonify(ok=True)

# ---------------------------------------------------------------- qr, export
@app.route('/api/plants/<code>/qr.svg')
def qr(code):
    c = db(); plant_row(c, code)
    base = request.args.get('base', '').rstrip('/') or request.host_url.rstrip('/')
    if not re.match(r'^https?://[\w.\-]+(:\d+)?$', base): abort(400, 'bad base url')
    buf = io.BytesIO()
    segno.make(f'{base}/#/plant/{code}', error='m').save(buf, kind='svg', scale=6, border=2, dark='#000', light='#fff', xmldecl=False, svgns=True)
    return Response(buf.getvalue(), mimetype='image/svg+xml')

@app.route('/api/export.json')
def export_json():
    c = db()
    data = {'exported_at': now(), 'plants': [plant_dict(c, r) for r in c.execute('SELECT * FROM plants ORDER BY code')],
            'unassigned_photos': [dict(r) for r in c.execute('SELECT * FROM photos WHERE plant_id IS NULL')],
            'audit_log': [dict(r) for r in c.execute('SELECT * FROM audit_log ORDER BY id')],
            'fertilizer_log': [dict(r) for r in c.execute('SELECT * FROM fertilizer_log ORDER BY applied_on, id')],
            'requests': [dict(r) for r in c.execute('SELECT * FROM requests ORDER BY id')],
            'weather_places': [loc_dict(r) for r in c.execute('SELECT * FROM locations ORDER BY id')]}
    return Response(json.dumps(data, indent=1), mimetype='application/json', headers={'Content-Disposition': 'attachment; filename=plants-export.json'})

def _csv_safe(v):
    s = '' if v is None else str(v)
    return "'" + s if s[:1] in '=+-@\t\r' else s                 # neutralise spreadsheet formulas

@app.route('/api/export.csv')
def export_csv():
    c = db()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(['code', 'version', 'status', 'updated_at', 'updated_by'] + FIELD_NAMES)
    for r in c.execute('SELECT * FROM plants ORDER BY code'):
        w.writerow([_csv_safe(r[k]) for k in ['code', 'version', 'status', 'updated_at', 'updated_by'] + FIELD_NAMES])
    return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=plants.csv'})

@app.route('/api/readings.csv')
def export_readings():
    """All stored readings (online weather, sensor and typed-in) for spreadsheets. Optional ?source=weather|sensor|manual"""
    c = db()
    out = io.StringIO(); w = csv.writer(out)
    cols = ['ts', 'source', 'device'] + list(METRICS)
    w.writerow(['when_utc', 'source', 'device', 'temp_f', 'humidity_pct', 'par', 'lux', 'soil_moisture_pct', 'soil_temp_f', 'soil_ph'])
    q, a = 'SELECT * FROM readings', []
    if request.args.get('source'): q += ' WHERE source=?'; a.append(request.args['source'])
    for r in c.execute(q + ' ORDER BY ts', a):
        w.writerow([_csv_safe(r[k]) for k in cols])
    return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=readings.csv'})

@app.route('/api/audit.csv')
def export_audit():
    c = db()
    out = io.StringIO(); w = csv.writer(out)
    w.writerow(['when_utc', 'plant', 'version', 'action', 'field', 'before', 'after', 'by', 'note'])
    for r in c.execute('SELECT * FROM audit_log ORDER BY id'):
        w.writerow([_csv_safe(x) for x in (r['changed_at'], r['plant_code'], r['version'], r['action'], FIELD_LABEL.get(r['field'], r['field']), r['old_value'], r['new_value'], r['changed_by'], r['note'])])
    return Response(out.getvalue(), mimetype='text/csv', headers={'Content-Disposition': 'attachment; filename=audit-log.csv'})

# ---------------------------------------------------------------- weather, sensors and current conditions
DEFAULT_LOC = {'name': 'Round Rock, TX', 'lat': 30.5083, 'lon': -97.6789, 'tz': 'America/Chicago'}
LUX_PER_PAR = 54.0          # sunlight: about 54 lux per umol/m2/s. A rough conversion; grow lights differ.
PAR_PER_WM2 = 2.1           # sunlight: global radiation (W/m2) to PAR (umol/m2/s), about 2.1
METRICS = ('temp_f', 'humidity', 'par', 'lux', 'soil_moisture', 'soil_temp_f', 'soil_ph')
LIMITS = {'temp_f': (-60, 160), 'humidity': (0, 100), 'par': (0, 4000), 'lux': (0, 200000),
          'soil_moisture': (0, 100), 'soil_temp_f': (-40, 160), 'soil_ph': (0, 14)}

def setting(c, key, default=None):
    r = c.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    return r[0] if r else default

def set_setting(c, key, value):
    c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)', (key, value))

def migrate_places(c):
    """Version 1.5: weather can be tracked for several places. The place used until now becomes the home place
    (the one your plants are at) and keeps all its readings: its rows are tagged device 'open-meteo', as before."""
    if 'loc_id' not in {r[1] for r in c.execute('PRAGMA table_info(weather_runs)')}:
        c.execute('ALTER TABLE weather_runs ADD COLUMN loc_id INTEGER NOT NULL DEFAULT 1')
    if 'loc_id' not in {r[1] for r in c.execute('PRAGMA table_info(weather_daily)')}:
        c.execute('ALTER TABLE weather_daily RENAME TO weather_daily_v13')
        c.execute("""CREATE TABLE weather_daily(loc_id INTEGER NOT NULL DEFAULT 1, date TEXT NOT NULL, data TEXT NOT NULL,
                     kind TEXT NOT NULL DEFAULT 'observed', updated_at TEXT NOT NULL, PRIMARY KEY(loc_id, date))""")
        c.execute('INSERT INTO weather_daily(loc_id,date,data,kind,updated_at) SELECT 1,date,data,kind,updated_at FROM weather_daily_v13')
        c.execute('DROP TABLE weather_daily_v13')
    if not c.execute('SELECT 1 FROM locations LIMIT 1').fetchone():
        def st(k, d=None):
            r = c.execute('SELECT value FROM settings WHERE key=?', (k,)).fetchone()
            return r[0] if r else d
        try: old = {**DEFAULT_LOC, **json.loads(st('location', '') or '{}')}
        except ValueError: old = dict(DEFAULT_LOC)
        c.execute('INSERT INTO locations(id,name,lat,lon,tz,enabled,is_home,device,forecast,status,detail_since,created_at) VALUES(1,?,?,?,?,?,1,?,?,?,?,?)',
                  (old['name'], old['lat'], old['lon'], old['tz'], 1 if st('weather_enabled', '1') == '1' else 0, 'open-meteo',
                   st('forecast'), st('weather_status'), st('wx_detail_since'), now()))
    c.commit()

LOC_COLS = ('id', 'name', 'lat', 'lon', 'tz', 'enabled', 'is_home', 'device', 'detail_since', 'note', 'created_at')
def loc_dict(r):
    d = {k: r[k] for k in LOC_COLS}
    d['enabled'], d['is_home'] = bool(d['enabled']), bool(d['is_home'])
    return d

def loc_get(c, loc_id=None):
    """A place by id; the home place when loc_id is empty. Falls back to the built-in default if the table is empty."""
    r = cur = None
    if loc_id not in (None, '', 'home'):
        try: cur = c.execute('SELECT * FROM locations WHERE id=?', (int(loc_id),)); r = cur.fetchone()
        except (TypeError, ValueError): r = None
        if r is None: return None
    else:
        cur = c.execute('SELECT * FROM locations ORDER BY is_home DESC, id LIMIT 1'); r = cur.fetchone()
    if r is not None and not isinstance(r, sqlite3.Row): r = dict(zip([d[0] for d in cur.description], r))   # works with plain connections too
    if r is None: return {**DEFAULT_LOC, 'id': 1, 'device': 'open-meteo', 'enabled': True, 'is_home': True, 'detail_since': None, 'note': '', 'created_at': None}
    return loc_dict(r)

def loc_json(c, loc_id, col):
    r = c.execute(f'SELECT {col} FROM locations WHERE id=?', (loc_id,)).fetchone()
    try: return json.loads(r[0]) if r and r[0] else {}
    except ValueError: return {}

def loc_set(c, loc_id, **kw):
    for k, v in kw.items():
        c.execute(f'UPDATE locations SET {k}=? WHERE id=?', (v, loc_id))

def req_loc(c, key='loc'):
    """The place a request is about (?loc=ID, or loc in a JSON body); the home place when not given."""
    v = request.args.get(key)
    if v is None and request.is_json: v = (request.get_json(silent=True) or {}).get(key)
    L = loc_get(c, v)
    if L is None: abort(404, 'That place does not exist (it may have been removed)')
    return L

def location(c):
    """The home place: where your plants are. Plant pages, current conditions and frost warnings use it."""
    return loc_get(c)

def tzinfo(name):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        return timezone(timedelta(hours=-6))

def iso(t): return datetime.fromtimestamp(t, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
def parse_ts(s):
    s = str(s).strip().replace('Z', '+00:00')
    d = datetime.fromisoformat(s)
    if d.tzinfo is None: d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)

def vpd_kpa(temp_f, rh):
    if temp_f is None or rh is None: return None
    t = (temp_f - 32) / 1.8
    es = 0.6108 * math.exp(17.27 * t / (t + 237.3))
    return round(es * (1 - rh / 100.0), 2)

class OMError(Exception):
    def __init__(self, code, reason=''):
        super().__init__(f'HTTP {code}: {reason}'[:300]); self.code, self.reason = code, reason

NET_RETRY_WAITS = (5, 15, 45, 90)     # seconds to wait before each retry after a dropped connection or a busy server

def _wait(sec, why):
    WX_JOB.update(waiting_until=time.time() + sec, waiting_why=why, beat=time.time())
    time.sleep(sec)
    WX_JOB.pop('waiting_until', None); WX_JOB.pop('waiting_why', None)

def http_json(url, tries=3):
    """Fetch JSON from Open-Meteo. Dropped connections, timeouts and server hiccups (5xx) are retried up to 4 times
    with growing pauses (5 s, 15 s, 45 s, 90 s); the per-minute limit is waited out. Other refusals raise OMError."""
    req = urllib.request.Request(url, headers={'User-Agent': 'plant-database/1.3 (home garden record)'})
    minute_waits = 0
    for attempt in range(len(NET_RETRY_WAITS) + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            WX_JOB['retries_in_a_row'] = 0
            return json.loads(data.decode('utf-8'))
        except urllib.error.HTTPError as e:
            try: reason = json.loads(e.read().decode('utf-8')).get('reason', '')
            except Exception: reason = str(e.reason)
            if e.code == 429 and 'minutely' in reason.lower() and minute_waits < tries:
                minute_waits += 1; _wait(62, "Open-Meteo's per-minute limit"); continue
            if e.code >= 500 and attempt < len(NET_RETRY_WAITS):
                WX_JOB['retries'] = WX_JOB.get('retries', 0) + 1
                _wait(NET_RETRY_WAITS[attempt], f'Open-Meteo was busy (HTTP {e.code}); trying again'); continue
            raise OMError(e.code, reason)
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError, ValueError) as e:
            # the connection dropped part-way (for example "UNEXPECTED_EOF_WHILE_READING"), timed out, or came back garbled
            if attempt < len(NET_RETRY_WAITS):
                WX_JOB['retries'] = WX_JOB.get('retries', 0) + 1
                _wait(NET_RETRY_WAITS[attempt], 'the connection to Open-Meteo dropped; trying again'); continue
            raise

# ---- everything Open-Meteo offers for one place, gathered hourly and daily.
# Requested in imperial units (F, mph, inches). Each group is asked for separately, and a variable the service does not
# offer for a period (history has fewer than the forecast) is remembered and skipped instead of breaking the update.
WX_CORE = ['temperature_2m', 'relative_humidity_2m', 'shortwave_radiation']
WX_HOURLY_GROUPS = [
    ('Air', ['temperature_2m', 'relative_humidity_2m', 'dew_point_2m', 'apparent_temperature', 'wet_bulb_temperature_2m', 'vapour_pressure_deficit',
             'temperature_80m', 'temperature_120m', 'temperature_180m']),
    ('Rain and snow', ['precipitation', 'rain', 'showers', 'snowfall', 'snow_depth', 'precipitation_probability']),
    ('Sky', ['weather_code', 'cloud_cover', 'cloud_cover_low', 'cloud_cover_mid', 'cloud_cover_high', 'visibility', 'is_day', 'sunshine_duration']),
    ('Sunlight', ['shortwave_radiation', 'direct_radiation', 'diffuse_radiation', 'direct_normal_irradiance', 'terrestrial_radiation', 'uv_index', 'uv_index_clear_sky']),
    ('Wind', ['wind_speed_10m', 'wind_speed_80m', 'wind_speed_120m', 'wind_speed_180m', 'wind_direction_10m', 'wind_direction_80m', 'wind_direction_120m',
              'wind_direction_180m', 'wind_gusts_10m']),
    ('Pressure and water loss', ['pressure_msl', 'surface_pressure', 'evapotranspiration', 'et0_fao_evapotranspiration']),
    ('Ground', ['soil_temperature_0cm', 'soil_temperature_6cm', 'soil_temperature_18cm', 'soil_temperature_54cm', 'soil_moisture_0_to_1cm',
                'soil_moisture_1_to_3cm', 'soil_moisture_3_to_9cm', 'soil_moisture_9_to_27cm', 'soil_moisture_27_to_81cm']),
    ('Upper atmosphere', ['total_column_integrated_water_vapour', 'freezing_level_height', 'cape', 'lifted_index', 'convective_inhibition', 'boundary_layer_height']),
]
WX_HOURLY = list(dict.fromkeys(v for _, vs in WX_HOURLY_GROUPS for v in vs))
WX_DAILY_GROUPS = [
    ('Temperature', ['temperature_2m_max', 'temperature_2m_min', 'temperature_2m_mean', 'apparent_temperature_max', 'apparent_temperature_min', 'apparent_temperature_mean',
                     'dew_point_2m_max', 'dew_point_2m_min', 'dew_point_2m_mean', 'wet_bulb_temperature_2m_max', 'wet_bulb_temperature_2m_min', 'wet_bulb_temperature_2m_mean']),
    ('Humidity', ['relative_humidity_2m_max', 'relative_humidity_2m_min', 'relative_humidity_2m_mean', 'vapour_pressure_deficit_max']),
    ('Sun', ['sunrise', 'sunset', 'daylight_duration', 'sunshine_duration', 'uv_index_max', 'uv_index_clear_sky_max', 'shortwave_radiation_sum',
             'cloud_cover_max', 'cloud_cover_min', 'cloud_cover_mean']),
    ('Rain and snow', ['weather_code', 'precipitation_sum', 'rain_sum', 'showers_sum', 'snowfall_sum', 'snowfall_water_equivalent_sum', 'precipitation_hours',
                       'precipitation_probability_max', 'precipitation_probability_min', 'precipitation_probability_mean']),
    ('Wind', ['wind_speed_10m_max', 'wind_speed_10m_min', 'wind_speed_10m_mean', 'wind_gusts_10m_max', 'wind_gusts_10m_min', 'wind_gusts_10m_mean', 'wind_direction_10m_dominant']),
    ('Pressure and water loss', ['pressure_msl_max', 'pressure_msl_min', 'pressure_msl_mean', 'surface_pressure_max', 'surface_pressure_min', 'surface_pressure_mean',
                                 'et0_fao_evapotranspiration', 'growing_degree_days_base_0_limit_50', 'leaf_wetness_probability_mean']),
    ('Other', ['visibility_max', 'visibility_min', 'visibility_mean', 'cape_max', 'cape_min', 'cape_mean']),
]
WX_DAILY = list(dict.fromkeys(v for _, vs in WX_DAILY_GROUPS for v in vs))
WX_GROUP_OF = {}
for _g, _vs in WX_HOURLY_GROUPS + WX_DAILY_GROUPS:
    for _v in _vs: WX_GROUP_OF.setdefault(_v, _g)
WX_LABELS = {'temperature_2m': 'Temperature', 'relative_humidity_2m': 'Humidity', 'shortwave_radiation': 'Solar radiation', 'dew_point_2m': 'Dew point',
             'apparent_temperature': 'Feels-like temperature', 'vapour_pressure_deficit': 'Air dryness (VPD)', 'precipitation': 'Precipitation',
             'precipitation_probability': 'Chance of precipitation', 'weather_code': 'Weather code', 'cloud_cover': 'Cloud cover',
             'sunshine_duration': 'Sunshine', 'uv_index': 'UV index', 'wind_speed_10m': 'Wind speed (10 m)', 'wind_gusts_10m': 'Wind gusts (10 m)',
             'wind_direction_10m': 'Wind direction (10 m)', 'pressure_msl': 'Pressure at sea level', 'surface_pressure': 'Pressure at the ground',
             'et0_fao_evapotranspiration': 'Water loss, reference crop (ET0)', 'evapotranspiration': 'Water loss, actual',
             'direct_normal_irradiance': 'Direct sun, facing the sun', 'cape': 'CAPE (storm energy)', 'snow_depth': 'Snow depth'}
WX_SUM = ('precipitation', 'rain', 'showers', 'snowfall', 'evapotranspiration', 'et0_fao_evapotranspiration', 'sunshine_duration')
WX_MAX = ('wind_gusts_10m', 'uv_index', 'precipitation_probability')
WX_SUFFIX = {'_max': 'highest', '_min': 'lowest', '_mean': 'average', '_sum': 'total', '_dominant': 'most common'}
def wx_label(v):
    if v in WX_LABELS: return WX_LABELS[v]
    for suf, word in WX_SUFFIX.items():
        if v.endswith(suf) and len(v) > len(suf) + 3:
            return f'{wx_label(v[:-len(suf)])}, {word}'
    s = v.replace('_', ' ').replace(' 2m', '').replace(' 10m', ' (10 m)').replace(' msl', ' at sea level')
    s = re.sub(r' (\d+)m$', r' at \1 m', s)
    s = re.sub(r' (\d+) to (\d+)cm$', r' \1 to \2 cm deep', s)
    s = re.sub(r' (\d+)cm$', r' at \1 cm deep', s)
    return s[:1].upper() + s[1:]
def wx_agg(v): return 'sum' if v in WX_SUM else 'max' if v in WX_MAX else 'avg'

WX_LOCK = threading.Lock()
WX_JOB = {'running': False}

def om_url(loc, kind, names, api, start=None, end=None, past_days=3, forecast_days=7):
    q = {'latitude': loc['lat'], 'longitude': loc['lon'], kind: ','.join(names), 'temperature_unit': 'fahrenheit', 'wind_speed_unit': 'mph',
         'precipitation_unit': 'inch', 'timeformat': 'unixtime', 'timezone': loc['tz']}
    if api == 'archive':
        q.update(start_date=start, end_date=end)
        return 'https://archive-api.open-meteo.com/v1/archive?' + urllib.parse.urlencode(q)
    q.update(past_days=past_days, forecast_days=forecast_days)
    return 'https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode(q)

def unsupported_get(c, api, kind):
    try: d = json.loads(setting(c, 'wx_unsupported', '{}') or '{}')
    except ValueError: d = {}
    if time.time() - d.get('_at', 0) > 14 * 86400: return set()        # try again every two weeks in case the service added them
    return set(d.get(f'{api}:{kind}', []))

def unsupported_add(c, api, kind, names):
    try: d = json.loads(setting(c, 'wx_unsupported', '{}') or '{}')
    except ValueError: d = {}
    if time.time() - d.get('_at', 0) > 14 * 86400: d = {'_at': int(time.time())}
    d.setdefault('_at', int(time.time()))
    d[f'{api}:{kind}'] = sorted(set(d.get(f'{api}:{kind}', [])) | set(names))
    set_setting(c, 'wx_unsupported', json.dumps(d))

def om_collect(c, loc, api, kind, names, **rng):
    """Ask for the variables in small groups. Returns ({unix: {variable: value}}, {variable: unit}, [variables not available])."""
    skip = unsupported_get(c, api, kind)
    want = [n for n in names if n not in skip]
    merged, units, missing = {}, {}, [n for n in names if n in skip]
    def take(data):
        blk = data.get(kind) or {}
        for i, t in enumerate(blk.get('time') or []):
            slot = merged.setdefault(int(t), {})
            for k, arr in blk.items():
                if k != 'time' and i < len(arr) and arr[i] is not None: slot[k] = arr[i]
        for k, u in (data.get(kind + '_units') or {}).items():
            if k != 'time': units[k] = u
    def ask(vs):
        WX_JOB['beat'] = time.time()                       # heartbeat for the progress display
        if WX_JOB.get('running'): WX_JOB['step'] = ('hourly' if kind == 'hourly' else 'daily') + ' values'
        try: return http_json(om_url(loc, kind, vs, api, **rng))
        except OMError as e:
            if e.code == 400: return e
            raise
    for i in range(0, len(want), 12):
        grp = want[i:i + 12]
        d = ask(grp)
        if not isinstance(d, OMError): take(d); time.sleep(0.2); continue
        for v in grp:                                   # something in this group is not offered: find out which
            d1 = ask([v])
            if isinstance(d1, OMError):
                if v not in d1.reason:                  # the complaint is not about this variable (bad dates, say): stop, do not blame it
                    raise d1
                missing.append(v); unsupported_add(c, api, kind, [v])
                if v in WX_CORE and kind == 'hourly': raise OMError(400, f'{v} is not available')
            else: take(d1)
            time.sleep(0.2)
    return merged, units, missing

def detail_years(c):
    try: return max(0, min(int(setting(c, 'wx_detail_years', '3')), 90))
    except (TypeError, ValueError): return 3
def rng_count(c, lo, hi, dev): return c.execute("SELECT COUNT(*) FROM readings WHERE source='weather' AND device=? AND ts>=? AND ts<=?", (dev, lo, hi)).fetchone()[0]
def wx_count(c, dev): return c.execute("SELECT COUNT(*) FROM readings WHERE source='weather' AND device=?", (dev,)).fetchone()[0]
def wxd_count(c, lid): return c.execute('SELECT COUNT(*) FROM weather_daily WHERE loc_id=?', (lid,)).fetchone()[0]

def store_hourly(c, merged, upto, dev='open-meteo'):
    n = 0
    for t in sorted(merged):
        if t > upto: continue
        d = merged[t]
        tmp, rh, sw = d.get('temperature_2m'), d.get('relative_humidity_2m'), d.get('shortwave_radiation')
        extra = {k: v for k, v in d.items() if k not in ('temperature_2m', 'relative_humidity_2m')}
        if tmp is None and rh is None and not extra: continue
        par = None if sw is None else round(sw * PAR_PER_WM2, 1)
        c.execute("""INSERT INTO readings(ts,source,device,temp_f,humidity,par,extra) VALUES(?,?,?,?,?,?,?)
                     ON CONFLICT(source,device,ts) DO UPDATE SET temp_f=COALESCE(excluded.temp_f,readings.temp_f), humidity=COALESCE(excluded.humidity,readings.humidity),
                       par=COALESCE(excluded.par,readings.par), extra=json_patch(COALESCE(readings.extra,'{}'),COALESCE(excluded.extra,'{}'))""",
                  (iso(t), 'weather', dev, tmp, rh, par, json.dumps(extra) if extra else None))
        n += 1
    return n

def store_daily(c, merged, tz, lid=1):
    n, today = 0, datetime.now(tz).date().isoformat()
    for t in sorted(merged):
        day = datetime.fromtimestamp(t, tz).date().isoformat()
        c.execute("""INSERT INTO weather_daily(loc_id,date,data,kind,updated_at) VALUES(?,?,?,?,?)
                     ON CONFLICT(loc_id,date) DO UPDATE SET data=json_patch(COALESCE(weather_daily.data,'{}'),excluded.data),
                       kind=excluded.kind, updated_at=excluded.updated_at""",
                  (lid, day, json.dumps(merged[t]), 'forecast' if day >= today else 'observed', now()))
        n += 1
    return n

def merge_units(c, units):
    if not units: return
    try: u = json.loads(setting(c, 'wx_units', '{}') or '{}')
    except ValueError: u = {}
    u.update(units); set_setting(c, 'wx_units', json.dumps(u))

def daily_forecast(rows, upto, tz):
    days = {}
    for t, tmp, rh, par in rows:
        if t <= upto or tmp is None: continue
        d = datetime.fromtimestamp(t, tz).date().isoformat()
        x = days.setdefault(d, {'date': d, 'temps': [], 'rh': [], 'par': 0.0})
        x['temps'].append(tmp)
        if rh is not None: x['rh'].append(rh)
        if par is not None: x['par'] += par * 3600 / 1e6
    out = []
    for d in sorted(days):
        x = days[d]
        out.append({'date': d, 'low': round(min(x['temps'])), 'high': round(max(x['temps'])),
                    'rh': round(sum(x['rh']) / len(x['rh'])) if x['rh'] else None, 'dli': round(x['par'], 1), 'hours': len(x['temps'])})
    return out

def log_run(c, trigger, kind, api, start, end, hourly_rows, hourly_new, daily_days, daily_new, vars_ok, vars_missing, ok, error, secs, note='', loc_id=1):
    c.execute('INSERT INTO weather_runs(ran_at,trigger,kind,api,range_start,range_end,hourly_rows,hourly_new,daily_days,daily_new,vars_ok,vars_missing,ok,error,seconds,note,loc_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (now(), trigger, kind, api, start, end, hourly_rows, hourly_new, daily_days, daily_new, vars_ok, json.dumps(vars_missing), 1 if ok else 0, error, round(secs, 1), note, loc_id))
    c.commit()

def year_chunks(start, end):
    a, out = datetime.strptime(start, '%Y-%m-%d').date(), []
    z = datetime.strptime(end, '%Y-%m-%d').date()
    while a <= z:
        b = min(datetime(a.year + 1, a.month, a.day).date() - timedelta(days=1) if not (a.month == 2 and a.day == 29) else datetime(a.year + 1, 2, 28).date(), z)
        out.append((a.isoformat(), b.isoformat())); a = b + timedelta(days=1)
    return out

def run_weather(trigger, backfill_start=None, progress=None, conn=None, loc_id=None):
    """One update. trigger: auto, auto-first, update-now or load-history. Logs what it fetched; never raises."""
    own = conn is None
    c = conn or sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    loc, ts_now = loc_get(c, loc_id) or location(c), int(time.time())
    tz, dev, lid = tzinfo(loc['tz']), loc['device'], loc['id']
    status = {'at': now(), 'ok': False, 'error': '', 'stored': 0}
    logged = {'history': False}
    prog = progress or (lambda *a, **k: None)
    try:
        with WX_LOCK:
            first = not c.execute("SELECT 1 FROM readings WHERE source='weather' AND device=? LIMIT 1", (dev,)).fetchone()
            total = 0
            if backfill_start:
                t0, end = time.time(), (datetime.now(timezone.utc) - timedelta(days=6)).date().isoformat()
                chunks = year_chunks(backfill_start, end) if backfill_start <= end else []
                h_rows = h_new = d_days = d_new = skipped = 0; ok_vars, miss, err = set(), set(), ''
                cutoff = (datetime.now(timezone.utc) - timedelta(days=365 * detail_years(c))).date().isoformat()
                for i, (a, b) in enumerate(chunks):
                    prog(i, len(chunks), f'{a} to {b}', hourly_saved=h_rows, daily_saved=d_days, skipped=skipped, phase='history')
                    detail = b >= cutoff                       # recent years keep every hourly measurement; older years keep the basics hourly and everything daily
                    days = (datetime.strptime(b, '%Y-%m-%d') - datetime.strptime(a, '%Y-%m-%d')).days + 1
                    lo, hi = iso(datetime.strptime(a, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() - 86400), iso(datetime.strptime(b, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() + 2 * 86400)
                    have = c.execute("SELECT COUNT(*) FROM readings WHERE source='weather' AND device=? AND ts>=? AND ts<=?" + (" AND extra IS NOT NULL" if detail else ""), (dev, lo, hi)).fetchone()[0]
                    dhave = c.execute('SELECT COUNT(*) FROM weather_daily WHERE loc_id=? AND date>=? AND date<=?', (lid, a, b)).fetchone()[0]
                    need_h, need_d = not (have > 0 and have >= days * 24 - 24), dhave < days - 1
                    if not need_h and not need_d:
                        skipped += 1; continue                    # this period already holds everything it should
                    try:
                        before, dbefore = rng_count(c, lo, hi, dev), wxd_count(c, lid)
                        if need_h:
                            m, u, ms = om_collect(c, loc, 'archive', 'hourly', WX_HOURLY if detail else WX_CORE, start=a, end=b)
                            merge_units(c, u); h_rows += store_hourly(c, m, ts_now, dev); ok_vars |= {k for d in m.values() for k in d}; miss |= set(ms)
                        if need_d:
                            m, u, ms = om_collect(c, loc, 'archive', 'daily', WX_DAILY, start=a, end=b)
                            merge_units(c, u); d_days += store_daily(c, m, tz, lid); miss |= {x + ' (daily)' for x in ms}
                        h_new += rng_count(c, lo, hi, dev) - before; d_new += wxd_count(c, lid) - dbefore
                        ds0 = loc_get(c, lid)['detail_since']
                        if detail and (not ds0 or a < ds0): loc_set(c, lid, detail_since=a)
                        c.commit()
                    except OMError as e:
                        err = f'Open-Meteo said no ({e}). ' + ('You have used up the free limit for now; press Load history again later and it carries on where it stopped.' if e.code == 429 else '')
                        break
                    except Exception as e:
                        err = (f'Could not reach Open-Meteo after 5 tries over about 3 minutes ({type(e).__name__}: {e}). '
                               'Everything fetched before this was saved; press Load history again to carry on from here.')[:400]; break
                prog(len(chunks), len(chunks), 'the last 3 months and the forecast', hourly_saved=h_rows, daily_saved=d_days, skipped=skipped, phase='recent')
                total += h_rows
                log_run(c, trigger, 'history', 'archive', backfill_start, end, h_rows, h_new, d_days, d_new, len(ok_vars), sorted(miss), not err, err, time.time() - t0,
                        f'{skipped} of {len(chunks)} year-long periods already held every measurement and were skipped.' if skipped else '', loc_id=lid)
                logged['history'] = bool(err)
                if err: raise RuntimeError(err)
            t0 = time.time()
            past = 92 if (first or backfill_start) else 3
            before, dbefore = wx_count(c, dev), wxd_count(c, lid)
            m, u, ms = om_collect(c, loc, 'forecast', 'hourly', WX_HOURLY, past_days=past, forecast_days=7)
            merge_units(c, u)
            rows = [(t, d.get('temperature_2m'), d.get('relative_humidity_2m'), None if d.get('shortwave_radiation') is None else round(d['shortwave_radiation'] * PAR_PER_WM2, 1)) for t, d in sorted(m.items())]
            n = store_hourly(c, m, ts_now, dev); total += n
            md, ud, msd = om_collect(c, loc, 'forecast', 'daily', WX_DAILY, past_days=past, forecast_days=7)
            merge_units(c, ud); dn = store_daily(c, md, tz, lid)
            loc_set(c, lid, forecast=json.dumps({'fetched_at': now(), 'days': daily_forecast(rows, ts_now, tz)}))
            ts_list = [t for t in m if t <= ts_now]
            if ts_list:
                d0 = datetime.fromtimestamp(min(ts_list), tz).date().isoformat()
                ds0 = loc_get(c, lid)['detail_since']
                if not ds0 or d0 < ds0: loc_set(c, lid, detail_since=d0)
            log_run(c, 'auto-first' if (first and trigger == 'auto') else trigger, 'recent', 'forecast',
                    datetime.fromtimestamp(min(ts_list), tz).date().isoformat() if ts_list else None, datetime.fromtimestamp(max(m), tz).date().isoformat() if m else None,
                    n, wx_count(c, dev) - before, dn, wxd_count(c, lid) - dbefore, len({k for d in m.values() for k in d}), sorted(set(ms) | {x + ' (daily)' for x in msd}), True, '', time.time() - t0, loc_id=lid)
            status.update(ok=True, stored=total)
    except Exception as e:                       # offline, blocked, API change: record it and carry on
        status['error'] = (str(e) if isinstance(e, RuntimeError) else f'{type(e).__name__}: {e}')[:400]
        if isinstance(e, (urllib.error.URLError, TimeoutError, OSError)) and not isinstance(e, OMError):
            status['error'] = ('Could not reach Open-Meteo after 5 tries over about 3 minutes. Check that this computer is online. Details: ' + status['error'])[:400]
        if not logged['history']:
            try: log_run(c, trigger, 'recent', 'forecast', None, None, 0, 0, 0, 0, 0, [], False, status['error'], 0, loc_id=lid)
            except Exception: pass
    status['place'] = loc['name']
    set_setting(c, 'weather_status', json.dumps(status))
    loc_set(c, lid, status=json.dumps(status))
    c.commit()
    WX_STATS.clear()
    if own: c.close()
    return status

def start_job(trigger, backfill_start=None, places=None):
    """places: list of (id, name). Several places are updated one after another."""
    if WX_JOB.get('running'): return False
    places = places or [(1, '')]
    WX_JOB.clear(); WX_JOB.update(running=True, trigger=trigger, started=now(), started_ts=time.time(), beat=time.time(), done=0, total=0, label='starting',
                                  start=backfill_start, hourly_saved=0, daily_saved=0, skipped=0, phase='history' if backfill_start else 'recent',
                                  place=places[0][1], place_id=places[0][0], places_total=len(places), place_no=1)
    def work():
        def prog(i, n, label, **kw): WX_JOB.update(done=i, total=n, label=label, beat=time.time(), **kw)
        errs = []
        for k, (pid, pname) in enumerate(places):
            WX_JOB.update(place=pname, place_id=pid, place_no=k + 1, done=0, total=0, hourly_saved=0, daily_saved=0, skipped=0)
            st = run_weather(trigger, backfill_start, prog, loc_id=pid)
            if not st['ok']: errs.append((pname + ': ' if len(places) > 1 else '') + st['error'])
        WX_JOB.update(running=False, finished=now(), ok=not errs, error=' | '.join(errs)[:600])
    threading.Thread(target=work, daemon=True).start()
    return True

def weather_loop():
    time.sleep(8)
    while True:
        try:
            c = sqlite3.connect(DB_PATH, timeout=30)
            try:
                c.row_factory = sqlite3.Row
                for r in c.execute('SELECT id FROM locations WHERE enabled=1 ORDER BY is_home DESC, id').fetchall():
                    if WX_JOB.get('running'): break        # a manual update or history load is busy; the next hour catches up
                    run_weather('auto', conn=c, loc_id=r['id'])
            finally: c.close()
        except Exception: pass
        time.sleep(3600)


def clean_reading(d, device_default='sensor'):
    """Validate one posted reading. Returns a dict ready to insert."""
    if not isinstance(d, dict): abort(400, 'each reading must be an object')
    out = {'device': re.sub(r'[^\w .\-@]', '', str(d.get('device') or device_default))[:40] or device_default}
    try: ts = parse_ts(d['ts']) if d.get('ts') else datetime.now(timezone.utc)
    except (ValueError, TypeError): abort(400, 'ts must look like 2026-10-19T18:30:00Z')
    if ts > datetime.now(timezone.utc) + timedelta(minutes=10): abort(400, 'ts is in the future')
    out['ts'] = ts.strftime('%Y-%m-%dT%H:%M:%SZ')
    conv = dict(d)
    if conv.get('temp_f') is None and conv.get('temp_c') is not None:
        try: conv['temp_f'] = float(conv['temp_c']) * 1.8 + 32
        except (TypeError, ValueError): abort(400, 'temp_c must be a number')
    if conv.get('soil_temp_f') is None and conv.get('soil_temp_c') is not None:
        try: conv['soil_temp_f'] = float(conv['soil_temp_c']) * 1.8 + 32
        except (TypeError, ValueError): abort(400, 'soil_temp_c must be a number')
    got = False
    for m in METRICS:
        v = conv.get(m)
        if v in (None, ''): out[m] = None; continue
        try: x = round(float(v), 2)
        except (TypeError, ValueError): abort(400, f'{m} must be a number')
        lo, hi = LIMITS[m]
        if not lo <= x <= hi: abort(400, f'{m} must be between {lo} and {hi}')
        out[m] = x; got = True
    if out['par'] is None and out['lux'] is not None: out['par'] = round(out['lux'] / LUX_PER_PAR, 1)
    if not got: abort(400, 'a reading needs at least one of: ' + ', '.join(METRICS))
    out['note'] = str(d.get('note') or '')[:200]
    return out

def insert_reading(c, source, r):
    c.execute('INSERT OR REPLACE INTO readings(ts,source,device,temp_f,humidity,par,lux,soil_moisture,soil_temp_f,soil_ph,note) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
              (r['ts'], source, r['device'], r['temp_f'], r['humidity'], r['par'], r['lux'], r['soil_moisture'], r['soil_temp_f'], r['soil_ph'], r.get('note')))

@app.route('/api/readings', methods=['POST'])
def post_readings():
    """Sensor ingest. Auth is the X-Ingest-Token header (checked in guard())."""
    c = db()
    body = request.get_json(silent=True)
    items = body.get('readings') if isinstance(body, dict) and 'readings' in body else (body if isinstance(body, list) else [body])
    if not items or items == [None]: abort(400, 'send a JSON reading or a list of readings')
    if len(items) > 500: abort(400, 'at most 500 readings per request')
    rows = [clean_reading(d) for d in items]
    for r in rows: insert_reading(c, 'sensor', r)
    c.commit()
    return jsonify(stored=len(rows)), 201

@app.route('/api/ingest')
def ingest_info():
    c = db()
    return jsonify(token=setting(c, 'ingest_token'), url=request.host_url.rstrip('/') + '/api/readings')

@app.route('/api/ingest/regenerate', methods=['POST'])
def ingest_regen():
    c = db()
    set_setting(c, 'ingest_token', secrets.token_urlsafe(18))
    audit_only(c, 'setting', 'ingest_token', None, None, editor(), 'Sensor token regenerated')
    c.commit()
    return jsonify(token=setting(c, 'ingest_token'))

def ts_filter(days):
    return iso(time.time() - days * 86400)

SERIES_BUCKETS = ('hour', 'day', 'week', 'month')

@app.route('/api/readings/series')
def readings_series():
    """Chart data, worked out by the database. Either days=N (back from now) or from/to (local dates, YYYY-MM-DD).
    vars=a,b,c adds any of the extra Open-Meteo measurements. The time step grows with the period: hours up to 10 days,
    days up to 3 years, weeks up to 15 years, months beyond that (or bucket=... to choose)."""
    c = db()
    source = request.args.get('source', 'weather')
    if source not in ('weather', 'sensor', 'manual', 'all'): abort(400, 'unknown source')
    device = request.args.get('device')
    loc = req_loc(c) if source == 'weather' else location(c); tz = tzinfo(loc['tz'])
    if source == 'weather': device = loc['device']
    fr, to = request.args.get('from'), request.args.get('to')
    if fr or to:
        lo, hi = local_bounds(c, fr, to, loc['tz'])
        if not lo:
            r = c.execute('SELECT MIN(ts) FROM readings' + ('' if source == 'all' else ' WHERE source=?') + (' AND device=?' if device and source != 'all' else ''),
                          ([] if source == 'all' else [source]) + ([device] if device and source != 'all' else [])).fetchone()
            lo = r[0] or iso(time.time() - 86400)
        hi = min(hi or iso(time.time() + 60), iso(time.time() + 60))
    else:
        try: days = max(1, min(int(request.args.get('days', 7)), 40000))
        except ValueError: abort(400, 'days must be a whole number')
        lo, hi = ts_filter(days), iso(time.time() + 60)
    span = (parse_ts(hi) - parse_ts(lo)).total_seconds() / 86400
    bucket = request.args.get('bucket')
    if bucket not in SERIES_BUCKETS:
        bucket = 'hour' if span <= 10 else 'day' if span <= 3 * 366 else 'week' if span <= 15 * 366 else 'month'
    off_h = round(parse_ts(lo).astimezone(tz).utcoffset().total_seconds() / 3600 + parse_ts(hi).astimezone(tz).utcoffset().total_seconds() / 3600) / 2
    off = f"{off_h:+.1f} hours"                      # local day boundaries (an hour out at most around a daylight-saving change)
    key = {'hour': 'substr(ts,1,13)', 'day': f"date(ts,'{off}')", 'week': f"date(ts,'{off}','-6 days','weekday 1')", 'month': f"strftime('%Y-%m-01',ts,'{off}')"}[bucket]
    names = [v for v in (request.args.get('vars') or request.args.get('var') or '').split(',') if v]
    names = list(dict.fromkeys(names))[:400]
    for v in names:
        if not re.match(r'^[a-z0-9_]{2,60}$', v): abort(400, 'unknown measurement')
    inner = ['ts', 'temp_f', 'humidity', 'par', 'lux', 'soil_moisture', 'soil_temp_f', 'soil_ph'] + [f"json_extract(extra,'$.{v}') AS x{i}" for i, v in enumerate(names)]
    sel = ['COUNT(*) AS n', 'AVG(temp_f) AS temp_f', 'MIN(temp_f) AS temp_min', 'MAX(temp_f) AS temp_max'] + \
          [f'AVG({m}) AS {m}' for m in METRICS if m != 'temp_f']
    for i, v in enumerate(names):
        fn = 'AVG' if bucket == 'hour' else {'sum': 'SUM', 'max': 'MAX'}.get(wx_agg(v), 'AVG')
        sel += [f'{fn}(x{i}) AS v{i}', f'COUNT(x{i}) AS n{i}']
    w, args = 'ts>=? AND ts<=?', [lo, hi]
    if source != 'all': w += ' AND source=?'; args.append(source)
    if device: w += ' AND device=?'; args.append(device)
    q = f"SELECT {key} AS k, {', '.join(sel)} FROM (SELECT {', '.join(inner)} FROM readings WHERE {w}) GROUP BY k ORDER BY k"
    rows = c.execute(q, args).fetchall()
    # Older years keep only daily summaries of the extra measurements: use them where there are no hourly values.
    daily = {}
    if names and bucket != 'hour' and source in ('weather', 'all'):
        dkey = {'day': 'date', 'week': "date(date,'-6 days','weekday 1')", 'month': "strftime('%Y-%m-01',date)"}[bucket]
        dlo, dhi = parse_ts(lo).astimezone(tz).date().isoformat(), parse_ts(hi).astimezone(tz).date().isoformat()
        exprs, which = [], []
        for v in names:
            agg = wx_agg(v)
            cand = [v] if v in WX_DAILY else [v + '_sum'] if agg == 'sum' else [v + '_max'] if agg == 'max' else [v + '_mean']
            dk = next((x for x in cand if x in WX_DAILY), None)
            if not dk: continue
            fn = {'sum': 'SUM', 'max': 'MAX'}.get(agg, 'AVG')
            if v in WX_DAILY: fn = 'SUM' if v.endswith('_sum') else 'MAX' if v.endswith('_max') else 'MIN' if v.endswith('_min') else 'AVG'
            exprs.append(f"{fn}(json_extract(data,'$.{dk}'))"); which.append(v)
        if exprs:                                        # one pass over the daily table for every measurement at once
            for r in c.execute(f"SELECT {dkey} AS k, {', '.join(exprs)} FROM weather_daily WHERE loc_id=? AND date>=? AND date<=? AND kind='observed' GROUP BY k", (loc['id'], dlo, dhi)):
                for v, val in zip(which, r[1:]):
                    if val is not None: daily.setdefault(r[0], {})[v] = val
    def t_of(k):
        if bucket == 'hour': return k + ':00:00Z'
        d = datetime.strptime(k, '%Y-%m-%d').replace(hour=12, tzinfo=tz)
        return d.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    pts, seen, used_daily = [], set(), set()
    for r in rows:
        seen.add(r['k'])
        p = {'t': t_of(r['k']), 'n': r['n']}
        for m in ('temp_f', 'temp_min', 'temp_max') + tuple(m for m in METRICS if m != 'temp_f'):
            p[m] = None if r[m] is None else round(r[m], 1)
        if names:
            p['x'] = {}
            for i, v in enumerate(names):
                val = r[f'v{i}'] if r[f'n{i}'] else None
                if val is None and v in daily.get(r['k'], {}): val = daily[r['k']][v]; used_daily.add(v)
                p['x'][v] = None if val is None else round(val, 2)
        pts.append(p)
    for k in sorted(set(daily) - seen):                 # days with daily summaries but no hourly rows at all
        pts.append({'t': t_of(k), 'n': 0, 'x': {v: (None if daily[k].get(v) is None else round(daily[k][v], 2)) for v in names}})
        used_daily |= set(daily[k])
    pts.sort(key=lambda p: p['t'])
    units = wx_units(c)
    meta = {v: {'label': wx_label(v), 'unit': units.get(v, ''), 'agg': wx_agg(v), 'group': WX_GROUP_OF.get(v, 'Other'), 'from_daily': v in used_daily} for v in names}
    devs = [r[0] for r in c.execute('SELECT DISTINCT device FROM readings WHERE source=? ORDER BY device', (source,))] if source not in ('all', 'weather') else []
    return jsonify(bucket=bucket, source=source, points=pts, devices=devs, tz=loc['tz'], vars=meta, start=lo, end=hi, place={'id': loc['id'], 'name': loc['name']} if source == 'weather' else None,
                   # old single-measurement form
                   **({'var': names[0], 'label': meta[names[0]]['label'], 'unit': meta[names[0]]['unit'], 'agg': meta[names[0]]['agg']} if len(names) == 1 else {}))

def integrate_dli(rows, tz):
    """mol/m2 so far today (local), from PAR readings. Each reading counts for the gap to the next one (max 1 hour)."""
    today = datetime.now(tz).date()
    pts = [(parse_ts(r['ts']), r['par']) for r in rows if r['par'] is not None]
    pts = [(t, p) for t, p in pts if t.astimezone(tz).date() == today]
    if not pts: return None
    tot = 0.0
    for i, (t, p) in enumerate(pts):
        nxt = pts[i + 1][0] if i + 1 < len(pts) else t + timedelta(hours=1)
        dt = min((nxt - t).total_seconds(), 3600)
        tot += p * dt / 1e6
    return round(tot, 1)

STALE_MIN = {'manual': 24 * 60, 'sensor': 90, 'weather': 180}
SOURCE_LABEL = {'manual': 'Typed in by you', 'sensor': 'Your sensor', 'weather': 'Online weather (Open-Meteo)'}

def resolve_current(c):
    mode = setting(c, 'current_mode', 'manual')
    if mode not in STALE_MIN: mode = 'manual'
    loc = location(c); tz = tzinfo(loc['tz'])
    out = {'mode': mode, 'label': SOURCE_LABEL[mode] + (f", {loc['name']}" if mode == 'weather' else ''), 'location': loc['name']}
    newest = None
    for m in ('temp_f', 'humidity', 'par', 'lux', 'soil_moisture', 'soil_temp_f', 'soil_ph'):
        if mode == 'weather' and m not in ('temp_f', 'humidity', 'par'):
            out[m] = None; continue                     # online weather never has these; searching for them would read every row
        if mode == 'weather':
            r = c.execute(f"SELECT ts,{m} FROM readings WHERE source='weather' AND device=? AND {m} IS NOT NULL AND ts<=? ORDER BY ts DESC LIMIT 1", (loc['device'], iso(time.time() + 300))).fetchone()
        else:
            r = c.execute(f'SELECT ts,{m} FROM readings WHERE source=? AND {m} IS NOT NULL AND ts<=? ORDER BY ts DESC LIMIT 1', (mode, iso(time.time() + 300))).fetchone()
        out[m] = r[1] if r else None
        if r and (newest is None or r[0] > newest): newest = r[0]
    out['as_of'] = newest
    out['age_minutes'] = int((time.time() - parse_ts(newest).timestamp()) / 60) if newest else None
    out['stale'] = newest is None or out['age_minutes'] > STALE_MIN[mode]
    out['vpd'] = vpd_kpa(out['temp_f'], out['humidity'])
    dev = None
    rows = c.execute('SELECT ts,par FROM readings WHERE source=? AND par IS NOT NULL AND ts>=?' + (' AND device=?' if mode == 'weather' else '') + ' ORDER BY ts',
                     (mode, iso(time.time() - 2 * 86400)) + ((loc['device'],) if mode == 'weather' else ())).fetchall()
    out['dli_today'] = integrate_dli(rows, tz) if mode != 'manual' else None
    return out

@app.route('/api/current', methods=['GET', 'PUT'])
def current():
    c = db()
    if request.method == 'PUT':
        b = request.get_json(silent=True) or {}
        mode = b.get('mode')
        if mode not in STALE_MIN: abort(400, 'mode must be manual, sensor or weather')
        set_setting(c, 'current_mode', mode)
        if mode == 'manual':
            vals = {k: b.get(k) for k in ('temp_f', 'humidity', 'par', 'lux')}
            if any(v not in (None, '') for v in vals.values()):
                r = clean_reading({**vals, 'device': 'typed in'})
                insert_reading(c, 'manual', r)
        c.commit()
    return jsonify(resolve_current(c))

WX_STATS = {}
def wx_stats(c, L=None):
    """Row counts over hundreds of thousands of rows: worked out once every couple of minutes per place, not on every page view."""
    L = L or location(c)
    key = L['device']
    hit = WX_STATS.get(key)
    if hit is None or time.time() - hit[0] > 120:
        hit = (time.time(), (tuple(c.execute("SELECT MIN(ts), MAX(ts), COUNT(*) FROM readings WHERE source='weather' AND device=?", (key,)).fetchone()),
                             tuple(c.execute("SELECT MIN(ts), MAX(ts), COUNT(*), COUNT(DISTINCT device) FROM readings WHERE source='sensor'").fetchone()),
                             tuple(c.execute('SELECT MIN(date), MAX(date), COUNT(*) FROM weather_daily WHERE loc_id=?', (L['id'],)).fetchone())))
        WX_STATS[key] = hit
    return hit[1]

def run_dict(r):
    d = dict(r)
    try: d['vars_missing'] = json.loads(d.get('vars_missing') or '[]')
    except ValueError: d['vars_missing'] = []
    d['ok'] = bool(d['ok'])
    return d

@app.route('/api/weather')
def weather_info():
    c = db()
    L = req_loc(c)
    fc, st = loc_json(c, L['id'], 'forecast'), loc_json(c, L['id'], 'status')
    first, sens, dd = wx_stats(c, L)
    q = lambda w: c.execute(f"SELECT * FROM weather_runs WHERE loc_id=? AND {w} ORDER BY id DESC LIMIT 1", (L['id'],)).fetchone()
    last_hist, last_ok_hist = q("kind='history'"), q("kind='history' AND ok=1 AND hourly_rows>0")
    last_auto, last_any = q("trigger IN ('auto','auto-first')"), q("kind!='earlier'")
    earlier = c.execute("SELECT * FROM weather_runs WHERE loc_id=? AND kind='earlier' ORDER BY id LIMIT 1", (L['id'],)).fetchone()
    return jsonify(location=L, places=places_list(c), forecast=fc, status=st, enabled=L['enabled'], home=location(c),
                   weather={'first': first[0], 'last': first[1], 'count': first[2], 'detail_since': L['detail_since'], 'detail_years': detail_years(c)},
                   daily={'first': dd[0], 'last': dd[1], 'count': dd[2]},
                   sensor={'first': sens[0], 'last': sens[1], 'count': sens[2], 'devices': sens[3]},
                   runs={'history': run_dict(last_hist) if last_hist else None, 'history_ok': run_dict(last_ok_hist) if last_ok_hist else None,
                         'auto': run_dict(last_auto) if last_auto else None, 'any': run_dict(last_any) if last_any else None,
                         'earlier': run_dict(earlier) if earlier else None},
                   db_mb=round(os.path.getsize(DB_PATH) / 1048576, 1), job={**WX_JOB, 'now_ts': time.time()}, background=os.environ.get('PLANTDB_WEATHER', '1') == '1')

@app.route('/api/weather/job')
def weather_job():
    return jsonify({**WX_JOB, 'now_ts': time.time()})

@app.route('/api/weather/runs')
def weather_runs():
    c = db()
    n = max(1, min(int(request.args.get('n', 100)), 1000))
    kind = request.args.get('kind')
    q, a = 'SELECT * FROM weather_runs WHERE loc_id=?', [req_loc(c)['id']]
    if kind in ('history', 'recent', 'earlier'): q += ' AND kind=?'; a.append(kind)
    rows = c.execute(q + ' ORDER BY id DESC LIMIT ?', a + [n]).fetchall()
    return jsonify([run_dict(r) for r in rows],)

def clean_place(b, old=None):
    old = old or {}
    try: lat, lon = float(b.get('lat', old.get('lat'))), float(b.get('lon', old.get('lon')))
    except (TypeError, ValueError): abort(400, 'Latitude and longitude must be numbers')
    if not (-90 <= lat <= 90 and -180 <= lon <= 180): abort(400, 'Latitude is -90 to 90 and longitude is -180 to 180')
    tz = str(b.get('tz', old.get('tz')) or '').strip()
    try:
        from zoneinfo import ZoneInfo; ZoneInfo(tz)
    except Exception: abort(400, 'Unknown time zone. Use a name like America/Chicago')
    name = str(b.get('name', old.get('name')) or '').strip()[:60]
    if not name: abort(400, 'Give the place a name')
    return {'name': name, 'lat': round(lat, 4), 'lon': round(lon, 4), 'tz': tz}

def places_list(c):
    out = []
    for r in c.execute('SELECT * FROM locations ORDER BY is_home DESC, name').fetchall():
        d = loc_dict(r)
        first, _, dd = wx_stats(c, d)
        try: st = json.loads(r['status'] or '{}')
        except ValueError: st = {}
        d.update(first=first[0], last=first[1], count=first[2], daily_first=dd[0], daily_count=dd[2], last_update=st.get('at'), last_ok=st.get('ok'), last_error=st.get('error'))
        out.append(d)
    return out

@app.route('/api/places', methods=['GET', 'POST'])
def places():
    c = db()
    if request.method == 'GET': return jsonify(places_list(c))
    b = request.get_json(silent=True) or {}
    P = clean_place(b)
    dup = c.execute('SELECT name FROM locations WHERE ABS(lat-?)<0.01 AND ABS(lon-?)<0.01', (P['lat'], P['lon'])).fetchone()
    if dup and not b.get('force'): abort(409, f'"{dup[0]}" is already at that spot')
    cur = c.execute('INSERT INTO locations(name,lat,lon,tz,enabled,is_home,created_at) VALUES(?,?,?,?,1,0,?)', (P['name'], P['lat'], P['lon'], P['tz'], now()))
    pid = cur.lastrowid
    c.execute('UPDATE locations SET device=? WHERE id=?', (f'place-{pid}', pid))
    audit_only(c, 'setting', 'weather_place', None, json.dumps(P), editor(), f'Weather place added: {P["name"]}')
    c.commit()
    started = start_job('auto-first', None, [(pid, P['name'])])          # fetch its last 3 months and forecast straight away
    return jsonify(place=loc_get(c, pid), started=started), 201

@app.route('/api/places/<int:pid>', methods=['PUT', 'DELETE'])
def place_one(pid):
    c = db()
    L = loc_get(c, pid)
    if L is None: abort(404, 'That place does not exist')
    if request.method == 'DELETE':
        if L['is_home']: abort(400, 'This is the home place your plants use. Make another place home first.')
        if WX_JOB.get('running') and WX_JOB.get('place_id') == pid: abort(409, 'This place is being updated right now. Try again when it finishes.')
        n = c.execute("DELETE FROM readings WHERE source='weather' AND device=?", (L['device'],)).rowcount
        c.execute('DELETE FROM weather_daily WHERE loc_id=?', (pid,))
        c.execute('DELETE FROM weather_runs WHERE loc_id=?', (pid,))
        c.execute('DELETE FROM locations WHERE id=?', (pid,))
        audit_only(c, 'setting', 'weather_place', json.dumps({k: L[k] for k in ('name', 'lat', 'lon', 'tz')}), None, editor(), f'Weather place removed with {n} hourly readings: {L["name"]}')
        c.commit(); WX_STATS.pop(L['device'], None)
        return jsonify(ok=True, removed_readings=n)
    b = request.get_json(silent=True) or {}
    P = clean_place(b, L)
    moved = abs(P['lat'] - L['lat']) > 0.0001 or abs(P['lon'] - L['lon']) > 0.0001
    c.execute('UPDATE locations SET name=?,lat=?,lon=?,tz=? WHERE id=?', (P['name'], P['lat'], P['lon'], P['tz'], pid))
    if 'enabled' in b: c.execute('UPDATE locations SET enabled=? WHERE id=?', (1 if b['enabled'] else 0, pid))
    if b.get('is_home'):
        c.execute('UPDATE locations SET is_home=CASE WHEN id=? THEN 1 ELSE 0 END', (pid,))
    if 'detail_years' in b and b['detail_years'] not in (None, ''):
        try: dy = int(b['detail_years'])
        except (TypeError, ValueError): abort(400, 'Years of detail must be a whole number')
        if not 0 <= dy <= 90: abort(400, 'Years of detail must be between 0 and 90')
        set_setting(c, 'wx_detail_years', str(dy))
    audit_only(c, 'setting', 'weather_place', json.dumps({k: L[k] for k in ('name', 'lat', 'lon', 'tz', 'enabled', 'is_home')}),
               json.dumps({**P, 'enabled': b.get('enabled', L['enabled']), 'is_home': bool(b.get('is_home')) or L['is_home']}), editor(), f'Weather place changed: {P["name"]}')
    c.commit()
    return jsonify(place=loc_get(c, pid), moved=moved)

@app.route('/api/places/search')
def place_search():
    """Find a town by name with Open-Meteo's free place search (no account needed)."""
    q = (request.args.get('q') or '').strip()
    if len(q) < 2: abort(400, 'Type at least 2 letters')
    url = 'https://geocoding-api.open-meteo.com/v1/search?' + urllib.parse.urlencode({'name': q, 'count': 10, 'language': 'en', 'format': 'json'})
    try: data = http_json(url, tries=1)
    except Exception as e:
        abort(502, f'The place search could not be reached ({type(e).__name__}). You can still type the latitude, longitude and time zone yourself.')
    out = []
    for r in data.get('results') or []:
        label = ', '.join(x for x in (r.get('name'), r.get('admin1'), r.get('country')) if x)
        out.append({'label': label, 'name': ', '.join(x for x in (r.get('name'), r.get('admin1_code') or r.get('admin1')) if x) if r.get('country_code') == 'US' else ', '.join(x for x in (r.get('name'), r.get('country')) if x),
                    'lat': r.get('latitude'), 'lon': r.get('longitude'), 'tz': r.get('timezone'), 'elevation_m': r.get('elevation'), 'population': r.get('population')})
    return jsonify(out)

@app.route('/api/weather/settings', methods=['PUT'])
def weather_settings():
    """Older form of PUT /api/places/<id> for the home place (or ?loc=)."""
    c = db()
    L = req_loc(c)
    return place_one(L['id'])

@app.route('/api/weather/refresh', methods=['POST'])
def weather_refresh():
    """Starts an update in the background (a long history load takes minutes) and returns at once. Poll /api/weather/job."""
    b = request.get_json(silent=True) or {}
    start = b.get('backfill_start')
    if start:
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(start)): abort(400, 'Start date must look like 2025-10-01')
        try: datetime.strptime(start, '%Y-%m-%d')
        except ValueError: abort(400, 'That date does not exist')
        if start < '1940-01-01': abort(400, 'Open-Meteo history starts in 1940')
    c = db()
    which = b.get('loc')
    if which == 'all':
        pl = [(r['id'], r['name']) for r in c.execute('SELECT id,name FROM locations WHERE enabled=1 ORDER BY is_home DESC, name')] or [(location(c)['id'], location(c)['name'])]
    else:
        L = loc_get(c, which)
        if L is None: abort(404, 'That place does not exist')
        pl = [(L['id'], L['name'])]
    started = start_job('load-history' if start else 'update-now', start or None, pl)
    return jsonify(started=started, job={**WX_JOB, 'now_ts': time.time()}), (202 if started else 409)

# ---- the table of everything logged
SENSOR_COLS = [('temp_f', 'Temperature', '°F'), ('humidity', 'Humidity', '%'), ('par', 'PAR', 'µmol/m²/s'), ('lux', 'Light', 'lux'),
               ('soil_moisture', 'Soil moisture', '%'), ('soil_temp_f', 'Soil temperature', '°F'), ('soil_ph', 'Soil pH', ''), ('note', 'Note', '')]

def wx_units(c):
    try: u = json.loads(setting(c, 'wx_units', '{}') or '{}')
    except ValueError: u = {}
    return u

def table_columns(c, kind, source):
    if source == 'sensor':
        return [{'key': k, 'label': l, 'unit': u, 'group': 'Sensor'} for k, l, u in SENSOR_COLS]
    units = wx_units(c)
    names = WX_HOURLY if kind == 'hourly' else WX_DAILY
    have = set(units)                     # every measurement ever received has its unit recorded, so no table scan is needed
    cols = []
    if kind == 'hourly':
        cols += [{'key': 'temperature_2m', 'label': wx_label('temperature_2m'), 'unit': units.get('temperature_2m', '°F'), 'group': 'Air'},
                 {'key': 'relative_humidity_2m', 'label': wx_label('relative_humidity_2m'), 'unit': units.get('relative_humidity_2m', '%'), 'group': 'Air'},
                 {'key': 'par', 'label': 'PAR (plant light)', 'unit': 'µmol/m²/s', 'group': 'Sunlight'}]
    for n in names:
        if n in ('temperature_2m', 'relative_humidity_2m') and kind == 'hourly': continue
        if n in have or n in units:
            cols.append({'key': n, 'label': wx_label(n), 'unit': units.get(n, ''), 'group': WX_GROUP_OF.get(n, 'Other')})
    return cols

def local_bounds(c, a, b, tzname=None):
    tz = tzinfo(tzname or location(c)['tz'])
    lo = hi = None
    if a:
        try: lo = iso(datetime.strptime(a, '%Y-%m-%d').replace(tzinfo=tz).timestamp())
        except ValueError: abort(400, 'From date must look like 2026-10-01')
    if b:
        try: hi = iso(datetime.strptime(b, '%Y-%m-%d').replace(tzinfo=tz).timestamp() + 86400 - 1)
        except ValueError: abort(400, 'To date must look like 2026-10-31')
    return lo, hi

def table_query(c, args):
    kind = 'daily' if args.get('kind') == 'daily' else 'hourly'
    g.wx_place = loc_get(c, args.get('loc'))
    if g.wx_place is None: abort(404, 'That place does not exist')
    source = 'sensor' if args.get('source') == 'sensor' else 'weather'
    if source == 'sensor': kind = 'hourly'
    order = 'ASC' if args.get('order') == 'asc' else 'DESC'
    a, b = args.get('from'), args.get('to')
    return kind, source, order, a, b

def table_rows(c, kind, source, order, a, b, limit=None, offset=0):
    L = getattr(g, 'wx_place', None) or location(c)
    tz = tzinfo(L['tz'] if source == 'weather' else location(c)['tz'])
    if kind == 'daily':
        w, ar = ['loc_id=?'], [L['id']]
        if a: w.append('date>=?'); ar.append(a)
        if b: w.append('date<=?'); ar.append(b)
        wh = ' WHERE ' + ' AND '.join(w) if w else ''
        total = c.execute('SELECT COUNT(*) FROM weather_daily' + wh, ar).fetchone()[0]
        q = f'SELECT date,data,kind FROM weather_daily{wh} ORDER BY date {order}' + (' LIMIT ? OFFSET ?' if limit else '')
        rs = c.execute(q, ar + ([limit, offset] if limit else [])).fetchall()
        return total, ({'when': r['date'], 'kind': r['kind'], **json.loads(r['data'])} for r in rs)
    lo, hi = local_bounds(c, a, b, L['tz'] if source == 'weather' else None)
    w, ar = ['source=?', 'ts<=?'], [source, iso(time.time() + 7200)]
    if source == 'weather': w.append('device=?'); ar.append(L['device'])
    if lo: w.append('ts>=?'); ar.append(lo)
    if hi: w.append('ts<=?'); ar.append(hi)
    wh = ' WHERE ' + ' AND '.join(w)
    total = c.execute('SELECT COUNT(*) FROM readings' + wh, ar).fetchone()[0]
    q = f'SELECT * FROM readings{wh} ORDER BY ts {order}' + (', device' if source == 'sensor' else '') + (' LIMIT ? OFFSET ?' if limit else '')
    if limit and source == 'weather':        # walk the (source, ts) index for the page, then fetch only those rows
        q = f'SELECT * FROM readings WHERE id IN (SELECT id FROM readings INDEXED BY readings_uq{wh} ORDER BY ts {order} LIMIT ? OFFSET ?) ORDER BY ts {order}'
    rs = c.execute(q, ar + ([limit, offset] if limit else [])).fetchall()
    def conv(r):
        when = parse_ts(r['ts']).astimezone(tz).strftime('%Y-%m-%d %H:%M')
        if source == 'sensor':
            return {'when': when, 'device': r['device'], **{k: r[k] for k, _, _ in SENSOR_COLS}}
        d = json.loads(r['extra']) if r['extra'] else {}
        return {'when': when, 'temperature_2m': r['temp_f'], 'relative_humidity_2m': r['humidity'], 'par': r['par'], **d}
    return total, (conv(r) for r in rs)

@app.route('/api/weather/table')
def weather_table():
    c = db()
    kind, source, order, a, b = table_query(c, request.args)
    try: per, page = max(10, min(int(request.args.get('per', 50)), 1000)), max(1, int(request.args.get('page', 1)))
    except ValueError: abort(400, 'page and per must be whole numbers')
    total, rows = table_rows(c, kind, source, order, a, b, per, (page - 1) * per)
    if total and (page - 1) * per >= total:                  # past the end: show the last page instead of an empty one
        page = -(-total // per)
        total, rows = table_rows(c, kind, source, order, a, b, per, (page - 1) * per)
    return jsonify(kind=kind, source=source, columns=table_columns(c, kind, source), rows=list(rows), total=total, page=page, per=per,
                   pages=max(1, -(-total // per)), tz=(g.wx_place if source == 'weather' else location(c))['tz'], place=g.wx_place)

@app.route('/api/weather/table.csv')
def weather_table_csv():
    c = db()
    kind, source, order, a, b = table_query(c, request.args)
    cols = table_columns(c, kind, source)
    total, rows = table_rows(c, kind, source, order, a, b)
    head = ['date' if kind == 'daily' else 'local_time'] + (['device'] if source == 'sensor' else []) + (['kind'] if kind == 'daily' else []) + \
           [k['key'] + (f" ({k['unit']})" if k['unit'] else '') for k in cols]
    def gen():
        buf = io.StringIO(); w = csv.writer(buf)
        w.writerow(head); yield buf.getvalue(); buf.seek(0); buf.truncate()
        for i, r in enumerate(rows):
            w.writerow([r['when']] + ([r.get('device')] if source == 'sensor' else []) + ([r.get('kind')] if kind == 'daily' else []) + [r.get(k['key']) for k in cols])
            if i % 500 == 499: yield buf.getvalue(); buf.seek(0); buf.truncate()
        yield buf.getvalue()
    slug = re.sub(r'[^A-Za-z0-9]+', '-', g.wx_place['name']).strip('-').lower()[:30] or 'place'
    name = f"{'sensor' if source == 'sensor' else 'weather-' + slug + '-' + kind}-readings-{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(gen(), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename={name}'})

@app.route('/api/weather/catalog')
def weather_catalog():
    """Every measurement we ask Open-Meteo for, its group and unit, and whether it has actually arrived."""
    c = db()
    units = wx_units(c)
    try: un = json.loads(setting(c, 'wx_unsupported', '{}') or '{}')
    except ValueError: un = {}
    out = []
    for kind, groups in (('hourly', WX_HOURLY_GROUPS), ('daily', WX_DAILY_GROUPS)):
        for g, vs in groups:
            for v in vs:
                out.append({'kind': kind, 'group': g, 'key': v, 'label': wx_label(v), 'unit': units.get(v, ''),
                            'history_missing': v in (un.get('archive:' + kind) or []), 'recent_missing': v in (un.get('forecast:' + kind) or [])})
    return jsonify(out)

@app.route('/api/weather/monthly')
def weather_monthly():
    """Observed monthly summary: average daily low/high, humidity, daily light, freezing nights."""
    c = db()
    source = request.args.get('source', 'weather')
    loc = req_loc(c) if source == 'weather' else location(c); tz = tzinfo(loc['tz'])
    since = request.args.get('from')                      # a month like 2025-09; the default is the last 14 months
    if not since or not re.match(r'^\d{4}-\d{2}$', since):
        d = datetime.now(tz).date().replace(day=1)
        for _ in range(14): d = (d - timedelta(days=1)).replace(day=1)
        since = d.strftime('%Y-%m')
    rows = c.execute('SELECT ts,temp_f,humidity,par FROM readings WHERE source=? AND ts>=?' + (' AND device=?' if source == 'weather' else '') + ' ORDER BY ts',
                     (source, since + '-01T00:00:00Z') + ((loc['device'],) if source == 'weather' else ())).fetchall()
    days = {}
    for r in rows:
        d = parse_ts(r['ts']).astimezone(tz).date().isoformat()
        x = days.setdefault(d, {'t': [], 'h': [], 'par': []})
        if r['temp_f'] is not None: x['t'].append(r['temp_f'])
        if r['humidity'] is not None: x['h'].append(r['humidity'])
        if r['par'] is not None: x['par'].append(r['par'])
    months = {}
    for d, x in days.items():
        if len(x['t']) < 12: continue                    # skip partial days
        m = months.setdefault(d[:7], {'lows': [], 'highs': [], 'rh': [], 'dli': [], 'freeze': 0, 'days': 0})
        m['lows'].append(min(x['t'])); m['highs'].append(max(x['t'])); m['days'] += 1
        if min(x['t']) <= 32: m['freeze'] += 1
        if x['h']: m['rh'].append(sum(x['h']) / len(x['h']))
        if len(x['par']) >= 12: m['dli'].append(sum(x['par']) * 3600 / len(x['par']) * 24 / 1e6)
    avg = lambda v: round(sum(v) / len(v), 1) if v else None
    return jsonify([{'month': k, 'days': m['days'], 'low': avg(m['lows']), 'high': avg(m['highs']), 'rh': avg(m['rh']),
                     'dli': avg(m['dli']), 'freeze_nights': m['freeze']} for k, m in sorted(months.items())])

# ---------------------------------------------------------------- fertilizer log
FERT_FORMS = ['liquid', 'powder', 'granular', 'slow-release', 'spikes', 'organic liquid', 'organic solid', 'foliar spray', 'other']
FERT_METHODS = ['water in', 'foliar spray', 'top-dress', 'mixed into soil', 'spike', 'other']
AMOUNT_UNITS = ['g', 'oz', 'ml', 'fl oz', 'tsp', 'tbsp']
WATER_UNITS = ['L', 'gal', 'qt', 'cup']
WATER_L = {'L': 1.0, 'gal': 3.78541, 'qt': 0.946353, 'cup': 0.236588}

def fert_calc(form, n, p, k, amount, unit, water, wunit):
    """Estimate how much nutrient went in. Dry spoon measures are taken as 4 g per tsp and 12 g per tbsp,
    liquid measures as 1 g per ml (liquid fertilizers are about 1.0 to 1.2). Treat results as estimates."""
    out = {'ppm_n': None, 'ppm_p2o5': None, 'ppm_k2o': None, 'n_grams': None}
    if not amount or not unit: return out
    liquid = form in ('liquid', 'organic liquid', 'foliar spray')
    if unit == 'g': g = amount
    elif unit == 'oz': g = amount * 28.3495
    elif unit == 'ml': g = amount
    elif unit == 'fl oz': g = amount * 29.5735
    elif unit == 'tsp': g = amount * (4.92892 if liquid else 4.0)
    elif unit == 'tbsp': g = amount * (14.7868 if liquid else 12.0)
    else: return out
    if n is not None: out['n_grams'] = round(g * n / 100, 3)
    L = water * WATER_L[wunit] if water and wunit in WATER_L else None
    if L:
        for key, pct in (('ppm_n', n), ('ppm_p2o5', p), ('ppm_k2o', k)):
            if pct is not None: out[key] = round(g * pct / 100 * 1000 / L, 1)
    return out

def _num(b, key, lo, hi, label, required=False):
    v = b.get(key)
    if v in (None, ''):
        if required: abort(400, f'{label} is required')
        return None
    try: x = round(float(v), 3)
    except (TypeError, ValueError): abort(400, f'{label} must be a number')
    if not lo <= x <= hi: abort(400, f'{label} must be between {lo} and {hi}')
    return x

def local_today(c):
    return datetime.now(tzinfo(location(c)['tz'])).date()

def fert_fields(c, b):
    product = re.sub(r'\s+', ' ', str(b.get('product', ''))).strip()[:80]
    if not product: abort(400, 'Type the fertilizer name')
    day = str(b.get('applied_on', '')).strip()
    try: d = datetime.strptime(day, '%Y-%m-%d').date()
    except ValueError: abort(400, 'Date must look like 2026-10-20')
    if d < datetime(2000, 1, 1).date() or d > local_today(c) + timedelta(days=1): abort(400, 'Date cannot be in the future')
    form = str(b.get('form') or 'liquid')
    if form not in FERT_FORMS: abort(400, 'Form must be one of: ' + ', '.join(FERT_FORMS))
    method = str(b.get('method') or 'water in')
    if method not in FERT_METHODS: abort(400, 'Method must be one of: ' + ', '.join(FERT_METHODS))
    n, p, k = (_num(b, x, 0, 100, lab) for x, lab in (('n', 'Nitrogen (N) %'), ('p', 'Phosphate (P) %'), ('k', 'Potash (K) %')))
    amount = _num(b, 'amount', 0, 100000, 'Amount')
    unit = b.get('amount_unit') or None
    if amount is not None and unit not in AMOUNT_UNITS: abort(400, 'Amount unit must be one of: ' + ', '.join(AMOUNT_UNITS))
    if amount is None: unit = None
    water = _num(b, 'water_amount', 0, 100000, 'Water amount')
    wunit = b.get('water_unit') or None
    if water is not None and wunit not in WATER_UNITS: abort(400, 'Water unit must be one of: ' + ', '.join(WATER_UNITS))
    if water is None: wunit = None
    calc = fert_calc(form, n, p, k, amount, unit, water, wunit)
    return dict(applied_on=day, product=product, form=form, n=n, p=p, k=k, amount=amount, amount_unit=unit, water_amount=water,
                water_unit=wunit, method=method, note=str(b.get('note', '')).strip()[:500], **calc)

FERT_COLS = ['applied_on', 'product', 'form', 'n', 'p', 'k', 'amount', 'amount_unit', 'water_amount', 'water_unit', 'method',
             'ppm_n', 'ppm_p2o5', 'ppm_k2o', 'n_grams', 'note']

def fert_text(f):
    npk = '-'.join('?' if f[x] is None else ('%g' % f[x]) for x in 'npk')
    dose = ''
    if f['amount'] is not None: dose = ', %g %s' % (f['amount'], f['amount_unit']) + (' per %g %s water' % (f['water_amount'], f['water_unit']) if f['water_amount'] else '')
    ppm = ', about %g ppm N' % f['ppm_n'] if f['ppm_n'] is not None else ''
    return f"{f['product']} ({npk}) on {f['applied_on']}, {f['method']}{dose}{ppm}" + (f". {f['note']}" if f['note'] else '')

def fert_summary(f):
    npk = '-'.join('?' if f[x] is None else ('%g' % f[x]) for x in 'npk')
    return f"{f['product']} ({npk}) on {f['applied_on']}"

@app.route('/api/fertilizer', methods=['GET', 'POST'])
def fertilizer():
    c = db()
    if request.method == 'GET':
        q, a = 'SELECT * FROM fertilizer_log WHERE 1=1', []
        for key, col, op in (('plant', 'plant_code', '='), ('from', 'applied_on', '>='), ('to', 'applied_on', '<=')):
            if request.args.get(key): q += f' AND {col}{op}?'; a.append(request.args[key])
        rows = c.execute(q + ' ORDER BY applied_on DESC, id DESC LIMIT 5000', a).fetchall()
        return jsonify([dict(r) for r in rows])
    b = request.get_json(silent=True) or {}
    codes = b.get('plants') or ([b['plant']] if b.get('plant') else [])
    if not isinstance(codes, list) or not codes: abort(400, 'Choose at least one plant')
    codes = list(dict.fromkeys(str(x) for x in codes))[:200]
    for code in codes: plant_row(c, code)
    f = fert_fields(c, b)
    who, bid = editor(), secrets.token_hex(6)
    ids = []
    for code in codes:
        cur = c.execute(f'INSERT INTO fertilizer_log(plant_code,{",".join(FERT_COLS)},batch_id,created_by,created_at) VALUES(?,{",".join("?" * len(FERT_COLS))},?,?,?)',
                        [code] + [f[x] for x in FERT_COLS] + [bid, who, now()])
        ids.append(cur.lastrowid)
        r = plant_row(c, code)
        audit_only(c, 'fertilizer', 'fertilizer_log', None, fert_text(f), who, 'Fertilized: ' + fert_summary(f), r['id'], code)
    c.commit()
    return jsonify(ids=ids, **{x: f[x] for x in ('ppm_n', 'ppm_p2o5', 'ppm_k2o', 'n_grams')}), 201

@app.route('/api/fertilizer/<int:i>', methods=['PUT', 'DELETE'])
def fertilizer_one(i):
    c = db()
    old = c.execute('SELECT * FROM fertilizer_log WHERE id=?', (i,)).fetchone()
    if not old: abort(404, 'entry not found')
    r = plant_row(c, old['plant_code']) if c.execute('SELECT 1 FROM plants WHERE code=?', (old['plant_code'],)).fetchone() else None
    who = editor()
    oldj = fert_text(old)
    if request.method == 'DELETE':
        c.execute('DELETE FROM fertilizer_log WHERE id=?', (i,))
        audit_only(c, 'fertilizer', 'fertilizer_log', oldj, None, who, 'Removed fertilizer entry: ' + fert_summary(old), r['id'] if r else None, old['plant_code'])
        c.commit()
        return jsonify(ok=True)
    f = fert_fields(c, request.get_json(silent=True) or {})
    c.execute(f'UPDATE fertilizer_log SET {",".join(x + "=?" for x in FERT_COLS)},updated_by=?,updated_at=? WHERE id=?', [f[x] for x in FERT_COLS] + [who, now(), i])
    audit_only(c, 'fertilizer', 'fertilizer_log', oldj, fert_text(f), who, 'Changed fertilizer entry: ' + fert_summary(f), r['id'] if r else None, old['plant_code'])
    c.commit()
    return jsonify(ok=True, **{x: f[x] for x in ('ppm_n', 'ppm_p2o5', 'ppm_k2o', 'n_grams')})

@app.route('/api/fertilizer/products')
def fertilizer_products():
    """Fertilizers used before, newest first, with the values from the last time so the form can be pre-filled."""
    c = db()
    seen, out = set(), []
    for r in c.execute('SELECT * FROM fertilizer_log ORDER BY applied_on DESC, id DESC'):
        key = r['product'].lower()
        if key in seen: continue
        seen.add(key)
        out.append({x: r[x] for x in ['product', 'form', 'n', 'p', 'k', 'amount', 'amount_unit', 'water_amount', 'water_unit', 'method']})
    return jsonify(out)

# ---------------------------------------------------------------- past days: what the values were, and what the ranges were then
HIST = {  # metric -> (column, low field, high field, unit, label)
    'temp': ('temp_f', 'temp_ideal_low', 'temp_ideal_high', '°F', 'Temperature'),
    'humidity': ('humidity', 'humidity_low', 'humidity_high', '%', 'Humidity'),
    'vpd': (None, 'vpd_low', 'vpd_high', ' kPa', 'Air dryness (VPD)'),
    'light': ('par', 'par_low', 'par_high', ' PAR', 'Light'),
    'soil_moisture': ('soil_moisture', 'soil_moisture_low', 'soil_moisture_high', '%', 'Soil moisture'),
    'soil_temp': ('soil_temp_f', 'soil_temp_low', 'soil_temp_high', '°F', 'Soil temperature'),
    'soil_ph': ('soil_ph', 'soil_ph_low', 'soil_ph_high', '', 'Soil pH'),
}
SOURCE_ORDER = ['sensor', 'manual', 'weather']
SOURCE_NAME = {'sensor': 'Your sensor', 'manual': 'Typed in by you', 'weather': 'Online weather (outdoors)'}

def versions_of(c, pid):
    out = []
    for v in c.execute('SELECT version,changed_at,snapshot FROM plant_versions WHERE plant_id=? ORDER BY version', (pid,)):
        try: out.append((parse_ts(v['changed_at']), v['version'], json.loads(v['snapshot'])['fields']))
        except (ValueError, KeyError): pass
    return out

def fields_at(vers, cur, when_utc):
    """Plant fields in effect at a moment: the newest saved version at or before it (the oldest one if the moment is earlier)."""
    pick = None
    for t, n, f in vers:
        if t <= when_utc: pick = (n, f)
    if pick is None and vers: pick = (vers[0][1], vers[0][2])
    return pick if pick else (None, cur)

def hourly(rows, col, tz):
    """{(local date, hour): mean} for one column"""
    acc = {}
    for r in rows:
        v = r[col] if col else None
        if v is None: continue
        d = parse_ts(r['ts']).astimezone(tz)
        acc.setdefault((d.date().isoformat(), d.hour), []).append(v)
    return {k: sum(v) / len(v) for k, v in acc.items()}

def grade_day(metric, hrs, lo, hi, f):
    """ok: every hour in range. near: some hours out, or the average is a little outside. bad: the average is well outside. danger: past the damage point."""
    if not hrs: return 'none'
    vals = list(hrs)
    if lo is None and hi is None: return 'info'
    if metric == 'temp':
        db_, da = f.get('temp_damage_below'), f.get('temp_damage_above')
        if (db_ is not None and min(vals) < db_) or (da is not None and max(vals) > da): return 'danger'
    out = [v for v in vals if (lo is not None and v < lo) or (hi is not None and v > hi)]
    if not out: return 'ok'
    avg = sum(vals) / len(vals)
    width = (hi - lo) if lo is not None and hi is not None else max(1.0, abs(lo if lo is not None else hi) * 0.4)
    dev = max((lo - avg) if lo is not None else 0, (avg - hi) if hi is not None else 0)
    return 'bad' if dev > 0.25 * width else 'near'

def grade_light(hrs_all, f):
    """Daily light from the hourly means: DLI when most of the day has readings, otherwise daytime average PAR.
    Returns (status, dli, kind judged on, low, high)."""
    vals = list(hrs_all.values())
    if not vals: return 'none', None, None, None, None
    dli = round(sum(vals) * 3600 / 1e6, 1) if len(vals) >= 18 else None
    day = [v for v in vals if v >= 20]
    use_dli = dli is not None and (f.get('dli_low') is not None or f.get('dli_high') is not None)
    lo, hi, kind = (f.get('dli_low'), f.get('dli_high'), 'dli') if use_dli else (f.get('par_low'), f.get('par_high'), 'par')
    x = dli if kind == 'dli' else (round(sum(day) / len(day), 1) if len(day) >= 3 else None)
    if x is None: return 'none', dli, kind, lo, hi
    if lo is None and hi is None: return 'info', dli, kind, lo, hi
    if lo is not None and x < lo: return ('bad' if x < lo * 0.5 else 'near'), dli, kind, lo, hi
    if hi is not None and x > hi: return ('bad' if x > hi * 1.3 else 'near'), dli, kind, lo, hi
    return 'ok', dli, kind, lo, hi

def month_bounds(c, month, tz):
    try: y, m = (int(x) for x in month.split('-')); first = datetime(y, m, 1).date()
    except (ValueError, AttributeError): abort(400, 'month must look like 2026-10')
    last = (datetime(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).date()
    return first, last

@app.route('/api/plants/<code>/daily')
def plant_daily(code):
    """One entry per day of a month: how that day's readings compared with the plant's range as recorded at the time."""
    c = db()
    r = plant_row(c, code)
    metric = request.args.get('metric', 'temp')
    if metric not in HIST: abort(400, 'unknown metric')
    want = request.args.get('source', 'auto')
    col, lof, hif, unit, label = HIST[metric]
    loc = location(c); tz = tzinfo(loc['tz'])
    first, last = month_bounds(c, request.args.get('month', local_today(c).strftime('%Y-%m')), tz)
    a = datetime(first.year, first.month, first.day, tzinfo=tz).astimezone(timezone.utc) - timedelta(hours=1)
    z = datetime(last.year, last.month, last.day, tzinfo=tz).astimezone(timezone.utc) + timedelta(days=1, hours=1)
    rows = c.execute("SELECT ts,source,temp_f,humidity,par,soil_moisture,soil_temp_f,soil_ph FROM readings WHERE ts>=? AND ts<=? AND (source!='weather' OR device=?) ORDER BY ts",
                     (iso(a.timestamp()), iso(z.timestamp()), loc['device'])).fetchall()
    by_src = {s: [x for x in rows if x['source'] == s] for s in SOURCE_ORDER}
    hours = {}
    for s, rs in by_src.items():
        if metric == 'vpd':
            h = {}
            t, rh = hourly(rs, 'temp_f', tz), hourly(rs, 'humidity', tz)
            for k in t:
                if k in rh:
                    v = vpd_kpa(t[k], rh[k])
                    if v is not None: h[k] = v
            hours[s] = h
        else:
            hours[s] = hourly(rs, col, tz)
    vers = versions_of(c, r['id']); cur = {n: r[n] for n in FIELD_NAMES}
    fert = {}
    for f_ in c.execute('SELECT applied_on,product FROM fertilizer_log WHERE plant_code=? AND applied_on>=? AND applied_on<=?', (code, first.isoformat(), last.isoformat())):
        fert.setdefault(f_['applied_on'], []).append(f_['product'])
    days, d = [], first
    while d <= last:
        ds = d.isoformat()
        src = None
        for s in ([want] if want in SOURCE_ORDER else SOURCE_ORDER):
            if any(k[0] == ds for k in hours[s]): src = s; break
        end = datetime(d.year, d.month, d.day, 23, 59, tzinfo=tz).astimezone(timezone.utc)
        ver, f = fields_at(vers, cur, end)
        lo, hi = f.get(lof), f.get(hif)
        fallback = False
        if lo is None and hi is None and (cur.get(lof) is not None or cur.get(hif) is not None):
            lo, hi, fallback = cur.get(lof), cur.get(hif), True
        day = {'date': ds, 'source': src, 'lo': lo, 'hi': hi, 'version': ver, 'range_from_now': fallback, 'status': 'none', 'fed': fert.get(ds, [])}
        if src:
            hh = {k: v for k, v in hours[src].items() if k[0] == ds}
            vals = list(hh.values())
            day.update(n=len(vals), min=round(min(vals), 1), max=round(max(vals), 1), avg=round(sum(vals) / len(vals), 1))
            if metric == 'light':
                day['status'], dli, kind, jl, jh = grade_light(hh, f if not fallback else {**f, lof: lo, hif: hi})
                day['dli'] = dli; day['judged_on'] = kind; day['lo'], day['hi'] = jl, jh
                day['daytime_avg'] = round(sum(v for v in vals if v >= 20) / max(1, sum(1 for v in vals if v >= 20)), 1) if any(v >= 20 for v in vals) else None
            else:
                day['status'] = grade_day(metric, vals, lo, hi, f)
                day['hours_in'] = sum(1 for v in vals if (lo is None or v >= lo) and (hi is None or v <= hi))
        days.append(day)
        d += timedelta(days=1)
    return jsonify(metric=metric, label=label, unit=unit, month=first.strftime('%Y-%m'), tz=loc['tz'], days=days,
                   sources={s: SOURCE_NAME[s] for s in SOURCE_ORDER}, today=local_today(c).isoformat())

@app.route('/api/plants/<code>/day')
def plant_day(code):
    """Everything known about one local day: readings in 15-minute steps from each source, the plant's ranges then, and feedings."""
    c = db()
    r = plant_row(c, code)
    loc = location(c); tz = tzinfo(loc['tz'])
    ds = request.args.get('date') or local_today(c).isoformat()
    try: d = datetime.strptime(ds, '%Y-%m-%d').date()
    except ValueError: abort(400, 'date must look like 2026-10-20')
    a = datetime(d.year, d.month, d.day, tzinfo=tz).astimezone(timezone.utc)
    z = a + timedelta(days=1)
    rows = c.execute("SELECT * FROM readings WHERE ts>=? AND ts<? AND (source!='weather' OR device=?) ORDER BY ts", (iso(a.timestamp()), iso(z.timestamp()), loc['device'])).fetchall()
    out = {}
    for s in SOURCE_ORDER:
        bins = {}
        for x in rows:
            if x['source'] != s: continue
            t = parse_ts(x['ts']); k = int(t.timestamp() // 900)
            bins.setdefault(k, []).append(x)
        pts = []
        for k in sorted(bins):
            g = bins[k]; p = {'t': iso(k * 900)}
            for m in ('temp_f', 'humidity', 'par', 'soil_moisture', 'soil_temp_f', 'soil_ph'):
                v = [q[m] for q in g if q[m] is not None]
                p[m] = round(sum(v) / len(v), 2) if v else None
            p['vpd'] = vpd_kpa(p['temp_f'], p['humidity']) if p['temp_f'] is not None and p['humidity'] is not None else None
            pts.append(p)
        if pts: out[s] = pts
    ver, f = fields_at(versions_of(c, r['id']), {n: r[n] for n in FIELD_NAMES}, a + timedelta(days=1) - timedelta(minutes=1))
    fert = [dict(x) for x in c.execute('SELECT * FROM fertilizer_log WHERE plant_code=? AND applied_on=? ORDER BY id', (code, ds))]
    last = c.execute('SELECT applied_on FROM fertilizer_log WHERE plant_code=? AND applied_on<=? ORDER BY applied_on DESC LIMIT 1', (code, ds)).fetchone()
    return jsonify(date=ds, tz=loc['tz'], version=ver, current_version=r['version'], ranges={n: f.get(n) for n in FIELD_NAMES if n.split('_')[0] in ('temp', 'humidity', 'vpd', 'par', 'dli', 'soil', 'fert')},
                   sources=out, source_names=SOURCE_NAME, fertilized=fert, last_fed=last[0] if last else None)

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

# ---------------------------------------------------------------- frost alert (added in 1.8.0)
FROST_MARGIN = 3          # °F: forecasts often miss a clear, still night by a few degrees, so warn this far above a plant's damage point
FROST_LEVELS = {'danger': 3, 'damage': 2, 'watch': 1}

def frost_done(c):
    try: return json.loads(setting(c, 'frost_done', '{}') or '{}')
    except ValueError: return {}

def frost_report(c):
    """Nights in the home forecast that would hurt plants that are outside (Outdoors or Covered porch), plant by plant."""
    L = location(c)
    fc = loc_json(c, L['id'], 'forecast')
    today = local_today(c).isoformat()
    days = [d for d in (fc.get('days') or []) if d.get('date', '') >= today and d.get('low') is not None][:7]
    done = frost_done(c)
    plants = c.execute("SELECT * FROM plants WHERE status='active' AND temp_damage_below IS NOT NULL ORDER BY code").fetchall()
    outdoor = [r for r in plants if (r['site'] or 'Outdoors') not in INSIDE_SITES]
    photo = lambda pid: (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (pid,)).fetchone() or [None])[0]
    nights, worst = [], None
    for d in days:
        low, at = d['low'], []
        for r in outdoor:
            dmg, leth = r['temp_damage_below'], r['temp_lethal_below']
            if leth is not None and low < leth: lv = 'danger'
            elif low < dmg: lv = 'damage'
            elif low < dmg + FROST_MARGIN: lv = 'watch'
            else: continue
            at.append({'code': r['code'], 'name': r['common_name'], 'photo': photo(r['id']), 'damage': dmg, 'lethal': leth,
                       'plan': r['winter_plan'], 'site': r['site'] or 'Outdoors', 'level': lv, 'done': done.get(d['date'], {}).get(r['code'])})
        at.sort(key=lambda x: (-FROST_LEVELS[x['level']], -(x['damage'] or 0), x['code']))
        lv = max((x['level'] for x in at), key=lambda v: FROST_LEVELS[v], default=None)
        n = {'date': d['date'], 'low': low, 'high': d.get('high'), 'hours': d.get('hours'), 'level': lv, 'plants': at,
             'counts': {k: sum(1 for x in at if x['level'] == k) for k in FROST_LEVELS}}
        nights.append(n)
        if lv and (worst is None or FROST_LEVELS[lv] > FROST_LEVELS[worst['level']]
                   or (lv == worst['level'] and low < worst['low'])):
            worst = n                                     # the most serious night; among equals, the coldest
    first = next((n for n in nights if n['level']), None)
    # the same, plant by plant: every cold night for each plant, the next one (what to act on) and the coldest
    by = {}
    for n in nights:
        for x in n['plants']:
            q = by.setdefault(x['code'], {k: x[k] for k in ('code', 'name', 'photo', 'damage', 'lethal', 'plan', 'site')} | {'nights': []})
            q['nights'].append({'date': n['date'], 'low': n['low'], 'level': x['level']})
    plants_out = []
    for q in by.values():
        q['next'] = q['nights'][0]
        q['worst'] = max(q['nights'], key=lambda z: (FROST_LEVELS[z['level']], -z['low']))
        q['level'] = q['worst']['level']
        q['done'] = done.get(q['next']['date'], {}).get(q['code'])
        plants_out.append(q)
    plants_out.sort(key=lambda q: (-FROST_LEVELS[q['level']], q['next']['date'], -(q['damage'] or 0), q['code']))
    return {'place': L['name'], 'fetched_at': fc.get('fetched_at'), 'margin': FROST_MARGIN, 'today': today, 'nights': nights, 'plants': plants_out,
            'outdoor': len(outdoor), 'level': worst['level'] if worst else None,
            'worst': {k: worst[k] for k in ('date', 'low', 'level', 'counts')} if worst else None,
            'first': {k: first[k] for k in ('date', 'low', 'level', 'counts')} if first else None}

@app.route('/api/frost')
def frost_api():
    return jsonify(frost_report(db()))

@app.route('/api/frost/done', methods=['POST'])
def frost_mark():
    """Tick a plant off the cold-night checklist ("covered") for one night, or untick it."""
    c = db()
    b = request.get_json(silent=True) or {}
    date, code, what = str(b.get('date', '')), str(b.get('code', '')), b.get('what')
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date): abort(400, 'date must look like 2026-11-03')
    r = plant_row(c, code)
    if what not in ('covered', None): abort(400, "what must be 'covered' or empty")
    done = frost_done(c)
    keep = local_today(c).isoformat()
    done = {k: v for k, v in done.items() if k >= keep}           # forget nights that have passed
    night = done.setdefault(date, {})
    if what: night[r['code']] = {'what': what, 'by': editor(), 'at': now()}
    else: night.pop(r['code'], None)
    if not night: done.pop(date, None)
    set_setting(c, 'frost_done', json.dumps(done))
    d = datetime.strptime(date, '%Y-%m-%d'); night_words = f'{d:%A}, {d:%b} {d.day}'      # "Sunday, Oct 25"
    audit_only(c, 'frost', 'frost', None, what or 'undone', editor(),
               ('Covered for the cold night of %s' % night_words) if what else ('Cold-night tick removed for %s' % night_words), r['id'], r['code'])
    c.commit()
    return jsonify(frost_report(c))

# ---------------------------------------------------------------- backups
import zipfile
BACKUP_RE = re.compile(r'^plantdb-backup-\d{8}-\d{6}-(manual|auto|update)(-photos)?\.zip$')
BK_LOCK = threading.Lock()
BK_JOB = {'running': False}
BK_FREQ = {'6h': 6, '12h': 12, 'daily': 24, '3d': 72, 'weekly': 168}
BK_DEFAULTS = {'enabled': True, 'freq': 'daily', 'hour': 3, 'keep': 14, 'photos': False}

def bk_settings(c):
    try: d = json.loads(setting(c, 'backup_settings', '') or '{}')
    except ValueError: d = {}
    return {**BK_DEFAULTS, **d}

def bk_list():
    out = []
    for f in os.listdir(BACKUP_DIR):
        if not BACKUP_RE.match(f): continue
        st = os.stat(os.path.join(BACKUP_DIR, f))
        m = BACKUP_RE.match(f)
        meta = {}
        try:
            with zipfile.ZipFile(os.path.join(BACKUP_DIR, f)) as z:
                if 'backup.json' in z.namelist(): meta = json.loads(z.read('backup.json'))
        except (zipfile.BadZipFile, OSError, ValueError): meta = {'broken': True}
        out.append({'file': f, 'bytes': st.st_size, 'kind': m.group(1), 'photos': bool(m.group(2)), 'created_at': meta.get('created_at') or iso(st.st_mtime),
                    'version': meta.get('version'), 'note': meta.get('note', ''), 'by': meta.get('by', ''), 'plants': meta.get('plants'), 'broken': meta.get('broken', False)})
    return sorted(out, key=lambda x: x['file'], reverse=True)

def make_backup(kind='manual', photos=False, note='', by='Unknown'):
    """A consistent copy of the database (SQLite's own backup, safe while the app runs), zipped, optionally with the photos."""
    with BK_LOCK:
        stamp = datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')
        name = f'plantdb-backup-{stamp}-{kind}{"-photos" if photos else ""}.zip'
        tmpdb = os.path.join(BACKUP_DIR, f'.tmp-{stamp}.db')
        tmpzip = os.path.join(BACKUP_DIR, f'.tmp-{stamp}.zip')
        try:
            src = sqlite3.connect(DB_PATH, timeout=60); dst = sqlite3.connect(tmpdb)
            with dst: src.backup(dst)
            plants = dst.execute('SELECT COUNT(*) FROM plants').fetchone()[0]
            src.close(); dst.close()
            meta = {'created_at': now(), 'version': APP_VERSION, 'kind': kind, 'photos': photos, 'note': note[:300], 'by': by, 'plants': plants,
                    'restore': 'Stop the app, put plants.db in the data folder (and the photos folder, if included), then start the app. See README, Backups.'}
            with zipfile.ZipFile(tmpzip, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
                z.write(tmpdb, 'plants.db')
                z.writestr('backup.json', json.dumps(meta, indent=1))
                if photos:
                    for f in sorted(os.listdir(PHOTO_DIR)):
                        fp = os.path.join(PHOTO_DIR, f)
                        if os.path.isfile(fp): z.write(fp, 'photos/' + f, compress_type=zipfile.ZIP_STORED)   # photos are already compressed
            os.replace(tmpzip, os.path.join(BACKUP_DIR, name))
        finally:
            for t in (tmpdb, tmpzip):
                try: os.remove(t)
                except OSError: pass
        return name

def prune_backups(keep):
    autos = [b for b in bk_list() if b['kind'] == 'auto']
    removed = []
    for b in autos[keep:]:
        try: os.remove(os.path.join(BACKUP_DIR, b['file'])); removed.append(b['file'])
        except OSError: pass
    return removed

def run_backup_job(kind, photos, note, by):
    if BK_JOB.get('running'): return False
    BK_JOB.clear(); BK_JOB.update(running=True, kind=kind, started=now(), photos=photos)
    def work():
        try:
            name = make_backup(kind, photos, note, by)
            c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
            try:
                removed = prune_backups(bk_settings(c)['keep']) if kind == 'auto' else []
                if kind == 'auto': set_setting(c, 'backup_last_auto', now())
                audit_only(c, 'backup', 'backup', None, name, by, f'Backup made ({kind}{", with photos" if photos else ""})' + (f'; removed {len(removed)} old automatic backup(s)' if removed else ''))
                c.commit()
            finally: c.close()
            BK_JOB.update(running=False, ok=True, file=name, finished=now())
        except Exception as e:
            BK_JOB.update(running=False, ok=False, error=f'{type(e).__name__}: {e}'[:300], finished=now())
    threading.Thread(target=work, daemon=True).start()
    return True

def backup_due(c, t=None):
    S = bk_settings(c)
    if not S['enabled']: return False
    last = setting(c, 'backup_last_auto')
    t = t or datetime.now(timezone.utc)
    if not last: return True
    lt = parse_ts(last)
    hours = BK_FREQ.get(S['freq'], 24)
    if hours < 24: return (t - lt).total_seconds() >= hours * 3600 - 60
    # daily or longer: at (or after) the chosen local hour, once enough days have passed
    tz = tzinfo(location(c)['tz'])
    lt_l, t_l = lt.astimezone(tz), t.astimezone(tz)
    due_day = lt_l.date() + timedelta(days=hours // 24)
    return t_l.date() > due_day or (t_l.date() == due_day and t_l.hour >= int(S['hour'])) or (t - lt).total_seconds() > (hours + 24) * 3600

def backup_loop():
    time.sleep(60)
    while True:
        try:
            c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
            try:
                if backup_due(c) and not BK_JOB.get('running'):
                    run_backup_job('auto', bk_settings(c)['photos'], 'Automatic backup', 'Automatic backup')
            finally: c.close()
        except Exception: pass
        time.sleep(300)

@app.route('/api/backups', methods=['GET', 'POST'])
def backups():
    c = db()
    if request.method == 'POST':
        b = request.get_json(silent=True) or {}
        kind = 'update' if b.get('kind') == 'update' else 'manual'
        if b.get('wait'):                         # the updater waits for the file before it touches anything
            if BK_JOB.get('running'): abort(409, 'A backup is already running')
            name = make_backup(kind, bool(b.get('photos')), str(b.get('note', '')), editor())
            audit_only(c, 'backup', 'backup', None, name, editor(), f'Backup made ({kind})'); c.commit()
            return jsonify(file=name, path=os.path.join(BACKUP_DIR, name)), 201
        started = run_backup_job(kind, bool(b.get('photos')), str(b.get('note', '')), editor())
        return jsonify(started=started, job=dict(BK_JOB)), (202 if started else 409)
    S = bk_settings(c)
    lst = bk_list()
    free = shutil.disk_usage(BACKUP_DIR)
    return jsonify(backups=lst, settings=S, job=dict(BK_JOB), last_auto=setting(c, 'backup_last_auto'), dir=BACKUP_DIR,
                   mounted=BACKUP_DIR == '/backups', total_bytes=sum(x['bytes'] for x in lst), free_bytes=free.free,
                   db_bytes=os.path.getsize(DB_PATH), photo_bytes=sum(os.path.getsize(os.path.join(PHOTO_DIR, f)) for f in os.listdir(PHOTO_DIR) if os.path.isfile(os.path.join(PHOTO_DIR, f))),
                   freqs=list(BK_FREQ))

@app.route('/api/backups/settings', methods=['PUT'])
def backup_settings_put():
    c = db()
    b = request.get_json(silent=True) or {}
    S = bk_settings(c)
    if 'enabled' in b: S['enabled'] = bool(b['enabled'])
    if 'freq' in b:
        if b['freq'] not in BK_FREQ: abort(400, 'Unknown frequency')
        S['freq'] = b['freq']
    for k, lo, hi in (('hour', 0, 23), ('keep', 1, 365)):
        if k in b:
            try: v = int(b[k])
            except (TypeError, ValueError): abort(400, f'{k} must be a whole number')
            if not lo <= v <= hi: abort(400, f'{k} must be between {lo} and {hi}')
            S[k] = v
    if 'photos' in b: S['photos'] = bool(b['photos'])
    old = setting(c, 'backup_settings', '')
    set_setting(c, 'backup_settings', json.dumps(S))
    audit_only(c, 'setting', 'backup_settings', old, json.dumps(S), editor(), 'Automatic backup settings changed')
    c.commit()
    return jsonify(settings=S)

@app.route('/api/backups/job')
def backup_job():
    return jsonify(dict(BK_JOB))

@app.route('/api/backups/<name>', methods=['GET', 'DELETE'])
def backup_file(name):
    if not BACKUP_RE.match(name) or not os.path.exists(os.path.join(BACKUP_DIR, name)): abort(404, 'No such backup')
    if request.method == 'DELETE':
        os.remove(os.path.join(BACKUP_DIR, name))
        c = db(); audit_only(c, 'backup', 'backup', name, None, editor(), 'Backup deleted'); c.commit()
        return jsonify(ok=True)
    return send_from_directory(BACKUP_DIR, name, as_attachment=True, mimetype='application/zip')

init_db()
threading.Thread(target=backup_loop, daemon=True).start()
if os.environ.get('PLANTDB_WEATHER', '1') == '1':
    threading.Thread(target=weather_loop, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
