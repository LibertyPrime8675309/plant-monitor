import pytest
import shops as SH

@pytest.mark.parametrize('title,price,kind,size,per,unit', [
    ('Pumice 1/4 in, 0.5 cu ft', 13.99, 'amend', '', 13.99 / (0.5 * 25.71), 'quart'),
    ('Succulent and cactus soil, 20 qt', 24.99, 'mix', '', 24.99 / 20, 'quart'),
    ('Potting mix 1.5 cu. ft.', 12, 'mix', '', 12 / (1.5 * 25.71), 'quart'),
    ('Pumice 1/4 in', 13.99, 'amend', '0.5 cu ft', 13.99 / (0.5 * 25.71), 'quart'),     # the size from the cheapest variant
    ('Bloom fertilizer 2-7-7', 11.95, 'fert', '2 lb', 11.95 / 2, 'pound'),
    ('Worm castings 15 lbs', 20, 'amend', '', 20 / 15, 'pound'),
    ('Seaweed 32 oz', 10, 'fert', '', 10 / 2, 'pound'),
    ('Liquid fish 1 gal', 30, 'fert', '', 30 / 4, 'quart'),
    ('Coco coir 5 kg block', 18, 'mix', '', 18 / (5 * 2.2046), 'pound'),
    ('Frost protection blanket 10 x 12 ft', 18.99, 'frost', '', 18.99 / 120, 'square foot'),
    ("Frost cloth 6.5' x 50'", 40, 'frost', '', 40 / 325, 'square foot'),
    ('Nursery pots 6 inch, 10 pack', 15, 'pots', '', 1.5, 'each'),
])
def test_unit_price(title, price, kind, size, per, unit):
    u = SH.unit_price(title, price, kind, size)
    assert u and u['unit'] == unit and abs(u['per'] - per) < 0.01

@pytest.mark.parametrize('title,kind', [('Monstera deliciosa 6 in pot', 'plant'), ('Neem oil 16 fl oz', 'pest'), ('A bag of something', 'mix'), ('Trowel', 'tools')])
def test_unit_price_none(title, kind):
    assert SH.unit_price(title, 9.99, kind) is None

def test_unit_price_no_price():
    assert SH.unit_price('Pumice 8 qt', None, 'amend') is None

def test_matches_every_word_of_a_term():
    assert SH.matches('Bluebonnet, Texas - 4 in. pot', ['Texas bluebonnet'])
    assert SH.matches('Texas bluebonnets (live plants)', ['Texas bluebonnet'])
    assert not SH.matches('Bluebonnet print poster', ['Texas bluebonnet'])
    assert not SH.matches('Anything', [])

def test_terms_for_prefers_own_search_words():
    assert SH.terms_for({'search_words': 'pumice; horticultural pumice', 'common_name': 'x', 'name': 'y'}) == ['pumice', 'horticultural pumice']
    assert SH.terms_for({'search_words': '', 'common_name': 'Texas bluebonnet', 'name': 'Lupinus texensis'}) == ['Texas bluebonnet', 'Lupinus texensis']
    assert SH.terms_for({'common_name': 'Swiss cheese plant (big)', 'name': 'Monstera deliciosa'})[0] == 'Swiss cheese plant'

def test_offers_from_lines_takes_the_price_on_the_same_line():
    lines = [('u', '4 inch Texas bluebonnet – $2.50'), ('u', 'Agave americana, large'), ('u', '$9.00')]
    out = SH.offers_from_lines(lines, ['Texas bluebonnet', 'Agave americana'])
    by = {o['title']: o for o in out}
    assert by['4 inch Texas bluebonnet – $2.50']['price'] == 2.5
    assert by['Agave americana, large']['price'] == 9.0       # the price on the next line of the same page
