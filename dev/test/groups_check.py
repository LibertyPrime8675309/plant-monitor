"""Checks 1.16.0: groups of plants. Smart groups (a rule) and hand-picked groups, the suggestions, filtering and sorting the
Plants page by group, a plant's own groups, what suits every plant in a group, and changes to a whole group: care, moving,
a grow light spot, and a setting with a preview and undo. Also that people who can only view change nothing.
Start the mock server with a fresh data folder (MOCK_TS=1), then:  python3 dev/test/groups_check.py [base] [tailscale-base]
Screenshots: dev/tmp/shots/groups-*.png"""
import json, os, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
LOCAL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = sys.argv[2] if len(sys.argv) > 2 else 'http://127.0.0.1:8081'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, base=None, h=None):
    hd = {'Content-Type': 'application/json', 'X-Editor': 'Group Test', **(h or {})}
    req = urllib.request.Request((base or LOCAL) + url, data=json.dumps(body).encode() if body is not None else None, headers=hd, method=m)
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'null')
    except urllib.error.HTTPError as e:
        t = e.read().decode()
        try: t = json.loads(t).get('error', t)
        except ValueError: pass
        return e.code, t
plant = lambda code: call('GET', '/api/plants/' + code)[1]
def edit(code, **fields):
    return call('PUT', '/api/plants/' + code, {'base_version': plant(code)['version'], 'fields': fields})

# ---- suggestions and smart groups
st, j = call('GET', '/api/groups')
sug = {x['name']: x for x in j['suggestions']}
check(st == 200 and not j['groups'], 'a new install has no groups yet')
check('Aroids' in sug and sug['Aroids']['count'] >= 15 and 'Philodendrons' in sug and sug['Philodendrons']['count'] >= 11 and 'Roses' in sug and 'Majesty palms' in sug,
      f"suggestions use friendly names: Aroids ({sug.get('Aroids', {}).get('count')}), Philodendrons, Roses, Majesty palms")
N = sug.get('Philodendrons', {}).get('count', 11)          # 11 in the seed; batch B8 adds 'Ring of Fire'
check('Daisy family' not in sug and 'Mint family' not in sug and 'Rosa plants' not in sug, 'no suggestions for families whose plants need different care, and no Latin-only names')
st, ph = call('POST', '/api/groups', {'name': 'Philodendrons', 'kind': 'smart', 'rule': sug['Philodendrons']['rule']})
check(st == 201 and ph['count'] == N and 'P-029' in ph['codes'], f'a smart group from a suggestion takes in its {N} plants ({st})')
check(call('POST', '/api/groups', {'name': 'philodendrons', 'kind': 'picked'})[0] == 409, 'two groups cannot have the same name')
st, e = call('POST', '/api/groups', {'name': 'Bad', 'kind': 'smart', 'rule': {'conds': [{'field': 'genus', 'op': 'is', 'value': ''}]}})
check(st == 400 and 'Genus' in e, f'a rule with an empty value is refused in plain words ({e})')
st, m = call('POST', '/api/groups/match', {'rule': {'match': 'any', 'conds': [{'field': 'site', 'op': 'is', 'value': 'Covered porch'}, {'field': 'name', 'op': 'contains', 'value': 'palm'}]}})
check(st == 200 and len(m['codes']) > 20 and 'P-017' in m['codes'] and 'or' in m['words'], f"a rule with \"any part fits\" joins both kinds of plant ({len(m['codes'])})")

# ---- hand-picked groups and a plant's own groups
st, sh = call('POST', '/api/groups', {'name': 'Tall Black Shelf', 'kind': 'picked', 'codes': ['P-001', 'P-011', 'P-037']})
check(st == 201 and sh['codes'] == ['P-001', 'P-011', 'P-037'], 'a hand-picked group holds the plants chosen')
st, r = call('POST', f"/api/groups/{sh['id']}/members", {'add': ['P-038'], 'remove': ['P-011']})
check(st == 200 and r['added'] == ['P-038'] and r['removed'] == ['P-011'] and r['group']['count'] == 3, 'plants can be added to it and taken out')
check(call('POST', f"/api/groups/{ph['id']}/members", {'add': ['P-001']})[0] == 400, 'plants cannot be added by hand to a smart group')
st, gs = call('POST', '/api/plants/P-029/groups', {'picked': [sh['id']]})
check(st == 200 and {g['name'] for g in gs} == {'Philodendrons', 'Tall Black Shelf'}, f"a plant's page sets its hand-picked groups and lists its smart ones ({[g['name'] for g in gs]})")
call('POST', '/api/plants/P-038/status', {'archived': True})
check('P-038' not in call('GET', f"/api/groups/{sh['id']}")[1]['codes'], 'an archived plant is not shown in its group')
call('POST', '/api/plants/P-038/status', {'archived': False})

# ---- what suits all of them
st, d = call('GET', f"/api/groups/{ph['id']}")
fit = {x['key']: x for x in d['fit']}
check(st == 200 and len(d['members']) == N and fit['temp']['lo'] <= fit['temp']['hi'] and fit['temp']['n'] == N, f"the group page has its plants and a temperature range for all {N} ({fit['temp']['lo']} to {fit['temp']['hi']})")
check('cold' in fit and fit['cold']['by'] and 'soil' in fit, 'it says how warm to keep them because of which plants, and compares potting mixes')

# ---- a setting for the whole group: preview, apply, a change in between is skipped, undo
st, pv = call('POST', f"/api/groups/{ph['id']}/preview", {'set': {'soil_medium': 'Chunky aroid mix: bark, perlite and coco coir'}})
check(st == 200 and len(pv['rows']) == N and all(not x['same'] for x in pv['rows']), 'the preview shows every plant with what it has now')
edit('P-030', soil_medium='Changed by someone else')
p30 = plant('P-030')
codes = [x['code'] for x in pv['rows']]
st, a = call('POST', f"/api/groups/{ph['id']}/apply", {'set': pv['set'], 'codes': codes, 'expect': {x['code']: x['current'] for x in pv['rows']}})
check(st == 200 and len(a['changed']) == N - 1 and a['skipped'] == ['P-030'] and a['bulk_id'], f"{N - 1} plants change; the one edited since the preview is skipped ({a.get('skipped') if isinstance(a, dict) else a})")
check(plant('P-029')['soil_medium'].startswith('Chunky aroid mix: bark') and plant('P-030')['soil_medium'] == p30['soil_medium'], 'the new mix is on the plant pages, and the skipped plant keeps its own')
check(call('POST', f"/api/groups/{ph['id']}/apply", {'set': {'common_name': 'X'}, 'codes': codes})[0] == 400, 'names and other facts cannot be changed for a whole group')
check(call('POST', f"/api/groups/{ph['id']}/apply", {'set': {'site': 'Indoors'}, 'codes': ['P-001']})[0] == 400, 'only plants in the group can be changed through it')
edit('P-009', soil_medium='Edited again after the group change')
st, u = call('POST', f"/api/bulk/{a['bulk_id']}/undo")
check(st == 200 and len(u['undone']) == N - 2 and u['kept'] == ['P-009'], f"undo puts {N - 2} back and leaves the plant edited again since ({u})")
check(not plant('P-029')['soil_medium'].startswith('Chunky aroid mix: bark') and plant('P-009')['soil_medium'] == 'Edited again after the group change', 'the plant pages show it')
check(call('POST', f"/api/bulk/{a['bulk_id']}/undo")[0] == 409, 'a change cannot be undone twice')

# ---- moving, a grow light spot, care for all
st, a2 = call('POST', f"/api/groups/{sh['id']}/apply", {'set': {'site': 'Indoors', 'location': 'Tall Black Shelf'}, 'codes': ['P-001', 'P-037']})
check(st == 200 and plant('P-001')['site'] == 'Indoors' and plant('P-037')['location'] == 'Tall Black Shelf', 'moving a group sets Location and Spot')
L = {x['key']: x for x in call('GET', '/api/lights')[1]['lights']}
st, sp = call('POST', '/api/lights/spots', {'name': 'Shelf light', 'light': L['sansi-tripod']['id'], 'distance': 20, 'hours': 12, 'plants': []})
st, r = call('POST', f"/api/groups/{sh['id']}/spot", {'spot': sp['id'], 'codes': ['P-001', 'P-037']})
asg = call('GET', '/api/lights')[1]['assigned']
check(st == 200 and asg.get('P-001') == sp['id'] and asg.get('P-037') == sp['id'], 'the group can be put under a grow light spot')
call('POST', f"/api/groups/{sh['id']}/spot", {'spot': None, 'codes': ['P-001']})
check('P-001' not in call('GET', '/api/lights')[1]['assigned'], 'and taken out of it')
st, cr = call('POST', '/api/care', {'plants': ['P-001', 'P-037', 'P-029'], 'kind': 'water'})
check(st in (200, 201), 'care is logged for several plants at once')
st, au = call('GET', '/api/audit?kind=groups&n=100')
rows = au.get('rows', au.get('entries', [])) if isinstance(au, dict) else au
check(st == 200 and len(rows) >= 6, f'group changes are in the audit log under their own kind ({len(rows)})')

# ---- people who can only view
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', base=TS, h=E); call('GET', '/api/me', base=TS, h=V)
check(call('GET', '/api/groups', base=TS, h=V)[0] == 200, 'a viewer can see the groups')
check(call('POST', '/api/groups', {'name': 'X', 'kind': 'picked'}, base=TS, h=V)[0] == 403 and call('POST', f"/api/groups/{ph['id']}/apply", {'set': {'site': 'Indoors'}, 'codes': ['P-029']}, base=TS, h=V)[0] == 403,
      'but cannot make groups or change plants through them')

# ---- the pages
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and '404' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Group Test');localStorage.setItem('plantdb.morefilters','1')")
    pg.goto(LOCAL + '/#/groups'); pg.wait_for_timeout(2500)
    check(pg.locator('#sub-nav a[data-nav=groups][aria-current=page]').count() == 1, 'Groups is in the top menu')
    check(pg.locator('#grp-yours .grp-card').count() == 2 and pg.locator('#grp-suggest .grp-card').count() >= 10, 'the Groups page lists your groups and the suggestions')
    pg.screenshot(path=os.path.join(OUT, 'groups-1-page.png'))
    pg.locator('#grp-suggest .grp-card', has=pg.locator('h3', has_text='Majesty palms')).locator('[data-act=grpaddsug]').click(); pg.wait_for_timeout(1500)
    check('Majesty palms' in pg.inner_text('#grp-yours'), 'Add this group makes the suggested group')
    pg.goto(LOCAL + f"/#/group/{ph['id']}"); pg.wait_for_timeout(2000)
    check(pg.locator('#g-plants li.job').count() == N and pg.locator('#g-fit .fit-item').count() >= 6, 'a group page lists its plants and what suits them')
    check(pg.locator('#g-recent [data-act=grpundo]').count() == 0 and 'Undone by' in pg.inner_text('#g-recent'), 'recent changes show the undone one')
    pg.click('[data-act=grpset]'); pg.wait_for_timeout(500)
    pg.select_option('dialog select[name=field]', 'water_every_days'); pg.wait_for_timeout(300)
    pg.fill('dialog input[name=water_every_days]', '6'); pg.click('dialog button[value=ok]'); pg.wait_for_timeout(1200)
    check(pg.locator('dialog .gset-tbl tbody tr').count() == N and pg.locator('dialog .gset-tbl input:checked').count() >= 1, 'the setting window shows each plant before anything changes')
    pg.screenshot(path=os.path.join(OUT, 'groups-2-preview.png'))
    pg.locator('dialog .gset-tbl input[type=checkbox]').first.uncheck()
    pg.click('dialog button[value=ok]'); pg.wait_for_timeout(2000)
    check(plant('P-009')['water_every_days'] != 6 and plant('P-029')['water_every_days'] == 6, 'only the ticked plants changed')
    check(pg.locator('#g-recent [data-act=grpundo]').count() == 1, 'and the change can be undone from the group page')
    pg.screenshot(path=os.path.join(OUT, 'groups-3-group.png'), full_page=True)
    pg.goto(LOCAL + '/#/groups'); pg.wait_for_timeout(1500)
    pg.click('[data-act=grpnew][data-kind=smart]'); pg.wait_for_timeout(500)
    pg.fill('dialog input[name=name]', 'Porch plants'); pg.select_option('dialog select[name=rf]', 'site'); pg.wait_for_timeout(300)
    pg.fill('dialog input[name=rv]', 'Covered porch'); pg.wait_for_timeout(1200)
    check('plants fit now' in pg.inner_text('#rule-prev'), 'while making a smart group the window says which plants fit')
    pg.click('dialog button[value=ok]'); pg.wait_for_timeout(2000)
    check(pg.locator('h1').inner_text() == 'Porch plants' and pg.locator('#g-plants li.job').count() > 10, 'the new smart group opens with its plants')
    pg.goto(LOCAL + '/#/plants'); pg.wait_for_timeout(2000)
    pg.select_option('select[data-f=group]', str(ph['id'])); pg.wait_for_timeout(800)
    check(pg.locator('#grid .sheet').count() == N, 'the Plants page shows only the plants in the chosen group')
    pg.goto(LOCAL + '/#/plant/P-029'); pg.wait_for_timeout(2500)
    check('group Philodendrons' in pg.inner_text('#pn-sum') and f'plant 2 of {N}' in pg.inner_text('#pn-pos'), 'Previous and Next follow the group')
    gl = pg.inner_text('#pl-groups')
    check('Philodendrons' in gl and 'Tall Black Shelf' in gl, f'the plant page lists its groups ({gl.strip()[:60]})')
    pg.click('[data-act=plgroups]'); pg.wait_for_timeout(500)
    pg.fill('dialog input[name=newg]', 'Pink ones'); pg.click('dialog button[value=ok]'); pg.wait_for_timeout(2000)
    check('Pink ones' in pg.inner_text('#pl-groups'), 'a new hand-picked group can be made from a plant page')
    pg.goto(LOCAL + '/#/plants'); pg.wait_for_timeout(1500); pg.select_option('select[data-f=group]', ''); pg.select_option('select[data-f=sort]', 'group'); pg.wait_for_timeout(800)
    first = pg.locator('#grid .sheet .acc').first.inner_text()
    alpha = sorted(call('GET', '/api/groups')[1]['groups'], key=lambda g: g['name'].lower())[0]
    check(first in alpha['codes'], f"sorting by group puts plants of the first group A to Z ({alpha['name']}) first")
    ph2 = b.new_page(viewport={'width': 390, 'height': 844})
    ph2.add_init_script("localStorage.setItem('plantdb.editor','Group Test');localStorage.setItem('plantdb.morefilters','1');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    ph2.goto(LOCAL + f"/#/group/{ph['id']}"); ph2.wait_for_timeout(2500)
    wide = ph2.evaluate('document.documentElement.scrollWidth <= innerWidth + 1')
    ph2.click('[data-act=grpcare]'); ph2.wait_for_timeout(600)
    check(wide and ph2.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'on a phone with the largest text there is no sideways scrolling, with or without a window open')
    ph2.screenshot(path=os.path.join(OUT, 'groups-4-phone-care.png'))
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    vw.goto(TS + f"/#/group/{ph['id']}"); vw.wait_for_timeout(2500)
    check(vw.locator('#g-plants li.job').count() == N and vw.locator('[data-act^=grp]:not([data-act=grpshow]):visible').count() == 0, 'a viewer sees the group but no buttons that change anything')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails))
sys.exit(1 if fails else 0)
