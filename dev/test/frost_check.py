"""Checks the frost alert and the cold-night checklist. Start the mock server with cold weather first:
  MOCK_BASE_F=40 DATA_DIR=dev/tmp/data python3 dev/test/mock_server.py   then press Update now (or POST /api/weather/refresh)
  python3 dev/test/frost_check.py [base-url]       screenshots go to dev/tmp/shots/frost-*.png"""
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
errs, fails = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': 1366, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Frost Test')")
    pg.goto(BASE + '/#/plants'); pg.wait_for_timeout(2000)
    ban = pg.locator('.fz-banner')
    check(ban.count() == 1, 'banner shows on the Plants page')
    print('     ' + ban.inner_text().replace('\n', ' | ')[:300])
    pg.screenshot(path=f'{OUT}/frost-banner-light.png')
    pg.goto(BASE + '/#/plant/P-031'); pg.wait_for_timeout(1500)
    check(pg.locator('.fz-note').count() == 1, 'plant page shows its own frost risk')
    check(pg.locator('.fz-banner').count() == 0, 'no banner on a plant page (its own note is enough)')
    pg.click('.fz-note a[href="#/frost"]'); pg.wait_for_timeout(1500)
    check('Cold-night checklist' in pg.locator('h1').inner_text(), 'checklist page opens')
    check(pg.locator('.fz-banner').count() == 0, 'no banner on the checklist page itself')
    groups = pg.locator('section.blk[id^=fz-]'); check(groups.count() >= 1, f'{groups.count()} groups of plants listed')
    pg.screenshot(path=f'{OUT}/frost-checklist-light.png', full_page=False)
    # cover the first plant that has a Covered button
    row = pg.locator('.fz-row:has(button[data-act=frostcover])').first; code = row.get_attribute('data-code')
    row.locator('button[data-act=frostcover]').click(); pg.wait_for_timeout(1500)
    check(pg.locator(f'.fz-row[data-code="{code}"].is-done').count() == 1, f'{code} ticked as covered')
    focused = pg.evaluate('document.activeElement && document.activeElement.textContent')
    check('Undo' in (focused or ''), f'focus stays on that plant (on "{focused}")')
    # move a plant indoors: it leaves the list
    row = pg.locator('.fz-row:has(button[data-act=frostin])').first; code2 = row.get_attribute('data-code')
    row.locator('button[data-act=frostin]').click()
    for _ in range(12):
        pg.wait_for_timeout(500)
        if pg.locator(f'.fz-row[data-code="{code2}"]').count() == 0: break
    check(pg.locator(f'.fz-row[data-code="{code2}"]').count() == 0, f'{code2} moved indoors and left the list')
    pg.locator('#fz-in').screenshot(path=f'{OUT}/frost-group-light.png')
    pg.locator('.fz-row').first.screenshot(path=f'{OUT}/frost-row-light.png')
    # undo the cover
    pg.locator(f'.fz-row[data-code="{code}"] button[data-act=frostundo]').first.click(); pg.wait_for_timeout(1500)
    check(pg.locator(f'.fz-row[data-code="{code}"].is-done').count() == 0, 'undo works')
    # the table counts covered plants
    check(pg.locator('.fz-tbl tbody tr').count() == 7, 'seven nights in the table')
    # hide the banner
    pg.goto(BASE + '/#/winter'); pg.wait_for_timeout(1500)
    pg.click('button[data-act=frosthide]'); pg.wait_for_timeout(500)
    pg.goto(BASE + '/#/plants'); pg.wait_for_timeout(1500)
    check(pg.locator('.fz-banner').count() == 0, 'hidden banner stays hidden')
    pg.evaluate("localStorage.removeItem('plantdb.frosthide')")
    for name, vp, theme in [('phone-dark', (390, 844), 'dark'), ('wide-dark', (1920, 1080), 'dark')]:
        q = b.new_page(viewport={'width': vp[0], 'height': vp[1]}); q.on('pageerror', lambda e: errs.append(str(e)))
        q.add_init_script("localStorage.setItem('plantdb.editor','Frost Test');localStorage.setItem('plantdb.display',JSON.stringify({theme:'%s'}))" % theme)
        q.goto(BASE + '/#/plants'); q.wait_for_timeout(1800); q.screenshot(path=f'{OUT}/frost-banner-{name}.png')
        q.goto(BASE + '/#/frost'); q.wait_for_timeout(1800); q.screenshot(path=f'{OUT}/frost-checklist-{name}.png')
        over = q.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
        check(over <= 2, f'{name}: no sideways scrolling ({over}px)')
        q.close()
    # 1.58.0 (November 12 review, item 8): each night says its own numbers. Made-up forecasts are put in the page's place, since the mock's is whatever the date makes it.
    t = b.new_page(viewport={'width': 1366, 'height': 900}); t.on('pageerror', lambda e: errs.append(str(e)))
    t.add_init_script("localStorage.setItem('plantdb.editor','Frost Test')")
    t.goto(BASE + '/#/today'); t.wait_for_timeout(2500)
    say = lambda nights: t.evaluate('''nights => {
      const keep = FROST, LV = { danger: 3, damage: 2, watch: 1 }, day = k => addDays(keep.today, k);
      const some = (n, level, done) => Array.from({ length: n || 0 }, (_, i) => ({ code: 'T-' + level + i, name: 'x', level, done: i < (done || 0) ? { by: 'me', at: '' } : null }));
      const ns = nights.map(([k, low, c, done]) => ({ date: day(k), low, counts: { danger: c.danger || 0, damage: c.damage || 0, watch: c.watch || 0 },
        level: c.danger ? 'danger' : c.damage ? 'damage' : c.watch ? 'watch' : null, plants: [...some(c.danger, 'danger', done), ...some(c.damage, 'damage', c.danger ? 0 : done), ...some(c.watch, 'watch', c.danger || c.damage ? 0 : done)] }));
      const at = ns.filter(n => n.level), worst = at.reduce((w, n) => !w || LV[n.level] > LV[w.level] || (n.level === w.level && n.low < w.low) ? n : w, null);
      FROST = Object.assign({}, keep, { nights: ns, worst, first: at[0], outdoor: 86 });
      const el = document.createElement('div'); el.innerHTML = rend(frostBanner(true));
      const out = { text: el.textContent.replace(/\\s+/g, ' ').trim(), today: fzToday(), by: [0, 1, 5].map(k => fzActBy(day(k))) };
      FROST = keep; return out; }''', nights)
    r = say([[0, 61, {'watch': 1}], [5, 50, {'damage': 11, 'watch': 14}]])           # what his own Today showed on November 12
    print('     ' + r['text'][:420])
    check('11 would be damaged and 14 are close calls that night' in r['text'] and 'at 61°F: 1 is a close call' in r['text'], 'a close call tonight and a cold night later: each night has its own numbers')
    check('before dark today' not in r['text'] and '1 is a close call, and nothing would be damaged.' in r['text'] and f"Bring them in or cover them {r['by'][2]}, before the first night" in r['text'], 'the deadline is the evening before the first night that would damage a plant, not today')
    check(r['today']['n'] == 1 and r['today']['bit'].startswith('1 close call today') and 'and a cold night' in r['today']['bit'], f"Today counts tonight's one plant and names both nights: {r['today']}")
    r = say([[0, 45, {'damage': 3, 'watch': 2}]])
    check('3 would be damaged and 2 are close calls that night. Bring them in or cover them before dark today.' in r['text'] and r['today'] == {'n': 5, 'bit': r['today']['bit']} and r['today']['bit'].startswith('a cold night today'),
          'a night that would damage plants tonight still says before dark today')
    r = say([[1, 58, {'watch': 4}]])
    check('None is forecast to be damaged' in r['text'] and 'To be safe, bring them in or cover them this evening' in r['text'] and r['today']['n'] == 4 and r['today']['bit'].startswith('4 close calls tomorrow'),
          'close calls only: it says nothing is forecast to be damaged, and why to cover them anyway')
    r = say([[0, 45, {'damage': 3}, 1]])
    check('before dark today. 1 is already marked as covered.' in r['text'] and r['today']['n'] == 2, 'plants ticked as covered are not counted again')
    r = say([[0, 45, {'damage': 3}, 3]])
    check('All 3 are marked as covered for today' in r['text'] and r['today']['n'] == 0 and r['today']['bit'] == '', 'when all are covered Today stops asking')
    r = say([[0, 48, {'damage': 2}], [3, 30, {'danger': 5, 'damage': 10}]])
    check('at 48°F: 2 would be damaged. Bring those in or cover them before dark today. The checklist says which night each of the others needs it by.' in r['text'] and r['today']['n'] == 2,
          'two plants tonight and a freeze later: tonight\'s two first')
    # and on the page itself: the button counts the next cold night's plants that are still to do
    import json, urllib.request
    F = json.load(urllib.request.urlopen(BASE + '/api/frost'))
    first = next((n for n in F['nights'] if n['level']), None)
    if first:
        left = sum(1 for x in first['plants'] if not x.get('done'))
        jump = t.locator('.td-jumps a[data-sec=today-cold]')
        check((jump.count() == 1 and jump.inner_text() == f'Cold night ({left})') if left else jump.count() == 0, f"Today's button counts the next cold night's {left} plants, not the worst night's ({sum(F['worst']['counts'].values())})")
        t.locator('#today-cold').screenshot(path=f'{OUT}/frost-today.png')
    t.close()
    b.close()
for e in errs: print('JS error:', e)
sys.exit(1 if fails or errs else 0)
