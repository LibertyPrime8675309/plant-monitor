"""Checks 1.49.0 (PLAN.md step 4c): the plant-sitter sheet by link. An editor makes a link on the sitter page, copies it, a sitter
with no sign-in opens it in a browser of their own, reads the sheet in large print, ticks a box, and the tick shows on the printout
in the app. A viewer sees no "Share the sheet by link". The link taken down answers 410 in plain words. Nothing but the sheet is
reachable through it.
1.58.0: the sitter arrives the way a Funnel visitor really does: on this computer's own port (8080, where every other request is
the owner's), marked by Tailscale with the Tailscale-Funnel-Request header. Before, this check used the Tailscale port with no
identity, which is not where the README's Funnel command sends people, and so it missed that /share itself took pictures from anyone.
Start the mock server with a fresh data folder (MOCK_TS=1), then:  python3 dev/test/sitlink_check.py [base]
Screenshots: dev/tmp/shots/sitlink-*.png"""
import json, os, sys, urllib.request, urllib.error
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = BASE.replace(':8080', ':8081')                     # the Tailscale port: people with an identity
FUN = {'Tailscale-Funnel-Request': '?1'}                # what Tailscale adds to every request that came in from the internet through Funnel
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails = []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, base=BASE, headers=None):
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Link Test', **(headers or {})}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def status(url, base=TS, headers=None, method='GET', data=None):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k): return None
    try:
        with urllib.request.build_opener(NoRedirect).open(urllib.request.Request(base + url, headers=headers or {}, method=method, data=data)) as r: return r.status
    except urllib.error.HTTPError as e: return e.code
def visitor(url, method='GET', data=None, more=None):
    """As someone on the internet: this computer's own port, with Tailscale's Funnel mark."""
    return status(url, base=BASE, headers={**FUN, **(more or {})}, method=method, data=data)

OWN = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
VIEW = {'Tailscale-User-Login': 'aunt@example.com', 'Tailscale-User-Name': 'Aunt May'}
call('GET', '/api/me', base=TS, headers=OWN)            # the first person in through Tailscale is the owner
call('GET', '/api/me', base=TS, headers=VIEW)           # the second can only look
today = date.fromisoformat(call('GET', '/api/water')['today'])
call('POST', '/api/care', {'kind': 'water', 'plants': [f'P-{n:03d}' for n in range(1, 40)], 'done_on': (today - timedelta(days=2)).isoformat()})
a, z = (today + timedelta(days=1)).isoformat(), (today + timedelta(days=5)).isoformat()

with sync_playwright() as p:
    b = p.chromium.launch()
    # --- the owner, on the sitter page: makes a link
    pg = b.new_page(viewport={'width': 1280, 'height': 900}); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.set_extra_http_headers(OWN)
    pg.goto(TS + '/sitter.html'); pg.wait_for_selector('.ps-doc')
    pg.get_by_label('First day').fill(a); pg.get_by_label('Last day').fill(z); pg.wait_for_timeout(800)
    pg.get_by_label('Printed at the top', exact=False).fill('The key is under the mat.'); pg.wait_for_timeout(800)
    share = pg.locator('#ps-share')
    check(share.is_visible(), 'the owner sees "Share the sheet by link"')
    check(pg.locator('#ps-share-hint').is_visible() and 'Funnel' in pg.locator('#ps-share-hint').inner_text(), 'with no public address saved, the page says the link works at home only and names Funnel')
    pg.get_by_role('button', name='Make a link').click(); pg.wait_for_selector('.ps-linkrow'); pg.wait_for_timeout(300)
    row = pg.locator('.ps-linkrow')
    check(row.count() == 1 and 'Nothing ticked yet' in row.inner_text() and 'Not opened yet' in row.inner_text(), 'the new link is listed: nothing ticked, not opened')
    url = row.locator('.ps-url').input_value()
    check(url.startswith('http') and '/share/' in url and len(url.rsplit('/', 1)[1]) >= 30, f'the link has a long token: {url}')
    check(pg.locator('#ps-share-msg').inner_text().startswith('Link made'), 'the page says the link was made')
    check(pg.locator('.ps-tick').count() == 0 and pg.locator('.ps-box').count() > 0, 'in the app the sheet keeps its printed boxes (no live check boxes)')
    pg.screenshot(path=os.path.join(OUT, 'sitlink-owner.png'), full_page=True)
    tok = url.rsplit('/', 1)[1]

    # --- the sitter: a browser of their own, no sign-in, arriving through Funnel (this computer's own port, with Tailscale's mark)
    ctx = b.new_context(viewport={'width': 390, 'height': 844}, extra_http_headers=FUN)
    sp = ctx.new_page(); serrs = []
    sp.on('pageerror', lambda e: serrs.append(str(e))); sp.on('console', lambda m: m.type == 'error' and '404' not in m.text and serrs.append(m.text))
    sp.goto(f'{BASE}/share/{tok}'); sp.wait_for_selector('.ps-doc'); sp.wait_for_timeout(500)
    check(sp.locator('.ps-doc h2').inner_text() == 'Looking after the plants', 'the sitter sees the sheet with no sign-in')
    check('The key is under the mat.' in sp.locator('.ps-msg').inner_text(), 'the note is on it')
    check(sp.locator('.ps-day').count() == 5, 'five days, day by day')
    check(sp.locator('.ps-before').count() == 0, '"Before you go" (the owner\'s job) is left off')
    ticks = sp.locator('.ps-tick')
    check(ticks.count() > 0, f'the boxes are real check boxes ({ticks.count()})')
    unlabeled = sp.evaluate("[...document.querySelectorAll('.ps-tick')].filter(e => !e.getAttribute('aria-label')).length")
    check(unlabeled == 0, 'every box says which plant it is for')
    size = sp.evaluate("parseFloat(getComputedStyle(document.documentElement).fontSize)")
    check(size >= 21, f'large print by default ({size}px)')
    over = sp.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
    check(over <= 2, f'phone: no sideways scrolling ({over}px)')
    pics = sp.locator('.ps-pic[src]')
    if pics.count():
        ok = sp.evaluate("[...document.querySelectorAll('.ps-pic[src]')].every(i => i.getAttribute('src').startsWith('/share/'))")
        check(ok, 'photos come through the link\'s own path')
    sp.screenshot(path=os.path.join(OUT, 'sitlink-sitter-phone.png'), full_page=True)
    # tick the first box; it saves at once
    first = ticks.first
    day, code = first.get_attribute('data-day'), first.get_attribute('data-plant')
    first.check(); sp.wait_for_timeout(600)
    check(sp.locator('#sh-saved').inner_text() == 'Saved.', 'a tick says "Saved."')
    check(sp.locator('li.ps-done').count() == 1, 'the ticked line is marked done')
    sp.reload(); sp.wait_for_selector('.ps-doc'); sp.wait_for_timeout(400)
    check(sp.locator('.ps-tick').first.is_checked(), 'the tick is still there after a reload')
    # larger text, dark, high contrast: the buttons work and are remembered
    sp.get_by_role('button', name='Larger text').click(); sp.wait_for_timeout(200)
    check(sp.evaluate("parseFloat(getComputedStyle(document.documentElement).fontSize)") > size, 'Larger text makes the text larger')
    sp.get_by_role('button', name='Dark').click(); sp.wait_for_timeout(200)
    check(sp.evaluate("document.documentElement.getAttribute('data-theme')") == 'dark' and sp.get_by_role('button', name='Light').count() == 1, 'Dark turns the page dark and the button now says Light')
    sp.get_by_role('button', name='High contrast').click(); sp.wait_for_timeout(200)
    sp.screenshot(path=os.path.join(OUT, 'sitlink-sitter-dark-large.png'), full_page=False)
    sp.reload(); sp.wait_for_selector('.ps-doc')
    check(sp.evaluate("document.documentElement.getAttribute('data-theme')") == 'dark' and sp.evaluate("document.documentElement.getAttribute('data-contrast')") == 'high', 'the display choices are remembered')
    for e in serrs: check(False, f'sitter page: {e}')
    # nothing else through the link
    check(status(f'/share/{tok}/photo/not-here.jpg') == 404, 'a photo that is not on the sheet is not served')
    check(status('/api/plants') == 403, 'the Tailscale port still refuses an unknown visitor elsewhere')
    check(status('/share/' + 'x' * 32) == 404, 'a wrong token is refused')
    # 1.58.0: from the internet, a sitter link or the calendar and nothing else, on the port where everyone else is the owner
    check(visitor(f'/share/{tok}/data') == 200 and visitor(f'/share/{tok}/photo/not-here.jpg') == 404 and visitor('/share/' + 'x' * 32) == 404, 'a visitor from the internet reaches the link, and only what is on it')
    shut = {u: visitor(u) for u in ('/', '/share', '/share-in', '/api/plants', '/api/people', '/api/backups', '/healthz', '/app.js', '/sitter.html')}
    check(all(v == 404 for v in shut.values()), f'everything else is "not found" to a visitor from the internet: {shut}')
    boundary = '----plantrec'
    body = (f'--{boundary}\r\nContent-Disposition: form-data; name="photos"; filename="visitor.jpg"\r\nContent-Type: image/jpeg\r\n\r\n').encode() + open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'app', 'static', 'icon-192.png'), 'rb').read() + f'\r\n--{boundary}--\r\n'.encode()
    n0 = len(call('GET', '/api/photos/unassigned'))
    posts = {u: visitor(u, 'POST', body, {'Content-Type': f'multipart/form-data; boundary={boundary}', 'X-Editor': 'Visitor'}) for u in ('/share', '/share-in', '/api/photos')}
    check(all(v == 404 for v in posts.values()) and len(call('GET', '/api/photos/unassigned')) == n0, f'a visitor cannot send pictures in, whatever headers they add: {posts}')
    cal = call('GET', '/api/calendar/settings')['links']['local']
    check(visitor('/cal/' + cal.rsplit('/', 1)[-1]) == 200 and visitor('/cal/wrong.ics') == 404, 'the calendar link still works from the internet, and only with its own token')

    # --- back in the app: the tick shows on the printout
    pg.reload(); pg.wait_for_selector('.ps-doc'); pg.wait_for_timeout(1200)
    check(pg.locator('.ps-box.ps-ticked').count() == 1, 'the sitter\'s tick shows on the owner\'s sheet')
    check(pg.locator('li.ps-done .ps-code').first.inner_text() == code, f'on the right plant ({code})')
    pg.wait_for_selector('.ps-linkrow')
    check('1 box ticked' in pg.locator('.ps-linkrow').inner_text() and 'Last opened' in pg.locator('.ps-linkrow').inner_text(), 'the link row counts the tick and says when it was opened')
    pg.screenshot(path=os.path.join(OUT, 'sitlink-owner-ticked.png'), full_page=True)

    # --- a viewer sees no share box
    vp = b.new_page(viewport={'width': 1280, 'height': 900}); vp.set_extra_http_headers(VIEW)
    vp.goto(TS + '/sitter.html'); vp.wait_for_selector('.ps-doc'); vp.wait_for_timeout(800)
    check(not vp.locator('#ps-share').is_visible(), 'a viewer does not see "Share the sheet by link"')
    vp.close()

    # --- taking the link down
    pg.get_by_role('button', name='Take the link down').click(); pg.wait_for_timeout(800)
    check(pg.locator('.ps-linkrow').count() == 0 and 'taken down' in pg.locator('#ps-share-msg').inner_text(), 'the link is gone from the list and the page says so')
    sp.reload(); sp.wait_for_timeout(800)
    check('taken down' in sp.locator('#ps-sheet').inner_text() and sp.locator('.ps-tick').count() == 0, 'the sitter now sees "taken down" instead of the sheet')
    check(status(f'/share/{tok}') == 410 and visitor(f'/share/{tok}') == 410, 'the link answers 410')
    sp.screenshot(path=os.path.join(OUT, 'sitlink-sitter-down.png'))
    for e in errs: check(False, f'owner page: {e}')
    ctx.close(); b.close()

print(f'\n{len(fails)} failed' if fails else '\nall good')
sys.exit(1 if fails else 0)
