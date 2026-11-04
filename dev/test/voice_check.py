"""Search by voice (prototype proto/voice-search). A stand-in speech recogniser says what the test tells it to.
Start the app first (dev/test/mock_server.py), then:  python3 dev/test/voice_check.py [base-url]
Screenshots go to dev/tmp/shots/voice-*.png."""
import json, os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
FAKE = """
class FakeRec {
  start() { this.t = setTimeout(() => {
    if (window.__vsErr) { this.onerror && this.onerror({ error: window.__vsErr }); this.onend && this.onend(); return; }
    if (window.__vsHold) return;
    const say = window.__vsSay || '';
    const mk = (t, fin) => { const r = [{ transcript: t }]; r.isFinal = fin; return { results: [r] }; };
    this.onresult && this.onresult(mk(say.split(' ')[0], false));
    setTimeout(() => { this.onresult && this.onresult(mk(say, true)); this.onend && this.onend(); }, 150);
  }, 300); }
  abort() { clearTimeout(this.t); this.onerror && this.onerror({ error: 'aborted' }); this.onend && this.onend(); }
  stop() { this.abort(); }
}
window.webkitSpeechRecognition = FakeRec; window.SpeechRecognition = FakeRec;
"""
bad = []
def check(ok, what):
    print(('ok   ' if ok else 'FAIL ') + what)
    if not ok: bad.append(what)
with sync_playwright() as p:
    b = p.chromium.launch()
    def page(theme='light', w=1280, h=900, fake=True, size=None):
        pg = b.new_page(viewport={'width': w, 'height': h})
        errs = []; pg.on('pageerror', lambda e: errs.append(str(e))); pg.errs = errs
        prefs = {'theme': theme, **({'size': size} if size else {})}
        pg.add_init_script("localStorage.setItem('plantdb.editor','Voice Test');localStorage.removeItem('plantdb.filters');localStorage.setItem('plantdb.display',JSON.stringify(%s))" % json.dumps(prefs))
        pg.add_init_script(FAKE if fake else "delete window.webkitSpeechRecognition; delete window.SpeechRecognition;")
        return pg
    pg = page()
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#grid .sheet'); pg.wait_for_timeout(500)
    cases = {'p 6': 'P-006', 'P 36.': 'P-036', 'pea zero three six': 'P-036', 'P-036': 'P-036', 'p036': 'P-036', 'f 2': 'F-002',
             'Show me the monstera plants': 'monstera', 'Philodendron.': 'philodendron', 'open p six': 'P-006', 'peace lily': 'peace lily'}
    for said, want in cases.items():
        got = pg.evaluate('s => PlantVoice.clean(s).q', said)
        check(got == want, f'"{said}" becomes {want!r} (got {got!r})')
    check(pg.evaluate("PlantVoice.clean('open p six').open") is True and pg.evaluate("PlantVoice.clean('show p six').open") is False, '"open" opens, "show" only searches')
    btn = pg.locator('.filters .vs-btn').first
    check(btn.count() == 1 and btn.is_visible(), 'the Plants page has a Search by voice button')
    check('Search by voice' in (btn.get_attribute('aria-label') or ''), 'the button has a full label')
    check(pg.evaluate("document.querySelector('.filters label input[data-f=q]').labels[0].textContent.trim()") == 'Search', 'the search box keeps its own label')
    pg.evaluate("window.__vsHold = true"); btn.click(); pg.wait_for_timeout(200)
    check(btn.get_attribute('aria-pressed') == 'true' and 'Listening' in btn.inner_text(), 'while listening it says so in words')
    pg.screenshot(path=os.path.join(OUT, 'voice-laptop-listening.png'))
    btn.click(); pg.wait_for_timeout(200)
    check(btn.get_attribute('aria-pressed') == 'false' and 'Stopped' in pg.locator('.filters .vs-msg').inner_text(), 'pressing again stops')
    pg.evaluate("window.__vsHold = false; window.__vsSay = 'p 6'"); btn.click(); pg.wait_for_timeout(900)
    check(pg.input_value('.filters input[data-f=q]') == 'P-006', 'what was heard goes in the search box, tidied')
    check(pg.locator('#grid .sheet').count() == 1, 'the list shows the one plant')
    msg = pg.locator('.filters .vs-msg').inner_text(); check('One plant matches' in msg, f'the message says how many match ({msg})')
    pg.screenshot(path=os.path.join(OUT, 'voice-laptop-heard.png'))
    pg.evaluate("window.__vsSay = 'open p six'"); btn.click(); pg.wait_for_timeout(1200)
    check(pg.url.endswith('#/plant/P-006'), '"open p six" opens the plant page')
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#grid .sheet'); pg.wait_for_timeout(400)
    pg.evaluate("window.__vsErr = 'not-allowed'"); pg.locator('.filters .vs-btn').click(); pg.wait_for_timeout(700)
    check('not allowed to use the microphone' in pg.locator('.filters .vs-msg').inner_text(), 'a refused microphone is explained')
    pg.evaluate("window.__vsErr = null; window.__vsSay = 'philodendron'")
    pg.mouse.click(5, 5); pg.keyboard.press('v'); pg.wait_for_timeout(900)
    check(pg.input_value('.filters input[data-f=q]') == 'philodendron', 'the V key searches by voice')
    pg.goto(BASE + '/#/library'); pg.wait_for_timeout(2500)
    check(pg.locator('input[data-f=libq]').count() == 1 and pg.locator('input[data-f=libq]').evaluate("i => !!i.closest('label').nextElementSibling.querySelector('.vs-btn')"), 'the Library search has a button too')
    for path, sel in (('#/fungi', 'input[data-f=muq]'), ('#/identify', 'input[data-f=q]')):
        pg.goto(BASE + '/' + path); pg.wait_for_timeout(2500)
        check(pg.locator(sel).count() >= 1 and pg.locator(sel).first.evaluate("i => !!i.closest('label').nextElementSibling.querySelector('.vs-btn')"), f'{path} search has a button too')
    pg.goto(BASE + '/#/history'); pg.wait_for_timeout(2000)
    check(pg.locator('.aud-filters .vs-btn').count() == 1, 'the Audit log search has a button too')
    pg.evaluate("window.__vsSay = 'watered'"); pg.locator('.aud-filters .vs-btn').click(); pg.wait_for_timeout(900)
    check(pg.input_value('.aud-filters input[data-f=audq]') == 'watered', 'the Audit log search is filled')
    pg.keyboard.press('Shift+Slash'); pg.wait_for_timeout(400)
    check('Search by voice' in pg.locator('#dlg').inner_text(), 'the shortcuts list has V')
    check(not pg.errs, 'no JavaScript errors: ' + '; '.join(pg.errs)); pg.close()
    pg = page(fake=False); pg.goto(BASE + '/#/'); pg.wait_for_selector('#grid .sheet'); pg.wait_for_timeout(500)
    check(pg.locator('.vs-btn').count() == 0, 'browsers with no speech recognition show no button')
    pg.close()
    for theme in ('light', 'dark'):
        for nm, (w, h, size) in {'phone': (390, 844, None), 'phone-bigtext': (390, 844, '190')}.items():
            pg = page(theme, w, h, size=size); pg.goto(BASE + '/#/'); pg.wait_for_selector('#grid .sheet'); pg.wait_for_timeout(500)
            pg.evaluate("window.__vsSay = 'monstera'"); pg.locator('.filters .vs-btn').click(); pg.wait_for_timeout(900)
            over = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            check(over <= 2, f'{nm} {theme}: no sideways scrolling ({over})')
            pg.locator('.filters').first.scroll_into_view_if_needed(); pg.screenshot(path=os.path.join(OUT, f'voice-{nm}-{theme}.png'))
            pg.close()
    b.close()
print('\n' + ('All voice search checks passed.' if not bad else f'{len(bad)} failed.'))
sys.exit(1 if bad else 0)
