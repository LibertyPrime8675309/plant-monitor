"""Makes an upgrade fixture: the database an older version of Plant record leaves behind after some ordinary use, as SQL text.

    python3 dev/test/fixtures/make_upgrade_fixture.py <the old version's app folder> dev/test/fixtures/plants-<version>.sql.gz

Get the old app folder out of git, for example (1.7.5 is the first commit; 1.28.0 is the last version before rooms and spots
and before server.py was split into the plantdb package):

    git archive fca4db6 app | tar -x -C /tmp/v175        then  .../make_upgrade_fixture.py /tmp/v175/app  .../plants-1.7.5.sql.gz
    git archive c67c60b app | tar -x -C /tmp/v1280       then  .../make_upgrade_fixture.py /tmp/v1280/app .../plants-1.28.0.sql.gz

    git archive fc85d81 app | tar -x -C /tmp/v1570       then  .../make_upgrade_fixture.py /tmp/v1570/app .../plants-1.57.0.sql.gz

**After each release, make the fixture of that release and take the last release's away** (three are kept: the first version, the
last before rooms and spots, and the version on Ethan's PC now, which is the upgrade his own record makes next).

It starts that version on an empty data folder (its own seed and batches), then does what a person does, through that version's
own routes: edits two plants by hand, adds a plant of their own with a photo, logs a feeding and a watering, answers a question,
archives a plant, makes a group, moves a plant indoors, and, where the version can, makes a shelf and puts a plant on it, sets up
a grow light spot, records what a pot is in with a repot, makes a plant-sitter link and turns the photos off in automatic backups
(as they were on his PC in November). A step the version has no page for is skipped and says so.
dev/test/unit/test_upgrade.py loads the result and lets this version upgrade it. The words below are what that test looks for
afterwards, so keep the two in step.
Every check before 1.58.0 started from a new install, while Ethan's database has come through every version since October."""
import gzip, io, os, sqlite3, sys, tempfile
from datetime import date, timedelta

EDITED_NOTES = 'Edited by hand before the upgrade.'
EDITED_LOCATION = 'Moved by hand to the back fence'
ADDED_NAME = 'My own added plant'
ANSWER = 'Answered before the upgrade'
WHO = 'Before the upgrade'
SHELF = 'Hand-made shelf'
LIGHT_SPOT = 'Hand-set light shelf'
MIX_PLANT, MIX_DAY = 'P-004', '2026-11-01'
LINK = 'fixture-link-fixture-link-0001'

def main(old_app, out):
    tmp = tempfile.mkdtemp(prefix='plantdb-fixture-')
    os.environ.update(DATA_DIR=tmp, PLANTDB_BACKUP_DIR=os.path.join(tmp, 'backups'), PLANTDB_WEATHER='0', PLANTDB_SHOPS='0', PLANTDB_OSM='0', PLANTDB_UPDATES='0',
                      PLANTDB_PUSH='0', PLANTDB_BACKUPS='0', PLANTDB_VISION='0', PLANTDB_VISION_URL='http://127.0.0.1:9', PLANTDB_ASPCA_MIN='0')
    os.makedirs(os.environ['PLANTDB_BACKUP_DIR'], exist_ok=True)
    version = os.path.basename(out).replace('plants-', '').replace('.sql.gz', '')
    os.environ['PLANTDB_VERSION'] = version              # the app folder alone has no VERSION file; from 1.31.0 the database remembers which version opened it
    sys.path.insert(0, old_app); os.chdir(old_app)
    import server as S                                   # the old version: makes its database from its seed and batches
    c = S.app.test_client(); H = {'X-Editor': WHO}
    def step(what, fn):
        try: r = fn()
        except Exception as e: print(f'skip  {what}: {type(e).__name__}: {e}'); return None
        ok = r.status_code in (200, 201)
        print(('ok    ' if ok else f'skip  ({r.status_code}) ') + what)
        return r if ok else None
    ver = lambda code: c.get(f'/api/plants/{code}').get_json()['version']
    step('edit the notes of P-003', lambda: c.put('/api/plants/P-003', json={'base_version': ver('P-003'), 'fields': {'notes': EDITED_NOTES}}, headers=H))
    step('edit the location of P-005', lambda: c.put('/api/plants/P-005', json={'base_version': ver('P-005'), 'fields': {'location': EDITED_LOCATION}}, headers=H))
    r = step('add a plant', lambda: c.post('/api/plants', json={'fields': {'common_name': ADDED_NAME, 'scientific_name': 'Ficus elastica', 'location': 'Kitchen window'}}, headers=H))
    code = r.get_json()['code'] if r else None
    if code:
        from PIL import Image
        b = io.BytesIO(); Image.new('RGB', (64, 48), (60, 120, 70)).save(b, 'JPEG'); b.seek(0)
        step(f'add a photo to {code}', lambda: c.post(f'/api/plants/{code}/photos', data={'files': (b, 'mine.jpg')}, content_type='multipart/form-data', headers=H))
    step('log a feeding for P-003', lambda: c.post('/api/fertilizer', json={'plants': ['P-003'], 'applied_on': '2026-10-20', 'product': 'Fish emulsion', 'n': 5, 'p': 1, 'k': 1}, headers=H))
    step('log a watering for P-003', lambda: c.post('/api/care', json={'plant': 'P-003', 'kind': 'water', 'done_on': '2026-10-21'}, headers=H))
    def answer():
        rows = c.get('/api/requests').get_json()
        rows = rows if isinstance(rows, list) else rows.get('requests', [])
        rid = next(x['id'] for x in rows if not x.get('done'))
        return c.put(f'/api/requests/{rid}', json={'done': True, 'answer': ANSWER}, headers=H)
    step('answer a question', answer)
    step('add to the photo list', lambda: c.post('/api/to-photograph', json={'label': 'The new shelf'}, headers=H))
    step('archive P-007', lambda: c.post('/api/plants/P-007/status', json={'archived': True}, headers=H))
    step('make a group', lambda: c.post('/api/groups', json={'name': 'Hand-picked before', 'kind': 'picked', 'codes': ['P-001', 'P-002']}, headers=H))
    step('put P-002 indoors', lambda: c.post('/api/plants/P-002/site', json={'site': 'Indoors'}, headers=H))
    # what later versions can do
    def shelf():
        it = next(x for x in c.get('/api/where/sort').get_json()['items'] if x['plants'])
        return c.post('/api/where/sort', json={'items': [{'text': it['text'], 'from_area_id': it['area_id'], 'area_id': it['area_id'], 'name': SHELF, 'codes': [it['plants'][0]['code']]}]}, headers=H)
    step('make a shelf and put a plant on it', shelf)
    def light_spot():
        L = c.get('/api/lights').get_json(); L = L if isinstance(L, list) else L.get('lights', [])
        return c.post('/api/lights/spots', json={'name': LIGHT_SPOT, 'light': L[0]['id'], 'units': 1, 'distance': 12, 'hours': 12, 'plants': ['P-001']}, headers=H)
    step('set up a grow light spot with P-001 under it', light_spot)
    def mix():
        am = c.get('/api/mixes').get_json()['amendments']
        return c.post(f'/api/mixes/plant/{MIX_PLANT}', json={'mixed_on': MIX_DAY, 'parts': [{'amendment_id': am[0]['id'], 'parts': 2}, {'amendment_id': am[1]['id'], 'parts': 1}], 'repot': True}, headers=H)
    step(f'record what {MIX_PLANT} is in, with a repot', mix)
    day = lambda n: (date.today() + timedelta(days=n)).isoformat()
    step('make a plant-sitter link', lambda: c.post('/api/sitter/shares', json={'from': day(2), 'to': day(5), 'note': 'Made before the upgrade'}, headers=H))
    step('turn the photos off in automatic backups', lambda: c.put('/api/backups/settings', json={'photos': False}, headers=H))
    db = sqlite3.connect(os.path.join(tmp, 'plants.db'))
    for k in ('ingest_token', 'ics_token', 'push_vapid_private', 'push_vapid_public'):          # made at random on a first start: not worth keeping
        db.execute("UPDATE settings SET value='fixture' WHERE key=?", (k,))
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='sitter_shares'").fetchone(): db.execute('UPDATE sitter_shares SET token=?', (LINK,))
    db.commit()
    n = db.execute('SELECT COUNT(*) FROM plants').fetchone()[0]
    sql = '\n'.join(db.iterdump()) + '\n'
    db.close()
    with open(out, 'wb') as f:
        with gzip.GzipFile(fileobj=f, mode='wb', mtime=0, filename='') as g: g.write(sql.encode('utf-8'))
    print(f'{out}: version {version}, {n} plants, {len(sql) // 1024} KB of SQL, {os.path.getsize(out) // 1024} KB zipped')

if __name__ == '__main__':
    if len(sys.argv) != 3: raise SystemExit(__doc__)
    main(os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2]))
