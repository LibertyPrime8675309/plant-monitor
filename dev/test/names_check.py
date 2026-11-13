"""Checks the small accessibility things from the November 12 review (item 11, 1.58.0), on every page in the top bar and a few more,
on a computer in the light theme and on a phone in the dark theme:

- A control's spoken name starts with, or at least contains, the words it shows (WCAG 2.5.3). "Read aloud" was named "Read the
  Water section aloud", so saying "click Read aloud" to voice control found nothing. 395 controls on these pages were like that.
- All text is at 7 to 1 against what is behind it. The health and winter-plan tags, "Damaged" and the Remove buttons were 6.3 to
  6.8 to 1 in the light theme; in the dark theme the camera box on Identify was near-white with white words on it.
- A table that scrolls inside its box can be reached with Tab and scrolled with the arrow keys; one that fits is not a Tab stop.

A page added later is checked too (the list comes from the top bar), so a new page has to meet the same bar.
Start the mock server with a fresh data folder, then:  python3 dev/test/names_check.py [base-url]"""
import sys
from playwright.sync_api import sync_playwright
from waits import until
BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)

NAMES = r'''() => {
  const norm = s => (s || '').toLowerCase().replace(/[^a-z0-9 ]+/g, ' ').replace(/\s+/g, ' ').trim();
  const shown = el => { let t = ''; const walk = n => { for (const c of n.childNodes) {
      if (c.nodeType === 3) t += c.textContent; else if (c.nodeType === 1) { const cs = getComputedStyle(c);
        if (c.getAttribute('aria-hidden') === 'true' || cs.display === 'none' || cs.visibility === 'hidden' || c.classList.contains('sr')) continue; walk(c); } } }; walk(el); return t.replace(/\s+/g, ' ').trim(); };
  const out = [];
  for (const el of document.querySelectorAll('button[aria-label], a[aria-label], summary[aria-label], [role=button][aria-label]')) {
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    const vis = shown(el), label = el.getAttribute('aria-label');
    if (!vis || !/[a-z]/i.test(vis)) continue;                                   // an icon or a symbol alone: the label is its only name
    if (!norm(label).includes(norm(vis))) out.push(`"${vis.slice(0, 40)}" is named "${label.slice(0, 70)}"`);
  }
  return out; }'''
CONTRAST = r'''() => {
  const lum = c => { const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const parse = s => { const m = /rgba?\(([^)]+)\)/.exec(s); if (!m) return null; const p = m[1].split(/[ ,\/]+/).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const over = (top, under) => { const a = top[3]; return [0, 1, 2].map(i => top[i] * a + under[i] * (1 - a)).concat(1); };
  const bgOf = el => { const stack = []; for (let e = el; e; e = e.parentElement) { const cs = getComputedStyle(e); if (cs.backgroundImage !== 'none') return null;      // a picture or a gradient: not judged here
      const c = parse(cs.backgroundColor); if (c && c[3] > 0) { stack.push(c); if (c[3] === 1) break; } }
    let b = parse(getComputedStyle(document.documentElement).backgroundColor) || [255, 255, 255, 1]; if (b[3] < 1) b = [255, 255, 255, 1];
    for (const c of stack.reverse()) b = over(c, b); return b; };
  const out = [], seen = new Set(), walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const t = walker.currentNode, el = t.parentElement; if (!el || !t.textContent.trim() || seen.has(el)) continue; seen.add(el);
    const cs = getComputedStyle(el); if (cs.visibility === 'hidden' || cs.display === 'none' || el.closest('[disabled],[aria-disabled=true],option,.ph-n,.photo-wrap figcaption')) continue;
    const r = el.getBoundingClientRect(); if (!r.width || !r.height) continue;
    const bg = bgOf(el); let fg = parse(cs.color); if (!fg || !bg) continue; fg = over(fg, bg);
    const L1 = lum(fg), L2 = lum(bg), cr = (Math.max(L1, L2) + 0.05) / (Math.min(L1, L2) + 0.05);
    if (cr < 6.95) out.push(`${cr.toFixed(2)} to 1: "${t.textContent.trim().slice(0, 30)}" (${el.tagName.toLowerCase()}.${[...el.classList].join('.')})`);
  }
  return out; }'''

with sync_playwright() as p:
    b = p.chromium.launch()
    total = {'names': 0, 'contrast': 0, 'pages': 0}
    for name, vp, mob, theme in [('computer, light theme', (1707, 960), False, 'light'), ('phone, dark theme', (412, 915), True, 'dark')]:
        ctx = b.new_context(viewport={'width': vp[0], 'height': vp[1]}, is_mobile=mob, has_touch=mob, service_workers='block')
        ctx.add_init_script("localStorage.setItem('plantdb.editor','Names Test');localStorage.setItem('plantdb.display',JSON.stringify({theme:'%s'}))" % theme)
        pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.goto(BASE + '/#/'); until(pg, lambda: pg.locator('#app h1').count() > 0)
        pages = pg.evaluate("[...new Set(SECTIONS.flatMap(s => s[2].map(x => x[2])))]") + ['#/plant/P-031', '#/plant/P-031/edit', '#/mixes', '#/guide', '#/compare', '#/health', '#/repotting', '#/turning']
        bad_names, bad_contrast = {}, {}
        for h in pages:
            pg.goto(BASE + '/' + h)
            until(pg, lambda: pg.locator('#app h1').count() > 0 and pg.locator('#app[aria-busy=true]').count() == 0)
            pg.wait_for_timeout(1500)                                            # the parts a page fills in after it is drawn
            n, c = pg.evaluate(NAMES), pg.evaluate(CONTRAST)
            if n: bad_names[h] = n
            if c: bad_contrast[h] = c
        total['pages'] += len(pages)
        check(not bad_names, f'{name}: on {len(pages)} pages every control\'s spoken name has the words it shows' +
              (': ' + '; '.join(f'{h} {v[0]} ({len(v)})' for h, v in list(bad_names.items())[:4]) if bad_names else ''))
        check(not bad_contrast, f'{name}: all text is at 7 to 1 or better' + (': ' + '; '.join(f'{h} {v[0]} ({len(v)})' for h, v in list(bad_contrast.items())[:4]) if bad_contrast else ''))
        if theme == 'light':
            # the name of the button that says who is editing starts with what it shows
            who = pg.locator('button.who'); t = who.inner_text().strip()
            check(t.startswith('Editing as') and (who.get_attribute('aria-label') or '').startswith(t), f'"{t}" is named "{who.get_attribute("aria-label")}"')
            rd = pg.locator('button[data-act=readsec]').first
            if rd.count(): check((rd.get_attribute('aria-label') or '').startswith('Read aloud: '), 'Read aloud buttons are named "Read aloud: the ... section"')
            # a calendar day: its number and badge first, then the full date
            pg.goto(BASE + '/#/fertilizer'); until(pg, lambda: pg.locator('table.cal button.day').count() > 20)
            day = pg.locator('table.cal button.day').first; shown = ' '.join(day.inner_text().split()); lab = day.get_attribute('aria-label')
            check(lab.startswith(shown + '. ') and ', 20' in lab, f'a calendar day shows "{shown}" and is named "{lab[:70]}"')
            # the long weather table scrolls from the keyboard
            pg.goto(BASE + '/#/weather'); until(pg, lambda: pg.locator('.tbl-wrap.wide').count() > 0, 30000)
            w = pg.locator('.tbl-wrap.wide').first; w.scroll_into_view_if_needed()
            check(until(pg, lambda: w.get_attribute('tabindex') == '0') and w.get_attribute('role') == 'region' and 'Scroll it with the arrow keys' in (w.get_attribute('aria-label') or ''),
                  f'the long weather table is a Tab stop with a name: "{w.get_attribute("aria-label")}"')
            def scrolls():                                                           # the page may draw its table once more just after it opens, so this is tried until it holds
                w.focus(); x0, y0 = w.evaluate('e => [e.scrollLeft, e.scrollTop]')
                pg.keyboard.press('ArrowRight'); pg.keyboard.press('ArrowDown'); pg.wait_for_timeout(200)
                x1, y1 = w.evaluate('e => [e.scrollLeft, e.scrollTop]')
                return x1 > x0 and y1 > y0
            check(until(pg, scrolls, 15000, 400), 'with the keyboard on it, the arrow keys scroll it sideways and down')
            check(pg.evaluate("document.activeElement.matches('.tbl-wrap') && getComputedStyle(document.activeElement).outlineStyle !== 'none'"), 'and it shows where the keyboard is')
            fit = pg.evaluate("[...document.querySelectorAll('.tbl-wrap')].filter(w => w.scrollWidth <= w.clientWidth + 1 && w.scrollHeight <= w.clientHeight + 1 && w.hasAttribute('tabindex')).length")
            check(fit == 0, 'a table that fits is not a Tab stop')
        else:
            pg.goto(BASE + '/#/identify'); until(pg, lambda: pg.locator('.id-view').count() > 0)
            bg = pg.evaluate("getComputedStyle(document.querySelector('.id-view')).backgroundColor")
            check(bg == 'rgb(11, 20, 26)', f'dark theme: the camera box is dark behind its white words ({bg})')
            pg.goto(BASE + '/#/weather'); until(pg, lambda: pg.locator('.tbl-wrap.wide').count() > 0, 30000)
            check(until(pg, lambda: pg.locator('.tbl-wrap.wide').first.get_attribute('tabindex') == '0'), 'phone: the weather table is a Tab stop too')
            check(not pg.evaluate('document.documentElement.scrollWidth > innerWidth + 1'), 'phone: nothing scrolls sideways')
        ctx.close()
    b.close()
check(not errs, 'no script errors' + (': ' + '; '.join(errs[:3]) if errs else ''))
print('\n' + ('All names checks passed' if not fails else f'{len(fails)} names check(s) failed'))
sys.exit(1 if fails else 0)
