"""PLAN.md step 9 (1.56.0): what is in each pot. mix_summary() and mix_warning() are pure: parts by volume in, an estimate and a
plain sentence out. The routes record a recipe and a pot, and the watering list, the sitter sheet and the repot plan use them.
Ethan's answers of November 10, 2026: semi-hydro pots are topped up and flushed about weekly; water-only plants get fresh water
weekly; his pots (P-032, P-092, P-094 to P-098) are recorded by batch C5."""
import json
from datetime import date, timedelta
import server as S
M = S.MODULES[[m.__name__ for m in S.MODULES].index('plantdb.mixes')]
H = {'X-Editor': 'Unit'}

def row(name, parts, water=None, air=None, lasts=None, role='part', grade=''):
    return {'name': name, 'parts': parts, 'holds_water': water, 'airy': air, 'lasts_months': lasts, 'role': role, 'grade': grade, 'amount': ''}
BARK = lambda n, g='': row('Orchid bark', n, 2, 5, 18, grade=g)
PERLITE = lambda n: row('Horticultural perlite', n, 1, 5, 0)
COIR = lambda n: row('Coco coir', n, 4, 3, 24)
PEAT = lambda n: row('Peat moss', n, 5, 2, 24)
LECA = lambda n: row('Clay pebbles (LECA)', n, 2, 5, 0, role='medium')

def test_a_mix_is_estimated_from_its_parts_by_volume():
    s = M.mix_summary([BARK(3), PERLITE(2), COIR(1)])
    assert [x['share'] for x in s['shares']] == [50, 33, 17]
    assert s['water'] == round((3 * 2 + 2 * 1 + 1 * 4) / 6, 1) and s['air'] == round((3 * 5 + 2 * 5 + 1 * 3) / 6, 1)
    assert s['lasts_months'] == 18 and s['lasts_by'] == 'Orchid bark', 'the soonest-breaking part that is a fifth or more of it'
    assert s['words'].startswith('About: holds some water, lets in a great deal of air, wants freshening in about 1.5 years (the orchid bark breaks down).')
    assert 'An estimate' in s['words'], 'never told as a measurement'

def test_additives_and_small_shares_do_not_steer_it():
    s = M.mix_summary([PERLITE(9), row('Worm castings', 1, 4, 2, 6), row('Slow-release fertilizer', None, role='additive')])
    assert s['lasts_months'] == 0 and 'nothing in it breaks down soon' in s['words'], 'castings at a tenth do not set the freshening'
    assert len(s['shares']) == 2
    assert M.mix_summary([row('Mystery', 3), PERLITE(1)])['water'] is None, 'less than half the mix has a value: no estimate'
    assert M.mix_summary([])['known'] is False

def test_the_words_for_a_mix():
    assert M.parts_words([BARK(3, 'medium'), PERLITE(2), {**row('Slow-release fertilizer', None, role='additive'), 'amount': '1 teaspoon a gallon'}]) \
        == '3 orchid bark (medium), 2 horticultural perlite, plus slow-release fertilizer (1 teaspoon a gallon)'
    assert M.parts_words([LECA(1)]) == 'all clay pebbles (LECA)', 'one part: "all", and LECA keeps its capitals'
    assert M.am_low('LECA') == 'LECA' and M.am_low('Orchid bark') == 'orchid bark'

def test_a_warning_only_when_the_mix_and_the_species_disagree():
    wet = M.mix_summary([PEAT(3), COIR(1)]); airy = M.mix_summary([BARK(3), PERLITE(2)])
    assert 'fast-draining' in M.mix_warning(wet, 'Fast-draining', 'Soil mix')
    assert M.mix_warning(airy, 'Fast-draining', 'Soil mix') is None
    assert 'stays moist' in M.mix_warning(airy, 'Moisture-holding', 'Soil mix')
    assert M.mix_warning(wet, 'Fast-draining', 'Semi-hydro') is None, 'semi-hydro pots are wet by design'
    assert M.mix_warning(wet, '', 'Soil mix') is None

def test_median_and_how_often():
    assert M.median([3, 1, 2]) == 2 and M.median([1, 2, 3, 4]) == 2.5 and M.median([]) is None
    with S.app.app_context():
        c = S.db()
        assert M.hydro_every(c)['flush'] == 7 and M.hydro_every(c)['rootcheck'] == 30

def test_ethan_s_pots_and_the_amendments_came_with_batch_c5():
    with S.app.test_client() as t:
        d = t.get('/api/mixes').get_json()
        keys = {a['key'] for a in d['amendments']}
        assert {'orchid-bark', 'coco-coir', 'charcoal', 'pumice', 'worm-castings', 'perlite', 'vermiculite', 'leca'} <= keys, 'every one Ethan listed'
        assert len(d['amendments']) >= 20
        p = t.get('/api/mixes/plant/P-032').get_json()
        assert p['grow_kind'] == 'Semi-hydro' and p['reservoir'] == 'The pot itself (no holes)'
        assert p['mix']['words'] == 'all clay pebbles (LECA)' and p['hydro'] and {h['kind'] for h in p['hydro']} == {'topup', 'flush'}
        p = t.get('/api/mixes/plant/P-094').get_json()
        assert p['mix']['top'] and 'phagnum' in p['mix']['top']['name'], 'LECA with a sphagnum top layer'
        assert t.get('/api/mixes/plant/P-096').get_json()['grow_kind'] == 'Soil mix'

def test_record_a_recipe_and_a_repot():
    with S.app.test_client() as t:
        am = {a['key']: a['id'] for a in t.get('/api/mixes').get_json()['amendments']}
        r = t.post('/api/mixes/recipes', json={'name': 'Unit chunky', 'parts': [{'amendment_id': am['orchid-bark'], 'grade': 'medium', 'parts': 3},
                   {'amendment_id': am['perlite'], 'parts': 2}, {'amendment_id': am['coco-coir'], 'parts': 1}]}, headers=H)
        assert r.status_code == 201, r.get_json()
        rid = r.get_json()['id']
        assert t.post('/api/mixes/recipes', json={'name': 'Unit chunky', 'parts': []}, headers=H).status_code == 409, 'names are unique'
        r = t.post('/api/mixes/plant/P-001', json={'mixed_on': (date.today() - timedelta(days=1)).isoformat(), 'recipe_id': rid, 'repot': True}, headers=H)   # yesterday: today in UTC can be tomorrow in Texas
        assert r.status_code == 201
        p = r.get_json()
        assert p['mix']['recipe'] == 'Unit chunky' and p['mix']['care_id'] and p['mix']['words'].startswith('3 orchid bark (medium)')
        rec = next(x for x in t.get('/api/mixes').get_json()['recipes'] if x['id'] == rid)
        assert rec['plants'] == ['P-001'] and rec['interval']['plants'] == 0
        assert any(x['kind'] == 'repot' and x['id'] == p['mix']['care_id'] for x in t.get('/api/care?plant=P-001').get_json()), 'the repot is logged on the day'
        # a flush logged on a semi-hydro pot counts as a top-up too
        assert t.post('/api/care', json={'kind': 'flush', 'plant': 'P-092'}, headers=H).status_code in (200, 201)
        h = {x['kind']: x for x in t.get('/api/mixes/plant/P-092').get_json()['hydro']}
        assert h['flush']['state'] == 'ok' and h['topup']['last'] == h['flush']['last']
        with S.app.app_context():
            assert S.repot_mix(S.db(), 'P-001') == {'mix_months': 18, 'mix_by': 'Orchid bark'}
        assert t.post('/api/mixes/plant/P-001', json={'mixed_on': '2999-01-01', 'recipe_id': rid}, headers=H).status_code == 400
        assert t.put('/api/mixes/every', json={'flush': 0}, headers=H).status_code == 400
        assert t.put('/api/mixes/every', json={'flush': 10}, headers=H).get_json()['every']['flush'] == 10
        t.put('/api/mixes/every', json={'flush': 7}, headers=H)

def test_the_watering_list_says_top_up_for_semi_hydro():
    with S.app.test_client() as t:
        plants = {p['code']: p for p in t.get('/api/water').get_json()['plants']}
        assert plants['P-032']['action'] == 'topup' and plants['P-032']['action_word'] == 'Topped up the reservoir'
        soil = next(p for p in plants.values() if p.get('grow_kind') == 'Soil mix')
        assert soil['action'] == 'water'
        items = t.get('/api/mixes/care').get_json()['items']
        assert {x['kind'] for x in items} <= {'flush', 'rootcheck'}, 'top-ups are in the watering list, not twice'
        p32 = next(x for x in items if x['code'] == 'P-032')
        main = next(ph['file'] for ph in t.get('/api/plants/P-032').get_json()['photos'] if ph['is_primary'])
        assert p32['photo'] == main, '1.56.1: each plant comes with its main photo for Today'

def test_a_new_plant_and_clearing_the_fields_need_no_answer():
    with S.app.test_client() as t:
        r = t.post('/api/plants', json={'fields': {'common_name': 'Unit fern', 'site': 'Outdoors'}}, headers=H)
        assert r.status_code == 201, r.get_json()
        code = r.get_json()['code']
        assert t.get(f'/api/mixes/plant/{code}').get_json()['grow_kind'] == 'Soil mix', 'empty is a soil mix'
        v = t.get(f'/api/plants/{code}').get_json()['version']
        r = t.put(f'/api/plants/{code}', json={'base_version': v, 'fields': {'grow_kind': 'Semi-hydro'}}, headers=H)
        assert r.status_code == 200 and t.get(f'/api/mixes/plant/{code}').get_json()['grow_kind'] == 'Semi-hydro'
        r = t.put(f'/api/plants/{code}', json={'base_version': v + 1, 'fields': {'grow_kind': '', 'mix_wants': ''}}, headers=H)
        assert r.status_code == 200, 'choosing "not set" again clears it'
