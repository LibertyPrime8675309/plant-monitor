"""Checks the prototype "Frost dates" (proto/frost-dates): the usual first and last freeze, hard freeze and 36°F night from the
weather history on the Weather page; when each damage temperature of the plants outside is usually first reached on the Cold-night
checklist, one plant a line with its photo; the usual last dates on Back outside; the line on Today; not enough history says so;
nothing is changed. At laptop and phone width, light and dark, with the largest text.
Start the mock server with a fresh data folder, then:  python3 dev/test/frostdates_check.py      Screenshots: dev/tmp/shots/frostdates-*.png"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
BASE = 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Frost Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
D0 = call('GET', '/api/frost/dates')
check(not D0['ready'] and 'freeze' not in D0, f"without 3 whole winters of history there are no dates yet ({D0['winters']} so far)")
audit0 = len(call('GET', '/api/audit?n=500'))
call('POST', '/mock/history', {'years': 5})
call('POST', '/api/weather/refresh'); import time; time.sleep(5)       # this winter so far comes from the hourly update's past days
D = call('GET', '/api/frost/dates')
check(D['now']['nights'] > 0 and D['now']['coldest'] is not None, f"this winter so far: {D['now']['nights']} nights, coldest {D['now']['coldest']}")
check(D['ready'] and D['winters'] == 4, 'with 5 years of history, 4 whole winters (July to June) count')
F = D['freeze']
check(F['first']['usual'].startswith('Nov') and F['last']['usual'].startswith('Mar'), f"usual first freeze {F['first']['usual']}, last {F['last']['usual']}")
check(D['hard']['first']['usual_day'] >= F['first']['usual_day'] and D['hard']['last']['usual_day'] <= F['last']['usual_day'], 'a hard freeze starts later and ends sooner than a freeze')
check(len({w['last'][5:] for w in D['per_winter']}) <= 2, 'the same weather each year gives the same last-freeze day give or take a leap day')
check(D['frost_free_days'] and 200 < D['frost_free_days'] < 300, f"frost-free days between: {D['frost_free_days']}")
plants = {p['code']: p for p in call('GET', '/api/plants')}
outside = {c for c, p in plants.items() if not p.get('home_id') and p.get('temp_damage_below') is not None and (p.get('site') or 'Outdoors') not in ('Indoors', 'Garage or shed')}
listed = {p['code'] for g in D['plants'] for p in g['plants']}
check(listed == outside, f'every plant outside with a damage temperature is listed once ({len(listed)})')
days = [g['first']['usual_day'] for g in D['plants'] if g['first'] and not g['most_none']]
check(days == sorted(days), 'the groups are in date order, earliest first')
check(all(g['below'] >= 32 or g['first'] is None or g['first']['usual_day'] >= F['first']['usual_day'] for g in D['plants']), 'plants damaged below 32°F or less are reached no sooner than the freeze')
check(len(call('GET', '/api/audit?n=500')) == audit0, 'nothing was written to the audit log (read only)')
# Ethan's answers of November 6
P = D['possible']
check(P['first']['usual_day'] <= F['first']['usual_day'] and P['last']['usual_day'] >= F['last']['usual_day'], f"frost possible (36°F) from {P['first']['usual']} to {P['last']['usual']}, around the freeze")
check(all('first_possible' in w for w in D['per_winter']) and 'first_possible' in D['now'], 'each winter and this winter so far have their first 36°F night')
check(set(D['days_to_last']) == {'freeze', 'hard', 'possible'} and D['days_to_usual'] is not None, f"days to the usual dates: first freeze {D['days_to_usual']}, last {D['days_to_last']}")
with_photo = sum(1 for g in D['plants'] for p in g['plants'] if p['photo'])
check(with_photo > 0, f'the plants come with their photos ({with_photo} of {len(listed)})')
N = D['now']
today_due = (D['month'] in (10, 11) and not N['first_freeze']) or (D['month'] in (2, 3) and D['days_to_last']['freeze'] >= -21)

with sync_playwright() as p:
    b = p.chromium.launch()
    for name, (w, h, prefs) in {'laptop-light': (1280, 900, {'theme': 'light'}), 'phone-dark': (390, 844, {'theme': 'dark'}),
                                'phone-bigtext': (390, 844, {'theme': 'light', 'size': '190'})}.items():
        pg = b.new_page(viewport={'width': w, 'height': h})
        pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
        pg.add_init_script("localStorage.setItem('plantdb.editor','Frost Test');localStorage.setItem('plantdb.display',JSON.stringify(%s))" % json.dumps(prefs))
        pg.goto(BASE + '/#/weather?sec=wx-frostdates'); pg.wait_for_selector('.fd-box[data-fd-done] .fd-dl', timeout=20000); pg.wait_for_timeout(800)
        box = pg.locator('#wx-frostdates')
        check(box.locator('dt', has_text='Usual first freeze').count() == 1 and F['first']['usual'] in box.inner_text(), f'{name}: the Weather page shows the usual first freeze')
        check(box.locator('h3', has_text='Frost possible: 36°F').count() == 1 and box.locator('dt', has_text='Usual first night of 36°F or colder').count() == 1, f'{name}: and the usual first night of 36°F or colder (frost possible)')
        check(box.locator('.fd-now').count() == 1, f'{name}: a line about this winter so far')
        check(box.locator('table.fd-tbl tbody tr').count() == len(D['per_winter']), f'{name}: one row per winter')
        if w < 500: check(pg.locator('table.fd-tbl.stacked').count() == 1, f'{name}: the table stacks into boxes on a phone')
        check(pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth') <= 2, f'{name}: no sideways scrolling on the Weather page')
        if name == 'laptop-light': check(pg.locator('#sidenav a', has_text='Frost dates').count() >= 1, 'the Navigation menu lists Frost dates')
        box.screenshot(path=os.path.join(OUT, f'frostdates-weather-{name}.png'))
        pg.locator('#wx-frostdates a[href^="#/frost"]').click(); pg.wait_for_selector('.fd-box[data-fd-done] .fd-groups', timeout=20000); pg.wait_for_timeout(800)
        sec = pg.locator('#fz-dates')
        check(sec.locator('li.fd-g').count() == len(D['plants']), f'{name}: the checklist groups the plants outside by damage temperature')
        if any(g['this_winter'] for g in D['plants']): check('Already this winter' in sec.inner_text(), f'{name}: a damaging night that already came this winter is named')
        check(sec.locator('a[href^="#/plant/"]').count() == len(listed), f'{name}: each plant is a link to its page')
        check(sec.locator('li.fd-p').count() == len(listed) and sec.locator('table').count() == 0, f'{name}: one plant a line, in a list (not a table)')
        check(sec.locator('li.fd-p img').count() == with_photo and sec.locator('li.fd-p img:not([alt=""])').count() == 0, f'{name}: each plant with a photo shows it, with an empty alt (the name is beside it)')
        big = [g for g in D['plants'] if len(g['plants']) > 6]
        check(sec.locator('details.fd-more').count() == len(big), f'{name}: long groups show 5 plants and fold the rest ({len(big)} folded)')
        if big:
            more = sec.locator('details.fd-more').first
            more.locator('summary').focus(); pg.keyboard.press('Enter'); pg.wait_for_timeout(200)
            check(more.evaluate('d => d.open') and more.locator('li.fd-p').first.is_visible(), f'{name}: the fold opens from the keyboard')
        check(pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth') <= 2, f'{name}: no sideways scrolling on the checklist')
        sec.screenshot(path=os.path.join(OUT, f'frostdates-frost-{name}.png'))
        pg.goto(BASE + '/#/outside?sec=bo-frostdates'); pg.wait_for_selector('.fd-box[data-fd="outside"][data-fd-done] .fd-dl', timeout=20000); pg.wait_for_timeout(800)
        bo = pg.locator('#bo-frostdates')
        check(bo.locator('dt', has_text='Usual last freeze (32°F)').count() == 1 and F['last']['usual'] in bo.inner_text() and P['last']['usual'] in bo.inner_text(),
              f'{name}: Back outside shows the usual last freeze, hard freeze and 36°F night')
        check(pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth') <= 2, f'{name}: no sideways scrolling on Back outside')
        bo.screenshot(path=os.path.join(OUT, f'frostdates-outside-{name}.png'))
        pg.goto(BASE + '/#/today'); pg.wait_for_selector('.td-jumps', timeout=20000); pg.wait_for_timeout(2500)
        line = pg.locator('.fd-today')
        check(line.count() == (1 if today_due else 0), f'{name}: Today ' + ('has the frost-dates line' if today_due else 'has no frost-dates line this month'))
        if today_due and D['month'] in (10, 11):
            check('No freeze yet' in line.inner_text() and line.locator('a[href^="#/weather"]').count() == 1, f'{name}: it says no freeze yet, with days to the usual first freeze')
        check(pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth') <= 2, f'{name}: no sideways scrolling on Today')
        pg.screenshot(path=os.path.join(OUT, f'frostdates-today-{name}.png'))
        pg.close()
    b.close()
for e in errs: check(False, 'page error: ' + e)
print('frost dates check: ' + ('passed' if not fails else f'{len(fails)} failed'))
sys.exit(1 if fails else 0)
