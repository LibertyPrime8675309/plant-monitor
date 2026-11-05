"""Checks 1.38.0, "phone and offline": a watering made offline leaves the Today list at once; the app notices when the plant server
can be reached again (and "Try to connect now"); Back returns to the same place on a page; photos on the single Add a plant form, with
the names filled in from the first photo; a plant added without a connection is kept, sent later, and its photo is then checked.
This check runs its own mock server (port 8480) so it can stop and start it; the server on 8080 is not used.
    python3 dev/test/phone_check.py      Screenshots: dev/tmp/shots/phone-*.png"""
import glob, json, os, shutil, subprocess, sys, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(HERE, '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
DATA = os.path.join(HERE, '..', 'tmp', 'phone-data'); LOG = os.path.join(HERE, '..', 'tmp', 'phone-server.log')
B = 'http://127.0.0.1:8480'
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None):
    req = urllib.request.Request(B + u, data=None if body is None else json.dumps(body).encode(), method=method, headers={'Content-Type': 'application/json', 'X-Editor': 'Phone Test'})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
PHOTOS = sorted(glob.glob(os.path.join(ROOT, 'dev', 'photos-raw', '**', '*.jpg'), recursive=True))[:3]
SERVER = None
def start(fresh):
    global SERVER
    if fresh: shutil.rmtree(DATA, ignore_errors=True); os.makedirs(DATA)
    env = dict(os.environ, PORT='8480', PLANTDB_TS_PORT='8481', PLANTDB_SENSOR_PORT='8482', MOCK_VISION_PORT='8490', MOCK_TS='1', MOCK_BASE_F='40', DATA_DIR=DATA)
    env.pop('MOCK_VISION', None)
    SERVER = subprocess.Popen([sys.executable, os.path.join(HERE, 'mock_server.py')], cwd=ROOT, env=env, stdout=open(LOG, 'a'), stderr=subprocess.STDOUT)
    for _ in range(60):
        time.sleep(1)
        try: urllib.request.urlopen(B + '/api/meta', timeout=2).read(); break
        except Exception: pass
    else: raise SystemExit('the phone check\'s server did not start; see ' + LOG)
    if fresh:
        try: urllib.request.urlopen(urllib.request.Request(B + '/api/weather/refresh', data=b'{}', headers={'X-Editor': 'Test', 'Content-Type': 'application/json'}), timeout=10).read()
        except Exception: pass
        for _ in range(40):
            time.sleep(3)
            try:
                if b'"running": false' in urllib.request.urlopen(B + '/api/weather/job', timeout=5).read().replace(b'"running":false', b'"running": false'): break
            except Exception: pass
def stop():
    if not SERVER: return
    SERVER.terminate()
    try: SERVER.wait(10)
    except subprocess.TimeoutExpired: SERVER.kill()
    time.sleep(1)
def wait_net(pg, word, secs):
    for i in range(secs // 2):
        pg.wait_for_timeout(2000)
        if pg.locator('#net').inner_text().startswith(word): return (i + 1) * 2
    return None

start(True)
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={'width': 400, 'height': 800}, is_mobile=True, has_touch=True)
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.add_init_script("localStorage.setItem('plantdb.editor','Phone Test')")
        pg.goto(B + '/#/'); pg.wait_for_timeout(4000)       # the first visit registers the service worker; these pages are then saved on the device
        pg.goto(B + '/#/plants'); pg.wait_for_timeout(3000)
        pg.goto(B + '/#/'); pg.wait_for_timeout(3000)
        check(pg.evaluate('!!navigator.serviceWorker.controller'), 'the service worker is in charge of the page')
        code = pg.locator('#today-water .job').first.get_attribute('data-code'); n0 = pg.locator('#today-water .job').count()
        pg.goto(B + '/#/plant/' + code); pg.wait_for_timeout(3000)
        st, F = call('GET', '/api/frost'); cold = next(x for x in F['plants'] if x['plan'] == 'Move indoors' and x['code'] != code)['code']
        pg.goto(B + '/#/frost'); pg.wait_for_timeout(3000)
        pg.goto(B + '/#/new'); pg.wait_for_timeout(2500)
        pg.goto(B + '/#/'); pg.wait_for_timeout(3000)

        # ---- Today, offline: Watered leaves the list at once, and the care log shows the entry as waiting
        stop()
        pg.click(f'#today-water .job[data-code="{code}"] [data-kind=water]'); pg.wait_for_timeout(8000)
        check(pg.locator('#net').inner_text().startswith('Offline') and pg.locator(f'#today-water .job[data-code="{code}"]').count() == 0 and pg.locator('#today-water .job').count() == n0 - 1,
              'offline, "Watered" takes the plant off the Water list at once and the badge says Offline')
        note = pg.locator('.off-note')
        check(note.count() >= 1 and 'what this device saved' in note.first.inner_text() and pg.locator('[data-act=offtry]').count() == 1, 'the page says it shows what the device saved, with "Try to connect now"')
        pg.screenshot(path=f'{OUT}/phone-today-offline.png')
        pg.goto(B + '/#/plant/' + code); pg.wait_for_timeout(5000)
        log = pg.locator('.care-log li').first
        check(log.count() == 1 and log.inner_text().startswith('Watered') and 'not sent yet' in log.inner_text() and log.locator('[data-act=caredel]').count() == 0,
              'the plant\'s care log shows the watering as not sent yet, without a Remove button')
        pg.click('[data-act=offtry]'); pg.wait_for_timeout(1500)
        check(pg.locator('.toast').count() == 1 and 'cannot be reached' in pg.locator('.toast').inner_text(), '"Try to connect now" says the plant server still cannot be reached')
        # the other changes made from a phone show at once too: other care, and the cold-night list
        pg.click('[data-act=careother]'); pg.wait_for_timeout(800)
        pg.select_option('#dlg select[name=kind]', 'repot'); pg.fill('#dlg input[name=note]', 'offline repot'); pg.click('#dlg button[value=ok]'); pg.wait_for_timeout(4000)
        logs = pg.locator('.care-log li').all_inner_texts()
        check(len(logs) >= 2 and logs[0].startswith('Repotted') and 'offline repot' in logs[0] and 'not sent yet' in logs[0], '"Log other care" offline: the entry shows in the care log as not sent yet')
        pg.goto(B + '/#/frost'); pg.wait_for_timeout(4000)
        n_rows = pg.locator('.fz-row').count()
        pg.click(f'[data-act=frostin][data-code="{cold}"]'); pg.wait_for_timeout(4000)
        check(pg.locator(f'.fz-row[data-code="{cold}"]').count() == 0 and pg.locator('.fz-row').count() == n_rows - 1, f'"Moved indoors" offline takes the plant off the cold-night list at once ({cold}: rows {n_rows} -> {pg.locator(".fz-row").count()}; {[t[:60] for t in pg.locator(".toast").all_inner_texts()]})')
        # ---- the server comes back: the app notices on its own (every 30 seconds), sends the outbox and shows the real page
        start(False)
        took = wait_net(pg, 'Online', 70)
        check(took is not None, f'the badge goes back to Online on its own once the server answers ({took} s)')
        pg.wait_for_timeout(3000)
        st, log = call('GET', '/api/care?n=3&plant=' + code)
        check(log and {log[0]['kind'], log[1]['kind']} == {'water', 'repot'} and call('GET', '/api/plants/' + cold)[1]['site'] == 'Indoors', 'the watering, the repotting and the move made offline reached the server')
        check(pg.locator('.off-note').count() == 0 and pg.locator('.fz-row').count() == n_rows - 1, 'the page is drawn again from the server: no offline note, and the list is the real one')

        # ---- Back returns to where you were
        pg.goto(B + '/#/plants'); pg.wait_for_timeout(3000)
        pg.evaluate('window.scrollTo(0, 2200)'); pg.wait_for_timeout(300)
        pg.evaluate("document.querySelectorAll('.sheet-link')[5].click()"); pg.wait_for_timeout(2500)     # a click without Playwright scrolling the link into view
        check(pg.url.split('#')[1].startswith('/plant/') and pg.evaluate('window.scrollY') == 0, 'a link to a plant opens its page at the top')
        pg.go_back(); pg.wait_for_timeout(2500)
        y = pg.evaluate('window.scrollY')
        check(pg.url.endswith('#/plants') and abs(y - 2200) < 60, f'Back returns to the same place on the Plants page ({y})')
        check(pg.evaluate("getComputedStyle(document.querySelector('.sheet .mat img') || document.body).aspectRatio") not in ('auto', ''), 'photo boxes have their size before the photo arrives, so the page does not jump')

        # ---- the single Add a plant form: photos from the phone, names from the first photo, no forced camera
        pg.goto(B + '/#/new'); pg.wait_for_timeout(2500)
        check(pg.locator('input[name=__photos]').count() == 1 and pg.locator('input[type=file][capture]').count() == 0 and pg.locator('#newfill-btn').is_disabled(), 'the form has a Photos field; nothing forces the camera open, so the phone offers its photos too')
        save = pg.locator('form[data-form=new] button[type=submit]'); save.scroll_into_view_if_needed(); pg.wait_for_timeout(400)
        sb, cb = save.bounding_box(), pg.locator('#corner').bounding_box()
        check(sb and cb and sb['y'] + sb['height'] <= cb['y'] + 1, 'the Save bar sits above the bottom bar, not under it')
        pg.set_input_files('input[name=__photos]', PHOTOS[:2]); pg.wait_for_timeout(400)
        check(not pg.locator('#newfill-btn').is_disabled() and not pg.evaluate("document.querySelector('input[name=common_name]').required"), 'with photos chosen, the names can be filled in from the first one, and the common name may wait')
        pg.click('#newfill-btn'); pg.wait_for_timeout(6000)
        st = pg.locator('#newfill-st').inner_text()
        check(st.startswith('Filled in:') and pg.input_value('input[name=common_name]') == 'Texas bluebonnet' and pg.input_value('input[name=scientific_name]') == 'Lupinus texensis', f'the picture checker fills in the names ({st[:60]})')
        pg.click('form[data-form=new] button[type=submit]'); pg.wait_for_timeout(6000)
        new1 = pg.url.split('/plant/')[-1]
        st, d = call('GET', '/api/plants/' + new1)
        check(st == 200 and len(d['photos']) == 2 and d['photos'][0]['is_primary'] and d['id_basis'].startswith('Suggested by the picture checker'), 'saving adds the plant with both photos, the first as its main photo')
        pg.screenshot(path=f'{OUT}/phone-new-plant.png')

        # ---- a plant added without a connection: kept with a stand-in name, sent later, its first photo checked then
        pg.goto(B + '/#/new'); pg.wait_for_timeout(2500)
        stop()
        pg.set_input_files('input[name=__photos]', PHOTOS[:1]); pg.wait_for_timeout(300)
        pg.click('#newfill-btn'); pg.wait_for_timeout(9000)
        check('needs a connection' in pg.locator('#newfill-st').inner_text(), 'without a connection the form says the photo is checked later')
        pg.fill('input[name=location]', 'Kitchen window')
        pg.click('form[data-form=new] button[type=submit]'); pg.wait_for_timeout(6000)
        ops = pg.locator('.off-list li').all_inner_texts()
        check(pg.url.endswith('#/offline') and len(ops) >= 3 and ops[0].startswith('New plant NEW-') and 'New plant,' in ops[0] and '1 photo added' in ops[1] and 'Waiting for a connection' in ops[2],
              'the plant waits on the Offline page with a stand-in name, its photo and its picture to check')
        pg.screenshot(path=f'{OUT}/phone-offline-add.png')
        pg.goto(B + '/#/plants'); pg.wait_for_timeout(5000)
        check(any('1 new plant waiting to be sent' in t for t in pg.locator('.off-note').all_inner_texts()), 'the Plants page says a new plant is waiting')
        start(False)
        took = wait_net(pg, 'Online', 70); pg.wait_for_timeout(8000)
        st, plants = call('GET', '/api/plants')
        new2 = plants[-1]
        st, d = call('GET', '/api/plants/' + new2['code'])
        check(new2['code'] != new1 and d['common_name'].startswith('New plant,') and d['location'] == 'Kitchen window' and len(d['photos']) == 1, 'back online, the plant is added with its photo and the stand-in name')
        pg.goto(B + '/#/offline'); pg.wait_for_timeout(3000)
        row = pg.locator('.off-list li', has_text='It looks most like')
        check(row.count() == 1 and new2['code'] in row.inner_text() and row.locator('[data-act=offiduse]').count() == 1, 'the Offline page shows what the photo looks like, for the new plant, with a button to use the name')
        pg.click('[data-act=offiduse]'); pg.wait_for_timeout(4000)
        st, d = call('GET', '/api/plants/' + new2['code'])
        check(d['common_name'] == 'Texas bluebonnet' and d['scientific_name'] == 'Lupinus texensis' and d['id_confidence'] == 41 and pg.url.endswith('#/plant/' + new2['code']), 'the name goes on the plant, and its page opens')
        b.close()
finally:
    stop()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
