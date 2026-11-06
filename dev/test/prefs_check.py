"""Checks 1.29.0: settings that follow you, and the new top bar. The Plants filters and other choices are saved for your sign-in and
show up on another device; Display settings stay on each device unless "Use these on every device I sign in on" is ticked; a viewer
keeps their own; the top bar has six sections with a row of their pages, and the version is always on screen.
Start the mock server with a fresh data folder (MOCK_TS=1), then:  python3 dev/test/prefs_check.py"""
import json, os, urllib.request, urllib.error
from playwright.sync_api import sync_playwright
LOCAL, TS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081'
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(method, u, body=None, h=None, base=LOCAL):
    req = urllib.request.Request(base + u, data=None if body is None else json.dumps(body).encode(), method=method,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Prefs Test', **(h or {})})
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'{}')
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b'{}')
        except ValueError: return e.code, {}
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', h=E, base=TS); call('GET', '/api/me', h=V, base=TS)
check(call('PUT', '/api/me/prefs', {'filters': '{"q":"aloe"}'}, h=V, base=TS)[0] == 200, 'someone who can only view can still keep their own settings')
check(call('GET', '/api/me/prefs', h=E, base=TS)[1]['prefs'].get('filters') is None, 'and they are not anyone else\'s')
check(call('PUT', '/api/me/prefs', {'BAD KEY': 'x'}, h=E, base=TS)[0] == 400, 'odd setting names are refused')

with sync_playwright() as p:
    b = p.chromium.launch()
    def device(w, h):
        ctx = b.new_context(viewport={'width': w, 'height': h}, extra_http_headers=E)
        ctx.add_init_script("localStorage.setItem('plantdb.editor','Ethan');localStorage.setItem('plantdb.morefilters','1')")
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); return pg
    a = device(1920, 1080)
    a.goto(TS + '/#/plants'); a.wait_for_timeout(3000)
    check(a.locator('#main-nav a[data-sec]').count() == 6 and a.locator('#main-nav a[aria-current=page]').inner_text().strip() == 'Plants', 'the top bar has six sections, with Plants marked')
    check([x.strip() for x in a.locator('#sub-nav a').all_inner_texts()][:4] == ['All plants', 'Groups', 'Add plants', 'Mushrooms'], 'Plants has its pages on a second row, Mushrooms among them')
    check(a.locator('#app-ver').is_visible() and a.locator('#app-ver').inner_text().startswith('v'), 'the version is on screen')
    a.goto(TS + '/#/settings'); a.wait_for_timeout(1500)
    check(a.locator('#app-ver').is_visible() and a.locator('#debug-btn').count() == 1, 'Settings has Debug, and the version is still on screen')
    a.goto(TS + '/#/wishlist'); a.wait_for_timeout(2000)
    check(a.locator('#main-nav a[aria-current=page]').inner_text().strip() == 'Discover' and a.locator('#sub-nav a[aria-current=page]').inner_text().strip().startswith('Wishlist'), 'Wishlist has its own link under Discover')
    check(a.locator('#place-btn .pl-l').inner_text().strip() == 'Home:', 'the Location button says Home')
    # a filter on one device follows to another
    a.goto(TS + '/#/plants'); a.wait_for_timeout(2500)
    a.locator('select[data-f=health]').select_option('Good'); a.wait_for_timeout(1500)
    check('"health":"Good"' in (call('GET', '/api/me/prefs', h=E, base=TS)[1]['prefs'].get('filters') or ''), 'a Plants filter is saved for your sign-in')
    # Display: this device only by default
    a.evaluate("window.PlantPrefs.set('size', '160')"); a.wait_for_timeout(1500)
    check(not any(k.startswith('display.') for k in call('GET', '/api/me/prefs', h=E, base=TS)[1]['prefs']), 'text size stays on this device unless you choose otherwise')
    a.evaluate("window.PlantSync.share('text', true)"); a.wait_for_timeout(1500)
    pr = call('GET', '/api/me/prefs', h=E, base=TS)[1]['prefs']
    check('"size":"160"' in (pr.get('display.text') or ''), 'ticking "Use these on every device" shares that part')
    c2 = device(1280, 900)
    c2.goto(TS + '/#/plants'); c2.wait_for_timeout(3000)
    for _ in range(20):                       # it starts again once with the synced settings: give that a moment
        if c2.locator('select[data-f=health]').count() and c2.locator('select[data-f=health]').input_value() == 'Good': break
        c2.wait_for_timeout(500)
    check(c2.locator('select[data-f=health]').input_value() == 'Good', 'another device opens with the same Plants filter')
    check(c2.evaluate("document.documentElement.dataset.size") != '160', 'but keeps its own text size, because it has not ticked the box')
    c2.evaluate("window.PlantSync.share('text', true)"); c2.wait_for_timeout(1500)
    check(c2.evaluate("document.documentElement.dataset.size") == '160', 'when it ticks the box too, it takes the shared text size')
    c2.locator('select[data-f=health]').select_option(''); c2.wait_for_timeout(1500)
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All prefs checks passed' if not fails else f'{len(fails)} prefs check(s) failed'))
raise SystemExit(1 if fails else 0)
