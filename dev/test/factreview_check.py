"""Checks 1.54.0 (PLAN.md step 6b): proposing and reviewing facts. An editor suggests a correction on a species page (it shows as
proposed, not as the value); she cannot accept her own; another editor (or the owner) accepts it from the page or from "Facts to
review", and it becomes the accepted value with the old one in the history; a rejection says why; Today tells editors what waits;
viewers see none of the buttons; a mushroom fact that says "edible" is refused; import adds proposals only.
Start the mock server with a fresh data folder (MOCK_TS=1), then:  python3 dev/test/factreview_check.py [base]
Screenshots: dev/tmp/shots/factreview-*.png"""
import json, os, re, sys, urllib.error, urllib.request
from playwright.sync_api import sync_playwright
LOCAL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
TS = LOCAL.rsplit(':', 1)[0] + ':' + str(int(LOCAL.rsplit(':', 1)[1]) + 1)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tmp', 'shots'); os.makedirs(OUT, exist_ok=True)
fails, errs = [], []
def check(cond, what):
    print(('ok   ' if cond else 'FAIL ') + what)
    if not cond: fails.append(what)
def call(m, url, body=None, headers=None, base=TS):
    req = urllib.request.Request(base + url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Content-Type': 'application/json', **(headers or {})}, method=m)
    try:
        with urllib.request.urlopen(req) as r: return r.status, json.loads(r.read() or b'null')
    except urllib.error.HTTPError as e: return e.code, json.loads(e.read() or b'{}')
E = {'Tailscale-User-Login': 'ethan@example.com', 'Tailscale-User-Name': 'Ethan', 'X-Editor': 'Ethan'}
S = {'Tailscale-User-Login': 'sam@example.net', 'Tailscale-User-Name': 'Sam', 'X-Editor': 'Sam'}
J = {'Tailscale-User-Login': 'jo@example.net', 'Tailscale-User-Name': 'Jo', 'X-Editor': 'Jo'}
V = {'Tailscale-User-Login': 'vee@example.net', 'Tailscale-User-Name': 'Vee', 'X-Editor': 'Vee'}
call('GET', '/api/me', headers=E); call('GET', '/api/me', headers=S); call('GET', '/api/me', headers=J); call('GET', '/api/me', headers=V)
for who in ('sam@example.net', 'jo@example.net'): call('PUT', '/api/people', {'login': who, 'role': 'editor'}, headers=E)
# the API's rules
st, d = call('POST', '/api/facts/rows', {'name': 'Agave americana', 'field': 'light_summary', 'value': 'Full sun, all day', 'source': 'My agaves on the south wall', 'source_kind': 'observation', 'confidence': 'certain'}, headers=S)
check(st == 201 and d['status'] == 'proposed', 'an editor proposes a fact (a species that had only genus facts)')
pid = d['id']
check(call('POST', f'/api/facts/rows/{pid}/accept', {}, headers=S)[0] == 403, 'she cannot accept her own')
check(call('POST', '/api/facts/rows', {'name': 'Agave americana', 'field': 'light_summary', 'value': 'Full sun, all day', 'source': 'x'}, headers=J)[0] == 409, 'the same value twice is refused while it waits')
check(call('POST', '/api/facts/rows', {'name': 'Agave americana', 'field': 'temp_ideal_low', 'value': 'warm', 'source': 'x'}, headers=J)[0] == 400, 'a number field refuses words')
check(call('POST', '/api/facts/rows', {'name': 'Agave americana', 'field': 'light_summary', 'value': 'Shade', 'source': ''}, headers=J)[0] == 400, 'a source is required')
check(call('POST', '/api/facts/rows', {'name': 'Agave americana', 'field': 'light_summary', 'value': 'Shade', 'source': 'x'}, headers=V)[0] == 403, 'a viewer cannot propose')
st, d = call('POST', '/api/facts/rows', {'name': 'Leucocoprinus birnbaumii', 'kind': 'fungus', 'field': 'about_summary', 'value': 'A yellow pot mushroom, said to be edible when young', 'source': 'a forum'}, headers=J)
check(st == 400 and 'edible' in d.get('error', ''), 'a mushroom fact that says "edible" is refused')
st, d = call('POST', '/api/facts/rows', {'name': 'Leucocoprinus birnbaumii', 'kind': 'fungus', 'field': 'temp_ideal_low', 'value': '60', 'source': 'x'}, headers=J)
check(st == 400, 'a mushroom gets no care values')
st, d = call('POST', '/api/facts/rows', {'name': 'Leucocoprinus birnbaumii', 'kind': 'fungus', 'field': 'about_summary', 'value': 'A small yellow mushroom that turns up in warm potting mix; it does no harm to the plant.', 'source': 'Texas Mushrooms (Metzler), p. 112', 'source_kind': 'reference'}, headers=J)
check(st == 201, 'a mushroom description with a book as its source is proposed')
mush_id = d['id']
with sync_playwright() as pw:
    b = pw.chromium.launch()
    # Sam, the proposer, sees it as proposed and cannot accept
    sp = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=S)
    sp.on('pageerror', lambda e: errs.append(str(e)))
    sp.goto(TS + '/#/species/Agave%20americana'); sp.wait_for_selector('#sp-facts-rows', timeout=15000); sp.wait_for_timeout(500)
    sec = sp.locator('#sp-facts-rows')
    light = sec.locator('.fr-group', has_text='Light')
    check(light.count() == 1 and light.get_attribute('open') is not None and 'a proposal to review' in light.locator('summary').inner_text(), 'the group with a proposal is open and says so')
    prop = light.locator('.fr-prop')
    check(prop.count() == 1 and 'Proposed' in prop.inner_text() and 'Full sun, all day' in prop.inner_text() and 'Yours' in prop.inner_text() and prop.locator('[data-act=fraccept]').count() == 0, 'the proposer sees her proposal, marked as hers, with no Accept button')
    check(light.locator('.fr-row dd .fr-val').count() == 0 or 'Full sun, all day' not in light.locator('.fr-row dd .fr-val').first.inner_text(), 'the proposal is not shown as the value')
    check(sec.locator('[data-act=fradd]').count() == 1 and sec.locator('[data-act=frpropose]').count() >= 1, 'an editor has "Add a fact" and "Suggest a change" buttons')
    sp.screenshot(path=os.path.join(OUT, 'factreview-1-proposed.png'), full_page=False)
    # she proposes a correction through the form, on a fact that exists (the summary)
    sec.locator('.fr-group', has_text='Uses and partners').locator('summary').click(); sp.wait_for_timeout(300)
    sec.locator('[data-act=frpropose][data-field=about_summary]').click(); sp.wait_for_timeout(500)
    check(sp.locator('dialog[open] .fr-form').count() == 1 and 'Suggest a change: In short' in sp.locator('dialog[open] h2').inner_text(), 'the form opens for that fact')
    sp.fill('dialog[open] [name=value]', 'Tough rosette succulents for dry, sunny beds; the plant dies after flowering once, but leaves pups.')
    sp.fill('dialog[open] [name=source]', 'https://plants.ces.ncsu.edu/plants/agave-americana/')
    sp.select_option('dialog[open] [name=source_kind]', 'reference'); sp.select_option('dialog[open] [name=confidence]', 'certain')
    sp.locator('dialog[open] button[value=ok]').click(); sp.wait_for_timeout(2000)
    check('Sent for review' in sp.inner_text('#toasts'), 'sending says it went for review')
    sp.wait_for_timeout(500)
    check(sp.locator('#sp-facts-rows .fr-prop').count() == 2, 'both proposals show on the page')
    # Jo, another editor: Today says facts wait, the queue lists them, Accept works
    jp = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=J)
    jp.on('pageerror', lambda e: errs.append(str(e)))
    jp.goto(TS + '/#/'); jp.wait_for_timeout(3000)
    check(jp.locator('#today-facts').count() == 1 and 'Facts to review (3)' in jp.locator('#today-facts h2').inner_text(), 'Today tells an editor three facts wait')
    check(jp.locator('.td-jumps a[data-sec=today-facts]').count() == 1 and jp.locator('.td-jumps a[data-sec=today-facts]').inner_text() == 'Facts (3)', 'with a jump button')
    jp.goto(TS + '/#/facts'); jp.wait_for_timeout(2500)
    items = jp.locator('.fr-qitem')
    check(items.count() == 3 and 'Facts to review' in jp.locator('h1').inner_text(), 'the Facts to review page lists them')
    check(jp.locator('#main-nav a[aria-current=page], #sub-nav a[aria-current=page]').filter(has_text='Facts to review').count() >= 1, 'the page is in the top bar (Plants section)')
    first = items.filter(has_text='Full sun, all day').first
    check(first.locator('[data-act=fraccept]').count() == 1 and 'No accepted value yet' in first.inner_text(), 'Jo may accept Sam\'s, and sees there was no value before')
    jp.screenshot(path=os.path.join(OUT, 'factreview-2-queue.png'), full_page=True)
    first.locator('[data-act=fraccept]').click(); jp.wait_for_timeout(2000)
    check('Accepted' in jp.inner_text('#toasts') and jp.locator('.fr-qitem').count() == 2, 'accepting removes it from the queue')
    # Jo's own mushroom proposal has no buttons for her; she rejects Sam's second one with a reason
    check(jp.locator('.fr-qitem', has_text='Leucocoprinus').first.locator('[data-act=frreject]').count() == 0 and 'Yours' in jp.locator('.fr-qitem', has_text='Leucocoprinus').first.inner_text(), 'her own proposal shows without Accept or Reject')
    m = jp.locator('.fr-qitem', has_text='Tough rosette').first
    m.locator('[data-act=frreject]').click(); jp.wait_for_timeout(400)
    jp.fill('dialog[open] [name=note]', 'The old summary says this already'); jp.locator('dialog[open] button[value=ok]').click(); jp.wait_for_timeout(2000)
    check(jp.locator('.fr-qitem').count() == 1, 'rejecting removes it too')
    st, d = call('GET', '/api/facts/rows?name=Agave%20americana', headers=J)
    rej = [h for g in d['groups'] for f in g['fields'] for h in f['history'] if h['status'] == 'rejected']
    check(rej and 'The old summary says this already' in rej[0]['note'] and 'Rejected by Jo' in rej[0]['note'], 'the rejection and its reason are kept in the history')
    # the owner rejects the mushroom one
    check(call('POST', f'/api/facts/rows/{mush_id}/reject', {'note': 'Needs a page check'}, headers=E)[0] == 200, 'the owner may reject anyone\'s')
    # the accepted one is now the value on the species page, for everyone, with the history
    sp.reload(); sp.wait_for_selector('#sp-facts-rows', timeout=15000); sp.wait_for_timeout(600)
    light = sp.locator('#sp-facts-rows .fr-group', has_text='Light')
    check('Full sun, all day' in light.locator('.fr-val').first.inner_text() and 'My agaves on the south wall' in light.inner_text() and 'Certain' in light.inner_text(), 'the accepted proposal is the value shown, with its source and confidence')
    st, A = call('GET', '/api/audit?limit=30', headers=E)
    notes = [x.get('note', '') for x in A]
    check(any(n.startswith('Proposed for agave americana') for n in notes) and any(n.startswith('Accepted for agave americana') and 'proposed by Sam' in n for n in notes) and any(n.startswith('Rejected for') for n in notes), 'the audit log has the proposal, the acceptance (by whom, proposed by whom) and the rejection')
    # the owner may accept his own
    st, d = call('POST', '/api/facts/rows', {'name': 'Agave americana', 'field': 'zone_low', 'value': '8', 'source': 'Texas A&M AgriLife', 'confidence': 'likely'}, headers=E)
    check(st == 201 and call('POST', f'/api/facts/rows/{d["id"]}/accept', {}, headers=E)[0] == 200, 'the owner may accept his own proposal')
    # a viewer: reads, no buttons
    vp = b.new_page(viewport={'width': 1280, 'height': 900}, extra_http_headers=V)
    vp.goto(TS + '/#/species/Agave%20americana'); vp.wait_for_selector('#sp-facts-rows', timeout=15000); vp.wait_for_timeout(400)
    check(vp.locator('#sp-facts-rows [data-act=frpropose]:visible, #sp-facts-rows [data-act=fradd]:visible, #sp-facts-rows [data-act=fraccept]:visible').count() == 0 and 'Full sun, all day' in vp.inner_text('#sp-facts-rows'), 'a viewer reads the facts and sees none of the buttons')
    vp.goto(TS + '/#/'); vp.wait_for_timeout(2500)
    check(vp.locator('#today-facts').count() == 0, 'and Today does not ask a viewer to review anything')
    vp.close()
    # import: the export's rows come back as proposals, never accepted
    st, X = call('GET', '/api/facts/export', headers=E)
    rows = [x for x in X['facts'] if x['key'] == 'agave' and x['status'] == 'accepted'][:3]
    for x in rows: x['value'] = (x['value'] + ' (from another install)') if isinstance(x['value'], str) else x['value']
    st, d = call('POST', '/api/facts/import', {'facts': rows + [{'key': 'agave', 'field': 'about_summary', 'value': 'A duplicate', 'source': 'x'}, {'key': 'agave', 'field': 'about_summary', 'value': 'A duplicate', 'source': 'x'}]}, headers=E)
    check(st == 200 and d['added'] >= 1 and d['skipped'] >= 1, f'import adds proposals and skips duplicates ({d})')
    st, Q = call('GET', '/api/facts/queue', headers=E)
    check(all(q['status'] == 'proposed' for q in Q['queue']) and any('Imported by' in q['note'] for q in Q['queue']), 'imported rows wait in the queue as proposals')
    # phone width
    ph = b.new_page(viewport={'width': 390, 'height': 844}, extra_http_headers=J)
    ph.add_init_script("localStorage.setItem('plantdb.display',JSON.stringify({size:'190'}))")
    ph.goto(TS + '/#/facts'); ph.wait_for_timeout(2500)
    over = ph.evaluate('document.documentElement.scrollWidth - document.documentElement.clientWidth')
    check(over <= 2, f'phone, largest text: the queue has no sideways scrolling ({over}px)')
    ph.screenshot(path=os.path.join(OUT, 'factreview-3-phone.png'), full_page=False)
    for e in errs: check(False, 'browser error: ' + e)
    b.close()
print(f'\n{len(fails)} failed' if fails else '\nall good')
sys.exit(1 if fails else 0)
