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
check([S.heat_level(x) for x in (None, 0, 0.4, 0.5, 9.9, 10, 40)] == [None, 'fine', 'fine', 'few', 'few', 'hard', 'hard'], 'verdicts: under half a day is fine, under 10 days is a few, 10 or more is hard')
check([S.heat_zone_fit(9, 12, 7), S.heat_zone_fit(9, 8, 1), S.heat_zone_fit(9, 12, 10), S.heat_zone_fit(9, 1, 9), S.heat_zone_fit(None, 9, 1), S.heat_zone_fit(9, None, 1)] == ['within', 'hotter', 'cooler', 'within', None, None],
      'heat zone ranges: within, hotter than, cooler than (either order)')

# ---- batch B3: AHS heat zone ranges with their sources, only where a page printed one
db = sqlite3.connect(os.path.join(data, 'plants.db')); db.row_factory = sqlite3.Row
got = {r['code']: r for r in db.execute('SELECT code, heat_zone_high, heat_zone_low, heat_zone_source FROM plants WHERE heat_zone_high IS NOT NULL')}
check(len(got) == 18 and all(r['heat_zone_high'] >= r['heat_zone_low'] and 1 <= r['heat_zone_low'] <= 12 for r in got.values()), f'batch B3 fills 18 plants with ranges from 1 to 12, hottest first ({len(got)})')
check(all(' | https://' in r['heat_zone_source'] for r in got.values()), 'every range has its source link')
check((got['P-012']['heat_zone_high'], got['P-012']['heat_zone_low']) == (9, 4) and 'P-009' not in got and 'P-008' not in got, 'Aeonium is 9 to 4; Philodendron and Bougainvillea (no trustworthy range) are left empty')
db.execute("UPDATE plants SET heat_zone_high=11 WHERE code='P-013'"); db.execute("DELETE FROM settings WHERE key='batch_applied:batchB3'"); db.commit()
S.apply_batches(db); db.commit()
check(db.execute("SELECT heat_zone_high FROM plants WHERE code='P-013'").fetchone()[0] == 11, 'running the batch again leaves a range you changed yourself alone')
db.execute("UPDATE plants SET heat_zone_high=8 WHERE code='P-069'"); db.commit(); db.close()

# ---- every plant's verdict (the Summer here filter and the Weather page)
P = t.get('/api/heat/plants', headers=h).get_json()
pl = P['plants']
check(P['zone'] == r['zone'] and len(pl) >= 85, f'every active plant has a verdict ({len(pl)})')
check(pl['P-012']['level'] == 'hard' and pl['P-044']['level'] == 'fine' and pl['P-009']['level'] in ('few', 'hard'), 'Aeonium hard, Boobie cactus fine, Philodendron Birkin warned')
check(pl['P-012']['fit'] == 'within' and pl['P-069']['fit'] == 'hotter' and pl['P-009']['fit'] is None, 'Aeonium within its heat zones, white sage (now 8 to 1) hotter, Philodendron no range')

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
        for code in ('P-012', 'P-009', 'P-044'):
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
                if code == 'P-044': check('✓ Summer heat is fine for it here' in txt, 'Boobie cactus (115°F): "Summer heat is fine for it here"')
                check('(so far)' in txt, f'{code}: this year is marked "so far"')
            over = pg.evaluate("(() => { const W = document.documentElement.clientWidth; return Math.max(0, ...[...document.querySelectorAll('#heat-box, #heat-box *')].map(e => Math.round(e.getBoundingClientRect().right - W))); })()")
            check(over <= 1, f'{name} {code}: Summer heat fits the screen width ({over}px over)')   # the whole page is checked by smoke.py
            if code == 'P-012':
                box.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
                pg.evaluate("document.getElementById('heat-box').scrollIntoView({block: 'start'})"); pg.wait_for_timeout(300)
                pg.screenshot(path=os.path.join(OUT, f'heat-{name}.png'))
                if w < 600: box.screenshot(path=os.path.join(OUT, f'heat-{name}-whole.png'))       # the whole box (phones scroll the page, not a pane)
                wide = pg.evaluate("(() => { const w = document.querySelector('#heat-box .tbl-wrap'); return w.scrollWidth - w.clientWidth; })()")
                check(wide <= 2, f'{name}: the table fits without scrolling sideways ({wide}px)')
        if name == 'laptop':        # the plant's own AHS range against the zone here
            pg.goto(BASE + '/#/plant/P-012'); pg.wait_for_selector('#heat-box h3'); pg.wait_for_timeout(400)
            txt = pg.locator('#heat-box').inner_text()
            check('within its heat zones' in txt and 'AHS heat zones 9 to 4' in txt and pg.locator('#heat-box a[href*="gardenia.net"]').count() == 1, 'Aeonium: "within its heat zones", 9 to 4, with the source link')
            pg.goto(BASE + '/#/plant/P-069'); pg.wait_for_selector('#heat-box h3'); pg.wait_for_timeout(400)
            check('hotter than its heat zones' in pg.locator('#heat-box').inner_text(), 'White sage at 8 to 1: "hotter than its heat zones"')
            pg.goto(BASE + '/#/plant/P-009'); pg.wait_for_selector('#heat-box h3'); pg.wait_for_timeout(400)
            check('No published AHS heat zone range' in pg.locator('#heat-box').inner_text(), 'Philodendron: says there is no published range yet')
            pg.goto(BASE + '/#/plant/P-012/edit'); pg.wait_for_timeout(1500)
            check(all(pg.get_by_label(l, exact=False).count() >= 1 for l in ('Heat zone, hottest (AHS)', 'Heat zone, coolest (AHS)', 'Heat zone source')), 'the edit form has the three heat zone fields, with labels')
        if name in ('laptop', 'phone-dark', 'phone-bigtext'):     # the Weather page and the Summer here filter
            pg.goto(BASE + '/#/weather'); pg.wait_for_selector('#wx-heat .heat-counts a', timeout=20000); pg.wait_for_timeout(500)
            sec = pg.locator('#wx-heat')
            st = sec.inner_text()
            if name == 'laptop':
                check('heat zone' in st and pg.locator('#wx-heat ~ #wx-logged, #wx-heat + #wx-logged').count() >= 1, 'Weather page: Summer heat comes before All logged weather data')
                check(sec.locator('a[data-heatf=hard]').count() == 1 and sec.locator('a[data-heatf=hotter]').count() == 1, 'Weather page: links for "hard on them" and "hotter than their heat zones"')
            over = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            check(over <= 2, f'{name} Weather page: no sideways scrolling ({over}px)')
            sec.scroll_into_view_if_needed(); pg.evaluate("document.getElementById('wx-heat').scrollIntoView({block: 'start'})"); pg.wait_for_timeout(300)
            pg.screenshot(path=os.path.join(OUT, f'heat-weather-{name}.png'))
            if w < 600: sec.screenshot(path=os.path.join(OUT, f'heat-weather-{name}-whole.png'))
            if name == 'laptop':
                n_hard = int(sec.locator('a[data-heatf=hard]').inner_text().split()[0])
                sec.locator('a[data-heatf=hard]').click(); pg.wait_for_timeout(2500)
                cards = pg.evaluate("[...document.querySelectorAll('#app a[href^=\"#/plant/\"]')].map(a => a.getAttribute('href').split('/')[2]).filter((v, i, a) => a.indexOf(v) === i)")
                check('P-012' in cards and 'P-044' not in cards, f'the link opens the Plants page filtered to plants summer is hard on ({len(cards)} shown, {n_hard} counted)')
                sel = pg.locator('select[data-key=heat]')
                check(sel.count() == 0 or sel.input_value() == 'hard', 'the "Summer here" filter shows the choice')
                pg.evaluate("localStorage.removeItem('plantdb.filters')")
        if name == 'laptop':        # swiping to the next plant redraws the box for that plant
            pg.goto(BASE + '/#/plant/P-012'); pg.wait_for_selector('#heat-box h3')
            pg.goto(BASE + '/#/plant/P-044'); pg.wait_for_selector('#heat-box h3'); pg.wait_for_timeout(400)
            check(pg.locator('#heat-box').count() == 1 and 'fine for it' in pg.locator('#heat-box').inner_text(), 'moving to another plant shows that plant\'s verdict, once')
        pg.close()
    b.close()
check(not errs, f'no JavaScript errors ({errs[:3]})')
print('\n' + ('All checks passed.' if not fails else f'{len(fails)} failed.'))
sys.exit(1 if fails else 0)
