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
