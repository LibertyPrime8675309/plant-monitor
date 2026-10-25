"""Checks the calendar (feeding days and cold nights as a .ics file and a subscription link). Start the mock server with cold weather first:
  MOCK_BASE_F=40 DATA_DIR=dev/tmp/data python3 dev/test/mock_server.py   then press Update now (or POST /api/weather/refresh)
  python3 dev/test/calendar_check.py [base-url]       screenshots go to dev/tmp/shots/calendar-*.png"""
import json, os, re, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def get(path):
    with urllib.request.urlopen(BASE + path) as r: return r.read().decode('utf-8'), r.headers

def send(method, path, body=None):
    rq = urllib.request.Request(BASE + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                headers={'Content-Type': 'application/json', 'X-Editor': 'Calendar Test'})
    with urllib.request.urlopen(rq) as r: return json.loads(r.read())
def status(path):
    try:
        with urllib.request.urlopen(BASE + path) as r: return r.status
    except urllib.error.HTTPError as e: return e.code
from datetime import date

# start from the defaults
DEF = {'feed': True, 'cold': True, 'close': True, 'months': 3, 'weekly': True, 'day': 5, 'feed_remind': True, 'feed_at': '08:00', 'cold_remind': True, 'cold_at': '16:00', 'public_base': ''}
S0 = send('PUT', '/api/calendar/settings', DEF)
check(S0['options'] == DEF and S0['days'][5] == 'Saturday', 'choices saved and read back')

# ---- the file itself
D = json.loads(get('/api/calendar?months=3')[0])
check(D['counts']['feed'] > 0, f"{D['counts']['feed']} weekly feeding days in 3 months")
check(all(date.fromisoformat(e['date']).weekday() == 5 for e in D['events'] if e['kind'] == 'feed'), 'weekly: every feeding day is a Saturday')
check(all(e['title'].startswith('Feeding day: ') for e in D['events'] if e['kind'] == 'feed'), 'weekly events are called "Feeding day"')
check(D['counts']['cold'] > 0, f"{D['counts']['cold']} cold nights in the forecast")
Dd = json.loads(get('/api/calendar?weekly=0')[0])
check(len({date.fromisoformat(e['date']).weekday() for e in Dd['events'] if e['kind'] == 'feed'}) >= 1 and any(e['title'].startswith('Feed ') for e in Dd['events']), 'weekly=0: each plant on its own due day')
Dw = json.loads(get('/api/calendar?day=2')[0])
check(all(date.fromisoformat(e['date']).weekday() == 2 for e in Dw['events'] if e['kind'] == 'feed'), 'day=2: every feeding day is a Wednesday')
body, hd = get('/api/calendar.ics?months=3')
check(hd['Content-Type'].startswith('text/calendar'), 'served as text/calendar')
check('attachment' in (hd.get('Content-Disposition') or ''), 'offered as a download')
lines = body.split('\r\n')
check(lines[0] == 'BEGIN:VCALENDAR' and lines[-2] == 'END:VCALENDAR' and lines[-1] == '', 'starts and ends as a calendar, with CRLF line ends')
check(max(len(l.encode('utf-8')) for l in lines) <= 75, 'every line folded to 75 bytes or less')
check(body.count('BEGIN:VEVENT') == len(D['events']) == body.count('END:VEVENT'), f"{body.count('BEGIN:VEVENT')} events, the same as the preview")
check(body.count('BEGIN:VALARM') == len(D['events']), 'a reminder on every event')
check('TRIGGER;RELATED=START:PT8H0M' in body, 'feeding reminder at 08:00 on the day')
b7, _ = get('/api/calendar.ics?feed_at=07:30&cold_at=19:15')
check('TRIGGER;RELATED=START:PT7H30M' in b7, 'feeding reminder time can be changed (07:30)')
cold = [e for e in D['events'] if e['kind'] == 'cold']
trig = re.findall(r'TRIGGER;VALUE=DATE-TIME:(\d{8}T\d{6}Z)', b7)
check(trig and all(t.endswith(('001500Z', '011500Z')) for t in trig), f'cold-night reminder time can be changed (19:15 Central = {trig[:1]})')
uids = re.findall(r'\nUID:([^\r]*)', body); check(len(uids) == len(set(uids)), 'every event has its own UID')
check(re.search(r'\nDTSTART;VALUE=DATE:\d{8}\r\n', body) is not None, 'feeding days are all-day events')
check(re.search(r'\nDTSTART:\d{8}T\d{6}Z\r\n', body) is not None, 'cold nights are timed events (from the evening before)')
unf = body.replace('\r\n ', '')
check(all(',' not in l.replace('\\,', '') for l in unf.split('\r\n') if l.startswith(('SUMMARY:', 'DESCRIPTION:'))), 'commas in text are escaped')
b2, _ = get('/api/calendar.ics?feed=0&feed_remind=0&cold_remind=0')
check('SUMMARY:Feed' not in b2 and 'VALARM' not in b2 and 'Cold night' in b2, 'feed=0 and reminders off leave out feeding days and reminders')
b3 = json.loads(get('/api/calendar?close=0')[0])
check(all(e['level'] != 'watch' for e in b3['events'] if e['kind'] == 'cold'), 'close=0 leaves out nights that are only close calls')
b12 = json.loads(get('/api/calendar?months=12&cold=0')[0]); check(b12['counts']['feed'] >= D['counts']['feed'] and b12['counts']['cold'] == 0, '12 months lists at least as many feeding days')
try: send('PUT', '/api/calendar/settings', {'feed_at': '25:00'}); check(False, 'a bad time is refused')
except urllib.error.HTTPError as e: check(e.code == 400, 'a bad time is refused')
try: send('PUT', '/api/calendar/settings', {'public_base': 'javascript:alert(1)'}); check(False, 'a bad internet address is refused')
except urllib.error.HTTPError as e: check(e.code == 400, 'a bad internet address is refused')

# ---- the subscribed calendar
link = D['links']['local']; tok = link.rsplit('/', 1)[1]
check(status('/cal/' + tok) == 200, 'the subscription link works')
check(status('/cal/wrong-token.ics') == 404, 'a wrong token gets nothing')
send('PUT', '/api/calendar/settings', {'weekly': False, 'cold': False})
sub, _ = get('/cal/' + tok)
check('Cold night' not in sub and 'SUMMARY:Feeding day' not in sub and 'SUMMARY:Feed ' in sub, 'the subscribed calendar follows the saved choices')
send('PUT', '/api/calendar/settings', DEF)
S = send('PUT', '/api/calendar/settings', {'public_base': 'https://my-pc.example.ts.net/'})
check(S['links']['public'] == 'https://my-pc.example.ts.net/cal/' + tok, 'the internet address goes into the link')
N = send('POST', '/api/calendar/new-link')
check(status('/cal/' + tok) == 404 and status('/cal/' + N['links']['local'].rsplit('/', 1)[1]) == 200, 'a new link replaces the old one')
send('PUT', '/api/calendar/settings', DEF)
A = send('GET', '/api/audit?limit=20')
A = A if isinstance(A, list) else A.get('entries', [])
check(any('Calendar choices changed' in (x.get('note') or '') for x in A), 'changing the choices is in the audit log')

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 1366, 'height': 900}, accept_downloads=True)
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Calendar Test')")
    for page in ('today', 'fertilizer', 'frost'):
        pg.goto(f'{BASE}/#/{page}'); pg.wait_for_timeout(1800)
        check(pg.locator('#ics-box').count() == 1, f'"Add to your calendar" section on the {page} page')
    pg.goto(BASE + '/#/'); pg.wait_for_timeout(1200)
    check(pg.locator('#ics-box').count() == 0, 'not on the Plants page')
    pg.goto(BASE + '/#/fertilizer'); pg.wait_for_timeout(1800)
    pg.locator('#ics-box').scroll_into_view_if_needed(); pg.locator('#ics-box').screenshot(path=f'{OUT}/calendar-section-light.png')
    pg.click('[data-act=icsopen]'); pg.wait_for_timeout(1500)
    dlg = pg.locator('dialog.ics-dlg')
    check(dlg.is_visible(), 'window opens')
    check(pg.evaluate('document.activeElement.name') == 'feed', 'focus starts on the first choice, at the top of the window')
    prev = pg.locator('#ics-prev').inner_text(); print('     ' + prev.replace('\n', ' | ')[:240])
    check('weekly feeding day' in prev and 'cold night' in prev, 'preview counts both kinds')
    for sel in ('input[name=feed]', 'input[name=cold]', 'input[name=close]', 'input[name=weekly][value="1"]', 'input[name=weekly][value="0"]', 'input[name=feed_remind]', 'input[name=cold_remind]', 'select[name=day]', 'select[name=months]', 'input[name=feed_at]', 'input[name=cold_at]', '#ics-link', '#ics-pub'):
        lab = pg.locator(f'dialog.ics-dlg label:has({sel})')
        check(lab.count() == 1 and len(lab.inner_text().strip()) > 3, f'{sel} has a written label')
    pg.screenshot(path=f'{OUT}/calendar-dialog-light.png')
    pg.locator('input[name=feed]').uncheck(); pg.wait_for_timeout(1000)
    prev2 = pg.locator('#ics-prev').inner_text()
    check('feeding day' not in prev2 and 'cold night' in prev2, 'unticking feeding days updates the preview')
    check('Saved' in pg.locator('#ics-status').inner_text(), 'says the choice was saved')
    pg.locator('input[name=feed]').check(); pg.wait_for_timeout(600)
    pg.select_option('select[name=day]', '6'); pg.wait_for_timeout(1000)
    days = pg.locator('#ics-prev li:has(.k-feed) b').all_inner_texts()
    check(days and all(t.startswith('Sun') for t in days), f'choosing Sunday moves the feeding days ({days[:2]})')
    pg.fill('input[name=feed_at]', '07:30'); pg.locator('input[name=feed_at]').dispatch_event('change'); pg.wait_for_timeout(900)
    check(send('GET', '/api/calendar/settings')['options']['feed_at'] == '07:30', 'reminder time saved from the window')
    check('7:30' in pg.locator('#ics-prev').inner_text(), 'preview says the new reminder time')
    pg.locator('input[name=weekly][value="0"]').check(); pg.wait_for_timeout(1000)
    check(send('GET', '/api/calendar/settings')['options']['weekly'] is False, '"Each day a plant is due" saved')
    pg.locator('input[name=weekly][value="1"]').check(); pg.wait_for_timeout(800)
    check('home network' in pg.locator('#ics-linkwhere').inner_text(), 'says the link only works at home without an internet address')
    pg.fill('#ics-pub', 'https://my-pc.example.ts.net'); pg.click('[data-act=icspub]'); pg.wait_for_timeout(900)
    check(pg.locator('#ics-link').input_value().startswith('https://my-pc.example.ts.net/cal/'), 'saving the internet address changes the link')
    pg.locator('dialog.ics-dlg details').evaluate('d => d.open = true')
    pg.locator('dialog.ics-dlg').screenshot(path=f'{OUT}/calendar-dialog-full-light.png')
    with pg.expect_download() as dl: pg.click('[data-act=icssave]')
    d = dl.value; path = os.path.join(OUT, '..', 'calendar.ics'); d.save_as(path)
    check(d.suggested_filename.startswith('plant-record-calendar-') and d.suggested_filename.endswith('.ics'), f'downloads {d.suggested_filename}')
    txt = open(path, encoding='utf-8').read(); check('BEGIN:VEVENT' in txt and 'PT7H30M' in txt, 'the download is a calendar with the saved choices')
    check('Saved to your Downloads' in pg.locator('#ics-status').inner_text(), 'says where the file went')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300); check(not dlg.is_visible(), 'Escape closes the window')
    # phone width, dark, large text
    for theme, size in (('dark', '190'), ('light', '160')):
        q = ctx.new_page(); q.set_viewport_size({'width': 390, 'height': 844})
        q.on('pageerror', lambda e: errs.append(str(e)))
        q.add_init_script("localStorage.setItem('plantdb.display',JSON.stringify({theme:'%s',size:'%s',navopen:'0'}))" % (theme, size))
        q.goto(BASE + '/#/frost'); q.wait_for_timeout(1800)
        q.click('[data-act=icsopen]'); q.wait_for_timeout(1500)
        q.locator('dialog.ics-dlg details').evaluate('d => d.open = true')
        sw = q.evaluate('[document.querySelector("dialog.ics-dlg").scrollWidth, document.querySelector("dialog.ics-dlg").clientWidth]')
        check(sw[0] <= sw[1] + 1, f'{theme} {size}%: nothing in the window scrolls sideways ({sw})')
        q.screenshot(path=f'{OUT}/calendar-phone-{theme}.png')
        q.locator('.ics-rem').first.scroll_into_view_if_needed(); q.screenshot(path=f'{OUT}/calendar-phone-{theme}-rem.png')
        q.locator('#ics-link').scroll_into_view_if_needed(); q.screenshot(path=f'{OUT}/calendar-phone-{theme}-link.png')
        q.close()
    b.close()
send('PUT', '/api/calendar/settings', DEF)
check(not errs, 'no script errors' + (': ' + '; '.join(errs) if errs else ''))
print('\n' + ('All calendar checks passed' if not fails else f'{len(fails)} failed'))
sys.exit(1 if fails else 0)
