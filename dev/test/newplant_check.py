"""Checks 1.17.1: the "Add a plant" form opens, saves a plant with just a common name, and the new plant's location
starts as Outdoors. (Before 1.17.1 the form stopped with "Assignment to constant variable".)
Start the mock server with a fresh data folder first, then:  python3 dev/test/newplant_check.py"""
import json, os, sys, urllib.error, urllib.request
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
    pg.goto(BASE + '/#/plants'); pg.wait_for_timeout(2000)
    pg.click('a[href="#/new"]'); pg.wait_for_timeout(1500)
    check(pg.locator('form[data-form=new]').count() == 1 and 'Something went wrong' not in pg.inner_text('main'), 'Add a plant opens the form')
    check(pg.locator('[name=__side][value=out]').is_checked(), 'the plant starts as Outside (1.29.0: Inside or outside, then the area)')
    bg = lambda v: pg.locator(f'[name=__side][value={v}] + span').evaluate('e => getComputedStyle(e).backgroundColor')
    check(pg.locator('[name=__side] + span').count() == 2 and bg('out') != bg('in'), '1.56.4: Outside and Inside are buttons, and the chosen one looks different')
    pg.locator('label:has([name=__side][value=in])').click(); pg.wait_for_timeout(200)
    check(pg.locator('[name=__side][value=in]').is_checked() and bg('in') != bg('out'), 'pressing Inside chooses it and shows it')
    pg.locator('label:has([name=__side][value=out])').click(); pg.wait_for_timeout(200)
    # 1.58.0: Date acquired, a date box with a real label, on the form and then on the plant's page
    box = pg.locator('form[data-form=new] input[name=acquired_on]')
    check(box.count() == 1 and box.get_attribute('type') == 'date' and pg.evaluate("document.querySelector('form[data-form=new] input[name=acquired_on]').labels[0].textContent.startsWith('Date acquired')"),
          'the form has a Date acquired box, a date, with its label')
    box.fill('2024-05-17')
    pg.fill('input[name=common_name]', 'Test basil'); pg.click('form[data-form=new] button[type=submit]'); pg.wait_for_timeout(2000)
    code = pg.evaluate('location.hash').split('/')[-1]
    r = json.loads(urllib.request.urlopen(BASE + '/api/plants/' + code).read())
    check(r['common_name'] == 'Test basil' and r['site'] == 'Outdoors' and pg.evaluate('location.hash').startswith('#/plant/P-'), f'saving adds the plant ({code}) and opens its page')
    check(r['acquired_on'] == '2024-05-17', 'the date is saved with the plant')
    words = pg.evaluate("(() => { const dt = [...document.querySelectorAll('main dt')].find(x => x.textContent.trim() === 'Date acquired'); return dt ? dt.nextElementSibling.textContent : ''; })()")
    check('2024' in words and '2 years and 5 months ago' in words or '2 years and 6 months ago' in words, f'its page says Date acquired and how long ago ({words!r})')
    pg.goto(BASE + f'/#/plant/{code}/edit'); pg.wait_for_selector('form input[name=acquired_on]')
    check(pg.input_value('form input[name=acquired_on]') == '2024-05-17', 'Edit shows the saved date')
    def put(v):
        ver = json.loads(urllib.request.urlopen(BASE + '/api/plants/' + code).read())['version']
        req = urllib.request.Request(BASE + '/api/plants/' + code, data=json.dumps({'base_version': ver, 'fields': {'acquired_on': v}}).encode(), method='PUT', headers={'Content-Type': 'application/json', 'X-Editor': 'Check'})
        try: return urllib.request.urlopen(req).status
        except urllib.error.HTTPError as e: return e.code
    check(put('2999-01-01') == 400 and put('last spring') == 400 and put('') == 200 and json.loads(urllib.request.urlopen(BASE + '/api/plants/' + code).read())['acquired_on'] in ('', None),
          'a day in the future or words are refused; an empty box clears it')
    pg.goto(BASE + f'/#/plant/{code}'); pg.wait_for_timeout(1500)
    check('Date acquired' not in pg.inner_text('main dl'), 'a page with no date does not show the line')
    b.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
