"""Unit tests for propagation (proto/propagation): the ways match the guide's sections and the dates behave."""
import os, re
import server as S

def test_every_way_points_at_a_guide_section():
    js = open(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'app', 'static', 'js', 'guide.js'), encoding='utf-8').read()
    ids = set(re.findall(r"id: '(gd-[a-z-]+)'", js))
    assert {m['guide'] for m in S.METHODS.values()} <= ids

def test_every_mark_has_words_and_seed_counts_sprouts():
    for k, m in S.METHODS.items():
        assert all(x in S.EVENT_WORD for x in m['marks']), k
    assert S.METHODS['seed']['marks'] == ('sprouted',) and 'sprouted' in S.COUNTED

def test_stage_presets_cover_every_kind_and_are_sane():
    assert set(S.STAGE_PRESET) == set(S.STAGE_KINDS)
    for k, (days, lo, hi) in S.STAGE_PRESET.items():
        assert days >= 0 and (lo is None) == (hi is None) and (lo is None or lo < hi)

def test_check_days_prefers_the_persons_number_then_water_then_the_way():
    row = lambda **k: {'check_every': None, 'medium': '', 'method': 'layer', **k}
    assert S.check_days(row()) == 14 and S.check_days(row(medium='Water')) == 7 and S.check_days(row(check_every=3, medium='Water')) == 3

def test_dates_and_numbers_are_checked():
    from datetime import date
    import pytest, werkzeug.exceptions as E
    with pytest.raises(E.BadRequest): S.prop_iso('nope', 'Date')
    with pytest.raises(E.BadRequest): S.prop_iso('2999-01-01', 'Date', date(2026, 11, 12))
    assert S.prop_iso('2026-11-01', 'Date', date(2026, 11, 12)) == '2026-11-01'
    assert S.to_int('', 'x', 1, 5, none_ok=True) is None
    with pytest.raises(E.BadRequest): S.to_int('9', 'x', 1, 5)
