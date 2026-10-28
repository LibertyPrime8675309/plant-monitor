"""Checks 1.18.0: Identify a plant (camera and photos) and the plant library, against the fake picture checker
(dev/test/mock_vision.py, started by mock_server.py). The fake decides by colour: red -> P-020 for sure, green -> unsure
between three Monsteras, blue -> none of yours. The browser gets a fake red camera.
Start the mock server with a fresh data folder first (MOCK_TS=1), then:  python3 dev/test/identify_check.py
Screenshots: dev/tmp/shots/identify-*.png"""
import io, json, os, sys, urllib.error, urllib.request
from PIL import Image
from playwright.sync_api import sync_playwright
LOCAL, TS, VIS = 'http://127.0.0.1:8080', 'http://127.0.0.1:8081', 'http://127.0.0.1:8090'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
TMP = os.path.abspath(os.path.join(OUT, '..')); fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def pic(colour, path=None):
    b = io.BytesIO(); Image.new('RGB', (320, 240), colour).save(b, 'PNG')
    if path: open(path, 'wb').write(b.getvalue())
    return b.getvalue()
def call(m, url, base=LOCAL, h=None, body=None, image=None):
    hd = {'X-Editor': 'Identify Test', **(h or {})}; data = None
    if image is not None:
        bd = 'xx' + os.urandom(6).hex()
        data = f'--{bd}\r\nContent-Disposition: form-data; name="image"; filename="p.png"\r\nContent-Type: image/png\r\n\r\n'.encode() + image + f'\r\n--{bd}--\r\n'.encode()
        hd['Content-Type'] = 'multipart/form-data; boundary=' + bd
    elif body is not None: data = json.dumps(body).encode(); hd['Content-Type'] = 'application/json'
    req = urllib.request.Request(base + url, data=data, headers=hd, method=m)
    try:
        with urllib.request.urlopen(req, timeout=60) as r: return r.status, json.loads(r.read() or b'null')
    except urllib.error.HTTPError as e:
        t = e.read().decode()
        try: return e.code, json.loads(t)
        except ValueError: return e.code, t
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan'}
ED = {'Tailscale-User-Login': 'editor@example.net', 'Tailscale-User-Name': 'Ed'}
V = {'Tailscale-User-Login': 'viewer@example.net', 'Tailscale-User-Name': 'Viewer'}
call('GET', '/api/me', base=TS, h=E); call('GET', '/api/me', base=TS, h=ED); call('GET', '/api/me', base=TS, h=V)
call('PUT', '/api/people', body={'login': 'editor@example.net', 'role': 'editor'})

# ---- the server routes
st, s = call('GET', '/api/identify/status')
check(st == 200 and s['state'] == 'ready' and s['plantnet'] is False and s['claude'] is False, 'status: the picture checker is ready; no second opinions set up yet')
st, r = call('POST', '/api/identify?scope=texas', image=pic('red'))
check(st == 200 and r['matches'][0]['code'] == 'P-020' and r['matches'][0]['confidence'] == 0.93 and r['matches'][0]['common_name'] and r['matches'][0]['photo'],
      'a picture comes back with the closest plant, its name, photo and confidence')
check(r['scope'] == 'texas' and r['species'][0]['scientific_name'] and 'yours' in r['species'][0], 'and species guesses from the chosen list, marked when you have them')
mon = [x for x in r['species'] if x['scientific_name'] == 'Monstera deliciosa']
check(mon and mon[0]['yours'], f"Monstera deliciosa is marked as one you have ({mon[0]['yours'] if mon else ''})")
st, r = call('POST', '/api/identify', image=b'not a picture')
check(st == 400 and 'picture' in r['error'], 'something that is not a picture is refused')
st, r = call('POST', '/api/identify', base=TS, h=V, image=pic('red'))
check(st == 200 and r['matches'][0]['code'] == 'P-020', 'people who can only view can identify too (it changes nothing)')
st, r = call('POST', '/api/identify/plantnet', base=TS, h=V, image=pic('red'))
check(st == 403, 'but cannot ask Pl@ntNet or Claude (they use the owner\'s keys)')
st, r = call('POST', '/api/identify/plantnet', image=pic('blue'))
check(st == 400 and 'not set up' in r['error'], 'Pl@ntNet without a key says it is not set up')
st, r = call('PUT', '/api/identify/settings', base=TS, h=ED, body={'plantnet_key': '2b10abcdefghijklmnopqrstu'})
check(st == 403, 'an editor cannot change the keys (owner only)')
st, r = call('PUT', '/api/identify/settings', body={'plantnet_key': 'has spaces in it'})
check(st == 400, 'a key that does not look like one is refused')
st, r = call('PUT', '/api/identify/settings', body={'plantnet_key': '2b10abcdefghijklmnopqrstu', 'claude_key': 'sk-ant-api03-testtesttest-9876'})
check(st == 200 and r['plantnet'] and r['plantnet_hint'] == '…rstu' and r['claude_hint'] == '…9876', 'the owner saves both keys; only the last 4 characters come back')
alltext = json.dumps([call('GET', u)[1] for u in ('/api/identify/settings', '/api/identify/status', '/api/settings', '/api/meta')])
check('abcdefghijklmnop' not in alltext and 'testtesttest' not in alltext, 'the keys are never sent to the browser')
st, a = call('GET', '/api/audit?limit=5')
check('abcdefghijklmnop' not in json.dumps(a), 'and not written in the audit log')
st, r = call('POST', '/api/identify/plantnet', image=pic('blue'))
check(st == 200 and r['species'][0]['scientific_name'] == 'Lupinus texensis' and r['species'][0]['probability'] == 0.87 and r['remaining'] == 499,
      'Pl@ntNet answers come back with names, score and the pictures left today')
st, r = call('POST', '/api/identify/claude', image=pic('blue'))
check(st == 200 and r['species'][0]['common_name'] == 'Texas bluebonnet' and r['species'][0]['why'] and r['tip'], 'Claude answers come back with names, reasons and a photo tip')
call('PUT', '/api/identify/settings', body={'plantnet_key': 'bad-key-0000'})
st, r = call('POST', '/api/identify/plantnet', image=pic('blue'))
check(st == 502 and 'refused the key' in r['error'], 'a key Pl@ntNet refuses says so in plain words')
call('PUT', '/api/identify/settings', body={'plantnet_key': '2b10abcdefghijklmnopqrstu'})
st, r = call('GET', '/api/library?q=bluebonnet&scope=texas')
check(st == 200 and r['results'][0]['scientific_name'] == 'Lupinus texensis' and r['results'][0]['yours'] == [], 'the library finds a plant by its common name')
st, r = call('GET', '/api/library?q=m')
check(st == 200 and r['results'] == [], 'one letter finds nothing (at least 2)')
urllib.request.urlopen(urllib.request.Request(VIS + '/mock/state', data=b'{"state":"setting up"}', headers={'Content-Type': 'application/json'}))
st, r = call('POST', '/api/identify', image=pic('red'))
check(st == 503 and 'setting up' in r['error'], 'while the checker sets up, pictures get a clear "still setting up" answer')

# ---- the pages
y4m = os.path.join(TMP, 'red.y4m')                  # a fake camera that films a red plant
with open(y4m, 'wb') as f:
    w, h = 320, 240
    f.write(f'YUV4MPEG2 W{w} H{h} F10:1 Ip A1:1 C420jpeg\n'.encode())
    for _ in range(10): f.write(b'FRAME\n' + bytes([76]) * (w * h) + bytes([84]) * (w * h // 4) + bytes([255]) * (w * h // 4))
blue, green = os.path.join(TMP, 'blue.png'), os.path.join(TMP, 'green.png'); pic('blue', blue); pic((20, 160, 40), green)
code = lambda pg: pg.evaluate("location.hash")
with sync_playwright() as p:
    b = p.chromium.launch(args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--use-file-for-fake-video-capture=' + y4m])
    ctx = b.new_context(viewport={'width': 1280, 'height': 900}, permissions=['camera'])
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.on('console', lambda m: errs.append(m.text) if m.type == 'error' and '503' not in m.text and '502' not in m.text and '404' not in m.text else None)
    pg.add_init_script("localStorage.setItem('plantdb.editor','Identify Test')")
    pg.goto(LOCAL + '/#/identify'); pg.wait_for_timeout(2500)
    check(pg.locator('nav[aria-label=Main] a[href="#/identify"][aria-current=page]').count() == 1 and pg.locator('nav[aria-label=Main] a[href="#/library"]').count() == 1, 'Identify and Library are in the top menu')
    check('setting up' in pg.inner_text('#id-st'), 'the page says the checker is still setting up')
    urllib.request.urlopen(urllib.request.Request(VIS + '/mock/state', data=b'{"state":"ready"}', headers={'Content-Type': 'application/json'}))
    pg.wait_for_timeout(6000)
    check('Ready' in pg.inner_text('#id-st'), 'and then that it is ready (it checks again by itself)')
    check(pg.locator('select[data-f=idscope]').count() == 1 and pg.locator('label:has(select[data-f=idscope])').count() == 1, 'the species list choice has a real label')
    pg.click('#id-cam-btn'); pg.wait_for_timeout(1500)
    check(pg.locator('#id-cam-btn').inner_text() == 'Stop camera' and not pg.locator('#id-snap').is_disabled(), 'Start camera turns the camera on')
    pg.wait_for_selector('dialog[open] .id-pop', timeout=15000)
    t = pg.inner_text('dialog[open]')
    check('P-020' in t and '93% sure' in t and 'Very likely' in t, 'pointing at a plant: a window names the plant and how sure it is')
    check(pg.locator('dialog[open] button', has_text='Open its page').count() == 1 and pg.locator('dialog[open] button', has_text='Add this picture to its photos').count() == 1,
          'with "Open its page" and "Add this picture to its photos"')
    check(pg.locator('dialog[open] .id-pair img').count() == 2, 'it shows your picture next to the closest photo of that plant')
    pg.screenshot(path=os.path.join(OUT, 'identify-1-popup.png'))
    n0 = len(call('GET', '/api/plants/P-020')[1]['photos'])
    pg.click('dialog[open] button:has-text("Add this picture to its photos")'); pg.wait_for_timeout(1500)
    ph = call('GET', '/api/plants/P-020')[1]['photos']
    check(len(ph) == n0 + 1 and 'Identify' in (ph[-1].get('caption') or ''), 'Add this picture to its photos adds it to P-020')
    pg.wait_for_selector('dialog[open] .id-pop', timeout=15000)
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    pg.click('#id-cam-btn'); pg.wait_for_timeout(500)
    check(pg.locator('#id-cam-btn').inner_text() == 'Start camera', 'Stop camera turns it off')
    if pg.locator('dialog[open]').count(): pg.keyboard.press('Escape')
    # a photo of something new
    pg.set_input_files('input[data-act=idfile]', blue); pg.wait_for_selector('dialog[open] .id-pop', timeout=10000)
    check('Probably not one of your plants' in pg.inner_text('dialog[open]') and 'Lupinus texensis' in pg.inner_text('dialog[open]'), 'a photo of a plant you do not have: it says so and suggests a name')
    check(pg.locator('dialog[open] button.linkish[value="open:P-030"]').count() == 1, 'and still offers the closest of your plants, in case it is one')
    pg.click('dialog[open] button:has-text("See the suggestions")'); pg.wait_for_timeout(500)
    res = pg.inner_text('#id-res')
    check('Texas bluebonnet' in res and 'Grows wild in Texas' in res and pg.locator('#id-res .id-links a[href*="plants.usda.gov/plant-profile/LUTE"]').count() == 1,
          'the suggestions list names, Texas, and links to USDA PLANTS, Kew and Wikipedia')
    check(pg.evaluate("document.activeElement && document.activeElement.id") == 'h-idres', 'the keyboard focus moves to the suggestions')
    check(pg.locator('#id-res [data-act=idask][data-who=plantnet]').count() == 1 and pg.locator('#id-res [data-act=idask][data-who=claude]').count() == 1, 'with Ask Pl@ntNet and Ask Claude buttons')
    pg.click('[data-act=idask][data-who=plantnet]'); pg.wait_for_timeout(1200)
    check('Pl@ntNet says' in pg.inner_text('#id-ext-plantnet') and '87%' in pg.inner_text('#id-ext') and 'left today: 499' in pg.inner_text('#id-ext'), 'Ask Pl@ntNet shows its answer')
    pg.click('[data-act=idask][data-who=claude]'); pg.wait_for_timeout(1200)
    check('Claude says' in pg.inner_text('#id-ext-claude') and 'Palmate leaves' in pg.inner_text('#id-ext') and 'Pl@ntNet says' in pg.inner_text('#id-ext'), 'Ask Claude shows its answer and why')
    pg.screenshot(path=os.path.join(OUT, 'identify-2-new.png'), full_page=True)
    pg.click('#id-ext-claude [data-act=idnew]'); pg.wait_for_timeout(1500)
    check(code(pg) == '#/new' and pg.locator('input[name=scientific_name]').input_value() == 'Lupinus texensis' and pg.locator('input[name=common_name]').input_value() == 'Texas bluebonnet'
          and pg.locator('input[name=family]').input_value() == 'Fabaceae', 'Add as a new plant opens the form with the names filled in')
    check('Names from Claude' in pg.inner_text('main') and 'picture is added' in pg.inner_text('main'), 'and says where the names came from, and that the picture comes too')
    pg.click('form[data-form=new] button[type=submit]'); pg.wait_for_timeout(2000)
    newc = code(pg).split('/')[-1]
    np_ = call('GET', '/api/plants/' + newc)[1]
    check(np_.get('scientific_name') == 'Lupinus texensis' and len(np_.get('photos', [])) == 1, f'saving adds the plant ({newc}) with the picture')
    pg.goto(LOCAL + '/#/new'); pg.wait_for_timeout(1500)
    check(pg.locator('input[name=scientific_name]').input_value() == '', 'Add a plant opened later starts empty again')
    # unsure: which one is it?
    pg.goto(LOCAL + '/#/identify'); pg.wait_for_timeout(2000)
    pg.set_input_files('input[data-act=idfile]', green); pg.wait_for_selector('dialog[open] .id-pop', timeout=10000)
    t = pg.inner_text('dialog[open]')
    check('Which one is it?' in t and pg.locator('dialog[open] .id-ch').count() == 3 and all(c in t for c in ('P-049', 'P-050', 'P-051')), 'when it is unsure it asks which one it is, with 3 photos')
    pg.screenshot(path=os.path.join(OUT, 'identify-3-which.png'))
    pg.click('dialog[open] .id-ch >> nth=1'); pg.wait_for_timeout(1500)
    check(code(pg) == '#/plant/P-050', 'choosing one opens its page')
    # the library
    pg.goto(LOCAL + '/#/library'); pg.wait_for_timeout(2000)
    check(pg.locator('nav[aria-label=Main] a[href="#/library"][aria-current=page]').count() == 1 and pg.locator('label:has(input[name=q])').count() == 1, 'the library page has a labelled search box')
    pg.fill('input[name=q]', 'monstera'); pg.select_option('select[name=scope]', 'world'); pg.click('form[data-form=libsearch] button[type=submit]'); pg.wait_for_timeout(1200)
    t = pg.inner_text('#lib-res')
    check('Monstera deliciosa' in t and 'You have this' in t and code(pg).startswith('#/library?q=monstera'), 'searching finds it, says you have it, and keeps the search in the address')
    check(pg.evaluate("document.activeElement && document.activeElement.id") == 'h-libres', 'the focus moves to the results heading')
    pg.reload(); pg.wait_for_timeout(2500)
    check('Monstera deliciosa' in pg.inner_text('#lib-res'), 'reloading shows the same search')
    pg.screenshot(path=os.path.join(OUT, 'identify-4-library.png'), full_page=True)
    pg.click('#lib-res [data-act=idnew]'); pg.wait_for_timeout(1200)
    check(code(pg) == '#/new' and pg.locator('input[name=genus]').input_value() == 'Monstera' and 'the plant library' in pg.inner_text('main') and 'picture' not in pg.inner_text('.notice.ok'),
          'Add to my plants from the library fills the form, without a picture')
    # owner settings form
    pg.goto(LOCAL + '/#/identify'); pg.wait_for_timeout(2000)
    check(pg.locator('form[data-form=idkeys] input[type=password]').count() == 2 and '…rstu' not in pg.inner_text('main') and 'rstu' in pg.inner_text('main'), 'the owner sees the key form, and only the end of each key')
    # phone width, biggest text
    ph = b.new_page(viewport={'width': 390, 'height': 844})
    ph.add_init_script("localStorage.setItem('plantdb.editor','Identify Test');localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    for u in ('/#/identify', '/#/library?q=agave&scope=world'):
        ph.goto(LOCAL + u); ph.wait_for_timeout(2500)
        check(ph.evaluate('document.documentElement.scrollWidth <= innerWidth + 1'), f'{u}: no sideways scrolling on a phone with the largest text')
    ph.screenshot(path=os.path.join(OUT, 'identify-5-phone.png'), full_page=True)
    # someone who can only view
    vw = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    vw.on('pageerror', lambda e: errs.append(str(e)))
    vw.goto(TS + '/#/identify'); vw.wait_for_timeout(2500)
    check(vw.locator('form[data-form=idkeys]').count() == 0, 'a viewer does not get the key form')
    vw.set_input_files('input[data-act=idfile]', pic('red', os.path.join(TMP, 'red.png')) and os.path.join(TMP, 'red.png')); vw.wait_for_selector('dialog[open] .id-pop', timeout=10000)
    check('P-020' in vw.inner_text('dialog[open]') and vw.locator('dialog[open] button', has_text='Add this picture').count() == 0, 'a viewer can identify, but gets no "Add this picture" button')
    vw.keyboard.press('Escape'); vw.wait_for_timeout(300)
    vw.set_input_files('input[data-act=idfile]', blue); vw.wait_for_selector('dialog[open] .id-pop', timeout=10000)
    vw.click('dialog[open] button:has-text("See the suggestions")'); vw.wait_for_timeout(500)
    check(vw.locator('#id-res [data-act=idnew]').count() == 0 and vw.locator('#id-res [data-act=idask]').count() == 0, 'and no Add or Ask buttons')
    b.close()
    # a camera on a plant it is less sure of: after a few checks in a row it asks which one it is
    y4g = os.path.join(TMP, 'green.y4m')
    with open(y4g, 'wb') as f:
        f.write(f'YUV4MPEG2 W{w} H{h} F10:1 Ip A1:1 C420jpeg\n'.encode())
        for _ in range(10): f.write(b'FRAME\n' + bytes([110]) * (w * h) + bytes([75]) * (w * h // 4) + bytes([70]) * (w * h // 4))
    b = p.chromium.launch(args=['--use-fake-ui-for-media-stream', '--use-fake-device-for-media-stream', '--use-file-for-fake-video-capture=' + y4g])
    gp = b.new_context(viewport={'width': 1280, 'height': 900}, permissions=['camera']).new_page()
    gp.on('pageerror', lambda e: errs.append(str(e)))
    gp.add_init_script("localStorage.setItem('plantdb.editor','Identify Test')")
    gp.goto(LOCAL + '/#/identify'); gp.wait_for_timeout(2500); gp.click('#id-cam-btn')
    gp.wait_for_timeout(2500)
    check('Possibly P-049' in gp.inner_text('#id-live') and gp.locator('dialog[open]').count() == 0, 'while unsure, the camera says what it thinks below the picture, without a window yet')
    gp.wait_for_selector('dialog[open] .id-pop', timeout=15000)
    check('Which one is it?' in gp.inner_text('dialog[open]'), 'after four checks in a row, it asks which one it is')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails))
sys.exit(1 if fails else 0)
