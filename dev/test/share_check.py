"""Checks 1.37.0: photos shared from a phone's share sheet (the service worker keeps them, the Shared photos page adds them to a
plant), the year in review, and the mirror (a second instance started read-only from a backup). Start the mock server with a
fresh data folder (MOCK_TS=1), then:  python3 dev/test/share_check.py      Screenshots: dev/tmp/shots/share-*.png"""
import glob, json, os, shutil, subprocess, sys, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(HERE, '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Share Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'gf@example.net', 'Tailscale-User-Name': 'Partner'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)
PHOTO = sorted(glob.glob(os.path.join(ROOT, 'dev', 'photos-raw', '**', '*.jpg'), recursive=True))[0]

# ---- the year in review
for d in ('2026-10-12', '2026-10-24'): call('POST', '/api/care', {'kind': 'water', 'plant': 'P-006', 'done_on': d})
v = call('GET', '/api/plants/P-006')[1]['version']
call('PUT', '/api/plants/P-006', {'base_version': v, 'fields': {'health_rating': 'Poor'}, 'note': 'went downhill'})
R = call('GET', '/api/review')[1]
p6 = next(p for p in R['plants'] if p['code'] == 'P-006')
check(R['year'] == 2026 and R['years'] == [2026] and R['totals']['plants'] > 50 and 'cold_nights' in R['weather'], f'the review covers {R["totals"]["plants"]} plants of {R["year"]}')
check(p6['water'] == 2 and p6['health']['trend'] == 'worse' and p6['health']['end'] == 'Poor' and p6['photos']['n'] >= 1, 'a plant\'s year: its waterings, how its health went, its photos')
check(call('GET', '/api/review?year=abc')[0] == 400 and call('GET', '/api/review?year=2019')[1]['plants'] == [], 'a bad year is refused; a year before the plants has none')

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Share Test')")
    pg.goto(LOCAL + '/#/review'); pg.wait_for_timeout(4000)
    check(pg.locator('h1').inner_text() == '2026 in review' and pg.locator('#sub-nav a[aria-current=page]').inner_text().strip() == 'Year in review' and pg.locator('.rv-card').count() > 50, 'the Year in review page sits in the Plants row, one card per plant')
    first = pg.locator('.rv-card').first
    check('rv-bad' in first.get_attribute('class') and 'P-006' in first.inner_text() and 'health Fair → Poor' in first.inner_text().replace('Good → Poor', 'Fair → Poor'), 'the plant with the hardest year comes first, with its story in words')
    pg.select_option('select[data-act=rvonly]', 'better'); pg.wait_for_timeout(1500)
    check(pg.locator('.rv-card').count() < 50, 'the Show choice narrows the cards')
    pg.screenshot(path=f'{OUT}/share-review.png', full_page=False)

    # ---- the share sheet: the service worker keeps the pictures, the page adds them to a plant
    pg.goto(LOCAL + '/#/photos'); pg.wait_for_timeout(3500)
    check(pg.locator('a[href="#/share"]').count() == 1, 'the Photos page links to the shared photos')
    check(pg.evaluate("navigator.serviceWorker.controller ? true : false"), 'the service worker is in charge of the page')
    pg.evaluate("() => { const f = document.createElement('form'); f.method = 'POST'; f.action = '/share-in'; f.enctype = 'multipart/form-data'; const i = document.createElement('input'); i.type = 'file'; i.name = 'photos'; f.appendChild(i); document.body.appendChild(f); window.__f = f; }")
    pg.set_input_files('form[action="/share-in"] input', PHOTO)
    pg.evaluate("window.__f.submit()"); pg.wait_for_timeout(4000)
    check(pg.url.endswith('#/share') and pg.locator('h1').inner_text() == 'Photos shared with Plant record' and pg.locator('.share-grid img').count() == 1, 'sharing a picture lands on the Shared photos page with the picture shown')
    pg.screenshot(path=f'{OUT}/share-page.png')
    n0 = len(call('GET', '/api/plants/P-012')[1]['photos'])
    pg.select_option('form[data-form=shareadd] select', 'P-012'); pg.fill('form[data-form=shareadd] input[name=caption]', 'From the phone'); pg.click('form[data-form=shareadd] button[type=submit]'); pg.wait_for_timeout(4500)
    ph = call('GET', '/api/plants/P-012')[1]['photos']
    check(len(ph) == n0 + 1 and any(x['caption'] == 'From the phone' for x in ph) and pg.url.endswith('#/plant/P-012?sec=photos'), 'Add puts it on the chosen plant with the caption and opens the plant page at its photos')
    pg.goto(LOCAL + '/#/share'); pg.wait_for_timeout(2500)
    check('Nothing shared right now' in pg.inner_text('main'), 'and the shared pictures are cleared')
    # the fallback without a service worker: the server takes the share as unassigned photos
    import mimetypes
    boundary = '----plantrec'
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="photos"; filename="shared.jpg"\r\nContent-Type: image/jpeg\r\n\r\n').encode() + open(PHOTO, 'rb').read() + f'\r\n--{boundary}--\r\n'.encode()
    req = urllib.request.Request(LOCAL + '/share-in', data=body, method='POST', headers={'Content-Type': f'multipart/form-data; boundary={boundary}', 'X-Editor': 'Share Test'})
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k): return None
    try: urllib.request.build_opener(NoRedirect).open(req); st = 200
    except urllib.error.HTTPError as e: st = e.code
    check(st == 303 and any(x['caption'] == 'shared.jpg' for x in call('GET', '/api/photos/unassigned')[1]), 'without a service worker, the server keeps a shared picture as an unassigned photo')
    # 1.58.0: the old address (/share, the prefix Funnel publishes for sitter links) takes no pictures from the server any more;
    # an installed app that still has it is answered by the service worker, as the first part of this check does for /share-in
    req = urllib.request.Request(LOCAL + '/share', data=body, method='POST', headers={'Content-Type': f'multipart/form-data; boundary={boundary}', 'X-Editor': 'Share Test'})
    try: urllib.request.build_opener(NoRedirect).open(req); st = 200
    except urllib.error.HTTPError as e: st = e.code
    check(st == 405, f'the server no longer takes pictures at /share ({st})')
    pg.goto(LOCAL + '/#/photos'); pg.wait_for_timeout(2500)
    pg.evaluate("() => { const f = document.createElement('form'); f.method = 'POST'; f.action = '/share'; f.enctype = 'multipart/form-data'; f.id = 'oldshare'; const i = document.createElement('input'); i.type = 'file'; i.name = 'photos'; f.appendChild(i); document.body.appendChild(f); window.__g = f; }")
    pg.set_input_files('#oldshare input', PHOTO)
    pg.evaluate("window.__g.submit()"); pg.wait_for_timeout(4000)
    check(pg.url.endswith('#/share') and pg.locator('.share-grid img').count() == 1, 'an installed app with the old address still works: the service worker takes the share')
    b.close()

# ---- the mirror: a second instance, read-only, fed from a backup of this one
st, r = call('POST', '/api/backups', {'photos': True})
for i in range(40):
    time.sleep(1)
    if not call('GET', '/api/backups/job')[1].get('running'): break
backs = call('GET', '/api/backups')[1]['backups']
name = next((x['file'] for x in backs if x.get('photos')), None)
check(bool(name), f'a backup with photos was made ({name})')
MI = os.path.join(HERE, '..', 'tmp', 'mirror-in'); MD = os.path.join(HERE, '..', 'tmp', 'mirror-data')
shutil.rmtree(MI, ignore_errors=True); shutil.rmtree(MD, ignore_errors=True); os.makedirs(MI); os.makedirs(MD)
with open(os.path.join(MI, name), 'wb') as f: f.write(urllib.request.urlopen(LOCAL + '/api/backups/' + name).read())
env = dict(os.environ, DATA_DIR=MD, PLANTDB_MIRROR='1', PLANTDB_MIRROR_IN=MI, PLANTDB_MIRROR_MAIN='https://plants.example.ts.net', PLANTDB_MIRROR_MINUTES='1',
           PLANTDB_OSM='0', PLANTDB_WEATHER='0', PLANTDB_SHOPS='0', PLANTDB_PUSH='0', PLANTDB_VISION_URL='http://127.0.0.1:9', PLANTDB_SENSOR_PORT='8382', PLANTDB_TS_PORT='8381')
proc = subprocess.Popen([sys.executable, '-c', "import sys; sys.path.insert(0, 'app'); import server; server.app.run(host='127.0.0.1', port=8380, threaded=True)"], cwd=ROOT, env=env, stdout=open(os.path.join(HERE, '..', 'tmp', 'mirror.log'), 'w'), stderr=subprocess.STDOUT)
try:
    M = 'http://127.0.0.1:8380'
    for i in range(60):
        time.sleep(1)
        try:
            if json.loads(urllib.request.urlopen(M + '/api/mirror').read()).get('last'): break
        except Exception: pass
    mi = json.loads(urllib.request.urlopen(M + '/api/mirror').read())
    check(mi['on'] and mi['last'] == name and mi['made'] and not mi['error'], f'the mirror took the backup ({mi.get("last")})')
    check(len(call('GET', '/api/plants', base=M)[1]) == len(call('GET', '/api/plants')[1]) and len(call('GET', '/api/plants/P-012', base=M)[1]['photos']) == len(call('GET', '/api/plants/P-012')[1]['photos']), 'it shows the same plants and photos')
    check(call('GET', '/api/me', base=M)[1]['role'] == 'viewer' and call('POST', '/api/care', {'kind': 'water', 'plant': 'P-001'}, base=M)[0] == 403, 'everyone on the mirror can only look; a change is refused')
    check(call('GET', '/api/meta', base=M)[1]['mirror']['main'] == 'https://plants.example.ts.net', 'the pages know the main app\'s address')
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1280, 'height': 900}); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(M + '/#/plants'); pg.wait_for_timeout(3500)
        note = pg.locator('.mirror-note')
        check(note.count() == 1 and note.inner_text().startswith('This is the mirror') and note.locator('a[href="https://plants.example.ts.net"]').count() == 1 and not pg.locator('a[href="#/new"]').first.is_visible(), 'every page says it is the mirror, links to the main app, and hides the editing buttons')
        pg.screenshot(path=f'{OUT}/share-mirror.png', clip={'x': 0, 'y': 0, 'width': 1280, 'height': 420})
        b.close()
finally:
    proc.terminate()
    try: proc.wait(10)
    except subprocess.TimeoutExpired: proc.kill()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
