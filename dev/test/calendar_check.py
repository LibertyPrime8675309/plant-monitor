"""Checks the calendar file (feeding days and cold nights as a .ics file). Start the mock server with cold weather first:
  MOCK_BASE_F=40 DATA_DIR=dev/tmp/data python3 dev/test/mock_server.py   then press Update now (or POST /api/weather/refresh)
  python3 dev/test/calendar_check.py [base-url]       screenshots go to dev/tmp/shots/calendar-*.png"""
import json, os, re, sys, urllib.request
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def get(path):
    with urllib.request.urlopen(BASE + path) as r: return r.read().decode('utf-8'), r.headers

# ---- the file itself
D = json.loads(get('/api/calendar?months=3')[0])
check(D['counts']['feed'] > 0, f"{D['counts']['feed']} feeding days in 3 months")
check(D['counts']['cold'] > 0, f"{D['counts']['cold']} cold nights in the forecast")
body, hd = get('/api/calendar.ics?months=3')
check(hd['Content-Type'].startswith('text/calendar'), 'served as text/calendar')
check('attachment' in (hd.get('Content-Disposition') or ''), 'offered as a download')
lines = body.split('\r\n')
check(lines[0] == 'BEGIN:VCALENDAR' and lines[-2] == 'END:VCALENDAR' and lines[-1] == '', 'starts and ends as a calendar, with CRLF line ends')
check(max(len(l.encode('utf-8')) for l in lines) <= 75, 'every line folded to 75 bytes or less')
check(body.count('BEGIN:VEVENT') == len(D['events']) == body.count('END:VEVENT'), f"{body.count('BEGIN:VEVENT')} events, the same as the preview")
check(body.count('BEGIN:VALARM') == len(D['events']), 'a reminder on every event')
uids = re.findall(r'\nUID:([^\r]*)', body); check(len(uids) == len(set(uids)), 'every event has its own UID')
check(re.search(r'\nDTSTART;VALUE=DATE:\d{8}\r\n', body) is not None, 'feeding days are all-day events')
check(re.search(r'\nDTSTART:\d{8}T\d{6}Z\r\n', body) is not None, 'cold nights are timed events (from the evening before)')
unf = body.replace('\r\n ', '')
check(all(',' not in l.replace('\\,', '') for l in unf.split('\r\n') if l.startswith(('SUMMARY:', 'DESCRIPTION:'))), 'commas in text are escaped')
b2, _ = get('/api/calendar.ics?feed=0&remind=0')
check('Feed ' not in b2 and 'VALARM' not in b2 and 'Cold night' in b2, 'feed=0 and remind=0 leave out feeding days and reminders')
b3 = json.loads(get('/api/calendar?close=0')[0])
check(all(e['level'] != 'watch' for e in b3['events'] if e['kind'] == 'cold'), 'close=0 leaves out nights that are only close calls')
b12 = json.loads(get('/api/calendar?months=12&cold=0')[0]); check(b12['counts']['feed'] >= D['counts']['feed'] and b12['counts']['cold'] == 0, '12 months lists at least as many feeding days')

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1366, 'height': 900}, accept_downloads=True)
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Calendar Test');localStorage.removeItem('plantdb.ics')")
    for page in ('today', 'fertilizer', 'frost'):
        pg.goto(f'{BASE}/#/{page}'); pg.wait_for_timeout(1800)
        check(pg.locator('#ics-box').count() == 1, f'"Add to your calendar" section on the {page} page')
    pg.goto(BASE + '/#/'); pg.wait_for_timeout(1200)
    check(pg.locator('#ics-box').count() == 0, 'not on the Plants page')
    pg.goto(BASE + '/#/fertilizer'); pg.wait_for_timeout(1800)
    pg.locator('#ics-box').scroll_into_view_if_needed(); pg.locator('#ics-box').screenshot(path=f'{OUT}/calendar-section-light.png')
    pg.click('[data-act=icsopen]'); pg.wait_for_timeout(1200)
    dlg = pg.locator('dialog.ics-dlg')
    check(dlg.is_visible(), 'window opens')
    check(pg.evaluate('document.activeElement.name') == 'feed', 'focus starts on the first choice, at the top of the window')
    prev = pg.locator('#ics-prev').inner_text(); print('     ' + prev.replace('\n', ' | ')[:240])
    check('feeding day' in prev and 'cold night' in prev, 'preview counts both kinds')
    for nm in ('feed', 'cold', 'close', 'remind'):
        lab = pg.locator(f'dialog.ics-dlg label:has(input[name={nm}])')
        check(lab.count() == 1 and len(lab.inner_text().strip()) > 10, f'checkbox "{nm}" has a written label')
    pg.screenshot(path=f'{OUT}/calendar-dialog-light.png')
    pg.locator('input[name=feed]').uncheck(); pg.wait_for_timeout(900)
    prev2 = pg.locator('#ics-prev').inner_text()
    check('feeding day' not in prev2 and 'cold night' in prev2, 'unticking feeding days updates the preview')
    check('feed=0' in pg.locator('#ics-link').input_value(), 'the subscribe link follows the choices')
    pg.locator('input[name=feed]').check(); pg.select_option('select[name=months]', '6'); pg.wait_for_timeout(900)
    check(json.loads(pg.evaluate("localStorage.getItem('plantdb.ics')"))['months'] == 6, 'choices are remembered in this browser')
    with pg.expect_download() as dl: pg.click('[data-act=icssave]')
    d = dl.value; path = os.path.join(OUT, '..', 'calendar.ics'); d.save_as(path)
    check(d.suggested_filename.startswith('plant-record-calendar-') and d.suggested_filename.endswith('.ics'), f'downloads {d.suggested_filename}')
    txt = open(path, encoding='utf-8').read(); check('BEGIN:VEVENT' in txt, 'the download is a calendar with events')
    check('Saved to your Downloads' in pg.locator('#ics-status').inner_text(), 'says where the file went')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300); check(not dlg.is_visible(), 'Escape closes the window')
    # phone width, dark, large text
    for theme, size in (('dark', '190'), ('light', '160')):
        q = ctx.new_page(); q.set_viewport_size({'width': 390, 'height': 844})
        q.on('pageerror', lambda e: errs.append(str(e)))
        q.add_init_script("localStorage.setItem('plantdb.display',JSON.stringify({theme:'%s',size:'%s',navopen:'0'}))" % (theme, size))
        q.goto(BASE + '/#/frost'); q.wait_for_timeout(1800)
        q.click('[data-act=icsopen]'); q.wait_for_timeout(1300)
        sw = q.evaluate('[document.querySelector("dialog.ics-dlg").scrollWidth, document.querySelector("dialog.ics-dlg").clientWidth]')
        check(sw[0] <= sw[1] + 1, f'{theme} {size}%: nothing in the window scrolls sideways ({sw})')
        q.screenshot(path=f'{OUT}/calendar-phone-{theme}.png')
        q.locator('dialog.ics-dlg details').nth(1).evaluate('d => d.open = true'); q.locator('#ics-link').scroll_into_view_if_needed()
        q.screenshot(path=f'{OUT}/calendar-phone-{theme}-link.png')
        q.close()
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs) if errs else ''))
print('\n' + ('All calendar checks passed' if not fails else f'{len(fails)} failed'))
sys.exit(1 if fails else 0)
