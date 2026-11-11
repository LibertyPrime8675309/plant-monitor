"""Pests that eat plants (prototype proto/browse-risk): the pure part."""
import server as S

def test_matches_by_genus_species_and_common_name():
    f = S.browse_for
    assert f('Dieffenbachia seguine', '')[0] == 'Low'
    assert f("Philodendron erubescens 'Pink Princess'", '')[0] == 'Low'
    assert f('Ficus lyrata', '')[0] == 'Low' and f('Ficus carica', '')[0] == 'Moderate'
    assert f('Ipomoea batatas (probable)', '')[0] == 'High' and f('Ipomoea hederacea (probable)', '')[0] == 'Moderate'
    assert f('Plectranthus scutellarioides', 'Coleus')[0] == 'High'
    assert f("xGraptosedum 'Francesco Baldi' type (probable)", '')[0] == 'Moderate'
    assert f('Cucurbitaceae (probably a gourd or melon; species unconfirmed)', '')[0] == 'High'

def test_falls_back_to_the_common_name_then_unknown():
    assert S.browse_for('Unknown', 'Hibiscus (Summer Vibes)')[0] == 'High'
    assert S.browse_for('Not identified', 'Young shrub with toothed leaves') == ('Unknown', '')
    assert S.browse_for(None, None) == ('Unknown', '')

def test_every_entry_has_a_valid_risk_and_a_reason():
    for k, (risk, why) in S.BROWSE.items():
        assert risk in S.RISKS and len(why) > 20, k

def test_a_risk_set_by_hand_beats_the_usual_for_the_kind():
    row = {'code': 'P-1', 'common_name': 'Coleus', 'scientific_name': 'Plectranthus scutellarioides', 'site': 'Outdoors', 'browse_risk': ''}
    assert S.browse_row(row)['risk'] == 'High' and S.browse_row(row)['source'] == 'kind'
    own = S.browse_row(dict(row, browse_risk='Low'))
    assert own['risk'] == 'Low' and own['source'] == 'you' and own['usual'] == 'High'
    assert S.browse_row(dict(row, browse_risk='Bogus'))['risk'] == 'High'          # not one of the choices: ignored

def test_sightings_are_counted_with_who_ate_it():
    row = {'code': 'P-1', 'common_name': 'Aloe', 'scientific_name': 'Aloe vera', 'site': 'Outdoors', 'browse_risk': None}
    seen = [{'seen_on': '2026-11-10', 'pest': 'Rat'}, {'seen_on': '2026-11-01', 'pest': 'Not sure'}, {'seen_on': '2026-10-20', 'pest': 'Rabbit'}]
    x = S.browse_row(row, seen)['seen']
    assert x == {'count': 3, 'last': '2026-11-10', 'pests': ['Rabbit', 'Rat']}
    assert S.browse_row(row)['seen']['count'] == 0

def test_the_choices_for_a_sighting():
    assert 'Not sure' in S.BROWSE_PESTS and 'Rabbit' in S.BROWSE_PESTS and 'Rat' in S.BROWSE_PESTS and 'Mouse' in S.BROWSE_PESTS
    assert S.RISKS == ['Low', 'Moderate', 'High'] == S.BROWSE_RISKS
