"""Browser smoke test: opens every main page at three screen sizes and fails on JavaScript errors or sideways scrolling.
Start the app first (dev/test/mock_server.py), then:  python3 dev/test/smoke.py [base-url]
Screenshots go to dev/tmp/shots/ so you can look at them."""
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
PAGES = ['#/', '#/plant/P-006', '#/plant/P-006/edit', '#/winter', '#/weather', '#/fertilizer', '#/photos', '#/labels', '#/history', '#/backups']
SIZES = {'wide': (1920, 1080), 'laptop': (1280, 800), 'phone': (390, 844)}
bad = []
with sync_playwright() as p:
    b = p.chromium.launch()
    for size, (w, h) in SIZES.items():
        for theme in ('light', 'dark'):
            pg = b.new_page(viewport={'width': w, 'height': h})
            errs = []
            pg.on('pageerror', lambda e: errs.append(str(e)))
            pg.on('console', lambda m: m.type == 'error' and errs.append(m.text))
            pg.add_init_script("localStorage.setItem('plantdb.editor','Smoke Test');localStorage.setItem('plantdb.display',JSON.stringify({theme:'%s'}))" % theme)
            for path in PAGES:
                pg.goto(BASE + '/' + path); pg.wait_for_timeout(1500)
                over = pg.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
                name = f"{size}-{theme}-{path.strip('#/').replace('/', '_') or 'plants'}.png"
                pg.screenshot(path=os.path.join(OUT, name))
                if over > 2: bad.append(f'{name}: page scrolls sideways by {over}px')
                for e in errs: bad.append(f'{name}: {e}')
                errs.clear()
            pg.close()
    b.close()
print('\n'.join(bad) if bad else 'smoke test passed: no errors, no sideways scrolling')
sys.exit(1 if bad else 0)
