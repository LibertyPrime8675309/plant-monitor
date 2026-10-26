"""Checks 1.17.1: the "Add a plant" form opens, saves a plant with just a common name, and the new plant's location
starts as Outdoors. (Before 1.17.1 the form stopped with "Assignment to constant variable".)
Start the mock server with a fresh data folder first, then:  python3 dev/test/newplant_check.py"""
import json, os, sys, urllib.request
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','New Plant Test')")
    pg.goto(BASE + '/'); pg.wait_for_timeout(2000)
    pg.click('a[href="#/new"]'); pg.wait_for_timeout(1500)
    check(pg.locator('form[data-form=new]').count() == 1 and 'Something went wrong' not in pg.inner_text('main'), 'Add a plant opens the form')
    check(pg.locator('select[name=site]').input_value() == 'Outdoors', 'the location starts as Outdoors')
    pg.fill('input[name=common_name]', 'Test basil'); pg.click('form[data-form=new] button[type=submit]'); pg.wait_for_timeout(2000)
    code = pg.evaluate('location.hash').split('/')[-1]
    r = json.loads(urllib.request.urlopen(BASE + '/api/plants/' + code).read())
    check(r['common_name'] == 'Test basil' and r['site'] == 'Outdoors' and pg.evaluate('location.hash').startswith('#/plant/P-'), f'saving adds the plant ({code}) and opens its page')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
