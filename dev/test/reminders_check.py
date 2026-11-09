"""Checks the prototype "Reminders" (proto/reminders): add a reminder from the Reminders page and from a plant's page, Today when one
is due, Done (with a repeat), "Not done yet", "A week later", Change and Remove, viewers, at laptop and phone width, light and dark,
with large text. Start the mock server with a fresh data folder, then: python3 dev/test/reminders_check.py
Screenshots: dev/tmp/shots/reminders-*.png"""
import json, os, sys, urllib.request
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
BASE = 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None):
    req = urllib.request.Request(BASE + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Remind Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
R = lambda q='': call('GET', '/api/reminders' + q)
today = R()['today']
plants = call('GET', '/api/plants'); A, B = plants[0], plants[1]
late = (date.fromisoformat(today) - timedelta(days=2)).isoformat()
# one that is already late (written straight into the API with today's date, then moved back: the API refuses a past date for a new one)
x = call('POST', '/api/reminders', {'text': 'Look for new roots on the cutting', 'due_on': today, 'plant': B['code']})
call('PUT', f"/api/reminders/{x['id']}", {'due_on': late})
check(next(r for r in R()['open'] if r['id'] == x['id'])['state'] == 'late', 'a reminder past its day is late')
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Remind Test')")
    pg.goto(BASE + '/#/reminders'); pg.wait_for_selector('#rm-due')
    check(pg.locator('#sub-nav a[aria-current=page]').inner_text().strip() == 'Reminders', 'the page is in the Today row, as "Reminders"')
    check(pg.evaluate("document.documentElement.dataset.toptall") != '1', 'the top bar stays short on a laptop')
    check('Late:' in pg.inner_text('#rm-due') and '2 days late: it was due' in pg.inner_text('#rm-due'), 'a late one says so in words, not only colour')
    # add one for no plant, repeating
    pg.click('[data-act=rmnew]'); pg.wait_for_selector('dialog[open] form.rm-dlg')
    check(pg.locator('dialog[open] label:has(input[name=text])').count() == 1 and pg.locator('dialog[open] label:has(select[name=plant])').count() == 1, 'the window has real labels')
    check(pg.locator('dialog[open] input[name=when][value="7"]').is_checked(), '"In a week" is chosen to start with')
    pg.fill('dialog[open] input[name=text]', 'Buy potting mix')
    pg.check('dialog[open] input[name=when][value="1"]'); pg.select_option('dialog[open] select[name=repeat]', '30')
    pg.locator('dialog[open]').screenshot(path=os.path.join(OUT, 'reminders-1-dialog.png'))
    pg.click('dialog[open] button[value=ok]'); pg.wait_for_timeout(1500)
    nx = next((r for r in R()['open'] if r['text'] == 'Buy potting mix'), None)
    check(nx and nx['plant_code'] is None and nx['due_on'] == (date.fromisoformat(today) + timedelta(days=1)).isoformat() and nx['repeat_days'] == 30,
          'Add the reminder saves it for tomorrow, every month, for no plant')
    check(pg.locator('#rm-later .rm-job').count() == 1, 'it is under Coming up')
    pg.screenshot(path=os.path.join(OUT, 'reminders-2-page.png'), full_page=True)
    # a plant's page
    pg.goto(BASE + f"/#/plant/{A['code']}"); pg.wait_for_selector('#rm-plant', timeout=15000)
    check('none set' in pg.inner_text('#rm-plant'), "a plant's page says when it has no reminders")
    pg.click('#rm-plant [data-act=rmnew]'); pg.wait_for_selector('dialog[open] form.rm-dlg')
    check(A['common_name'] in pg.inner_text('dialog[open] h2') and pg.locator('dialog[open] select[name=plant]').count() == 0, 'from a plant, the window is for that plant')
    pg.fill('dialog[open] input[name=text]', 'Spray again for mealybugs'); pg.check('dialog[open] input[name=when][value=day]')
    pg.fill('dialog[open] input[name=day]', today); pg.select_option('dialog[open] select[name=repeat]', '7')
    pg.click('dialog[open] button[value=ok]'); pg.wait_for_selector('#rm-plant .rm-job', timeout=8000)
    check('Due today' in pg.inner_text('#rm-plant') and 'Every week' in pg.inner_text('#rm-plant'), 'it is listed on the plant page: due today, every week')
    pg.evaluate("document.querySelectorAll('#toasts > *').forEach(t => t.remove())")
    pg.evaluate("document.querySelector('#rm-plant').scrollIntoView({block: 'center'})"); pg.wait_for_timeout(200)
    pg.locator('.quick').screenshot(path=os.path.join(OUT, 'reminders-3-plant.png'))
    # Today
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#today-remind', timeout=15000)
    check(pg.inner_text('#today-remind h2') == 'Reminders (2)', 'Today has "Reminders" with the two due (one late, one today)')
    check(pg.locator('.td-jumps a[data-sec=today-remind]').inner_text() == 'Reminders (2)', 'and a jump button for it')
    check('Buy potting mix' not in pg.inner_text('#today-remind'), "tomorrow's reminder is not on Today yet")
    pg.locator('#today-remind').screenshot(path=os.path.join(OUT, 'reminders-4-today.png'))
    # Done, with a repeat
    rid = next(r['id'] for r in R()['open'] if r['text'] == 'Spray again for mealybugs')
    pg.click(f'#today-remind [data-rm="{rid}"] [data-act=rmdone]'); pg.wait_for_timeout(1500)
    wk = (date.fromisoformat(today) + timedelta(days=7)).isoformat()
    check(any(r['text'] == 'Spray again for mealybugs' and r['due_on'] == wk for r in R()['open']), 'Done on a weekly one sets the next for a week from today')
    check(pg.inner_text('#today-remind h2') == 'Reminders (1)', 'and Today counts one fewer')
    check(pg.evaluate("!!document.activeElement && document.activeElement.tagName === 'BUTTON'"), 'the focus lands on a button, not lost')
    # A week later
    pg.click(f'#today-remind [data-rm="{x["id"]}"] [data-act=rmlater]'); pg.wait_for_timeout(1500)
    check(next(r for r in R()['open'] if r['id'] == x['id'])['due_on'] == wk, 'A week later on a late one moves it to a week from today')
    check(pg.locator('#today-remind').count() == 0, 'with nothing due, Today has no Reminders section')
    # Not done yet, on the page
    pg.goto(BASE + '/#/reminders'); pg.wait_for_selector('#rm-done')
    pg.click(f'#rm-done [data-rm="{rid}"] [data-act=rmundo]'); pg.wait_for_timeout(1500)
    check(any(r['id'] == rid and r['due_on'] == today for r in R()['open']) and not any(r['due_on'] == wk and r['text'].startswith('Spray') for r in R()['open']),
          '"Not done yet" puts it back and takes back the next one')
    # Change: text and date; then Remove
    pg.click(f'[data-rm="{x["id"]}"] [data-act=rmedit]'); pg.wait_for_selector('dialog[open] form.rm-dlg')
    check(pg.locator('dialog[open] input[name=when][value=""]').is_checked(), 'Change keeps the date unless you choose another')
    pg.fill('dialog[open] input[name=text]', 'Look for roots, and pot it up if there are some'); pg.click('dialog[open] button[value=ok]'); pg.wait_for_timeout(1500)
    rx = next(r for r in R()['open'] if r['id'] == x['id'])
    check(rx['text'].startswith('Look for roots, and pot') and rx['due_on'] == wk, 'Change saves the new words and keeps the date')
    pg.click(f'[data-rm="{x["id"]}"] [data-act=rmedit]'); pg.wait_for_selector('dialog[open] form.rm-dlg')
    pg.click('dialog[open] button[value=del]'); pg.wait_for_selector('dialog[open] h2:text("Remove this reminder?")')
    pg.click('dialog[open] button[value=ok]'); pg.wait_for_timeout(1500)
    check(not any(r['id'] == x['id'] for r in R()['open']), 'Remove it (after asking) takes it off the list')
    check(any((a.get('note') or '').startswith('Reminder removed') for a in call('GET', '/api/audit?n=30')), 'and the audit log has it')
    # keyboard: Tab reaches Add a reminder and Enter opens the window
    pg.goto(BASE + '/#/reminders'); pg.wait_for_selector('#rm-due')
    pg.focus('[data-act=rmnew]'); pg.keyboard.press('Enter'); pg.wait_for_selector('dialog[open] form.rm-dlg')
    check(pg.evaluate("document.activeElement.name") == 'text', 'Enter on Add a reminder opens the window with the focus in "What to do"')
    pg.keyboard.press('Escape'); pg.wait_for_timeout(300)
    pg.evaluate("document.documentElement.dataset.role = 'viewer'")
    check(pg.locator('[data-act^=rm]:visible').count() == 0, 'people who can only view do not see the buttons')
    # phone, dark and large text
    for name, disp in (('phone-light', {}), ('phone-dark-big', {'theme': 'dark', 'size': '160'})):
        ph = br.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        ph.on('pageerror', lambda e: errs.append(str(e)))
        ph.add_init_script("localStorage.setItem('plantdb.editor','Remind Test');localStorage.setItem('plantdb.display', JSON.stringify(%s))" % json.dumps(disp))
        ph.goto(BASE + '/#/reminders'); ph.wait_for_selector('#rm-due'); ph.wait_for_timeout(800)
        over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 0, f'{name}: nothing scrolls sideways ({over}px)')
        ph.evaluate("window.scrollTo(0, document.querySelector('#app h1').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'reminders-5-{name}.png'))
        ph.goto(BASE + '/#/'); ph.wait_for_selector('#today-remind', timeout=15000); ph.wait_for_timeout(500)
        ph.evaluate("window.scrollTo(0, document.getElementById('today-remind').getBoundingClientRect().top + window.scrollY - 8)"); ph.wait_for_timeout(300)
        over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 0, f'{name}: Today fits too ({over}px)')
        ph.screenshot(path=os.path.join(OUT, f'reminders-5-{name}-today.png'))
        ph.goto(BASE + f"/#/plant/{A['code']}"); ph.wait_for_selector('#rm-plant .rm-job', timeout=15000); ph.wait_for_timeout(500)
        ph.evaluate("document.querySelector('#rm-plant').scrollIntoView({block: 'center'})"); ph.wait_for_timeout(300)
        ph.screenshot(path=os.path.join(OUT, f'reminders-5-{name}-plant.png'))
        ph.click('#rm-plant [data-act=rmnew]'); ph.wait_for_selector('dialog[open]'); ph.wait_for_timeout(300)
        over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 0, f'{name}: the window fits too')
        ph.screenshot(path=os.path.join(OUT, f'reminders-5-{name}-dialog.png'))
        ph.close()
    br.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
