"""Checks 1.18.1: the top menu links sit side by side and wrap (from 1.26.0, once the Pages button has opened them where they fold), at every text size, on phones, iPads (including the iPad mini,
744 px wide) and computers. Before 1.18.1, at iPad width with larger text, the menu shrank to one link wide, so every link
sat on its own line. Start the mock server first, then:  python3 dev/test/header_check.py
Screenshots: dev/tmp/shots/header-*.png"""
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails = []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
MEASURE = """() => { const nav = document.querySelector('.top nav'), a = [...nav.querySelectorAll('a')].map(x => x.getBoundingClientRect());
  const rows = {}; a.forEach(r => { const k = Math.round(r.top); rows[k] = (rows[k] || 0) + 1; });
  const counts = Object.keys(rows).sort((x, y) => x - y).map(k => rows[k]);
  return { navw: nav.getBoundingClientRect().width, counts, sw: document.documentElement.scrollWidth,
           rem: parseFloat(getComputedStyle(document.documentElement).fontSize) }; }"""
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h, name in ((390, 844, 'phone'), (744, 1133, 'iPad mini'), (1133, 744, 'iPad mini, sideways'), (1024, 1366, 'iPad Pro'), (1280, 900, 'computer')):
        for size in ('100', '115', '135', '160', '190'):
            pg = b.new_page(viewport={'width': w, 'height': h})
            pg.add_init_script(f"localStorage.setItem('plantdb.editor','Header Test');localStorage.setItem('plantdb.display',JSON.stringify({{size:'{size}'}}))")
            pg.goto(BASE + '/#/plant/P-011'); pg.wait_for_timeout(1200)
            folded = pg.locator('#pages-btn').is_visible()       # 1.26.0: narrow windows and large text fold the links behind Pages
            if folded:
                check(pg.locator('#main-nav').is_hidden(), f"{name} ({w} px), text {size}%: the links fold behind the Pages button")
                pg.click('#pages-btn'); pg.wait_for_timeout(200)
            m = pg.evaluate(MEASURE)
            wide = m['navw'] >= min(w - 80, 24 * m['rem'] - 1)
            # every row but the last holds at least two links (on a phone with the largest text, long names may stand alone)
            paired = all(c >= 2 for c in m['counts'][:-1]) or (w < 500 and size in ('160', '190'))
            check(wide and paired and m['sw'] <= w + 1, f"{name} ({w} px), text {size}%: links side by side in {len(m['counts'])} rows {m['counts']}")
            if size == '135': pg.screenshot(path=os.path.join(OUT, f'header-{w}.png'), clip={'x': 0, 'y': 0, 'width': w, 'height': 420})
            pg.close()
    b.close()
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
