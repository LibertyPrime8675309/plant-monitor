"""Checks 1.14.0: "About this plant". Every plant gets its details from upgrade batch batchA5 (type of plant, classification,
mature size, hardiness zones, native range, conservation status, flowers, fruit, dangers, propagation and linked sources),
the zone where the plants are, the hardy-or-not verdict, the edit form, phone width and people who can only view.
Start the mock server with a fresh data folder first, then:  python3 dev/test/details_check.py
Screenshots: dev/tmp/shots/details-*.png"""
import json, os, re, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'app'))
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
OUT = os.path.join(HERE, '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, base=LOCAL, h=None):
    req = urllib.request.Request(base + url, headers={'X-Editor': 'Details Test', **(h or {})}, method=m)
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'null')
    except urllib.error.HTTPError as e: return e.code, e.read().decode()

# ---- zones, straight from the server module
os.environ.setdefault('DATA_DIR', os.path.join(OUT, '..', 'details-check-data'))
import server as S
check(S.usda_zone(22) == '9a' and S.usda_zone(17) == '8b' and S.usda_zone(-60) == '1a' and S.usda_zone(42) == '11a', 'USDA zones: 22°F is 9a, 17°F is 8b, -60°F is 1a, 42°F is 11a')
check(S.zone_num('9a') == 9 and S.zone_num('9b') == 9.5 and S.zone_num('12') == 12 and S.zone_num('') is None, 'zone names turn into numbers for comparing')

# ---- the details from the batch
batch = json.load(open(os.path.join(HERE, '..', '..', 'app', 'seed', 'batches', 'batchA5.json'), encoding='utf-8'))
srcfile = {l.split('|')[2].strip() for l in open(os.path.join(HERE, '..', 'seed_src', 'sources_A5.txt'), encoding='utf-8') if l.strip()}
st, plants = call('GET', '/api/plants')
plants = plants if isinstance(plants, list) else plants.get('plants', [])
full = {p['code']: call('GET', '/api/plants/' + p['code'])[1] for p in plants}
need = ['growth_habit', 'kingdom', 'family', 'genus', 'height_pot', 'native_range', 'conservation_status', 'danger_humans', 'danger_animals', 'propagation']
gaps = [(c, f) for c, p in full.items() if c != 'P-036' for f in need if not (p.get(f) or '').strip()]
check(len(full) >= 79 and not gaps, f'every plant has its details ({len(full)} plants; missing: {gaps[:4]})')
nosrc = [c for c, p in full.items() if c not in ('P-036', 'P-053') and not (p.get('sources') or '').strip()]
check(not nosrc, f'every identified plant lists its sources ({nosrc[:5]})')
urls = [l.rsplit('|', 1)[1].strip() for p in full.values() for l in (p.get('sources') or '').splitlines() if '|' in l]
aspca = 'https://www.aspca.org/pet-care/animal-poison-control/toxic-and-non-toxic-plants'
check(urls and all(u.startswith('https://') for u in urls) and all(u in srcfile or u == aspca for u in urls), f'every source is a secure link from the checked source list ({len(set(urls))} links)')
check(all('Plantae' in (p.get('kingdom') or '') for p in full.values()), 'the kingdom is Plantae for all of them')
check('Vulnerable' in full['P-017']['conservation_status'] and 'Endangered' in full['P-046']['conservation_status'], 'majesty palm is Vulnerable and vanilla is Endangered on the IUCN Red List')
check('cardiac glycosides' in full['P-021']['danger_humans'] and 'kidney failure' in full['P-004']['danger_animals'], 'desert rose sap and grapes for dogs are flagged as dangerous')
check(not full['P-005'].get('zone_low') and 'annual' in full['P-005']['zone_notes'].lower(), 'annuals have no zone, and say they are annuals')
check(all(u['set'][f][0] == '' for u in batch['updates'] for f in u['set']), 'the batch only fills fields that are still empty')

# ---- the zone where the plants are
st, meta = call('GET', '/api/meta')
Z = meta.get('zone') or {}
check(Z.get('map_zone') == '8b to 9a' and Z.get('map_url') == S.USDA_MAP_URL, f"Round Rock is on the 8b/9a line of the 2023 USDA map ({Z.get('map_zone')})")

# ---- the page
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', base=TS, h=E); call('GET', '/api/me', base=TS, h=V)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and '404' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Details Test')")
    pg.goto(LOCAL + '/#/plant/P-020'); pg.wait_for_timeout(2500)
    t = pg.inner_text('#about')
    check('Moraceae' in t and 'Ficus' in t and 'Rosales' in t, 'the fiddle-leaf fig page shows its order, family and genus')
    check(pg.locator('#about table.tbl tbody tr').count() == 2, 'mature size in the ground and in a pot, as a table')
    check('Not hardy here' in t and 'zone 8b to 9a' in t, 'it says the fig is not hardy here, and names the zone')
    check(pg.locator('#about .danger-box').count() == 1 and '1-800-222-1222' in t, 'dangers are in their own box with the Poison Control number')
    links = pg.locator('#about ul.srcs a')
    n = links.count()
    check(n == len(full['P-020']['sources'].splitlines()) and all(links.nth(i).get_attribute('rel') == 'noopener noreferrer' and links.nth(i).get_attribute('target') == '_blank' for i in range(n)), f'each source is a link that opens in a new tab ({n})')
    check(pg.locator('#about ol li').count() >= 2, 'propagation is a numbered list')
    check(pg.locator('nav.jump [data-id=about]').count() == 1, 'the jump row has an About button')
    pg.screenshot(path=os.path.join(OUT, 'details-1-fig.png'), full_page=False)
    pg.locator('#about').screenshot(path=os.path.join(OUT, 'details-2-about.png'))
    pg.goto(LOCAL + '/#/plant/P-015'); pg.wait_for_timeout(2000)
    check('✓ Hardy here' in pg.inner_text('#about'), 'the hardy aloe is hardy here (zone 8a)')
    lo = next(c for c, q in full.items() if q.get('id_confidence') is not None and q['id_confidence'] < 85 and c != 'P-036')
    pg.goto(LOCAL + '/#/plant/' + lo); pg.wait_for_timeout(2000)
    check('closest match' in pg.inner_text('#about'), f'a plant with an unsure ID ({lo}) says the details are for the closest match')
    pg.goto(LOCAL + '/#/plant/P-020/edit'); pg.wait_for_timeout(2000)
    fs = pg.locator('fieldset', has=pg.locator('legend', has_text='About this plant'))
    check(fs.count() == 1 and fs.locator('textarea, input').count() >= 23, 'the edit form has an About this plant section with every field')
    check(fs.locator('label', has_text='Hardiness zone, coldest (USDA)').count() == 1 and fs.locator('label', has_text='Sources').count() >= 1, 'with real labels')
    ph = b.new_page(viewport={'width': 390, 'height': 844})
    ph.add_init_script("localStorage.setItem('plantdb.editor','Details Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    ph.goto(LOCAL + '/#/plant/P-021'); ph.wait_for_timeout(2500)
    check(ph.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'on a phone with the largest text there is no sideways scrolling')
    ph.locator('#about').scroll_into_view_if_needed(); ph.wait_for_timeout(300)
    ph.screenshot(path=os.path.join(OUT, 'details-3-phone.png'))
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    vw.goto(TS + '/#/plant/P-020'); vw.wait_for_timeout(2500)
    check('Moraceae' in vw.inner_text('#about'), 'a viewer can read the details')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails))
sys.exit(1 if fails else 0)
