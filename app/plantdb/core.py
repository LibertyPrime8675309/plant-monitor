"""Plant record: the core. The app, its database, helpers, people and security: what every other module needs. Module-level names here are safe to use at import time; the rest are linked by server.py once every module is loaded (see link()).

Plant Database - small Flask + SQLite app.

Everything lives in DATA_DIR (default /data): plants.db, photos/, cache/.
Edits are versioned: every save bumps the plant's page version, writes a full snapshot
to plant_versions and one row per changed field to audit_log (what / before / after / who / when).
"""
import csv, gzip, hmac, html as html_mod, io, ipaddress, json, math, os, re, secrets, shutil, sqlite3, threading, time, urllib.error, urllib.parse, urllib.request, uuid
from datetime import date, datetime, timedelta, timezone
from urllib.parse import urlparse

from flask import Flask, Response, abort, g, has_app_context, has_request_context, jsonify, request, send_from_directory
from PIL import Image, ImageOps
import segno
import writable                 # 1.12.1: the start-up write check, shared with start.py
import shops as SH              # 1.27.0: reading shops for the plants on the wishlist

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))     # app/: static/, seed/, VERSION live beside the plantdb package
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
    ('home_id', 'home', 'Home'),                                                    # 1.28.0: which home it is at (empty: the main home)
    ('area_id', 'area', 'Area or room'), ('spot_id', 'spot', 'Spot'),                # 1.29.0: inside or outside, the area or room, the spot
    ('pot_id', 'pot', 'Pot'), ('tray_id', 'tray', 'Catch tray'),                    # 1.29.0: pots and trays you keep as items
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
    ('heat_zone_high', 'int', 'Heat zone, hottest (AHS)'), ('heat_zone_low', 'int', 'Heat zone, coolest (AHS)'), ('heat_zone_source', 'text', 'Heat zone source'),   # 1.36.0: summer heat
    ('native_range', 'long', 'Native range'), ('conservation_status', 'long', 'Conservation status'), ('invasive', 'long', 'Invasive risk'),
    ('bloom', 'long', 'Flowers'), ('fruit', 'long', 'Fruit'),
    ('danger_humans', 'long', 'Dangers to people'), ('danger_animals', 'long', 'Dangers to pets and other animals'),
    ('propagation', 'list', 'Propagation'), ('sources', 'list', 'Sources'),
    ('pet_safety', 'enum', 'Safety for pets'),                                                          # 1.17.0, for the pets filter
    ('height_in', 'num', 'Height now, with its pot (in)'),                                              # 1.56.0 (PLAN.md step 8c): for fitting it under a shelf or a light
    ('grow_kind', 'enum', 'How it grows'),                                                               # 1.56.0 (PLAN.md step 9): soil mix, semi-hydro or water only
    ('reservoir', 'enum', 'What holds its water'),                                                       # 1.56.0: drains freely, a tray, a catch pot, or the pot itself
    ('mix_wants', 'enum', 'Mix it wants'),                                                               # 1.56.0: fast-draining, balanced or moisture-holding (also a species fact)
    ('browse_risk', 'enum', 'Risk of being eaten by pests (set by you)'),                                # 1.57.0 (browse.py): empty = the usual for this kind of plant
]
BROWSE_RISKS = ['Low', 'Moderate', 'High']
GROW_KINDS = ['Soil mix', 'Semi-hydro', 'Water only']                       # 1.56.0 (PLAN.md step 9); empty means a soil mix
RESERVOIRS = ['Drains freely', 'A tray under it', 'A catch pot', 'The pot itself (no holes)']
MIX_WANTS = ['Fast-draining', 'Balanced', 'Moisture-holding']
MIXES_SCHEMA = '''
CREATE TABLE IF NOT EXISTS amendments(
  id INTEGER PRIMARY KEY AUTOINCREMENT, key TEXT UNIQUE, name TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'part',
  grades TEXT NOT NULL DEFAULT '[]', holds_water INTEGER, airy INTEGER, lasts_months INTEGER, feeds INTEGER, ph INTEGER, weight INTEGER,
  source TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '', created_by TEXT, created_at TEXT, updated_by TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS mix_recipes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, notes TEXT NOT NULL DEFAULT '',
  created_by TEXT, created_at TEXT, updated_by TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS mix_parts(
  id INTEGER PRIMARY KEY AUTOINCREMENT, recipe_id INTEGER NOT NULL, amendment_id INTEGER NOT NULL, grade TEXT NOT NULL DEFAULT '',
  parts REAL, amount TEXT NOT NULL DEFAULT '', sort INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS pot_mixes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, plant_code TEXT NOT NULL, care_id INTEGER, mixed_on TEXT NOT NULL, recipe_id INTEGER,
  parts TEXT NOT NULL DEFAULT '[]', top TEXT NOT NULL DEFAULT '', bottom TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
  created_by TEXT, created_at TEXT);
CREATE INDEX IF NOT EXISTS pot_mixes_code ON pot_mixes(plant_code, mixed_on);
'''
ENUMS = {'grow_kind': GROW_KINDS, 'reservoir': RESERVOIRS, 'mix_wants': MIX_WANTS, 'winter_plan': WINTER_PLANS, 'site': SITES, 'health_rating': HEALTH, 'leaf_type': LEAF_TYPES, 'pot_size': POT_SIZES, 'fert_strength': FERT_STRENGTHS, 'pet_safety': PET_SAFETY, 'browse_risk': BROWSE_RISKS}
OPTIONAL_ENUMS = ('leaf_type', 'pot_size', 'fert_strength', 'pet_safety', 'grow_kind', 'reservoir', 'mix_wants', 'browse_risk')        # may be left as "Not set"
FIELD_NAMES = [f[0] for f in FIELDS]
FIELD_KIND = {f[0]: f[1] for f in FIELDS}
FIELD_LABEL = {f[0]: f[2] for f in FIELDS}
FIELD_LABEL['fertilizer_log'] = 'Fertilizer entry'
INT_RANGES = {'id_confidence': (0, 100), 'temp_ideal_low': (-60, 150), 'temp_ideal_high': (-60, 150), 'heat_zone_high': (1, 12), 'heat_zone_low': (1, 12),
              'temp_damage_below': (-60, 150), 'temp_lethal_below': (-60, 150),
              'humidity_low': (0, 100), 'humidity_high': (0, 100),
              'temp_damage_above': (0, 200), 'par_low': (0, 4000), 'par_high': (0, 4000),
              'soil_moisture_low': (0, 100), 'soil_moisture_high': (0, 100), 'soil_temp_low': (-40, 150), 'soil_temp_high': (-40, 150),
              'fert_from_month': (1, 12), 'fert_to_month': (1, 12), 'fert_every_days': (1, 365),
              'water_every_days': (1, 60)}
NUM_RANGES = {'height_in': (0.5, 600), 'vpd_low': (0, 6), 'vpd_high': (0, 6), 'dli_low': (0, 80), 'dli_high': (0, 80), 'soil_ph_low': (0, 14), 'soil_ph_high': (0, 14)}

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

# 1.57.0: the settings table helpers (in weather.py until then)
def setting(c, key, default=None):
    r = c.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    return r[0] if r else default

def set_setting(c, key, value):
    c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)', (key, value))

@app.teardown_appcontext
def close_db(_):
    c = g.pop('db', None)
    if c: c.close()

SQLTYPE = {'int': 'INTEGER', 'num': 'REAL', 'home': 'INTEGER', 'area': 'INTEGER', 'spot': 'INTEGER', 'pot': 'INTEGER', 'tray': 'INTEGER'}
SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS problems(id INTEGER PRIMARY KEY AUTOINCREMENT, area TEXT NOT NULL, text TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '',
  at TEXT NOT NULL, times INTEGER NOT NULL DEFAULT 1, cleared_at TEXT);
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
CREATE INDEX IF NOT EXISTS readings_src_dev_ts ON readings(source, device, ts);   -- 1.31.0: the weather history is asked for one place at a time
CREATE INDEX IF NOT EXISTS photos_plant ON photos(plant_id, is_primary);
CREATE TABLE IF NOT EXISTS user_prefs(login TEXT NOT NULL, key TEXT NOT NULL, value TEXT, updated_at TEXT, PRIMARY KEY(login, key));
CREATE TABLE IF NOT EXISTS areas(
  id INTEGER PRIMARY KEY AUTOINCREMENT, home_id INTEGER, side TEXT NOT NULL, name TEXT NOT NULL, sheltered INTEGER NOT NULL DEFAULT 0,
  sort INTEGER NOT NULL DEFAULT 0, created_by TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS spots(
  id INTEGER PRIMARY KEY AUTOINCREMENT, area_id INTEGER NOT NULL REFERENCES areas(id), name TEXT NOT NULL, sort INTEGER NOT NULL DEFAULT 0,
  created_by TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS containers(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, name TEXT NOT NULL, shape TEXT NOT NULL DEFAULT 'circle',
  dia_in REAL, len_in REAL, wid_in REAL, height_in REAL, drainage INTEGER, material TEXT NOT NULL DEFAULT '', qty INTEGER NOT NULL DEFAULT 1,
  notes TEXT NOT NULL DEFAULT '', created_by TEXT, created_at TEXT NOT NULL, updated_by TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS container_photos(
  id INTEGER PRIMARY KEY AUTOINCREMENT, container_id INTEGER NOT NULL REFERENCES containers(id) ON DELETE CASCADE, file TEXT NOT NULL,
  is_primary INTEGER NOT NULL DEFAULT 0, added_by TEXT, added_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS lib_areas(
  id INTEGER PRIMARY KEY AUTOINCREMENT, place_id INTEGER UNIQUE NOT NULL, name TEXT NOT NULL, total INTEGER NOT NULL DEFAULT 0,
  checked_at TEXT, added_by TEXT, added_at TEXT NOT NULL);
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
CREATE TABLE IF NOT EXISTS id_rejections(
  id INTEGER PRIMARY KEY AUTOINCREMENT, plant_code TEXT, name TEXT NOT NULL, genus INTEGER NOT NULL DEFAULT 0,
  rejected_by TEXT NOT NULL, rejected_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS id_examples(
  id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL, name TEXT NOT NULL, file TEXT NOT NULL, source TEXT NOT NULL DEFAULT '',
  plant_code TEXT, added_by TEXT NOT NULL, added_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS bulk_changes(
  id INTEGER PRIMARY KEY AUTOINCREMENT, group_id INTEGER, what TEXT NOT NULL, changes TEXT NOT NULL,
  done_by TEXT NOT NULL, done_at TEXT NOT NULL, undone_by TEXT, undone_at TEXT);
""" % ',\n  '.join(f"{n} {SQLTYPE.get(k, 'TEXT')}" for n, k, _ in FIELDS)

JOURNAL = {'mode': None, 'probe': None}   # 1.57.0: the journal mode in use, and what the WAL test found
def wal_works():
    """1.57.0: does WAL work in the data folder? Writes through one connection and reads through another, on a scratch database."""
    path = os.path.join(os.path.dirname(DB_PATH), '.wal-probe.db')
    try:
        for f in (path, path + '-wal', path + '-shm'):
            if os.path.exists(f): os.remove(f)
        a = sqlite3.connect(path, timeout=5); b = None
        try:
            if a.execute('PRAGMA journal_mode=WAL').fetchone()[0].lower() != 'wal': raise RuntimeError('WAL was refused')
            a.execute('CREATE TABLE t(x)'); a.execute('INSERT INTO t VALUES(42)'); a.commit()
            b = sqlite3.connect(path, timeout=5)
            if b.execute('SELECT x FROM t').fetchone() != (42,): raise RuntimeError('a second connection did not see the write')
            a.execute('INSERT INTO t VALUES(43)'); a.commit()
            if b.execute('SELECT COUNT(*) FROM t').fetchone()[0] != 2: raise RuntimeError('a second connection did not see a later write')
        finally:
            if b: b.close()
            a.close()
        JOURNAL['probe'] = 'WAL works in the data folder.'
        return True
    except Exception as e:
        JOURNAL['probe'] = f'WAL was asked for but does not work in the data folder ({e}), so the app uses DELETE.'
        return False
    finally:
        for f in (path, path + '-wal', path + '-shm'):
            try: os.remove(f)
            except OSError: pass
NEWER_DB = {}        # 1.31.0: set when the database was last opened by a newer version than this one; the app then only says so
def init_db():
    c = sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    # WAL can misbehave on Windows bind mounts; the default rollback journal is safe everywhere for a single-process home app.
    # 1.57.0: PLANTDB_JOURNAL=WAL (in .env) lets pages read while a save is being written. It is tried on a scratch copy first; if
    # a second connection cannot see a write there (the shared-memory file does not work on this folder), the app stays on DELETE.
    want = os.environ.get('PLANTDB_JOURNAL', 'DELETE').upper()
    if want == 'WAL' and not wal_works(): want = 'DELETE'
    if want not in ('DELETE', 'WAL', 'TRUNCATE', 'PERSIST'): want = 'DELETE'
    JOURNAL['mode'] = c.execute('PRAGMA journal_mode=' + want).fetchone()[0]
    # 1.31.0: never let an older version change a database a newer one has already upgraded (its tables and columns would be
    # half understood, and its batches could run again). The app starts, but only to say which version to install.
    try:
        r = c.execute("SELECT value FROM settings WHERE key='db_version'").fetchone()
        last = r[0] if r else None
    except sqlite3.OperationalError: last = None
    if last and version_tuple(last) > version_tuple(APP_VERSION) and os.environ.get('PLANTDB_ALLOW_OLDER') != '1':
        NEWER_DB.update(last=last, this=APP_VERSION); print(f'[start] the database was last opened by version {last}, newer than this {APP_VERSION}: refusing to change it', flush=True)
        c.close(); return
    c.executescript(SCHEMA)
    c.executescript(FUNGI_SCHEMA)                 # 1.22.0: mushroom finds, library notes and the wishlist
    fc = {r[1] for r in c.execute('PRAGMA table_info(fungi_finds)')}
    for col in ('habitat', 'stem'):               # 1.51.1 (PLAN.md step 5d): the fields a person uses to check a mushroom lead
        if col not in fc: c.execute(f'ALTER TABLE fungi_finds ADD COLUMN {col} TEXT')
    c.executescript(SYNC_SCHEMA)                  # 1.24.0: changes sent later from devices, and clashes to decide
    c.executescript(FACTS_SCHEMA)                 # 1.27.0: uses, partners, deterrents, propagation and breeding for each species
    c.executescript(SHOPS_SCHEMA)                 # 1.27.0: shops, what they have from the wishlist, and price alerts
    c.executescript(SENSOR_SCHEMA)                # 1.35.0: your sensors: names, where they sit, the plant they are in
    if 'weight_g' not in {r[1] for r in c.execute('PRAGMA table_info(readings)')}: c.execute('ALTER TABLE readings ADD COLUMN weight_g REAL')   # 1.35.0: a weighing cell under the pot
    rc = {r[1] for r in c.execute('PRAGMA table_info(readings)')}
    if 'soil_raw' not in rc: c.execute('ALTER TABLE readings ADD COLUMN soil_raw REAL')          # 1.36.0: the soil probe's raw volts, for calibrating in the app
    sd = {r[1] for r in c.execute('PRAGMA table_info(sensor_devices)')}
    for col in ('cal_dry', 'cal_wet'):
        if col not in sd: c.execute(f'ALTER TABLE sensor_devices ADD COLUMN {col} REAL')
    c.executescript(PUSH_SCHEMA)                  # 1.33.0: devices that get notifications
    c.executescript(SITTER_SCHEMA)                # 1.49.0: plant-sitter sheets shared by link, and the sitter's ticks
    c.executescript(KNOWLEDGE_SCHEMA)             # 1.53.0 (PLAN.md step 6a): one row per species fact, with its source (the facts table)
    c.executescript(BROWSE_SCHEMA)                # 1.57.0: pests seen eating a plant, with pictures as evidence (browse.py)
    c.executescript(MIXES_SCHEMA)                 # 1.56.0 (PLAN.md step 9): amendments, recipes, what is in each pot (mixes.py)
    if 'status' not in {r[1] for r in c.execute('PRAGMA table_info(lights)')}:     # 1.56.0 (PLAN.md step 10b): owned, considering, no longer used
        c.execute("ALTER TABLE lights ADD COLUMN status TEXT NOT NULL DEFAULT 'owned'")
    wl = {r[1] for r in c.execute('PRAGMA table_info(wishlist)')}
    for col, typ in (('max_price', 'REAL'), ('alert_stock', 'INTEGER NOT NULL DEFAULT 0'), ('search_words', "TEXT NOT NULL DEFAULT ''")):
        if col not in wl: c.execute(f'ALTER TABLE wishlist ADD COLUMN {col} {typ}')
    for col, typ in (('kind', "TEXT NOT NULL DEFAULT 'plant'"), ('price_per', "TEXT NOT NULL DEFAULT ''"), ('source', "TEXT NOT NULL DEFAULT ''")):   # 1.30.0: Shopping
        if col not in wl: c.execute(f'ALTER TABLE wishlist ADD COLUMN {col} {typ}')
    if 'home_id' not in {r[1] for r in c.execute('PRAGMA table_info(people)')}: c.execute('ALTER TABLE people ADD COLUMN home_id INTEGER')   # 1.31.0
    shc = {r[1] for r in c.execute('PRAGMA table_info(shops)')}
    for col, typ in SHOP_DETAIL_COLS:                # 1.30.0: where each store is, how to reach it, what it carries
        if col not in shc: c.execute(f'ALTER TABLE shops ADD COLUMN {col} {typ}')
    if 'online' not in shc: c.execute("UPDATE shops SET online=CASE WHEN local=0 OR key='mindseye' THEN 1 ELSE 0 END")
    if 'size' not in {r[1] for r in c.execute('PRAGMA table_info(offers)')}: c.execute("ALTER TABLE offers ADD COLUMN size TEXT NOT NULL DEFAULT ''")
    for i, (k, name, kind, url, pages, local) in enumerate(SH.DEFAULT_SHOPS):
        c.execute('INSERT OR IGNORE INTO shops(key,name,kind,url,pages,local,online,sort) VALUES(?,?,?,?,?,?,?,?)',
                  (k, name, kind, url, json.dumps(pages), int(local), int(not local or k == 'mindseye'), i))
    have = {r[1] for r in c.execute('PRAGMA table_info(plants)')}
    for n, k, _ in FIELDS:                      # upgrade an older database: add any column this version needs
        if n not in have: c.execute(f"ALTER TABLE plants ADD COLUMN {n} {SQLTYPE.get(k, 'TEXT')}")
    if 'extra' not in {r[1] for r in c.execute('PRAGMA table_info(readings)')}: c.execute('ALTER TABLE readings ADD COLUMN extra TEXT')
    if 'plants_here' not in {r[1] for r in c.execute('PRAGMA table_info(locations)')}: c.execute('ALTER TABLE locations ADD COLUMN plants_here INTEGER NOT NULL DEFAULT 0')   # 1.28.0: homes
    lcols = {r[1] for r in c.execute('PRAGMA table_info(locations)')}          # 1.48.0 (PLAN.md step 4b): a home is a site
    if 'country' not in lcols: c.execute("ALTER TABLE locations ADD COLUMN country TEXT NOT NULL DEFAULT ''")      # ISO code, 'US'
    if 'units' not in lcols: c.execute("ALTER TABLE locations ADD COLUMN units TEXT NOT NULL DEFAULT ''")          # a region key (UNIT_REGIONS) or '' for US
    if 'season' not in lcols: c.execute("ALTER TABLE locations ADD COLUMN season TEXT NOT NULL DEFAULT 'temperate'")   # temperate | mild | tropical
    if 'tended' not in lcols: c.execute('ALTER TABLE locations ADD COLUMN tended INTEGER NOT NULL DEFAULT 1')   # 1.58.0: 0 = its plants are cared for outside the app; bulk watering leaves them out
    if 'edit_homes' not in {r[1] for r in c.execute('PRAGMA table_info(people)')}: c.execute("ALTER TABLE people ADD COLUMN edit_homes TEXT NOT NULL DEFAULT ''")   # 1.48.0: an editor limited to some homes (JSON list of ids; '' = all)
    c.execute("UPDATE locations SET country='US' WHERE country='' AND lat BETWEEN 24 AND 50 AND lon BETWEEN -125 AND -66")   # 1.48.0: a first guess for places in the lower 48; editable on Homes and places
    if 'place_id' not in {r[1] for r in c.execute('PRAGMA table_info(light_spots)')}: c.execute('ALTER TABLE light_spots ADD COLUMN place_id INTEGER')   # 1.13.1
    lsc = {r[1] for r in c.execute('PRAGMA table_info(light_spots)')}           # 1.56.0 (PLAN.md step 8): which level, what a bulb screws into, set up and checked
    for col, typ in (('level', "TEXT NOT NULL DEFAULT ''"), ('holder', "TEXT NOT NULL DEFAULT ''"), ('checked_at', 'TEXT'), ('checked_by', 'TEXT'), ('checked_note', 'TEXT'), ('checked_sig', 'TEXT')):
        if col not in lsc: c.execute(f'ALTER TABLE light_spots ADD COLUMN {col} {typ}')
    for tbl in ('areas', 'spots'):                                               # 1.56.0: a room's or shelf's measurements (fit.py)
        if 'sheet' not in {r[1] for r in c.execute(f'PRAGMA table_info({tbl})')}: c.execute(f"ALTER TABLE {tbl} ADD COLUMN sheet TEXT NOT NULL DEFAULT ''")
    c.execute('''CREATE TABLE IF NOT EXISTS place_photos(
      id INTEGER PRIMARY KEY AUTOINCREMENT, area_id INTEGER NOT NULL, spot_id INTEGER, file TEXT NOT NULL, caption TEXT NOT NULL DEFAULT '',
      is_primary INTEGER NOT NULL DEFAULT 0, added_by TEXT, added_at TEXT NOT NULL)''')                    # 1.56.0: photos of rooms and shelves
    migrate_places(c)
    where_seed(c)                                       # 1.29.0: areas and spots for every home
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
    where_seed(c)                                       # 1.29.0: homes and plants that batches just added get their areas too
    c.execute("UPDATE plants SET site='Outdoors' WHERE site IS NULL OR site=''")   # 1.7.0: every existing plant starts out as Outdoors
    c.commit()
    repair_seed_photos(c)
    facts_migrate(c)                                    # 1.53.0: the facts table, loaded once from what the record already knows
    backup_photos_once(c)                               # 1.58.0: automatic backups include the photos (a saved "no" is switched once)
    c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('db_version',?)", (APP_VERSION,)); c.commit()
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

def batch_pot_mix(c, m, r, care_id, who, ts, label):
    """Record what a pot is in from a batch ({mixed_on, parts: [{key, grade?, parts}], top?, bottom?, notes}); r is the plant's row.
    Used by pot_mixes_add (by code, only where nothing is recorded) and by a new page's own pot_mix (C9)."""
    am = {k: (i, n, ro) for i, k, n, ro in c.execute('SELECT id, key, name, role FROM amendments')}
    parts = [{'amendment_id': am[x['key']][0], 'name': am[x['key']][1], 'role': am[x['key']][2], 'grade': x.get('grade', ''), 'parts': x.get('parts'), 'amount': x.get('amount', '')}
             for x in m.get('parts', []) if x['key'] in am]
    lay = lambda L: json.dumps({'amendment_id': am[L['key']][0], 'name': am[L['key']][1], 'grade': L.get('grade', ''), 'depth_in': L.get('depth_in')}) if L and L.get('key') in am else ''
    c.execute('INSERT INTO pot_mixes(plant_code,care_id,mixed_on,parts,top,bottom,notes,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)',
              (r['code'], care_id, m.get('mixed_on') or ts[:10], json.dumps(parts), lay(m.get('top')), lay(m.get('bottom')), m.get('notes', ''), who, ts))
    audit_only(c, 'mixes', 'pot_mix', None, ', '.join(f"{x['parts']:g} {x['name'].lower()}" for x in parts if x.get('parts')), who,
               '%s (batch %s)' % ('Repotted' if care_id else 'What it is in', label), r['id'], r['code'])

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
        label = b['id']; new_requests = []
        try:
            c.execute('BEGIN')
            for h in b.get('homes_add', []):                 # 1.28.0: another home where plants live (skipped if a place is already there)
                r = c.execute('SELECT id FROM locations WHERE ABS(lat-?)<0.05 AND ABS(lon-?)<0.05', (h['lat'], h['lon'])).fetchone()
                if r: c.execute('UPDATE locations SET plants_here=1 WHERE id=?', (r[0],)); continue
                hid = c.execute('INSERT INTO locations(name,lat,lon,tz,enabled,is_home,plants_here,created_at,tended) VALUES(?,?,?,?,1,0,1,?,?)',
                                (h['name'], h['lat'], h['lon'], h['tz'], ts, 0 if h.get('tended') is False else 1)).lastrowid
                c.execute('UPDATE locations SET device=? WHERE id=?', (f'place-{hid}', hid))
                audit_only(c, 'setting', 'weather_place', None, json.dumps(h), who, f'Home added ({label}): {h["name"]}')
            for h in b.get('homes_update', []):              # 1.58.0: a home found by its place; each field says the value it expects to replace
                r = c.execute('SELECT * FROM locations WHERE ABS(lat-?)<0.05 AND ABS(lon-?)<0.05', (h['lat'], h['lon'])).fetchone()
                if not r: continue                                # not there (yet): nothing to change
                for k, (old, new) in (h.get('fields') or {}).items():
                    if k not in ('tended',): raise ValueError(f'homes_update cannot change {k}')
                    if int(r[k]) != int(old): continue           # changed since (by hand on Homes and places): left alone
                    c.execute(f'UPDATE locations SET {k}=? WHERE id=?', (int(new), r['id']))
                    audit_only(c, 'setting', 'weather_place', json.dumps({k: old}), json.dumps({k: new}), who, f'{r["name"]}: ' + ('care is logged in the app' if new else 'cared for outside the app') + f' ({label})')
            for p in b.get('plants', []):
                n = c.execute("SELECT COALESCE(MAX(CAST(SUBSTR(code,3) AS INTEGER)),0)+1 FROM plants").fetchone()[0]
                code = f'P-{n:03d}'
                cols = ['code'] + FIELD_NAMES + ['version', 'status', 'created_at', 'created_by', 'updated_at', 'updated_by']
                tp = p['dated'] + 'T12:00:00Z' if p.get('dated') else ts      # C9: a page can carry the date it really dates from (the photos')
                if p.get('home_near'):                                          # C9: the home it lives at, found by its place (added by homes_add above)
                    hm = c.execute('SELECT id FROM locations WHERE ABS(lat-?)<0.05 AND ABS(lon-?)<0.05', (p['home_near']['lat'], p['home_near']['lon'])).fetchone()
                    if hm: p = {**p, 'home_id': hm[0]}
                p = {**p, 'site': p.get('site') or 'Outdoors'}          # so later batches in the same start-up can expect it
                vals = [code] + [p.get(k) for k in FIELD_NAMES] + [1, 'active', tp, who, tp, who]
                pid = c.execute(f"INSERT INTO plants({','.join(cols)}) VALUES({','.join('?' * len(cols))})", vals).lastrowid
                for ph in p.get('photos', []):
                    copy_seed_photo(ph['file'])
                    c.execute("INSERT INTO photos(plant_id,file,caption,kind,is_primary,source_name,added_by,added_at) VALUES(?,?,?,?,?,?,?,?)",
                              (pid, ph['file'], ph['caption'], 'plant', 1 if ph['primary'] else 0, ph.get('source'), who, tp))
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
                          (pid, 1, json.dumps(snapshot(c, pid)), who, tp, 'Initial record from photo analysis (%s)' % label))
                c.execute("INSERT INTO audit_log(plant_id,plant_code,version,action,field,old_value,new_value,changed_by,changed_at,note) VALUES(?,?,?,?,?,?,?,?,?,?)",
                          (pid, code, 1, 'create', None, None, None, who, tp, 'Record created from photos (%s)' % label))
                # C9: a new page can come with its own care log and potting mix (a repot logged with the mix it was done with)
                care_id = None
                for cl in p.get('care', []):
                    cid = c.execute('INSERT INTO care_log(plant_code,kind,done_on,note,created_by,created_at) VALUES(?,?,?,?,?,?)',
                                    (code, cl['kind'], cl['done_on'], cl.get('note', ''), who, tp)).lastrowid
                    if cl['kind'] == 'repot': care_id = cid
                if p.get('pot_mix'): batch_pot_mix(c, p['pot_mix'], {'code': code, 'id': pid}, care_id, who, tp, label)
                for q in p.get('requests', []):                 # questions for Ethan about this new page, shown on it until he answers
                    if c.execute('INSERT OR IGNORE INTO requests(rkey,plant_code,kind,text,created_by,created_at) VALUES(?,?,?,?,?,?)',
                                 (q['key'], code, q.get('kind', 'question'), q['text'], who, ts)).rowcount: new_requests.append({'plant_code': code, 'text': q['text']})
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
                if c.execute('INSERT OR IGNORE INTO requests(rkey,plant_code,kind,text,created_by,created_at) VALUES(?,?,?,?,?,?)',
                             (q['key'], code, q.get('kind', 'question'), q['text'], who, ts)).rowcount: new_requests.append({'plant_code': code, 'text': q['text']})
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
            for sh in b.get('shops_add', []):                   # 1.30.0: a store, added once (skipped if its key is there already)
                if c.execute('SELECT 1 FROM shops WHERE key=?', (sh['key'],)).fetchone(): continue
                hid = None
                if sh.get('home'):
                    hr = c.execute('SELECT id, is_home FROM locations WHERE name=? AND (is_home=1 OR plants_here=1)', (sh['home'],)).fetchone()
                    if not hr: continue                                  # that home is not set up here
                    hid = None if hr['is_home'] else hr['id']
                n = c.execute('SELECT COALESCE(MAX(sort),0)+1 FROM shops').fetchone()[0]
                c.execute('INSERT INTO shops(key,name,kind,url,pages,local,online,home_id,address,phone,hours,email,website,carries,details_src,details_at,sort) '
                          'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                          (sh['key'], sh['name'], sh.get('kind', 'auto'), sh['url'], json.dumps(sh.get('pages', [])), int(sh.get('local', 1)), int(sh.get('online', 0)), hid,
                           sh.get('address', ''), sh.get('phone', ''), sh.get('hours', ''), sh.get('email', ''), sh.get('website', ''),
                           json.dumps(sh.get('carries', [])), sh.get('details_src', ''), sh.get('details_at'), n))
                audit_only(c, 'setting', 'shops', None, sh['name'], who, f'Store added ({label}): {sh["name"]}')
            for u in b.get('shops_update', []):                 # guarded: a detail is set only if it still holds the value expected
                r = c.execute('SELECT * FROM shops WHERE key=?', (u['key'],)).fetchone()
                if not r: continue
                done = {}
                for f, (old, new) in u['set'].items():
                    if f not in ('address', 'phone', 'hours', 'email', 'website', 'carries', 'details_src', 'details_at', 'online', 'name', 'url'): continue
                    cur = json.loads(r[f] or '[]') if f == 'carries' else r[f]
                    emp = lambda v: None if v is None or v == '' or v == [] else v
                    if emp(cur) != emp(old): continue
                    done[f] = json.dumps(new) if f == 'carries' else new
                if done:
                    c.execute('UPDATE shops SET ' + ', '.join(f'{k}=?' for k in done) + ' WHERE key=?', (*done.values(), r['key']))
                    audit_only(c, 'setting', 'shops', None, ', '.join(done), who, f'Store details added ({label}): {r["name"]}')
            for a in b.get('amendments_add', []):              # 1.56.0 (PLAN.md step 9a): added once by key; Ethan's own changes stay
                if c.execute('SELECT 1 FROM amendments WHERE key=? OR lower(name)=lower(?)', (a['key'], a['name'])).fetchone(): continue
                c.execute('INSERT INTO amendments(key,name,role,grades,holds_water,airy,lasts_months,feeds,ph,weight,source,notes,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                          (a['key'], a['name'], a.get('role', 'part'), json.dumps(a.get('grades') or []), a.get('holds_water'), a.get('airy'), a.get('lasts_months'),
                           a.get('feeds'), a.get('ph'), a.get('weight'), a.get('source', ''), a.get('notes', ''), who, ts))
            for m in b.get('pot_mixes_add', []):               # 1.56.0 (9c): what a pot is in, only where nothing is recorded yet
                r = c.execute('SELECT * FROM plants WHERE code=?', (m['code'],)).fetchone()
                if not r:
                    audit_only(c, 'note', None, None, None, who, 'Batch %s could not find %s for its potting mix, so it was skipped' % (label, m['code'])); continue
                if c.execute('SELECT 1 FROM pot_mixes WHERE plant_code=?', (m['code'],)).fetchone(): continue
                batch_pot_mix(c, m, r, None, who, ts, label)
            if b.get('place_sheets'): where_seed(c)              # 1.56.0 (PLAN.md step 8b): rooms and shelves are areas and spots by now
            for ps in b.get('place_sheets', []):               # a room's or shelf's measurements, only where none are set (Ethan's own stay)
                a = c.execute("SELECT * FROM areas WHERE side='in' AND home_id IS NULL AND name=?", (ps['room'],)).fetchone()
                if not a: continue
                row = c.execute('SELECT * FROM spots WHERE area_id=? AND name=?', (a['id'], ps['name'])).fetchone() if ps.get('name') else a
                if not row or (row['sheet'] or '') not in ('', '{}'): continue
                c.execute(f"UPDATE {'spots' if ps.get('name') else 'areas'} SET sheet=? WHERE id=?", (json.dumps(ps['sheet']), row['id']))
                audit_only(c, 'where', 'place_sheet', None, ps['room'] + (', ' + ps['name'] if ps.get('name') else ''), who, f"Measurements added ({label}): {ps['room']}{', ' + ps['name'] if ps.get('name') else ''}")
            for ps in b.get('place_sheets_update', []):        # 1.56.0: measurements field by field, each only if it still holds the old value
                q = "SELECT s.* FROM spots s JOIN areas a ON a.id=s.area_id WHERE a.side=? AND a.home_id IS NULL" + (' AND a.name=?' if ps.get('room') else '')
                names = {n.lower() for n in [ps.get('name') or ''] + ps.get('aka', []) if n}
                rows = [r for r in c.execute(q, (ps.get('side', 'in'),) + ((ps['room'],) if ps.get('room') else ())).fetchall()
                        if r['name'].strip().lower() in names or (ps.get('contains') and ps['contains'].lower() in r['name'].lower())]
                if len(rows) != 1: continue                     # not there, or more than one could be meant: leave it to Ethan
                row = rows[0]
                try: d = json.loads(row['sheet'] or '{}') or {}
                except ValueError: d = {}
                done = []
                for f, (old, new) in ps['set'].items():
                    if json.dumps(d.get(f)) != json.dumps(old): continue
                    if new is None: d.pop(f, None)
                    else: d[f] = new
                    done.append(f)
                if done:
                    c.execute('UPDATE spots SET sheet=? WHERE id=?', (json.dumps(d), row['id']))
                    audit_only(c, 'where', 'place_sheet', None, row['name'], who, f"Measurements added ({label}): {row['name']}")
            for u in b.get('lights_update', []):                # guarded, like plant updates: only if the light still holds the old value
                L = c.execute('SELECT * FROM lights WHERE lkey=?', (u['key'],)).fetchone()
                if not L: continue
                d, cols, done = light_specs(L), {}, []
                for f, (old, new) in u['set'].items():
                    cur = L[f] if f in ('fixture', 'notes', 'count', 'name') else d.get(f)
                    if str(cur if cur is not None else '') != str(old if old is not None else ''): continue
                    if f in ('fixture', 'notes', 'count', 'name'): cols[f] = new
                    else: d[f] = new
                    done.append(f)
                if done:
                    c.execute('UPDATE lights SET %s data=?, updated_by=?, updated_at=? WHERE id=?' % ''.join('%s=?, ' % k for k in cols),
                              (*cols.values(), json.dumps(d), who, ts, L['id']))
                    audit_only(c, 'light', 'light', None, ', '.join(done), who, 'Grow light updated (%s): %s, %s' % (label, L['name'], u.get('note') or ', '.join(done)))
            facts_from_batch(c, b, who, ts)                 # 1.53.0: facts as rows, with this batch as their source
            for f in b.get('species_facts_add', []):       # 1.27.0: added once; a later batch or Claude never overwrites them
                d = facts_clean(f['data'], f.get('kind', 'plant'))
                c.execute('INSERT OR IGNORE INTO species_facts(key,name,kind,data,origin,written_by,written_at) VALUES(?,?,?,?,?,?,?)',
                          (f['key'].lower(), f['name'], f.get('kind', 'plant'), json.dumps(d), 'researched', who, ts))
            for code, k in b.get('facts_link', {}).items():   # plants whose scientific name does not say which facts are theirs
                c.execute('INSERT OR IGNORE INTO facts_link(code,key) VALUES(?,?)', (code, k.lower()))
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
        if new_requests:                                   # 1.33.0: a notification for requests Claude just added
            try: push_requests(c, new_requests)
            except Exception as e: problem_exc('push', e, 'Requests could not be sent as notifications')

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
    home_check(c, r)                     # 1.58.0: in a request that changes something, an editor limited to some homes is stopped here
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
    if kind in ('area', 'spot', 'pot', 'tray'):                # 1.29.0: an id in its own list, or empty
        if v in (None, '', 0, '0'): return None
        try: i = int(v)
        except (TypeError, ValueError): abort(400, f'{FIELD_LABEL[name]} must be chosen from the list')
        if has_app_context():
            tbl, extra = {'area': ('areas', ''), 'spot': ('spots', ''), 'pot': ('containers', " AND kind='pot'"), 'tray': ('containers', " AND kind='tray'")}[kind]
            if not db().execute(f'SELECT 1 FROM {tbl} WHERE id=?{extra}', (i,)).fetchone(): abort(400, f'That {FIELD_LABEL[name].lower()} is not in the list any more')
        return i
    if kind == 'home':                                      # 1.28.0: a home's id; empty means the main home
        if v in (None, '', 0, '0'): return None
        try: i = int(v)
        except (TypeError, ValueError): abort(400, 'Home must be one of your homes')
        if has_app_context():
            r = db().execute('SELECT is_home, plants_here FROM locations WHERE id=?', (i,)).fetchone()
            if r is None or not (r[0] or r[1]): abort(400, 'Home must be one of your homes (a place where plants live)')
            if r[0]: return None                     # the main home is stored as empty, so plants follow if another place becomes the main home
        return i
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
    home_check(c, pid)                   # 1.58.0: the home limit, where the plant is changed (see home_check)
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
    home_check(c, r)                                         # 1.58.0: the home limit, where the plant is changed
    if 'home_id' in new_fields: home_check_new(c, new_fields.get('home_id'))     # and it cannot be moved to a home outside the limit
    new_fields = place_sync(c, r, dict(new_fields))          # 1.29.0
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
    return {'via': 'tailscale', 'login': r['login'], 'name': r['name'], 'role': r['role'] if r['role'] in ROLES else 'viewer', 'edit_homes': edit_homes_of(r)}   # 1.48.0: the homes an editor may change plants at

def owner_name(c):
    r = c.execute("SELECT name FROM people WHERE role='owner' ORDER BY first_seen LIMIT 1").fetchone()
    return r[0] if r else 'the owner'

OWNER_ONLY_PATHS = ('/api/backups', '/api/ingest', '/api/people')        # any request (the people list shows everyone's login)
OWNER_ONLY_CHANGES = ('/api/settings', '/api/weather/settings', '/api/identify/settings', '/api/library/settings', '/api/library/areas', '/api/shops', '/api/problems', '/api/backups/restore', '/api/jobs')   # changes only
VIEWER_POSTS = ('/api/identify', '/api/me/prefs', '/api/voice', '/api/whatsnew/seen')   # 1.55.0: "Got it" on What's new is the person's own setting   # 1.18.0: asks this computer what a picture shows; 1.29.0: your own settings; search by voice: words from a recording. None changes the plants
VIEWER_PREFIXES = ('/api/push/',)                   # 1.33.0: your own devices and notification choices

def edit_homes_of(r):
    """1.48.0: the home ids an editor is limited to, as a list; [] means every home."""
    try: v = json.loads(r['edit_homes'] or '[]') if r is not None and 'edit_homes' in r.keys() else []
    except Exception: v = []
    return [int(x) for x in v] if isinstance(v, list) else []

def plant_home_of(c, code):
    """The home a plant lives at (the main home's id when its home_id is empty), or None for an unknown code."""
    r = c.execute("SELECT home_id FROM plants WHERE code=?", (str(code or '').strip().upper(),)).fetchone()
    if r is None: return None
    return int(r[0]) if r[0] else home_place(c)['id']

def home_limit():
    """The home ids this request's person may change plants at, when they are limited (an editor with people.edit_homes) and the
    request is one that changes something; None otherwise (owners, editors without a limit, reading, batches, background jobs,
    a sensor's or a plant-sitter's request)."""
    if not has_request_context() or request.method in ('GET', 'HEAD', 'OPTIONS'): return None
    u = g.get('user')
    if not u or u.get('role') != 'editor': return None
    return u.get('edit_homes') or None

def home_words(c, allowed, code, h):
    names = {x['id']: x['name'] for x in homes(c)}
    return f"You can change plants at {', '.join(names.get(x, str(x)) for x in allowed)} only. {code} is at {names.get(h, 'another home')}."

def home_check(c, plant):
    """1.58.0: refuses (403) a change to a plant at a home this person may not change. `plant` is its row, its code or its id.
    home_refusal() below reads the plant out of the request before the route runs, which misses every request that names the
    plant another way (a photo's id, a care entry, a mix, a light spot). So the limit is also checked here, where a plant is
    fetched for a change (plant_row) and where it is changed (apply_changes, bump, set_spot_plants), and by the few routes that
    reach a plant's records without those. A route that changes a plant some new way must call this too:
    test_every_route_that_changes_a_plant_keeps_the_home_limit tries each one."""
    allowed = home_limit()
    if not allowed or plant is None: return
    if isinstance(plant, int): r = c.execute('SELECT code, home_id FROM plants WHERE id=?', (plant,)).fetchone()
    elif isinstance(plant, str): r = c.execute('SELECT code, home_id FROM plants WHERE code=?', (plant.strip().upper(),)).fetchone()
    else: r = plant
    if r is None: return
    h = int(r['home_id']) if r['home_id'] else home_place(c)['id']
    if h not in allowed: abort(403, home_words(c, allowed, r['code'], h))

def home_check_new(c, home_id):
    """The same for a plant that is being added, or moved to another home: the home it would be at."""
    allowed = home_limit()
    if not allowed: return
    try: h = int(home_id) if home_id not in (None, '', 0, '0') else home_place(c)['id']
    except (TypeError, ValueError): h = home_place(c)['id']
    if h not in allowed:
        names = {x['id']: x['name'] for x in homes(c)}
        abort(403, f"You can add or move plants at {', '.join(names.get(x, str(x)) for x in allowed)} only, not at {names.get(h, 'another home')}.")

def home_refusal(u, c):
    """1.48.0 (PLAN.md step 4b): an editor limited to some homes may change plants only at those homes. The request's plant comes
    from its path (/api/plants/<code>...) or its body (plant, plants, plant_code); a change of a care-log entry follows its plant.
    Changes that belong to no plant (lights, pots, groups, places) are not limited."""
    allowed = u.get('edit_homes') or []
    if not allowed or u['role'] != 'editor' or request.method in ('GET', 'HEAD', 'OPTIONS'): return None
    codes = []
    m = re.match(r'^/api/plants/([^/]+)', request.path)
    if m and m.group(1) != 'several': codes.append(m.group(1))
    m = re.match(r'^/api/care/(\d+)$', request.path)
    if m:
        r = c.execute('SELECT plant_code FROM care_log WHERE id=?', (int(m.group(1)),)).fetchone()
        if r: codes.append(r[0])
    b = request.get_json(silent=True) if request.is_json else None
    if isinstance(b, dict):
        for k in ('plant', 'plant_code', 'code'):
            if b.get(k): codes.append(str(b[k]))
        if isinstance(b.get('plants'), list): codes += [str(x) for x in b['plants']]
        if isinstance(b.get('codes'), list): codes += [str(x) for x in b['codes']]
    if request.form:
        for k in ('plant', 'code'):
            if request.form.get(k): codes.append(request.form.get(k))
    for code in codes:
        h = plant_home_of(c, code)
        if h is not None and h not in allowed:
            names = {x['id']: x['name'] for x in homes(c)}
            return f"You can change plants at {', '.join(names.get(x, str(x)) for x in allowed)} only. {code} is at {names.get(h, 'another home')}."
    return None

def role_refusal(u):
    """Why this person may not make this request, or None. The server decides; the page only hides what would be refused."""
    role, path, change = u['role'], request.path, request.method not in ('GET', 'HEAD', 'OPTIONS')
    if role == 'owner': return None
    if path == '/api/me': return None                                    # your own name
    if path.startswith(OWNER_ONLY_PATHS) or (change and path.startswith(OWNER_ONLY_CHANGES)) or (change and re.match(r'^/api/places/\d+$', path)) \
       or (request.method == 'DELETE' and path.startswith('/api/sensors/')):      # 1.35.0: forgetting a sensor and its readings
        return f'Only {owner_name(db())} can do this.'
    if role == 'viewer' and change and path not in VIEWER_POSTS and not path.startswith(VIEWER_PREFIXES):
        return f'You can look at everything, but changes are turned off for you. Ask {owner_name(db())} if you would like to edit.'
    if role == 'editor' and change: return home_refusal(u, db())          # 1.48.0: an editor limited to some homes
    return None

def me_dict(c):
    u = getattr(g, 'user', None) or {'via': 'local', 'login': None, 'name': '', 'role': 'owner'}
    return {'via': u['via'], 'login': u['login'], 'name': u['name'] if u['via'] == 'tailscale' else '', 'role': u['role'],
            'role_word': ROLE_WORD[u['role']], 'owner_name': owner_name(c), 'edit_homes': u.get('edit_homes') or [],
            'viewer_ok': {'posts': list(VIEWER_POSTS), 'prefixes': list(VIEWER_PREFIXES)}}   # 1.56.5: the page checks against the same lists

# ---------- units (1.47.0, PLAN.md step 4a) ----------
# Everything is stored and sent in °F and inches. A person's units come from their 'units' setting (user_prefs, saved by the Display
# window on any of their devices): a region sets temperature, length and rain at once, and each can be changed by hand. The front end
# converts what it shows; these helpers convert the sentences the server writes itself (push messages, the calendar, spray notes).
UNIT_REGIONS = {'us': {'temp': 'f', 'len': 'in', 'rain': 'in'}, 'ca': {'temp': 'c', 'len': 'in', 'rain': 'mm'}, 'metric': {'temp': 'c', 'len': 'cm', 'rain': 'mm'}}
# 1.48.0: what kind of year a site has. temperate: a winter with frost (the cold-season pages apply); mild: a cool season where
# frost is rare (the pages stay, since one night can still bite); tropical: wet and dry seasons and no frost (the cold-season pages
# and Today's cold blocks are left out there).
SEASONS = {'temperate': 'A winter with frost', 'mild': 'A cool season, frost rare', 'tropical': 'Wet and dry seasons, no frost'}

def units_for(c, login=None):
    """{'temp': 'f'|'c', 'len': 'in'|'cm', 'rain': 'in'|'mm'} for a sign-in (the request's own when login is None)."""
    login = login or prefs_login(c)
    r = c.execute("SELECT value FROM user_prefs WHERE login=? AND key='units'", (login,)).fetchone()
    try: u = json.loads(r[0]) if r and r[0] else {}
    except Exception: u = {}
    if not isinstance(u, dict): u = {}
    region = u.get('region')
    if region not in UNIT_REGIONS:                       # 1.48.0: no choice of their own: the site's default (the place in use, else the main home)
        try: region = (location(c) if has_request_context() else home_place(c)).get('units') or 'us'
        except Exception: region = 'us'
    base = UNIT_REGIONS.get(region, UNIT_REGIONS['us'])
    return {k: (u.get(k) if u.get(k) in ('f', 'c', 'in', 'cm', 'mm') else base[k]) for k in ('temp', 'len', 'rain')}

def units():
    """The units of the person making this request, read once per request."""
    if not has_request_context(): return UNIT_REGIONS['us']
    if not hasattr(g, 'units'): g.units = units_for(db())
    return g.units

def temp_text(f, u=None, unit=True):
    """A °F value as the person sees it: 72 -> '72°F' or '22°C' (whole degrees for whole input, else one decimal)."""
    if f is None or f == '': return ''
    u = u or units(); f = float(f)
    if u['temp'] == 'c':
        v = (f - 32) * 5 / 9; v = round(v) if float(f).is_integer() else round(v, 1)
    else: v = round(f) if float(f).is_integer() else round(f, 1)
    return f'{v:g}' + ('°C' if u['temp'] == 'c' else '°F') if unit else f'{v:g}'

def temp_diff_text(df, u=None, unit=True):
    """A difference in °F ('within 3°F'): no offset, so 3°F is 1.7°C."""
    u = u or units(); v = float(df) * 5 / 9 if u['temp'] == 'c' else float(df)
    v = round(v) if abs(v - round(v)) < 0.05 else round(v, 1)
    return f'{v:g}' + (('°C' if u['temp'] == 'c' else '°F') if unit else '')

def rain_text(inches, u=None):
    u = u or units(); x = float(inches)
    if u['rain'] == 'mm': mm = x * 25.4; return (f'{round(mm, 1):g}' if mm < 1 else f'{round(mm):g}') + ' mm'
    return f'{round(x, 2):g} in'

def len_text(inches, u=None):
    u = u or units(); x = float(inches)
    if u['len'] == 'cm': cm = x * 2.54; return (f'{round(cm, 1):g}' if cm < 3 else f'{round(cm):g}') + ' cm'
    return f'{round(x, 1):g} in'

def temps_in_text(text, u=None):
    """Converts the °F figures in a sentence written for Fahrenheit ('between 50 and 90°F', 'above 35°F') for a person who reads °C."""
    u = u or units()
    if u['temp'] != 'c' or not text: return text
    text = re.sub(r'(-?\d+(?:\.\d+)?) (and|to|or) (-?\d+(?:\.\d+)?)°F', lambda m: f'{temp_text(m.group(1), u, False)} {m.group(2)} {temp_text(m.group(3), u)}', text)
    return re.sub(r'(-?\d+(?:\.\d+)?)°F', lambda m: temp_text(m.group(1), u), text)

# 1.29.0: settings that follow you: the Plants filters, the Library's choices, folded sections, the Location button, and the parts of
# Display you choose to share between devices. Kept per Tailscale login; on this computer (localhost) they are the owner's.
def prefs_login(c):
    u = getattr(g, 'user', None) or {'via': 'local', 'login': None}
    if u.get('via') == 'tailscale' and u.get('login'): return u['login']
    r = c.execute("SELECT login FROM people WHERE role='owner' ORDER BY first_seen LIMIT 1").fetchone()
    return r[0] if r else 'local-owner'

@app.route('/api/me/prefs', methods=['GET', 'PUT'])
def me_prefs():
    c = db(); login = prefs_login(c)
    if request.method == 'PUT':
        b = request.get_json(silent=True) or {}
        if not isinstance(b, dict) or len(b) > 60: abort(400, 'Send up to 60 settings')
        for k, v in b.items():
            if not re.match(r'^[a-z][a-z0-9._-]{0,40}$', str(k)): abort(400, 'That setting name is not allowed')
            if v is None: c.execute('DELETE FROM user_prefs WHERE login=? AND key=?', (login, k)); continue
            v = str(v)
            if len(v) > 20000: abort(400, 'That setting is too long')
            c.execute('INSERT OR REPLACE INTO user_prefs(login,key,value,updated_at) VALUES(?,?,?,?)', (login, k, v, now()))
        c.commit()
    prefs = {k: v for k, v in c.execute('SELECT key, value FROM user_prefs WHERE login=?', (login,))}
    if 'place' not in prefs and 'place_given' not in prefs:   # 1.31.0: a person with a home of their own starts there, once; their later choices stand
        p = c.execute('SELECT home_id FROM people WHERE login=?', (login,)).fetchone()
        if p and p['home_id'] and c.execute('SELECT 1 FROM locations WHERE id=? AND enabled=1', (p['home_id'],)).fetchone():
            prefs['place'] = str(p['home_id'])
            for k, v in (('place', prefs['place']), ('place_given', '1')):
                c.execute('INSERT OR REPLACE INTO user_prefs(login,key,value,updated_at) VALUES(?,?,?,?)', (login, k, v, now()))
            c.commit()
    return jsonify(prefs=prefs, login=login)

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
        hid = r['home_id'] if r else None                  # 1.31.0: the home each person starts on (empty: the main home)
        if 'home_id' in b:
            hid = b['home_id']
            if hid in ('', None): hid = None
            else:
                try: hid = int(hid)
                except (TypeError, ValueError): abort(400, 'Choose one of your homes')
                if hid not in {h['id'] for h in homes(c)}: abort(400, 'Choose one of your homes')
                if hid == home_place(c)['id']: hid = None
        eh = r['edit_homes'] if r else ''                 # 1.48.0: the homes an editor may change plants at ('' = all of them)
        if 'edit_homes' in b:
            ids = b['edit_homes'] or []
            if not isinstance(ids, list): abort(400, 'edit_homes is a list of home ids')
            try: ids = sorted({int(x) for x in ids})
            except (TypeError, ValueError): abort(400, 'edit_homes is a list of home ids')
            allh = {h['id'] for h in homes(c)}
            if any(x not in allh for x in ids): abort(400, 'Choose from your homes')
            eh = json.dumps(ids) if ids and len(ids) < len(allh) else ''
        if r:
            c.execute('UPDATE people SET name=?, role=?, home_id=?, edit_homes=? WHERE login=?', (name, role, hid, eh, login))
            if (r['edit_homes'] or '') != eh:
                H = {h['id']: h['name'] for h in homes(c)}
                audit_only(c, 'setting', 'person', r['edit_homes'] or 'all homes', eh or 'all homes', editor(), f"{name} may edit plants at: {', '.join(H.get(x, str(x)) for x in json.loads(eh)) if eh else 'every home'}")
            if (r['name'], r['role']) != (name, role):
                audit_only(c, 'setting', 'person', f"{r['name']}: {r['role']}", f"{name}: {role}", editor(), f"{name} ({login}) is now: {ROLE_WORD[role]}")
            if r['home_id'] != hid:
                H = {h['id']: h['name'] for h in homes(c)}
                audit_only(c, 'setting', 'person', H.get(r['home_id']), H.get(hid), editor(), f"{name} starts on {H.get(hid) or 'the main home'}")
                c.execute("DELETE FROM user_prefs WHERE login=? AND key IN ('place', 'place_given')", (login,))   # so the new home is used on their next visit
        else:
            t = now()
            c.execute('INSERT INTO people(login,name,role,home_id,edit_homes,first_seen,last_seen) VALUES(?,?,?,?,?,?,?)', (login, name, role, hid, eh, t, t))
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
    rows = [dict(r) | {'role_word': ROLE_WORD.get(r['role'], r['role']), 'edit_homes': edit_homes_of(r)} for r in c.execute("SELECT * FROM people ORDER BY CASE role WHEN 'owner' THEN 0 WHEN 'editor' THEN 1 ELSE 2 END, name")]
    return jsonify(people=rows, roles=[{'key': k, 'label': ROLE_WORD[k]} for k in ROLES], me=me_dict(c), homes=[{'id': h['id'], 'name': h['name']} for h in homes(c)], main_home=home_place(c)['id'])

# ---------------------------------------------------------------- security
@app.before_request
def took_start():                   # 1.30.0: how long each answer takes to make, sent back as X-Took-Ms for the Debug page timings
    g.t0 = time.perf_counter()

# ---- 1.58.0: what the internet may reach. Tailscale Funnel publishes a path of this computer's own port (README, "A calendar
# link that works away from home" and "A plant-sitter sheet by link"), where every other request is the owner's. Tailscale marks
# each request that came in through Funnel with this header and removes any copy the visitor sent, so a visitor cannot take it
# off, and a request from this computer that carries it only loses access.
FUNNEL_HEADER = 'Tailscale-Funnel-Request'
SITTER_LINK = re.compile(r'^/share/[A-Za-z0-9_-]{20,}(/|$)')

def from_funnel():
    return bool(has_request_context() and request.headers.get(FUNNEL_HEADER))

def public_link():
    """The only two things reachable without being a person of this record: the subscribed calendar (calendar services cannot
    type a password, so its link carries a private token, checked in frost.py) and a plant-sitter sheet (1.49.0: the long token
    in the link is the key; sitter.py checks it on every route under it). A new public route must be added here."""
    m = request.method
    if request.path.startswith('/cal/'): return m in ('GET', 'HEAD')
    return bool(SITTER_LINK.match(request.path)) and m in ('GET', 'HEAD', 'POST')

# ---- 1.58.0: the names this computer's port answers to. On that port every request is the owner's, so a web page from somewhere
# else must not be able to reach it through the browser by pointing a name of its own at 127.0.0.1 ("DNS rebinding"; the page
# would then be the same site as far as the browser can tell, X-Editor and the Origin check included). Such a name is always a
# public one, with dots in it. A plain number address, localhost, a single-word name (a PC on the home network) and names
# ending in .local and the like cannot be pointed here by a stranger; anything else has to be listed in PLANTDB_HOSTS (commas,
# in .env) or be the address saved for labels or for the calendar. People who come in through Tailscale are not checked this
# way: they are let in by who they are, not by the port.
LOCAL_SUFFIXES = ('.local', '.localhost', '.lan', '.home', '.home.arpa', '.internal', '.localdomain')
EXTRA_HOSTS = {h.strip().lower().rstrip('.') for h in os.environ.get('PLANTDB_HOSTS', '').split(',') if h.strip()}

def host_name():
    h = (request.host or '').strip().lower()
    if h.startswith('['): return h[1:h.index(']')] if ']' in h else h          # [::1]:8080
    return (h.rsplit(':', 1)[0] if ':' in h else h).rstrip('.')

def host_known():
    h = host_name()
    if not h or h == 'localhost' or '.' not in h or h.endswith(LOCAL_SUFFIXES) or h in EXTRA_HOSTS: return True
    try: ipaddress.ip_address(h); return True
    except ValueError: pass
    c = db()
    saved = [setting(c, 'base_url', '')]
    try: saved.append(json.loads(setting(c, 'ics_options', '') or '{}').get('public_base', ''))
    except ValueError: pass
    return any(s and (urlparse(s).hostname or '').lower() == h for s in saved)

@app.before_request
def guard():
    if from_funnel() and not public_link():        # 1.58.0: from the internet, a calendar or sitter link and nothing else
        return Response('Not found', 404, {'Content-Type': 'text/plain; charset=utf-8'})
    if NEWER_DB:                     # 1.31.0: an older version on a newer database: every page says what to do, and nothing is changed
        msg = (f"This plant record was last opened by version {NEWER_DB['last']}, and this is the older version {NEWER_DB['this']}. "
               f"To keep your data safe it will not run. Install version {NEWER_DB['last']} or newer with the updater (Update Plant Database.cmd), "
               "or restore a backup made by this version.")
        if request.path.startswith('/api/'): return jsonify(error=msg, newer_db=NEWER_DB['last']), 503
        return Response(f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Plant record: newer database</title>'
                        '<style>body{font:1.25rem/1.5 system-ui,sans-serif;max-width:40rem;margin:3rem auto;padding:0 1rem;color:#0e2233;background:#f5f7f6}</style></head>'
                        f'<body><h1>Plant record will not run on this database</h1><p>{html_mod.escape(msg)}</p></body></html>', status=503, mimetype='text/html')
    if request.path == '/healthz': return None
    if has_request_context() and str(request.environ.get('SERVER_PORT', '')) == SENSOR_PORT and not (request.path == '/api/readings' and request.method == 'POST'):
        abort(404, 'This port only takes sensor readings (POST /api/readings).')
    if request.path == '/api/readings' and request.method == 'POST':
        # sensors cannot type a password or send a browser header, so this one route is checked by a secret token instead
        tok = setting(db(), 'ingest_token', '')
        if not tok or not hmac.compare_digest(request.headers.get('X-Ingest-Token', ''), tok): abort(403, 'missing or wrong X-Ingest-Token')
        return None
    if public_link(): return None    # the calendar and plant-sitter links carry their own token (see public_link)
    if via_tailscale():
        g.user = ts_user()
        if g.user is None:
            return Response('Open Plant record from a device that is signed in to Tailscale as a person.', 403, {'Content-Type': 'text/plain; charset=utf-8'})
    else:
        if not host_known():             # 1.58.0: not a name this computer answers to (see host_known)
            return Response(f'Plant record on this computer does not answer to the name "{host_name()}". Open it at http://localhost:8080 here, '
                            'or through its Tailscale address. If this is a name you gave this computer yourself, add the line '
                            f'PLANTDB_HOSTS={host_name()} to the .env file next to docker-compose.yml and run the updater '
                            '(README, "The names this computer answers to").', 403, {'Content-Type': 'text/plain; charset=utf-8'})
        if PASSWORD:
            a = request.authorization
            if not (a and hmac.compare_digest(a.password or '', PASSWORD)):
                return Response('Password required', 401, {'WWW-Authenticate': 'Basic realm="Plant database"'})
        g.user = {'via': 'local', 'login': None, 'name': editor(), 'role': 'owner'}     # this computer (or the home network, if opened to it)
    if MIRROR:                       # 1.37.0: on the mirror everyone can only look
        g.user = dict(g.user, role='viewer', mirror=True)
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and request.path not in ('/api/me/prefs', '/api/whatsnew/seen'): abort(403, 'This is the read-only mirror. Make changes in the main app' + (f' at {MIRROR_MAIN}' if MIRROR_MAIN else '') + '.')
    refusal = role_refusal(g.user)
    if refusal: abort(403, refusal)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        # CSRF guard: custom header cannot be sent cross-site without a CORS preflight (which we never allow)
        if not request.headers.get('X-Editor'): abort(403, 'missing X-Editor header')
        o = request.headers.get('Origin')
        if o and urlparse(o).netloc != request.host: abort(403, 'cross-origin request refused')
        replay = offline_replay()                   # 1.24.0: a change from a device that was already made
        if replay is not None: return replay

@app.after_request
def headers(resp):
    resp = offline_remember(resp)
    if via_tailscale():                              # always HTTPS (Tailscale Serve), so browsers can be told to stay on HTTPS
        resp.headers['Strict-Transport-Security'] = 'max-age=31536000'
    resp.headers['Permissions-Policy'] = 'geolocation=(self), microphone=(self), payment=(), usb=(), camera=(self)'   # 1.22.0: location for mushroom finds; microphone for search by voice
    resp.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-App-Version'] = APP_VERSION     # 1.56.5: an open page sees at once that a new version is running, and reloads
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['Referrer-Policy'] = 'no-referrer'
    resp.headers['Content-Security-Policy'] = "default-src 'self'; img-src 'self' data: blob:; connect-src 'self' blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; frame-ancestors 'none'"
    t0 = g.get('t0')
    if t0 is not None:
        ms = round((time.perf_counter() - t0) * 1000)
        resp.headers['X-Took-Ms'] = str(ms); resp.headers['Server-Timing'] = f'app;dur={ms}'
    return gzip_answer(resp)

GZ_TYPES = ('application/json', 'text/html', 'text/css', 'application/javascript', 'text/javascript', 'image/svg+xml', 'text/plain', 'text/csv', 'text/calendar', 'application/manifest+json')
GZ_STATIC = {}                       # the app's own files, squeezed once per version of each file: path -> (etag, bytes)
def gzip_answer(resp):
    """1.30.0: text answers over about 1 KB are sent squeezed (gzip) when the browser accepts it, which is about 5 times smaller."""
    try:
        if resp.status_code != 200 or resp.headers.get('Content-Encoding') or 'gzip' not in request.headers.get('Accept-Encoding', '').lower(): return resp
        if resp.mimetype not in GZ_TYPES or request.method == 'HEAD' or resp.is_streamed and not resp.direct_passthrough: return resp
        key, old = None, resp.response
        if resp.direct_passthrough:                    # a file sent from disk (the app's own scripts and styles)
            key = (request.path, resp.headers.get('ETag', ''))
            got = GZ_STATIC.get(request.path)
            if got and got[0] == key[1] and key[1]: body = got[1]
            else:
                resp.direct_passthrough = False
                raw = resp.get_data()
                if len(raw) < 1400: return resp
                body = gzip.compress(raw, 6)
                if key[1]: GZ_STATIC[request.path] = (key[1], body)
            resp.direct_passthrough = False
        else:
            raw = resp.get_data()
            if len(raw) < 1400: return resp
            body = gzip.compress(raw, 5)
        resp.set_data(body)
        if old is not resp.response and hasattr(old, 'close'): old.close()
        resp.headers['Content-Encoding'] = 'gzip'; resp.headers['Content-Length'] = str(len(body))
        resp.vary.add('Accept-Encoding')
    except Exception as e:
        problem('gzip', 'A page could not be squeezed and was sent as it is', f'{request.path}: {type(e).__name__}: {e}', db() if has_app_context() else None)
    return resp

@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(409)
@app.errorhandler(410)                             # 1.49.0: a plant-sitter link taken down or past its days
@app.errorhandler(413)
@app.errorhandler(502)
@app.errorhandler(503)
def err(e):
    return jsonify(error=getattr(e, 'description', str(e))), e.code

def read_version():
    """The release number: VERSION next to server.py (copied in by the Dockerfile), or PLANTDB_VERSION."""
    for f in (os.path.join(APP_DIR, 'VERSION'), os.path.join(os.path.dirname(APP_DIR), 'VERSION')):
        try:
            v = open(f, encoding='utf-8').read().strip()
            if v: return v
        except OSError: pass
    return os.environ.get('PLANTDB_VERSION', 'unknown')
APP_VERSION = read_version()
def version_tuple(v):
    try: return tuple(int(x) for x in str(v).split('.')[:3])
    except ValueError: return (0, 0, 0)

@app.route('/healthz')
def healthz(): return 'ok ' + APP_VERSION


def link(modules):
    """1.32.0: server.py was one file; it is now these modules. Each one imports the core's names, and the rest (a plant helper
    used by the weather module, say) are filled in here once every module is loaded: Python looks a name up when the function
    runs, so a function can call across modules exactly as it did in one file. Module-level code may only use the core's names."""
    ns = {}
    for m in modules: ns.update({k: v for k, v in vars(m).items() if not k.startswith('__')})
    for m in modules:
        d = vars(m)
        for k, v in ns.items():
            if k not in d: d[k] = v
    return ns
