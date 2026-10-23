"""Checks read aloud, keyboard shortcuts and the phone top bar. The browser's speech is replaced by a recorder, so
this tests what would be read, not the voice. Start the mock server first, then:  python3 dev/test/read_check.py
Screenshots: dev/tmp/shots/read-*.png"""
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
STUB = """window.__spoken = [];
if (window.speechSynthesis) {
  speechSynthesis.speak = u => { window.__spoken.push(u.text); setTimeout(() => u.onend && u.onend(), 30); };
  speechSynthesis.cancel = () => {}; speechSynthesis.getVoices = () => [];
}"""
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
with sync_playwright() as p:
    b = p.chromium.launch()
    def page(w, h, prefs='{}'):
        pg = b.new_page(viewport={'width': w, 'height': h}); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.add_init_script("localStorage.setItem('plantdb.editor','Read Test');localStorage.setItem('plantdb.display',JSON.stringify(%s));" % prefs + STUB)
        return pg
    pg = page(1366, 900, "{navopen:'0'}")
    pg.goto(BASE + '/#/plant/P-006'); pg.wait_for_timeout(2500)
    n = pg.locator('.rd-btn').count(); check(n >= 8, f'{n} Read aloud buttons on the plant page')
    pg.locator('section#temp .rd-btn').click(); pg.wait_for_timeout(600)
    said = ' '.join(pg.evaluate('window.__spoken'))
    check('Temperature' in said and 'degrees' in said, 'Temperature section read: ' + said[:140])
    check('Read aloud' not in said and '°' not in said, 'button text and ° signs are not read out')
    pg.evaluate('window.__spoken = []'); pg.keyboard.press('r'); pg.wait_for_timeout(800)
    said = ' '.join(pg.evaluate('window.__spoken'))
    check('Sweet potato' in said and 'P 0 0 6' in said, 'R reads the whole page, codes digit by digit: ' + said[:120])
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    check(pg.locator('#rd-stop').is_hidden(), 'Escape stops reading and hides the Stop button')
    pg.keyboard.press(']'); pg.wait_for_timeout(1800)
    check(pg.url.endswith('/plant/P-007'), '] goes to the next plant')
    pg.keyboard.press('['); pg.wait_for_timeout(1800)
    check(pg.url.endswith('/plant/P-006'), '[ goes back')
    pg.keyboard.press('?'); pg.wait_for_timeout(500)
    check(pg.locator('dialog[open] h2').inner_text() == 'Keyboard shortcuts', '? lists the shortcuts')
    pg.locator('dialog[open]').screenshot(path=f'{OUT}/read-shortcuts.png'); pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    pg.screenshot(path=f'{OUT}/read-plant-light.png')
    pg.keyboard.press('h'); pg.wait_for_timeout(1500); pg.keyboard.press('/'); pg.wait_for_timeout(300)
    check(pg.evaluate("document.activeElement && document.activeElement.dataset.f") == 'q', '/ puts the cursor in the search box')
    pg.keyboard.type('fern'); pg.wait_for_timeout(500)
    check(pg.locator('#grid .sheet').count() >= 1, 'typing in the box after / still searches (shortcuts do not fire while typing)')
    pg.click('#display-btn'); pg.wait_for_timeout(500)
    check(pg.locator('dialog[open] legend:text("Reading speed")').count() == 1 and pg.locator('dialog[open] legend:text("Keyboard shortcuts")').count() == 1, 'Display settings has reading speed, voice and shortcuts')
    pg.locator('dialog[open] input[data-pref=keys][value="0"]').check(); pg.locator('dialog[open] button[value=ok]').click(); pg.wait_for_timeout(300)
    pg.goto(BASE + '/#/plant/P-006'); pg.wait_for_timeout(1800); pg.keyboard.press(']'); pg.wait_for_timeout(1200)
    check(pg.url.endswith('/plant/P-006'), 'with shortcuts off, ] does nothing')
    pg.close()
    q = page(390, 844, "{theme:'dark'}")
    q.goto(BASE + '/#/plant/P-006'); q.wait_for_timeout(2500)
    q.evaluate('window.scrollTo(0, 1400)'); q.wait_for_timeout(400)
    bottom = q.evaluate("document.querySelector('.top').getBoundingClientRect().bottom")
    check(bottom <= 0, f'phone: the top bar scrolls away (bottom at {bottom:.0f}px)')
    over = q.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth'); check(over <= 2, f'phone: no sideways scrolling ({over}px)')
    q.screenshot(path=f'{OUT}/read-phone-dark.png')
    q.close()
    b.close()
for e in errs: print('JS error:', e)
sys.exit(1 if fails or errs else 0)
