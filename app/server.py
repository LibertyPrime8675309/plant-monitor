"""Plant Database - small Flask + SQLite app.

Everything lives in DATA_DIR (default /data): plants.db, photos/, cache/.
Edits are versioned: every save bumps the plant's page version, writes a full snapshot
to plant_versions and one row per changed field to audit_log (what / before / after / who / when).
"""
import csv, hmac, io, json, math, os, re, secrets, shutil, sqlite3, threading, time, urllib.error, urllib.parse, urllib.request, uuid
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

from flask import Flask, Response, abort, g, has_request_context, jsonify, request, send_from_directory
from PIL import Image, ImageOps
import segno
import writable                 # 1.12.1: the start-up write check, shared with start.py

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.environ.get('DATA_DIR', '/data')
DB_PATH = os.path.join(DATA_DIR, 'plants.db')
PHOTO_DIR = os.path.join(DATA_DIR, 'photos')
TRASH_DIR = os.path.join(DATA_DIR, 'photos_deleted')
THUMB_DIR = os.path.join(DATA_DIR, 'cache', 'thumbs2')     # 1.21.0: sized by the short side (thumbs/ was 520 px on the long side)
SEED_DIR = os.path.join(APP_DIR, 'seed')
PASSWORD = os.environ.get('PLANTDB_PASSWORD', '')
# Backups go to /backups when that folder is mounted (docker-compose maps ./backups there), otherwise data/backups.
BACKUP_DIR = os.environ.get('PLANTDB_BACKUP_DIR') or ('/backups' if os.path.isdir('/backups') else os.path.join(DATA_DIR, 'backups'))

def _check_writable():
    """1.12.0: say plainly if Docker gives the app no write access to the data or backups folder. Since 1.12.1 start.py
    already ran this check as the app's own user and switched to root inside the container if it failed, so this only
    stops the app when even that cannot write (the updater looks for PLANTDB_NOT_WRITABLE)."""
    bad = writable.problem(DATA_DIR, BACKUP_DIR)
    if bad:
        print('PLANTDB_NOT_WRITABLE: the app cannot write to %s (%s). See README, "If the app does not start after updating".' % bad, flush=True)
        raise SystemExit(3)
_check_writable()

app = Flask(__name__, static_folder=os.path.join(APP_DIR, 'static'), static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 60 * 1024 * 1024

WINTER_PLANS = ['Move indoors', 'Protect outside', 'Hardy outside', 'Seasonal die-back', 'Annual']
HEALTH = ['Good', 'Fair', 'Poor', 'Critical']
# where the plant is now (added in 1.7.0); plants at an "inside" place are left off the outdoor winter lists and frost warnings
SITES = ['Outdoors', 'Covered porch', 'Indoors', 'Garage or shed']
# 1.9.0: what decides which pest treatments suit a plant before it comes inside (chosen on its page)
LEAF_TYPES = ['Large leaves', 'Small or many leaves', 'Fuzzy or velvety leaves', 'Succulent or cactus', 'Fern fronds', 'Palm fronds', 'Grows in water']
POT_SIZES = ['Small: fits in a bucket', 'Medium: fits in a big tub', 'Large: too big to soak']
PET_SAFETY = ['Toxic to pets', 'Mildly toxic to pets', 'Not known to be toxic', 'Safe for pets (ASPCA)']    # 1.17.0
FERT_STRENGTHS = ['None needed', 'Quarter strength', 'Quarter to half strength', 'Half strength', 'Full strength']   # 1.11.0
PESTS = ['Spider mites', 'Mealybugs', 'Scale', 'Aphids', 'Whiteflies', 'Thrips', 'Ants', 'Fungus gnats', 'Root mealybugs',
         'Slugs or snails', 'Pill bugs or earwigs', 'Other']
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
    # ---- added in 1.9.0
    ('leaf_type', 'enum', 'Leaf type'), ('pot_size', 'enum', 'Pot size'), ('pests_found', 'list', 'Pests you found'),
    # ---- added in 1.11.0: the fertilizer this plant needs, for matching it to the fertilizers you have
    ('npk_ratio', 'text', 'Fertilizer ratio needed (N-P-K)'), ('fert_strength', 'enum', 'Fertilizer strength'),
    # ---- added in 1.14.0: more about the plant itself (About this plant on its page), with sources
    ('growth_habit', 'text', 'Type of plant'), ('kingdom', 'text', 'Kingdom'), ('taxon_order', 'text', 'Order'),
    ('family', 'text', 'Family'), ('genus', 'text', 'Genus'),
    ('height_ground', 'text', 'Mature height in the ground'), ('width_ground', 'text', 'Mature width in the ground'),
    ('height_pot', 'text', 'Mature height in a pot'), ('width_pot', 'text', 'Mature width in a pot'),
    ('growth_rate', 'text', 'Growth rate'), ('lifespan', 'text', 'Lifespan'),
    ('zone_low', 'text', 'Hardiness zone, coldest (USDA)'), ('zone_high', 'text', 'Hardiness zone, warmest (USDA)'), ('zone_notes', 'long', 'Hardiness notes'),
    ('native_range', 'long', 'Native range'), ('conservation_status', 'long', 'Conservation status'), ('invasive', 'long', 'Invasive risk'),
    ('bloom', 'long', 'Flowers'), ('fruit', 'long', 'Fruit'),
    ('danger_humans', 'long', 'Dangers to people'), ('danger_animals', 'long', 'Dangers to pets and other animals'),
    ('propagation', 'list', 'Propagation'), ('sources', 'list', 'Sources'),
    ('pet_safety', 'enum', 'Safety for pets'),                                                          # 1.17.0, for the pets filter
]
ENUMS = {'winter_plan': WINTER_PLANS, 'site': SITES, 'health_rating': HEALTH, 'leaf_type': LEAF_TYPES, 'pot_size': POT_SIZES, 'fert_strength': FERT_STRENGTHS, 'pet_safety': PET_SAFETY}
OPTIONAL_ENUMS = ('leaf_type', 'pot_size', 'fert_strength', 'pet_safety')        # may be left as "Not set"
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
CREATE TABLE IF NOT EXISTS fertilizers(
  id INTEGER PRIMARY KEY AUTOINCREMENT, product TEXT NOT NULL UNIQUE COLLATE NOCASE, form TEXT NOT NULL DEFAULT 'liquid',
  n REAL, p REAL, k REAL, note TEXT NOT NULL DEFAULT '', created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS people(
  login TEXT PRIMARY KEY, name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'viewer', first_seen TEXT NOT NULL, last_seen TEXT NOT NULL);
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
CREATE TABLE IF NOT EXISTS lights(
  id INTEGER PRIMARY KEY AUTOINCREMENT, lkey TEXT UNIQUE, name TEXT NOT NULL, data TEXT NOT NULL DEFAULT '{}', count INTEGER NOT NULL DEFAULT 1,
  fixture TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', sort INTEGER NOT NULL DEFAULT 0,
  created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS light_spots(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, light_id INTEGER NOT NULL, units INTEGER NOT NULL DEFAULT 1,
  distance_in REAL NOT NULL, hours REAL NOT NULL, dim_pct INTEGER NOT NULL DEFAULT 100, notes TEXT NOT NULL DEFAULT '',
  created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS light_assign(
  plant_code TEXT PRIMARY KEY, spot_id INTEGER NOT NULL, assigned_by TEXT, assigned_at TEXT);
CREATE TABLE IF NOT EXISTS indoor_places(
  id INTEGER PRIMARY KEY AUTOINCREMENT, room TEXT NOT NULL, name TEXT NOT NULL DEFAULT '', sort INTEGER NOT NULL DEFAULT 0,
  created_by TEXT NOT NULL, created_at TEXT NOT NULL, UNIQUE(room, name));
CREATE TABLE IF NOT EXISTS plant_groups(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE COLLATE NOCASE, kind TEXT NOT NULL DEFAULT 'picked',
  rule TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', created_by TEXT NOT NULL, created_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS group_members(
  group_id INTEGER NOT NULL, plant_id INTEGER NOT NULL, added_by TEXT, added_at TEXT, PRIMARY KEY(group_id, plant_id));
CREATE TABLE IF NOT EXISTS bulk_changes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER, what TEXT NOT NULL, changes TEXT NOT NULL,
  done_by TEXT NOT NULL, done_at TEXT NOT NULL, undone_by TEXT, undone_at TEXT);
""" % ',\n  '.join(f"{n} {SQLTYPE.get(k, 'TEXT')}" for n, k, _ in FIELDS)

def init_db():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    # WAL can misbehave on Windows bind mounts; the default rollback journal is safe everywhere for a single-process home app.
    c.execute('PRAGMA journal_mode=' + os.environ.get('PLANTDB_JOURNAL', 'DELETE'))
    c.executescript(SCHEMA)
    c.executescript(FUNGI_SCHEMA)                 # 1.22.0: mushroom finds, library notes and the wishlist
    have = {r[1] for r in c.execute('PRAGMA table_info(plants)')}
    for n, k, _ in FIELDS:                      # upgrade an older database: add any column this version needs
        if n not in have: c.execute(f"ALTER TABLE plants ADD COLUMN {n} {SQLTYPE.get(k, 'TEXT')}")
    if 'extra' not in {r[1] for r in c.execute('PRAGMA table_info(readings)')}: c.execute('ALTER TABLE readings ADD COLUMN extra TEXT')
    if 'place_id' not in {r[1] for r in c.execute('PRAGMA table_info(light_spots)')}: c.execute('ALTER TABLE light_spots ADD COLUMN place_id INTEGER')   # 1.13.1
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
            for i, L in enumerate(b.get('lights_add', [])):     # 1.13.0: grow lights; added once, then yours to edit
                if c.execute('SELECT 1 FROM lights WHERE lkey=? OR name=?', (L['key'], L['name'])).fetchone(): continue
                spec = {k: v for k, v in L.items() if k not in ('key', 'name', 'count', 'fixture', 'notes')}
                c.execute('INSERT INTO lights(lkey,name,data,count,fixture,notes,sort,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                          (L['key'], L['name'], json.dumps(spec), L.get('count', 1), L.get('fixture', ''), L.get('notes', ''), i, who, ts))
                audit_only(c, 'light', 'light', None, '%s (%d)' % (L['name'], L.get('count', 1)), who, 'Grow light added (%s): %s' % (label, L['name']))
            for i, pl in enumerate(b.get('places_add', [])):    # 1.13.1: rooms and shelves inside, where light spots go
                c.execute('INSERT OR IGNORE INTO indoor_places(room,name,sort,created_by,created_at) VALUES(?,?,?,?,?)',
                          (pl['room'], pl.get('name', ''), pl.get('sort', i), who, ts))
            for u in b.get('lights_update', []):                # guarded, like plant updates: only if the light still holds the old value
                L = c.execute('SELECT * FROM lights WHERE lkey=?', (u['key'],)).fetchone()
                if not L: continue
                d, cols, done = light_specs(L), {}, []
                for f, (old, new) in u['set'].items():
                    cur = L[f] if f in ('fixture', 'notes', 'count') else d.get(f)
                    if str(cur if cur is not None else '') != str(old if old is not None else ''): continue
                    if f in ('fixture', 'notes', 'count'): cols[f] = new
                    else: d[f] = new
                    done.append(f)
                if done:
                    c.execute('UPDATE lights SET %s data=?, updated_by=?, updated_at=? WHERE id=?' % ''.join('%s=?, ' % k for k in cols),
                              (*cols.values(), json.dumps(d), who, ts, L['id']))
                    audit_only(c, 'light', 'light', None, ', '.join(done), who, 'Grow light updated (%s): %s, %s' % (label, L['name'], u.get('note') or ', '.join(done)))
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
    u = getattr(g, 'user', None)
    if u and u.get('via') == 'tailscale': return u['name']          # 1.12.0: signed in through Tailscale, so not typed in
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
        allowed = ENUMS.get(name, HEALTH)
        if s == '' and name in OPTIONAL_ENUMS: return ''
        if s not in allowed: abort(400, f'{FIELD_LABEL[name]} must be one of: ' + ', '.join(allowed))
    if kind == 'list': s = '\n'.join(x.strip() for x in s.split('\n') if x.strip())
    if name == 'npk_ratio' and s:
        r = parse_ratio(s)
        if not r: abort(400, 'Fertilizer ratio needed must be three numbers for N, P and K, such as 3-1-2')
        s = '-'.join('%g' % x for x in r)
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

# ---------------------------------------------------------------- people (1.12.0): who is using the app, and what they may do
# The Tailscale container (docker-compose.yml) is the only way in to TS_PORT, which is never published to the computer or the
# home network. Tailscale Serve adds the visitor's login and name to every request and removes any copy the visitor sent, so on
# that port the headers can be trusted. Requests on the other port come from this computer itself (the updater, a browser on the
# PC) or, if PLANTDB_BIND opens it, the home network; those keep working as before and have full access.
TS_PORT = os.environ.get('PLANTDB_TS_PORT', '8081')
SENSOR_PORT = os.environ.get('PLANTDB_SENSOR_PORT', '8082')     # sensors only: POST /api/readings with the token, nothing else
ROLES = ['owner', 'editor', 'viewer']
ROLE_WORD = {'owner': 'Owner', 'editor': 'Can edit', 'viewer': 'Can view only'}
SEEN = {}                                            # login -> when last_seen was last written, so it is not written on every request

def via_tailscale():
    return has_request_context() and str(request.environ.get('SERVER_PORT', '')) == TS_PORT

def clean_person_name(n):
    return re.sub(r'[^\w .\-@\']', '', str(n or '')).strip()[:40]

def ts_user():
    login = request.headers.get('Tailscale-User-Login', '').strip()[:200]
    if not login: return None                        # a tagged device or something else that is not a person
    c, t = db(), now()
    r = c.execute('SELECT * FROM people WHERE login=?', (login,)).fetchone()
    if r is None:
        name = clean_person_name(request.headers.get('Tailscale-User-Name')) or clean_person_name(login.split('@')[0]) or 'Someone'
        first = not c.execute("SELECT 1 FROM people WHERE role='owner'").fetchone()   # the first person in (the setup script makes it you) owns it
        c.execute('INSERT INTO people(login,name,role,first_seen,last_seen) VALUES(?,?,?,?,?)', (login, name, 'owner' if first else 'viewer', t, t))
        audit_only(c, 'setting', 'person', None, f"{name} ({login})", 'Plant record', f"New person signed in through Tailscale: {name}, {'owner' if first else 'can view only'}")
        c.commit()
        r = c.execute('SELECT * FROM people WHERE login=?', (login,)).fetchone()
        SEEN[login] = time.time()
    elif time.time() - SEEN.get(login, 0) > 600:
        c.execute('UPDATE people SET last_seen=? WHERE login=?', (t, login)); c.commit()
        SEEN[login] = time.time()
    return {'via': 'tailscale', 'login': r['login'], 'name': r['name'], 'role': r['role'] if r['role'] in ROLES else 'viewer'}

def owner_name(c):
    r = c.execute("SELECT name FROM people WHERE role='owner' ORDER BY first_seen LIMIT 1").fetchone()
    return r[0] if r else 'the owner'

OWNER_ONLY_PATHS = ('/api/backups', '/api/ingest', '/api/people')        # any request (the people list shows everyone's login)
OWNER_ONLY_CHANGES = ('/api/settings', '/api/weather/settings', '/api/identify/settings', '/api/library/settings', '/api/library/prefetch')   # changes only
VIEWER_POSTS = ('/api/identify',)            # 1.18.0: asks this computer what a picture shows; changes nothing, so viewers may use it

def role_refusal(u):
    """Why this person may not make this request, or None. The server decides; the page only hides what would be refused."""
    role, path, change = u['role'], request.path, request.method not in ('GET', 'HEAD', 'OPTIONS')
    if role == 'owner': return None
    if path == '/api/me': return None                                    # your own name
    if path.startswith(OWNER_ONLY_PATHS) or (change and path.startswith(OWNER_ONLY_CHANGES)) or (change and re.match(r'^/api/places/\d+$', path)):
        return f'Only {owner_name(db())} can do this.'
    if role == 'viewer' and change and path not in VIEWER_POSTS:
        return f'You can look at everything, but changes are turned off for you. Ask {owner_name(db())} if you would like to edit.'
    return None

def me_dict(c):
    u = getattr(g, 'user', None) or {'via': 'local', 'login': None, 'name': '', 'role': 'owner'}
    return {'via': u['via'], 'login': u['login'], 'name': u['name'] if u['via'] == 'tailscale' else '', 'role': u['role'],
            'role_word': ROLE_WORD[u['role']], 'owner_name': owner_name(c)}

@app.route('/api/me', methods=['GET', 'PUT'])
def me():
    """Who you are to the app. PUT {name} renames you, if you are signed in through Tailscale."""
    c = db()
    if request.method == 'PUT':
        u = g.user
        if u['via'] != 'tailscale': abort(400, 'On this computer your name is typed in; it is not stored by the app.')
        name = clean_person_name((request.get_json(silent=True) or {}).get('name'))
        if not name: abort(400, 'Type a name')
        if name != u['name']:
            c.execute('UPDATE people SET name=? WHERE login=?', (name, u['login']))
            audit_only(c, 'setting', 'person', u['name'], name, name, f"Name changed from {u['name']} to {name} ({u['login']})")
            c.commit(); g.user = dict(u, name=name)
    return jsonify(me_dict(c))

@app.route('/api/people', methods=['GET', 'PUT', 'DELETE'])
def people():
    """The people who have signed in through Tailscale (owner only for changes). PUT {login, name?, role?} adds or changes one;
    DELETE ?login= removes one (they come back as "Can view only" if they visit again)."""
    c = db()
    if request.method == 'PUT':
        b = request.get_json(silent=True) or {}
        login = str(b.get('login', '')).strip()[:200]
        if not login: abort(400, 'login is required')
        r = c.execute('SELECT * FROM people WHERE login=?', (login,)).fetchone()
        role = b.get('role', r['role'] if r else 'viewer')
        if role not in ROLES: abort(400, 'role must be one of: ' + ', '.join(ROLES))
        name = clean_person_name(b.get('name')) or (r['name'] if r else clean_person_name(login.split('@')[0]) or 'Someone')
        if r and r['role'] == 'owner' and role != 'owner' and c.execute("SELECT COUNT(*) FROM people WHERE role='owner'").fetchone()[0] < 2:
            abort(409, 'There must be at least one owner. Make someone else an owner first.')
        if r:
            c.execute('UPDATE people SET name=?, role=? WHERE login=?', (name, role, login))
            if (r['name'], r['role']) != (name, role):
                audit_only(c, 'setting', 'person', f"{r['name']}: {r['role']}", f"{name}: {role}", editor(), f"{name} ({login}) is now: {ROLE_WORD[role]}")
        else:
            t = now()
            c.execute('INSERT INTO people(login,name,role,first_seen,last_seen) VALUES(?,?,?,?,?)', (login, name, role, t, t))
            audit_only(c, 'setting', 'person', None, f"{name}: {role}", editor(), f"{name} ({login}) added: {ROLE_WORD[role]}")
        c.commit()
    elif request.method == 'DELETE':
        login = request.args.get('login', '')
        r = c.execute('SELECT * FROM people WHERE login=?', (login,)).fetchone()
        if not r: abort(404, 'That person is not in the list')
        if getattr(g, 'user', {}).get('login') == login: abort(409, 'You cannot remove yourself')
        if r['role'] == 'owner' and c.execute("SELECT COUNT(*) FROM people WHERE role='owner'").fetchone()[0] < 2: abort(409, 'There must be at least one owner')
        c.execute('DELETE FROM people WHERE login=?', (login,))
        audit_only(c, 'setting', 'person', f"{r['name']}: {r['role']}", None, editor(), f"{r['name']} ({login}) removed from the list of people")
        c.commit()
    rows = [dict(r) | {'role_word': ROLE_WORD.get(r['role'], r['role'])} for r in c.execute("SELECT * FROM people ORDER BY CASE role WHEN 'owner' THEN 0 WHEN 'editor' THEN 1 ELSE 2 END, name")]
    return jsonify(people=rows, roles=[{'key': k, 'label': ROLE_WORD[k]} for k in ROLES], me=me_dict(c))

# ---------------------------------------------------------------- security
@app.before_request
def guard():
    if request.path == '/healthz': return None
    if has_request_context() and str(request.environ.get('SERVER_PORT', '')) == SENSOR_PORT and not (request.path == '/api/readings' and request.method == 'POST'):
        abort(404, 'This port only takes sensor readings (POST /api/readings).')
    if request.path == '/api/readings' and request.method == 'POST':
        # sensors cannot type a password or send a browser header, so this one route is checked by a secret token instead
        tok = setting(db(), 'ingest_token', '')
        if not tok or not hmac.compare_digest(request.headers.get('X-Ingest-Token', ''), tok): abort(403, 'missing or wrong X-Ingest-Token')
        return None
    if request.path.startswith('/cal/') and request.method in ('GET', 'HEAD'):
        return None                  # the subscribed calendar: calendar services cannot type a password, so its link carries a private token instead
    if via_tailscale():
        g.user = ts_user()
        if g.user is None:
            return Response('Open Plant record from a device that is signed in to Tailscale as a person.', 403, {'Content-Type': 'text/plain; charset=utf-8'})
    else:
        if PASSWORD:
            a = request.authorization
            if not (a and hmac.compare_digest(a.password or '', PASSWORD)):
                return Response('Password required', 401, {'WWW-Authenticate': 'Basic realm="Plant database"'})
        g.user = {'via': 'local', 'login': None, 'name': editor(), 'role': 'owner'}     # this computer (or the home network, if opened to it)
    refusal = role_refusal(g.user)
    if refusal: abort(403, refusal)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        # CSRF guard: custom header cannot be sent cross-site without a CORS preflight (which we never allow)
        if not request.headers.get('X-Editor'): abort(403, 'missing X-Editor header')
        o = request.headers.get('Origin')
        if o and urlparse(o).netloc != request.host: abort(403, 'cross-origin request refused')

@app.after_request
def headers(resp):
    if via_tailscale():                              # always HTTPS (Tailscale Serve), so browsers can be told to stay on HTTPS
        resp.headers['Strict-Transport-Security'] = 'max-age=31536000'
    resp.headers['Permissions-Policy'] = 'geolocation=(self), microphone=(), payment=(), usb=(), camera=(self)'   # 1.22.0: location for mushroom finds
    resp.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
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
@app.errorhandler(502)
@app.errorhandler(503)
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
# 1.9.0: the steps for getting a plant ready to come inside are logged as care too (see PREP_METHODS)
CARE_KINDS.update({'prep_inspect': 'Inspected for pests', 'prep_potclean': 'Cleaned the pot and saucer', 'prep_rinse': 'Rinsed with water',
                   'prep_wipe': 'Wiped the leaves', 'prep_soap': 'Sprayed insecticidal soap', 'prep_oil': 'Sprayed horticultural oil',
                   'prep_alcohol': 'Dabbed pests with rubbing alcohol', 'prep_soak': 'Soaked the pot', 'prep_topsoil': 'Refreshed the top of the soil',
                   'prep_repot': 'Repotted in fresh soil'})
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
    for code, kind, d in c.execute("SELECT plant_code, CASE WHEN kind IN ('prep_soak','prep_repot') THEN 'water' ELSE kind END AS k, MAX(done_on) "
                                   "FROM care_log WHERE kind IN ('water','check','prep_soak','prep_repot') GROUP BY plant_code, k"):     # a soak or a repot waters the plant
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
    who, ids, skipped = editor(), [], []
    for code in codes:
        r = plant_row(c, code)
        # 1.21.0: a plant is watered at most once a day, so "Water all" and a second press skip it instead of logging it twice
        if kind == 'water' and c.execute("SELECT 1 FROM care_log WHERE plant_code=? AND kind='water' AND done_on=?", (r['code'], day)).fetchone():
            skipped.append(r['code']); continue
        ids.append(c.execute('INSERT INTO care_log(plant_code,kind,done_on,note,created_by,created_at) VALUES(?,?,?,?,?,?)',
                             (r['code'], kind, day, note, who, now())).lastrowid)
        audit_only(c, 'care', 'care_log', None, f'{CARE_KINDS[kind]} {day}' + (f': {note}' if note else ''), who,
                   CARE_KINDS[kind] + (f': {note}' if note else '') + ('' if day == local_today(c).isoformat() else f' (for {day_words(day)})'), r['id'], r['code'])
    c.commit()
    return jsonify(ids=ids, skipped=skipped, water=water_report(c, codes)['plants']), 201

@app.route('/api/care/<int:i>', methods=['DELETE'])
def care_one(i):
    c = db()
    old = c.execute('SELECT * FROM care_log WHERE id=?', (i,)).fetchone()
    if not old: abort(404, 'entry not found')
    c.execute('DELETE FROM care_log WHERE id=?', (i,))
    r = c.execute('SELECT id FROM plants WHERE code=?', (old['plant_code'],)).fetchone()
    audit_only(c, 'care', 'care_log', f"{CARE_KINDS.get(old['kind'], old['kind'])} {old['done_on']}", None, editor(),
               ('Undone right after it was logged: ' if request.args.get('undo') == '1' else 'Removed from the care log: ')     # ?undo=1: the Undo button (prototype)
               + CARE_KINDS.get(old['kind'], old['kind']) + ', ' + day_words(old['done_on']), r['id'] if r else None, old['plant_code'])
    c.commit()
    return jsonify(ok=True)

def runs_as():
    """1.12.1: which user the app runs as inside its container (set by start.py), for the owner's Debug window."""
    if (getattr(g, 'user', None) or {}).get('role') != 'owner': return None
    v = os.environ.get('PLANTDB_RUNS_AS', '')
    if v == 'user': return {'root': False, 'text': 'Its own user, without special privileges'}
    if v.startswith('root:'): return {'root': True, 'text': 'Root inside its container, because ' + v[5:]}
    return None

@app.route('/api/version')
def version(): return jsonify(version=APP_VERSION)

# ---------------------------------------------------------------- api: meta/reference
@app.route('/api/meta')
def meta():
    c = db()
    L = location(c)
    return jsonify(fields=[{'name': n, 'kind': k, 'label': l} for n, k, l in FIELDS], winter_plans=WINTER_PLANS, health=HEALTH, sites=SITES, inside_sites=INSIDE_SITES,
                   enums=ENUMS, optional_enums=OPTIONAL_ENUMS, pests=PESTS,
                   counts={'plants': c.execute("SELECT COUNT(*) FROM plants WHERE status='active'").fetchone()[0],
                           'photos': c.execute('SELECT COUNT(*) FROM photos').fetchone()[0]},
                   password_protected=bool(PASSWORD), int_ranges=INT_RANGES, num_ranges=NUM_RANGES, version=APP_VERSION,
                   home_tz=L['tz'],              # the browser uses this for "today", so dates match the server's
                   place=place_brief(L), climate=place_climate(c, L), zone=place_zone(c, L), me=me_dict(c), runs_as=runs_as(),
                   places=[place_brief(loc_dict(r)) for r in c.execute('SELECT * FROM locations ORDER BY is_home DESC, name')])

REF_PLACE = (30.5083, -97.6789)       # the written winter reference (climate table and notes) is for Round Rock, TX

@app.route('/api/reference')
def reference():
    """The written winter reference, plus (1.11.0) whether it is about the place in use, and that place's own monthly
    averages from its weather history when it has 3 years or more, so the Winter plan works for any place."""
    c = db()
    r = c.execute("SELECT value FROM settings WHERE key='reference'").fetchone()
    ref = json.loads(r[0]) if r else {}
    L = location(c)
    ref['applies'] = abs(L['lat'] - REF_PLACE[0]) < 0.5 and abs(L['lon'] - REF_PLACE[1]) < 0.5
    ref['place'] = place_brief(L)
    ref['normals'] = place_normals(c, L)
    return jsonify(ref)

PLACE_NORMALS = {}
def place_normals(c, L):
    """Average low, high, freezing nights and humidity for each month at a place, from its daily weather history."""
    hit = PLACE_NORMALS.get(L['id'])
    if hit and time.time() - hit[0] < 6 * 3600: return hit[1]
    out = None
    try:
        rows = c.execute("""SELECT CAST(substr(date, 6, 2) AS INTEGER) m, COUNT(DISTINCT substr(date, 1, 4)) years,
              AVG(json_extract(data, '$.temperature_2m_min')), AVG(json_extract(data, '$.temperature_2m_max')),
              SUM(CASE WHEN json_extract(data, '$.temperature_2m_min') <= 32 THEN 1 ELSE 0 END), AVG(json_extract(data, '$.relative_humidity_2m_mean'))
              FROM weather_daily WHERE loc_id=? AND kind='observed' GROUP BY m ORDER BY m""", (L['id'],)).fetchall()
        if len(rows) == 12 and min(r[1] for r in rows) >= 3:
            out = {'years': min(r[1] for r in rows), 'since': c.execute("SELECT MIN(date) FROM weather_daily WHERE loc_id=? AND kind='observed'", (L['id'],)).fetchone()[0],
                   'months': [{'month': MONTH_ABBR[r[0] - 1], 'low': round(r[2]) if r[2] is not None else None, 'high': round(r[3]) if r[3] is not None else None,
                               'freeze_nights': round(r[4] / r[1], 1), 'rh': round(r[5]) if r[5] is not None else None} for r in rows]}
    except sqlite3.OperationalError: out = None
    PLACE_NORMALS[L['id']] = (time.time(), out)
    return out
MONTH_ABBR = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

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

# ---------------------------------------------------------------- 1.18.0: identify a plant from a picture, and the plant library
# The pictures go to the vision service (container "plant-vision", vision/service.py) on Docker's private network. It runs
# BioCLIP on this computer and compares the picture with your own photos and with its species list. Pl@ntNet and Claude
# are optional second opinions, asked only when you press their buttons, with keys the owner saves on the Identify page.
VISION_URL = os.environ.get('PLANTDB_VISION_URL', 'http://vision:8090').rstrip('/')
PLANTNET_URL = os.environ.get('PLANTDB_PLANTNET_URL', 'https://my-api.plantnet.org/v2/identify/all')
CLAUDE_URL = os.environ.get('PLANTDB_CLAUDE_URL', 'https://api.anthropic.com/v1/messages')
CLAUDE_MODEL = 'claude-sonnet-5-5'
ID_SCOPES = ('common', 'texas', 'us', 'world', 'fungi')

def vision_call(path, data=None, ctype=None, timeout=60):
    req = urllib.request.Request(VISION_URL + path, data=data, headers={'Content-Type': ctype} if ctype else {}, method='POST' if data is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read())
        except Exception: body = {}
        if e.code == 503: abort(503, body.get('error') or 'The picture checker is still setting up. Try again in a few minutes.')
        abort(502, body.get('error') or f'The picture checker could not read that ({e.code}).')
    except (urllib.error.URLError, OSError, TimeoutError):
        abort(503, 'The picture checker is not running. Start it with the updater, or see README, "Identify a plant".')

def picture_bytes(max_side=None):
    """The picture sent with the request (field 'image'), checked, turned upright and saved as JPEG."""
    f = request.files.get('image')
    if not f: abort(400, 'Send a picture')
    try:
        im = ImageOps.exif_transpose(Image.open(f.stream)); im.load(); im = im.convert('RGB')
    except Exception:
        abort(400, 'That is not a picture this can read (use JPG or PNG)')
    if max_side: im.thumbnail((max_side, max_side))
    b = io.BytesIO(); im.save(b, 'JPEG', quality=88); return b.getvalue()

def multipart(fields, files):
    """A small multipart/form-data body: fields {name: value}, files [(name, filename, bytes, type)]."""
    bd = 'plantdb' + uuid.uuid4().hex
    out = io.BytesIO()
    for k, v in fields.items():
        out.write(f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    for k, fn, data, ct in files:
        out.write(f'--{bd}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\nContent-Type: {ct}\r\n\r\n'.encode() + data + b'\r\n')
    out.write(f'--{bd}--\r\n'.encode())
    return out.getvalue(), 'multipart/form-data; boundary=' + bd

def plant_brief(c, code):
    r = c.execute('SELECT id, code, common_name, scientific_name, location, site, status FROM plants WHERE code=?', (code,)).fetchone()
    if not r: return None
    ph = c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC, id LIMIT 1', (r['id'],)).fetchone()
    return {'code': r['code'], 'common_name': r['common_name'], 'scientific_name': r['scientific_name'], 'location': r['location'],
            'site': r['site'], 'photo': ph[0] if ph else None}

def species_owned(c):
    """{'genus species' (lower case): [codes]} and {'genus': [codes]} for the plants in the record, to say "You have this"."""
    sp, gn = {}, {}
    for code, sci in c.execute("SELECT code, scientific_name FROM plants WHERE status='active'"):
        m = re.match(r'^\s*([A-Z][a-z]+)(?:\s+([a-z][a-z\-]+))?', sci or '')
        if not m: continue
        gn.setdefault(m.group(1).lower(), []).append(code)
        if m.group(2) and m.group(2) not in ('sp', 'spp', 'x'): sp.setdefault((m.group(1) + ' ' + m.group(2)).lower(), []).append(code)
    return sp, gn

def mark_owned(c, items, key='scientific_name'):
    sp, gn = species_owned(c)
    for x in items:
        n = (x.get(key) or '').lower()
        x['yours'] = sp.get(n, []); x['yours_genus'] = [] if x['yours'] else gn.get(n.split(' ')[0], [])
    if items:                                     # 1.22.0: your wishlist and your tags, shown on the cards
        wish = {r[0].lower(): r[1] for r in c.execute('SELECT name, status FROM wishlist')}
        tags = {r[0].lower(): [t.strip() for t in r[1].split(',') if t.strip()] for r in c.execute("SELECT name, tags FROM species_notes WHERE tags<>''")}
        for x in items:
            n = (x.get(key) or '').lower()
            x['wish'] = wish.get(n); x['tags'] = tags.get(n, [])
    return items

@app.route('/api/identify', methods=['POST'])
def identify():
    """A picture (field 'image') in; the closest plants in the record and the likeliest species out (from this computer)."""
    scope = request.args.get('scope', 'common')
    if scope not in ID_SCOPES: scope = 'common'
    body, ct = multipart({}, [('image', 'picture.jpg', picture_bytes(1024), 'image/jpeg')])
    out = vision_call('/identify?scope=' + scope, body, ct, timeout=90)
    c = db()
    matches = []
    for m in out.get('matches', []):
        b = plant_brief(c, m['code'])
        if b: matches.append(b | {'score': m['score'], 'confidence': m.get('confidence'), 'matched_photo': m.get('photo')})
    out['matches'] = matches
    mark_owned(c, out.get('species', []))
    return jsonify(out)

@app.route('/api/identify/status')
def identify_status():
    try: st = vision_call('/status', timeout=5)
    except Exception as e:
        st = {'state': 'off', 'step': getattr(e, 'description', 'The picture checker is not running.')}
    c = db()
    st['plantnet'] = bool(setting(c, 'plantnet_key')); st['claude'] = bool(setting(c, 'claude_key'))
    return jsonify(st)

@app.route('/api/library')
def library():
    """Search the species list (?q=, &scope=texas|us|common|world)."""
    q, scope = request.args.get('q', '').strip()[:80], request.args.get('scope', 'world')
    if scope not in ID_SCOPES: scope = 'world'
    if len(q) < 2: return jsonify(results=[], total=0)
    out = vision_call('/names?' + urllib.parse.urlencode({'q': q, 'scope': scope, 'limit': 60}), timeout=30)
    mark_owned(db(), out.get('results', []))
    out['results'].sort(key=lambda x: (not x['yours'], not x['yours_genus']))      # yours first (a stable sort keeps the rest in order)
    return jsonify(out)

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
        if int(b.get('base_version', r['version'])) != r['version']:
            abort(409, f'Someone else changed {code} while you were editing. Reload the page to see their changes, then make yours again.')
        f, who, ch = b.get('fields') or {}, editor(), []
        for n in FUNGI_NAMES:
            if n not in f: continue
            v = fungi_norm(c, n, f[n])
            if (r[n] if r[n] is not None else '') != (v if v is not None else ''): ch.append((n, r[n], v))
        if ch:
            c.execute(f"UPDATE fungi_finds SET {', '.join(n + '=?' for n, _, _ in ch)}, version=version+1, updated_by=?, updated_at=? WHERE id=?",
                      [v for _, _, v in ch] + [who, now(), r['id']])
            for n, o, v in ch:
                audit_only(c, 'fungi', n, None if o is None else str(o)[:500], None if v is None else str(v)[:500], who, f'{code}: {FUNGI_LABEL[n]} changed', None, code)
            c.commit()
        return jsonify(find_dict(c, find_row(c, code)) | {'changed': len(ch)})
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
    c.commit()
    return jsonify(find_dict(c, find_row(c, code)) | {'added': added}), 201

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

# ---- library notes, tags and wishlist (shared with everyone who can open the app; viewers can read them)
@app.route('/api/library/notes', methods=['GET', 'PUT'])
def library_notes():
    c = db()
    if request.method == 'PUT':
        b = request.get_json(silent=True) or {}
        name = str(b.get('name') or '').strip()[:120]
        if not name: abort(400, 'Which species?')
        notes = str(b.get('notes') or '').strip()[:5000]
        tags = ', '.join(dict.fromkeys(t.strip().lower()[:40] for t in str(b.get('tags') or '').split(',') if t.strip()))[:500]
        old = c.execute('SELECT * FROM species_notes WHERE name=?', (name,)).fetchone()
        c.execute('INSERT OR REPLACE INTO species_notes(name,notes,tags,updated_by,updated_at) VALUES(?,?,?,?,?)', (name, notes, tags, editor(), now()))
        audit_only(c, 'library', 'notes', (old['notes'] + ' | ' + old['tags']) if old else None, notes + ' | ' + tags, editor(), f'Library notes for {name} saved')
        c.commit()
    name = request.args.get('name') or (request.get_json(silent=True) or {}).get('name') or ''
    if name:
        r = c.execute('SELECT * FROM species_notes WHERE name=?', (name.strip(),)).fetchone()
        return jsonify(dict(r) if r else {'name': name, 'notes': '', 'tags': ''})
    return jsonify(notes=[dict(r) for r in c.execute("SELECT * FROM species_notes WHERE notes<>'' OR tags<>'' ORDER BY name")],
                   tags=sorted({t.strip() for (x,) in c.execute('SELECT tags FROM species_notes') for t in x.split(',') if t.strip()}))

@app.route('/api/wishlist', methods=['GET', 'PUT', 'DELETE'])
def wishlist_api():
    c = db()
    if request.method in ('PUT', 'DELETE'):
        b = request.get_json(silent=True) or {}
        name = str(b.get('name') or request.args.get('name') or '').strip()[:120]
        if not name: abort(400, 'Which species?')
        old = c.execute('SELECT * FROM wishlist WHERE name=?', (name,)).fetchone()
        if request.method == 'DELETE':
            c.execute('DELETE FROM wishlist WHERE name=?', (name,))
            audit_only(c, 'library', 'wishlist', name, None, editor(), f'{name} taken off the wishlist')
        else:
            st = b.get('status', old['status'] if old else 'want')
            if st not in ('want', 'got'): abort(400, 'status must be want or got')
            vals = (str(b.get('common_name', old['common_name'] if old else '') or '')[:120], str(b.get('notes', old['notes'] if old else '') or '').strip()[:2000],
                    str(b.get('where_seen', old['where_seen'] if old else '') or '').strip()[:300], st)
            if old: c.execute('UPDATE wishlist SET common_name=?, notes=?, where_seen=?, status=?, updated_by=?, updated_at=? WHERE name=?', vals + (editor(), now(), name))
            else: c.execute('INSERT INTO wishlist(name,common_name,notes,where_seen,status,added_by,added_at) VALUES(?,?,?,?,?,?,?)', (name,) + vals + (editor(), now()))
            audit_only(c, 'library', 'wishlist', None, name, editor(), f'{name} ' + ('updated on the wishlist' if old else 'added to the wishlist'))
        c.commit()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishlist ORDER BY status='got', added_at DESC")]
    sp, _ = species_owned(c)
    for r in rows: r['yours'] = sp.get(r['name'].lower(), [])
    return jsonify(wishlist=rows)

# ---------------------------------------------------------------- 1.21.0: the library as a browsable knowledge base
# Names, classification and US states come from the picture checker (offline). Photos and the short description come from
# iNaturalist (CC-licensed photos by its members; the description is from Wikipedia), fetched once per species in the
# background, about one request a second as iNaturalist asks, and kept in data/library. Only species names are sent.
LIB_DIR = os.path.join(DATA_DIR, 'library')
INAT_URL = os.environ.get('PLANTDB_INAT_URL', 'https://api.inaturalist.org/v1').rstrip('/')
INAT_IMG_OK = tuple(x for x in os.environ.get('PLANTDB_INAT_IMG_OK', 'https://inaturalist-open-data.s3.amazonaws.com/,https://static.inaturalist.org/').split(',') if x)
LIB_RECHECK_DAYS = 30            # a species with no photo is looked up again after this many days
LIBQ = {'queue': [], 'set': set(), 'lock': threading.Lock(), 'thread': None, 'last': 0.0}

def lib_slug(name):
    return re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:120]

def lib_meta(name):
    p = os.path.join(LIB_DIR, lib_slug(name) + '.json')
    try:
        with open(p, encoding='utf-8') as f: return json.load(f)
    except (OSError, ValueError): return None

def lib_save(name, meta):
    os.makedirs(LIB_DIR, exist_ok=True)
    p = os.path.join(LIB_DIR, lib_slug(name) + '.json')
    with open(p + '.tmp', 'w', encoding='utf-8') as f: json.dump(meta, f)
    os.replace(p + '.tmp', p)

def lib_online(c=None):
    return setting(c or db(), 'library_online', '1') == '1'

def inat_get(path):
    """One iNaturalist API call, at most one a second (shared by every request)."""
    with LIBQ['lock']:
        wait = 1.05 - (time.time() - LIBQ['last'])
        if wait > 0: time.sleep(wait)
        LIBQ['last'] = time.time()
    req = urllib.request.Request(INAT_URL + path, headers={'User-Agent': f'plant-database/{APP_VERSION} (a home plant record)', 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=20) as r: return json.loads(r.read())

def lib_download(url, dest, big=1024):
    if not url.startswith(INAT_IMG_OK): raise ValueError('not an iNaturalist photo address')
    req = urllib.request.Request(url, headers={'User-Agent': f'plant-database/{APP_VERSION} (a home plant record)'})
    with urllib.request.urlopen(req, timeout=30) as r: raw = r.read(8_000_000)
    im = ImageOps.exif_transpose(Image.open(io.BytesIO(raw))); im = im.convert('RGB')
    im.thumbnail((big, big))
    im.save(dest + '.tmp', 'JPEG', quality=84, optimize=True); os.replace(dest + '.tmp', dest)

def inat_find(name):
    """The iNaturalist taxon with exactly this name, or None."""
    j = inat_get('/taxa?' + urllib.parse.urlencode({'q': name, 'is_active': 'true', 'per_page': 10, 'locale': 'en'}))
    for t in j.get('results') or []:
        if (t.get('name') or '').lower() == name.lower(): return t
    return None

def photo_meta(ph, file):
    return {'file': file, 'credit': ph.get('attribution') or '', 'license': (ph.get('license_code') or '').upper(),
            'page': f"https://www.inaturalist.org/photos/{ph['id']}" if ph.get('id') else ''}

def lib_fetch_photo(name):
    """Looks a species up on iNaturalist and keeps its main photo (and the basic facts) in data/library."""
    meta = lib_meta(name) or {}
    t = inat_find(name)
    meta.update(name=name, checked=date.today().isoformat(), taxon_id=t['id'] if t else None,
                inat_common=(t or {}).get('preferred_common_name') or '', observations=(t or {}).get('observations_count'),
                wikipedia_url=(t or {}).get('wikipedia_url') or '')
    ph = (t or {}).get('default_photo') or {}
    url = ph.get('medium_url') or ph.get('url')
    if url:
        f = lib_slug(name) + '.jpg'
        lib_download(url, os.path.join(LIB_DIR, f), big=640)
        meta['photo'] = photo_meta(ph, f)
    else:
        meta['photo'] = None
    lib_save(name, meta)
    return meta

def lib_worker():
    while True:
        with LIBQ['lock']:
            if not LIBQ['queue']: LIBQ['thread'] = None; return
            name = LIBQ['queue'].pop(0)
        try:                                                          # turned off since it was queued: stop
            c2 = sqlite3.connect(DB_PATH, timeout=10)
            try: online = lib_online(c2)
            finally: c2.close()
        except Exception: online = True
        if not online:
            with LIBQ['lock']: LIBQ['queue'].clear(); LIBQ['set'].clear(); LIBQ['thread'] = None
            return
        try: lib_fetch_photo(name)
        except Exception as e:
            print(f'[library] {name}: {e}', flush=True)
            lib_save(name, (lib_meta(name) or {}) | {'name': name, 'checked': date.today().isoformat(), 'photo': None, 'error': str(e)[:200]})
        finally:
            with LIBQ['lock']: LIBQ['set'].discard(name)

def lib_enqueue(names, front=True):
    """Queues species for a photo. Ones someone is looking at go first (front=True); a whole-list download goes last."""
    with LIBQ['lock']:
        if front:
            for n in reversed(names):
                if n in LIBQ['set']:
                    try: LIBQ['queue'].remove(n)
                    except ValueError: pass
                LIBQ['set'].add(n); LIBQ['queue'].insert(0, n)
        else:
            for n in names:
                if n not in LIBQ['set']: LIBQ['set'].add(n); LIBQ['queue'].append(n)
        if LIBQ['queue'] and not LIBQ['thread']:
            LIBQ['thread'] = threading.Thread(target=lib_worker, daemon=True); LIBQ['thread'].start()

PREFETCH = {'scope': None, 'names': set(), 'total': 0, 'started': None, 'by': None}

@app.route('/api/library/prefetch', methods=['GET', 'POST', 'DELETE'])
def library_prefetch():
    """1.22.0: download the photo and facts for every species in a list (Texas plants), so the library works offline.
    Owner only (OWNER_ONLY_CHANGES). It goes about one species a second, after anything someone is looking at."""
    c = db()
    if request.method == 'POST':
        if not lib_online(c): abort(409, 'Library photos are turned off. Turn them on first.')
        scope = (request.get_json(silent=True) or {}).get('scope', 'texas')
        if scope not in ('texas',): abort(400, 'Only the Texas list can be downloaded')
        names = vision_call('/scope_names?scope=' + scope, timeout=60).get('names', [])
        todo = []
        for n in names:
            m = lib_meta(n)
            if not (m and m.get('checked') and (m.get('photo') or (date.today() - date.fromisoformat(m['checked'])).days < LIB_RECHECK_DAYS)): todo.append(n)
        PREFETCH.update(scope=scope, names=set(todo), total=len(todo), started=now(), by=editor(), all=len(names))
        lib_enqueue(todo, front=False)
        audit_only(c, 'library', 'prefetch', None, f'{len(todo)} of {len(names)}', editor(), f'Download of the photos for the {scope.title()} list started ({len(todo)} to fetch)')
        c.commit()
    elif request.method == 'DELETE':
        with LIBQ['lock']:
            LIBQ['queue'] = [n for n in LIBQ['queue'] if n not in PREFETCH['names']]
            LIBQ['set'] -= PREFETCH['names']
        PREFETCH.update(names=set(), total=0)
    with LIBQ['lock']: left = len(PREFETCH['names'] & LIBQ['set'])
    return jsonify(scope=PREFETCH['scope'], total=PREFETCH['total'], left=left, done=PREFETCH['total'] - left, started=PREFETCH['started'],
                   by=PREFETCH['by'], all=PREFETCH.get('all'), running=left > 0, online=lib_online(c))

def lib_photo_state(name):
    """{'url', 'credit', ...} when kept, None when there is none, 'pending' while it is being fetched."""
    m = lib_meta(name)
    if m and m.get('photo'): return {'url': '/library-photos/' + m['photo']['file'], 'credit': m['photo']['credit'], 'license': m['photo']['license'], 'page': m['photo']['page']}
    fresh = m and m.get('checked') and (date.today() - date.fromisoformat(m['checked'])).days < LIB_RECHECK_DAYS
    if fresh or not lib_online(): return None
    return 'pending'

def owned_lists(c):
    sp, gn = species_owned(c)
    return '|'.join(sp), '|'.join(gn)

def own_photo(c, codes):
    for code in codes:
        b = plant_brief(c, code)
        if b and b['photo']: return '/thumbs/' + urllib.parse.quote(b['photo'])
    return None

@app.route('/api/library/browse')
def library_browse():
    """Every species in a list, filtered and sorted, a page at a time (see the picture checker's /browse)."""
    c, a = db(), request.args
    own, owngenus = owned_lists(c)
    q = {k: a.get(k, '')[:80] for k in ('scope', 'q', 'kind', 'family', 'genus', 'order', 'state', 'common', 'mine', 'sort', 'offset', 'limit')}
    if q['scope'] not in ID_SCOPES: q['scope'] = 'common'
    if q['mine'] == 'wish':                        # 1.22.0: your wishlist, your notes and tags (names sent as the "own" list)
        q.update(mine='species', own='|'.join(r[0] for r in c.execute('SELECT name FROM wishlist')), owngenus='')
    elif q['mine'] == 'notes':
        q.update(mine='species', own='|'.join(r[0] for r in c.execute("SELECT name FROM species_notes WHERE notes<>'' OR tags<>''")), owngenus='')
    elif q['mine'].startswith('tag:'):
        t = q['mine'][4:].strip().lower()
        q.update(mine='species', own='|'.join(n for n, tg in c.execute("SELECT name, tags FROM species_notes WHERE tags<>''") if t in [x.strip() for x in tg.split(',')]), owngenus='')
    elif q['mine']: q.update(own=own, owngenus=owngenus)
    if q['mine'] == 'species' and not q.get('own'): q['own'] = '-'           # an empty list matches nothing
    out = vision_call('/browse?' + urllib.parse.urlencode({k: v for k, v in q.items() if v}), timeout=30)
    mark_owned(c, out.get('results', []))
    for x in out['results']:
        x['own_photo'] = own_photo(c, x['yours']) if x['yours'] else None
    return jsonify(out)

@app.route('/api/library/facets')
def library_facets():
    scope = request.args.get('scope', 'common')
    return jsonify(vision_call('/facets?' + urllib.parse.urlencode({'scope': scope if scope in ID_SCOPES else 'common'}), timeout=30))

@app.route('/api/library/photos')
def library_photos():
    """?names=a|b|c: each one's photo, null when there is none, or "pending" while it is fetched in the background."""
    names = [n.strip() for n in request.args.get('names', '').split('|') if n.strip()][:150]
    out = {n: lib_photo_state(n) for n in names}
    if lib_online(): lib_enqueue([n for n, v in out.items() if v == 'pending'])
    return jsonify(photos=out, online=lib_online())

@app.route('/api/library/taxon')
def library_taxon():
    """One species in full, plus your plants of it and of its genus."""
    c, name = db(), request.args.get('name', '').strip()[:120]
    if not name: abort(400, 'Which species?')
    out = vision_call('/taxon?' + urllib.parse.urlencode({'name': name}), timeout=30)
    mark_owned(c, [out]); mark_owned(c, out.get('similar', []))
    out['your_plants'] = [plant_brief(c, x) for x in out['yours'] + out['yours_genus']]
    nt = c.execute('SELECT * FROM species_notes WHERE lower(name)=lower(?)', (out.get('scientific_name') or name,)).fetchone()
    out['notes'] = dict(nt) if nt else {'notes': '', 'tags': '', 'updated_by': None, 'updated_at': None}
    w = c.execute('SELECT * FROM wishlist WHERE lower(name)=lower(?)', (out.get('scientific_name') or name,)).fetchone()
    out['wishlist'] = dict(w) if w else None
    out['your_finds'] = [{'code': r['code'], 'name': r['name'], 'found_on': r['found_on'], 'id_status': r['id_status']}
                         for r in c.execute('SELECT * FROM fungi_finds WHERE lower(scientific_name)=lower(?) ORDER BY found_on DESC', (out.get('scientific_name') or name,))]
    m = lib_meta(name) or {}
    out['inat'] = {k: m.get(k) for k in ('inat_common', 'taxon_id', 'observations', 'wikipedia_url', 'summary', 'photos', 'detail_checked')}
    out['online'] = lib_online(c)
    return jsonify(out)

@app.route('/api/library/info', methods=['GET'])
def library_info():
    """The species' photos (up to 6) and short description, from iNaturalist, fetched on first view and then kept."""
    c, name = db(), request.args.get('name', '').strip()[:120]
    if not name: abort(400, 'Which species?')
    m = lib_meta(name) or {}
    fresh = m.get('detail_checked') and (date.today() - date.fromisoformat(m['detail_checked'])).days < LIB_RECHECK_DAYS
    if not fresh and lib_online(c):
        try:
            if 'taxon_id' not in m: m = lib_fetch_photo(name)
            if m.get('taxon_id'):
                t = (inat_get(f"/taxa/{int(m['taxon_id'])}?locale=en").get('results') or [{}])[0]
                summ = re.sub(r'<[^>]+>', '', t.get('wikipedia_summary') or '')
                photos = []
                for k, tp in enumerate((t.get('taxon_photos') or [])[:6]):
                    ph = tp.get('photo') or {}
                    url = (ph.get('medium_url') or ph.get('url') or '').replace('/medium.', '/large.')
                    if not url: continue
                    f = f'{lib_slug(name)}-{k + 1}.jpg'
                    try: lib_download(url, os.path.join(LIB_DIR, f)); photos.append(photo_meta(ph, f))
                    except Exception as e: print(f'[library] {name} photo {k + 1}: {e}', flush=True)
                m.update(summary=html_unescape(summ)[:3000], photos=photos, inat_common=t.get('preferred_common_name') or m.get('inat_common', ''),
                         observations=t.get('observations_count'), wikipedia_url=t.get('wikipedia_url') or m.get('wikipedia_url', ''))
            m['detail_checked'] = date.today().isoformat(); m.setdefault('name', name)
            lib_save(name, m)
        except Exception as e:
            return jsonify(error='Could not reach iNaturalist for the photos and description. They are tried again next time.', detail=str(e)[:200], online=True)
    return jsonify(summary=m.get('summary', ''), photos=[p | {'url': '/library-photos/' + p['file']} for p in (m.get('photos') or [])],
                   inat_common=m.get('inat_common', ''), observations=m.get('observations'), wikipedia_url=m.get('wikipedia_url', ''),
                   inat_url=f"https://www.inaturalist.org/taxa/{m['taxon_id']}" if m.get('taxon_id') else '', online=lib_online(c))

def html_unescape(t):
    import html as _h
    return _h.unescape(t).strip()

@app.route('/library-photos/<path:name>')
def library_photo_file(name):
    return send_from_directory(LIB_DIR, os.path.basename(name), max_age=86400)

@app.route('/api/library/settings', methods=['GET', 'PUT'])
def library_settings():
    """Whether the library may look up photos and descriptions on iNaturalist (owner only to change)."""
    c = db()
    if request.method == 'PUT':
        on = bool((request.get_json(silent=True) or {}).get('online'))
        set_setting(c, 'library_online', '1' if on else '0')
        audit_only(c, 'setting', 'library_online', None, 'on' if on else 'off', editor(), 'Library photos from iNaturalist turned ' + ('on' if on else 'off'))
        c.commit()
    return jsonify(online=lib_online(c))

def key_hint(k):
    return ('…' + k[-4:]) if k else ''

@app.route('/api/identify/settings', methods=['GET', 'PUT'])
def identify_settings():
    """The Pl@ntNet and Claude keys (owner only to change). The keys never leave the server: only their last 4 characters."""
    c = db()
    if request.method == 'PUT':
        b = request.get_json(silent=True) or {}
        for name, word in (('plantnet_key', 'Pl@ntNet'), ('claude_key', 'Claude')):
            if name not in b: continue
            k = str(b.get(name) or '').strip()
            if k and not re.match(r'^[A-Za-z0-9_\-]{10,200}$', k): abort(400, f'That does not look like a {word} key. Copy it again, without spaces.')
            set_setting(c, name, k)
            audit_only(c, 'setting', name, None, key_hint(k) or '(removed)', editor(), f'{word} key ' + ('saved' if k else 'removed'))
        c.commit()
    pk, ck = setting(c, 'plantnet_key', ''), setting(c, 'claude_key', '')
    return jsonify(plantnet=bool(pk), plantnet_hint=key_hint(pk), claude=bool(ck), claude_hint=key_hint(ck), claude_model=CLAUDE_MODEL)

def outside_call(url, data, headers, timeout=60):
    req = urllib.request.Request(url, data=data, headers=headers | {'User-Agent': 'plant-database (home garden record)'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read())
        except Exception: return e.code, {}
    except (urllib.error.URLError, OSError, TimeoutError):
        return 0, {}

@app.route('/api/identify/plantnet', methods=['POST'])
def identify_plantnet():
    """Second opinion from Pl@ntNet (free key: 500 pictures a day). Pl@ntNet does not keep the pictures, by its terms."""
    c = db()
    key = setting(c, 'plantnet_key', '')
    if not key: abort(400, 'Pl@ntNet is not set up. The owner can save a key on the Identify page, under "Second opinions".')
    body, ct = multipart({'organs': 'auto'}, [('images', 'picture.jpg', picture_bytes(1280), 'image/jpeg')])
    url = PLANTNET_URL + '?' + urllib.parse.urlencode({'api-key': key, 'lang': 'en', 'nb-results': 5, 'include-related-images': 'false'})
    st, j = outside_call(url, body, {'Content-Type': ct})
    if st == 404: return jsonify(species=[], note='Pl@ntNet did not recognise a plant in that picture.')
    if st in (401, 403): abort(502, 'Pl@ntNet refused the key. Check it on my.plantnet.org and save it again.')
    if st == 429: abort(502, 'The Pl@ntNet key has used all of today\'s pictures. It resets tomorrow.')
    if st != 200: abort(502, 'Could not reach Pl@ntNet. Check the internet connection and try again.')
    out = []
    for r in (j.get('results') or [])[:5]:
        sp = r.get('species') or {}
        out.append({'scientific_name': sp.get('scientificNameWithoutAuthor', ''), 'author': sp.get('scientificNameAuthorship', ''),
                    'genus': (sp.get('genus') or {}).get('scientificNameWithoutAuthor', ''), 'family': (sp.get('family') or {}).get('scientificNameWithoutAuthor', ''),
                    'common_name': ', '.join((sp.get('commonNames') or [])[:3]), 'probability': round(float(r.get('score') or 0), 3)})
    mark_owned(c, out)
    return jsonify(species=out, remaining=j.get('remainingIdentificationRequests'), source='Pl@ntNet')

CLAUDE_ASK = ('Identify the plant in this photo. It is one of the potted or garden plants of a home grower in Round Rock, Texas '
              '(USDA zone 8b/9a). Reply with JSON only, no other text: {"plant": true or false (is there a plant in the photo), '
              '"guesses": [up to 3 of {"scientific_name": "Genus species", "common_name": "...", "family": "...", '
              '"probability": 0 to 1, "why": "one short sentence on the features you used"}], '
              '"photo_tip": "one short sentence on what photo would make you surer, or empty"}')

@app.route('/api/identify/claude', methods=['POST'])
def identify_claude():
    """Second opinion from Claude, with the owner's Anthropic API key (paid per picture, a cent or two)."""
    import base64
    c = db()
    key = setting(c, 'claude_key', '')
    if not key: abort(400, 'Claude is not set up. The owner can save an Anthropic API key on the Identify page, under "Second opinions".')
    pic = base64.b64encode(picture_bytes(1280)).decode()
    body = json.dumps({'model': CLAUDE_MODEL, 'max_tokens': 800, 'messages': [{'role': 'user', 'content': [
        {'type': 'image', 'source': {'type': 'base64', 'media_type': 'image/jpeg', 'data': pic}}, {'type': 'text', 'text': CLAUDE_ASK}]}]}).encode()
    st, j = outside_call(CLAUDE_URL, body, {'Content-Type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01'}, timeout=90)
    if st in (401, 403): abort(502, 'Anthropic refused the key. Check it at console.anthropic.com and save it again.')
    if st == 429 or st == 529: abort(502, 'Claude is busy or the key has reached its limit. Try again in a minute.')
    if st != 200: abort(502, 'Could not reach Claude. Check the internet connection and try again.')
    text = ''.join(b.get('text', '') for b in j.get('content', []) if b.get('type') == 'text')
    m = re.search(r'\{.*\}', text, re.S)
    try: a = json.loads(m.group(0)) if m else {}
    except ValueError: a = {}
    out = [{'scientific_name': str(x.get('scientific_name', ''))[:120], 'common_name': str(x.get('common_name', ''))[:120], 'family': str(x.get('family', ''))[:80],
            'probability': max(0.0, min(1.0, float(x.get('probability') or 0))), 'why': str(x.get('why', ''))[:300]}
           for x in (a.get('guesses') or [])[:3] if isinstance(x, dict)]
    mark_owned(c, out)
    return jsonify(species=out, plant=a.get('plant', True), tip=str(a.get('photo_tip', ''))[:300], source='Claude (' + CLAUDE_MODEL + ')',
                   note='' if out or a else 'Claude did not give an answer this could read. Try again.')

# ---------------------------------------------------------------- api: plants
@app.route('/api/plants')
def list_plants():
    c = db()
    q = request.args.get('q', '').strip().lower()
    status = request.args.get('status', 'active')          # 'active', 'archived', or 'all' (1.16.2: both, for the Status filter)
    rows = c.execute('SELECT * FROM plants ORDER BY code').fetchall() if status == 'all' else c.execute('SELECT * FROM plants WHERE status=? ORDER BY code', (status,)).fetchall()
    open_req = {k: n for k, n in c.execute('SELECT plant_code, COUNT(*) FROM requests WHERE done=0 AND plant_code IS NOT NULL GROUP BY plant_code')}
    spots = plant_spots(c)
    out = []
    for r in rows:
        hay = ' '.join(str(r[n] or '') for n in ('code', 'common_name', 'scientific_name', 'aliases', 'location', 'container', 'plant_type', 'notes')).lower()
        if q and q not in hay: continue
        files = [x[0] for x in c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id', (r['id'],))]
        p = {'file': files[0]} if files else None
        pn, pat = c.execute('SELECT COUNT(*), MAX(added_at) FROM photos WHERE plant_id=?', (r['id'],)).fetchone()
        out.append({'code': r['code'], 'common_name': r['common_name'], 'scientific_name': r['scientific_name'], 'plant_type': r['plant_type'],
                    'location': r['location'], 'aliases': r['aliases'], 'id_confidence': r['id_confidence'], 'winter_plan': r['winter_plan'], 'health_rating': r['health_rating'],
                    'site': r['site'] or 'Outdoors', 'version': r['version'], 'updated_at': r['updated_at'], 'updated_by': r['updated_by'], 'photo': p['file'] if p else None,
                    'temp_damage_below': r['temp_damage_below'], 'temp_ideal_low': r['temp_ideal_low'], 'temp_ideal_high': r['temp_ideal_high'],
                    'fert_from_month': r['fert_from_month'], 'fert_to_month': r['fert_to_month'], 'fert_every_days': r['fert_every_days'], 'fertilizer': r['fertilizer'],
                    'requests_open': open_req.get(r['code'], 0), 'status': r['status'],
                    # 1.17.0: for the filters on the Plants page
                    'dli_low': r['dli_low'], 'dli_high': r['dli_high'], 'zone_low': r['zone_low'], 'pet_safety': r['pet_safety'] or '',
                    'leaf_type': r['leaf_type'] or '', 'pot_size': r['pot_size'] or '', 'photo_count': pn, 'photo_at': pat,
                    'light_spot': spots.get(r['code']),
                    'photos': files})                      # 1.20.0: every photo, main photo first, to browse on the Plants page
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

# ---------------------------------------------------------------- copy my answers for Claude (added in 1.8.0)
FC_KEY = 'claude_copied_at'                       # settings: when the message was last copied or saved
FC_EPOCH = '1970-01-01T00:00:00Z'
FC_PAGE = ('create', 'update', 'edit', 'restore', 'archive', 'unarchive')
FC_PHOTO = ('photo_add', 'photo_assign', 'photo_move', 'photo_remove', 'photo_caption', 'photo_primary')
FC_CARE = ('fertilizer', 'care', 'frost')         # care and frost come from the watering and frost prototypes, if merged

def fc_person(who):
    """Changes made by people. Upgrade batches and the first import are signed "Claude (...)" and Claude knows those."""
    return not (who or '').startswith('Claude')

def fc_when(c, ts, with_time=True):
    """'2026-10-23T20:40:00Z' -> 'Friday, Oct 23, 3:40 PM', in the home place's time zone."""
    d = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(tzinfo(location(c)['tz']))
    day = f'{d:%A}, {d:%b} {d.day}'
    return day + f', {d.hour % 12 or 12}:{d:%M} {"AM" if d.hour < 12 else "PM"}' if with_time else day

def fc_clip(v, n=300):
    v = re.sub(r'\s+', ' ', str(v if v is not None else '')).strip()
    return v if len(v) <= n else v[:n - 1].rstrip() + '…'

def fc_since(c, rng):
    if rng in ('7', '30'): return (datetime.now(timezone.utc) - timedelta(days=int(rng))).strftime('%Y-%m-%dT%H:%M:%SZ')
    if rng == 'all': return FC_EPOCH
    return setting(c, FC_KEY) or FC_EPOCH        # 'last': since it was last copied, or everything the first time

def for_claude_message(c, since, until, with_open=False):
    """The message to paste into the chat: what people did since `since` (answers first), as plain text."""
    names = {r['code']: r['common_name'] for r in c.execute('SELECT code, common_name FROM plants')}
    nm = lambda code: f'{code} {names.get(code, "")}'.strip() if code else 'General'
    cap = {r['file']: r['caption'] for r in c.execute('SELECT file, caption FROM photos')}
    out, n = [], {'answers': 0, 'pages': 0, 'photos': 0, 'care': 0, 'todo': 0}

    ans = [r for r in c.execute('SELECT * FROM requests WHERE done=1 AND done_at > ? AND done_at <= ? ORDER BY plant_code IS NULL, plant_code, done_at',
                                (since, until)) if fc_person(r['done_by'])]
    if ans:
        n['answers'] = len(ans)
        out.append(f'Answers ({len(ans)}):')
        for r in ans:
            out += [f'- {nm(r["plant_code"])} ({fc_when(c, r["done_at"])})', f'  Asked: {fc_clip(r["text"], 800)}',
                    f'  Answer: {fc_clip(r["answer"], 2000)}' if r['answer'] and r['answer'] != 'Done' else '  Marked done, with no answer written.']
        out.append('')

    log = [a for a in c.execute('SELECT * FROM audit_log WHERE changed_at > ? AND changed_at <= ? ORDER BY id', (since, until)) if fc_person(a['changed_by'])]

    pages = {}                                     # one entry per save: same plant, time, note and action
    for a in log:
        if a['action'] in FC_PAGE and a['plant_code']: pages.setdefault((a['plant_code'], a['changed_at'], a['note'] or '', a['action']), []).append(a)
    if pages:
        n['pages'] = len(pages)
        out.append(f'Changes to plant pages ({len(pages)}):')
        for (code, ts, note, act), rows in pages.items():
            if act == 'create': out.append(f'- New page: {nm(code)} ({fc_when(c, ts)})'); continue
            out.append(f'- {nm(code)} ({fc_when(c, ts)})' + (f': {fc_clip(note, 300)}' if note else ''))
            for a in rows:
                if not a['field']: continue
                label = FIELD_LABEL.get(a['field']) or a['field'].replace('_', ' ').capitalize()
                old, new = fc_clip(a['old_value'], 1000), fc_clip(a['new_value'], 1000)
                if len(old) <= 60 and len(new) <= 60: out.append(f'  {label}: from {old or "(empty)"} to {new or "(empty)"}')
                else: out.append(f'  {label}, now: {new or "(empty)"}')
        out.append('')

    ph = {}                                        # per plant (None = the Photos page, no plant)
    for a in log:
        if a['action'] not in FC_PHOTO: continue
        p = ph.setdefault(a['plant_code'], {'added': [], 'in': [], 'out': [], 'removed': 0, 'captions': 0, 'main': 0})
        if a['action'] == 'photo_add': p['added'].append(a['new_value'])
        elif a['action'] == 'photo_assign': p['in'].append((a['old_value'] or '').replace('from ', '', 1))
        elif a['action'] == 'photo_move': p['out'].append((a['new_value'] or '').replace('moved to ', '', 1))
        elif a['action'] == 'photo_remove': p['removed'] += 1
        elif a['action'] == 'photo_caption': p['captions'] += 1
        elif a['action'] == 'photo_primary': p['main'] += 1
    if ph:
        n['photos'] = len(ph)
        out.append('Photos:')
        for code, p in sorted(ph.items(), key=lambda x: (x[0] is None, x[0] or '')):
            bits = []
            if p['added']:
                caps = [f'"{fc_clip(cap.get(f), 80)}"' for f in p['added'] if cap.get(f)]
                bits.append(f'{len(p["added"])} photo{"s" if len(p["added"]) > 1 else ""} ' + ('uploaded without a plant' if code is None else 'added')
                            + (f' ({", ".join(caps[:6])})' if caps else ''))
            if p['in']: bits.append(f'{len(p["in"])} moved here from ' + ', '.join(sorted(set(x if x.startswith('P-') else 'the Photos page' for x in p['in']))))
            if p['out']: bits.append(f'{len(p["out"])} moved to ' + ', '.join(sorted(set(x if x.startswith('P-') else 'the Photos page' for x in p['out']))))
            if p['removed']: bits.append(f'{p["removed"]} removed')
            if p['captions']: bits.append(f'{p["captions"]} caption{"s" if p["captions"] > 1 else ""} edited')
            if p['main']: bits.append('main photo changed')
            out.append(f'- {"Photos page" if code is None else nm(code)}: ' + '; '.join(bits))
        if any(p['added'] for p in ph.values()):
            out.append("  The photos themselves can't go in this message. Attach the ones you want me to look at, or send a backup made with photos.")
        out.append('')

    care = {}                                      # same note on the same day for several plants reads as one line
    for a in log:
        if a['action'] in FC_CARE: care.setdefault((fc_when(c, a['changed_at'], False), a['note'] or a['action']), []).append(a['plant_code'])
    if care:
        n['care'] = sum(len(v) for v in care.values())
        out.append('Feeding and care:')
        for (day, note), codes in care.items():
            codes = sorted(set(x for x in codes if x))
            who = ', '.join(nm(x) for x in codes) if len(codes) <= 3 else ', '.join(codes)
            out.append(f'- {day}: {fc_clip(note, 300)}' + (f' ({who})' if who else ''))
        out.append('')

    todo = [a for a in log if a['action'] == 'todo']
    if todo:
        n['todo'] = len(todo)
        out.append('"Still to photograph" list:')
        out += [f'- {fc_clip(a["note"], 300)}' for a in todo]
        out.append('')

    open_req = c.execute('SELECT * FROM requests WHERE done=0 ORDER BY plant_code IS NULL, plant_code, id').fetchall()
    open_todo = c.execute('SELECT * FROM to_photograph WHERE done=0 ORDER BY id').fetchall()
    if with_open and (open_req or open_todo):
        out.append(f'Still open ({len(open_req)} requests, {len(open_todo)} to photograph):')
        out += [f'- {nm(r["plant_code"])}: {fc_clip(r["text"], 300)}' for r in open_req]
        out += [f'- To photograph: {fc_clip(t["label"], 200)}' + (f' ({fc_clip(t["note"], 200)})' if t['note'] else '') for t in open_todo]
        out.append('')
    elif open_req or open_todo:
        out.append(f'Still open: {len(open_req)} request{"" if len(open_req) == 1 else "s"} and {len(open_todo)} thing{"" if len(open_todo) == 1 else "s"} to photograph.')
        out.append('')

    span = 'everything so far' if since == FC_EPOCH else f'{fc_when(c, since)} to {fc_when(c, until)}'
    head = [f'Plant record update for Claude (version {APP_VERSION})', f'Covers {span}.', '']
    if not any(n.values()): head.append('Nothing new from me in that time.\n')
    return '\n'.join(head + out).rstrip() + '\n', n, {'requests': len(open_req), 'todo': len(open_todo)}

@app.route('/api/for-claude')
def for_claude():
    c = db()
    rng = request.args.get('range', 'last')
    if rng not in ('last', '7', '30', 'all'): abort(400, "range must be last, 7, 30 or all")
    since, until, last = fc_since(c, rng), now(), setting(c, FC_KEY)
    text, counts, still = for_claude_message(c, since, until, request.args.get('open') == '1')
    return jsonify(range=rng, since=since, until=until, last_copied=last, last_copied_words=fc_when(c, last) if last else None,
                   text=text, counts=counts, still_open=still)

@app.route('/api/for-claude.txt')
def for_claude_txt():
    c = db()
    rng = request.args.get('range', 'last')
    if rng not in ('last', '7', '30', 'all'): abort(400, "range must be last, 7, 30 or all")
    text = for_claude_message(c, fc_since(c, rng), now(), request.args.get('open') == '1')[0]
    name = 'plant-record-for-claude-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M') + '.txt'
    return Response(text, mimetype='text/plain; charset=utf-8', headers={'Content-Disposition': f'attachment; filename={name}'})

@app.route('/api/for-claude/copied', methods=['POST'])
def for_claude_copied():
    """Remember that the message up to `until` has been copied or saved, so next time starts from there."""
    c = db()
    until = str((request.get_json(silent=True) or {}).get('until') or now())
    if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$', until) or until > now(): abort(400, 'until must be a time that has passed, like 2026-10-23T20:40:00Z')
    old = setting(c, FC_KEY)
    if not old or until > old:
        set_setting(c, FC_KEY, until)
        audit_only(c, 'setting', FC_KEY, old, until, editor(), 'Copied my answers for Claude')
        c.commit()
    return jsonify(last_copied=setting(c, FC_KEY), last_copied_words=fc_when(c, setting(c, FC_KEY)))

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

# ---------------------------------------------------------------- back outside in spring (prototype: proto/move-outside)
# Plants that are inside now (Indoors, Garage or shed), and whether the nights in the 7-day forecast are warm enough for each
# to go back out. Levels, best first:
#   ready  every night at or above the plant's ideal low
#   safe   no night within FROST_MARGIN of its damage point, but some nights cooler than it likes
#   early  the forecast is safe, but the place's weather history says colder nights usually still come at this time of year
#   wait   a night in the forecast is below its damage point, or within FROST_MARGIN of it
# Reads only; moving a plant uses the existing /api/plants/<code>/site.
BO_LEVELS = ('ready', 'safe', 'early', 'wait')
BO_LOWS = {}                 # place id -> (time worked out, {date: low})

def bo_daily_lows(c, L):
    hit = BO_LOWS.get(L['id'])
    if hit and time.time() - hit[0] < 6 * 3600: return hit[1]
    try: rows = c.execute("SELECT date, json_extract(data, '$.temperature_2m_min') FROM weather_daily WHERE loc_id=? AND kind='observed'", (L['id'],)).fetchall()
    except sqlite3.OperationalError:            # an SQLite without JSON functions
        rows = [(d, (json.loads(x) if x else {}).get('temperature_2m_min')) for d, x in c.execute("SELECT date, data FROM weather_daily WHERE loc_id=? AND kind='observed'", (L['id'],))]
    lows = {d: t for d, t in rows if isinstance(t, (int, float))}
    BO_LOWS[L['id']] = (time.time(), lows)
    return lows

def bo_md(d):
    """A date as 'MM-DD' (Feb 29 counts as Feb 28), so days of different years compare."""
    return '02-28' if d[5:] == '02-29' else d[5:]

def bo_usual(lows, t):
    """From the daily history, for nights below t°F: the day after the last one each spring (January to June) and the first one
    each autumn (July to December). Medians over the years with enough days (150 in that half), and the latest spring date.
    None for a half with fewer than 3 such years. A spring with no night below t counts as '01-01'; autumn medians only count
    years that had one, and need at least half the years to have one."""
    halves = {}
    for d, v in lows.items():
        y, m = int(d[:4]), int(d[5:7])
        halves.setdefault((y, 'spring' if m <= 6 else 'autumn'), []).append((d, v))
    spring, autumn, years_a = [], [], 0
    for (y, h), vals in halves.items():
        if len(vals) < 150: continue
        cold = sorted(d for d, v in vals if v < t)
        if h == 'spring':
            if not cold: spring.append('01-01')
            else:
                nxt = (datetime.strptime(cold[-1], '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                spring.append(bo_md(nxt) if nxt[5:7] <= '06' else '07-01')
        else:
            years_a += 1
            if cold: autumn.append(bo_md(cold[0]))
    med = lambda xs: sorted(xs)[(len(xs) - 1) // 2] if xs else None
    out = {}
    if len(spring) >= 3:
        out |= {'safe': med(spring), 'safe_latest': max(spring), 'spring_years': len(spring), 'spring_cold': sum(1 for x in spring if x != '01-01')}
    if years_a >= 3:
        out |= {'first': med(autumn) if len(autumn) * 2 >= years_a else None, 'autumn_years': years_a}
    return out or None

BO_PORCH_DAYS = 7           # a week on the porch, out of full sun, before the move to the summer spot

def bo_porch_state(c):
    try: return json.loads(setting(c, 'bo_porch', '{}') or '{}')
    except ValueError: return {}

def bo_porch_list(c, today, photo):
    """Plants moved to the porch with "Moved to the porch" that are still on it, and when each is due its move to the summer spot."""
    out = []
    for code, v in sorted(bo_porch_state(c).items()):
        r = c.execute("SELECT * FROM plants WHERE code=? AND status='active'", (code,)).fetchone()
        if not r or r['site'] != 'Covered porch': continue          # it has moved on: nothing to remind about
        try: on = datetime.strptime(v.get('on', ''), '%Y-%m-%d').date()
        except ValueError: continue
        due = on + timedelta(days=BO_PORCH_DAYS)
        out.append({'code': code, 'name': r['common_name'], 'photo': photo(r['id']), 'on': on.isoformat(), 'due': due.isoformat(),
                    'days': (today - on).days, 'is_due': today >= due, 'by': v.get('by')})
    out.sort(key=lambda p: (p['due'], p['code']))
    return out

def outside_report(c):
    L = location(c)
    fc = loc_json(c, L['id'], 'forecast')
    today = local_today(c)
    td, tmd = today.isoformat(), bo_md(today.isoformat())
    nights = [{'date': d['date'], 'low': d['low']} for d in (fc.get('days') or []) if d.get('date', '') >= td and d.get('low') is not None][:7]
    spring = today.month <= 6
    lows = bo_daily_lows(c, L)
    usual_at = {}
    photo = lambda pid: (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (pid,)).fetchone() or [None])[0]
    rows = c.execute("SELECT * FROM plants WHERE status='active' ORDER BY code").fetchall()
    out = []
    for r in rows:
        if (r['site'] or 'Outdoors') not in INSIDE_SITES: continue
        dmg, ideal = r['temp_damage_below'], r['temp_ideal_low']
        p = {'code': r['code'], 'name': r['common_name'], 'photo': photo(r['id']), 'site': r['site'], 'plan': r['winter_plan'],
             'damage': dmg, 'lethal': r['temp_lethal_below'], 'ideal': ideal, 'level': None}
        if dmg is None and ideal is None: out.append(p); continue
        safe_at = dmg + FROST_MARGIN if dmg is not None else ideal
        like = ideal if ideal is not None and ideal > safe_at else safe_at
        if safe_at not in usual_at: usual_at[safe_at] = bo_usual(lows, safe_at)
        u = usual_at[safe_at]
        p |= {'safe_at': safe_at, 'like': like, 'usual': u}
        if not nights: out.append(p); continue
        cold = next((n for n in nights if n['low'] < safe_at), None)
        cool = [n for n in nights if n['low'] < like]
        p |= {'coldest': min(nights, key=lambda n: (n['low'], n['date'])), 'first_cold': cold, 'cool_nights': len(cool)}
        if cold: p['level'] = 'wait'
        else:
            p['level'] = 'safe' if cool else 'ready'
            if u and spring and u.get('safe') and tmd < u['safe']:
                p |= {'level': 'early', 'why': 'spring'}
            elif u and not spring and u.get('first') and tmd >= bo_md((datetime.strptime('2001-' + u['first'], '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')):
                p |= {'level': 'early', 'why': 'autumn'}
        out.append(p)
    porch = bo_porch_list(c, today, photo)
    rank = {k: i for i, k in enumerate(BO_LEVELS)}
    out.sort(key=lambda p: (rank.get(p['level'], 9), (p['name'] or '').lower(), p['code']))
    return {'place': L['name'], 'fetched_at': fc.get('fetched_at'), 'today': td, 'season': 'spring' if spring else 'autumn', 'margin': FROST_MARGIN,
            'nights': nights, 'plants': out, 'porch': porch, 'history_days': len(lows),
            'counts': {k: sum(1 for p in out if p['level'] == k) for k in BO_LEVELS} | {'unknown': sum(1 for p in out if not p['level'])}}

@app.route('/api/outside')
def outside_api():
    return jsonify(outside_report(db()))

@app.route('/api/outside/porch', methods=['POST'])
def outside_porch():
    """'start': move a plant to the covered porch (out of full sun, so leaves that grew indoors do not scorch) and remind
    in a week; 'clear': leave it on the porch and stop the reminder. Leaving the porch needs nothing: the reminder follows the Location."""
    c = db()
    b = request.get_json(silent=True) or {}
    r = plant_row(c, str(b.get('code', '')))
    act = b.get('action')
    if act not in ('start', 'clear'): abort(400, "action must be 'start' or 'clear'")
    keep = {k: v for k, v in bo_porch_state(c).items() if k != r['code']}
    if act == 'start':
        apply_changes(c, r, {'site': 'Covered porch'}, editor(), 'update', 'Moved to covered porch (sun protection first)')
        keep[r['code']] = {'on': local_today(c).isoformat(), 'by': editor()}
    else:
        audit_only(c, 'care', 'porch', None, 'stay', editor(), 'Staying on the porch: reminder to move it to its summer spot turned off', r['id'], r['code'])
    set_setting(c, 'bo_porch', json.dumps(keep))
    c.commit()
    return jsonify(outside_report(c))

# ---------------------------------------------------------------- getting plants ready to come inside (added in 1.9.0)
# Ten ways to keep outdoor pests out of the house, rated for each plant from what is chosen on its page (leaf type,
# pot size, pests found) and what the app knows (health, how dry it likes its soil, the pests it often gets, the weather).
PREP_METHODS = [
    {'key': 'inspect', 'title': 'Inspect for pests', 'steps': [
        'Look at the undersides of the leaves, where the leaves join the stems, and the new growth.',
        'Run your fingers over the leaves. Sticky leaves mean aphids, scale or mealybugs are feeding.',
        'Mite check: hold a white sheet of paper under the leaves and tap the plant. Specks that crawl are mites.',
        'Lift the pot and look underneath it and in the saucer.',
        'Use your phone camera\'s zoom or a lighted magnifier, or send Claude close-up photos of the leaf undersides.',
        'Tick what you found under "Pests you found" on the plant\'s page. If you found nothing, tick nothing: the other methods still work as a precaution.']},
    {'key': 'potclean', 'title': 'Clean the pot and saucer', 'steps': [
        'Wear gloves: in Central Texas, bark scorpions hide under pots.',
        'Lift the pot, look underneath, and knock off anything clinging to the bottom.',
        'Scrub the outside of the pot, the bottom and the drainage holes with soapy water and a brush.',
        'Empty and wash the saucer, and check under the rim of the pot.']},
    {'key': 'rinse', 'title': 'Rinse with water', 'steps': [
        'Do it outdoors in the morning, so the leaves dry by evening.',
        'Spray the plant hard with the hose: the undersides of the leaves first, then the tops and the stems.',
        'Hold delicate stems while you spray, and let the pot drain.']},
    {'key': 'wipe', 'title': 'Wipe the leaves', 'steps': [
        'Dip a soft cloth in lukewarm water with a drop of mild dish soap, and wring it out.',
        'Support each leaf with one hand and wipe the top, then the underside, from the stem to the tip.',
        'Rinse the cloth often, then wipe the leaves again with plain water.',
        'This also removes dust, so the leaves get more light indoors.']},
    {'key': 'soap', 'title': 'Spray insecticidal soap', 'repeat': True, 'steps': [
        'Use a ready-to-use insecticidal soap (potassium salts of fatty acids), or mix a concentrate as its label says.',
        'Test it on one leaf first and wait 2 days. If that leaf turns brown, use another method.',
        'Spray in the shade, between 50 and 90°F, until the tops and undersides of the leaves are wet. It only kills the pests it touches.',
        'Spray again every 5 to 7 days, 2 or 3 times in all, because it does not kill eggs.',
        'Press "Done today" after each round, and the Today page reminds you of the next one.']},
    {'key': 'oil', 'title': 'Spray horticultural or neem oil', 'repeat': True, 'steps': [
        'Use it outdoors only (neem oil smells), in the shade, between 50 and 90°F, and never on a plant that is dry or wilting.',
        'Test it on one leaf first and wait 2 days.',
        'Mix it as its label says and wet every surface, especially the stems and the undersides of the leaves, where scale and eggs sit.',
        'Spray again in 7 to 10 days if you still find live scale.']},
    {'key': 'alcohol', 'title': 'Dab with rubbing alcohol', 'steps': [
        'Dip a cotton swab in 70% rubbing alcohol.',
        'Touch each mealybug or scale insect with it. Scale may need a gentle scrape with a fingernail afterwards.',
        'On soft or thin leaves, test one spot first and wait a day.',
        'Check again every few days and dab any new ones.']},
    {'key': 'soak', 'title': 'Soak the pot', 'steps': [
        'Outdoors, choose a bucket or tub a little wider than the pot. Plain water works.',
        'Lower the pot in until the water just covers the soil.',
        'Leave it for 15 to 30 minutes. Ants, pill bugs and earwigs climb out or drown.',
        'If they are fire ants, wear gloves and stand back: they swarm up the pot.',
        'Lift it out and let it drain completely. This counts as a watering, so the watering reminder starts again from today.']},
    {'key': 'topsoil', 'title': 'Refresh the top of the soil', 'steps': [
        'Let the top of the soil dry a little first.',
        'Scrape off the top 1 to 2 inches of soil with a spoon, away from the stems, and bag it for the trash.',
        'Fill back up with fresh bagged potting mix, or with coarse sand or grit, which fungus gnats cannot lay eggs in.',
        'Water lightly.']},
    {'key': 'repot', 'title': 'Repot in fresh soil', 'steps': [
        'Water the plant the day before.',
        'Outdoors, slide the plant out of its pot and gently tease the old soil off the roots. Bag the old soil for the trash.',
        'Rinse the roots in a bucket of water. White cottony patches are root mealybugs. Trim mushy, dark roots with clean scissors.',
        'Use a new pot, or clean the old one without bleach: scrub it with hot soapy water and a brush, rinse it, and let it dry in the sun for a day. '
        'For extra cleaning, soak it for 10 minutes in 3% hydrogen peroxide from the pharmacy, straight from the bottle, then rinse. Never mix peroxide with vinegar or other cleaners.',
        'Repot in fresh bagged potting mix that suits the plant (see its Water and soil section), and water it in.',
        'Keep it out of strong light for a week while the roots recover.']},
]
PREP_KEYS = [m['key'] for m in PREP_METHODS]
PREP_TITLE = {m['key']: m['title'] for m in PREP_METHODS}
PREP_RANK = {'Best': 4, 'Good': 3, 'Use with care': 2, 'Not needed': 1, 'Not for this plant': 0}
PREP_WINDOW_DAYS = 75           # prep steps logged within this many days count towards this move inside
KEEP_APART_DAYS = 21            # keep plants that came in apart from long-term houseplants this long
KEEP_APART_AFTER_TREATMENT = 14
SOFT_PESTS = {'Spider mites', 'Mealybugs', 'Aphids', 'Whiteflies', 'Thrips'}
SOIL_PESTS = {'Ants', 'Pill bugs or earwigs', 'Slugs or snails'}

def prep_weather(c):
    """Today's forecast high and low at home, and what that means for spraying."""
    try:
        fc = loc_json(c, location(c)['id'], 'forecast')
        today = local_today(c).isoformat()
        d = next((x for x in (fc.get('days') or []) if x.get('date') == today), None)
    except Exception:
        d = None
    if not d or d.get('high') is None: return {'high': None, 'low': None, 'spray': None}
    hi, lo = round(d['high']), round(d['low']) if d.get('low') is not None else None
    if hi >= 90: note = f'Today reaches {hi}°F: spray early in the morning or in the evening, in the shade, or wait for a cooler day.'
    elif hi < 55: note = f'Today only reaches {hi}°F: sprays work poorly in the cold, so wait for a day between 55 and 90°F if you can.'
    else: note = f'Today ({lo}°F to {hi}°F) is fine for spraying in the shade.' if lo is not None else f'Today (up to {hi}°F) is fine for spraying in the shade.'
    return {'high': hi, 'low': lo, 'spray': note}

def prep_rate(r, pests, wx):
    """Each method's rating and the reason, in plain words, for one plant."""
    lt, ps = r['leaf_type'] or '', r['pot_size'] or ''
    watch = ' '.join(x.lower() for x in (r['pests_watch'] or '').split('\n'))
    weak = r['health_rating'] in ('Poor', 'Critical')
    succ, fern, fuzzy, palm, water, big = (lt == 'Succulent or cactus', lt == 'Fern fronds', lt == 'Fuzzy or velvety leaves',
                                           lt == 'Palm fronds', lt == 'Grows in water', lt == 'Large leaves')
    dry = succ or (r['soil_moisture_high'] is not None and r['soil_moisture_high'] <= 35)
    soft, soil = sorted(pests & SOFT_PESTS, key=PESTS.index), sorted(pests & SOIL_PESTS, key=PESTS.index)
    words = lambda xs: ', '.join(xs[:-1]) + ' and ' + xs[-1] if len(xs) > 1 else (xs[0] if xs else '')
    lower = lambda xs: words([x.lower() for x in xs])
    mites_prone = 'spider mite' in watch or palm
    out = {}
    def put(k, rating, reason): out[k] = (rating, reason)

    put('inspect', 'Best', 'Do this first: what you find decides which of the other methods are needed.')
    put('potclean', 'Good' if water else 'Best', 'Wash the jar and give it fresh water.' if water else
        'Slugs, roaches, ants and scorpions hide under pots and in saucers.')

    if succ: put('rinse', 'Not for this plant', 'Water left in the rosettes or crowns can rot them. Use a soft dry brush, and rubbing alcohol for mealybugs.')
    elif fern: put('rinse', 'Best', 'Plain water is the safest treatment for ferns, which soaps and oils often damage.')
    elif fuzzy: put('rinse', 'Use with care', 'Rinse gently in the morning so the leaves dry fast; water can mark fuzzy leaves.')
    elif water: put('rinse', 'Good', 'Rinse the leaves and roots gently and give it fresh water.')
    elif soft: put('rinse', 'Best', f'A hard spray of water knocks off most of the {lower(soft)}.')
    elif mites_prone: put('rinse', 'Best', ('Palms' if palm else 'This plant') + ' often get spider mites, and rinsing the undersides of the leaves is the best prevention.')
    else: put('rinse', 'Good', 'Quick insurance against pests too small to see.')

    if big or water: put('wipe', 'Best' if big else 'Good', 'Big leaves are quick to wipe, and it removes dust so they get more light indoors.' if big else 'Wipe the leaves gently with a damp cloth.')
    elif palm: put('wipe', 'Good', 'Wipe the leaflets top and bottom if you have time; rinsing is quicker.')
    elif fuzzy: put('wipe', 'Use with care', 'Brush the leaves with a soft dry paintbrush instead of a wet cloth.')
    elif succ: put('wipe', 'Not for this plant', 'Wiping rubs off the powdery coating that protects the leaves. Use a soft dry brush.')
    elif fern: put('wipe', 'Not for this plant', 'The fronds break easily. Rinse instead.')
    elif lt == 'Small or many leaves': put('wipe', 'Not needed', 'Too many small leaves to wipe one by one; rinsing does the same job.')
    else: put('wipe', 'Good', 'Choose the leaf type above to rate this properly.')

    if soft or 'Scale' in pests:
        found = soft + (['Scale'] if 'Scale' in pests else [])
        if fern: put('soap', 'Use with care', f'It kills {lower(found)}, but ferns are often damaged by soap: test one frond and wait 2 days, or keep rinsing with water.')
        elif succ: put('soap', 'Use with care', f'It kills {lower(found)}; test one leaf first. For a few mealybugs, rubbing alcohol is gentler.')
        elif weak: put('soap', 'Use with care', f'It kills {lower(found)}, but this plant is already struggling: test one leaf and wait 2 days.')
        else: put('soap', 'Best', f'Kills {lower(found)} on contact. Spray 2 or 3 times, 5 to 7 days apart.')
    elif mites_prone or 'mealybug' in watch or 'aphid' in watch:
        put('soap', 'Not needed' if (fern or succ) else 'Good', 'Only if you find pests.' if (fern or succ) else
            'A precaution: this plant often gets ' + lower([p for p in ('Spider mites', 'Mealybugs', 'Aphids') if p.lower().rstrip('s') in watch or (p == 'Spider mites' and palm)]) + '.')
    else: put('soap', 'Not needed', 'Only if you find soft-bodied pests such as mites, aphids or mealybugs.')

    if succ or fuzzy or fern:
        put('oil', 'Not for this plant', 'Oil can burn ' + ('succulents' if succ else 'fuzzy leaves' if fuzzy else 'fern fronds') + '.')
    elif 'Scale' in pests: put('oil', 'Use with care' if weak else 'Best', 'Smothers scale and its eggs, which soap misses.' + (' This plant is struggling, so test one leaf first.' if weak else ''))
    elif {'Mealybugs', 'Spider mites'} & pests: put('oil', 'Use with care' if weak else 'Good', 'Also smothers eggs: use it if soap alone does not clear them.')
    else: put('oil', 'Not needed', 'Only for scale, or eggs that soap does not clear.')

    if {'Mealybugs', 'Scale'} & pests:
        what = lower(sorted({'Mealybugs', 'Scale'} & pests, key=PESTS.index))
        put('alcohol', 'Best' if succ else 'Use with care' if fern else 'Good',
            f'The gentlest way to clear {what} from succulents.' if succ else f'Quick for a few {what} you can reach; spray if there are many.')
    else: put('alcohol', 'Not needed', 'Only for mealybugs or scale.')

    if water: put('soak', 'Not needed', 'It already grows in water; change the water instead.')
    elif dry: put('soak', 'Not for this plant', 'A long soak keeps its roots wet for days. Refresh the top of the soil instead, or repot if there are pests in the soil.')
    elif ps.startswith('Large'): put('soak', 'Use with care', 'Too big for a bucket. Water it slowly and heavily instead, and watch what crawls out.')
    elif soil: put('soak', 'Best', f'Drives the {lower(soil)} out of the soil.' + ('' if ps else ' Choose the pot size above.'))
    else: put('soak', 'Good', 'Insurance against ants and other pests hiding in the soil, and it waters the plant.' + ('' if ps else ' Only if the pot fits in a bucket or tub.'))

    if water: put('topsoil', 'Not needed', 'It grows in water.')
    elif 'Fungus gnats' in pests or 'Ants' in pests:
        put('topsoil', 'Best', ('Fungus gnats lay their eggs' if 'Fungus gnats' in pests else 'Ants nest') + ' in the top inch or two of soil.')
    elif succ: put('topsoil', 'Good', 'Fresh grit on top keeps the base dry and fungus gnats away.')
    elif (r['soil_moisture_high'] or 0) >= 60: put('topsoil', 'Good', 'It likes damp soil, which draws fungus gnats indoors; a fresh top layer helps.')
    else: put('topsoil', 'Good', 'Quick, and removes eggs and debris from the surface.')

    if water: put('repot', 'Good', 'Rinse the roots and refill a clean jar with fresh water.')
    elif 'Root mealybugs' in pests: put('repot', 'Use with care' if weak else 'Best', 'Root mealybugs live on the roots; only fresh soil clears them.' + (' It is struggling already, so be gentle.' if weak else ''))
    elif soil or 'Fungus gnats' in pests: put('repot', 'Use with care' if weak else 'Good', 'Only if soaking or a fresh top layer did not clear them; repotting adds stress just as it loses light.')
    elif weak: put('repot', 'Not needed', 'It is already struggling, and repotting adds stress. Wait until spring.')
    else: put('repot', 'Not needed', 'Repotting now adds stress just as it loses light. Wait until spring unless you find pests in the soil.')

    if wx.get('spray'):
        for k in ('soap', 'oil'):
            rt, why = out[k]
            if PREP_RANK[rt] >= 2: out[k] = (rt, why + ' ' + wx['spray'])
    return out

def prep_moved_in(c, r):
    """The day the plant last moved to an inside Location, from its change log, or None."""
    a = c.execute("SELECT changed_at FROM audit_log WHERE plant_id=? AND field='site' AND new_value IN (%s) ORDER BY id DESC LIMIT 1"
                  % ','.join('?' * len(INSIDE_SITES)), [r['id']] + INSIDE_SITES).fetchone()
    if not a: return None
    tz = tzinfo(location(c)['tz'])
    return datetime.strptime(a[0], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(tz).date()

def prep_plan(c, r, wx, log=None, with_steps=False):
    """Everything about one plant's move inside: ratings, what has been done, its status and the next step."""
    today = local_today(c)
    since = (today - timedelta(days=PREP_WINDOW_DAYS)).isoformat()
    if log is None:
        log = [dict(x) for x in c.execute("SELECT * FROM care_log WHERE plant_code=? AND kind LIKE 'prep_%' AND done_on>=? ORDER BY done_on, id", (r['code'], since))]
    done = {k: sorted(x['done_on'] for x in log if x['kind'] == 'prep_' + k) for k in PREP_KEYS}
    pests = {x for x in (r['pests_found'] or '').split('\n') if x in PESTS}
    rates = prep_rate(r, pests, wx)
    methods = []
    for m in PREP_METHODS:
        rt, why = rates[m['key']]
        d = done[m['key']]
        rounds_needed = 2 if m.get('repeat') and rt == 'Best' else 1
        due = None
        if m.get('repeat') and d and len(d) < rounds_needed:
            due = (date.fromisoformat(d[-1]) + timedelta(days=5)).isoformat()
        x = {'key': m['key'], 'title': m['title'], 'rating': rt, 'rank': PREP_RANK[rt], 'reason': why, 'done': d,
             'rounds': rounds_needed, 'complete': len(d) >= rounds_needed, 'next_due': due}
        if with_steps: x['steps'] = m['steps']
        methods.append(x)
    site = r['site'] or 'Outdoors'
    inside = site in INSIDE_SITES
    moved = prep_moved_in(c, r) if inside else None
    treat = [x['done_on'] for x in log if x['kind'] in ('prep_soap', 'prep_oil', 'prep_alcohol', 'prep_repot')]
    keep = None
    if moved:
        keep = moved + timedelta(days=KEEP_APART_DAYS)
        if pests and treat:
            keep = max(keep, date.fromisoformat(max(treat)) + timedelta(days=KEEP_APART_AFTER_TREATMENT))
    todo = [x for x in methods if x['rating'] == 'Best' and not x['complete']]
    if inside:
        if keep and today <= keep: status, nxt = 'apart', f'Keep it apart from your other houseplants until {keep:%A}, {keep:%b} {keep.day}, and check it at every watering.'
        else: status, nxt = 'settled', 'Inside and settled. Check it at every watering.'
    elif not any(done.values()): status, nxt = 'todo', 'Start by inspecting it for pests.'
    elif not done['inspect']: status, nxt = 'doing', 'Inspect it for pests.'
    elif todo:
        status = 'doing'
        first = next((x for x in todo if not x['next_due']), None)
        if first: nxt = f'Next: {first["title"].lower()}.'
        else:
            x = todo[0]; dd = date.fromisoformat(x['next_due'])
            nxt = f'{x["title"]} again on or after {dd:%A}, {dd:%b} {dd.day} (round {len(x["done"]) + 1}).'
    else: status, nxt = 'ready', 'Ready to come inside. Change its Location (or press Moved indoors) when you bring it in.'
    return {'code': r['code'], 'name': r['common_name'], 'site': site, 'winter_plan': r['winter_plan'], 'health': r['health_rating'],
            'leaf_type': r['leaf_type'] or '', 'pot_size': r['pot_size'] or '', 'pests_found': sorted(pests, key=PESTS.index),
            'watch': [x for x in (r['pests_watch'] or '').split('\n') if x.strip()],
            'methods': methods, 'best': [x['title'] for x in methods if x['rating'] == 'Best'],
            'status': status, 'next': nxt, 'moved_in': moved.isoformat() if moved else None, 'keep_until': keep.isoformat() if keep else None,
            'done_count': sum(1 for x in methods if x['done']), 'log': log}

PREP_STATUS = {'todo': 'Not started', 'doing': 'In progress', 'ready': 'Ready to come inside', 'apart': 'Inside, kept apart', 'settled': 'Inside and settled'}

@app.route('/api/prep')
def prep_list():
    """Plants coming inside this winter (winter plan "Move indoors"), or every plant with ?all=1."""
    c = db()
    wx = prep_weather(c)
    since = (local_today(c) - timedelta(days=PREP_WINDOW_DAYS)).isoformat()
    logs = {}
    for x in c.execute("SELECT * FROM care_log WHERE kind LIKE 'prep_%' AND done_on>=? ORDER BY done_on, id", (since,)):
        logs.setdefault(x['plant_code'], []).append(dict(x))
    q = "SELECT * FROM plants WHERE status='active'" + ('' if request.args.get('all') == '1' else " AND (winter_plan='Move indoors' OR code IN (SELECT DISTINCT plant_code FROM care_log WHERE kind LIKE 'prep_%' AND done_on>=?))") + ' ORDER BY code'
    rows = c.execute(q, () if request.args.get('all') == '1' else (since,)).fetchall()
    photo = lambda pid: (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (pid,)).fetchone() or [None])[0]
    plants = []
    for r in rows:
        p = prep_plan(c, r, wx, logs.get(r['code'], []))
        p['photo'] = photo(r['id']); p.pop('log')
        plants.append(p)
    counts = {k: sum(1 for p in plants if p['status'] == k) for k in PREP_STATUS}
    return jsonify(weather=wx, status_words=PREP_STATUS, counts=counts, plants=plants,
                   methods=[{'key': m['key'], 'title': m['title'], 'steps': m['steps']} for m in PREP_METHODS],
                   keep_apart_days=KEEP_APART_DAYS)

@app.route('/api/plants/<code>/prep')
def prep_one(code):
    c = db()
    p = prep_plan(c, plant_row(c, code), prep_weather(c), with_steps=True)
    p.update(status_word=PREP_STATUS[p['status']], options={'leaf_types': LEAF_TYPES, 'pot_sizes': POT_SIZES, 'pests': PESTS})
    return jsonify(p)

@app.route('/api/plants/<code>/prep-traits', methods=['POST'])
def prep_traits(code):
    """Saves the leaf type, pot size and pests found, as a new page version, and returns the new ratings."""
    c = db()
    r = plant_row(c, code)
    b = request.get_json(silent=True) or {}
    f = {}
    if 'leaf_type' in b: f['leaf_type'] = str(b['leaf_type'] or '')
    if 'pot_size' in b: f['pot_size'] = str(b['pot_size'] or '')
    if 'pests_found' in b:
        got = b['pests_found'] if isinstance(b['pests_found'], list) else []
        f['pests_found'] = '\n'.join(x for x in PESTS if x in got)
    if not f: abort(400, 'Nothing to save')
    note = None
    if 'pests_found' in f: note = 'Pests found: ' + (', '.join(f['pests_found'].split('\n')) if f['pests_found'] else 'none')
    apply_changes(c, r, f, editor(), 'update', note)
    c.commit()
    p = prep_plan(c, plant_row(c, code), prep_weather(c), with_steps=True)
    p.update(status_word=PREP_STATUS[p['status']], options={'leaf_types': LEAF_TYPES, 'pot_sizes': POT_SIZES, 'pests': PESTS},
             version=plant_row(c, code)['version'])
    return jsonify(p)

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

# ---------------------------------------------------------------- audit log: every change to every record (filters added in 1.10.0)
AUDIT_KINDS = {                          # kind of change (the filter on the Audit log page) -> actions in audit_log
    'edits': ('Changes to plant pages', ('update', 'edit', 'restore')),
    'plants': ('Plants added, archived or brought back', ('create', 'archive', 'unarchive')),
    'photos': ('Photos', ('photo_add', 'photo_assign', 'photo_move', 'photo_remove', 'photo_caption', 'photo_primary')),
    'care': ('Feeding, watering and care', ('care', 'fertilizer', 'frost')),
    'requests': ('Requests and answers', ('request',)),
    'list': ('"Still to photograph" list', ('todo',)),
    'settings': ('Settings and backups', ('setting', 'backup')),
    'lights': ('Grow lights', ('light',)),
    'groups': ('Groups and changes to a whole group', ('group',)),
    'notes': ('Notes from updates', ('note',)),
    'fungi': ('Mushroom finds', ('fungi',)),
    'library': ('Library notes, tags and wishlist', ('library',)),
}
ACTION_WORD = {'create': 'Page created', 'update': 'Edited', 'edit': 'Updated', 'restore': 'Restored', 'archive': 'Archived', 'unarchive': 'Brought back',
               'photo_add': 'Photo added', 'photo_assign': 'Photo assigned', 'photo_move': 'Photo moved', 'photo_remove': 'Photo removed',
               'photo_caption': 'Caption edited', 'photo_primary': 'Main photo changed', 'care': 'Care', 'fertilizer': 'Feeding', 'frost': 'Cold night',
               'request': 'Request', 'todo': 'Photo list', 'setting': 'Setting', 'backup': 'Backup', 'note': 'Note', 'light': 'Grow light', 'group': 'Group', 'fungi': 'Mushroom find', 'library': 'Library'}

def audit_query(c, a, count=False):
    """SQL and arguments for the audit log with the filters in `a` (request.args): q, plant, who, kind, field, from, to,
    after (id, for the live console) and order."""
    w, args = [], []
    q = (a.get('q') or '').strip()
    if q:
        like = '%' + q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'      # match the text itself, wildcards included
        fields = [n for n, l in FIELD_LABEL.items() if q.lower() in str(l).lower()]
        cols = ('a.note', 'a.old_value', 'a.new_value', 'a.changed_by', 'a.plant_code', 'a.action', 'a.field', 'p.common_name')
        w.append('(' + ' OR '.join(f"{col} LIKE ? ESCAPE '\\'" for col in cols)
                 + (' OR a.field IN (%s)' % ','.join('?' * len(fields)) if fields else '') + ')')
        args += [like] * len(cols) + fields
    plant = (a.get('plant') or '').strip()
    if plant == '-': w.append('a.plant_code IS NULL')
    elif plant: w.append('a.plant_code = ?'); args.append(plant)
    who = (a.get('who') or '').strip()
    if who == '~claude': w.append("a.changed_by LIKE 'Claude%'")
    elif who == '~people': w.append("a.changed_by NOT LIKE 'Claude%'")
    elif who: w.append('a.changed_by = ?'); args.append(who)
    kind = a.get('kind') or ''
    if kind in AUDIT_KINDS:
        acts = AUDIT_KINDS[kind][1]; w.append('a.action IN (%s)' % ','.join('?' * len(acts))); args += list(acts)
    field = a.get('field') or ''
    if field: w.append('a.field = ?'); args.append(field)
    tz = tzinfo(location(c)['tz'])
    for key, op, extra in (('from', '>=', 0), ('to', '<', 1)):
        v = a.get(key) or ''
        try: d = datetime.strptime(v, '%Y-%m-%d') + timedelta(days=extra)
        except ValueError: continue
        w.append(f'a.changed_at {op} ?'); args.append(d.replace(tzinfo=tz).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    if a.get('after'):
        try: w.append('a.id > ?'); args.append(int(a['after']))
        except ValueError: abort(400, 'after must be a number')
    where = (' WHERE ' + ' AND '.join(w)) if w else ''
    base = ' FROM audit_log a LEFT JOIN plants p ON p.code = a.plant_code' + where
    if count: return 'SELECT COUNT(*)' + base, args
    order = 'ASC' if a.get('order') == 'asc' or a.get('after') else 'DESC'
    return 'SELECT a.*, p.common_name AS plant_name' + base + f' ORDER BY a.id {order}', args

AUDIT_FIELD_LABEL = {'status': 'Status', 'photo': 'Photo', 'photo caption': 'Photo caption', 'main photo': 'Main photo', 'care_log': 'Care log',
                     'frost': 'Cold night', 'request': 'Request', 'to_photograph': '"Still to photograph" list', 'base_url': 'Label web address',
                     'backup_settings': 'Automatic backups', 'weather_place': 'Weather place', 'ingest_token': 'Sensor token', 'backup': 'Backup',
                     'claude_copied_at': 'Copied for Claude', 'grow_light': 'Grow light spot', 'light_spot': 'Light spot', 'light': 'Grow light',
                     'indoor_place': 'Room or shelf'}

def audit_label(field):
    if not field: return None
    return FIELD_LABEL.get(field) or AUDIT_FIELD_LABEL.get(field) or str(field).replace('_', ' ').capitalize()

def audit_rows(c, sql, args):
    rows = [dict(x) for x in c.execute(sql, args)]
    for r in rows:
        r['label'] = audit_label(r['field'])
        r['action_word'] = ACTION_WORD.get(r['action'], r['action'])
    return rows

@app.route('/api/audit')
def audit():
    """The newest changes first (a list), with the same filters as /api/audit/search. ?after=<id> returns the changes
    since that one, oldest first: the live console asks for this every few seconds."""
    c = db()
    limit = max(1, min(int(request.args.get('limit', 200)), 2000))
    sql, args = audit_query(c, request.args)
    return jsonify(audit_rows(c, sql + ' LIMIT ?', args + [limit]))

@app.route('/api/audit/search')
def audit_search():
    """One page of the audit log with filters, plus how many changes match in all."""
    c = db()
    limit = max(1, min(int(request.args.get('limit', 100)), 500))
    offset = max(0, int(request.args.get('offset', 0) or 0))
    sql, args = audit_query(c, request.args)
    csql, cargs = audit_query(c, request.args, count=True)
    total = c.execute(csql, cargs).fetchone()[0]
    return jsonify(entries=audit_rows(c, sql + ' LIMIT ? OFFSET ?', args + [limit, offset]), total=total, offset=offset, limit=limit,
                   max_id=c.execute('SELECT MAX(id) FROM audit_log').fetchone()[0] or 0)

@app.route('/api/audit/facets')
def audit_facets():
    """What the filters on the Audit log page can choose from."""
    c = db()
    who = [{'name': r[0], 'count': r[1]} for r in c.execute('SELECT changed_by, COUNT(*) FROM audit_log GROUP BY changed_by ORDER BY changed_by LIKE ?, changed_by', ('Claude%',))]
    used = {r[0] for r in c.execute('SELECT DISTINCT field FROM audit_log WHERE field IS NOT NULL')}
    fields = [{'name': n, 'label': audit_label(n)} for n in used]
    plants = [{'code': r['code'], 'name': r['common_name'], 'status': r['status']} for r in c.execute('SELECT code, common_name, status FROM plants ORDER BY code')]
    first = c.execute('SELECT MIN(changed_at), COUNT(*) FROM audit_log').fetchone()
    return jsonify(who=who, fields=sorted(fields, key=lambda f: str(f['label']).lower()), plants=plants,
                   kinds=[{'key': k, 'label': v[0]} for k, v in AUDIT_KINDS.items()], first=first[0], total=first[1])

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
        # 1.21.0: the short side is at least 640 px, so a wide photo cropped to fill a tall card (or shown whole) stays sharp on
        # high-resolution screens. Before, wide photos were 520 x 390 and blurry when cropped.
        im = ImageOps.exif_transpose(Image.open(src)); im = im.convert('RGB') if im.mode not in ('RGB', 'L') else im
        k = min(1.0, 640 / min(im.size), 1400 / max(im.size))
        if k < 1: im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        os.makedirs(THUMB_DIR, exist_ok=True)
        im.save(dst + '.tmp', 'JPEG', quality=82, optimize=True); os.replace(dst + '.tmp', dst)
    return send_from_directory(THUMB_DIR, safe, max_age=3600)

# ---------------------------------------------------------------- to-photograph list
@app.route('/api/to-photograph', methods=['GET', 'POST'])
def to_photograph():
    c = db()
    if request.method == 'POST':
        b = request.get_json(silent=True) or {}
        if not str(b.get('label', '')).strip(): abort(400, 'label required')
        c.execute('INSERT INTO to_photograph(label,note) VALUES(?,?)', (str(b['label']).strip()[:200], str(b.get('note', '') or '').strip()[:1000]))
        audit_only(c, 'todo', 'to_photograph', None, str(b['label']).strip()[:200], editor(), 'Added: ' + str(b['label']).strip()[:200])
        c.commit()
    return jsonify([dict(r) for r in c.execute('SELECT * FROM to_photograph ORDER BY done, id')])

@app.route('/api/to-photograph/<int:i>', methods=['PATCH', 'DELETE'])
def to_photograph_item(i):
    c = db()
    t = c.execute('SELECT * FROM to_photograph WHERE id=?', (i,)).fetchone()
    if request.method == 'DELETE':
        c.execute('DELETE FROM to_photograph WHERE id=?', (i,))
        if t: audit_only(c, 'todo', 'to_photograph', t['label'], None, editor(), 'Removed from the list: ' + t['label'])
    else:
        b = request.get_json(silent=True) or {}
        if 'done' in b:
            c.execute('UPDATE to_photograph SET done=? WHERE id=?', (1 if b.get('done') else 0, i))
            if t and bool(t['done']) != bool(b.get('done')):
                audit_only(c, 'todo', 'to_photograph', t['label'], 'done' if b.get('done') else 'open', editor(), ('Ticked off: ' if b.get('done') else 'Unticked: ') + t['label'])
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
    return "'" + s if s and s[0] in '=+-@\t\r' else s           # neutralise spreadsheet formulas

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
    sql, args = audit_query(c, request.args)                 # the Audit log page's filters, if any (all changes otherwise)
    if request.args.get('order') != 'desc': sql = sql.replace(' ORDER BY a.id DESC', ' ORDER BY a.id ASC')
    for r in c.execute(sql, args):
        w.writerow([_csv_safe(x) for x in (r['changed_at'], r['plant_code'], r['version'], r['action'], audit_label(r['field']), r['old_value'], r['new_value'], r['changed_by'], r['note'])])
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
    """The place a request is about (?loc=ID, or loc in a JSON body); otherwise the place in use (see location())."""
    v = request.args.get(key)
    if v is None and request.is_json: v = (request.get_json(silent=True) or {}).get(key)
    if v in (None, ''): return location(c)
    L = loc_get(c, v)
    if L is None: abort(404, 'That place does not exist (it may have been removed)')
    return L

def home_place(c):
    """The home place: the one every browser starts with, and the one background work (hourly updates, backups) uses."""
    return loc_get(c)

def location(c):
    """The place in use (1.11.0): the one chosen with the Location button in this browser, which the page sends as the
    X-Place header on every request; the home place when none is chosen, or the chosen one has been removed.
    Weather, frost warnings, watering, the Winter plan and "today" all follow it."""
    if has_request_context():
        v = request.headers.get('X-Place', '').strip()
        if v.isdigit():
            L = loc_get(c, v)
            if L is not None: return L
    return loc_get(c)

PLACE_CLIMATE = {}
USDA_MAP_URL = 'https://planthardiness.ars.usda.gov/'

def usda_zone(f):
    """USDA hardiness zone for an average yearly coldest night (F): zone 1a starts at -60 F, each half zone is 5 F."""
    if f is None: return None
    n = math.floor((f + 60) / 5)
    if n < 0: return '1a'
    if n > 25: return '13b'
    return '%d%s' % (n // 2 + 1, 'ab'[n % 2])

def zone_num(z):
    """'9a' -> 9.0, '9b' -> 9.5, '10' -> 10.0; None if it is not a zone."""
    m = re.match(r'^\s*(\d{1,2})\s*([ab])?\s*$', str(z or ''), re.I)
    return int(m.group(1)) + (0.5 if (m.group(2) or '').lower() == 'b' else 0.0) if m else None

def place_zone(c, L):
    """1.14.0: the hardiness zone where the plants are, from the place's own weather history (the average of each winter's
    coldest night, which is how the USDA defines zones), and for the Round Rock area the 2023 USDA map's zone too."""
    cl = place_climate(c, L)
    near_ref = L.get('lat') is not None and abs(L['lat'] - REF_PLACE[0]) < 0.25 and abs(L['lon'] - REF_PLACE[1]) < 0.25
    return {'zone': usda_zone(cl['winter_low']) if cl else None, 'winter_low': cl['winter_low'] if cl else None, 'years': cl['years'] if cl else 0,
            'map_zone': '8b to 9a' if near_ref else None, 'map_note': 'Round Rock is on the line between zones 8b and 9a on the 2023 USDA map.' if near_ref else None,
            'map_url': USDA_MAP_URL}

def place_climate(c, L):
    """Typical winter cold at a place, from its daily weather history: the average of each winter's coldest night, and the
    average night in its coldest month. Needs at least 3 whole years of history; worked out at most every 6 hours."""
    hit = PLACE_CLIMATE.get(L['id'])
    if hit and time.time() - hit[0] < 6 * 3600: return hit[1]
    lows, winters = {}, {}
    try: rows = c.execute("SELECT date, json_extract(data, '$.temperature_2m_min') FROM weather_daily WHERE loc_id=? AND kind='observed'", (L['id'],)).fetchall()
    except sqlite3.OperationalError:            # an SQLite without JSON functions
        rows = [(d, (json.loads(x) if x else {}).get('temperature_2m_min')) for d, x in c.execute("SELECT date, data FROM weather_daily WHERE loc_id=? AND kind='observed'", (L['id'],))]
    for d, t in rows:
        if not isinstance(t, (int, float)): continue
        y, m = int(d[:4]), int(d[5:7])
        lows.setdefault(m, []).append(t)
        winters.setdefault(y if m >= 7 else y - 1, []).append(t)        # a winter runs from July to June
    whole = [v for v in winters.values() if len(v) >= 330]
    out = None
    if len(whole) >= 3 and len(lows) == 12:
        cold = min(lows, key=lambda m: sum(lows[m]) / len(lows[m]))
        warm = max(lows, key=lambda m: sum(lows[m]) / len(lows[m]))
        winter = sorted(m for m in range(1, 13) if min(abs(m - cold), 12 - abs(m - cold)) <= 1)     # the coldest month and the ones either side
        rh = None
        try:
            r = c.execute(f"SELECT AVG(json_extract(data, '$.relative_humidity_2m_mean')) FROM weather_daily WHERE loc_id=? AND kind='observed' "
                          f"AND CAST(substr(date, 6, 2) AS INTEGER) IN ({','.join('?' * len(winter))})", (L['id'], *winter)).fetchone()
            rh = round(r[0]) if r and r[0] is not None else None
        except sqlite3.OperationalError: pass
        out = {'winter_low': round(sum(min(v) for v in whole) / len(whole)), 'cold_month': cold, 'warm_month': warm,
               'cold_month_low': round(sum(lows[cold]) / len(lows[cold])), 'winter_months': winter, 'winter_rh': rh, 'years': len(whole)}
    PLACE_CLIMATE[L['id']] = (time.time(), out)
    return out

def place_brief(L):
    return {k: L[k] for k in ('id', 'name', 'tz', 'is_home', 'enabled')}

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
    return jsonify(location=L, places=places_list(c), forecast=fc, status=st, enabled=L['enabled'], home=home_place(c),
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

# ---- 1.11.0: the fertilizers you have, and which one suits each plant
def parse_ratio(s):
    """'3-1-2', '3:1:2', '24 8 16' -> (3.0, 1.0, 2.0); None when it is not three numbers with at least one above 0."""
    parts = [x for x in re.split(r'[\s\-:/,]+', str(s or '').strip()) if x]
    if len(parts) != 3: return None
    try: v = tuple(float(x) for x in parts)
    except ValueError: return None
    if any(x < 0 or x > 100 for x in v) or not sum(v): return None
    return v

FERT_LIQUID = ('liquid', 'organic liquid', 'foliar spray')
FERT_SOIL = ('granular', 'slow-release', 'spikes', 'organic solid')        # go on or in the mix, not into water
STRENGTH_PPM = {'Quarter strength': 40, 'Quarter to half strength': 55, 'Half strength': 75, 'Full strength': 150}
STRENGTH_SHARE = {'Quarter strength': 'a quarter of', 'Quarter to half strength': 'a quarter to half of', 'Half strength': 'half', 'Full strength': 'all of'}
NUTRIENT = ('nitrogen (N)', 'phosphate (P)', 'potash (K)')
FRACTIONS = {0.125: '⅛', 0.25: '¼', 0.375: '⅜', 0.5: '½', 0.625: '⅝', 0.75: '¾', 0.875: '⅞'}

def nice_amount(x):
    """A spoon measure people can actually use: eighths under 1, quarters up to 3, halves above."""
    step = 0.125 if x < 1 else 0.25 if x < 3 else 0.5
    v = max(step, round(x / step) * step)
    whole, frac = int(v), round(v - int(v), 3)
    return v, (str(whole) if whole else '') + FRACTIONS.get(frac, '' if not frac else '%g' % frac)

def ratio_words(v):
    m = min(x for x in v if x > 0)
    return ' : '.join('%g' % round(x / m, 1) for x in v)

def fert_match(need, prod):
    """How well a fertilizer's N-P-K fits the ratio a plant needs, compared as shares of the total."""
    rs, fs = [x / sum(need) for x in need], [x / sum(prod) for x in prod]
    diff = max(abs(a - b) for a, b in zip(rs, fs))
    quality = 'Matches' if diff <= 0.05 else 'Close' if diff <= 0.12 else 'Usable' if diff <= 0.22 else 'Not a good match'
    more = [NUTRIENT[i] for i in range(3) if fs[i] - rs[i] > 0.08]
    less = [NUTRIENT[i] for i in range(3) if rs[i] - fs[i] > 0.08]
    j = lambda xs: ' and '.join(xs)
    why = ''
    if more or less:
        why = 'It has ' + ' and '.join(x for x in (('more ' + j(more)) if more else '', ('less ' + j(less)) if less else '') if x) + ' than this plant needs.'
    return {'quality': quality, 'diff': round(diff, 3), 'why': why}

def fert_dose(prod, strength):
    """How much of this fertilizer to use for a plant that wants it at this strength. Mixed into water, the strongest of
    N, P and K is aimed at about 150 ppm for full strength (75 for half, 40 for a quarter), close to typical label rates."""
    if strength == 'None needed': return {'kind': 'none', 'words': 'This plant needs little or no fertilizer.'}
    if strength not in STRENGTH_PPM: return None
    share = STRENGTH_SHARE[strength]
    if prod['form'] in FERT_SOIL:
        return {'kind': 'soil', 'words': f"This one goes on or into the mix, not into water. Use {share} the amount on its label for the pot size."}
    vals = [prod[x] for x in 'npk']
    if any(x is None for x in vals) or not max(vals): return None
    target, top = STRENGTH_PPM[strength], max(vals)
    liquid = prod['form'] in FERT_LIQUID
    per_tsp = 4.92892 if liquid else 4.0                 # grams per teaspoon, as in fert_calc
    g_gal = target * WATER_L['gal'] / (top * 10)
    water = 1
    for w in (1, 2, 5):                                   # less than ⅛ tsp is hard to measure: make a bigger batch
        water = w
        if g_gal * w / per_tsp >= 0.125: break
    amount, amt_txt = nice_amount(g_gal * water / per_tsp)
    unit = 'tsp'
    if amount >= 3: unit = 'tbsp'; amount, amt_txt = nice_amount(amount / 3)
    calc = fert_calc(prod['form'], prod['n'], prod['p'], prod['k'], amount, unit, water, 'gal')
    per_l = g_gal / WATER_L['gal']
    metric = ('%s ml' if liquid else '%s g') % ('%.1f' % per_l if per_l < 10 else '%.0f' % per_l) + ' per liter'
    return {'kind': 'water', 'amount': amount, 'unit': unit, 'amount_text': amt_txt + ' ' + unit, 'water': water, 'water_unit': 'gal', 'metric': metric, 'target_ppm': target,
            'ppm_n': calc['ppm_n'], 'ppm_p2o5': calc['ppm_p2o5'], 'ppm_k2o': calc['ppm_k2o'],
            'words': f"Mix {amt_txt} {unit} into {water} gallon{'s' if water > 1 else ''} of water ({metric})."}

def fert_products(c):
    """Fertilizers you have: the ones saved on the Fertilizer page, plus every one ever logged, newest first.
    A saved one's N-P-K and type win over what was logged; the last logged dose is kept either way."""
    out, by = [], {}
    for r in c.execute('SELECT * FROM fertilizers ORDER BY COALESCE(updated_at, created_at) DESC'):
        d = {'id': r['id'], 'product': r['product'], 'form': r['form'], 'n': r['n'], 'p': r['p'], 'k': r['k'], 'note': r['note'],
             'saved': True, 'uses': 0, 'last_used': None, 'amount': None, 'amount_unit': None, 'water_amount': None, 'water_unit': None, 'method': None}
        out.append(d); by[r['product'].lower()] = d
    for r in c.execute('SELECT * FROM fertilizer_log ORDER BY applied_on DESC, id DESC'):
        key = r['product'].lower()
        d = by.get(key)
        if d is None:
            d = {'id': None, 'product': r['product'], 'form': r['form'], 'n': r['n'], 'p': r['p'], 'k': r['k'], 'note': '', 'saved': False,
                 'uses': 0, 'last_used': None, 'amount': None, 'amount_unit': None, 'water_amount': None, 'water_unit': None, 'method': None}
            out.append(d); by[key] = d
        d['uses'] += 1
        if d['last_used'] is None:
            d.update(last_used=r['applied_on'], amount=r['amount'], amount_unit=r['amount_unit'], water_amount=r['water_amount'],
                     water_unit=r['water_unit'], method=r['method'])
    out.sort(key=lambda d: (d['last_used'] or '', d['saved']), reverse=True)
    return out

def fert_need(p, products):
    """What a plant needs, and the fertilizer you have that fits it best."""
    need = parse_ratio(p['npk_ratio'])
    strength = p['fert_strength'] or ''
    out = {'code': p['code'], 'ratio': list(need) if need else None, 'ratio_text': p['npk_ratio'] or '', 'ratio_words': ratio_words(need) if need else '',
           'strength': strength, 'match': None, 'note': ''}
    if strength == 'None needed' and not need:
        out['note'] = 'This plant needs little or no fertilizer.'
        return out
    if not need:
        out['note'] = 'No fertilizer ratio set yet. Add one on the Edit page, under Nutrients.'
        return out
    usable = [f for f in products if f['n'] is not None and f['p'] is not None and f['k'] is not None and (f['n'] + f['p'] + f['k']) > 0]
    if not usable:
        out['note'] = 'None of your fertilizers have their N-P-K numbers yet. Add the ones you have under "Your fertilizers".' if products else \
                      'No fertilizers yet. Add the ones you have under "Your fertilizers", or log a feeding, and the closest one shows here.'
        return out
    best = min(usable, key=lambda f: (fert_match(need, (f['n'], f['p'], f['k']))['diff'], f['form'] in FERT_SOIL, -(f['uses'] or 0)))
    m = fert_match(need, (best['n'], best['p'], best['k']))
    out['match'] = {'product': best['product'], 'form': best['form'], 'n': best['n'], 'p': best['p'], 'k': best['k'],
                    'npk_text': '-'.join('%g' % best[x] for x in 'npk'), 'ratio_words': ratio_words((best['n'], best['p'], best['k'])),
                    **m, 'dose': fert_dose(best, strength or 'Half strength'), 'strength_assumed': not strength,
                    'last': ({'amount': best['amount'], 'amount_unit': best['amount_unit'], 'water_amount': best['water_amount'], 'water_unit': best['water_unit'],
                              'on': best['last_used']} if best['amount'] is not None else None)}
    return out

@app.route('/api/fertilizer/products', methods=['GET', 'POST'])
def fertilizer_products():
    """GET: fertilizers you have (saved and logged), newest first, with the last dose so the form can be filled in.
    POST: save one you have, even before you use it: {product, form, n, p, k, note}."""
    c = db()
    if request.method == 'GET': return jsonify(fert_products(c))
    f = fert_product_fields(request.get_json(silent=True) or {})
    if c.execute('SELECT 1 FROM fertilizers WHERE product=?', (f['product'],)).fetchone(): abort(409, f'"{f["product"]}" is already in your fertilizers')
    who = editor()
    cur = c.execute('INSERT INTO fertilizers(product,form,n,p,k,note,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)',
                    (f['product'], f['form'], f['n'], f['p'], f['k'], f['note'], who, now()))
    audit_only(c, 'fertilizer', 'fertilizer_product', None, fert_product_text(f), who, 'Fertilizer added to your list: ' + fert_product_text(f))
    c.commit()
    return jsonify(id=cur.lastrowid), 201

def fert_product_fields(b):
    product = re.sub(r'\s+', ' ', str(b.get('product', ''))).strip()[:80]
    if not product: abort(400, 'Type the fertilizer name')
    form = str(b.get('form') or 'liquid')
    if form not in FERT_FORMS: abort(400, 'Type must be one of: ' + ', '.join(FERT_FORMS))
    n, p, k = (_num(b, x, 0, 100, lab, required=True) for x, lab in (('n', 'Nitrogen (N) %'), ('p', 'Phosphate (P) %'), ('k', 'Potash (K) %')))
    if not (n + p + k): abort(400, 'At least one of N, P and K must be above 0')
    return {'product': product, 'form': form, 'n': n, 'p': p, 'k': k, 'note': str(b.get('note', '')).strip()[:300]}

def fert_product_text(f):
    return f"{f['product']} ({'-'.join('%g' % f[x] for x in 'npk')}, {f['form']})"

@app.route('/api/fertilizer/products/<int:i>', methods=['PUT', 'DELETE'])
def fertilizer_product_one(i):
    c = db()
    old = c.execute('SELECT * FROM fertilizers WHERE id=?', (i,)).fetchone()
    if not old: abort(404, 'That fertilizer is not in your list')
    who = editor()
    if request.method == 'DELETE':
        c.execute('DELETE FROM fertilizers WHERE id=?', (i,))
        audit_only(c, 'fertilizer', 'fertilizer_product', fert_product_text(old), None, who, 'Fertilizer removed from your list: ' + fert_product_text(old))
        c.commit()
        return jsonify(ok=True)
    f = fert_product_fields(request.get_json(silent=True) or {})
    if c.execute('SELECT 1 FROM fertilizers WHERE product=? AND id<>?', (f['product'], i)).fetchone(): abort(409, f'"{f["product"]}" is already in your fertilizers')
    c.execute('UPDATE fertilizers SET product=?,form=?,n=?,p=?,k=?,note=?,updated_by=?,updated_at=? WHERE id=?',
              (f['product'], f['form'], f['n'], f['p'], f['k'], f['note'], who, now(), i))
    audit_only(c, 'fertilizer', 'fertilizer_product', fert_product_text(old), fert_product_text(f), who, 'Fertilizer changed: ' + fert_product_text(f))
    c.commit()
    return jsonify(ok=True)

@app.route('/api/fertilizer/needs')
def fertilizer_needs():
    """For every active plant (or ?plant=CODE): the N-P-K ratio and strength it needs, and the closest fertilizer you have."""
    c = db()
    products = fert_products(c)
    q, a = "SELECT * FROM plants WHERE status='active'", []
    if request.args.get('plant'): q += ' AND code=?'; a.append(request.args['plant'])
    return jsonify(needs=[fert_need(r, products) for r in c.execute(q + ' ORDER BY code', a)], products=len(products))

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

# ---------------------------------------------------------------- grow lights (1.13.0)
# Ethan's own lights (table lights, specs in a JSON column so a light can carry whatever its maker publishes), the spots
# they light (table light_spots: one kind of light, how many of it, how far above or beside the plants, hours a day and
# brightness) and which plants sit in which spot (table light_assign). From the maker's PPFD-at-distance figures the
# app works out the daily light (DLI) at the leaves and compares it with each plant's dli_low..dli_high.
LIGHT_FOOTPRINT = {'Small': 0.75, 'Medium': 1.5, 'Large': 3.0}       # square feet of light a pot takes, by pot size (prep traits)
LIGHT_HOURS = (12, 14, 16, 10, 8)                                     # hours a day to try, in this order
LIGHT_VERDICT = {'too_dim': 'Too dim', 'dim': 'A bit dim', 'good': 'Good', 'bright': 'A bit bright', 'too_bright': 'Too bright', 'unknown': 'Needs not set'}

def light_specs(r):
    try: d = json.loads(r['data'] or '{}')
    except ValueError: d = {}
    return d

def light_points(d):
    """[(inches, ppfd, area_sqft or None)], nearest first. Points without a distance or PPFD are dropped."""
    out = []
    for p in d.get('ppfd') or []:
        try:
            x, y = float(p[0]), float(p[1])
            a = float(p[2]) if len(p) > 2 and p[2] not in (None, '') else None
        except (TypeError, ValueError, IndexError): continue
        if x > 0 and y > 0: out.append((x, y, a))
    return sorted(out)

def _loglog(pairs, d):
    """Value at distance d from (distance, value) pairs, straight lines on log-log axes (light falls off as a power of distance).
    Outside the measured range the nearest segment is extended; with one point, an exponent of 1.6 is assumed."""
    pairs = [(x, y) for x, y in pairs if x > 0 and y and y > 0]
    if not pairs: return None
    if len(pairs) == 1:
        x0, y0 = pairs[0]
        return y0 * (x0 / d) ** 1.6
    if d <= pairs[0][0]: (x1, y1), (x2, y2) = pairs[0], pairs[1]
    elif d >= pairs[-1][0]: (x1, y1), (x2, y2) = pairs[-2], pairs[-1]
    else:
        i = next(i for i in range(1, len(pairs)) if pairs[i][0] >= d)
        (x1, y1), (x2, y2) = pairs[i - 1], pairs[i]
    if x2 == x1: return y1
    k = math.log(y2 / y1) / math.log(x2 / x1)
    return y1 * (d / x1) ** k

def ppfd_at(pts, d): return _loglog([(x, y) for x, y, _ in pts], d)

def area_at(pts, d):
    ar = [(x, a) for x, _, a in pts if a]
    if not ar: return None
    if len(ar) == 1: return ar[0][1] * (d / ar[0][0]) ** 2
    return _loglog(ar, d)

def light_range(pts):
    """Practical distances for a light: a little closer than the nearest figure, a little past the farthest."""
    if not pts: return None, None
    return max(3.0, round(pts[0][0] * 0.75)), round(pts[-1][0] * 1.25)

def dli_of(ppfd, hours, dim=100): return round(ppfd * dim / 100 * hours * 3600 / 1e6, 1)

def light_verdict(dli, lo, hi):
    if dli is None or (lo is None and hi is None): return 'unknown'
    if lo is not None and dli < lo: return 'too_dim' if dli < lo * 0.8 else 'dim'
    if hi is not None and dli > hi: return 'too_bright' if dli > hi * 1.3 else 'bright'
    return 'good'

def plant_need(r):
    lo, hi = r['dli_low'], r['dli_high']
    if lo is None and hi is None: return None
    lo = lo if lo is not None else hi * 0.5
    hi = hi if hi is not None else lo * 2
    return {'lo': lo, 'hi': hi, 'target': round(lo + (hi - lo) * 0.4, 1)}

def light_timer_note(d, hours):
    hrs = d.get('timer_hours') or []
    if hours in hrs and d.get('timer_repeats'): return 'Set its own timer to %g hours.' % hours
    if hours in hrs: return "Its timer has a %g-hour setting, but it may not repeat every day; a plug-in outlet timer is surer." % hours
    return 'Use a plug-in outlet timer set to %g hours a day.' % hours

def light_setting(d, target, lo=None, hi=None, hours_first=None):
    """Distance, hours and brightness that give about `target` mol/day under one light. Returns a dict, with reach='ok',
    'weak' (cannot give that much, so the strongest setting) or 'strong' (too much even at the gentlest setting)."""
    pts = light_points(d)
    if not pts: return None
    dmin, dmax = light_range(pts)
    dims = sorted({int(x) for x in (d.get('dimming') or [100]) if 0 < int(x) <= 100} | {100}, reverse=True)
    order = ([hours_first] if hours_first else []) + [h for h in LIGHT_HOURS if h != hours_first]
    for h in order:
        for dim in dims:
            need = target * 1e6 / (h * 3600) / (dim / 100)
            if ppfd_at(pts, dmin) < need or ppfd_at(pts, dmax) > need: continue
            a, b = dmin, dmax                      # PPFD falls with distance: halve the interval until it gives `need`
            for _ in range(40):
                m = (a + b) / 2
                if ppfd_at(pts, m) > need: a = m
                else: b = m
            exact = (a + b) / 2
            for dist in dict.fromkeys(max(dmin, min(dmax, x)) for x in (round(exact), math.floor(exact), math.ceil(exact))):
                p = ppfd_at(pts, dist)                 # whole inches: the nearest, else the next one closer or farther that still suits
                dl = dli_of(p, h, dim)
                if lo is None or hi is None or lo <= dl <= hi: break
            else: continue
            return {'distance_in': dist, 'hours': h, 'dim_pct': dim, 'ppfd': round(p), 'dli': dl, 'reach': 'ok',
                    'area_sqft': round(area_at(pts, dist), 1) if area_at(pts, dist) else None}
    best = max(((dli_of(ppfd_at(pts, dmin), 16), 'weak', dmin, 16, 100), (dli_of(ppfd_at(pts, dmax), 8, dims[-1]), 'strong', dmax, 8, dims[-1])),
               key=lambda t: -abs(math.log(max(t[0], 0.01) / max(target, 0.01))))
    dl, reach, dist, h, dim = best
    return {'distance_in': dist, 'hours': h, 'dim_pct': dim, 'ppfd': round(ppfd_at(pts, dist)), 'dli': dl, 'reach': reach,
            'area_sqft': round(area_at(pts, dist), 1) if area_at(pts, dist) else None}

def light_dict(r, used=0):
    d = light_specs(r)
    pts = light_points(d)
    dmin, dmax = light_range(pts)
    return {'id': r['id'], 'key': r['lkey'], 'name': r['name'], 'count': r['count'], 'in_use': used, 'fixture': r['fixture'], 'notes': r['notes'],
            'specs': d, 'points': [{'distance_in': x, 'ppfd': y, 'area_sqft': a} for x, y, a in pts], 'min_in': dmin, 'max_in': dmax,
            'max_dli': dli_of(ppfd_at(pts, dmin), 16) if pts else None,
            'photo': d.get('photo'), 'chart': d.get('chart'), 'updated_by': r['updated_by'] or r['created_by'], 'updated_at': r['updated_at'] or r['created_at']}

def spot_eval(c, s, L, plants):
    d = light_specs(L) if L is not None else {}
    pts = light_points(d)
    p = ppfd_at(pts, s['distance_in']) if pts else None
    dl = dli_of(p, s['hours'], s['dim_pct']) if p else None
    area = area_at(pts, s['distance_in']) if pts else None
    rows, need = [], 0.0
    for r in plants:
        n = plant_need(r)
        need += LIGHT_FOOTPRINT.get((r['pot_size'] or '').split(':')[0], 1.0)
        v = light_verdict(dl, n and n['lo'], n and n['hi'])
        rows.append({'code': r['code'], 'name': r['common_name'], 'lo': n and n['lo'], 'hi': n and n['hi'], 'verdict': v, 'verdict_word': LIGHT_VERDICT[v],
                     'photo': plant_photo(c, r['id'])})
    cover = round(area * s['units'], 1) if area else None
    return {'ppfd': round(p) if p else None, 'dli': dl, 'area_sqft': cover, 'plants': rows, 'room_needed_sqft': round(need, 1),
            'crowded': bool(cover and need > cover * LIGHT_ROOM * 1.1), 'timer_note': light_timer_note(d, s['hours']) if L is not None else ''}

def plant_photo(c, pid):
    r = c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC, id LIMIT 1', (pid,)).fetchone()
    return r[0] if r else None

def light_candidates(c):
    """Plants that live inside or are going inside for the winter."""
    q = "SELECT * FROM plants WHERE status='active' AND (site IN (%s) OR winter_plan='Move indoors') ORDER BY code" % ','.join('?' * len(INSIDE_SITES))
    return c.execute(q, INSIDE_SITES).fetchall()

LIGHT_ROOM = 1.5     # a light lights usefully about this much more than the circle its maker measured (the edges get less, but enough)

def light_plan(c, lights, spots_used, assigned):
    """A suggested layout for plants that are not in a spot yet. Each free unit of a light can be one spot with one
    setting. Plants needing the most light are placed first. A plant joins a suggested spot when its light needs overlap
    with everyone already there and there is room under the light (area it lights at that distance, against each pot's
    size), adding another unit of the same light if one is free; otherwise it starts a new spot under the smallest of your
    lights that can give it enough."""
    free = {L['id']: max(0, L['count'] - spots_used.get(L['id'], 0)) for L in lights}
    specs = {L['id']: light_specs(L) for L in lights}
    todo = [r for r in light_candidates(c) if r['code'] not in assigned and plant_need(r)]
    todo.sort(key=lambda r: (-plant_need(r)['target'], r['code']))
    foot = lambda r: LIGHT_FOOTPRINT.get((r['pot_size'] or '').split(':')[0], 1.0)
    slots, unplaced = [], []

    def fit(L, lo, hi, used, units, maxu=None):
        """Setting for a spot under light L serving [lo, hi] with `used` square feet of pots, and how many units it then
        needs (None if it cannot). Aims near the middle of the range; when that needs more units than `maxu`, it aims
        lower, which raises the light so it covers more."""
        first = None
        for frac in (0.45, 0.3, 0.15, 0.05):
            st = light_setting(specs[L['id']], round(lo + (hi - lo) * frac, 1), lo, hi)
            if not st or st['reach'] != 'ok': continue
            need = max(units, math.ceil(used / ((st['area_sqft'] or 1.0) * LIGHT_ROOM) - 1e-9))
            if first is None: first = (st, need)
            if maxu is None or need <= maxu: return st, need
        return first if first else (None, None)

    for r in todo:
        n, f = plant_need(r), foot(r)
        best = None
        for sl in slots:
            lo, hi = max(sl['lo'], n['lo']), min(sl['hi'], n['hi'])
            if lo > hi: continue
            st, units = fit(sl['L'], lo, hi, sl['used'] + f, sl['units'], sl['units'] + free[sl['L']['id']])
            if st is None or units - sl['units'] > free[sl['L']['id']]: continue
            key = (units - sl['units'], specs[sl['L']['id']].get('watts') or 999)
            if best is None or key < best[0]: best = (key, sl, lo, hi, units)
        if best and best[0][0] == 0:
            pass                                     # joins a spot without needing another light
        else:
            new = None
            for L in lights:
                if not free[L['id']]: continue
                st, units = fit(L, n['lo'], n['hi'], f, 1, free[L['id']])
                if st is None or units > free[L['id']]: continue
                dmin = light_range(light_points(specs[L['id']]))[0]
                strain = (st['hours'] > 14) + (st['distance_in'] <= dmin + 1)       # only reaches it at its limits
                key = (strain, specs[L['id']].get('watts') or 999, L['id'])
                if new is None or key < new[2]: new = (L, units, key)
            if new and (best is None or (specs[new[0]['id']].get('watts') or 999) <= (specs[best[1]['L']['id']].get('watts') or 999)):
                L, units, _ = new
                free[L['id']] -= units
                slots.append({'L': L, 'lo': n['lo'], 'hi': n['hi'], 'used': f, 'units': units, 'members': [r]})
                continue
        if best:
            _, sl, lo, hi, units = best
            free[sl['L']['id']] -= units - sl['units']
            sl.update(lo=lo, hi=hi, used=sl['used'] + f, units=units); sl['members'].append(r)
            continue
        strongest = max((dli_of(ppfd_at(light_points(specs[L['id']]), light_range(light_points(specs[L['id']]))[0]), 16)
                         for L in lights if light_points(specs[L['id']])), default=0)
        why = ('None of your lights can give it %g mol/day: the strongest gives about %g at its closest, 16 hours a day.' % (n['lo'], strongest)
               if strongest < n['lo'] else 'The lights that suit it are full in this layout. Another light, a spot already set up with room, or a bright window would do.')
        unplaced.append({'code': r['code'], 'name': r['common_name'], 'lo': n['lo'], 'hi': n['hi'], 'why': why, 'photo': plant_photo(c, r['id'])})
    out = []
    for sl in slots:
        L, g = sl['L'], sl['members']
        st, _ = fit(L, sl['lo'], sl['hi'], sl['used'], sl['units'], sl['units'])
        st = st or light_setting(specs[L['id']], (sl['lo'] + sl['hi']) / 2)
        s = {'units': sl['units'], 'distance_in': st['distance_in'], 'hours': st['hours'], 'dim_pct': st['dim_pct']}
        ev = spot_eval(c, s, L, g)
        out.append({**s, 'light_id': L['id'], 'light': L['name'], 'band': spot_band(g), 'codes': [x['code'] for x in g], **ev})
    out.sort(key=lambda s: (-(s['dli'] or 0), s['light']))
    seen = {}
    for sp in out:                                   # "Bright light 1", "Medium light 2" ...: Ethan renames them to the room or shelf
        seen[sp['band']] = seen.get(sp['band'], 0) + 1
        sp['name'] = '%s light %d' % (sp['band'], seen[sp['band']])
    return out, unplaced

def spot_band(g):
    lo = min(plant_need(x)['lo'] for x in g)
    return 'Bright' if lo >= 12 else 'Medium' if lo >= 6 else 'Low'

def outdoor_dli(c):
    """Average daily light over the last 7 observed days at home, open sky (mol/m2/day), from the weather's solar radiation."""
    L = home_place(c)
    rows = c.execute("SELECT data FROM weather_daily WHERE loc_id=? AND kind='observed' ORDER BY date DESC LIMIT 7", (L['id'],)).fetchall()
    vals = []
    for (x,) in rows:
        try: v = (json.loads(x) or {}).get('shortwave_radiation_sum')
        except ValueError: v = None
        if v is not None: vals.append(v * PAR_PER_WM2)       # MJ/m2 of sunlight -> mol/m2 of PAR (same 2.1 factor as hourly)
    avg = sum(vals) / len(vals) if vals else None
    return round(avg, 1) if avg is not None and avg <= 75 else None      # above 75 mol/m2 a day is not possible outdoors: bad data

def step_down(L, s, plants, outdoor):
    """Easing plants from outdoor light into this spot: the first week as bright as the light allows without going over
    any plant's high, then halfway, then the spot's own setting."""
    d = light_specs(L)
    ns = [plant_need(r) for r in plants if plant_need(r)]
    if not ns: return []
    hi = min(n['hi'] for n in ns)
    pts = light_points(d)
    final = dli_of(ppfd_at(pts, s['distance_in']), s['hours'], s['dim_pct'])
    first = light_setting(d, hi * 0.95, None, hi, hours_first=16)
    if not first or first['dli'] < final * 1.2: return []
    mid = light_setting(d, round((first['dli'] + final) / 2, 1), None, hi, hours_first=14)
    steps = []
    if any(r['site'] == 'Outdoors' for r in plants) and outdoor and outdoor > hi * 1.5:
        steps.append({'when': 'Before moving in', 'text': 'Give the plants that are out in the open 5 to 7 days on the covered porch or in bright shade first, so the drop in light is smaller.'})
    for when, st in (('First week inside', first), ('Second week', mid)):
        if st: steps.append({'when': when, 'distance_in': st['distance_in'], 'hours': st['hours'], 'dim_pct': st['dim_pct'], 'dli': st['dli'],
                             'text': light_timer_note(d, st['hours'])})
    steps.append({'when': 'From the third week', 'distance_in': s['distance_in'], 'hours': s['hours'], 'dim_pct': s['dim_pct'], 'dli': final,
                  'text': "The spot's own setting."})
    return steps

def lights_state(c):
    lights = c.execute('SELECT * FROM lights ORDER BY sort, id').fetchall()
    byid = {L['id']: L for L in lights}
    spots = c.execute('SELECT * FROM light_spots ORDER BY id').fetchall()
    used = {}
    for s in spots: used[s['light_id']] = used.get(s['light_id'], 0) + s['units']
    assign = {}
    for code, sid in c.execute('SELECT plant_code, spot_id FROM light_assign'): assign.setdefault(sid, []).append(code)
    assigned = {code for codes in assign.values() for code in codes}
    outdoor = outdoor_dli(c)
    out_spots = []
    for s in spots:
        ps = [r for r in (c.execute('SELECT * FROM plants WHERE code=?', (code,)).fetchone() for code in assign.get(s['id'], [])) if r]
        L = byid.get(s['light_id'])
        ev = spot_eval(c, s, L, ps)
        out_spots.append({'id': s['id'], 'name': s['name'], 'light_id': s['light_id'], 'light': L['name'] if L else 'A light that was removed',
                          'place_id': s['place_id'], 'place': place_label(c, s['place_id']),
                          'units': s['units'], 'distance_in': s['distance_in'], 'hours': s['hours'], 'dim_pct': s['dim_pct'], 'notes': s['notes'],
                          'steps': step_down(L, s, ps, outdoor) if L else [], **ev})
    plan, unplaced = light_plan(c, lights, used, assigned)
    for p in plan:
        p['steps'] = step_down(byid[p['light_id']], p, [c.execute('SELECT * FROM plants WHERE code=?', (x,)).fetchone() for x in p['codes']], outdoor)
    cands = [{'code': r['code'], 'name': r['common_name'], 'site': r['site'], 'winter_plan': r['winter_plan'], 'need': plant_need(r),
              'pot_size': r['pot_size']} for r in light_candidates(c)]
    places = [{'id': r['id'], 'room': r['room'], 'name': r['name'], 'label': r['room'] + (', ' + r['name'] if r['name'] else ''),
               'spots': [s['id'] for s in out_spots if s['place_id'] == r['id']]}
              for r in c.execute('SELECT * FROM indoor_places ORDER BY sort, id')]
    return {'lights': [light_dict(L, used.get(L['id'], 0)) for L in lights], 'spots': out_spots, 'plan': plan, 'unplaced': unplaced, 'places': places,
            'candidates': cands, 'assigned': {code: sid for sid, codes in assign.items() for code in codes}, 'outdoor_dli': outdoor,
            'verdicts': LIGHT_VERDICT}

@app.route('/api/lights')
def lights_get():
    """Everything the Grow lights page shows: your lights, your spots, a suggested layout for the rest, and the step-down plans.
    ?plant=CODE gives just that plant's spot (or suggestion), for its own page."""
    c = db()
    st = lights_state(c)
    code = request.args.get('plant')
    if not code: return jsonify(st)
    sid = st['assigned'].get(code)
    spot = next((s for s in st['spots'] if s['id'] == sid), None) if sid else None
    sug = next((s for s in st['plan'] if code in s['codes']), None)
    un = next((u for u in st['unplaced'] if u['code'] == code), None)
    return jsonify(spot=spot, suggestion=sug, unplaced=un, candidate=any(x['code'] == code for x in st['candidates']), lights=len(st['lights']))

@app.route('/api/lights/preview')
def lights_preview():
    """Light at the leaves for a spot that is being set up: ?light=ID&distance=IN&hours=H&dim=PCT&units=N&plants=P-001,P-002"""
    c = db()
    try: lid = int(request.args.get('light', 0))
    except ValueError: abort(400, 'light must be a number')
    L = c.execute('SELECT * FROM lights WHERE id=?', (lid,)).fetchone()
    if not L: abort(404, 'That light is not in your list')
    s = spot_fields(request.args, partial=True)
    codes = [x for x in (request.args.get('plants') or '').split(',') if x]
    ps = [r for r in (c.execute('SELECT * FROM plants WHERE code=?', (x,)).fetchone() for x in codes) if r]
    return jsonify(spot_eval(c, s, L, ps))

def spot_fields(b, partial=False):
    name = re.sub(r'\s+', ' ', str(b.get('name', ''))).strip()[:60]
    if not name and not partial: abort(400, 'Give the spot a name, for example "Living room shelf"')
    units = int(_num(b, 'units', 1, 50, 'How many of this light') or 1)
    dist = _num(b, 'distance', 1, 120, 'Distance from the leaves (inches)', required=True)
    hours = _num(b, 'hours', 1, 24, 'Hours a day', required=True)
    dim = int(_num(b, 'dim', 1, 100, 'Brightness (%)') or 100)
    place = b.get('place')
    try: place = int(place) if place not in (None, '', 'null') else None
    except (TypeError, ValueError): abort(400, 'Choose a room or shelf from the list')
    return {'name': name, 'units': units, 'distance_in': dist, 'hours': hours, 'dim_pct': dim, 'notes': str(b.get('notes', '')).strip()[:300], 'place_id': place}

def spot_text(s, light_name, c=None):
    where = place_label(c, s['place_id']) if c is not None and s['place_id'] else None
    return '%s%s: %s%s, %g in from the leaves, %g hours a day%s' % (s['name'], ' (%s)' % where if where else '', '%d x ' % s['units'] if s['units'] > 1 else '', light_name,
                                                                    s['distance_in'], s['hours'], '' if s['dim_pct'] == 100 else ', %d%% brightness' % s['dim_pct'])

def place_label(c, pid):
    r = c.execute('SELECT room, name FROM indoor_places WHERE id=?', (pid,)).fetchone() if pid else None
    return (r['room'] + (', ' + r['name'] if r['name'] else '')) if r else None

def check_place(c, pid):
    if pid is not None and not c.execute('SELECT 1 FROM indoor_places WHERE id=?', (pid,)).fetchone(): abort(400, 'That room or shelf is not in the list any more')

def set_spot_plants(c, sid, spot_name, codes, who):
    old = {x for (x,) in c.execute('SELECT plant_code FROM light_assign WHERE spot_id=?', (sid,))}
    new = set(codes)
    for code in sorted(new - old):
        r = c.execute('SELECT id, code FROM plants WHERE code=?', (code,)).fetchone()
        if not r: abort(400, f'There is no plant {code}')
        prev = c.execute('SELECT s.name FROM light_assign a JOIN light_spots s ON s.id=a.spot_id WHERE a.plant_code=?', (code,)).fetchone()
        c.execute('INSERT OR REPLACE INTO light_assign(plant_code,spot_id,assigned_by,assigned_at) VALUES(?,?,?,?)', (code, sid, who, now()))
        audit_only(c, 'light', 'grow_light', prev[0] if prev else None, spot_name, who, 'Grow light: now in the spot ' + spot_name, r['id'], code)
    for code in sorted(old - new):
        r = c.execute('SELECT id FROM plants WHERE code=?', (code,)).fetchone()
        c.execute('DELETE FROM light_assign WHERE plant_code=? AND spot_id=?', (code, sid))
        audit_only(c, 'light', 'grow_light', spot_name, None, who, 'Grow light: taken out of the spot ' + spot_name, r['id'] if r else None, code)

@app.route('/api/lights/spots', methods=['POST'])
def light_spot_add():
    """Set up a spot: {name, light, units, distance, hours, dim, notes, plants: [codes]}"""
    c = db()
    b = request.get_json(silent=True) or {}
    s = spot_fields(b)
    L = c.execute('SELECT * FROM lights WHERE id=?', (int(_num(b, 'light', 1, 1e9, 'Light', required=True)),)).fetchone()
    if not L: abort(400, 'Choose one of your lights')
    who = editor()
    check_place(c, s['place_id'])
    sid = c.execute('INSERT INTO light_spots(name,light_id,units,distance_in,hours,dim_pct,notes,place_id,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)',
                    (s['name'], L['id'], s['units'], s['distance_in'], s['hours'], s['dim_pct'], s['notes'], s['place_id'], who, now())).lastrowid
    audit_only(c, 'light', 'light_spot', None, spot_text(s, L['name'], c), who, 'Grow light spot set up: ' + spot_text(s, L['name'], c))
    set_spot_plants(c, sid, s['name'], [str(x) for x in b.get('plants') or []], who)
    c.commit()
    return jsonify(id=sid), 201

@app.route('/api/lights/spots/<int:i>', methods=['PUT', 'DELETE'])
def light_spot_one(i):
    c = db()
    old = c.execute('SELECT * FROM light_spots WHERE id=?', (i,)).fetchone()
    if not old: abort(404, 'That spot is not set up any more')
    L0 = c.execute('SELECT name FROM lights WHERE id=?', (old['light_id'],)).fetchone()
    who = editor()
    if request.method == 'DELETE':
        set_spot_plants(c, i, old['name'], [], who)
        c.execute('DELETE FROM light_spots WHERE id=?', (i,))
        audit_only(c, 'light', 'light_spot', spot_text(old, L0[0] if L0 else 'light', c), None, who, 'Grow light spot removed: ' + old['name'])
        c.commit()
        return jsonify(ok=True)
    b = request.get_json(silent=True) or {}
    s = spot_fields(b)
    L = c.execute('SELECT * FROM lights WHERE id=?', (int(_num(b, 'light', 1, 1e9, 'Light', required=True)),)).fetchone()
    if not L: abort(400, 'Choose one of your lights')
    check_place(c, s['place_id'])
    c.execute('UPDATE light_spots SET name=?,light_id=?,units=?,distance_in=?,hours=?,dim_pct=?,notes=?,place_id=?,updated_by=?,updated_at=? WHERE id=?',
              (s['name'], L['id'], s['units'], s['distance_in'], s['hours'], s['dim_pct'], s['notes'], s['place_id'], who, now(), i))
    a, z = spot_text(old, L0[0] if L0 else 'light', c), spot_text(s, L['name'], c)
    if a != z: audit_only(c, 'light', 'light_spot', a, z, who, 'Grow light spot changed: ' + z)
    if 'plants' in b: set_spot_plants(c, i, s['name'], [str(x) for x in b.get('plants') or []], who)
    c.commit()
    return jsonify(ok=True)

def place_fields(b):
    room = re.sub(r'\s+', ' ', str(b.get('room', ''))).strip()[:60]
    if not room: abort(400, 'Type the room, for example "Downstairs Living Room"')
    return room, re.sub(r'\s+', ' ', str(b.get('name', ''))).strip()[:60]

@app.route('/api/lights/places', methods=['POST'])
def light_place_add():
    """A room, or a shelf or table in a room, where light spots can go: {room, name}. Leave name empty for the room itself."""
    c = db()
    room, name = place_fields(request.get_json(silent=True) or {})
    if c.execute('SELECT 1 FROM indoor_places WHERE room=? AND name=?', (room, name)).fetchone(): abort(409, f'"{room}{", " + name if name else ""}" is already in the list')
    who = editor()
    n = c.execute('SELECT COALESCE(MAX(sort),0)+1 FROM indoor_places').fetchone()[0]
    pid = c.execute('INSERT INTO indoor_places(room,name,sort,created_by,created_at) VALUES(?,?,?,?,?)', (room, name, n, who, now())).lastrowid
    audit_only(c, 'light', 'indoor_place', None, place_label(c, pid), who, 'Room or shelf added: ' + place_label(c, pid))
    c.commit()
    return jsonify(id=pid), 201

@app.route('/api/lights/places/<int:i>', methods=['PUT', 'DELETE'])
def light_place_one(i):
    c = db()
    old = place_label(c, i)
    if not old: abort(404, 'That room or shelf is not in the list')
    who = editor()
    if request.method == 'DELETE':
        n = c.execute('SELECT COUNT(*) FROM light_spots WHERE place_id=?', (i,)).fetchone()[0]
        c.execute('UPDATE light_spots SET place_id=NULL WHERE place_id=?', (i,))
        c.execute('DELETE FROM indoor_places WHERE id=?', (i,))
        audit_only(c, 'light', 'indoor_place', old, None, who, 'Room or shelf removed: %s%s' % (old, ' (%d spot%s there now say "Not chosen yet")' % (n, 's' if n != 1 else '') if n else ''))
        c.commit()
        return jsonify(ok=True)
    room, name = place_fields(request.get_json(silent=True) or {})
    if c.execute('SELECT 1 FROM indoor_places WHERE room=? AND name=? AND id<>?', (room, name, i)).fetchone(): abort(409, f'"{room}{", " + name if name else ""}" is already in the list')
    c.execute('UPDATE indoor_places SET room=?, name=? WHERE id=?', (room, name, i))
    audit_only(c, 'light', 'indoor_place', old, place_label(c, i), who, 'Room or shelf renamed: ' + place_label(c, i))
    c.commit()
    return jsonify(ok=True)

def light_fields(b, old=None):
    d = dict(old or {})
    name = re.sub(r'\s+', ' ', str(b.get('name', ''))).strip()[:80]
    if not name: abort(400, 'Type the name of the light')
    count = int(_num(b, 'count', 0, 100, 'How many you have', required=True))
    if 'watts' in b: d['watts'] = _num(b, 'watts', 0, 2000, 'Watts')
    if 'points' in b:                  # "12 in 719, 24 in 234 ..." or "12: 719 (0.5 sq ft)"
        pts = []
        for part in re.split(r'[,;\n]+', str(b.get('points') or '')):
            nums = [float(x) for x in re.findall(r'\d+(?:\.\d+)?', part)]
            if not part.strip(): continue
            if len(nums) < 2: abort(400, f'"{part.strip()}" needs a distance in inches and a PPFD, like "12 in 719"')
            pts.append([nums[0], nums[1], nums[2] if len(nums) > 2 else None])
        d['ppfd'] = pts
    if 'kind' in b: d['kind'] = str(b.get('kind') or '').strip()[:40]
    if 'model' in b: d['model'] = str(b.get('model') or '').strip()[:80]       # 1.13.1: the maker's model number
    if 'timer' in b: d['timer'] = str(b.get('timer') or '').strip()[:120]
    if 'dimming' in b: d['dimming'] = sorted({int(x) for x in re.findall(r'\d+', str(b.get('dimming') or '')) if 0 < int(x) <= 100}) or [100]
    return name, count, str(b.get('fixture', '')).strip()[:120], str(b.get('notes', '')).strip()[:600], d

def light_text(name, count, fixture):
    return '%s (%d)%s' % (name, count, ', ' + fixture if fixture else '')

@app.route('/api/lights', methods=['POST'])
def light_add():
    """A light you have: {name, count, watts, points, kind, timer, dimming, fixture, notes}"""
    c = db()
    name, count, fixture, notes, d = light_fields(request.get_json(silent=True) or {})
    if c.execute('SELECT 1 FROM lights WHERE name=?', (name,)).fetchone(): abort(409, f'"{name}" is already in your lights')
    who = editor()
    lid = c.execute('INSERT INTO lights(lkey,name,data,count,fixture,notes,sort,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
                    (None, name, json.dumps(d), count, fixture, notes, 1000, who, now())).lastrowid
    audit_only(c, 'light', 'light', None, light_text(name, count, fixture), who, 'Grow light added: ' + light_text(name, count, fixture))
    c.commit()
    return jsonify(id=lid), 201

@app.route('/api/lights/<int:i>', methods=['PUT', 'DELETE'])
def light_one(i):
    c = db()
    old = c.execute('SELECT * FROM lights WHERE id=?', (i,)).fetchone()
    if not old: abort(404, 'That light is not in your list')
    who = editor()
    if request.method == 'DELETE':
        n = c.execute('SELECT COUNT(*) FROM light_spots WHERE light_id=?', (i,)).fetchone()[0]
        if n: abort(409, f'"{old["name"]}" is used by {n} spot{"s" if n != 1 else ""}. Change or remove those spots first.')
        c.execute('DELETE FROM lights WHERE id=?', (i,))
        audit_only(c, 'light', 'light', light_text(old['name'], old['count'], old['fixture']), None, who, 'Grow light removed: ' + old['name'])
        c.commit()
        return jsonify(ok=True)
    name, count, fixture, notes, d = light_fields(request.get_json(silent=True) or {}, light_specs(old))
    if c.execute('SELECT 1 FROM lights WHERE name=? AND id<>?', (name, i)).fetchone(): abort(409, f'"{name}" is already in your lights')
    c.execute('UPDATE lights SET name=?,count=?,fixture=?,notes=?,data=?,updated_by=?,updated_at=? WHERE id=?', (name, count, fixture, notes, json.dumps(d), who, now(), i))
    a, z = light_text(old['name'], old['count'], old['fixture']), light_text(name, count, fixture)
    audit_only(c, 'light', 'light', a, z, who, 'Grow light changed: ' + z + ('' if light_specs(old) == d else ' (specs changed)'))
    c.commit()
    return jsonify(ok=True)

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

# ---------------------------------------------------------------- calendar file: feeding days and cold nights (prototype, proto/calendar-file)
# GET /api/calendar.ics makes an iCalendar file to import into a phone, Outlook or Google calendar.
# GET /cal/<token>.ics is the same calendar for subscribing: it needs no password, only the private token in the link, so a
# calendar service on the internet can fetch it (guard() lets /cal/ through; the token is checked here).
# GET /api/calendar gives the events as JSON, for the preview in the "Add to your calendar" window.
# The choices are kept in settings 'ics_options' (GET/PUT /api/calendar/settings), so the file and the subscribed
# calendar always match the window. Query arguments of the same names override them for one request (used by the tests).
ICS_NAME = 'Plant record'
ICS_DEFAULTS = {'feed': True, 'cold': True, 'close': True, 'months': 3, 'weekly': True, 'day': 5,      # day: 0 = Monday ... 5 = Saturday
                'feed_remind': True, 'feed_at': '08:00', 'cold_remind': True, 'cold_at': '16:00', 'public_base': ''}
ICS_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def ics_text(s):
    """Escape text for an iCalendar value (RFC 5545 section 3.3.11)."""
    return str(s).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\r\n', '\n').replace('\n', '\\n')

def ics_fold(line):
    """Fold a content line at 75 octets, as the standard asks; continuation lines start with one space."""
    b = line.encode('utf-8')
    if len(b) <= 75: return line
    out, cur = [], b''
    for ch in line:
        e = ch.encode('utf-8')
        if len(cur) + len(e) > (75 if not out else 74):
            out.append(cur.decode('utf-8')); cur = b''
        cur += e
    out.append(cur.decode('utf-8'))
    return '\r\n '.join(out)

def ics_season(r, m):
    a, b = r['fert_from_month'], r['fert_to_month']
    return a <= m <= b if a <= b else (m >= a or m <= b)

def ics_season_start(r, d):
    """The first day on or after d that falls in the plant's feeding season (d itself when it already does)."""
    for _ in range(14):
        if ics_season(r, d.month): return d
        d = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
    return d

def ics_feed_days(c, today, end, weekday=None):
    """Projected feeding days per plant, the same way the Fertilizer page works out "Next feeding" (nextDue() in app.js),
    then every "Feed every (days)" after that, skipping the resting months. Later dates assume each feeding is done on time.
    With a weekday (0 = Monday), each feeding moves to the first feeding day of the week on or after the day it is due
    (never earlier: Ethan asked that a plant is never fed too early), and the next one is counted from that day, since that
    is when the plant will be fed."""
    last = dict(c.execute('SELECT plant_code, MAX(applied_on) FROM fertilizer_log GROUP BY plant_code').fetchall())
    rows = c.execute("""SELECT code, common_name, fert_from_month, fert_to_month, fert_every_days, site FROM plants WHERE status='active'
                        AND fert_from_month IS NOT NULL AND fert_to_month IS NOT NULL AND fert_every_days IS NOT NULL ORDER BY code""").fetchall()
    first = today + timedelta(days=(weekday - today.weekday()) % 7) if weekday is not None else today
    def snap(d):
        if weekday is None: return d
        return max(d + timedelta(days=(weekday - d.weekday()) % 7), first)    # the feeding day on or after d
    days = {}
    for r in rows:
        every = max(1, int(r['fert_every_days']))
        lf = last.get(r['code'])
        d = date.fromisoformat(lf) + timedelta(days=every) if lf else today
        if d < today: d = today
        for _ in range(400):
            d = snap(ics_season_start(r, d))
            while not ics_season(r, d.month): d += timedelta(days=7)          # snapped back across the start of the season
            if d > end: break
            days.setdefault(d.isoformat(), []).append({'code': r['code'], 'name': r['common_name'], 'every': every, 'last': lf})
            d = d + timedelta(days=every)
    return [{'date': k, 'plants': v} for k, v in sorted(days.items())]

def ics_clean(o):
    """Check and fill in a set of choices; anything missing or wrong falls back to the default."""
    out = dict(ICS_DEFAULTS)
    for k, v in (o or {}).items():
        if k not in ICS_DEFAULTS: continue
        d = ICS_DEFAULTS[k]
        if isinstance(d, bool): out[k] = v if isinstance(v, bool) else str(v).lower() not in ('0', 'false', 'no', '')
        elif k == 'months':
            try: out[k] = min(12, max(1, int(v)))
            except (TypeError, ValueError): abort(400, 'How far ahead must be a number of months from 1 to 12')
        elif k == 'day':
            try: out[k] = int(v) % 7
            except (TypeError, ValueError): abort(400, 'The feeding day must be a day of the week')
        elif k in ('feed_at', 'cold_at'):
            if not re.match(r'^([01]\d|2[0-3]):[0-5]\d$', str(v)): abort(400, 'Reminder times look like 08:00 or 16:30')
            out[k] = str(v)
        elif k == 'public_base':
            v = re.sub(r'/cal$', '', str(v or '').strip().rstrip('/'))          # a pasted link with /cal on the end still works
            if v and not re.match(r'^https?://[A-Za-z0-9.\-]+(:\d+)?(/[\w.\-/]*)?$', v): abort(400, 'The internet address should look like https://your-pc.tail1234.ts.net:8443')
            out[k] = v
    return out

def ics_saved(c):
    try: return ics_clean(json.loads(setting(c, 'ics_options', '{}') or '{}'))
    except ValueError: return dict(ICS_DEFAULTS)

def ics_options(c):
    """The saved choices, with any query arguments of the same names on top."""
    o = ics_saved(c)
    over = {k: request.args[k] for k in ICS_DEFAULTS if k in request.args and k != 'public_base'}
    if 'remind' in request.args: over['feed_remind'] = over['cold_remind'] = request.args['remind']     # older one-switch form
    return ics_clean({**o, **over}) if over else o

def ics_token(c):
    t = setting(c, 'ics_token')
    if not t:
        t = secrets.token_urlsafe(18); set_setting(c, 'ics_token', t); c.commit()
    return t

def ics_use_place():
    """?place=ID works like the X-Place header (see location()), for links that cannot send headers."""
    v = request.args.get('place', '').strip()
    if v.isdigit() and not request.headers.get('X-Place'):
        request.environ['HTTP_X_PLACE'] = v                  # Flask reads headers from the environ, so location() sees it

def ics_events(c, o):
    ics_use_place()
    L = location(c)
    tz = tzinfo(L['tz'])
    today = local_today(c)
    end = today + timedelta(days=round(30.5 * o['months']))
    ev = []
    if o['feed']:
        weekly = o['weekly']
        for f in ics_feed_days(c, today, end, o['day'] if weekly else None):
            ps = f['plants']; n = len(ps)
            names = ', '.join(p['name'] for p in ps[:3]) + (f' and {n - 3} more' if n > 3 else '')
            title = (f'Feeding day: {n} plant{"s" if n != 1 else ""} ({names})' if weekly
                     else f'Feed {n} plant{"s" if n != 1 else ""}: {names}')
            lines = [f'{p["name"]} ({p["code"]}), every {p["every"]} days.' + (f' Last fed {p["last"]}.' if p['last'] else ' No feeding logged yet.') for p in ps]
            desc = (('Your weekly feeding day. These plants are due by now' if weekly else 'Plants due for fertilizer on this day') + ', from Plant record.\n\n' + '\n'.join(lines) +
                    '\n\nOpen the Fertilizer page that morning before you feed: it says "Hold off" when a cold night is coming or a plant is unwell.'
                    ' Later dates assume each feeding is done on the day shown.')
            ev.append({'kind': 'feed', 'uid': f'feed-{f["date"]}', 'date': f['date'], 'title': title, 'desc': desc,
                       'plants': [p['code'] for p in ps], 'path': '#/fertilizer'})
    if o['cold']:
        F = frost_report(c)
        words = {'danger': 'Could die', 'damage': 'Damaged', 'watch': 'Close call'}
        for n in F['nights']:
            at = [x for x in n['plants'] if o['close'] or x['level'] != 'watch']
            if not at: continue
            serious = [x for x in at if x['level'] != 'watch']
            d = date.fromisoformat(n['date'])
            start = datetime.combine(d - timedelta(days=1), datetime.min.time(), tz).replace(hour=18)   # the evening before: lows come just before dawn
            stop = datetime.combine(d, datetime.min.time(), tz).replace(hour=8)
            if stop < datetime.now(tz): continue                 # that night is over
            k = len(at)
            title = (f'Cold night, low {round(n["low"])}°F: protect {len(serious)} plant{"s" if len(serious) != 1 else ""}' if serious
                     else f'Cold night, low {round(n["low"])}°F: {k} close call{"s" if k != 1 else ""}')
            lines = []
            for lv in ('danger', 'damage', 'watch'):
                g = [x for x in at if x['level'] == lv]
                if g: lines.append(words[lv] + ': ' + ', '.join(f'{x["name"]} ({x["code"]})' for x in g) + '.')
            desc = (f'Forecast low of {round(n["low"])}°F before dawn on {d:%A}, {d:%B} {d.day}, in {F["place"]}. These plants are outside:\n\n' + '\n'.join(lines) +
                    f'\n\nMove them in or cover them before dark, then tick them off on the cold-night checklist.'
                    f' "Close call" means within {F["margin"]}°F of the plant\'s damage point. This comes from the forecast of {datetime.now(tz):%B} {datetime.now(tz).day}; forecasts change, so a subscribed calendar is the way to keep this current.')
            ev.append({'kind': 'cold', 'uid': f'cold-{n["date"]}', 'date': n['date'], 'title': title, 'desc': desc, 'level': n['level'] if serious else 'watch',
                       'start': start.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ'), 'end': stop.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
                       'plants': [x['code'] for x in at], 'path': '#/frost'})
    ev.sort(key=lambda e: (e['date'], e['kind']))
    return {'place': L['name'], 'place_id': L['id'], 'today': today.isoformat(), 'until': end.isoformat(), 'options': o, 'events': ev,
            'counts': {'feed': sum(1 for e in ev if e['kind'] == 'feed'), 'cold': sum(1 for e in ev if e['kind'] == 'cold')}}

def ics_body(c, o, E, base):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    host = 'plant-record-' + str(E['place_id'])
    tz = tzinfo(location(c)['tz'])
    fh, fm = map(int, o['feed_at'].split(':')); ch, cm = map(int, o['cold_at'].split(':'))
    out = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Plant record//Calendar file ' + APP_VERSION + '//EN', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
           'X-WR-CALNAME:' + ics_text(ICS_NAME), 'X-WR-CALDESC:' + ics_text('Feeding days and cold nights for ' + E['place']),
           'REFRESH-INTERVAL;VALUE=DURATION:PT6H', 'X-PUBLISHED-TTL:PT6H']
    for e in E['events']:
        out += ['BEGIN:VEVENT', f'UID:{e["uid"]}@{host}', 'DTSTAMP:' + stamp]
        if e['kind'] == 'feed':
            d = date.fromisoformat(e['date'])
            out += ['DTSTART;VALUE=DATE:' + d.strftime('%Y%m%d'), 'DTEND;VALUE=DATE:' + (d + timedelta(days=1)).strftime('%Y%m%d'),
                    'TRANSP:TRANSPARENT', 'CATEGORIES:Plants,Feeding']
        else:
            out += ['DTSTART:' + e['start'], 'DTEND:' + e['end'], 'TRANSP:TRANSPARENT', 'CATEGORIES:Plants,Cold night']
        out += ['SUMMARY:' + ics_text(e['title']), 'DESCRIPTION:' + ics_text(e['desc'] + ('\n\n' + base + e['path'] if base else ''))] + (['URL:' + base + e['path']] if base else [])
        trig = None
        if e['kind'] == 'feed' and o['feed_remind']:
            trig = f'TRIGGER;RELATED=START:PT{fh}H{fm}M'                     # that time on the feeding day
        elif e['kind'] == 'cold' and o['cold_remind']:
            d = date.fromisoformat(e['date']) - timedelta(days=1)            # that time on the day before the cold morning
            at = datetime.combine(d, datetime.min.time(), tz).replace(hour=ch, minute=cm).astimezone(timezone.utc)
            trig = 'TRIGGER;VALUE=DATE-TIME:' + at.strftime('%Y%m%dT%H%M%SZ')
        if trig: out += ['BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:' + ics_text(e['title']), trig, 'END:VALARM']
        out.append('END:VEVENT')
    out.append('END:VCALENDAR')
    return '\r\n'.join(ics_fold(x) for x in out) + '\r\n'

def ics_response(body, filename=None):
    resp = Response(body, mimetype='text/calendar')
    resp.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    resp.headers['Cache-Control'] = 'no-store'
    if filename: resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp

def ics_links(c, o):
    tok = ics_token(c)
    local = setting(c, 'base_url', '') or request.host_url.rstrip('/')        # the address set for labels, when there is one
    return {'local': f'{local}/cal/{tok}.ics', 'public': f'{o["public_base"]}/cal/{tok}.ics' if o['public_base'] else None}

@app.route('/api/calendar')
def calendar_preview():
    c = db(); o = ics_options(c)
    return jsonify(ics_events(c, o) | {'links': ics_links(c, o)})

@app.route('/api/calendar/settings', methods=['GET', 'PUT'])
def calendar_settings():
    c = db()
    if request.method == 'PUT':
        old = ics_saved(c)
        new = ics_clean({**old, **(request.get_json(silent=True) or {})})
        if new != old:
            set_setting(c, 'ics_options', json.dumps(new))
            what = ', '.join(k for k in ICS_DEFAULTS if new[k] != old[k])
            audit_only(c, 'setting', 'ics_options', None, None, editor(), 'Calendar choices changed: ' + what)
            c.commit()
    o = ics_saved(c)
    return jsonify(options=o, links=ics_links(c, o), days=ICS_DAYS)

@app.route('/api/calendar/new-link', methods=['POST'])
def calendar_new_link():
    c = db()
    set_setting(c, 'ics_token', secrets.token_urlsafe(18))
    audit_only(c, 'setting', 'ics_token', None, None, editor(), 'New calendar link made; the old one stopped working')
    c.commit()
    o = ics_saved(c)
    return jsonify(options=o, links=ics_links(c, o))

@app.route('/api/calendar.ics')
def calendar_ics():
    c = db(); o = ics_options(c); E = ics_events(c, o)
    body = ics_body(c, o, E, request.host_url.rstrip('/') + '/')
    return ics_response(body, None if request.args.get('download') == '0' else f'plant-record-calendar-{E["today"]}.ics')

@app.route('/cal/<path:p>')
def calendar_subscribed(p):
    """The subscribed calendar. No password (guard() lets /cal/ through), so the private token is the only key.
    Only the last part of the path counts (<token>.ics), so it works the same behind a proxy that adds or keeps a
    /cal prefix, such as Tailscale Funnel with --set-path=/cal."""
    c = db()
    name = p.rsplit('/', 1)[-1]
    if not name.endswith('.ics') or not hmac.compare_digest(name[:-4].encode(), ics_token(c).encode()): abort(404)
    o = ics_saved(c)
    E = ics_events(c, o)
    # links in the events go to the app itself, which the public address does not open (it only shares /cal/):
    # use the address set for labels, or the one this request came in on unless that is the public one
    pub = urlparse(o['public_base']).hostname if o['public_base'] else None
    base = setting(c, 'base_url', '') or ('' if pub and request.host.split(':')[0] == pub else request.host_url.rstrip('/'))
    base = base + '/' if base else ''
    return ics_response(ics_body(c, o, E, base))

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
