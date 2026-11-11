"""1.57.0: the propagation and breeding guide. Its words are in static/js/guide.js; the server's part is one read-only route that lists each
active plant's propagation notes (the plant's own lines, then its species' methods) so the page can say which plants suit which method.
Nothing in the guide changes data, so a viewer may read it and no change route is added."""
import json
import server as S
G = S.MODULES[[m.__name__ for m in S.MODULES].index('plantdb.guide')]

def test_a_plants_own_lines_come_first_then_its_species_methods():
    facts = json.dumps({'propagation': [{'method': 'Stem cuttings', 'when': 'spring', 'how': 'x'}, {'method': 'Air layering', 'when': '', 'how': 'y'}]})
    got = G.guide_lines('Stem cuttings root in days in water.\nAir layering a tall cane.', facts)
    assert got[:2] == ['Stem cuttings root in days in water.', 'Air layering a tall cane.']
    assert 'Stem cuttings' not in got, 'a method already said in the plant\'s own lines is not repeated'
    assert got == ['Stem cuttings root in days in water.', 'Air layering a tall cane.'], 'both methods were already in its own lines'
    assert G.guide_lines('', facts) == ['Stem cuttings', 'Air layering']

def test_a_fungus_has_no_methods_listed_and_bad_data_is_ignored():
    facts = json.dumps({'propagation': [{'method': 'Spore print', 'when': '', 'how': 'z'}]})
    assert G.guide_lines('', facts, kind='fungus') == [], 'the guide is about plants'
    assert G.guide_lines(None, 'not json') == [] and G.guide_lines('  \n ', '') == []
    assert G.guide_lines('', json.dumps({'propagation': ['not a dict', {'method': None}]})) == []

def test_lines_are_cut_short_and_few():
    many = '\n'.join(f'Method number {i}' for i in range(40))
    assert len(G.guide_lines(many, '')) == G.GUIDE_LINES_MAX
    assert len(G.guide_lines('x' * 900, '')[0]) == G.GUIDE_LINE_LEN

def test_the_route_lists_active_plants_with_notes():
    with S.app.test_client() as t:
        r = t.get('/api/guide/plants')
        assert r.status_code == 200
        d = r.get_json()['plants']
        assert d, 'a fresh install has plants with propagation notes (batch A5)'
        assert all(set(p) == {'code', 'name', 'lines'} and p['lines'] for p in d)
        codes = [p['code'] for p in d]
        assert codes == sorted(codes)
        everyone = {x['code'] for x in t.get('/api/plants').get_json()}
        assert set(codes) <= everyone

def test_a_viewer_may_read_the_guide_but_nothing_can_change_through_it():
    routes = [r for r in S.app.url_map.iter_rules() if r.rule.startswith('/api/guide')]
    assert [r.rule for r in routes] == ['/api/guide/plants'] and all(r.methods - {'HEAD', 'OPTIONS'} == {'GET'} for r in routes)
