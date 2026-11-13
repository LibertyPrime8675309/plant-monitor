"""1.58.0 (November 12 review, item 6): old databases, upgraded in place.

Every check started from a new install, while the record this app exists for has come through every version since October. The
fixtures in dev/test/fixtures are what three versions leave behind after some ordinary use: 1.7.5 (the first in git), 1.28.0 (the
last before rooms and spots, and before server.py became the plantdb package) and the last release (the version on Ethan's PC,
so the upgrade his own record makes next). In each a person edited two plants by hand, added a plant of their own with a photo,
logged a feeding and a watering, answered a question, archived a plant, moved one indoors, and, where the version could, made a
group, a shelf, a grow light spot, a pot's mix with a repot and a plant-sitter link, and turned the photos off in automatic
backups. make_upgrade_fixture.py made them, and says how to make the next one.

Each is loaded into an empty data folder and this version is started on it in a process of its own, as a container start does.
Then: nothing a person did is lost; what they changed by hand still says what they wrote; the record holds the same plants,
facts, photos and tables as a new install of this version; a second start changes nothing; and the pages answer.

The first run of this test found two things no other check could (both fixed in 1.58.0, see core.py batch_numbering):
a batch entry that named a plant by its code alone landed on the neighbouring plant in a record where the owner had added a
plant of their own, and batch C9 gave its new page a room by a row number that means another room in every other record."""
import glob, gzip, json, os, sqlite3, subprocess, sys
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
APP = os.path.join(ROOT, 'app')
FIXTURES = sorted(glob.glob(os.path.join(HERE, '..', 'fixtures', 'plants-*.sql.gz')))
NAMES = [os.path.basename(f)[7:-7] for f in FIXTURES]
VERSION = open(os.path.join(ROOT, 'VERSION')).read().strip()
# the words make_upgrade_fixture.py wrote (keep the two in step)
EDITED_NOTES, EDITED_LOCATION, ADDED_NAME, ANSWER = 'Edited by hand before the upgrade.', 'Moved by hand to the back fence', 'My own added plant', 'Answered before the upgrade'
SHELF, LIGHT_SPOT, MIX_PLANT, MIX_DAY, LINK = 'Hand-made shelf', 'Hand-set light shelf', 'P-004', '2026-11-01', 'fixture-link-fixture-link-0001'
BY_HAND = {'P-002': {'site', 'area'}, 'P-003': {'notes'}, 'P-005': {'location'}, 'P-007': {'status'}}      # the pages the person changed, and what they changed

KEPT = {   # what a person did, as rows that must all still be there afterwards: name -> (the tables it needs, the question). A version without those tables is not asked.
    'care log': ('care_log', 'SELECT plant_code, kind, done_on, note FROM care_log'),
    'feedings': ('fertilizer_log', 'SELECT plant_code, applied_on, product, n, p, k FROM fertilizer_log'),
    'questions asked': ('requests', 'SELECT rkey FROM requests'),
    'answers given': ('requests', 'SELECT rkey, answer FROM requests WHERE answer IS NOT NULL'),
    'still to photograph': ('to_photograph', 'SELECT label FROM to_photograph'),
    'groups': ('plant_groups group_members', 'SELECT g.name, p.code FROM plant_groups g JOIN group_members m ON m.group_id=g.id JOIN plants p ON p.id=m.plant_id'),
    'shelves': ('spots areas', 'SELECT a.name, s.name FROM spots s JOIN areas a ON a.id=s.area_id'),
    'plants on shelves': ('spots', 'SELECT p.code, s.name FROM plants p JOIN spots s ON s.id=p.spot_id'),
    'grow light spots': ('light_spots light_assign', 'SELECT s.name, a.plant_code FROM light_spots s JOIN light_assign a ON a.spot_id=s.id'),
    'what pots are in': ('pot_mixes', 'SELECT plant_code, mixed_on, parts FROM pot_mixes'),
    'plant-sitter links': ('sitter_shares', 'SELECT token, from_d, to_d, note FROM sitter_shares'),
    'photos': ('photos', 'SELECT file FROM photos'),
    'page versions': ('plant_versions', 'SELECT plant_id, version FROM plant_versions'),
    'history': ('audit_log', 'SELECT id, action, plant_code, changed_by, changed_at FROM audit_log'),
}
LISTS = {  # what batches bring besides plants: the same in an upgraded record as in a new install
    'grow lights': 'SELECT lkey, name FROM lights', 'stores': 'SELECT key, name FROM shops', 'amendments': 'SELECT key, name FROM amendments',
    'species facts': 'SELECT key, name, kind FROM species_facts', 'homes': 'SELECT name, is_home, plants_here, tended FROM locations',
    'rooms': "SELECT a.name, a.side, COALESCE(l.name, '') FROM areas a LEFT JOIN locations l ON l.id=a.home_id WHERE a.created_by='Plant record'",
}
NOT_FACTS = {'id', 'code', 'created_at', 'updated_at', 'version', 'created_by', 'updated_by', 'home_id', 'area_id', 'spot_id', 'pot_id', 'tray_id'}
SITE_OF = lambda side, sheltered: ('Covered porch' if sheltered else 'Outdoors') if side == 'out' else ('Indoors' if sheltered else 'Garage or shed')

def env_for(tmp):
    e = dict(os.environ, DATA_DIR=os.path.join(tmp, 'data'), PLANTDB_BACKUP_DIR=os.path.join(tmp, 'backups'), PLANTDB_WEATHER='0', PLANTDB_SHOPS='0', PLANTDB_OSM='0',
             PLANTDB_UPDATES='0', PLANTDB_PUSH='0', PLANTDB_BACKUPS='0', PLANTDB_VISION_URL='http://127.0.0.1:9', PLANTDB_ASPCA_MIN='0')
    for k in ('PLANTDB_MIRROR', 'PLANTDB_VERSION', 'PLANTDB_COPY_DIR', 'PLANTDB_COPY_MOUNT'): e.pop(k, None)
    return e

def start(tmp, code='import server', **env):
    """This version, started on that data folder in a process of its own; returns what it printed."""
    for d in ('data', 'backups'): os.makedirs(os.path.join(tmp, d), exist_ok=True)
    r = subprocess.run([sys.executable, '-c', code], cwd=APP, env=dict(env_for(tmp), **env), capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, 'this version did not start on that record:\n' + (r.stderr or r.stdout)[-3000:]
    return r.stdout

def read(db):
    """What a record holds, in a form two records can be compared in."""
    c = sqlite3.connect(db); c.row_factory = sqlite3.Row
    tables = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    s = {'tables': tables, 'columns': {(t, r[1]) for t in tables for r in c.execute(f'PRAGMA table_info("{t}")')},
         'indexes': {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'")},
         'integrity': c.execute('PRAGMA integrity_check').fetchone()[0], 'foreign': c.execute('PRAGMA foreign_key_check').fetchall(),
         'settings': {r[0]: r[1] for r in c.execute('SELECT key, value FROM settings')},
         'kept': {k: {tuple(r) for r in c.execute(q)} for k, (need, q) in KEPT.items() if set(need.split()) <= tables},
         'lists': {},
         'facts': {tuple(r) for r in c.execute('SELECT key, kind, field, value, status FROM facts')} if 'facts' in tables else set(),
         'not found': [r[0] for r in c.execute("SELECT note FROM audit_log WHERE note LIKE 'Batch % could not find %'")], 'plants': {}}
    try: s['lists'] = {k: {tuple(r) for r in c.execute(q)} for k, q in LISTS.items()}
    except sqlite3.OperationalError: pass                 # an old record, before these tables or columns: only this version's are compared
    place = 'areas' in tables
    q = ("SELECT p.*, COALESCE(l.name, '') AS _home, COALESCE(l.is_home, 1) AS _main, a.side AS _side, a.sheltered AS _sheltered, a.home_id AS _area_home, COALESCE(s.name, '') AS _spot "
         "FROM plants p LEFT JOIN locations l ON l.id=p.home_id LEFT JOIN areas a ON a.id=p.area_id LEFT JOIN spots s ON s.id=p.spot_id") if place else 'SELECT * FROM plants'
    for r in c.execute(q).fetchall():
        d = {k: (r[k] if r[k] is not None else '') for k in r.keys() if k not in NOT_FACTS and not k.startswith('_')}
        if place:
            d['home'] = r['_home']; d['spot'] = r['_spot']
            d['area'] = None if r['_side'] is None else (SITE_OF(r['_side'], r['_sheltered']), 'its own home' if r['_area_home'] == (None if r['_main'] else r['home_id']) else 'another home')
        s['plants'][r['code']] = {'facts': d, 'id': r['id'], 'last': (r['version'], r['updated_at']),
                                  'files': frozenset(x[0] for x in c.execute('SELECT file FROM photos WHERE plant_id=?', (r['id'],)))}
    c.close()
    return s

@pytest.fixture(scope='module')
def new_install(tmp_path_factory):
    tmp = str(tmp_path_factory.mktemp('new-install')); start(tmp)
    return read(os.path.join(tmp, 'data', 'plants.db'))

@pytest.fixture(scope='module', params=FIXTURES, ids=NAMES)
def upgraded(request, tmp_path_factory):
    """One old record: as it was, after this version started on it, and after a second start."""
    tmp = str(tmp_path_factory.mktemp('upgrade')); os.makedirs(os.path.join(tmp, 'data'))
    db = os.path.join(tmp, 'data', 'plants.db')
    c = sqlite3.connect(db)
    with gzip.open(request.param, 'rt', encoding='utf-8') as f: c.executescript(f.read())
    c.close()
    old = read(db); start(tmp); new = read(db); start(tmp); again = read(db)
    return {'tmp': tmp, 'db': db, 'old': old, 'new': new, 'again': again, 'own': next(k for k, p in old['plants'].items() if p['facts']['common_name'] == ADDED_NAME)}

def test_there_are_old_records_to_upgrade():
    assert len(FIXTURES) >= 3 and '1.7.5' in NAMES, 'the fixtures are in dev/test/fixtures (make_upgrade_fixture.py makes them)'

def test_the_record_is_sound_and_every_batch_is_applied_once(upgraded):
    old, new = upgraded['old'], upgraded['new']
    assert new['integrity'] == 'ok' and new['foreign'] == []
    assert new['settings'].get('db_version') == VERSION, 'the database remembers which version opened it'
    files = {json.load(open(p, encoding='utf-8'))['id'] for p in glob.glob(os.path.join(APP, 'seed', 'batches', '*.json'))}
    was = {k for k in old['settings'] if k.startswith('batch_applied:')}; now = {k for k in new['settings'] if k.startswith('batch_applied:')}
    assert now == {'batch_applied:' + i for i in files} and was < now, 'every batch is marked as applied, and the old marks are kept'
    assert all(new['settings'][k] == old['settings'][k] for k in was), 'a batch applied before is not applied again'
    assert new['not found'] == [], 'every batch entry found the plant it was written for'

def test_nothing_a_person_did_is_lost(upgraded):
    old, new = upgraded['old'], upgraded['new']
    for k, rows in old['kept'].items():
        gone = rows - new['kept'][k]
        assert not gone, f'{k}: {len(gone)} of {len(rows)} are gone after the upgrade, for example {sorted(gone, key=str)[:3]}'
    assert set(old['plants']) <= set(new['plants']), 'every plant is still there under its own code'
    for code, p in old['plants'].items():
        assert new['plants'][code]['id'] == p['id'] and p['files'] <= new['plants'][code]['files'], f'{code} kept its own photos'
    assert set(KEPT) == set(new['kept']), 'this version can answer every question above (a misspelt one would otherwise check nothing)'

def test_what_was_changed_by_hand_still_says_what_the_person_wrote(upgraded):
    old, P = upgraded['old'], {k: v['facts'] for k, v in upgraded['new']['plants'].items()}
    assert P['P-003']['notes'] == EDITED_NOTES                          # batches state the value they expect to replace, so an edited field is left alone
    assert P['P-005']['location'] == EDITED_LOCATION
    assert P['P-007']['status'] == 'archived'
    assert P['P-002']['site'] == 'Indoors' and P['P-002']['area'] == ('Indoors', 'its own home')
    own = upgraded['own']
    assert P[own]['common_name'] == ADDED_NAME and P[own]['scientific_name'] == 'Ficus elastica', 'the plant the owner added kept its page and its code'
    assert len(upgraded['new']['plants'][own]['files']) == 1, 'and its one photo: no batch photo landed on it'
    assert any(a == ANSWER for _, a in upgraded['new']['kept']['answers given'])
    K = upgraded['new']['kept']
    if 'plants on shelves' in old['kept']: assert {s for _, s in K['plants on shelves']} >= {SHELF} and old['kept']['plants on shelves'] == {r for r in K['plants on shelves'] if r[1] == SHELF}
    if 'grow light spots' in old['kept']: assert (LIGHT_SPOT, 'P-001') in K['grow light spots']
    if 'what pots are in' in old['kept']: assert any(r[:2] == (MIX_PLANT, MIX_DAY) for r in K['what pots are in']) and any(r[:3] == (MIX_PLANT, 'repot', MIX_DAY) for r in K['care log'])
    if 'plant-sitter links' in old['kept']: assert [r[0] for r in K['plant-sitter links']] == [LINK]

def test_automatic_backups_get_the_photos_once(upgraded):
    """Review item 2: his PC had the photos off. An upgraded record gets them switched on once, and says so in the history."""
    old, new = upgraded['old']['settings'], upgraded['new']['settings']
    assert json.loads(old['backup_settings'])['photos'] is False, 'the fixture has the photos off, as his PC had'
    assert json.loads(new['backup_settings'])['photos'] is True and new.get('backup_photos_once')
    assert upgraded['again']['settings']['backup_settings'] == new['backup_settings']

def test_the_upgraded_record_is_what_a_new_install_is(upgraded, new_install):
    """Plant by plant: the same facts and the same photos. The plants are matched by their name and photos, since in a record where the owner added a plant of their own
    the batches' later plants have the next codes. Only what the person changed by hand may differ."""
    old, new, own = upgraded['old'], upgraded['new'], upgraded['own']
    for k in ('tables', 'columns', 'indexes'):
        assert new[k] == new_install[k], f'{k} only in a new install: {sorted(new_install[k] - new[k])[:8]}; only in the upgraded record: {sorted(new[k] - new_install[k])[:8]}'
    assert set(new_install['lists']) == set(LISTS) == set(new['lists'])
    for k, rows in new_install['lists'].items():
        assert rows <= new['lists'][k], f'{k}: a new install has {sorted(rows - new["lists"][k], key=str)[:4]} and the upgraded record does not'
    here = {(p['facts']['common_name'], p['files']): code for code, p in new['plants'].items()}
    assert len(here) == len(new['plants'])
    on_shelf = {c for c, s in old['kept'].get('plants on shelves', ()) if s == SHELF}
    differ, missing, seen = {}, [], set()
    for code, p in sorted(new_install['plants'].items()):
        at = here.get((p['facts']['common_name'], p['files']))
        if at is None: missing.append((code, p['facts']['common_name'])); continue
        seen.add(at)
        may = BY_HAND.get(at, set()) | ({'spot'} if at in on_shelf else set())
        d = {k: (new['plants'][at]['facts'][k], v) for k, v in p['facts'].items() if new['plants'][at]['facts'][k] != v and k not in may}
        if d: differ[f'{code} (here {at})'] = {k: (str(a)[:60], str(b)[:60]) for k, (a, b) in d.items()}
    assert not missing, f'plants of a new install that are not in the upgraded record with the same photos: {missing[:6]}'
    assert not differ, f'{len(differ)} plants differ from a new install (upgraded, new): {dict(list(differ.items())[:4])}'
    assert set(new['plants']) - seen == {own}, 'and the only other plant is the one the owner added'
    for p in new['plants'].values():
        if p['facts']['status'] == 'active': assert p['facts']['area'] == (p['facts']['site'], 'its own home'), f"{p['facts']['common_name']} is in a room or area of the wrong home or kind: {p['facts']['area']}"
    archived = {k for k, p in new['plants'].items() if p['facts']['status'] == 'archived'} - {k for k, p in new_install['plants'].items() if p['facts']['status'] == 'archived'}
    assert archived == {'P-007'}
    lost = {f for f in new_install['facts'] - new['facts'] if f[0] not in new['plants']['P-007']['facts']['scientific_name'].lower()}      # a species' facts come from its active plants
    assert not lost, f'{len(lost)} facts of a new install are not in the upgraded record, for example {sorted(lost, key=str)[:3]}'

def test_a_new_install_is_sound_too(new_install):
    assert new_install['integrity'] == 'ok' and new_install['not found'] == [], 'in a new install every batch entry finds its plant'
    for p in new_install['plants'].values():
        if p['facts']['status'] == 'active': assert p['facts']['area'] == (p['facts']['site'], 'its own home'), f"{p['facts']['common_name']}: {p['facts']['area']}"

def test_a_second_start_changes_nothing(upgraded):
    new, again = upgraded['new'], upgraded['again']
    assert again['kept'] == new['kept'] and again['lists'] == new['lists'] and again['facts'] == new['facts'] and again['settings'] == new['settings']
    assert {k: (p['last'], p['files'], p['facts']) for k, p in again['plants'].items()} == {k: (p['last'], p['files'], p['facts']) for k, p in new['plants'].items()}, 'no page gets a new version from being started again'

PROBE = '''
import json, os, sqlite3, server as S
OWN, NAME = os.environ["UPGRADE_OWN"], "My own added plant"
t = S.app.test_client(); bad = {}
for u in ("/api/meta", "/api/plants?status=all", "/api/plants/P-003", "/api/plants/" + OWN, "/api/water", "/api/care?n=50", "/api/fertilizer", "/api/requests", "/api/where", "/api/lights",
          "/api/groups", "/api/frost", "/api/health", "/api/jobs", "/api/audit?limit=20", "/api/plants/P-003/timeline", "/api/mixes", "/api/mixes/plant/P-004", "/api/shopping", "/api/backups",
          "/api/sitter/shares", "/api/facts/rows?limit=5", "/api/people", "/"):
    r = t.get(u)
    if r.status_code != 200: bad[u] = r.status_code
c = sqlite3.connect(os.path.join(S.DATA_DIR, "plants.db")); c.row_factory = sqlite3.Row
meant, codes = S.batch_numbering(c)
name = lambda r: r["common_name"] if r else None
last = sorted(meant)[-1]; theirs = name(S.find_plant(c, {"code": last}, meant))
finds = {"numbered": len(meant), "last": last, "by the file's code": theirs,
         "own plant by its code and name": name(S.find_plant(c, {"code": OWN, "name": NAME}, meant)),
         "a code with the wrong name": name(S.find_plant(c, {"code": OWN, "name": "Something else"}, meant)),
         "own plant by its code alone": name(S.find_plant(c, {"code": OWN}, meant)),
         "what the own code means in the files": name(c.execute("SELECT * FROM plants WHERE id=?", (meant.get(OWN, 0),)).fetchone())}
# a batch as one is written from now on: every entry says the plant's name beside its code
real = S.batch_files(); am = c.execute("SELECT key FROM amendments ORDER BY id LIMIT 1").fetchone()[0]
later = {"id": "ZZ-upgrade-test", "author": "Upgrade test",
         "existing_photos": [{"code": last, "name": theirs, "file": "zz-theirs.jpg", "caption": "for the plant the files mean"},
                             {"code": OWN, "name": NAME, "file": "zz-own.jpg", "caption": "for the plant the owner added"},
                             {"code": OWN, "name": "Something else", "file": "zz-nobody.jpg", "caption": "for a plant that is not here"}],
         "updates": [{"code": OWN, "name": NAME, "set": {"aliases": [None, "Named by a later batch"]}}],
         "pot_mixes_add": [{"code": OWN, "name": NAME, "mixed_on": "2026-11-12", "parts": [{"key": am, "parts": 1}]}],
         "facts_link": [{"code": OWN, "name": NAME, "key": "Ficus elastica"}]}
S.patch("batch_files", lambda: real + [("batchZZ.json", later)])
S.apply_batches(c); S.apply_batches(c)
on = lambda f: [r[0] for r in c.execute("SELECT p.common_name FROM photos ph JOIN plants p ON p.id=ph.plant_id WHERE ph.file=?", (f,))]
own = c.execute("SELECT * FROM plants WHERE code=?", (OWN,)).fetchone()
did = {"theirs": on("zz-theirs.jpg"), "own": on("zz-own.jpg"), "nobody": on("zz-nobody.jpg"), "aliases": own["aliases"],
       "mix": [r[0] for r in c.execute("SELECT plant_code FROM pot_mixes WHERE mixed_on='2026-11-12'")] == [OWN],
       "link": [tuple(r) for r in c.execute("SELECT code, key FROM facts_link WHERE key='ficus elastica'")] == [(OWN, "ficus elastica")],
       "said": [r[0] for r in c.execute("SELECT note FROM audit_log WHERE note LIKE 'Batch ZZ-upgrade-test could not find%'")]}
try:
    S.patch("batch_files", lambda: real + [("batchZZ.json", later), ("batchZZ2.json", {"id": "ZZ-row-number", "updates": [{"code": "P-001", "set": {"area_id": [None, 7]}}]})])
    S.apply_batches(c); did["row number"] = "applied"
except ValueError: did["row number"] = "refused"
print("PROBE " + json.dumps({"pages": bad, "finds": finds, "later": did}))
'''

def test_the_pages_answer_and_batches_find_the_right_plant(upgraded, new_install):
    """What a later batch finds in this record. The files number plants as a new install does, so the owner's plant (which took the next number when it was added) shares its
    code with the plant the files mean by it: the files' plant is found by the code alone, the owner's by the code with its name. This test changes the record, so it is last."""
    out = start(upgraded['tmp'], PROBE, UPGRADE_OWN=upgraded['own'])
    got = json.loads([l for l in out.splitlines() if l.startswith('PROBE ')][-1][6:])
    assert got['pages'] == {}, f'pages that do not answer on the upgraded record: {got["pages"]}'
    f = got['finds']; last = max(new_install['plants'])
    assert f['numbered'] == len(new_install['plants']) and f['last'] == last, 'every plant of the files is numbered'
    assert f["by the file's code"] == new_install['plants'][last]['facts']['common_name'], 'the code a new install gives a plant means that plant here too'
    assert f['own plant by its code and name'] == ADDED_NAME and f['a code with the wrong name'] is None
    theirs = new_install['plants'][upgraded['own']]['facts']['common_name']           # the plant the files mean by the code the owner's plant has here
    assert f['what the own code means in the files'] == theirs and f['own plant by its code alone'] == theirs != ADDED_NAME
    L = got['later']
    assert L['theirs'] == [f["by the file's code"]] and L['own'] == [ADDED_NAME], 'a photo lands on the page its entry names, once, however often the app starts'
    assert L['nobody'] == [] and len(L['said']) == 1 and 'Something else' in L['said'][0], 'an entry whose plant is not here is left out, and the history says so'
    assert L['aliases'] == 'Named by a later batch' and L['mix'] and L['link'], "updates, potting mixes and fact links reach the owner's own plant by its code and name"
    assert L['row number'] == 'refused', 'a batch cannot set a room, spot, pot or home by its row number'
