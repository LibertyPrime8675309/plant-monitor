"""Checks 1.27.0: uses, partners, deterrents, propagation and breeding. Batch A9 adds them for the species in the record once each
(never over anything already there); plant pages, species pages and mushroom finds show them, with your plants linked as partners
and as plants it could cross with; Claude writes them on request for any other species (the owner's key), and for a fungus never
lists eating it. Start the mock server with a fresh data folder (MOCK_TS=1), then:
python3 dev/test/facts_check.py      Screenshots: dev/tmp/shots/facts-*.png"""
import json, os, sqlite3, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Facts Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e: return e.code, {}
codes = lambda xs: [x['code'] for x in xs]
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}       # the first person in is the owner
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)

f = call('GET', '/api/facts?code=P-014')[1]['facts']
check(f and f['key'] == 'aloe vera' and f['origin'] == 'researched', 'batch A9 gives the aloe its uses and partners')
check({'P-078', 'P-079'} <= set(codes(f['cross_same'])) and {'P-015', 'P-016', 'P-080'} <= set(codes(f['cross_other'])),
      'your other aloes are listed as the same species, and the haworthias and hardy aloe as plants it may cross with')
check(any('P-016' in codes(p['yours']) for p in f['partners_good']), 'a good partner you have is linked to your plant')
check(any('latex' in u['caution'] for u in f['uses']), 'the gel use warns about the latex')
check(call('GET', '/api/facts?code=P-080')[1]['facts']['key'] == 'aloe', 'a plant without a clear species name is linked by the batch (P-080 to Aloe)')
fig = call('GET', '/api/facts?code=P-003')[1]['facts']
check(fig['key'] == 'ficus carica' and not fig['cross_other'] and not fig['cross_same'], 'a fig lists no plants to cross with (it needs its wasp)')
check(call('GET', '/api/facts?code=P-036')[1]['facts'] is None, 'an unidentified plant has none')
st, r = call('GET', '/api/facts?name=Monstera%20deliciosa')
check(st == 200 and {'P-049', 'P-084'} <= set(codes(r['facts']['cross_same'])), 'a library species page finds the same facts, linked to your plants')
ph = call('GET', '/api/facts?code=P-062')[1]['facts']        # Philodendron erubescens 'White Knight': the genus facts
check(ph['key'] == 'philodendron' and 'P-029' in codes(ph['cross_same']) and 'P-009' in codes(ph['cross_other']),
      'a species without its own entry uses its genus; the same species and the rest of the genus are told apart')

# the batch never writes over facts already there
db = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'data', 'plants.db'))
check(db.execute("SELECT COUNT(*) FROM species_facts WHERE origin='researched'").fetchone()[0] >= 50, 'about 50 species are researched')
check(db.execute("SELECT value FROM settings WHERE key='batch_applied:A9'").fetchone() is not None, 'and the batch is recorded as applied')
db.close()

# Claude, on request
check(call('POST', '/api/facts', {'name': 'Lupinus texensis'})[0] == 400, 'without a Claude key it says what is needed')
call('PUT', '/api/identify/settings', {'claude_key': 'test-key-123'})
check(call('POST', '/api/facts', {'name': 'Aloe vera'})[0] == 409, 'researched facts are not written over by Claude')
check(call('POST', '/api/facts', {'name': 'Lupinus texensis'}, V, TS)[0] == 403, 'someone who can only view cannot ask Claude')
st, r = call('POST', '/api/facts', {'name': 'Lupinus texensis', 'common_name': 'Texas bluebonnet'})
f = r.get('facts') or {}
check(st == 200 and f.get('origin') == 'claude' and f['uses'][0]['kind'] == 'Cut flowers', 'Claude writes them for any species, and they are kept')
check(any(p['sci'] == 'Agave' and 'P-042' in codes(p['yours']) for p in f['partners_good']), 'and its partners are linked to your plants too')
check(len(f['sources']) == 1, 'a source that is not an https link is dropped')
st, r = call('POST', '/api/facts', {'name': 'Leucocoprinus birnbaumii', 'kind': 'fungus'})
f = r.get('facts') or {}
check(st == 200 and [u['kind'] for u in f['uses']] == ['Soil'], 'for a fungus, any use that means eating it is dropped')

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Facts Test')")
    pg.goto(LOCAL + '/#/plant/P-022'); pg.wait_for_timeout(2500)
    box = pg.locator('#uses .facts-box')
    box.locator('.facts').wait_for(timeout=8000)
    t = box.inner_text()
    check('Uses' in t and 'Good partners' in t and 'Propagation' in t and 'Breeding' in t, 'the plant page has uses, partners, propagation and breeding')
    check(box.locator('a[href="#/plant/P-073"]').count() >= 1 and 'patented' in t, 'it links your other roses to cross with, and warns about the patent')
    check(pg.locator('#jumprow button, #jumprow a').filter(has_text='Uses').count() == 1, 'the row of section buttons has "Uses"')
    pg.locator('#uses').screenshot(path=os.path.join(OUT, 'facts-1-plant.png'))
    pg.goto(LOCAL + '/#/species/Agave%20americana'); pg.wait_for_timeout(2500)
    box = pg.locator('.facts-box').first
    box.wait_for(timeout=8000); pg.wait_for_timeout(800)
    check(box.locator('.facts').count() == 1 and 'For the genus' in box.inner_text(), 'a species page without its own entry shows the genus, and says so')
    pg.goto(LOCAL + '/#/species/Testia%20species03'); pg.wait_for_timeout(2500)
    box = pg.locator('.facts-box').first; pg.wait_for_timeout(800)
    check(box.locator('[data-act=factswrite]').count() == 1, 'a species with none offers "Write them with Claude"')
    box.locator('[data-act=factswrite]').click()
    box.locator('.facts').wait_for(timeout=15000)
    check('Cut flowers' in box.inner_text() and 'Written by Claude' in box.inner_text(), 'pressing it writes and shows them')
    pg.screenshot(path=os.path.join(OUT, 'facts-2-species.png'), full_page=True)
    b.close()
    # a viewer sees them but cannot ask Claude
    ctx = p.chromium.launch().new_context(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    v = ctx.new_page(); v.goto(TS + '/#/species/Testia%20species04'); v.wait_for_timeout(3000)
    check(v.locator('[data-act=factswrite]').count() == 0 or not v.locator('[data-act=factswrite]').first.is_visible(), 'someone who can only view gets no Write button')
    # a phone with large text: nothing sideways
    ph = p.chromium.launch().new_context(viewport={'width': 384, 'height': 740}, is_mobile=True, has_touch=True, service_workers='block')
    ph.add_init_script("localStorage.setItem('plantdb.editor','Facts Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    q = ph.new_page(); q.on('pageerror', lambda e: errs.append(str(e)))
    q.goto(LOCAL + '/#/plant/P-014'); q.wait_for_timeout(3000)
    q.locator('#uses .facts').wait_for(timeout=8000)
    check(not q.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'on a phone with the largest text nothing scrolls sideways')
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All facts checks passed' if not fails else f'{len(fails)} facts check(s) failed'))
raise SystemExit(1 if fails else 0)
