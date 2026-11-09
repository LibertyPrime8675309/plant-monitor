"""The repotting plan (prototype proto/repotting): the pure parts."""
from datetime import date
import server as S

def row(code, rate='Moderate', leaf=None):
    return {'code': code, 'name': code, 'growth_rate': rate, 'leaf_type': leaf}

def test_add_months_keeps_the_day_or_the_month_end():
    assert S.add_months(date(2025, 4, 15), 12) == date(2026, 4, 15)
    assert S.add_months(date(2025, 4, 15), 18) == date(2026, 10, 15)
    assert S.add_months(date(2025, 8, 31), 6) == date(2026, 2, 28)
    assert S.add_months(date(2023, 8, 31), 6) == date(2024, 2, 29)

def test_how_often_comes_from_the_growth_rate():
    a = S.repot_auto
    assert a('Fast', None)[0] == a('Very fast in heat', None)[0] == a('Extremely fast: can double in about two weeks', None)[0] == 12
    assert a('Moderate to fast in warmth', None)[0] == 18
    assert a('Moderate; slower indoors', None)[0] == a('Slow to moderate', None)[0] == 24
    assert a('Slow: a few leaves a year', None)[0] == 36
    assert a('', None)[0] == 24 and 'not filled in' in a('', None)[1]
    assert a('Fast', 'Grows in water')[0] is None

def test_the_season_is_march_to_may():
    s = S.repot_season(date(2026, 11, 7))
    assert not s['now'] and s['from'] == '2027-03-01' and s['to'] == '2027-05-31'
    s = S.repot_season(date(2027, 4, 2))
    assert s['now'] and s['to'] == '2027-05-31'
    assert S.repot_season(date(2027, 6, 1))['year'] == 2028

def test_due_this_coming_spring_later_and_never():
    rows = [row('A', 'Fast'), row('B', 'Slow'), row('C'), row('D', 'Fast', 'Grows in water'), row('E', 'Fast')]
    last = {'A': '2025-10-01', 'B': '2025-04-15', 'E': '2026-07-01'}
    R = S.repot_plan(date(2026, 11, 7), rows, last, {'E': 'off'})
    st = {p['code']: p for p in R['plants']}
    assert st['A']['state'] == 'due' and st['A']['due_on'] == '2026-10-01'        # overdue: repot next spring
    assert st['B']['state'] == 'later' and st['B']['spring'] == 2028              # three years: due April 2028
    assert st['C']['state'] == 'never'
    assert {p['code'] for p in R['left_out']} == {'D', 'E'}
    assert next(p for p in R['left_out'] if p['code'] == 'E')['why'] == 'Switched off by hand'
    assert R['counts'] == {'due': 1, 'never': 1, 'later': 1, 'left_out': 2}
    # a fast grower repotted in July is due the next July: it is done that spring, a little early, rather than a year late
    E = S.repot_plan(date(2026, 11, 7), [row('E', 'Fast')], last, {})['plants'][0]
    assert E['state'] == 'due' and E['spring'] == 2027
    assert S.repot_plan(date(2026, 4, 10), [row('E', 'Fast')], {'E': '2026-04-01'}, {})['plants'][0]['state'] == 'later'   # just repotted
    # due in September waits for the next spring
    assert S.spring_of(date(2027, 9, 1)) == 2028 and S.spring_of(date(2027, 8, 31)) == 2027

def test_a_choice_by_hand_wins():
    R = S.repot_plan(date(2026, 11, 7), [row('A', 'Slow')], {'A': '2025-04-01'}, {'A': 12})
    p = R['plants'][0]
    assert p['months'] == 12 and p['state'] == 'due' and 'chosen by hand' in p['why']
