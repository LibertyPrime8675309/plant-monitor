"""Search by voice (prototype proto/voice-search, rebuilt on 1.42.0 with the local speech service). The browser's microphone is a
stand-in: a tone that "speaks" when the test says, so the real recording, the quiet-detection and the upload all run. The fake
speech service (dev/test/mock_speech.py, started by mock_server.py) says what the test tells it the recording said. A stand-in
speech synthesiser records what the app says aloud.
Start the app first (dev/test/mock_server.py), then:  python3 dev/test/voice_check.py [base-url]
(MOCK_SPEECH_PORT and PLANTDB_TS_PORT name the fake speech service's and the Tailscale stand-in's ports when not 8093 and 8081.)
Screenshots go to dev/tmp/shots/voice-*.png."""
import json, os, sys, time, urllib.request
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = 'http://127.0.0.1:' + os.environ.get('PLANTDB_TS_PORT', '8081')
SPEECH = 'http://127.0.0.1:' + os.environ.get('MOCK_SPEECH_PORT', '8093')
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
FAKE_MIC = """
(() => {
  window.__spoken = [];
  window.SpeechSynthesisUtterance = function (t) { this.text = t; };
  Object.defineProperty(window, 'speechSynthesis', { configurable: true, value: { speak: u => window.__spoken.push(u.text), cancel: () => {}, getVoices: () => [], addEventListener: () => {} } });
  if (!navigator.mediaDevices) return;
  window.__vsTalk = [400, 700];                 // [start after ms, talk for ms]; a long talk is stopped by a press or the 15-second limit
  navigator.mediaDevices.getUserMedia = async () => {
    window.__vsAsked = (window.__vsAsked || 0) + 1;
    if (window.__vsMicErr) { const e = new Error('refused'); e.name = window.__vsMicErr; throw e; }
    const ctx = new AudioContext(), osc = ctx.createOscillator(), gain = ctx.createGain(), dest = ctx.createMediaStreamDestination();
    osc.frequency.value = 220; gain.gain.value = 0; osc.connect(gain); gain.connect(dest); osc.start(); await ctx.resume();
    const [d, l] = window.__vsTalk;
    setTimeout(() => { gain.gain.value = 0.6; }, d); setTimeout(() => { gain.gain.value = 0; }, d + l);
    return dest.stream;
  };
})();
"""
bad = []
def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok: bad.append(what)
def speech(path, body=None):
    req = urllib.request.Request(SPEECH + path, data=json.dumps(body).encode() if body is not None else None, headers={'Content-Type': 'application/json'}, method='POST' if body is not None else 'GET')
    with urllib.request.urlopen(req, timeout=5) as r: return json.loads(r.read())
def say(text): speech('/mock/say', {'text': text})
def has_btn(pg, sel):
    return pg.locator(sel).count() >= 1 and pg.locator(sel).first.evaluate("i => { const w = (i.closest('label') || i).nextElementSibling; return !!(w && w.querySelector('.vs-btn')); }")
def wait_idle(pg, sel='.filters .vs-btn', ms=8000):           # until the button is back to "Search by voice" (recorded and sent)
    end = time.time() + ms / 1000
    while time.time() < end:
        if pg.locator(sel).first.inner_text().strip() == 'Search by voice' and pg.evaluate('!VS.busy && !VS.rec'): return True
        pg.wait_for_timeout(150)
    return False
with sync_playwright() as p:
    b = p.chromium.launch(args=['--autoplay-policy=no-user-gesture-required'])
    def page(theme='light', w=1280, h=900, size=None, extra=None, headers=None, mic=True, base=BASE):
        ctx = b.new_context(viewport={'width': w, 'height': h}, extra_http_headers=headers or {})
        pg = ctx.new_page()
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.errs = errs
        prefs = {'theme': theme, **({'size': size} if size else {}), **(extra or {})}
        pg.add_init_script("localStorage.setItem('plantdb.editor','Voice Test');localStorage.removeItem('plantdb.filters');localStorage.setItem('plantdb.morefilters','1');localStorage.setItem('plantdb.display',JSON.stringify(%s))" % json.dumps(prefs))
        pg.add_init_script(FAKE_MIC if mic else "Object.defineProperty(window, 'MediaRecorder', { value: undefined });")
        pg.base = base
        return pg
    def plants(pg):
        pg.goto(pg.base + '/#/plants'); pg.wait_for_selector('#grid .sheet'); pg.wait_for_timeout(500)
    speech('/mock/state', {'state': 'ready'})
    pg = page()
    plants(pg)
    cases = {'p 6': 'P-006', 'P 36.': 'P-036', 'P-36.': 'P-036', 'pea zero three six': 'P-036', 'P-036': 'P-036', 'p036': 'P-036', 'f 2': 'F-002',
             'Show me the monstera plants': 'monstera', 'Philodendron.': 'philodendron', 'open p six': 'P-006', 'peace lily': 'peace lily'}
    for said, want in cases.items():
        got = pg.evaluate('s => PlantVoice.clean(s).q', said)
        check(got == want, f'"{said}" becomes {want!r} (got {got!r})')
    check(pg.evaluate("PlantVoice.clean('open p six').open") is True and pg.evaluate("PlantVoice.clean('show p six').open") is False
          and pg.evaluate("PlantVoice.clean('take me to the weather').open") is True, '"open", "go to" and "take me to" open; "show" only searches')
    pages = {'weather': '#/weather', 'Today': '#/', 'grow lights': '#/lights', 'coming inside': '#/inside', 'the cold night checklist page': '#/frost',
             'all plants': '#/plants', 'audit log': '#/history', 'lights': '#/lights', 'mushrooms': '#/fungi', 'peace lily': None}
    for said, want in pages.items():
        got = pg.evaluate('s => PlantVoice.page(s)', said)
        check(got == want, f'the page for "{said}" is {want!r} (got {got!r})')
    check(pg.evaluate("typeof webkitSpeechRecognition === 'undefined' || !document.querySelector('script[src*=voice]') || !String(vsStart).includes('SpeechRecognition')"),
          "the browser's own speech recognition (Google or Microsoft) is not used")
    btn = pg.locator('.filters .vs-btn').first
    check(btn.count() == 1 and btn.is_visible(), 'the Plants page has a Search by voice button')
    check('Search by voice' in (btn.get_attribute('aria-label') or ''), 'the button has a full label')
    check(pg.evaluate("document.querySelector('.filters label input[data-f=q]').labels[0].textContent.trim()") == 'Search', 'the search box keeps its own label')
    # one search: it records, stops by itself after the pause, sends the recording to this computer and fills the box
    say('p 6'); pg.evaluate("window.__spoken = []; window.__vsTalk = [400, 700]")
    t0 = time.time(); btn.click(); pg.wait_for_timeout(250)
    check(btn.get_attribute('aria-pressed') == 'true' and 'Listening' in btn.inner_text(), 'while listening it says so in words')
    pg.screenshot(path=os.path.join(OUT, 'voice-laptop-listening.png'))
    check(wait_idle(pg), 'it stops by itself after the pause, and sends')
    took = time.time() - t0
    check(2.0 < took < 6.5, f'about 1.5 seconds of quiet after speaking ends the recording ({took:.1f} s in all)')
    last = speech('/mock/last')
    check(last.get('bytes', 0) > 500 and 'webm' in (last.get('type') or '') + (last.get('name') or ''), f'a real recording reached the speech service ({last.get("bytes")} bytes, {last.get("type")})')
    check('Grow lights' in last.get('prompt', '') and 'P-036' in last.get('prompt', ''), 'with the page names and codes as a prompt')
    check(pg.input_value('.filters input[data-f=q]') == 'P-006', 'what was heard goes in the search box, tidied')
    check(pg.locator('#grid .sheet').count() == 1, 'the list shows the one plant')
    msg = pg.locator('.filters .vs-msg').inner_text(); check('One plant matches' in msg, f'the message says how many match ({msg})')
    spoken = pg.evaluate('window.__spoken')
    check(spoken == [msg], f'answer 1: the line is said aloud in the Read aloud voice ({spoken})')
    pg.screenshot(path=os.path.join(OUT, 'voice-laptop-heard.png'))
    # pressing again while it listens stops it and sends what it has
    say('monstera'); pg.evaluate("window.__vsTalk = [300, 10000]")
    btn.click(); pg.wait_for_timeout(1500); btn.click()
    check(wait_idle(pg) and pg.input_value('.filters input[data-f=q]') == 'monstera', 'pressing again stops it and sends what it has')
    # nothing said
    pg.evaluate("window.__vsTalk = [99999, 0]"); btn.click(); pg.wait_for_timeout(7600)
    check('did not hear anything' in pg.locator('.filters .vs-msg').inner_text() and pg.evaluate('!VS.rec'), 'nothing said: it stops after a few seconds and says so')
    say('open p six'); pg.evaluate("window.__vsTalk = [300, 600]"); btn.click(); pg.wait_for_timeout(4500)
    check(pg.url.endswith('#/plant/P-006'), '"open p six" opens the plant page')
    # answer 2: "open" and a page name opens the page, from any search box
    plants(pg); say('Open weather.')
    pg.locator('.filters .vs-btn').click(); pg.wait_for_timeout(4500)
    check(pg.url.endswith('#/weather'), '"open weather" opens the Weather page')
    plants(pg); say('go to coming inside')
    pg.locator('.filters .vs-btn').click(); pg.wait_for_timeout(4500)
    check(pg.url.endswith('#/inside'), '"go to coming inside" opens Coming inside')
    plants(pg); say('open philodendron')
    pg.locator('.filters .vs-btn').click(); pg.wait_for_timeout(4500)
    m = pg.locator('.filters .vs-msg').inner_text()
    check(pg.url.endswith('#/plants') and 'plants match' in m and 'one of their codes' in m and pg.input_value('.filters input[data-f=q]') == 'philodendron',
          f'several plants match: the list is filtered and it asks for a code ({m})')
    pg.evaluate("window.__vsMicErr = 'NotAllowedError'"); pg.locator('.filters .vs-btn').click(); pg.wait_for_timeout(800)
    check('not allowed to use the microphone' in pg.locator('.filters .vs-msg').inner_text(), 'a refused microphone is explained')
    pg.evaluate("window.__vsMicErr = 'NotFoundError'"); pg.locator('.filters .vs-btn').click(); pg.wait_for_timeout(800)
    check('No microphone was found' in pg.locator('.filters .vs-msg').inner_text(), 'no microphone is explained')
    pg.evaluate("window.__vsMicErr = null")
    say('peace lily'); pg.mouse.click(5, 300); pg.keyboard.press('v'); pg.wait_for_timeout(4500)
    check(pg.input_value('.filters input[data-f=q]') == 'peace lily', 'the V key searches by voice')
    # the V key on a page with no search box: the Search window, listening; "open today" from there
    pg.goto(BASE + '/#/lights'); pg.wait_for_timeout(2500); say('open today')
    pg.mouse.click(5, 300); pg.keyboard.press('v'); pg.wait_for_timeout(4500)
    check(pg.evaluate("location.hash") in ('#/', '') and pg.locator('dialog[open]').count() == 0, 'V on a page with no search box listens in the Search window; "open today" goes to Today')
    searches = (('#/library', 'input[data-f=libq]'), ('#/fungi', 'input[data-f=muq]'), ('#/identify', 'input[data-f=q]'), ('#/history', 'input[data-f=audq]'), ('#/plant/P-006', 'input[data-f=q]'))
    for path, sel in searches:
        pg.goto(BASE + '/' + path); pg.wait_for_timeout(2500)
        check(has_btn(pg, sel), f'{path} search has a button too')
    pg.goto(BASE + '/#/identify'); pg.wait_for_timeout(2500)
    check('Search by voice is ready' in pg.locator('#vs-st').inner_text(), "the Identify page shows the speech service's state under the picture checker's")
    pg.goto(BASE + '/#/history'); pg.wait_for_timeout(2000); say('watered')
    pg.evaluate("document.querySelectorAll('#aud-fbox, details').forEach(d => d.open = true)"); pg.wait_for_timeout(200)     # the audit log's filters are folded (1.39.1)
    pg.locator('.aud-filters .vs-btn').click(); pg.wait_for_timeout(4500)
    check(pg.input_value('.aud-filters input[data-f=audq]') == 'watered', 'the Audit log search is filled')
    pg.click('[data-act=search]'); pg.wait_for_timeout(500)
    check(has_btn(pg, '#srch-q'), 'the Search window has a button too')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    pg.mouse.click(5, 300); pg.keyboard.press('Shift+Slash'); pg.wait_for_timeout(400)
    check('Search by voice' in pg.locator('#dlg').inner_text(), 'the shortcuts list has V')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    # the speech service still getting ready, or not running: said in plain words when the button is pressed
    speech('/mock/state', {'state': 'setting up'}); plants(pg)
    pg.locator('.filters .vs-btn').click(); pg.wait_for_timeout(1200)
    m = pg.locator('.filters .vs-msg').inner_text()
    check('getting ready' in m and '465 MB' in m and pg.evaluate('!VS.rec'), f'not ready yet: it says so and does not record ({m[:90]})')
    pg.goto(BASE + '/#/identify'); pg.wait_for_timeout(2500)
    check('getting ready' in pg.locator('#vs-st').inner_text() and '120 of 484 MB' in pg.locator('#vs-st').inner_text(), 'and the Identify page shows how far the download has got')
    speech('/mock/state', {'state': 'ready'})
    # answer 3: Display can hide them (and V goes too), or keep them without speaking
    pg.evaluate("PlantPrefs.set('vsearch', '0')"); plants(pg)
    check(pg.locator('.filters .vs-btn').count() == 1 and not pg.locator('.filters .vs-btn').is_visible(), 'answer 3: hidden in Display, the button is not shown')
    asked = pg.evaluate('window.__vsAsked || 0'); pg.mouse.click(5, 300); pg.keyboard.press('v'); pg.wait_for_timeout(900)
    check(pg.evaluate('window.__vsAsked || 0') == asked, 'and the V key does nothing')
    pg.mouse.click(5, 300); pg.keyboard.press('Shift+Slash'); pg.wait_for_timeout(400)
    check('Search by voice' not in pg.locator('#dlg').inner_text(), 'nor is V in the shortcuts list'); pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    pg.evaluate("PlantPrefs.set('vsearch', 'quiet'); window.__spoken = []"); plants(pg); say('monstera')
    pg.locator('.filters .vs-btn').click(); pg.wait_for_timeout(4500)
    check(pg.locator('.filters .vs-btn').is_visible() and 'Heard' in pg.locator('.filters .vs-msg').inner_text() and pg.evaluate('window.__spoken') == [],
          '"do not speak": the button and the line, nothing said aloud')
    pg.evaluate("PlantPrefs.set('vsearch', '1')")
    pg.locator('#display-btn').evaluate('b => b.click()'); pg.wait_for_timeout(1200)
    fs = pg.locator('dialog fieldset', has=pg.locator('legend', has_text='Search by voice'))
    check(fs.count() == 1 and fs.locator('input[type=radio]').count() == 3, 'Display has the Search by voice choice, with three options')
    check('ready' in pg.locator('#vs-dv-st').inner_text() and 'on this computer' in pg.locator('#vs-dv-st').inner_text(), "Display says the speech service is ready, on this computer")
    pg.locator('dialog .dv-tab:has-text("Keyboard and voice")').click(); pg.wait_for_timeout(600)
    fs.scroll_into_view_if_needed(); pg.wait_for_timeout(300)
    pg.screenshot(path=os.path.join(OUT, 'voice-laptop-display.png'))
    check(not pg.errs, 'no JavaScript errors: ' + '; '.join(pg.errs)); pg.context.close()
    # a viewer (through Tailscale) can search by voice: it changes nothing
    E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan Schmidtke'}
    G = {'Tailscale-User-Login': 'sam@example.net', 'Tailscale-User-Name': 'Sam Rivera'}
    urllib.request.urlopen(urllib.request.Request(TS + '/api/me', headers=E), timeout=10).read()
    pg = page(headers=G, base=TS); plants(pg)
    check(pg.evaluate("ME().role") == 'viewer', 'signed in as a viewer')
    say('monstera'); pg.locator('.filters .vs-btn').click(); pg.wait_for_timeout(4500)
    check(pg.input_value('.filters input[data-f=q]') == 'monstera' and 'Heard' in pg.locator('.filters .vs-msg').inner_text(), 'a viewer can search by voice too')
    pg.context.close()
    pg = page(mic=False); plants(pg)
    check(pg.locator('.vs-btn').count() == 0, 'browsers that cannot record show no button')
    pg.context.close()
    for theme in ('light', 'dark'):
        for nm, (w, h, size) in {'phone': (390, 844, None), 'phone-bigtext': (390, 844, '190')}.items():
            pg = page(theme, w, h, size=size); plants(pg); say('monstera')
            pg.locator('.filters .vs-btn').click(); pg.wait_for_timeout(4500)
            over = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            check(over <= 2, f'{nm} {theme}: no sideways scrolling ({over})')
            pg.locator('.filters').first.scroll_into_view_if_needed(); pg.screenshot(path=os.path.join(OUT, f'voice-{nm}-{theme}.png'))
            pg.context.close()
    b.close()
print('\n' + ('All voice search checks passed.' if not bad else f'{len(bad)} failed.'))
sys.exit(1 if bad else 0)
