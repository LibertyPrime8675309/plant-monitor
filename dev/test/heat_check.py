"""Checks the prototype proto/summer-heat: summer heat (AHS heat zones) under "About this plant".
The server part runs in this process on its own data folder (dev/tmp/heat-check-data). The browser part needs the mock server
running on a fresh data folder; this script first writes ten years of made-up summer highs into that folder's database:
  DATA_DIR=dev/tmp/heat-data python3 dev/test/mock_server.py      (in one window)
  SERVER_DATA=dev/tmp/heat-data python3 dev/test/heat_check.py     (in another)
Screenshots: dev/tmp/shots/heat-*.png"""
import json, math, os, shutil, sqlite3, sys
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
BASE = 'http://127.0.0.1:8080'
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)

TODAY = date(2026, 10, 31)
def high(d):
    """A made-up Round Rock-like daily high: about 60°F in January, about 98°F in late July, a few days above 105°F."""
    doy = d.timetuple().tm_yday
    return round(79 - 19 * math.cos((doy - 20) / 365 * 2 * math.pi) + 6 * math.sin(doy * 1.7) + (d.year % 4 - 1.5), 1)
def fill(db_path, start=date(2016, 1, 1), end=TODAY):
    c = sqlite3.connect(db_path)
    home = c.execute('SELECT id FROM locations WHERE is_home=1').fetchone()[0]
    d = start
    while d <= end:
        c.execute("INSERT OR REPLACE INTO weather_daily(loc_id,date,data,kind,updated_at) VALUES(?,?,?,'observed','x')",
                  (home, d.isoformat(), json.dumps({'temperature_2m_max': high(d), 'temperature_2m_min': high(d) - 22})))
        d += timedelta(days=1)
    c.commit(); c.close()

# ---- the server part
data = os.path.join(HERE, '..', 'tmp', 'heat-check-data'); shutil.rmtree(data, ignore_errors=True); os.makedirs(data)
os.environ['DATA_DIR'] = data
sys.path.insert(0, os.path.join(HERE, '..', '..', 'app'))
import server as S
S.init_db()
S.local_today = lambda c: TODAY
check([S.ahs_heat_zone(x) for x in (0, 0.9, 1, 7, 8, 30, 31, 60, 61, 90, 91, 150, 151, 180, 181, 210, 211, 300)] == [1, 1, 2, 2, 3, 4, 5, 6, 7, 7, 8, 9, 10, 10, 11, 11, 12, 12],
      'AHS heat zones: <1 day is 1, 1-7 is 2, 8-14 is 3, 15-30 is 4, ... 151-180 is 10, 181-210 is 11, over 210 is 12')
t = S.app.test_client()
h = {'X-Editor': 'Heat Test'}
r = t.get('/api/heat?above=100', headers=h).get_json()
check(r['zone'] is None and r['years'] == 0 and r['per_year'] == [], 'no weather history: no zone, no years')
fill(os.path.join(data, 'plants.db'), date(2024, 3, 1))
S.PLACE_HEAT.clear()
r = t.get('/api/heat?above=100', headers=h).get_json()
check(r['zone'] is None and r['years'] == 1 and [y['year'] for y in r['per_year']] == [2026, 2025], f'under 3 whole years: no zone yet, rows for 2025 and this year so far ({r["years"]}, {[y["year"] for y in r["per_year"]]})')
check(r['per_year'][0]['partial'] and not r['per_year'][1]['partial'], 'this year is marked "so far"; 2024 (from March) is left out')
fill(os.path.join(data, 'plants.db'))
S.PLACE_HEAT.clear()
r = t.get('/api/heat?above=100', headers=h).get_json()
yrs = range(2016, 2026)
over = [sum(1 for i in range((date(y + 1, 1, 1) - date(y, 1, 1)).days) if high(date(y, 1, 1) + timedelta(days=i)) > 86) for y in yrs]
avg = sum(over) / len(over)
check(r['years'] == 10 and r['over86'] == round(avg) and r['zone'] == S.ahs_heat_zone(avg), f'10 whole years, {round(avg)} days above 86°F a year, zone {r["zone"]}')
check(len(r['per_year']) == 11 and r['per_year'][0]['year'] == 2026 and r['per_year'][0]['partial'], 'the table has this year so far and the last 10 whole years')
reach = sum(1 for y in yrs for i in range(366) if date(y, 1, 1) + timedelta(days=i) < date(y + 1, 1, 1) and high(date(y, 1, 1) + timedelta(days=i)) >= 100) / 10
check(abs(r['reach'] - round(reach, 1)) < 0.01 and r['months'] and all(m['month'] in ('May', 'Jun', 'Jul', 'Aug', 'Sep') for m in r['months']), f'days at 100°F or more: {r["reach"]} a year, in {[m["month"] for m in r["months"]]}')
r2 = t.get('/api/heat', headers=h).get_json()
check('reach' not in r2 and r2['above'] is None and r2['zone'] == r['zone'], 'without a plant temperature: just the place')
check(t.get('/api/heat?above=hot', headers=h).status_code == 400 and t.get('/api/heat?above=20', headers=h).status_code == 400, 'a wrong temperature is refused')
check(t.get('/api/heat?above=200', headers=h).status_code == 400, 'a temperature over 140°F is refused')

# ---- the browser part
srv = os.environ.get('SERVER_DATA', os.path.join(HERE, '..', 'tmp', 'heat-data'))
fill(os.path.join(srv, 'plants.db'))
with sync_playwright() as p:
    b = p.chromium.launch()
    for name, w, hgt, prefs in (('laptop', 1280, 900, {'theme': 'light'}), ('phone-dark', 390, 844, {'theme': 'dark'}), ('phone-bigtext', 390, 844, {'theme': 'light', 'size': '190'}),
                                ('contrast', 1280, 900, {'theme': 'light', 'contrast': 'high'})):
        pg = b.new_page(viewport={'width': w, 'height': hgt})
        pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.on('console', lambda m: m.type == 'error' and 'Failed to load resource' not in m.text and errs.append(m.text))   # plant photos come in photo packs, not in git
        pg.add_init_script("localStorage.setItem('plantdb.editor','Heat Test');localStorage.setItem('plantdb.display',JSON.stringify(%s))" % json.dumps(prefs))
        for code in ('P-012', 'P-009', 'P-002'):
            pg.goto(BASE + '/#/plant/' + code); pg.wait_for_selector('#heat-box h3', timeout=15000); pg.wait_for_timeout(400)
            box = pg.locator('#heat-box')
            txt = box.inner_text()
            if name == 'laptop':
                check('heat zone' in txt and 'American Horticultural Society' in txt, f'{code}: says the heat zone in words')
                prev = pg.evaluate("(() => { const b = document.getElementById('heat-box'); let e = b.previousElementSibling; while (e && e.tagName !== 'H3') e = e.previousElementSibling; return e ? e.textContent : ''; })()")
                nxt = pg.evaluate("(() => { const n = document.getElementById('heat-box').nextElementSibling; return n ? n.textContent.slice(0, 30) : ''; })()")
                check(prev.startswith('Hardiness zones'), f'{code}: comes right after the hardiness zones (then "{nxt}")')
                check(box.locator('table[aria-labelledby=heat-cap]').count() == 1 and box.locator('th[scope=col]').count() == 4, f'{code}: a table with a heading and four column headings')
                if code == 'P-012': check('■ Summer heat is hard on it here' in txt and '90°F' in txt, 'Aeonium (heat damage at 90°F): "Summer heat is hard on it here"')
                if code == 'P-009': check('100°F' in txt and ('▲' in txt or '■' in txt), 'Philodendron Birkin (100°F): warned, with the temperature')
                if code == 'P-002': check('✓ Summer heat is fine for it here' in txt, 'Boobie cactus (115°F): "Summer heat is fine for it here"')
                check('(so far)' in txt, f'{code}: this year is marked "so far"')
            over = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            check(over <= 2, f'{name} {code}: no sideways scrolling ({over}px)')
            if code == 'P-012':
                box.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
                pg.evaluate("document.getElementById('heat-box').scrollIntoView({block: 'start'})"); pg.wait_for_timeout(300)
                pg.screenshot(path=os.path.join(OUT, f'heat-{name}.png'))
                if w < 600: box.screenshot(path=os.path.join(OUT, f'heat-{name}-whole.png'))       # the whole box (phones scroll the page, not a pane)
                wide = pg.evaluate("(() => { const w = document.querySelector('#heat-box .tbl-wrap'); return w.scrollWidth - w.clientWidth; })()")
                check(wide <= 2, f'{name}: the table fits without scrolling sideways ({wide}px)')
        if name == 'laptop':        # swiping to the next plant redraws the box for that plant
            pg.goto(BASE + '/#/plant/P-012'); pg.wait_for_selector('#heat-box h3')
            pg.goto(BASE + '/#/plant/P-002'); pg.wait_for_selector('#heat-box h3'); pg.wait_for_timeout(400)
            check(pg.locator('#heat-box').count() == 1 and 'fine for it' in pg.locator('#heat-box').inner_text(), 'moving to another plant shows that plant\'s verdict, once')
        pg.close()
    b.close()
check(not errs, f'no JavaScript errors ({errs[:3]})')
print('\n' + ('All checks passed.' if not fails else f'{len(fails)} failed.'))
sys.exit(1 if fails else 0)
