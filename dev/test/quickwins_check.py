"""Checks 1.31.0: Windows High Contrast mode (the chosen filter, links and focus stay visible), the Problems list on Settings,
Restore from a backup (a backup first, photos kept, a newer backup refused), the home each person starts on, the downgrade guard
(an older version will not change a newer database), and the new indexes. Start the mock server with a fresh data folder
(MOCK_TS=1), then:  python3 dev/test/quickwins_check.py      Screenshots: dev/tmp/shots/quickwins-*.png"""
import io, json, os, shutil, sqlite3, subprocess, sys, time, urllib.request, urllib.error, zipfile
from PIL import Image
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
DATA = os.path.join(HERE, '..', 'tmp', 'data'); DB = os.path.join(DATA, 'plants.db'); BK = os.path.join(DATA, 'backups')
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Quick Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'gf@example.net', 'Tailscale-User-Name': 'Partner'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)
plant = lambda c: call('GET', '/api/plants/' + c)[1]

# indexes
c = sqlite3.connect(DB)
idx = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='index'")}
check({'readings_src_dev_ts', 'offers_wish', 'offer_hist', 'photos_plant'} <= idx, 'the new indexes are there')
check(c.execute("SELECT value FROM settings WHERE key='db_version'").fetchone()[0] == call('GET', '/api/meta')[1]['version'], 'the database remembers the version that opened it')
c.close()

# problems
check(call('GET', '/api/problems')[1]['open'] == 0, 'nothing is on the Problems list to start with')
for _ in range(2): call('POST', '/mock/problem', {'area': 'weather', 'text': 'The weather for Round Rock, TX could not be updated', 'detail': 'Could not reach Open-Meteo'})
call('POST', '/mock/problem', {'area': 'backup', 'text': 'The backup failed', 'detail': 'disk full'})
pr = call('GET', '/api/problems')[1]
check(pr['open'] == 2 and pr['problems'][0]['area_word'] == 'Backup' and next(p for p in pr['problems'] if p['area'] == 'weather')['times'] == 2,
      'problems are listed in plain words, and the same one again counts up instead of repeating')
check(call('POST', '/api/problems', {'id': pr['problems'][0]['id']}, V, TS)[0] == 403, 'someone who can only view cannot clear them')
check(call('POST', '/api/problems', {'id': pr['problems'][0]['id']}, E, TS)[0] == 200 and call('GET', '/api/problems')[1]['open'] == 1, 'the owner can clear one')

# a person's home
check(call('PUT', '/api/people', {'login': 'gf@example.net', 'home_id': 999}, E, TS)[0] == 400, 'a person must start on one of your homes')
nc = [h for h in call('GET', '/api/people', h=E, base=TS)[1]['homes'] if h['name'].startswith('Nevada')][0]['id']
r = call('PUT', '/api/people', {'login': 'gf@example.net', 'role': 'editor', 'home_id': nc}, E, TS)[1]
check(next(p for p in r['people'] if p['login'] == 'gf@example.net')['home_id'] == nc, 'the owner can say which home a person starts on')
pf = call('GET', '/api/me/prefs', h=V, base=TS)[1]['prefs']
check(pf.get('place') == str(nc), 'she starts on Nevada City')
call('PUT', '/api/me/prefs', {'place': None}, V, TS)
check('place' not in call('GET', '/api/me/prefs', h=V, base=TS)[1]['prefs'], 'but when she chooses the main home herself, that choice stands')
check('place' not in call('GET', '/api/me/prefs', h=E, base=TS)[1]['prefs'], "and Ethan's own start is unchanged")

# restore
p14 = plant('P-014')
st, b1 = call('POST', '/api/backups', {'photos': True, 'note': 'Before the test'})
for _ in range(40):
    time.sleep(0.5)
    if not call('GET', '/api/backups/job')[1].get('running'): break
backs = call('GET', '/api/backups')[1]['backups']
first = backs[0]['file']
call('PUT', '/api/plants/P-014', {'base_version': p14['version'], 'fields': {'notes': 'Changed after the backup'}})
check(plant('P-014')['notes'] == 'Changed after the backup', 'a change is made after the backup')
im = Image.new('RGB', (200, 200), (90, 140, 60)); buf = io.BytesIO(); im.save(buf, 'JPEG')
boundary = 'xxBOUNDARYxx'
body = (f'--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="after.jpg"\r\nContent-Type: image/jpeg\r\n\r\n').encode() + buf.getvalue() + f'\r\n--{boundary}--\r\n'.encode()
req = urllib.request.Request(LOCAL + '/api/plants/P-014/photos', data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}', 'X-Editor': 'Quick Test'})
urllib.request.urlopen(req).read()
nphotos = len(plant('P-014')['photos'])
check(call('POST', '/api/backups/restore', {'file': first}, V, TS)[0] == 403, 'someone who is not the owner cannot restore')
st, r = call('POST', '/api/backups/restore', {'file': first}, E, TS)
check(st == 200 and r['ok'] and r['before'].startswith('plantdb-backup-'), f'the owner can restore, and a backup is made first ({r.get("before")})')
check(plant('P-014')['notes'] == p14['notes'], 'the change made after the backup is gone')
check(len(plant('P-014')['photos']) == nphotos - 1 and os.path.exists(os.path.join(DATA, 'photos', [f for f in os.listdir(os.path.join(DATA, 'photos')) if f][0])), 'the record is back as it was, and no photo file was deleted')
check(any(b['note'].startswith('Before restoring') for b in call('GET', '/api/backups')[1]['backups']), 'the "before restoring" backup is on the list')
# a backup from a newer version is refused
newer = os.path.join(BK, 'plantdb-backup-20991231-000000-manual.zip')
with zipfile.ZipFile(newer, 'w') as z:
    z.writestr('plants.db', open(DB, 'rb').read()); z.writestr('backup.json', json.dumps({'version': '99.0.0', 'created_at': '2099-12-31T00:00:00Z'}))
st, r = call('POST', '/api/backups/restore', {'file': os.path.basename(newer)}, E, TS)
check(st == 400 and 'newer' in r.get('error', ''), 'a backup made by a newer version is refused, with what to do')
os.remove(newer)

# the downgrade guard: a copy of the database marked as opened by a newer version, opened by this one, in another process
tmp = os.path.join(HERE, '..', 'tmp', 'dg'); shutil.rmtree(tmp, ignore_errors=True); os.makedirs(tmp)
shutil.copy(DB, os.path.join(tmp, 'plants.db'))
c = sqlite3.connect(os.path.join(tmp, 'plants.db')); c.execute("UPDATE settings SET value='99.0.0' WHERE key='db_version'"); c.commit(); c.close()
code = '''
import os, sys; sys.path.insert(0, sys.argv[1]); import server
t = server.app.test_client()
r1 = t.get('/'); r2 = t.get('/api/meta'); r3 = t.get('/healthz')
print(r1.status_code, r2.status_code, r3.status_code, b'newer' in r1.data, r2.get_json().get('newer_db'))
'''
env = dict(os.environ, DATA_DIR=tmp, PLANTDB_WEATHER='0', PLANTDB_SHOPS='0', PLANTDB_OSM='0', PLANTDB_VISION_URL='http://127.0.0.1:9')
out = subprocess.run([sys.executable, '-c', code, os.path.join(HERE, '..', '..', 'app')], env=env, capture_output=True, text=True, timeout=120)
line = (out.stdout.strip().splitlines() or [''])[-1]
check(line.startswith('503 503 503 True 99.0.0'), f'an older version refuses to run on a newer database, and says which version to install ({line or out.stderr[-200:]})')
c = sqlite3.connect(os.path.join(tmp, 'plants.db')); check(c.execute("SELECT value FROM settings WHERE key='db_version'").fetchone()[0] == '99.0.0', 'and changes nothing in it'); c.close()

with sync_playwright() as p:
    b = p.chromium.launch()
    # High Contrast mode
    ctx = b.new_context(viewport={'width': 1400, 'height': 900}, forced_colors='active', color_scheme='dark', extra_http_headers=E)
    ctx.add_init_script("localStorage.setItem('plantdb.editor','Ethan')")
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(TS + '/#/shopping'); pg.wait_for_timeout(2500)
    chosen = pg.locator('fieldset.buy-kinds-r input:checked + span').first
    st = chosen.evaluate("e => { const s = getComputedStyle(e); return [s.outlineStyle, s.outlineWidth, s.textDecorationLine, s.backgroundColor !== getComputedStyle(e.parentElement.parentElement).backgroundColor]; }")
    check(st[0] == 'solid' and st[1] != '0px' and 'underline' in st[2] and st[3], f'in High Contrast mode the chosen filter has an outline, an underline and its own colour ({st})')
    cur = pg.locator('#sub-nav a[aria-current=page]').evaluate("e => { const s = getComputedStyle(e); return [s.outlineStyle, s.textDecorationLine]; }")
    check(cur[0] == 'solid' and 'underline' in cur[1], 'the page you are on is outlined and underlined in the top bar')
    pg.keyboard.press('Tab'); pg.keyboard.press('Tab')
    foc = pg.evaluate("(() => { const e = document.activeElement, s = getComputedStyle(e); return [e.tagName, s.outlineStyle, s.outlineWidth]; })()")
    check(foc[1] == 'solid' and foc[2] != '0px', f'keyboard focus is outlined ({foc})')
    pg.screenshot(path=os.path.join(OUT, 'quickwins-1-contrast.png'))
    ctx.close()
    # Settings: Problems, the people list's home, and Restore on the Backups page
    ctx = b.new_context(viewport={'width': 1400, 'height': 900}, extra_http_headers=E)
    ctx.add_init_script("localStorage.setItem('plantdb.editor','Ethan')")
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.goto(TS + '/#/settings'); pg.wait_for_timeout(2500)
    check('(1)' in pg.locator('[data-act=problems]').inner_text(), 'Settings says how many problems are waiting')
    pg.locator('[data-act=problems]').click(); pg.wait_for_timeout(1000)
    check(pg.locator('#dlg .prob-list li').count() == 1 and 'Weather update' in pg.locator('#dlg').inner_text(), 'the Problems window lists them in plain words')
    pg.locator('[data-act=proball]').click(); pg.wait_for_timeout(1000)
    check(pg.locator('#dlg .prob-list li').count() == 2, 'and can show the cleared ones too')
    pg.screenshot(path=os.path.join(OUT, 'quickwins-2-problems.png'))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    pg.locator('main [data-act=who]').first.click(); pg.wait_for_timeout(1200)
    sel = pg.locator('#dlg select[data-f=phome][data-login="gf@example.net"]')
    check(sel.count() == 1 and sel.input_value() == str(nc), 'the people list shows which home each person starts on')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    pg.goto(TS + '/#/backups'); pg.wait_for_timeout(2500)
    check(pg.locator('[data-act=bkrestore]').count() >= 2, 'every backup has a Restore button')
    pg.locator('[data-act=bkrestore]').last.click(); pg.wait_for_timeout(500)
    check('backup of how things are now is made first' in pg.locator('#dlg').inner_text(), 'Restore explains what happens before it does anything')
    pg.screenshot(path=os.path.join(OUT, 'quickwins-3-restore.png'))
    pg.keyboard.press('Escape')
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All quick-wins checks passed' if not fails else f'{len(fails)} quick-wins check(s) failed'))
raise SystemExit(1 if fails else 0)
