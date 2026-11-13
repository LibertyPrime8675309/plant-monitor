"""Checks the prototype "Propagation" (proto/propagation): starting a cutting or a seed lot, what is recorded (looks, water changes, roots,
sprouts, losses), seed treatment steps that end by themselves, potting up into a plant with its own P-code and the parent's care
details, the family tree, what the attempts show, the pieces on Today, the plant page and the guide, at laptop and phone width, light
and dark, with large text. Start the mock server with a fresh data folder, then:
python3 dev/test/propagation_check.py      Screenshots: dev/tmp/shots/propagation-*.png"""
import json, os, sys, urllib.error, urllib.request
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
                                 headers={'Content-Type': 'application/json', 'X-Editor': 'Prop Test'}, method=m)
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'null')
def status(m, url, body=None):
    try: call(m, url, body); return 200
    except urllib.error.HTTPError as e: return e.code
A = lambda: call('GET', '/api/propagations')
plants = {p['code']: p for p in call('GET', '/api/plants')}
parent = next(c for c, p in sorted(plants.items()) if p['site'] == 'Indoors' and not p.get('home_id'))
pname = plants[parent]['common_name']
n_plants0 = len(plants)
maxn = max(int(p['code'][2:]) for p in call('GET', '/api/plants?status=all'))
t0 = A(); today = date.fromisoformat(t0['today'])
iso = lambda n: (today - timedelta(days=n)).isoformat()
check(t0['items'] == [] and t0['counts'] == dict(active=0, due=0, finished=0) and len(t0['methods']) == 12, 'a fresh install has no attempts and offers twelve ways')
check(call('GET', '/api/propagations/tree') == dict(roots=[], outside=[]), 'and the family tree is empty')
# ---- a cutting in water, 10 days ago: due for a look and a water change
a = call('POST', '/api/propagations', dict(method='stem', parent_code=parent, count=3, started_on=iso(10), medium='Water', place='Kitchen window'))
check(a['code'] == 'PR-001' and a['title'] == f'{pname}: stem cutting' and a['check_every'] == 7 and a['species'], 'a cutting in water is PR-001, named from its parent, to be looked at every 7 days')
check(a['due'] and a['due'][0]['kind'] == 'check' and 'last looked 10 days ago' in a['due'][0]['words'], 'and it is due for a look, saying how long it has been')
check(status('POST', '/api/propagations', dict(method='nonsense')) == 400 and status('POST', '/api/propagations', dict(method='stem', count=0)) == 400
      and status('POST', '/api/propagations', dict(method='stem', started_on='2999-01-01')) == 400 and status('POST', '/api/propagations', dict(method='stem', parent_code='P-999')) == 404,
      'an unknown way, none of them, a start date in the future and a plant that does not exist are refused')
call('POST', f"/api/propagations/{a['id']}/events", dict(kind='water'))
a1 = call('GET', f"/api/propagations/{a['id']}")
check(not a1['due'] and a1['last_seen'] == today.isoformat(), 'changing the water starts the clock again')
check(status('POST', f"/api/propagations/{a['id']}/events", dict(kind='sprouted')) == 400 and status('POST', f"/api/propagations/{a['id']}/events", dict(kind='note')) == 400
      and status('POST', f"/api/propagations/{a['id']}/events", dict(kind='check', on_date=iso(20))) == 400, 'Sprouted needs a number, a note needs words, and nothing can be dated before it started')
e = call('POST', f"/api/propagations/{a['id']}/events", dict(kind='roots', on_date=iso(2)))
check(any(x['word'] == 'Roots seen' for x in e['card']['events']), 'roots seen is recorded with its date')
call('DELETE', f"/api/propagations/events/{e['id']}")
check(not any(x['kind'] == 'roots' for x in call('GET', f"/api/propagations/{a['id']}")['events']), 'and can be taken back')
call('POST', f"/api/propagations/{a['id']}/events", dict(kind='roots', on_date=iso(2)))
# ---- pot it up: a real plant with its own P-code and the parent's care details
pr = call('POST', f"/api/propagations/{a['id']}/promote", dict(common_name=pname + ' cutting', site='Indoors'))
child = pr['code']; cp = call('GET', f'/api/plants/{child}')
check(child == f'P-{maxn + 1:03d}' and len(call('GET', '/api/plants')) == n_plants0 + 1, f'potting up makes a plant with the next P-code ({child})')
pp = plants[parent]; full = call('GET', f'/api/plants/{parent}')
check(cp['common_name'] == pname + ' cutting' and cp['scientific_name'] == full['scientific_name'] and cp['light_summary'] == full['light_summary']
      and cp['temp_ideal_low'] == full['temp_ideal_low'], 'it has the parent\'s species details (names, light, temperatures)')
check(f'stem cutting of {parent}' in cp['notes'] and 'PR-001' in cp['notes'] and cp['spot_id'] is None and cp['pot_id'] is None and not cp['photos'], 'its notes say where it came from; it has no shelf spot, pot or photos of its own')
check(pr['card']['status'] == 'active' and len(pr['card']['children']) == 1 and pr['card']['left'] == 2, 'three pieces, one potted: two are left and it is still going')
call('POST', f"/api/propagations/{a['id']}/events", dict(kind='lost', n=1))
pr2 = call('POST', f"/api/propagations/{a['id']}/promote", dict(common_name=pname + ' cutting 2'))
check(pr2['card']['status'] == 'done' and pr2['card']['left'] == 0 and pr2['card']['ended_on'] == today.isoformat(), 'one lost and the other potted: it finishes by itself')
check(status('POST', f"/api/propagations/{a['id']}/promote", dict(common_name='Too many')) == 409, 'nothing more can be potted up from it')
check(status('DELETE', f"/api/propagations/{a['id']}") == 409, 'a record that made plants cannot be removed')
audit = call('GET', '/api/audit?n=60')
check(any(x['plant_code'] == parent and x['action'] == 'propagation' for x in audit) and any(x['plant_code'] == child and 'potted up from PR-001' in (x.get('note') or '') for x in audit),
      'both plants carry it in the change log')
# ---- a second generation: a cutting from the cutting
b = call('POST', '/api/propagations', dict(method='airlayer', parent_code=child, count=1, started_on=iso(3)))
bp = call('POST', f"/api/propagations/{b['id']}/promote", dict(common_name='Air layer of the cutting'))
grand = bp['code']
T = call('GET', '/api/propagations/tree')
root = next(r for r in T['roots'] if r['code'] == parent)
c1 = next(k for m in root['makes'] for k in m['children'] if k['code'] == child)
check(root['generation'] == 1 and len(root['makes']) == 1 and len(root['makes'][0]['children']) == 2 and c1['generation'] == 2 and c1['makes'][0]['children'][0]['code'] == grand
      and c1['makes'][0]['children'][0]['generation'] == 3, 'the family tree runs from the plant through its cuttings to the next generation')
pl = call('GET', f'/api/propagations/plant/{grand}')
check(pl['generation'] == 3 and [x['code'] for x in pl['ancestors']] == [child, parent] and pl['origin']['code'] == b['code'], 'a plant knows its ancestors and which attempt made it')
# ---- seeds: ordered steps that end by themselves
s = call('POST', '/api/propagations', dict(method='seed', species='Quercus rubra', title='Red oak acorns', count=20, started_on=iso(40), collected_at='the park by the creek',
                                           stages=[dict(kind='scarify'), dict(kind='cold', days=45), dict(kind='warm', days=14, temp_low=70, temp_high=80)]))
check([x['kind'] for x in s['stages']] == ['scarify', 'cold', 'warm'] and s['stages'][1]['days'] == 45 and s['stages'][1]['temp_low'] == 34 and s['stages'][1]['temp_high'] == 41
      and s['stages'][2]['temp_low'] == 70, 'a seed lot keeps its steps in order, with the usual temperatures filled in where none were given')
check(s['due'][0]['kind'] == 'stage_start' and 'scarify' in s['due'][0]['words'].lower() or 'nick' in s['due'][0]['words'].lower(), 'the first step is waiting to be started')
sid = [x['id'] for x in s['stages']]
call('PUT', f'/api/propagations/stages/{sid[0]}', dict(action='start', on_date=iso(40))); call('PUT', f'/api/propagations/stages/{sid[0]}', dict(action='done', on_date=iso(40)))
c2 = call('PUT', f'/api/propagations/stages/{sid[1]}', dict(action='start', on_date=iso(43)))['card']        # 45 days from 43 days ago: ends in 2 days
st = {x['kind']: x for x in c2['stages']}
check(st['cold']['state'] == 'running' and st['cold']['days_left'] == 2 and any(n['kind'] == 'stage_end' and 'ends in 2 days' in n['words'] for n in c2['due']),
      'a step started 43 days ago for 45 days is running and Today is told it ends in 2 days')
c3 = call('PUT', f'/api/propagations/stages/{sid[1]}', dict(action='start', on_date=iso(50)))['card']
check(any(n['kind'] == 'stage_end' and 'ended 5 days ago' in n['words'] for n in c3['due']), 'one that ran out 5 days ago says so')
call('PUT', f'/api/propagations/stages/{sid[1]}', dict(action='done'))
c4 = call('GET', f"/api/propagations/{s['id']}")
check(any(n['kind'] == 'stage_start' and 'warm and moist' in n['words'] for n in c4['due']), 'when one is finished the next is offered')
check(status('PUT', f'/api/propagations/stages/{sid[2]}', dict(action='done')) == 409 and status('POST', f"/api/propagations/{s['id']}/stages", dict(kind='bogus')) == 400, 'a step cannot be finished before it starts, and only known steps can be added')
call('POST', f"/api/propagations/{s['id']}/events", dict(kind='sprouted', n=6, on_date=iso(1)))
c5 = call('GET', f"/api/propagations/{s['id']}")
check(c5['sprouted'] == 6 and c5['left'] == 20, 'six sprouted is counted; the lot has not made plants yet')
sp = call('POST', f"/api/propagations/{s['id']}/promote", dict(common_name='Red oak seedling', scientific_name='Quercus rubra', site='Outdoors'))
check(sp['card']['status'] == 'active' and sp['card']['children'][0]['name'] == 'Red oak seedling' and call('GET', f"/api/plants/{sp['code']}")['scientific_name'] == 'Quercus rubra',
      'a seed lot with no parent plant makes a named plant and stays open for more seedlings')
nameless = call('POST', '/api/propagations', dict(method='seed', count=3, started_on=iso(2)))
check(status('POST', f"/api/propagations/{nameless['id']}/promote", dict()) == 400 and len(call('GET', '/api/plants')) == n_plants0 + 4, 'a seed lot with no parent and no species needs a name before it can make a plant')
call('DELETE', f"/api/propagations/{nameless['id']}")
out = next((o for o in call('GET', '/api/propagations/tree')['outside'] if o['code'] == s['code']), None)
check(out and out['children'][0]['code'] == sp['code'], 'a seed lot with no parent plant appears under "from elsewhere" in the tree')
# ---- results: only finished attempts count
call('POST', f"/api/propagations/{s['id']}/status", dict(status='done'))
f2 = call('POST', '/api/propagations', dict(method='stem', parent_code=parent, count=4, started_on=iso(30)))
call('POST', f"/api/propagations/{f2['id']}/status", dict(status='failed', note='Rotted in the water'))
R = call('GET', '/api/propagations/results')
check(R['ways']['stem']['tried'] == 7 and R['ways']['stem']['made'] == 2 and R['ways']['stem']['rate'] == 29 and R['ways']['airlayer']['rate'] == 100,
      'results count pieces of finished attempts: 2 of 7 stem cuttings became plants (29%), the air layer 1 of 1')
check(R['ways']['seed']['tried'] == 20 and R['ways']['seed']['made'] == 1 and R['ways']['seed']['first_days'] == 39, 'and the middle days to a first sign (a sprout 39 days in)')
g = call('POST', '/api/propagations', dict(method='stem', parent_code=parent, count=2, started_on=iso(1)))
check(call('GET', '/api/propagations/results')['ways']['stem']['going'] == 1 and call('GET', '/api/propagations/results')['ways']['stem']['tried'] == 7, 'an attempt still going never changes a rate')
# ---- editing and removing
call('PUT', f"/api/propagations/{g['id']}", dict(title='Renamed cutting', hormone='Powder', check_every=3))
g2 = call('GET', f"/api/propagations/{g['id']}")
check(g2['title'] == 'Renamed cutting' and g2['hormone'] == 'Powder' and g2['check_every'] == 3 and status('PUT', f"/api/propagations/{g['id']}", dict(count=0)) == 400, 'details can be changed, with the same checks')
check(call('DELETE', f"/api/propagations/{g['id']}") == dict(removed=True) and status('GET', f"/api/propagations/{g['id']}") == 404, 'a record that made nothing can be removed')
h = call('POST', '/api/propagations', dict(method='stem', parent_code=parent, count=3, started_on=iso(9), medium='Water'))        # due today, for the pictures
due_n = A()['counts']['due']
with sync_playwright() as p:
    br = p.chromium.launch()
    pg = br.new_page(viewport={'width': 1280, 'height': 900})
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('plantdb.editor','Prop Test')")
    pg.goto(BASE + '/#/'); pg.wait_for_selector('#today-prop', timeout=15000)
    check(pg.inner_text('#today-prop h2') == f'Propagation ({due_n})' and pg.locator('.td-jumps a[data-sec=today-prop]').count() == 1, 'Today has a Propagation section with the number due, and a jump button')
    pg.locator('#today-prop').screenshot(path=os.path.join(OUT, 'propagation-1-today.png'))
    pg.locator(f'#today-prop .prp-job[data-prop="{h["id"]}"] [data-act=prpevent][data-kind=water]').click(); pg.wait_for_timeout(1800)
    check(any(x['kind'] == 'water' for x in call('GET', f"/api/propagations/{h['id']}")['events']) and 'saved' in pg.inner_text('#toasts'), 'Changed the water on Today records it and says so')
    # the page
    pg.goto(BASE + '/#/propagating'); pg.wait_for_selector('#prp-going')
    check(pg.locator('#prp-going .prp-job').count() == A()['counts']['active'] and pg.locator('#prp-results table').count() >= 1, 'the page lists what is going, and what the attempts show')
    check(pg.locator('#prp-results table').first.locator('th[scope=col]').count() >= 3, 'the results tables have real column headings')
    pg.screenshot(path=os.path.join(OUT, 'propagation-2-list.png'), full_page=True)
    # start one through the form
    pg.goto(BASE + f'/#/propagating/new?parent={parent}&method=airlayer'); pg.wait_for_selector('form[data-form=prpnew]')
    check(pg.locator('select[name=method]').input_value() == 'airlayer' and pg.locator('select[name=parent_code]').input_value() == parent, 'the form is filled in from the plant\'s own page link')
    check(pg.locator('form[data-form=prpnew] input:visible, form[data-form=prpnew] select:visible, form[data-form=prpnew] textarea:visible').evaluate_all(
        "els => els.filter(e => !e.closest('label') && e.type !== 'hidden' && e.type !== 'submit').length") == 0, 'every box in the form is inside a label')
    pg.fill('input[name=count]', '2'); pg.fill('input[name=medium]', 'Sphagnum'); pg.check('input[name=s_cold]'); pg.fill('input[name=d_cold]', '30')
    pg.screenshot(path=os.path.join(OUT, 'propagation-3-new.png'), full_page=True)
    pg.click('form[data-form=prpnew] button[type=submit]'); pg.wait_for_url('**/#/propagating/*'); pg.wait_for_selector('#prp-steps')
    nid = int(pg.url.rsplit('/', 1)[1]); card = call('GET', f'/api/propagations/{nid}')
    check(card['method'] == 'airlayer' and card['count'] == 2 and card['medium'] == 'Sphagnum' and [x['days'] for x in card['stages']] == [30], 'submitting the form starts it with its step')
    check(pg.inner_text('main h1') == card['title'] and pg.url.endswith('/#/propagating/%d' % nid), 'and opens its page')
    # its page
    pg.locator('#prp-steps [data-act=prpstage][data-do=start]').first.click(); pg.wait_for_timeout(1500)
    check(call('GET', f'/api/propagations/{nid}')['stages'][0]['state'] == 'running' and 'Started' in pg.inner_text('#prp-steps'), 'Start on a step starts it today')
    pg.locator('#prp-record [data-act=prpevent][data-kind=roots]').click(); pg.wait_for_timeout(1500)
    check('Roots seen' in pg.inner_text('#prp-history'), 'Roots seen goes in what happened')
    pg.fill('#prp-record form[data-form=prpnote] input[name=text]', 'White roots through the moss'); pg.click('#prp-record form[data-form=prpnote] button'); pg.wait_for_timeout(1500)
    check('White roots through the moss' in pg.inner_text('#prp-history'), 'a note is saved')
    pg.locator('#prp-history button[data-act=prpundo]').first.click(); pg.wait_for_timeout(1500)
    check('White roots through the moss' not in pg.inner_text('#prp-history'), 'Take back removes an entry')
    pg.locator('#prp-record [data-act=prpstatus][data-st=ready]').click(); pg.wait_for_timeout(1500)
    check(call('GET', f'/api/propagations/{nid}')['status'] == 'ready' and 'Ready to pot up' in pg.inner_text('.verdict-box'), 'Ready to pot up marks it ready')
    pg.fill('#prp-pot input[name=common_name]', 'Air layer baby'); pg.select_option('#prp-pot select[name=site]', 'Covered porch')
    pg.screenshot(path=os.path.join(OUT, 'propagation-4-one.png'), full_page=True)
    pg.click('#prp-pot button[type=submit]'); pg.wait_for_timeout(2000)
    kid = call('GET', f'/api/propagations/{nid}')['children']
    check(len(kid) == 1 and 'Potted up as' in pg.inner_text('#toasts') and kid[0]['code'] in pg.inner_text('#prp-made'), 'Pot it up makes the plant, says its code, and lists it under Plants made')
    check(call('GET', f"/api/plants/{kid[0]['code']}")['site'] == 'Covered porch', 'in the place chosen')
    # the family tree
    pg.goto(BASE + '/#/propagating/family'); pg.wait_for_selector('#prp-tree')
    tree_text = pg.inner_text('#prp-tree')
    check(parent in tree_text and child in tree_text and grand in tree_text and 'Generation 3' in tree_text and 'The original plant' in tree_text, 'the family tree page names every plant and its generation in words')
    check(pg.locator('#prp-tree a').count() >= 6 and pg.locator('#prp-outside li').count() >= 1, 'plants and attempts are links, and seed from elsewhere is its own list')
    pg.screenshot(path=os.path.join(OUT, 'propagation-5-family.png'), full_page=True)
    # the plant's own page, and the guide
    pg.goto(BASE + f'/#/plant/{parent}'); pg.wait_for_selector('#prp-plant', timeout=15000)
    check('Made from this plant' in pg.inner_text('#prp-plant') and pg.locator(f'#prp-plant a[href="#/propagating/new?parent={parent}"]').count() == 1, 'the original plant\'s page lists what was made from it and offers to start another')
    pg.locator('#prp-plant').screenshot(path=os.path.join(OUT, 'propagation-6-plant.png'))
    pg.goto(BASE + f'/#/plant/{grand}'); pg.wait_for_selector('#prp-plant:has-text("Generation 3")', timeout=15000)
    check('Generation 3' in pg.inner_text('#prp-plant') and f'Made from' in pg.inner_text('#prp-plant') and child in pg.inner_text('#prp-plant'), 'a grandchild\'s page says where it came from and which generation it is')
    check(pg.locator('#prp-plant h2').count() == 1 and pg.locator('#prp-plant h2').inner_text().startswith('Family and propagation'), 'the section has a real heading')
    pg.goto(BASE + '/#/guide'); pg.wait_for_selector('#prp-guidelink', timeout=15000)
    check(pg.locator('#prp-guidelink a[href="#/propagating"]').count() == 1, 'the guide links to the new page')
    pg.goto(BASE + '/#/search'); pg.wait_for_timeout(300)
    call('POST', '/api/propagations', dict(method='stem', parent_code=parent, count=2, started_on=iso(12), medium='Water'))     # something due, so Today shows the section
    # phone, light and dark with large text
    for name, disp in (('phone-light', {}), ('phone-dark-big', {'theme': 'dark', 'size': '160'})):
        ph = br.new_page(viewport={'width': 390, 'height': 844}, device_scale_factor=2)
        ph.on('pageerror', lambda e: errs.append(str(e)))
        ph.add_init_script("localStorage.setItem('plantdb.editor','Prop Test');localStorage.setItem('plantdb.display', JSON.stringify(%s))" % json.dumps(disp))
        for route, wait, tag in (('/#/propagating', '#prp-going', 'list'), (f"/#/propagating/{s['id']}", '#prp-steps', 'one'), ('/#/propagating/new', 'form[data-form=prpnew]', 'new'), ('/#/propagating/family', '#prp-tree', 'family'), ('/#/', '#today-prop', 'today')):
            ph.goto(BASE + route); ph.wait_for_selector(wait); ph.wait_for_timeout(700)
            over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
            check(over <= 0, f'{name}, {tag}: nothing scrolls sideways ({over}px)')
            if tag in ('one', 'family', 'new'):
                ph.screenshot(path=os.path.join(OUT, f'propagation-7-{tag}-{name}.png'))
        ph.close()
    # people who can only view do not see the buttons
    pg.goto(BASE + f"/#/propagating/{s['id']}"); pg.wait_for_selector('#prp-steps')
    pg.evaluate("document.documentElement.dataset.role = 'viewer'")
    check(pg.locator('[data-act^=prp]:visible, form[data-form^=prp]:visible').count() == 0, 'people who can only view see no buttons or forms')
    br.close()
check(not errs, 'no JavaScript errors' + ('' if not errs else ': ' + '; '.join(errs[:3])))
print('%d failed' % len(fails)); sys.exit(1 if fails else 0)
