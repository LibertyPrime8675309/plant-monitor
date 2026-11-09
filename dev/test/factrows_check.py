"""Checks 1.53.0 (PLAN.md step 6a): knowledge with provenance. A species page has "Facts and where they come from": the record's
facts for the species by group, each with its value, its source, how sure, who and when, and the history; a plant's page says which
care fields are shown from the species' facts and links to them; the groups fold; nothing breaks at phone width or for a viewer.
Start the mock server with a fresh data folder (MOCK_TS=1), then:  python3 dev/test/factrows_check.py [base]
Screenshots: dev/tmp/shots/factrows-*.png"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
LOCAL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = LOCAL.rsplit(':', 1)[0] + ':' + str(int(LOCAL.rsplit(':', 1)[1]) + 1)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, base=LOCAL, headers=None):
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Rows Test', **(headers or {})}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')

R = call('GET', '/api/facts/rows?name=Agave%20americana')
check(R['total'] >= 8 and R['accepted'] == R['total'] and all(f['accepted'] for g in R['groups'] for f in g['fields']), f'the API gives the agave\'s facts by group ({R["total"]})')
# the fig: one plant of its species, so clearing two fields on it makes the plant read them from the species
p = call('GET', '/api/plants/P-003')
call('PUT', '/api/plants/P-003', {'base_version': p['version'], 'fields': {'soil_medium': '', 'light_hours': ''}})
with sync_playwright() as pw:
    b = pw.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and '404' not in m.text and '502' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Rows Test')")
    pg.goto(LOCAL + '/#/species/Agave%20americana'); pg.wait_for_selector('#sp-facts-rows', timeout=15000); pg.wait_for_timeout(500)
    sec = pg.locator('#sp-facts-rows')
    check(sec.locator('h2').inner_text() == 'Facts and where they come from' and sec.evaluate("e => e.parentElement.closest('section') === null"), 'the species page has the section, beside the others (not inside one)')
    check('for the genus Agave as a whole' in sec.inner_text(), 'it says the facts are for the genus when that is what the record has')
    groups = sec.locator('.fr-group')
    check(groups.count() >= 2 and all(groups.nth(i).locator('summary').count() == 1 for i in range(groups.count())), f'facts come in {groups.count()} groups that fold')
    g = groups.filter(has_text='Uses and partners').first
    g.locator('summary').click(); pg.wait_for_timeout(300)
    t = g.inner_text()
    check('In short' in t and 'Uses' in t and 'Noted by' in t and 'Likely' in t and 'upgrade batch' in t, 'a row shows its value, its source, who noted it and how sure')
    check(g.locator('a[href^="http"]').count() >= 1, 'read-more sources are links')
    check(sec.locator('a[href="/api/facts/export.csv"]').count() == 1, 'every fact can be downloaded as a CSV')
    check(pg.locator('#sn-list a, #sn-list button').filter(has_text='Facts and where').count() >= 1, 'the section is in Navigation')
    pg.screenshot(path=os.path.join(OUT, 'factrows-1-species.png'), full_page=False)
    # the monstera: five plants of the species; the care values they agree on are facts, traced to the batch that set them
    pg.goto(LOCAL + '/#/species/Monstera%20deliciosa'); pg.wait_for_timeout(1500); pg.wait_for_selector('#sp-facts-rows', timeout=15000); pg.wait_for_timeout(500)
    sec = pg.locator('#sp-facts-rows'); t = sec.inner_text()
    check('Temperature' in t and 'Light' in t and ('first plant list' in t or 'Upgrade batch' in t or 'accepted facts' in t), 'a species in the record has its care facts')
    sec.locator('.fr-group').filter(has_text='Temperature').first.locator('summary').click(); pg.wait_for_timeout(300)
    check('plants of this species' in sec.inner_text() and ('first plant list' in sec.inner_text() or 'Upgrade batch' in sec.inner_text()), 'a care fact says how many plants agree on it and which batch or list set it')
    sec.locator('.fr-group').filter(has_text='Temperature').first.screenshot(path=os.path.join(OUT, 'factrows-2-temperature.png'))
    # the plant's page: the two cleared fields are shown from the species, and say so
    pg.goto(LOCAL + '/#/plant/P-003'); pg.wait_for_selector('#fr-plant', timeout=15000); pg.wait_for_timeout(300)
    line = pg.locator('#fr-plant').inner_text()
    check('Not set for this plant' in line and 'soil or potting mix' in line and 'hours of light' in line and 'Ficus carica' in line, f'the plant page says which fields come from the species: "{line[:120]}"')
    check(pg.locator('#soil h3', has_text='Soil or potting mix').count() == 1, 'and the soil section shows the species\' value')
    check(pg.locator('#fr-plant a').get_attribute('href') == '#/species/Ficus%20carica', 'with a link to the species\' facts')
    # the edit form does not get the filled values
    pg.goto(LOCAL + '/#/plant/P-003/edit'); pg.wait_for_timeout(2500)
    check(pg.locator('[name=soil_medium]').input_value() == '', 'the edit form shows the plant\'s own (empty) value, not the species\'')
    # a viewer reads the same
    urllib.request.urlopen(urllib.request.Request(TS + '/api/me', headers={'Tailscale-User-Login': 'owner@example.com', 'Tailscale-User-Name': 'Own'})).read()
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers={'Tailscale-User-Login': 'viewer@example.com', 'Tailscale-User-Name': 'Vee'})
    vw.goto(TS + '/#/species/Agave%20americana'); vw.wait_for_selector('#sp-facts-rows', timeout=15000)
    check(vw.locator('#sp-facts-rows .fr-group').count() >= 2, 'a viewer reads the facts too')
    vw.close()
    # phone width, largest text
    ph = b.new_page(viewport={'width': 390, 'height': 844})
    ph.add_init_script("localStorage.setItem('plantdb.editor','Rows Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    ph.goto(LOCAL + '/#/species/Agave%20americana'); ph.wait_for_selector('#sp-facts-rows', timeout=15000)
    ph.locator('#sp-facts-rows .fr-group').first.locator('summary').click(); ph.wait_for_timeout(300)
    over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
    check(over <= 2, f'phone, largest text: no sideways scrolling ({over}px)')
    ph.locator('#sp-facts-rows').screenshot(path=os.path.join(OUT, 'factrows-3-phone.png'))
    for e in errs: check(False, 'browser error: ' + e)
    b.close()
print(f'\n{len(fails)} failed' if fails else '\nall good')
sys.exit(1 if fails else 0)
