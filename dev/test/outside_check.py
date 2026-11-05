"""Checks the Back outside list (prototype: proto/move-outside). Runs its own copy of the app, so no mock server is needed:
  python3 dev/test/outside_check.py        screenshots go to dev/tmp/shots/outside-*.png
It makes a fresh install in dev/tmp/outside-check/, pretends today is March 20, 2027, writes a made-up 7-day forecast and
six years of made-up daily lows (coldest in mid-January, warmest in mid-July), moves a few plants inside, then checks the
levels from /api/outside and the page in a browser at laptop and phone width, light and dark."""
import json, math, os, shutil, sys, threading
from datetime import date, timedelta
HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(HERE, '..', 'tmp', 'outside-check')
OUT = os.path.join(HERE, '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
shutil.rmtree(TMP, ignore_errors=True)
os.environ.update(DATA_DIR=os.path.join(TMP, 'data'), PLANTDB_BACKUP_DIR=os.path.join(TMP, 'backups'), PLANTDB_WEATHER='0')
sys.path.insert(0, os.path.join(HERE, '..', '..', 'app'))
import server as S
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server, WSGIRequestHandler
WSGIRequestHandler.log_request = lambda *a, **k: None

TODAY = date(2027, 3, 20)
LOWS = [52, 58, 61, 50, 63, 66, 60]            # the forecast: coldest 50°F on March 23
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)

S.init_db()
S.patch('local_today', lambda c: TODAY)
c = S.sqlite3.connect(S.DB_PATH)
home = c.execute('SELECT id FROM locations WHERE is_home=1').fetchone()[0]
days = [{'date': (TODAY + timedelta(days=i)).isoformat(), 'low': v, 'high': v + 20} for i, v in enumerate(LOWS)]
c.execute('UPDATE locations SET forecast=? WHERE id=?', (json.dumps({'fetched_at': '2027-03-20T12:00:00Z', 'days': days}), home))
d = date(2021, 1, 1)
while d < date(2027, 1, 1):
    doy = d.timetuple().tm_yday
    low = round(57 - 20 * math.cos((doy - 15) / 365 * 2 * math.pi) + (d.year % 3 - 1) * 1.5, 1)
    c.execute("INSERT OR REPLACE INTO weather_daily(loc_id,date,data,kind,updated_at) VALUES(?,?,?,'observed','x')",
              (home, d.isoformat(), json.dumps({'temperature_2m_min': low}), ))
    d += timedelta(days=1)
c.execute("UPDATE plants SET site='Indoors' WHERE code IN ('P-001','P-003','P-005','P-008','P-012','P-013')")
c.execute("UPDATE plants SET site='Garage or shed' WHERE code='P-007'")
c.execute("UPDATE plants SET temp_damage_below=46 WHERE code='P-005'")      # safe at 49°F: fine this week, but early by the history
c.commit(); c.close()

# ---- the levels
api = S.app.test_client().get('/api/outside').get_json()
lv = {p['code']: p['level'] for p in api['plants']}
print('     ', lv, api['counts'])
check(api['season'] == 'spring', 'March counts as spring')
check(len(api['plants']) == 7, '7 plants inside are listed')
check(lv.get('P-012') == 'ready' and lv.get('P-013') == 'ready', 'Aeonium and prickly pear (like 50°F, coldest night 50°F) are ready')
check(lv.get('P-003') == 'safe' and lv.get('P-008') == 'safe', 'fig and bougainvillea are safe but cool')
check(lv.get('P-005') == 'early', 'a plant safe at 49°F is too early: in most years nights stay above 49°F only from late March')
check(lv.get('P-001') == 'wait', 'dieffenbachia (damaged below 50°F) waits: 50°F is within 3°F of its damage point')
dief = next(p for p in api['plants'] if p['code'] == 'P-001')
check(dief['first_cold']['date'] == '2027-03-20' and dief['first_cold']['low'] == 52, 'its first too-cold night is tonight, 52°F')
check(dief['usual'] and '04-01' <= dief['usual']['safe'] <= '04-12', f"usual date for 53°F is early April ({dief['usual'] and dief['usual']['safe']})")
order = [p['level'] for p in api['plants']]
check(order == sorted(order, key=S.BO_LEVELS.index), 'ready first, not yet last')
# no forecast: listed, but no level
u = S.bo_usual({}, 40)
check(u is None, 'no history: no usual dates')

# ---- the page
srv = make_server('127.0.0.1', 8093, S.app, threaded=True)
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = 'http://127.0.0.1:8093'
with sync_playwright() as p:
    b = p.chromium.launch()
    for size, (w, h, text) in {'laptop': (1280, 900, ''), 'phone': (390, 844, '160')}.items():
        for theme in ('light', 'dark'):
            pg = b.new_page(viewport={'width': w, 'height': h})
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: m.type == 'error' and '404' not in m.text and errs.append(m.text))
            prefs = {'theme': theme, **({'size': text} if text else {})}
            pg.add_init_script("localStorage.setItem('plantdb.editor','Outside Test');localStorage.setItem('plantdb.display',JSON.stringify(%s))" % json.dumps(prefs))
            pg.goto(BASE + '/#/outside'); pg.wait_for_timeout(1500)
            over = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            check(over <= 2, f'{size} {theme}: no sideways scrolling ({over}px)')
            pg.screenshot(path=f'{OUT}/outside-{size}-{theme}.png', full_page=True)
            if size == 'laptop' and theme == 'light':
                check(pg.locator('h1').inner_text() == 'Back outside', 'page opens')
                check(pg.locator('#bo-ready .bo-row').count() == 2 and pg.locator('#bo-wait .bo-row').count() == 1, 'groups: 2 ready, 1 not yet')
                check(pg.locator('.bo-sum').inner_text().startswith('5 of 7 plants inside can go back out now.'), 'summary counts ready and safe')
                check(pg.locator('#bo-wait :is([data-act=boporch],[data-act=boout])').count() == 0, 'no move buttons for a plant that must wait')
                check('nights stayed above 49°F from March' in pg.locator('.bo-row[data-code="P-005"]').inner_text(), 'the early plant says when nights usually warm up')
                # Today page note
                pg.goto(BASE + '/#/today'); pg.wait_for_timeout(1500)
                check(pg.locator('#bo-today a[href="#/outside"]').count() == 1, 'Today page links to the list in spring')
                pg.locator('#bo-today').screenshot(path=f'{OUT}/outside-today-note.png')
                pg.goto(BASE + '/#/winter'); pg.wait_for_timeout(1500)
                check(pg.locator('a[href="#/outside"]').count() >= 1, 'Winter plan links to the list')
                pg.goto(BASE + '/#/outside'); pg.wait_for_timeout(1500)
                # move one to the porch with the keyboard
                btn = pg.locator('.bo-row[data-code="P-012"] [data-act=boporch]')
                btn.focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(1500)
                check(pg.locator('#bo-ready .bo-row[data-code="P-012"]').count() == 0, 'Moved to the porch: it leaves the Ready list')
                check(pg.locator('#bo-porchwait .bo-row[data-code="P-012"]').count() == 1, 'and shows under "On the porch for now"')
                check('sun scorch' in pg.locator('.bo-why').inner_text(), 'the page says the porch is to protect leaves from sun scorch')
                check('sun scorch' in pg.locator('#bo-ready .bo-row').first.inner_text(), 'each plant that can go says so too')
                rec = json.loads(S.sqlite3.connect(S.DB_PATH).execute("SELECT value FROM settings WHERE key='bo_porch'").fetchone()[0])
                check(rec['P-012']['on'] == TODAY.isoformat(), 'the day it went to the porch is kept')
                site = S.app.test_client().get('/api/plants/P-012').get_json().get('site')
                check(site == 'Covered porch', f'its Location is now Covered porch ({site})')
                foc = pg.evaluate('document.activeElement && document.activeElement.textContent')
                check(foc == 'Moved to the porch', f'focus moves to the next plant\'s button ("{foc}")')
                # a week later: the reminder
                cx = S.sqlite3.connect(S.DB_PATH); cx.execute("UPDATE settings SET value=? WHERE key='bo_porch'", (json.dumps({'P-012': {'on': (TODAY - timedelta(days=8)).isoformat(), 'by': 'x'}}),)); cx.commit(); cx.close()
                pg.reload(); pg.wait_for_timeout(2000)
                check(pg.locator('#bo-porchdue .bo-row[data-code="P-012"]').count() == 1, 'after 8 days it is listed as time to move it')
                pg.evaluate("document.getElementById('corner').style.display='none'"); pg.locator('#bo-porchdue').screenshot(path=f'{OUT}/outside-porch-due.png'); pg.locator('.bo-why').screenshot(path=f'{OUT}/outside-why.png')
                pg.goto(BASE + '/#/today'); pg.wait_for_timeout(1500)
                check('ready for its summer spot' in pg.locator('#bo-today').inner_text(), 'the Today page reminds too')
                pg.locator('#bo-today').screenshot(path=f'{OUT}/outside-today-porch.png')
                pg.goto(BASE + '/#/outside'); pg.wait_for_timeout(1500)
                pg.locator('#bo-porchdue [data-act=boleave]').click(); pg.wait_for_timeout(1500)
                check(pg.locator('#bo-porchdue').count() == 0, 'Leave it on the porch turns the reminder off')
                check(S.app.test_client().get('/api/plants/P-012').get_json().get('site') == 'Covered porch', 'and it stays on the porch')
                cx = S.sqlite3.connect(S.DB_PATH); cx.execute("UPDATE settings SET value=? WHERE key='bo_porch'", (json.dumps({'P-012': {'on': (TODAY - timedelta(days=8)).isoformat(), 'by': 'x'}}),)); cx.commit(); cx.close()
                pg.reload(); pg.wait_for_timeout(2000)
                pg.locator('#bo-porchdue [data-act=boout]').click(); pg.wait_for_timeout(1500)
                check(pg.locator('#bo-porchdue').count() == 0, 'Moved outside from the reminder clears it')
                check(S.app.test_client().get('/api/plants/P-012').get_json().get('site') == 'Outdoors', 'and sets Outdoors')
                pg.locator('.bo-row[data-code="P-013"] [data-act=boout]').click(); pg.wait_for_timeout(1500)
                site = S.app.test_client().get('/api/plants/P-013').get_json().get('site')
                check(site == 'Outdoors', f'Moved outside sets Outdoors ({site})')
            pg.close()
    b.close()
srv.shutdown()
check(not errs, 'no JavaScript errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('PASSED' if not fails else f'{len(fails)} FAILED')
sys.exit(1 if fails else 0)
