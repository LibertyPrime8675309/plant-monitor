"""Checks 1.57.0: the propagation and breeding guide (#/guide). The page and its sections, the plants of yours listed under each method (from
their own propagation notes and their species' facts), which words in a note mean which section, deep links that open a method, lengths
and temperatures in the person's units, the links to it from a plant's page, the Library and Search, and the page at phone width with the
largest text and in dark mode. Start the mock server with a fresh data folder, then:
python3 dev/test/guide_check.py      Screenshots: dev/tmp/shots/guide-*.png"""
import json, os, re, urllib.request
from playwright.sync_api import sync_playwright
BASE = 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def get(url):
    with urllib.request.urlopen(BASE + url) as r: return json.loads(r.read() or b'null')
METHODS = ['gd-stem', 'gd-leaf', 'gd-root', 'gd-division', 'gd-offsets', 'gd-layering', 'gd-air-layering', 'gd-grafting', 'gd-bulbs', 'gd-spores', 'gd-tissue', 'gd-seed']
BREEDING = ['gd-genetics', 'gd-cross', 'gd-select', 'gd-variation', 'gd-orchid', 'gd-legal']
data = get('/api/guide/plants')['plants']
check(len(data) > 20 and all(p['lines'] for p in data), f'the server lists {len(data)} plants with propagation notes')
plants = {p['code']: p for p in get('/api/plants')}
check({p['code'] for p in data} <= set(plants) and all(plants[p['code']]['status'] == 'active' for p in data if 'status' in plants[p['code']]), 'only plants that are in the record, and active ones')
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Guide Test')")
    pg.goto(BASE + '/#/guide'); pg.wait_for_selector('#gd-choose', timeout=15000); pg.wait_for_timeout(800)
    check(pg.locator('h1').inner_text() == 'Propagation and breeding guide' and pg.title().startswith('Propagation and breeding guide'), 'the page has its title')
    h2 = pg.evaluate("[...document.querySelectorAll('main h2')].map(h => h.textContent.trim())")
    check(h2 == ['Which way should I do it?', 'Before you start', 'Copying a plant: propagation', 'Breeding: making plants that are new', 'Keeping a mother plant'], f'five sections in order ({h2})')
    check(all(pg.locator('#' + m).count() == 1 for m in METHODS + BREEDING), 'every method and every breeding topic has its own folded group')
    check(pg.evaluate("[...document.querySelectorAll('main details.gd-method')].every(d => !d.open)"), 'they start folded')
    check(pg.evaluate("[...document.querySelectorAll('main details.gd-method > summary')].every(s => s.querySelector('h3') && !s.querySelector('button'))"), 'each bar is a heading and one control, with no button inside it')
    check(pg.locator('#main-nav a[aria-current=page]').inner_text().strip().startswith('Discover') and pg.locator('#sub-nav a[aria-current=page]').inner_text().strip() == 'Library', 'it sits under Discover, with Library marked')
    check('[[' not in pg.inner_text('main') and ']]' not in pg.inner_text('main'), 'no length marker is left showing')
    check(pg.locator('#gd-choose a').count() >= 15 and all(pg.locator('#gd-choose a').nth(i).get_attribute('href').startswith('#/guide?sec=gd-') for i in range(pg.locator('#gd-choose a').count())),
          'the first section links each goal to the ways that suit it')
    check('not checked against a source by a person' in pg.inner_text('main'), 'it says where its words come from')
    # your plants
    y = pg.locator('#gd-stem-yours')
    check(y.count() == 1 and re.match(r'Your plants with this in their notes \((\d+)\):', y.text_content()) is not None, 'stem cuttings lists your plants that have it')
    n = int(re.match(r'Your plants with this in their notes \((\d+)\):', y.text_content()).group(1))
    codes = [re.search(r'/plant/([^/?]+)', y.locator('a').nth(i).get_attribute('href')).group(1) for i in range(y.locator('a').count())]
    check(n == len(codes) and n > 5, f'its count ({n}) is the number of plants linked')
    lines = {p['code']: ' '.join(p['lines']).lower() for p in data}
    check(all(re.search(r'cutting|stem|node', lines[c]) for c in codes), 'every plant listed has a cutting, stem or node in its notes')
    check(all(c in codes for c, t in lines.items() if re.search(r'stem cutting', t)), 'and every plant whose notes say "stem cutting" is listed')
    check(y.locator('a').first.get_attribute('href') == f'#/plant/{codes[0]}' and y.locator('.muted').first.text_content() == f'({codes[0]})', 'each is a link with its code beside the name, so two of the same name can be told apart')
    check(pg.locator('#gd-spores-yours').count() == 1, 'every method has its line, even where no plant has it (' + pg.locator('#gd-spores-yours').text_content()[:60] + ')')
    check(pg.locator('#gd-genetics-yours').count() == 0, 'breeding topics have none')
    # which words mean which section
    K = lambda s: pg.evaluate('s => gdKeys(s)', s)
    check(K('Air layering a tall, leggy cane.') == ['gd-air-layering'], '"air layering" is air layering only, not layering as well')
    check(K('Hardwood cuttings in winter. Layering a long cane into the soil.') == ['gd-layering', 'gd-stem'], 'cuttings and layering in one line are both found')
    check(K('Leaf cuttings of a single leaf') == ['gd-leaf'], '"leaf cuttings" are not also stem cuttings')
    check(K('Root cuttings in winter') == ['gd-root'] and K('Stem cuttings root in days in water.') == ['gd-stem'], 'root cuttings, and stem cuttings in water')
    check(K('Division of clumps in spring') == ['gd-division'] and K('Pups, runners or keikis') == ['gd-offsets'], 'division, and pups or keikis')
    check(K('Seed: nick or soak the hard seeds overnight.') == ['gd-seed'], 'a seed note does not count as a stem cutting')
    check(K('Tissue culture only') == ['gd-tissue'] and K('Grafting onto a rootstock') == ['gd-grafting'] and K('Spores on damp peat') == ['gd-spores'], 'tissue culture, grafting and spores')
    check(K('Overwinter a tuber indoors') == ['gd-bulbs'] and K('Nothing useful here') == [] and K('') == [], 'tubers are bulbs; a note about nothing matches nothing')
    # open and deep links
    pg.locator('#gd-air-layering > summary').click(); pg.wait_for_timeout(200)
    check(pg.locator('#gd-air-layering').evaluate('d => d.open') and pg.locator('#gd-air-layering ol li').count() == 7, 'air layering opens, with its seven steps in an ordered list')
    check('foil' in pg.inner_text('#gd-air-layering') and 'Suits:' in pg.inner_text('#gd-air-layering'), 'with what it suits and its tips')
    pg.goto(BASE + '/#/guide?sec=gd-cross'); pg.wait_for_selector('#gd-cross'); pg.wait_for_timeout(1800)
    check(pg.locator('#gd-cross').evaluate('d => d.open') and pg.locator('#gd-cross ol li').count() == 8, 'a link with ?sec= opens that group (making a cross has eight steps)')
    check(pg.evaluate("(() => { const r = document.getElementById('gd-cross').getBoundingClientRect(); return r.top < innerHeight && r.bottom > 0; })()"), 'and scrolls it into view')
    pg.goto(BASE + '/#/guide'); pg.wait_for_selector('#gd-choose'); pg.wait_for_timeout(500)
    pg.locator('#gd-choose a', has_text='Air layering').first.click(); pg.wait_for_timeout(1800)
    check(pg.locator('#gd-air-layering').evaluate('d => d.open'), 'a goal link opens the method it names')
    pg.screenshot(path=os.path.join(OUT, 'guide-1-laptop.png'), full_page=True)
    # temperatures and lengths in the person's units
    stem = lambda: pg.inner_text('#gd-stem')
    pg.goto(BASE + '/#/guide?sec=gd-stem'); pg.wait_for_selector('#gd-stem'); pg.wait_for_timeout(800)
    check('70 to 75°F' in stem() and '1 in long' in stem(), 'in US units, 70 to 75°F and 1 in')
    pg.evaluate("localStorage.setItem('plantdb.units', JSON.stringify({region: 'metric'}))")
    pg.reload(); pg.wait_for_selector('#gd-stem'); pg.wait_for_timeout(800)
    check('21 to 24°C' in stem() and '2.5 cm long' in stem() and '°F' not in stem() and ' in long' not in stem(), 'in metric, 21 to 24°C and 2.5 cm')
    pg.goto(BASE + '/#/guide?sec=gd-root'); pg.wait_for_selector('#gd-root'); pg.wait_for_timeout(800)
    check('5 to 10 cm' in pg.inner_text('#gd-root'), 'a range of lengths too (2 to 4 in is 5 to 10 cm)')
    pg.evaluate("localStorage.removeItem('plantdb.units')")
    # a plant's page
    with_facts = None
    for c in sorted(plants):
        f = get(f'/api/facts?code={c}')['facts']
        if f and f.get('propagation') and any(re.search(r'cutting|division|layer|seed|graft|offset', x['method'], re.I) for x in f['propagation']): with_facts = (c, f); break
    check(with_facts is not None, 'a plant with species facts to look at was found')
    if with_facts:
        code, f = with_facts
        pg.goto(BASE + f'/#/plant/{code}'); pg.wait_for_selector('#uses .facts-box .fact-list', timeout=20000); pg.wait_for_timeout(800)
        check(pg.locator('#uses #gd-plantlink a[href="#/guide"]').count() == 1, 'the plant page links to the guide from its uses and propagation part')
        how = pg.locator('#uses .gd-how')
        check(how.count() >= 1 and all(how.nth(i).get_attribute('href').startswith('#/guide?sec=gd-') for i in range(how.count())), f'{how.count()} propagation method(s) have a "How to" link')
        check(how.first.inner_text() == 'How to' and (how.first.get_attribute('aria-label') or '').startswith('How to do it: '), 'its name starts with the words on it')
        href = how.first.get_attribute('href'); how.first.click(); pg.wait_for_selector('#gd-methods'); pg.wait_for_timeout(1800)
        check(pg.evaluate('h => location.hash === h', href) and pg.locator('#' + href.split('sec=')[1]).evaluate('d => d.open'), 'it opens the guide at that method')
    # the Library, and Search
    pg.goto(BASE + '/#/library'); pg.wait_for_selector('#gd-liblink', timeout=20000)
    check(pg.locator('p.row #gd-liblink').count() == 1, 'the Library has a button to it beside Around home and Wishlist')
    check(pg.evaluate("pagesList().some(x => x[1] === '#/guide' && x[0] === 'Propagation and breeding guide')"), 'Search lists it among the pages')
    pg.goto(BASE + '/#/weather'); pg.wait_for_timeout(1500)
    pg.keyboard.press('/'); pg.wait_for_selector('dialog[open]'); pg.keyboard.type('propagation'); pg.wait_for_timeout(1200)
    check(pg.locator('dialog[open] a[href="#/guide"]').count() >= 1, 'typing "propagation" in Search finds the page')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    # phone width, the largest text, dark
    BIG = {'size': '190', 'space': 'roomy', 'contrast': 'high', 'theme': 'dark'}
    ctx = br.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    ctx.add_init_script(f"localStorage.setItem('plantdb.editor','Guide Test');localStorage.setItem('plantdb.display',JSON.stringify({json.dumps(BIG)}))")
    ph = ctx.new_page(); ph.on('pageerror', lambda e: errs.append(str(e)))
    ph.goto(BASE + '/#/guide?sec=gd-stem'); ph.wait_for_selector('#gd-stem'); ph.wait_for_timeout(1800)
    check(ph.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'at phone width with the largest text, nothing runs off the side')
    check(ph.evaluate("[...document.querySelectorAll('main h1, main h2, main summary h3')].every(h => h.getBoundingClientRect().width <= innerWidth)"), 'and no heading is wider than the screen')
    ph.screenshot(path=os.path.join(OUT, 'guide-2-phone-large-dark.png'), full_page=True)
    ph.goto(BASE + '/#/guide?sec=gd-cross'); ph.wait_for_selector('#gd-cross'); ph.wait_for_timeout(1800)
    check(ph.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), 'making a cross open at phone width: nothing runs off the side either')
    # a viewer can read it: the guide has no buttons that change anything
    acts = set(ph.evaluate("[...document.querySelectorAll('main section.blk [data-act], main details.grp [data-act]')].map(e => e.dataset.act)"))
    check(acts and acts <= {'readsec', 'secfold'}, f'the only buttons in its sections read one aloud or fold it ({sorted(acts)}); nothing changes any data')
    br.close()
check(not errs, 'no script errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('\n%d check(s) failed' % len(fails) if fails else '\nall checks passed')
raise SystemExit(1 if fails else 0)
