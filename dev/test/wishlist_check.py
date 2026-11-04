"""Checks 1.22.0: the library extras. A wishlist (add from a species page, the Wishlist page, got it, edit, take off), your own notes
and tags on any species (shown on the cards, and as library filters), and the owner's "Download photos for the Texas list" (which
fills data/library in the background from the iNaturalist stand-in in dev/test/mock_vision.py). People who can only view can read
all of it but change none of it. Start the mock server with a fresh data folder (MOCK_TS=1), then:
python3 dev/test/wishlist_check.py      Screenshots: dev/tmp/shots/wishlist-*.png"""
import json, os, sys, time, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Wish Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)
check(call('PUT', '/api/wishlist', {'name': 'Lupinus texensis'}, V, TS)[0] == 403, 'someone who can only view cannot change the wishlist')
check(call('PUT', '/api/library/notes', {'name': 'Lupinus texensis', 'notes': 'x'}, V, TS)[0] == 403, 'nor notes')
check(call('POST', '/api/library/areas', {'place_id': 18, 'name': 'Texas, US'}, V, TS)[0] == 403, 'nor start a photo download (1.28.0: by area)')

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and '404' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Wish Test')")
    pg.goto(LOCAL + '/#/today'); pg.wait_for_timeout(1000); pg.evaluate("localStorage.removeItem('plantdb.library')")
    # wishlist from a species page
    pg.goto(LOCAL + '/#/species/Lupinus%20texensis'); pg.wait_for_timeout(2500)
    pg.click('[data-act=spwish]'); pg.wait_for_timeout(1500)
    check('On your wishlist.' in pg.inner_text('.sp-wish'), '"Add to my wishlist" puts it on the list, and the page says so')
    # notes and tags
    pg.click('.sp-notes-edit summary')
    pg.fill('form[data-form=spnotes] textarea[name=notes]', 'Sow in fall.\nNeeds sun.'); pg.fill('form[data-form=spnotes] input[name=tags]', 'Wildflower, seed packet, wildflower')
    pg.click('form[data-form=spnotes] button[type=submit]'); pg.wait_for_timeout(1500)
    t = pg.inner_text('.sp-mynotes')
    check('Sow in fall.' in t and 'Tag: wildflower' in t and 'Tag: seed packet' in t and t.count('wildflower') == 1, 'notes and tags save (tags in lower case, no repeats)')
    pg.screenshot(path=os.path.join(OUT, 'wishlist-1-species.png'), full_page=True)
    pg.click('.sp-mynotes a.tag:has-text("wildflower")'); pg.wait_for_timeout(2500)
    check(pg.locator('select[data-f=libmine]').input_value() == 'tag:wildflower' and pg.locator('#lib-res .lib-card').count() == 1, 'a tag links to the library showing everything with that tag')
    check('Tag: wildflower' in pg.inner_text('#lib-res') and 'On your wishlist' in pg.inner_text('#lib-res'), 'the library cards show your tags and the wishlist')
    pg.select_option('select[data-f=libmine]', 'wish'); pg.wait_for_timeout(1500)
    check(pg.locator('#lib-res .lib-card').count() == 1, 'Show: On my wishlist')
    pg.select_option('select[data-f=libmine]', 'notes'); pg.wait_for_timeout(1500)
    check(pg.locator('#lib-res .lib-card').count() == 1, 'Show: Ones with notes or tags')
    pg.click('#lib-clear'); pg.wait_for_timeout(2000)
    # the Wishlist page
    call('PUT', '/api/wishlist', {'name': 'Monstera deliciosa', 'common_name': 'Swiss cheese plant'})
    pg.click('a:has-text("Your wishlist")'); pg.wait_for_timeout(1500)
    check(pg.evaluate('location.hash') == '#/wishlist' and pg.locator('.wl-item').count() == 2, 'the Library page links to the wishlist, which lists both')
    check('You have it: P-049' in pg.inner_text('main'), 'it says when you already have one')
    pg.locator('.wl-item', has_text='Texas bluebonnet').locator('[data-act=wledit]').click(); pg.wait_for_timeout(500)
    pg.fill('#dlg [name=where]', 'Wildseed Farms'); pg.click('#dlg button[value=ok]'); pg.wait_for_timeout(1500)
    check('Where to find it: Wildseed Farms' in pg.inner_text('main'), 'Edit saves where to find it')
    pg.locator('.wl-item', has_text='Texas bluebonnet').locator('[data-act=wlgot]').click(); pg.wait_for_timeout(1500)
    check('Got them (1)' in pg.inner_text('main') and 'Wanted (1)' in pg.inner_text('main'), '"Got it" moves it to Got them')
    pg.screenshot(path=os.path.join(OUT, 'wishlist-2-page.png'), full_page=True)
    pg.locator('.wl-item', has_text='Swiss cheese').locator('[data-act=wlrm]').click(); pg.wait_for_timeout(500)
    pg.locator('#dlg button', has_text='Take it off the list').click(); pg.wait_for_timeout(1500)
    check(pg.locator('.wl-item').count() == 1, '"Take it off the list" asks first, then removes it')
    check(any(x['action_word'] for x in call('GET', '/api/audit?kind=library')[1]), 'changes are in the Audit log')
    # the photo download by area (owner; 1.28.0, see places_check.py for the whole download)
    pg.goto(LOCAL + '/#/library'); pg.wait_for_timeout(3000)
    check(pg.locator('form[data-form=libareafind]').is_visible(), 'the owner gets "Add an area" for photos for offline use')
    pg.locator('#lib-pre').screenshot(path=os.path.join(OUT, 'wishlist-3-download.png'))
    # a viewer
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    vw.on('pageerror', lambda e: errs.append(str(e)))
    vw.goto(TS + '/#/species/Lupinus%20texensis'); vw.wait_for_timeout(2500)
    check('Sow in fall.' in vw.inner_text('main') and not vw.locator('.sp-notes-edit').is_visible() and vw.locator('[data-act=spwish]').count() == 0, 'a viewer reads the notes and wishlist, without the edit controls')
    vw.goto(TS + '/#/wishlist'); vw.wait_for_timeout(2000)
    check(vw.locator('.wl-item').count() == 1 and not vw.locator('[data-act=wlgot]').is_visible(), 'and sees the wishlist without its buttons')
    vw.goto(TS + '/#/library'); vw.wait_for_timeout(2500)
    check(vw.locator('form[data-form=libareafind]').count() == 0, 'and has no photo download controls')
    # phone
    ph = b.new_page(viewport={'width': 390, 'height': 844})
    ph.add_init_script("localStorage.setItem('plantdb.editor','Wish Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    for u in ('/#/wishlist', '/#/species/Lupinus%20texensis'):
        ph.goto(LOCAL + u); ph.wait_for_timeout(2500)
        check(ph.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'{u}: no sideways scrolling on a phone with the largest text')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
