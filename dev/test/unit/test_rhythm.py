"""How often you water (prototype proto/water-rhythm): the pure parts."""
import server as S

def test_state_needs_a_clear_difference():
    st = S.rhythm_state
    assert st(3, 10) == 'often' and st(20, 10) == 'seldom' and st(10, 10) == 'matches'
    assert st(5, 6) == 'matches'          # a day apart is not worth a change
    assert st(2, 3) == 'matches'          # nor is a short reminder a day early
    assert st(9, 6) == 'seldom' and st(4, 6) == 'often'

def test_the_setting_lands_the_reminder_nearest_the_gap():
    f = S.rhythm_setting_for
    for n in range(1, 40):
        for k in (0.6, 0.8, 1.0, 1.3, 1.5, 1.6):
            base, gives = f(n, k)
            assert 1 <= base <= 60 and gives == max(1, round(base * k))
            assert all(abs(gives - n) <= abs(max(1, round(b * k)) - n) for b in range(1, 61))   # no other setting comes closer
    assert f(3, 1.5) == (2, 3) and f(10, 1.0) == (10, 10)
