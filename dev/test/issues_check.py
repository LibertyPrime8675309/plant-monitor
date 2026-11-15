"""Checks the Issue tracker and Check for updates (1.58.0; asked for by Ethan on November 15, 2026): Report a problem at the foot of
Navigation and on Settings, for everyone; what a report carries; the owner's Issue tracker page; a report written offline; and the
Check for updates window beside the version on Settings and at the foot of Navigation.
Start the mock server with a fresh data folder (MOCK_TS=1), then: python3 dev/test/issues_check.py [http://127.0.0.1:8080]
Screenshots: dev/tmp/shots/issues-*.png"""
import io, json, os, sys, urllib.error, urllib.request
from PIL import Image
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from waits import until
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = BASE.rsplit(':', 1)[0] + ':' + os.environ.get('PLANTDB_TS_PORT', '8081')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan Schmidtke'}
G = {'Tailscale-User-Login': 'sam@example.net', 'Tailscale-User-Name': 'Sam Rivera'}
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, base=BASE, headers=None):
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None, headers={'Content-Type': 'application/json', 'X-Editor': 'Issues Test', **(headers or {})}, method=m)
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'null')
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b'null')
def png(col=(200, 220, 210)):
    b = io.BytesIO(); Image.new('RGB', (900, 600), col).save(b, 'PNG'); return b.getvalue()
issues = lambda: call('GET', '/api/issues')[1]['issues']
VERSION = call('GET', '/api/version')[1]['version']
# no name of a card, a button or a tag may be broken inside a word (the fault of 128's Small cards and 129's names)
BROKEN = """sel => [...document.querySelectorAll(sel)].filter(el => el.offsetParent).reduce((n, el) => {
  const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT); let bad = 0, node;
  while ((node = w.nextNode())) { const t = node.textContent; let last = null;
    for (let i = 0; i < t.length; i++) { const r = document.createRange(); r.setStart(node, i); r.setEnd(node, i + 1); const b = r.getBoundingClientRect(); if (!b.width) continue;
      if (last !== null && b.top > last + 4 && i > 0 && /\\S/.test(t[i - 1]) && /\\S/.test(t[i]) && !/[-\\/.:,(]/.test(t[i - 1])) bad++; last = b.top; } }
  return n + bad; }, 0)"""

call('GET', '/api/me', base=TS, headers=E)             # the first person through Tailscale owns the record; Sam can only view
check(call('GET', '/api/me', base=TS, headers=G)[1]['role'] == 'viewer' and issues() == [], 'a fresh record: Sam can only view, and there are no reports')

with sync_playwright() as pw:
    b = pw.chromium.launch()
    def page(base=BASE, h=None, vw=(1707, 960), disp=None, **kw):       # his larger monitor at 150%
        c = b.new_context(viewport={'width': vw[0], 'height': vw[1]}, extra_http_headers=h or {}, **kw)
        c.add_init_script("if (!localStorage.getItem('plantdb.editor')) localStorage.setItem('plantdb.editor','Issues Test'); if (!localStorage.getItem('plantdb.display')) localStorage.setItem('plantdb.display', JSON.stringify(%s))" % json.dumps(disp or {}))
        pg = c.new_page(); pg.on('pageerror', lambda e: errs.append(str(e))); pg.on('console', lambda m: m.type == 'error' and 'Failed to load resource' not in m.text and 'fetching the script' not in m.text and errs.append(m.text))   # the mock's Tailscale port refuses the service worker's own file, which carries no sign-in
        return c, pg
    def opened(pg, sel, ms=15000): return until(pg, lambda: pg.locator('dialog[open] ' + sel).count() > 0, ms)
    def closed(pg): return until(pg, lambda: pg.locator('dialog[open]').count() == 0)

    # ---- the owner, on a monitor: where the buttons are
    ctx, pg = page()
    ctx.grant_permissions(['clipboard-read', 'clipboard-write'], origin=BASE)
    pg.goto(BASE + '/#/settings')
    check(until(pg, lambda: pg.locator('#iss-set').count() == 1), 'Settings has a card "Problems and ideas"')
    check(pg.locator('.set-ver [data-act=rlcheck]').is_visible() and VERSION in pg.locator('.set-ver').inner_text(), 'Check for updates is beside the version number on Settings')
    check(pg.locator('#iss-set [data-act=issreport]').is_visible() and '(0 open)' in pg.locator('#iss-set a[href="#/issues"]').inner_text(), 'the card has Report a problem, and for the owner the Issue tracker with how many are open')
    foot = pg.locator('#sn-foot')
    check(foot.locator('#report-btn').is_visible() and foot.locator('#upcheck-btn').is_visible() and foot.locator('#display-btn').is_visible(), 'the foot of Navigation has Report a problem, Check for updates and Display')
    check(not pg.locator('#report-top').is_visible() and pg.locator('#page-foot #sn-more').count() == 0, 'on a page with Navigation they are nowhere else')
    check(pg.locator('#sub-nav a[href="#/issues"]').is_visible(), 'the Settings row of pages lists the Issue tracker for the owner')
    pg.screenshot(path=f'{OUT}/issues-1-settings.png', full_page=True)
    top = pg.evaluate("document.querySelector('header.top').offsetHeight")
    pg.goto(BASE + '/#/plants')
    check(until(pg, lambda: pg.evaluate("document.documentElement.dataset.navempty") == '1' and pg.locator('#page-foot #report-btn').is_visible()), 'a wide page with no Navigation has the pair at the foot of the page')
    check(pg.locator('#report-top').is_visible() and pg.locator('#report-top').text_content().strip() == 'Report a problem' and pg.locator('#report-top .sr').text_content() == ' a problem' and pg.locator('#page-foot #upcheck-btn').is_visible(),
          'and "Report" in the top bar beside Display (read out as Report a problem)')
    check(pg.evaluate("document.querySelector('header.top').offsetHeight") <= top + 24, 'the top bar is no taller for it')
    pg.set_viewport_size({'width': 1366, 'height': 768}); pg.wait_for_timeout(800)
    tall = pg.evaluate("document.querySelector('header.top').offsetHeight")
    pg.evaluate("document.getElementById('report-top').remove(); window.dispatchEvent(new Event('resize'))"); pg.wait_for_timeout(800)
    check(pg.evaluate("document.querySelector('header.top').offsetHeight") == tall and pg.locator('#page-foot #report-btn').is_visible(), 'in a narrower window, where the top bar has no room, "Report" stays out of it and the foot of the page still has the pair')
    pg.set_viewport_size({'width': 1707, 'height': 960}); pg.reload(); until(pg, lambda: pg.locator('#page-foot #report-btn').is_visible())
    box = pg.locator('#page-foot').bounding_box(); last = pg.evaluate("(() => { const m = document.querySelector('#app'); const k = [...m.children].filter(x => x.offsetParent); return k[k.length - 1].getBoundingClientRect().bottom + scrollY; })()")
    check(box and box['y'] + pg.evaluate('scrollY') >= last - 1, 'the pair at the foot of the page sits below the page, not over it')
    pg.evaluate("window.scrollTo(0, document.documentElement.scrollHeight)"); pg.wait_for_timeout(300); pg.screenshot(path=f'{OUT}/issues-2-page-foot.png')

    # ---- a report from a plant's page
    pg.goto(BASE + '/#/plant/P-006')
    until(pg, lambda: pg.locator('#sn-list a').count() > 3)
    pg.locator('#sn-list a').nth(2).click(); pg.wait_for_timeout(700)
    section = pg.locator('#sn-list a').nth(2).inner_text().strip(); title = pg.locator('#app h1').inner_text().strip()
    pg.click('#report-btn')
    check(opened(pg, '.iss-dlg') and pg.evaluate("document.activeElement.name") == 'notes', 'Report a problem opens a window, with the notes box ready to type in')
    check(pg.locator('#dlg').get_attribute('aria-labelledby') and pg.locator('#dlg h2').inner_text() == 'Report a problem', 'the window is named by its heading')
    check(title in pg.locator('.iss-dlg label.f small').first.inner_text() and section in pg.locator('.iss-dlg label.f small').first.inner_text(), f'it says which page and section it is about ({title}, {section})')
    pg.click('.iss-dlg button[type=submit]')
    check(until(pg, lambda: 'Write what happened' in pg.locator('#iss-msg').inner_text()) and pg.locator('dialog[open]').count() == 1, 'sending it empty is refused in words, and the window stays')
    pg.locator('.iss-dlg input[name=device]').press('Enter')
    check(until(pg, lambda: 'Write what happened' in pg.locator('#iss-msg').inner_text()) and pg.locator('dialog[open] .iss-dlg').count() == 1, 'Enter in the name box does not close the window unsent')
    pg.click('.iss-sent summary')
    sent = pg.locator('.iss-sent .iss-dl').inner_text()
    check(all(w in sent for w in ('Page', 'Version of the app on this device', VERSION, 'Account', 'Kind of device', 'Window', '1707 by 960', 'Text size', 'Display: contrast', 'Display: theme', 'Opened as', 'Online')),
          'the folded list shows everything that is sent: page, version, account, device, window, text size, Display settings')
    pg.fill('.iss-dlg textarea[name=notes]', 'High contrast in the Light theme hardly changes anything.\nOnly the lines get darker. Is that meant?')
    pg.set_input_files('.iss-dlg input[type=file]', [{'name': 'what I saw.png', 'mimeType': 'image/png', 'buffer': png()}])
    pg.fill('.iss-dlg input[name=device]', 'Desk monitor')
    pg.screenshot(path=f'{OUT}/issues-3-report.png')
    pg.click('.iss-dlg button[type=submit]')
    check(closed(pg) and until(pg, lambda: 'Report sent (number 1)' in pg.locator('#toasts').inner_text()), 'Send the report closes the window and says it was sent, with its number')
    L = issues(); x = L[0] if L else {}
    check(len(L) == 1 and x['page'] == '#/plant/P-006' and x['page_title'] == title and x['section'] == section and x['notes'].startswith('High contrast') and '\n' in x['notes'], 'the record has the report: its page, its section and the words as written')
    check(x.get('page_version') == VERSION and x.get('server_version') == VERSION and x.get('device') == 'Desk monitor' and x.get('name') == 'Issues Test' and x.get('role') == 'owner' and x.get('status') == 'open',
          'with the page\'s version, the server\'s version, the device name, who sent it and "open"')
    check(x.get('info', {}).get('Window', '').startswith('1707 by 960') and 'Browser says' in x.get('info', {}) and x.get('settings', {}).get('Display: size', '').startswith('115') and len(x.get('photos', [])) == 1,
          'and the device details, the Display settings and the picture')
    pg.click('#report-btn'); opened(pg, '.iss-dlg')
    check(pg.locator('.iss-dlg input[name=device]').input_value() == 'Desk monitor', 'the device name is remembered on the device for the next report')
    pg.click('[data-act=isscancel]'); check(closed(pg) and len(issues()) == 1, 'Cancel closes the window and sends nothing')
    pg.goto(BASE + '/#/offline'); until(pg, lambda: pg.locator('input[data-f=offdev]').count() == 1)
    check(pg.locator('input[data-f=offdev]').input_value() == 'Desk monitor', 'it is the same name the Offline page keeps')

    # ---- an error the app showed is carried by the next report
    pg.goto(BASE + '/#/settings'); until(pg, lambda: pg.locator('#iss-set').count() == 1)
    pg.evaluate("toast('The weather could not be loaded', true)")
    pg.click('#iss-set [data-act=issreport]'); opened(pg, '.iss-dlg'); pg.click('.iss-sent summary')
    check('Last errors shown' in pg.locator('.iss-sent .iss-dl').inner_text() and 'The weather could not be loaded' in pg.locator('.iss-sent .iss-dl').inner_text(), 'a report lists the last errors the app showed on this device')
    pg.click('[data-act=isscancel]'); closed(pg)

    # ---- a person who can only view sends one too
    vc, vw = page(TS, G)
    vw.goto(TS + '/#/settings')
    check(until(vw, lambda: vw.locator('#iss-set').count() == 1) and vw.locator('#iss-set a[href="#/issues"]').count() == 0 and not vw.locator('#sub-nav a[href="#/issues"]').is_visible(), 'a person who can only view sees the card, and no Issue tracker link anywhere')
    vw.click('#report-btn')
    check(opened(vw, '.iss-dlg') and vw.locator('.iss-dlg input[type=file]').is_visible() and 'Ethan Schmidtke' in vw.locator('.iss-dlg p').first.inner_text(), 'their window has the picture box too, and says the report goes to the owner')
    vw.fill('.iss-dlg textarea[name=notes]', 'The watering list is hard to read in the dark theme.')
    vw.set_input_files('.iss-dlg input[type=file]', [{'name': 'dark.png', 'mimeType': 'image/png', 'buffer': png((20, 30, 40))}])
    vw.click('.iss-dlg button[type=submit]')
    check(closed(vw) and until(vw, lambda: len(issues()) == 2), 'their report is sent')
    y = issues()[0]
    check(y['login'] == 'sam@example.net' and y['name'] == 'Sam Rivera' and y['role'] == 'viewer' and y['via'] == 'tailscale' and y['info'].get('Connected', '').startswith('Through Tailscale'), 'it names their account, their role and that it came through Tailscale')
    vw.goto(TS + '/#/issues')
    check(until(vw, lambda: 'Only Ethan Schmidtke can open the Issue tracker' in vw.locator('#app').inner_text()) and vw.locator('.iss-card').count() == 0, 'the Issue tracker page tells them it is the owner\'s, and shows no report')
    st = call('GET', '/api/issues', base=TS, headers=G)[0]; pic = call('GET', f"/api/issues/{y['id']}/photo/{y['photos'][0]['id']}", base=TS, headers=G)[0]
    check(st == 403 and pic == 403, 'the server refuses them the reports and the pictures, their own included')
    vc.close()

    # ---- Today tells the owner, once
    pg.goto(BASE + '/#/')
    check(until(pg, lambda: pg.locator('#iss-today').count() == 1) and 'A new problem report is waiting' in pg.locator('#iss-today').inner_text(), 'Today tells the owner that a new report from someone else is waiting')
    pg.screenshot(path=f'{OUT}/issues-4-today.png')
    pg.click('#iss-today a[href="#/issues"]')
    check(until(pg, lambda: pg.locator('.iss-card').count() == 2) and pg.evaluate("document.activeElement.tagName") == 'H1', 'its button opens the Issue tracker, with both reports, newest first')
    check(until(pg, lambda: call('GET', '/api/issues?brief=1')[1]['fresh'] == 0), 'opening the page marks them as seen')
    pg.goto(BASE + '/#/'); until(pg, lambda: pg.locator('.td-jumps, #today-quiet, h1').count() > 0); pg.wait_for_timeout(1500)
    check(pg.locator('#iss-today').count() == 0, 'and Today says no more about them')

    # ---- the Issue tracker page
    pg.goto(BASE + '/#/issues'); until(pg, lambda: pg.locator('.iss-card').count() == 2)
    c1 = pg.locator('#iss-1'); c2 = pg.locator('#iss-2')
    check('Report 2' in pg.locator('.iss-card h3').first.inner_text() and 'Desk monitor' in c1.inner_text() and 'Sam Rivera' in c2.inner_text() and 'Can view only' in c2.inner_text(), 'each card says who sent it, their role and the device')
    check(c1.locator('.iss-notes').inner_text().count('\n') == 1 and c1.locator('.iss-pics img').count() == 1 and c1.locator(f'a[href="#/plant/P-006"]').count() == 1, 'the words keep their lines, the picture is shown, and the page is a link')
    check(until(pg, lambda: pg.evaluate("document.querySelector('#iss-1 .iss-pics img').naturalWidth") == 900), 'the picture loads')
    c1.locator('.iss-more summary').click()
    more = c1.locator('.iss-more .iss-dl').inner_text()
    check(all(w in more for w in ('Account', 'Version of the app on the device', 'Version the server was running', 'Kind of device', 'Display: contrast')), 'the fold has the account, both versions, the device details and the settings')
    pg.screenshot(path=f'{OUT}/issues-5-tracker.png', full_page=True)
    check(pg.evaluate(BROKEN, '.iss-card h3, .iss-card .tag, .iss-card .btn, .iss-bar .btn') == 0 and pg.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth"), 'no name is broken inside a word, and nothing scrolls sideways')
    c1.locator('select[data-act=issstatus]').select_option('fixed')
    check(until(pg, lambda: pg.locator('#iss-1 input[data-act=issfixed]').count() == 0 and pg.locator('#iss-1').count() == 0), 'a report set to Fixed leaves the list of open ones')
    check('1 of 2 reports' in pg.locator('.iss-count').inner_text(), 'and the count says 1 of 2')
    pg.select_option('select[data-act=issshow]', 'all')
    check(until(pg, lambda: pg.locator('#iss-1 input[data-act=issfixed]').count() == 1), 'Show: All brings it back, with a box for the version it was fixed in')
    f = pg.locator('#iss-1 input[data-act=issfixed]'); f.fill('soon'); f.press('Tab')
    check(until(pg, lambda: 'three numbers' in pg.locator('#toasts').inner_text()), 'a version that is not three numbers is refused in words')
    until(pg, lambda: pg.locator('#iss-1 input[data-act=issfixed]').input_value() == '')
    f = pg.locator('#iss-1 input[data-act=issfixed]'); f.fill('1.58.0'); f.press('Tab')
    check(until(pg, lambda: pg.locator('#iss-1 .iss-st').inner_text() == 'Fixed in 1.58.0') and until(pg, lambda: issues()[1]['fixed_in'] == '1.58.0'), 'the version is saved and the tag says "Fixed in 1.58.0"')
    n = pg.locator('#iss-1 textarea[data-act=issnote]'); n.fill('The light theme was already at full contrast.'); n.press('Tab')
    check(until(pg, lambda: issues()[1]['owner_notes'] == 'The light theme was already at full contrast.') and until(pg, lambda: 'notes on report 1 are saved' in pg.locator('#iss-say').inner_text()), 'the owner\'s notes are saved on leaving the box, and it says so')
    pg.fill('input[data-f=issq]', 'dark theme')
    check(until(pg, lambda: pg.locator('.iss-card').count() == 1 and pg.locator('#iss-2').count() == 1), 'the search box narrows the list as you type')
    pg.fill('input[data-f=issq]', ''); until(pg, lambda: pg.locator('.iss-card').count() == 2)
    pg.locator('#iss-1 [data-act=isscopy]').click()
    check(until(pg, lambda: 'Copied report 1' in pg.locator('#iss-say').inner_text()), 'Copy for Claude says what it copied')
    clip = pg.evaluate('navigator.clipboard.readText()')
    check(all(w in clip for w in ('Report 1: Fixed in 1.58.0', 'High contrast in the Light theme', 'Device: Desk monitor', 'the page was ' + VERSION, 'Window: 1707 by 960', 'Display: contrast', "The owner's notes", '1 picture attached')), 'the copied text has the report, the versions, the device, the settings and the notes')
    pg.click('.iss-bar [data-act=isscopy]')
    check(until(pg, lambda: 'Copied 2 reports' in pg.locator('#iss-say').inner_text()) and 'Report 2: Open' in pg.evaluate('navigator.clipboard.readText()'), 'Copy the ones shown copies them all')
    pg.locator('#iss-2 [data-act=issdel]').click()
    check(opened(pg, 'form') and 'Remove report 2?' in pg.locator('#dlg h2').inner_text(), 'Remove asks first')
    pg.click('#dlg button[value=ok]')
    check(until(pg, lambda: pg.locator('#iss-2').count() == 0 and len(issues()) == 1), 'and then the report is gone')

    # ---- a report written with no connection waits on the device
    ctx.set_offline(True)
    pg.evaluate("window.dispatchEvent(new Event('offline'))"); pg.wait_for_timeout(300)
    pg.click('.iss-bar [data-act=issreport]'); opened(pg, '.iss-dlg')
    pg.fill('.iss-dlg textarea[name=notes]', 'Written in the garden with no signal.')
    pg.click('.iss-dlg button[type=submit]')
    check(closed(pg) and until(pg, lambda: 'Kept on this device' in pg.locator('#toasts').inner_text()), 'offline, the report is kept on the device, and it says so')
    check(len(issues()) == 1, 'nothing has reached the record yet')
    waiting = pg.evaluate("offOps().then(o => o.map(offWords))")
    check(waiting == ['A problem report: Written in the garden with no signal.'], 'the Offline page will name it among the changes waiting')
    ctx.set_offline(False); pg.evaluate("window.dispatchEvent(new Event('online')); offSync()")
    check(until(pg, lambda: len(issues()) == 2, 30000) and issues()[0]['notes'] == 'Written in the garden with no signal.' and issues()[0]['device'] == 'Desk monitor', 'back online it is sent by itself, once')
    pg.wait_for_timeout(1500); check(len(issues()) == 2 and pg.evaluate("offOps().then(o => o.length)") == 0, 'and nothing is left waiting')

    # ---- Check for updates
    pg.goto(BASE + '/#/settings'); until(pg, lambda: pg.locator('.set-ver [data-act=rlcheck]').count() == 1)
    pg.click('.set-ver [data-act=rlcheck]')
    check(opened(pg, '#rl-check-say') and 'This device is up to date' in pg.locator('#rl-check-say').inner_text(), 'Check for updates on Settings opens a window that says this device is up to date')
    t = pg.locator('.rl-check').inner_text()
    check(t.count('Version ' + VERSION) == 2 and 'The newest release' in t and 'turned off on this install' in t, 'it shows the version on this device, the version the server runs, and for the owner the newest release (not asked in a test)')
    check(pg.locator('#rl-check-live').inner_text().startswith('This device is up to date') and pg.evaluate("document.activeElement.dataset.act") == 'reloadnow', 'the answer is said once to screen readers, and the focus is on Reload the app')
    pg.screenshot(path=f'{OUT}/issues-6-check.png')
    pg.click('.rl-check-dlg button[value=ok]'); closed(pg)
    pg.evaluate("window.rlServerVersion = async () => '9.9.9'")                # as on a page left open since before an update
    pg.click('#upcheck-btn')
    check(opened(pg, '#rl-check-say') and until(pg, lambda: 'This device is behind' in pg.locator('#rl-check-say').inner_text()), 'from the foot of Navigation, with a newer server: "This device is behind"')
    go = pg.locator('.rl-check-dlg [data-act=reloadnow]')
    check(go.inner_text() == 'Reload the app to open version 9.9.9' and 'ghost' not in go.get_attribute('class'), 'and the main button reloads the app to open that version')
    pg.screenshot(path=f'{OUT}/issues-7-behind.png')
    pg.evaluate("window.rlServerVersion = async () => null")
    pg.click('.rl-check-dlg [data-act=rlcheck]')
    check(until(pg, lambda: 'The plant server did not answer' in pg.locator('#rl-check-say').inner_text()), 'Check again, with a server that does not answer, says so')
    pg.evaluate("window.STAYED = 1"); pg.click('.rl-check-dlg [data-act=reloadnow]')
    check(until(pg, lambda: pg.evaluate("typeof window.STAYED") == 'undefined' and pg.locator('.set-ver').count() == 1), 'Reload the app reloads it')
    ctx.close()

    # ---- an editor: no newest release, and who installs
    call('PUT', '/api/people', {'login': 'sam@example.net', 'role': 'editor'})
    ec, ed = page(TS, G)
    ed.goto(TS + '/#/settings'); until(ed, lambda: ed.locator('.set-ver [data-act=rlcheck]').count() == 1)
    ed.click('.set-ver [data-act=rlcheck]')
    check(opened(ed, '#rl-check-say') and 'The newest release' not in ed.locator('.rl-check').inner_text() and 'installed on the plant server by Ethan Schmidtke' in ed.locator('#rl-check-new').inner_text(), 'for someone who is not the owner the window leaves out the newest release and says who installs new versions')
    ec.close()

    # ---- a phone, at the usual text and at the largest
    for size, tag in (('115', 'usual'), ('190', 'largest')):
        pc, ph = page(vw=(390, 844), disp={'size': size}, has_touch=True, is_mobile=True)
        ph.goto(BASE + '/#/settings'); until(ph, lambda: ph.locator('#iss-set').count() == 1)
        ph.click('#nav-tab'); until(ph, lambda: ph.locator('#sidenav').is_visible())
        inside = ph.evaluate("document.getElementById('sn-more').parentNode.id")
        check(inside == ('sn-foot' if size == '115' else 'sidenav'), f'phone, {tag} text: the pair is ' + ('held at the foot of Navigation with Display' if size == '115' else 'after the list of sections, so the list keeps its room'))
        ph.locator('#report-btn').scroll_into_view_if_needed()
        check(ph.locator('#report-btn').is_visible() and ph.locator('#upcheck-btn').is_visible() and ph.evaluate(BROKEN, '#sn-more .btn') == 0, f'phone, {tag} text: both buttons are there, no word broken')
        if size == '190':
            lines = ph.evaluate("(() => { const l = document.getElementById('sn-list'), n = document.getElementById('sidenav'), f = document.getElementById('sn-foot'); return (f.getBoundingClientRect().top - l.getBoundingClientRect().top) / l.querySelector('a').offsetHeight; })()")
            ph.evaluate("document.getElementById('sidenav').scrollTop = 0"); ph.wait_for_timeout(200)
            seen = ph.evaluate("(() => { const f = document.getElementById('sn-foot').getBoundingClientRect().top; return [...document.querySelectorAll('#sn-list a')].filter(a => a.getBoundingClientRect().bottom <= f + 1).length; })()")
            check(seen >= 4, f'phone, largest text: Navigation still shows {seen} sections above Display before any scrolling')
        ph.screenshot(path=f'{OUT}/issues-8-phone-nav-{tag}.png')
        ph.click('#report-btn'); opened(ph, '.iss-dlg')
        check(ph.evaluate("(() => { const d = document.getElementById('dlg'); return d.scrollWidth <= d.clientWidth + 1 && document.documentElement.scrollWidth <= document.documentElement.clientWidth; })()") and ph.evaluate(BROKEN, '.iss-dlg label.f, .iss-dlg .btn, .iss-dlg h2') == 0,
              f'phone, {tag} text: the report window fits, with no word broken')
        inview = lambda sel: ph.evaluate("sel => { const b = document.querySelector(sel).getBoundingClientRect(); return b.top >= 0 && b.top < innerHeight - 40; }", sel)
        if size == '115': check(inview('.iss-dlg button[type=submit]') and inview('.iss-dlg textarea[name=notes]'), 'phone, usual text: the notes box and Send the report are both in view when the window opens')
        else:
            check(inview('.iss-dlg textarea[name=notes]'), 'phone, largest text: the notes box is in view when the window opens')
            ph.locator('.iss-dlg button[type=submit]').scroll_into_view_if_needed()
            check(inview('.iss-dlg button[type=submit]') and ph.evaluate("getComputedStyle(document.querySelector('.iss-dlg .row')).position") == 'static', 'phone, largest text: Send the report ends the form (it is not held over the notes box)')
        ph.screenshot(path=f'{OUT}/issues-9-phone-report-{tag}.png')
        ph.click('[data-act=isscancel]'); closed(ph)
        ph.goto(BASE + '/#/issues'); until(ph, lambda: ph.locator('.iss-card').count() >= 1)
        ph.select_option('select[data-act=issshow]', 'all'); until(ph, lambda: ph.locator('.iss-card').count() == 2)
        check(ph.evaluate("document.documentElement.scrollWidth <= document.documentElement.clientWidth") and ph.evaluate(BROKEN, '.iss-card h3, .iss-card .tag, .iss-card .btn, .iss-bar .btn, .iss-card label.f') == 0, f'phone, {tag} text: the Issue tracker fits, with no word broken')
        ph.screenshot(path=f'{OUT}/issues-10-phone-tracker-{tag}.png', full_page=True)
        pc.close()
    b.close()

check(not errs, 'no errors in the browser: ' + '; '.join(errs[:3]))
print('\n%d failed' % len(fails) if fails else '\nall passed')
sys.exit(1 if fails else 0)
