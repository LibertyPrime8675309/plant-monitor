"""1.53.0 (PLAN.md step 6a): knowledge with provenance. One row per species fact, loaded once from what the record already knows
(species notes, care sheets, the plants' care fields where every plant of the species agrees), each with the batch or person it
came from; a plant's page reads the species' facts for fields it leaves empty; rows export; a batch can add rows."""
import json
import server as S

def test_the_record_s_knowledge_is_loaded_once_as_rows():
    with S.app.app_context():
        c = S.db()
        n = c.execute('SELECT COUNT(*) FROM facts').fetchone()[0]
        assert n > 1000, n
        assert S.setting(c, 'facts_loaded') == '1' and S.facts_migrate(c) == 0, 'a second start loads nothing again'
        assert c.execute('SELECT COUNT(*) FROM facts').fetchone()[0] == n
        kinds = dict(c.execute('SELECT source_kind, COUNT(*) FROM facts GROUP BY 1').fetchall())
        assert kinds.get('batch', 0) > kinds.get('observation', 0) * 50, f'nearly everything traces to a batch or the first list: {kinds}'
        assert kinds.get('claude', 0) > 100, 'the species notes (uses, partners...) became about_* rows'
        # one species: the aloe's uses came from batch A9; its temperatures from the first list or a batch
        F = S.facts_of(c, 'Aloe vera')
        assert F['about_uses']['source_kind'] == 'claude' and 'Claude' in F['about_uses']['source'] and json.loads(F['about_uses']['value'])
        assert F['temp_ideal_low']['status'] == 'accepted' and F['temp_ideal_low']['source'].startswith(('The first plant list', 'Upgrade batch'))
        assert all(r['confidence'] in S.CONFIDENCE and r['status'] in S.STATUS for r in F.values())
        # a species whose plants disagree on a field gets no row for it
        rows = {r['field'] for r in c.execute("SELECT field FROM facts WHERE key='dieffenbachia seguine' AND status='accepted'")}
        assert 'temp_ideal_low' in rows and 'humidity_notes' not in rows, 'P-001 and P-010 give different humidity notes'

def test_values_are_compared_as_the_same_kind():
    assert S.fact_value_text('int', 6.0) == S.fact_value_text('int', '6') == '6' and S.fact_value_text('num', 0.8) == '0.8'
    assert S.fact_value_text('json', ['a', 'b']) == S.fact_value_text('json', '["a", "b"]') and S.fact_value_text('json', []) == ''
    assert S.fact_value_text('text', '  Bright,   indirect ') == 'Bright, indirect' and S.fact_value_text('text', None) == ''
    assert S.fact_value_out('int', '72') == 72 and S.fact_value_out('json', '[1]') == [1]

def test_an_accepted_row_retires_the_old_one_and_the_api_shows_history():
    with S.app.app_context():
        c = S.db()
        old = c.execute("SELECT id, value FROM facts WHERE key='ficus carica' AND field='light_summary' AND status='accepted'").fetchone()
        new_id = S.fact_add(c, 'ficus carica', 'plant', 'light_summary', 'Full sun, six hours or more', 'https://example.org/figs', 'reference', 'Tester', None, 'certain', 'accepted', 'A test')
        assert new_id and S.fact_add(c, 'ficus carica', 'plant', 'light_summary', 'Full sun, six hours or more', 'x', 'reference', 'Tester') is None, 'the same value twice adds nothing'
        c.commit()
        rows = c.execute("SELECT id, status, replaces FROM facts WHERE key='ficus carica' AND field='light_summary' ORDER BY id").fetchall()
        assert [r['status'] for r in rows] == ['retired', 'accepted'] and rows[-1]['replaces'] == old['id']
    with S.app.test_client() as t:
        R = t.get('/api/facts/rows?name=Ficus%20carica').get_json()
        light = next(f for g in R['groups'] if g['group'] == 'Light' for f in g['fields'] if f['field'] == 'light_summary')
        assert light['accepted']['value'] == 'Full sun, six hours or more' and light['accepted']['source'] == 'https://example.org/figs' and light['accepted']['confidence'] == 'certain'
        assert len(light['history']) == 1 and light['history'][0]['status'] == 'retired' and light['history'][0]['value'] == old['value']
        assert R['keys'] == ['ficus carica', 'ficus'] and R['accepted'] >= 20
        assert t.get('/api/facts/rows?name=Nothingia%20here').get_json()['groups'] == []
        csv_text = t.get('/api/facts/export.csv').get_data(as_text=True)
        assert csv_text.splitlines()[0].startswith('id,key,kind,field,label,group,value,source') and 'ficus carica' in csv_text
        J = t.get('/api/facts/export').get_json()
        assert J['version'] == S.APP_VERSION and any(f['key'] == 'ficus carica' and f['field'] == 'light_summary' and f['status'] == 'accepted' for f in J['facts'])

def test_a_plant_reads_the_species_facts_for_what_it_leaves_empty():
    with S.app.test_client() as t:
        H = {'X-Editor': 'Facts Test'}
        p = t.get('/api/plants/P-003').get_json()                          # the fig: one plant of its species, so its values are the species' facts
        assert p['soil_medium'] and 'from_species' not in p, 'the plain plant API is unchanged (the edit form uses it)'
        r = t.put('/api/plants/P-003', json={'base_version': p['version'], 'fields': {'soil_medium': '', 'light_hours': ''}}, headers=H); assert r.status_code == 200
        q = t.get('/api/plants/P-003?fill=1').get_json()
        assert q['soil_medium'] == p['soil_medium'] and q['light_hours'] == p['light_hours'], 'shown from the species'
        assert set(q['from_species']) == {'soil_medium', 'light_hours'} and q['from_species']['soil_medium']['source'].startswith(('Upgrade batch', 'The first plant list'))
        assert t.get('/api/plants/P-003').get_json()['soil_medium'] == '', 'the plant itself stays empty: nothing was written'
        # the plant's own value always wins
        t.put('/api/plants/P-003', json={'base_version': q['version'], 'fields': {'soil_medium': 'My own gritty mix'}}, headers=H)
        q = t.get('/api/plants/P-003?fill=1').get_json()
        assert q['soil_medium'] == 'My own gritty mix' and 'soil_medium' not in q['from_species']

def test_a_batch_adds_rows_with_itself_as_the_source():
    with S.app.app_context():
        c = S.db()
        b = {'id': 'test-facts', 'facts_add': [{'name': 'Ficus carica', 'field': 'zone_notes', 'value': 'Hardy to zone 7 with protection.', 'confidence': 'certain', 'source': 'Texas A&M AgriLife fig guide'},
                                             {'name': 'Ficus carica', 'field': 'not_a_field', 'value': 'x'}, {'name': '', 'field': 'zone_low', 'value': '7'}]}
        assert S.facts_from_batch(c, b, 'Claude (batch)', '2026-11-09T00:00:00Z') == 1
        r = c.execute("SELECT * FROM facts WHERE key='ficus carica' AND field='zone_notes' AND status='accepted'").fetchone()
        assert r['value'].startswith('Hardy to zone 7') and r['source'] == 'Texas A&M AgriLife fig guide' and r['source_kind'] == 'batch' and r['confidence'] == 'certain'
        c.rollback()

# ---- 6b (1.54.0): proposing and reviewing
def test_proposals_are_reviewed_by_someone_else_and_the_audit_log_says_who():
    with S.app.test_client() as t:
        TS = {'environ_overrides': {'SERVER_PORT': S.TS_PORT}}
        E = {'Tailscale-User-Login': 'own@example.com', 'Tailscale-User-Name': 'Own', 'X-Editor': 'Own'}
        A = {'Tailscale-User-Login': 'a@example.com', 'Tailscale-User-Name': 'Ann', 'X-Editor': 'Ann'}
        B = {'Tailscale-User-Login': 'b@example.com', 'Tailscale-User-Name': 'Bob', 'X-Editor': 'Bob'}
        for h in (E, A, B): t.get('/api/me', headers=h, **TS)
        for who in ('a@example.com', 'b@example.com'): assert t.put('/api/people', json={'login': who, 'role': 'editor'}, headers=E, **TS).status_code == 200
        body = {'name': 'Ficus carica', 'field': 'water_notes', 'value': 'Deep soak weekly in summer, rarely in winter.', 'source': 'Texas A&M fig guide', 'source_kind': 'reference', 'confidence': 'likely'}
        r = t.post('/api/facts/rows', json=body, headers=A, **TS); assert r.status_code == 201, r.get_data(as_text=True)
        rid = r.get_json()['id']
        assert t.post('/api/facts/rows', json=body, headers=B, **TS).status_code == 409, 'already proposed'
        assert t.post(f'/api/facts/rows/{rid}/accept', json={}, headers=A, **TS).status_code == 403, 'not your own'
        q = t.get('/api/facts/queue', headers=B, **TS).get_json()
        mine = next(x for x in q['queue'] if x['id'] == rid)
        assert mine['can_accept'] and not mine['mine'] and mine['current'] and mine['current']['status'] == 'accepted'
        rows = t.get('/api/facts/rows?name=Ficus%20carica', headers=A, **TS).get_json()
        water = next(f for g in rows['groups'] for f in g['fields'] if f['field'] == 'water_notes')
        assert water['accepted']['value'] != body['value'] and any(h['status'] == 'proposed' and h['mine'] for h in water['history']), 'a proposal is not the value, and the proposer sees it as hers'
        old_value = water['accepted']['value']
        assert t.post(f'/api/facts/rows/{rid}/accept', json={'note': 'Matches the county guide'}, headers=B, **TS).status_code == 200
        with S.app.app_context():
            c = S.db()
            r2 = c.execute('SELECT * FROM facts WHERE id=?', (rid,)).fetchone()
            assert r2['status'] == 'accepted' and r2['replaces'] and tuple(c.execute('SELECT status, value FROM facts WHERE id=?', (r2['replaces'],)).fetchone()) == ('retired', old_value)
            assert S.facts_of(c, 'Ficus carica')['water_notes']['id'] == rid
            notes = [x[0] for x in c.execute("SELECT note FROM audit_log WHERE action='fact' ORDER BY id DESC LIMIT 5")]
            assert any(n.startswith('Accepted for ficus carica') and 'proposed by Ann' in n for n in notes) and any(n.startswith('Proposed for ficus carica') for n in notes)
        # a rejection keeps the reason; a viewer can do none of it; the owner may accept his own
        r = t.post('/api/facts/rows', json=dict(body, value='Water daily'), headers=A, **TS); rid2 = r.get_json()['id']
        assert t.post(f'/api/facts/rows/{rid2}/reject', json={'note': 'Too much for a fig'}, headers=B, **TS).status_code == 200
        with S.app.app_context():
            r3 = S.db().execute('SELECT status, note FROM facts WHERE id=?', (rid2,)).fetchone(); assert r3[0] == 'rejected' and 'Too much for a fig' in r3[1]
        Vh = {'Tailscale-User-Login': 'v@example.com', 'Tailscale-User-Name': 'Vee', 'X-Editor': 'Vee'}
        t.get('/api/me', headers=Vh, **TS)
        assert t.post('/api/facts/rows', json=body, headers=Vh, **TS).status_code == 403
        r = t.post('/api/facts/rows', json=dict(body, field='zone_low', value='8'), headers=E, **TS); assert r.status_code == 201
        assert t.post(f'/api/facts/rows/{r.get_json()["id"]}/accept', json={}, headers=E, **TS).status_code == 200

def test_mushroom_facts_never_say_edible_and_import_only_proposes():
    with S.app.test_client() as t:
        H = {'X-Editor': 'Imp'}
        r = t.post('/api/facts/rows', json={'name': 'Amanita muscaria', 'kind': 'fungus', 'field': 'about_summary', 'value': 'Edible after boiling, some say', 'source': 'a forum'}, headers=H)
        assert r.status_code == 400 and 'edible' in r.get_json()['error']
        assert t.post('/api/facts/rows', json={'name': 'Amanita muscaria', 'kind': 'fungus', 'field': 'temp_ideal_low', 'value': '60', 'source': 'x'}, headers=H).status_code == 400, 'no care values for a mushroom'
        assert t.post('/api/facts/rows', json={'name': 'Amanita muscaria', 'kind': 'fungus', 'field': 'about_summary', 'value': 'The red-and-white toadstool of picture books, under birch and pine.', 'source': 'Texas Mushrooms, p. 40'}, headers=H).status_code == 201
        X = t.get('/api/facts/export').get_json()
        rows = [x for x in X['facts'] if x['status'] == 'accepted'][:3]
        for x in rows: x['value'] = (x['value'] + ' (elsewhere)') if isinstance(x['value'], str) else x['value']
        d = t.post('/api/facts/import', json={'facts': rows + rows[:1] + [{'key': 'x y', 'field': 'nope', 'value': '1'}, {'key': 'amanita muscaria', 'kind': 'fungus', 'field': 'about_summary', 'value': 'tasty', 'source': 'no'}]}, headers=H).get_json()
        assert d['added'] >= 1 and d['skipped'] >= 3, d
        with S.app.app_context():
            c = S.db()
            assert c.execute("SELECT COUNT(*) FROM facts WHERE note LIKE 'Imported by%' AND status<>'proposed'").fetchone()[0] == 0, 'import never accepts'
            assert not c.execute("SELECT 1 FROM facts WHERE value='tasty'").fetchone()
