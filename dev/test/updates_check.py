"""Checks Updates from Claude (1.58.0; Ethan's choices of November 13 and 14, 2026): a file of changes that Claude saves on the
computer, shown plant by plant to accept or leave; Today says when one is waiting; a file is brought in once.
Start the mock server with a fresh data folder, then: python3 dev/test/updates_check.py [http://127.0.0.1:8080]
Screenshots: dev/tmp/shots/updates-*.png"""
import io, json, os, sys, tempfile, urllib.error, urllib.request, zipfile
from PIL import Image
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from waits import until
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = BASE.rsplit(':', 1)[0] + ':' + os.environ.get('PLANTDB_TS_PORT', '8081')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, base=BASE, headers=None):
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None, headers={'Content-Type': 'application/json', 'X-Editor': 'Updates Test', **(headers or {})}, method=m)
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'null')
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b'null')
def jpg(col):
    b = io.BytesIO(); Image.new('RGB', (900, 675), col).save(b, 'JPEG', quality=80); return b.getvalue()

FOLDER = call('GET', '/api/updates')[1]['folder_path']
check(bool(FOLDER) and os.path.isdir(FOLDER), 'the app sees the folder Claude saves update files in')
P = {c: call('GET', '/api/plants/' + c)[1] for c in ('P-009', 'P-012', 'P-052', 'P-010', 'P-055', 'P-016', 'P-005', 'P-014', 'P-003')}
n = lambda c: P[c]['common_name']
other_plan = 'Annual' if P['P-052']['winter_plan'] != 'Annual' else 'Hardy outside'        # not what the page says: the page was changed since the file was made
to_plan = 'Move indoors' if P['P-052']['winter_plan'] != 'Move indoors' else 'Protect outside'
to_health = 'Good' if P['P-009']['health_rating'] != 'Good' else 'Fair'
CH = [
    {'kind': 'set', 'code': 'P-009', 'name': n('P-009'), 'field': 'health_rating', 'from': P['P-009']['health_rating'], 'to': to_health, 'why': 'Five new leaves since October.'},
    {'kind': 'set', 'code': 'P-009', 'name': n('P-009'), 'field': 'health_summary', 'from': P['P-009']['health_summary'], 'to': 'Recovered. Five new leaves have opened.', 'why': 'So the page says what it looks like now.'},
    {'kind': 'set', 'code': 'P-012', 'name': n('P-012'), 'field': 'id_confidence', 'from': P['P-012']['id_confidence'], 'to': 85, 'why': 'The close-up settles it.'},
    {'kind': 'set', 'code': 'P-052', 'name': n('P-052'), 'field': 'winter_plan', 'from': other_plan, 'to': to_plan, 'why': 'You said where it will spend the winter.'},
    {'kind': 'set', 'code': 'P-010', 'name': n('P-010'), 'field': 'water_every_days', 'from': P['P-010']['water_every_days'], 'to': 7, 'why': 'You said you water it every week.'},
    {'kind': 'set', 'code': 'P-055', 'name': n('P-055'), 'field': 'health_rating', 'from': P['P-055']['health_rating'], 'to': P['P-055']['health_rating'], 'why': ''},
    {'kind': 'set', 'code': 'P-016', 'name': 'A name it does not have', 'field': 'container', 'from': P['P-016']['container'], 'to': 'A pot of its own', 'why': ''},
    {'kind': 'archive', 'code': 'P-005', 'name': n('P-005'), 'why': 'It has died back and this kind does not return.'},
    {'kind': 'new', 'fields': {'common_name': 'Hardy aloe, second pot', 'scientific_name': 'Aloiampelos striatula', 'site': 'Outdoors', 'health_rating': 'Good'},
     'photos': [{'file': 'aloe-1.jpg', 'caption': 'The second pot'}, {'file': 'aloe-2.jpg', 'caption': 'Its leaves'}], 'why': 'Your photos show a second pot of it.'},
    {'kind': 'ask', 'code': 'P-014', 'name': n('P-014'), 'text': 'Is the largest aloe still in the black pot?', 'why': 'The newest photo shows another pot beside it.'},
    {'kind': 'ask', 'code': 'P-003', 'name': n('P-003'), 'text': 'Has the fig dropped its leaves yet?', 'why': ''},
]
NAME = 'plant-updates-20261114-0312.zip'
with zipfile.ZipFile(os.path.join(FOLDER, NAME), 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('updates.json', json.dumps({'format': 'plant-updates-1', 'made': '2026-11-14', 'about': 'From your photos of November 12.', 'changes': CH}))
    z.writestr('photos/aloe-1.jpg', jpg((70, 130, 80))); z.writestr('photos/aloe-2.jpg', jpg((120, 150, 70)))
with open(os.path.join(FOLDER, 'plant-updates-broken.json'), 'w') as f: f.write('this is not an update file')
with open(os.path.join(FOLDER, 'README.txt'), 'w') as f: f.write('Claude saves update files here.')
st, L = call('GET', '/api/updates')
good = [w for w in L['waiting'] if not w['bad']]
check(len(good) == 1 and good[0]['name'] == NAME and good[0]['changes'] == len(CH) and good[0]['plants'] == 10, 'a file saved in the folder is waiting: its name, its changes and its plants are counted')
check([w['name'] for w in L['waiting'] if w['bad']] == ['plant-updates-broken.json'], 'a file that is not an update file is named as one that cannot be used, and other things in the folder are ignored')
FID = good[0]['id']
st, R = call('GET', '/api/updates/' + FID)
states = [x['state'] for x in R['items']]
check(states == ['ready', 'ready', 'ready', 'conflict', 'ready', 'same', 'out', 'ready', 'ready', 'ready', 'ready'], 'each change is weighed against the record: ready, needing a decision, nothing to do, or left out')
check(call('GET', f'/api/updates/{FID}/photo/..%2Fupdates.json')[0] == 404 and call('GET', '/api/updates/' + 'f' * 16)[0] == 404 and call('GET', '/api/updates/..%2F..%2Fplants.db')[0] == 404,
      'only a photo named in the file, and only a file that is there, can be asked for')
st, bad = call('POST', f'/api/updates/{FID}/apply', {'accept': [5, 6, 3]})
check(st == 200 and bad['before']['made_n'] == 0 and call('GET', '/api/plants/P-052')[1]['winter_plan'] == P['P-052']['winter_plan'],
      'accepting what has nothing to do, was left out or needs a decision changes nothing')
# that marked the file as brought in with nothing made: start again with the same changes in a file of another name and made date
NAME2 = 'plant-updates-20261114-0900.zip'
os.remove(os.path.join(FOLDER, NAME))
with zipfile.ZipFile(os.path.join(FOLDER, NAME2), 'w', zipfile.ZIP_DEFLATED) as z:
    z.writestr('updates.json', json.dumps({'format': 'plant-updates-1', 'made': '2026-11-14', 'about': 'From your photos of November 12, and your answers of November 13.', 'changes': CH}))
    z.writestr('photos/aloe-1.jpg', jpg((70, 130, 80))); z.writestr('photos/aloe-2.jpg', jpg((120, 150, 70)))
FID = next(w['id'] for w in call('GET', '/api/updates')[1]['waiting'] if not w['bad'])

with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1366, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Updates Test')")
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#upd-today', timeout=30000)
    t = pg.locator('#upd-today').inner_text()
    check('Plant updates from Claude are waiting' in t and NAME2 in t and f'{len(CH)} changes for 10 plants' in t and 'Nothing is changed until you have looked' in t, 'Today says a file is waiting, how much is in it, and that nothing is changed yet')
    pg.locator('#upd-today a.btn').click(); pg.wait_for_selector('.upd-plants', timeout=20000)
    check(pg.locator('h1').inner_text().startswith('Updates from Claude') and pg.locator('#sub-nav a[data-nav=updates]').get_attribute('aria-current') == 'page', 'its button opens the file on the Updates from Claude page, which is in the Plants menu')
    check(pg.locator('.upd-file').first.inner_text().count(NAME2) == 1 and "Claude's note:" in pg.locator('.upd-file').first.inner_text(), 'the page names the file and shows Claude\'s note')
    S = lambda: pg.locator('#upd-sum').inner_text(); go = pg.locator('#upd-go')
    check(S().startswith(f'{len(CH)} changes for 10 plants. 8 are set to be made; 1 needs your decision') and '2 have nothing to do or cannot be made' in S() and go.inner_text() == 'Make the 8 changes',
          'the summary and the button count what will be made: the ready ones, not the one that needs a decision')
    check(pg.locator('.upd-plant').count() == 10 and pg.locator('.upd-plant').first.locator('.upd-ch').count() == 2 and pg.locator('.upd-plant').first.locator('.upd-ph img').count() == 1,
          'every plant is one block with its picture and its changes')
    c0 = pg.locator('#upd-c0')
    check(c0.locator('input[type=checkbox]').is_checked() and 'Now:' in c0.inner_text() and 'Change to:' in c0.inner_text() and to_health in c0.inner_text() and 'Why: Five new leaves' in c0.inner_text(),
          'a change is ticked to begin with, and says what the page says now, what it would say, and why')
    check(pg.get_by_label('Health rating', exact=True).first.is_checked(), 'its tick box is named for what it changes')
    cf = pg.locator('#upd-c3')
    check('Needs your decision' in cf.inner_text() and cf.locator('input[value=mine]').is_checked() and P['P-052']['winter_plan'] in cf.inner_text() and to_plan in cf.inner_text() and cf.locator('input[type=checkbox]').count() == 0,
          'a change the page no longer agrees with needs a decision, and starts on "Keep what it says now"')
    check('Nothing to do' in pg.locator('#upd-c5').inner_text() and 'already says this' in pg.locator('#upd-c5').inner_text() and pg.locator('#upd-c5 input').count() == 0, 'a change the page already has says so, with nothing to tick')
    check('Left out' in pg.locator('#upd-c6').inner_text() and 'A name it does not have' in pg.locator('#upd-c6').inner_text() and pg.locator('#upd-c6 input').count() == 0, 'a change for a plant the record does not have under that code and name is left out, and says why')
    check(pg.locator('.upd-plant', has=pg.locator('#upd-c6')).locator('.upd-ph').inner_text().strip() == 'No photo', 'a block with no picture to show says "No photo" in words')
    nw = pg.locator('#upd-c8')
    check('A new page for this plant' in nw.inner_text() and nw.locator('.upd-pics img').count() == 2 and until(pg, lambda: nw.locator('.upd-pics img').first.evaluate('i => i.complete && i.naturalWidth > 0')),
          'a new page shows the photos that come with it')
    check(pg.locator('.upd-needs button').count() == 1, 'a notice lists what needs a decision')
    pg.locator('.upd-needs button').first.click()
    check(until(pg, lambda: pg.evaluate('document.activeElement && document.activeElement.id') == 'upd-c3'), 'and its link goes to that change')
    pg.screenshot(path=os.path.join(OUT, 'updates-review.png'), full_page=True)
    c0.locator('input[type=checkbox]').uncheck()
    check(until(pg, lambda: go.inner_text() == 'Make the 7 changes' and '7 are set to be made' in S()), 'unticking a change takes it off the count')
    cf.locator('input[value=claude]').check()
    check(until(pg, lambda: go.inner_text() == 'Make the 8 changes' and 'needs your decision' in S()), 'choosing Claude\'s for the one that needed a decision adds it')
    pg.locator('[data-act=updall][data-on="0"]').click()
    check(until(pg, lambda: pg.locator('#upd-go').inner_text() == 'Make the 1 change' and pg.locator('#upd-c1 input').is_checked() is False and pg.locator('#upd-c3 input[value=claude]').is_checked()), 'Untick every change unticks the ready ones and leaves your decision as you made it')
    pg.locator('#upd-c3 input[value=mine]').check()
    check(until(pg, lambda: pg.locator('#upd-go').is_disabled() and pg.locator('#upd-go-why').is_visible() and pg.locator('#upd-go-why').inner_text() == 'Nothing is ticked.'), 'with nothing to make, the button is off and says why')
    pg.locator('[data-act=updall][data-on="1"]').click()
    check(until(pg, lambda: pg.locator('#upd-go').inner_text() == 'Make the 8 changes'), 'Tick every change ticks them again')
    pg.locator('#upd-c0 input[type=checkbox]').uncheck(); pg.locator('#upd-c3 input[value=claude]').check()        # leave the first one, take Claude's for the decision
    check(call('GET', '/api/plants/P-009')[1]['health_summary'] == P['P-009']['health_summary'], 'nothing in the record has changed so far')
    pg.locator('#upd-go').click()
    check(until(pg, lambda: pg.locator('.upd-done').count() == 1 and '8 changes made, 3 left as they were' in pg.locator('.upd-done').inner_text(), 20000), 'the button makes the changes, and the page says how many were made and how many were left')
    after = {c: call('GET', '/api/plants/' + c)[1] for c in P}
    check(after['P-009']['health_rating'] == P['P-009']['health_rating'] and after['P-009']['health_summary'].startswith('Recovered.') and after['P-012']['id_confidence'] == 85
          and after['P-052']['winter_plan'] == to_plan and after['P-010']['water_every_days'] == 7 and after['P-016']['container'] == P['P-016']['container'],
          'the ticked changes are in the record; the unticked one, and the one that was left out, are not')
    check(after['P-005']['status'] == 'archived' and any(q['text'] == 'Is the largest aloe still in the black pot?' and not q['done'] for q in after['P-014']['requests'])
          and any(q['text'] == 'Has the fig dropped its leaves yet?' for q in after['P-003']['requests']), 'the plant is in the archive, and the questions are on their plants\' pages')
    new = next((x for x in call('GET', '/api/plants')[1] if x['common_name'] == 'Hardy aloe, second pot'), None)
    np_ = call('GET', '/api/plants/' + new['code'])[1] if new else None
    check(bool(np_) and np_['scientific_name'] == 'Aloiampelos striatula' and len(np_['photos']) == 2 and np_['photos'][0]['is_primary'] == 1 and np_['photos'][0]['caption'] == 'The second pot'
          and urllib.request.urlopen(BASE + '/photos/' + np_['photos'][0]['file']).status == 200, 'the new page is made, with its two photos and their captions')
    H = call('GET', '/api/plants/P-012/history')[1]
    a = next(x for x in H['audit'] if x['field'] == 'id_confidence')
    check(a['changed_by'] == f'Claude ({NAME2})' and 'The close-up settles it.' in a['note'] and 'accepted by Updates Test' in a['note'], 'each change is in the plant\'s history, signed with Claude and the file, with the reason and who accepted it')
    d = pg.locator('main').inner_text()
    check('What changed' in d and n('P-012') in d and 'What was left as it was' in d and 'You left it as it was.' in d and 'Page history' in d, 'the page lists what changed and what was left, and says how to take a change back')
    pg.screenshot(path=os.path.join(OUT, 'updates-done.png'), full_page=True)
    check(call('POST', f'/api/updates/{FID}/apply', {'accept': [0]})[0] == 409 and call('GET', '/api/plants/P-009')[1]['health_rating'] == P['P-009']['health_rating'], 'a file is brought in once: asking again is refused')
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#today-water', timeout=30000)
    check(until(pg, lambda: pg.locator('.td-none, #today-needs').count() > 0) and pg.locator('#upd-today').count() == 0, 'Today no longer says a file is waiting')
    # the page before a file is chosen, and files chosen by hand
    pg.goto(BASE + '/#/updates'); pg.wait_for_selector('.upd-choose', timeout=20000)
    m = pg.locator('main').inner_text()
    check('No update file is waiting.' in m and 'Files that cannot be used (1)' in m and 'plant-updates-broken.json' in m and 'Files you brought in before' in m and f'{NAME2}. 8 changes made, 3 left as they were.' in m,
          'the Updates page says nothing is waiting, names the file it cannot use, and lists what was brought in before')
    tmp = tempfile.mkdtemp()
    again = os.path.join(tmp, NAME2)
    with open(os.path.join(FOLDER, NAME2), 'rb') as f, open(again, 'wb') as o: o.write(f.read())
    pg.set_input_files('.upd-choose input[type=file]', again); pg.locator('.upd-choose button[type=submit]').click()
    check(until(pg, lambda: pg.locator('.upd-done').count() == 1 and 'brought in already' in pg.locator('#toasts').inner_text()), 'choosing a file that was brought in already says so and shows what it did')
    small = os.path.join(tmp, 'plant-updates-20261115-0800.json')
    with open(small, 'w') as f: json.dump({'format': 'plant-updates-1', 'made': '2026-11-15', 'about': 'One more thing.', 'changes': [
        {'kind': 'set', 'code': 'P-010', 'name': n('P-010'), 'field': 'water_every_days', 'from': 7, 'to': 9, 'why': 'It dries more slowly indoors.'},
        {'kind': 'new', 'fields': {'common_name': 'Hardy aloe, second pot', 'site': 'Outdoors'}, 'why': 'A page for the second pot.'}]}, f)
    pg.goto(BASE + '/#/updates'); pg.wait_for_selector('.upd-choose', timeout=20000)
    pg.set_input_files('.upd-choose input[type=file]', small); pg.locator('.upd-choose button[type=submit]').click()
    check(until(pg, lambda: pg.locator('.upd-plants').count() == 1 and pg.locator('#upd-go').inner_text() == 'Make the 1 change'), 'a file chosen on the page shows its changes the same way')
    c1 = pg.locator('#upd-c1')
    check('Needs your decision' in c1.inner_text() and 'already in your record' in c1.inner_text() and c1.locator('input[value=mine]').is_checked() and 'Do not make this page' in c1.inner_text(),
          'a new page for a name the record already has needs a decision, and starts on not making it')
    pg.locator('.upd-bar [data-act=updaside]').click()
    check(until(pg, lambda: pg.locator('.upd-choose').count() == 1 and 'Set aside, nothing changed.' in pg.locator('main').inner_text()) and call('GET', '/api/plants/P-010')[1]['water_every_days'] == 7,
          'Change nothing sets the file aside: nothing is changed and the list says so')
    pg.set_input_files('.upd-choose input[type=file]', small); pg.locator('.upd-choose button[type=submit]').click()
    check(until(pg, lambda: pg.locator('.upd-plants').count() == 1), 'a file set aside can be chosen again')
    pg.locator('#upd-go').click()
    check(until(pg, lambda: pg.locator('.upd-done').count() == 1 and call('GET', '/api/plants/P-010')[1]['water_every_days'] == 9, 20000), 'and brought in then')
    # a file in Claude's folder set aside from the list, and looked at again
    with open(os.path.join(FOLDER, 'plant-updates-20261116-0700.json'), 'w') as f: json.dump({'format': 'plant-updates-1', 'made': '2026-11-16', 'about': '', 'changes': [
        {'kind': 'ask', 'code': 'P-012', 'name': n('P-012'), 'text': 'Has it flowered?', 'why': ''}]}, f)
    pg.goto(BASE + '/#/updates'); pg.wait_for_selector('.upd-wait', timeout=20000)
    check('Waiting for you (1)' in pg.locator('main').inner_text() and '1 change for 1 plant' in pg.locator('.upd-wait').inner_text(), 'a new file in the folder is listed as waiting')
    pg.locator('.upd-wait [data-act=updaside]').click()
    check(until(pg, lambda: pg.locator('.upd-wait').count() == 0 and pg.locator('[data-act=updback]').count() == 1), 'Set it aside takes it off the waiting list, with a way to look at it again')
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#today-water', timeout=30000)
    check(pg.locator('#upd-today').count() == 0, 'and Today stops naming it')
    pg.goto(BASE + '/#/updates'); pg.wait_for_selector('[data-act=updback]', timeout=20000); pg.locator('[data-act=updback]').click()
    check(until(pg, lambda: pg.locator('.upd-plants').count() == 1 and 'Has it flowered?' in pg.locator('main').inner_text()), 'Look at it again opens its changes')
    # files that are not update files are refused in plain words
    for what, body, words in (('a text file', b'hello', 'not an update file'), ('a file of another format', json.dumps({'format': 'something-else', 'changes': []}).encode(), 'not an update file for this app'),
                              ('a change with no plant', json.dumps({'format': 'plant-updates-1', 'changes': [{'kind': 'archive', 'code': 'P-001'}]}).encode(), 'does not say which plant'),
                              ('a kind this version does not know', json.dumps({'format': 'plant-updates-1', 'changes': [{'kind': 'delete', 'code': 'P-001', 'name': 'x'}]}).encode(), 'a kind this version does not know')):
        bnd = 'xXupdXx'; data = (f'--{bnd}\r\nContent-Disposition: form-data; name="file"; filename="plant-updates-x.json"\r\nContent-Type: application/json\r\n\r\n').encode() + body + f'\r\n--{bnd}--\r\n'.encode()
        req = urllib.request.Request(BASE + '/api/updates/upload', data=data, headers={'Content-Type': 'multipart/form-data; boundary=' + bnd, 'X-Editor': 'Updates Test'}, method='POST')
        try: urllib.request.urlopen(req); got = (200, '')
        except urllib.error.HTTPError as e: got = (e.code, json.loads(e.read())['error'])
        check(got[0] == 400 and words in got[1], f'{what} is refused: "{got[1][:70]}"')
    st, r = call('GET', '/api/updates')
    check(not any('plant-updates-x' in w['name'] for w in r['waiting']), 'and none of them is kept')
    # only the owner
    try:
        own = {'Tailscale-User-Login': 'owner@example.com', 'Tailscale-User-Name': 'Owner Person'}; ed = {'Tailscale-User-Login': 'ed@example.com', 'Tailscale-User-Name': 'Ed Person'}
        call('GET', '/api/me', base=TS, headers=own); call('GET', '/api/me', base=TS, headers=ed)
        call('PUT', '/api/people', {'login': 'ed@example.com', 'role': 'editor'})
        check(call('GET', '/api/updates', base=TS, headers=ed)[0] == 403 and call('POST', f'/api/updates/{FID}/aside', {'on': True}, base=TS, headers=ed)[0] == 403 and call('GET', '/api/updates', base=TS, headers=own)[0] == 200,
              'someone who can edit cannot see or use the update files; the owner can, through Tailscale too')
        ec = br.new_context(viewport={'width': 1366, 'height': 900}, extra_http_headers=ed); ep = ec.new_page()
        ep.goto(TS + '/#/updates'); ep.wait_for_selector('main h1', timeout=30000)
        check(until(ep, lambda: 'Only Owner Person can bring in updates from Claude.' in ep.locator('main').inner_text()) and not ep.locator('#sub-nav a[href="#/updates"]').is_visible(), 'for them the page says it is the owner\'s, and the menu leaves it out')
        ep.goto(TS + '/#/'); ep.wait_for_selector('#today-water', timeout=30000)
        check(ep.locator('#upd-today').count() == 0, 'and Today does not mention update files to them')
        ec.close()
    except urllib.error.URLError:
        print('skip  the owner-only checks (the mock server was started without MOCK_TS=1)')
    # a phone
    with open(os.path.join(FOLDER, 'plant-updates-20261117-0700.json'), 'w') as f: json.dump({'format': 'plant-updates-1', 'made': '2026-11-17', 'about': 'For the phone.', 'changes': [
        {'kind': 'set', 'code': 'P-012', 'name': n('P-012'), 'field': 'health_summary', 'from': P['P-012']['health_summary'], 'to': 'Compact rosettes, firm leaves, no pests seen.', 'why': 'From the newest photos.'},
        {'kind': 'set', 'code': 'P-012', 'name': n('P-012'), 'field': 'id_confidence', 'from': 10, 'to': 90, 'why': ''},
        {'kind': 'archive', 'code': 'P-016', 'name': n('P-016'), 'why': 'A second page for the same plant.'}]}, f)
    ph = br.new_page(viewport={'width': 384, 'height': 740}); ph.on('pageerror', lambda e: errs.append(str(e)))
    ph.add_init_script("localStorage.setItem('plantdb.editor','Updates Test')")
    ph.goto(BASE + '/#/'); ph.wait_for_selector('#upd-today', timeout=30000)
    check('2 files of plant updates from Claude are waiting' in ph.locator('#upd-today').inner_text() and not ph.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'with two files waiting Today says so, and fits a phone')
    ph.locator('#upd-today a.btn').click(); ph.wait_for_selector('.upd-wait', timeout=20000)
    ph.locator('.upd-wait a.btn', has_text='Look at the changes').last.click(); ph.wait_for_selector('.upd-plants', timeout=20000)
    check(not ph.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'a file\'s changes fit a phone with no sideways scrolling')
    bar = ph.evaluate("() => { const b = document.querySelector('.upd-bar'), k = [...b.querySelectorAll('button')].filter(e => e.offsetParent); return [k.length, document.querySelector('.upd-no-end button').offsetParent !== null]; }")
    check(bar == [1, True], 'on a phone the bar holds the one button, and Change nothing ends the page')
    ph.screenshot(path=os.path.join(OUT, 'updates-phone.png'), full_page=True)
    # the same page at the largest text: a name keeps its words whole, a tag stays in its box, and nothing is cut off at the side
    big = br.new_page(viewport={'width': 384, 'height': 740}); big.on('pageerror', lambda e: errs.append(str(e)))
    big.add_init_script("localStorage.setItem('plantdb.editor','Updates Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    big.goto(ph.url); big.wait_for_selector('.upd-plants', timeout=30000)
    m = big.evaluate("""() => { const rem = parseFloat(getComputedStyle(document.documentElement).fontSize), out = { rem, side: document.documentElement.scrollWidth - innerWidth, names: [], tags: [], indent: [] };
      document.querySelectorAll('.upd-plant').forEach(a => { const h = a.querySelector('h3').getBoundingClientRect(), p = a.querySelector('.upd-ph').getBoundingClientRect(), c = a.getBoundingClientRect();
        out.names.push([Math.round(h.width), h.width >= 9 * rem - 1, h.top >= p.bottom - 2, h.right <= c.right + 1]); });
      document.querySelectorAll('.upd-tag').forEach(t => { const r = t.getBoundingClientRect(), b = t.closest('.upd-ch').getBoundingClientRect(); out.tags.push(r.right <= b.right + 1 && r.left >= b.left - 1); });
      document.querySelectorAll('.upd-vals:not(.upd-flat)').forEach(v => out.indent.push(getComputedStyle(v).marginLeft));
      return out; }""")
    check(m['rem'] > 28 and m['side'] <= 1, 'at the largest text a file\'s changes still fit a phone with no sideways scrolling')
    check(m['names'] and all(wide and under and inside for _, wide, under, inside in m['names']), f'there a plant\'s name goes under its picture and has the card\'s width, so no word is broken in the middle ({m["names"]})')
    check(m['tags'] and all(m['tags']), 'and "Needs your decision" stays inside its box')
    check(m['indent'] and set(m['indent']) == {'0px'}, 'and what a change says starts at the card\'s edge, where the card is too narrow to indent it')
    big.screenshot(path=os.path.join(OUT, 'updates-phone-bigtext.png'), full_page=True)
    usual = ph.evaluate("""() => [...document.querySelectorAll('.upd-plant')].map(a => { const h = a.querySelector('h3').getBoundingClientRect(), p = a.querySelector('.upd-ph').getBoundingClientRect(); return h.left >= p.right && h.top < p.bottom; })""")
    check(usual and all(usual), 'at the usual text the name stays beside the picture')
    br.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print(f"\n{'FAILED' if fails else 'passed'}: {len(fails)} of the checks failed" if fails else '\nAll update file checks passed')
sys.exit(1 if fails else 0)
