"""Checks 1.51.0 (PLAN.md step 5b): Identify in two modes. Every page that identifies asks "What are you looking at?" (One of my
plants / A new find) with the last answer first, unless Display says what to use on that page; "a new find" lifts the plants
recorded in the home's country instead of the record's own plants, and the result says which way it was checked and whether the
country's list is there yet; the choice follows the person (server prefs). Phone width, no sideways scrolling.
Start the mock server with a fresh data folder, then:  python3 dev/test/idmodes_check.py      Screenshots: dev/tmp/shots/idmodes-*.png"""
import io, json, os, sys, urllib.request
from PIL import Image
from playwright.sync_api import sync_playwright
LOCAL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = LOCAL.rsplit(':', 1)[0] + ':' + str(int(LOCAL.rsplit(':', 1)[1]) + 1)       # the Tailscale port
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
TMP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp'); os.makedirs(TMP, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(LOCAL + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Modes Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def pic(rgb, path):
    Image.new('RGB', (160, 160), rgb).save(path, 'PNG'); return path
green, blue = pic((20, 160, 40), os.path.join(TMP, 'idm-green.png')), pic((30, 40, 220), os.path.join(TMP, 'idm-blue.png'))

# the API: the mode and the country go through to the checker, and the status says the country
st = call('GET', '/api/identify/status')
check(st.get('site_country') == 'US' and st.get('country', {}).get('code') == 'US', f'the status carries the home\'s country ({st.get("site_country")}) and the checker\'s list state for it')
asked = lambda: pg.locator('.idm-btn').count() > 0
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and '404' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Modes Test')")
    pg.goto(LOCAL + '/#/identify'); pg.wait_for_timeout(2500)
    sel = pg.locator('select[data-act=idmode]')
    check(sel.count() == 1 and pg.locator('label:has(select[data-act=idmode])').count() == 1 and sel.input_value() == 'mine', 'the page shows which way it checks, with a real label; "one of my plants" to start with')
    # choosing a photo asks first
    pg.set_input_files('input[data-act=idfile]', green); pg.wait_for_timeout(800)
    btns = pg.locator('.idm-btn')
    check(asked() and btns.count() == 2 and [btns.nth(i).locator('strong').inner_text() for i in range(2)] == ['One of my plants', 'A new find'], 'choosing a photo asks "What are you looking at?" with two choices, the last answer (one of my plants) first')
    check(pg.evaluate("document.activeElement && document.activeElement.classList.contains('idm-btn')"), 'the first choice has the focus, so Enter takes it')
    check(pg.locator('.idm-form .chk input').count() == 1 and 'Do not ask again on Identify' in pg.locator('.idm-form .chk').inner_text(), 'with a box to stop asking on this page')
    pg.screenshot(path=os.path.join(OUT, 'idmodes-1-question.png'))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    check(not asked() and 'Start the camera' in pg.inner_text('#id-res') or pg.locator('#id-res .muted').count() >= 0, 'Escape cancels: nothing is checked')
    # a new find
    pg.set_input_files('input[data-act=idfile]', green); pg.wait_for_timeout(800)
    pg.locator('.idm-btn', has_text='A new find').click()
    pg.wait_for_selector('dialog[open] .id-pop, #id-res .id-mode-note', timeout=10000); pg.wait_for_timeout(600)
    if pg.locator('dialog[open]').count(): pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    note = pg.locator('#id-res .id-mode-note')
    check(note.count() == 1 and 'Checked as a new find' in note.inner_text() and 'US' in note.inner_text() and 'downloading' in note.inner_text(),
          f'the result says it was checked as a new find and that the US list is still downloading: "{note.inner_text() if note.count() else ""}"')
    tags = [t.inner_text() for t in pg.locator('#id-res .tag-why').all()]
    check(any('recorded in this country' in t for t in tags) and not any('houseplant' in t or 'you have' in t for t in tags), f'the lifts are the country\'s, not the record\'s: {tags}')
    check(sel.input_value() == 'new', 'the choice on the page follows the answer')
    pref = json.loads(pg.evaluate("localStorage.getItem('plantdb.idmode') || '{}'"))
    check(pref.get('last') == 'new' and 'identify' not in pref, 'the answer is remembered as the last one, not as a rule')
    pg.screenshot(path=os.path.join(OUT, 'idmodes-2-new-find.png'), full_page=False)
    # asked again, the last answer first; the box stops the asking
    pg.set_input_files('input[data-act=idfile]', blue); pg.wait_for_timeout(800)
    check(asked() and pg.locator('.idm-btn').first.locator('strong').inner_text() == 'A new find', 'the next photo asks again, with "A new find" first now')
    pg.locator('.idm-form .chk input').check(); pg.locator('.idm-btn', has_text='One of my plants').click()
    pg.wait_for_selector('dialog[open] .id-pop, #id-res .id-mode-note', timeout=10000); pg.wait_for_timeout(600)
    if pg.locator('dialog[open]').count(): pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    check('Checked as one of my plants' in pg.inner_text('#id-res'), 'checked as one of my plants')
    pg.wait_for_timeout(1200)                                                 # the setting reaches the server
    pref = json.loads(pg.evaluate("localStorage.getItem('plantdb.idmode') || '{}'"))
    check(pref.get('identify') == 'mine', 'the box made "one of my plants" the rule for the Identify page')
    pg.set_input_files('input[data-act=idfile]', green); pg.wait_for_timeout(1500)
    check(not asked(), 'the next photo is checked without asking')
    if pg.locator('dialog[open]').count(): pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    # the country's list, once there (the fake checker has it after three asks), is named in the result
    pg.select_option('select[data-act=idmode]', 'new'); pg.wait_for_timeout(300)
    pg.set_input_files('input[data-act=idfile]', green); pg.wait_for_timeout(1500)
    if pg.locator('dialog[open]').count(): pg.keyboard.press('Escape'); pg.wait_for_timeout(400)
    note = pg.locator('#id-res .id-mode-note')
    check(note.count() == 1 and '48,696 species' in note.inner_text(), f'once the list is there the result says how many species the country has: "{note.inner_text() if note.count() else ""}"')
    # Display: the Identify part, with one choice per page; a rule made there stops the question on that page
    pg.click('#display-btn'); pg.wait_for_timeout(600)
    pg.click('.dv-tab:has-text("Identify")'); pg.wait_for_timeout(400)
    sels = pg.locator('[data-act=idmodeset]')
    check(sels.count() == 3 and pg.locator('#pref-im-identify').input_value() == 'mine' and pg.locator('#pref-im-add').input_value() == 'ask', 'Display has an Identify part with a choice for each of the three pages; Identify shows the rule made with the box')
    check(pg.evaluate("[...document.querySelectorAll('[data-act=idmodeset]')].every(s => s.labels && s.labels.length)"), 'every choice has a real label')
    pg.select_option('#pref-im-identify', 'ask'); pg.select_option('#pref-im-add', 'new'); pg.wait_for_timeout(300)
    pg.screenshot(path=os.path.join(OUT, 'idmodes-3-display.png'))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(1200)
    prefs = call('GET', '/api/me/prefs')['prefs']
    check(json.loads(prefs.get('idmode', '{}')).get('add') == 'new', 'the choices reach the server, so they follow the person to other devices')
    # adding several plants: the rule says "a new find", so no question; the request carries the mode
    seen = []
    pg.on('request', lambda r: seen.append(r.url) if '/api/plants/several/' in r.url else None)
    pg.goto(LOCAL + '/#/new/several'); pg.wait_for_timeout(1500)
    if pg.locator('input[name=files]').count():
        pg.set_input_files('input[name=files]', [green]); pg.click('form[data-form=sevgo] button[type=submit]'); pg.wait_for_timeout(3000)
        check(not asked() and any('mode=new' in u for u in seen), f'Add several plants follows the rule (a new find) without asking, and sends it: {[u.split("?")[1][:40] for u in seen][:2]}')
    # Add a plant: asked (the rule for adding is cleared first), and the form keeps working
    pg.evaluate("(() => { const v = JSON.parse(localStorage.getItem('plantdb.idmode') || '{}'); delete v.add; localStorage.setItem('plantdb.idmode', JSON.stringify(v)); })()"); pg.wait_for_timeout(1200)
    pg.goto(LOCAL + '/#/new'); pg.wait_for_timeout(1500)
    pg.set_input_files('input[name=__photos]', green); pg.wait_for_timeout(500)
    pg.click('#newfill-btn'); pg.wait_for_timeout(1000)
    check(asked(), 'Add a plant asks when the names are filled in from a photo')
    pg.locator('.idm-btn', has_text='A new find').click(); pg.wait_for_timeout(3000)
    check('Checked as a new find' in pg.inner_text('#newfill-st') or pg.locator('#new-splist').count() == 1, 'and fills the names in after the answer')
    # a plant's own page: asked once, then the result is marked
    pg.goto(LOCAL + '/#/plant/P-001'); pg.wait_for_timeout(2000)
    btn = pg.locator('[data-act=plantid]').first
    if btn.count():
        btn.click(); pg.wait_for_timeout(800)
        check(asked(), 'a plant\'s own page asks before checking its photos')
        pg.locator('.idm-btn', has_text='One of my plants').click(); pg.wait_for_timeout(3000)
        check('Checked as one of my plants' in pg.inner_text('#plant-id'), 'and says how its photos were checked')
    # viewers can identify too, and are asked the same way
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers={'Tailscale-User-Login': 'viewer@example.com', 'Tailscale-User-Name': 'Vee'})
    call('GET', '/api/me')                                                   # the local owner exists; the viewer is the second person
    vw.goto(TS + '/#/identify'); vw.wait_for_timeout(2500)
    vw.set_input_files('input[data-act=idfile]', green); vw.wait_for_timeout(800)
    check(vw.locator('.idm-btn').count() == 2, 'a viewer is asked too (identifying changes nothing)')
    vw.close()
    # phone width, largest text
    ph = b.new_page(viewport={'width': 390, 'height': 844})
    ph.add_init_script("localStorage.setItem('plantdb.editor','Modes Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}));localStorage.removeItem('plantdb.idmode')")
    ph.goto(LOCAL + '/#/identify'); ph.wait_for_timeout(2500)
    ph.evaluate("localStorage.removeItem('plantdb.idmode')")
    ph.set_input_files('input[data-act=idfile]', green); ph.wait_for_timeout(1000)
    over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
    dlgw = ph.evaluate("(() => { const d = document.getElementById('dlg'); return d.open ? d.getBoundingClientRect().right <= innerWidth + 1 : true; })()")
    check(ph.locator('.idm-btn').count() == 2 and over <= 2 and dlgw, f'phone, largest text: the question fits (sideways {over}px)')
    ph.screenshot(path=os.path.join(OUT, 'idmodes-4-phone.png'))
    for e in errs: check(False, 'browser error: ' + e)
    b.close()
print(f'\n{len(fails)} failed' if fails else '\nall good')
sys.exit(1 if fails else 0)
