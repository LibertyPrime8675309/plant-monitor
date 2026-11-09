"""1.49.0 (PLAN.md step 4c): the plant-sitter sheet by link. A link is a long token under /share/; only the sheet, its files and the
photos on it are reachable through it; the sitter's ticks come back to the app; a link taken down or past its days answers 410."""
import io, os
from datetime import date, timedelta
import server as S

ED = {'X-Editor': 'Share Test'}

def days():
    d0 = date.today() + timedelta(days=2)
    return d0.isoformat(), (d0 + timedelta(days=4)).isoformat()

def make(c, **extra):
    f, t = days()
    r = c.post('/api/sitter/shares', json=dict({'from': f, 'to': t, 'note': 'The key is under the mat.'}, **extra), headers=ED)
    assert r.status_code == 201, r.get_data(as_text=True)
    return r.get_json()['share']

def test_a_link_serves_the_sheet_and_nothing_else():
    with S.app.test_client() as c:
        sh = make(c)
        tok = sh['token']
        assert len(tok) >= 30 and sh['live'] and sh['local_url'].endswith('/share/' + tok)
        assert sh['url'] is None, 'no public address saved yet'
        # the page, without any sign-in or editor header
        r = c.get(f'/share/{tok}'); assert r.status_code == 200 and tok in r.get_data(as_text=True) and 'no-store' in r.headers['Cache-Control']
        r = c.get(f'/share/{tok}/data'); assert r.status_code == 200
        D = r.get_json()
        assert D['note'] == 'The key is under the mat.' and D['before'] == [] and D['ticks'] == [] and D['units']['temp'] in ('f', 'c') and D['owner']
        for p in D['plants']:
            if p['photo']: assert p['photo'].startswith(f'/share/{tok}/photo/')
        assert c.get(f'/share/{tok}/style.css').status_code == 200
        assert c.get(f'/share/{tok}/share.js').status_code == 200
        assert c.get(f'/share/{tok}/sitter-sheet.js').status_code == 200
        # a photo that is not on the sheet is not served, nor anything outside /share/<token>/
        assert c.get(f'/share/{tok}/photo/not-on-the-sheet.jpg').status_code == 404
        assert c.get(f'/share/{tok}/../api/plants').status_code in (403, 404)
        # the wrong token, and a token too short to pass the guard
        assert c.get('/share/' + 'x' * 32).status_code == 404
        assert c.get('/share/short').status_code in (401, 403, 404)

def test_ticks_come_back_to_the_app_and_a_link_can_be_taken_down():
    with S.app.test_client() as c:
        sh = make(c); tok = sh['token']
        D = c.get(f'/share/{tok}/data').get_json()
        day = D['days'][0]['date']
        code = (D['days'][0]['plants'] or [p['code'] for p in D['plants']])[0] if D['plants'] else None
        if code is None:
            return                                                       # an empty database: nothing to tick
        r = c.post(f'/share/{tok}/tick', json={'day': day, 'plant': code, 'kind': 'water', 'on': True}); assert r.status_code == 200, r.get_data(as_text=True)
        assert c.post(f'/share/{tok}/tick', json={'day': '2000-01-01', 'plant': code, 'on': True}).status_code == 400, 'a day outside the sheet'
        assert c.post(f'/share/{tok}/tick', json={'day': day, 'plant': 'P-999', 'on': True}).status_code == 400, 'a plant that is not there'
        T = c.get(f'/api/sitter/ticks?from={sh["from"]}&to={sh["to"]}').get_json()
        assert T['share']['token'] == tok and [(t['day'], t['plant_code'], t['kind']) for t in T['ticks']] == [(day, code, 'water')]
        assert c.get(f'/share/{tok}/data').get_json()['ticks'][0]['plant_code'] == code
        r = c.post(f'/share/{tok}/tick', json={'day': day, 'plant': code, 'kind': 'water', 'on': False}); assert r.status_code == 200
        assert c.get(f'/api/sitter/ticks?from={sh["from"]}&to={sh["to"]}').get_json()['ticks'] == []
        # the list, then taking the link down
        L = c.get('/api/sitter/shares').get_json()
        assert any(x['token'] == tok for x in L['shares']) and L['share_path'] == '/share'
        assert c.delete(f'/api/sitter/shares/{tok}', headers=ED).status_code == 200
        assert c.get(f'/share/{tok}').status_code == 410
        assert c.get(f'/share/{tok}/data').status_code == 410
        assert c.post(f'/share/{tok}/tick', json={'day': day, 'plant': code, 'on': True}).status_code == 410
        T = c.get(f'/api/sitter/ticks?from={sh["from"]}&to={sh["to"]}').get_json()
        assert not T['share'] or T['share']['token'] != tok, 'a link taken down no longer feeds the printout'

def test_a_link_expires_the_day_after_the_last_day():
    with S.app.test_client() as c:
        sh = make(c); tok = sh['token']
        with S.app.app_context():
            d = S.db(); d.execute('UPDATE sitter_shares SET expires_at=? WHERE token=?', ('2000-01-01T00:00:00Z', tok)); d.commit()
        r = c.get(f'/share/{tok}/data'); assert r.status_code == 410 and 'expired' in r.get_json()['error'], 'the reason comes as JSON for the page to show'

def test_viewers_cannot_make_or_take_down_links():
    with S.app.test_client() as c:
        f, t = days()
        TS = {'environ_overrides': {'SERVER_PORT': S.TS_PORT}}
        c.get('/api/me', headers={'Tailscale-User-Login': 'owner@example.com', 'Tailscale-User-Name': 'Own'}, **TS)   # the first person in is the owner
        H = {'Tailscale-User-Login': 'viewer@example.com', 'Tailscale-User-Name': 'Vee', 'X-Editor': 'Vee'}
        r = c.post('/api/sitter/shares', json={'from': f, 'to': t}, headers=H, environ_overrides={'SERVER_PORT': S.TS_PORT})
        assert r.status_code == 403, r.get_data(as_text=True)
        assert c.get('/api/sitter/shares', headers=H, environ_overrides={'SERVER_PORT': S.TS_PORT}).status_code == 200, 'looking is fine'

def test_bad_dates_are_refused():
    with S.app.test_client() as c:
        assert c.post('/api/sitter/shares', json={'from': '2000-01-01', 'to': '2000-01-02'}, headers=ED).status_code == 400
        f, t = days()
        assert c.post('/api/sitter/shares', json={'from': t, 'to': f}, headers=ED).status_code == 400
