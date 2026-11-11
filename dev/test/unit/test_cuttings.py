"""Cuttings and new plants (prototype proto/cuttings): the pure parts."""
from datetime import date
import pytest
from werkzeug.exceptions import HTTPException
import server as S

T = date(2026, 11, 11)

def row(started, stage='rooting', stage_on=None, checked=None):
    return {'started_on': started, 'stage': stage, 'stage_on': stage_on, 'checked_on': checked}

def test_a_new_cutting_is_due_a_look_after_a_week():
    a = S.cut_state(row('2026-11-05'), T)
    assert a['days'] == 6 and a['active'] and not a['look_due'] and a['next_look'] == '2026-11-12'
    b = S.cut_state(row('2026-11-04'), T)
    assert b['look_due'] and b['next_look'] == '2026-11-11'

def test_a_look_or_a_new_stage_starts_the_week_again():
    assert not S.cut_state(row('2026-10-01', checked='2026-11-09'), T)['look_due']
    r = S.cut_state(row('2026-10-01', 'rooted', stage_on='2026-10-20'), T)
    assert r['look_due'] and r['rooted_after'] == 19

def test_finished_cuttings_are_never_due():
    for st in ('potted', 'given', 'lost'):
        s = S.cut_state(row('2026-09-01', st, stage_on='2026-10-01'), T)
        assert not s['active'] and not s['look_due'] and s['next_look'] is None

def test_clean_checks_the_fields():
    f = S.cut_clean({'method': 'Stem cuttings', 'medium': 'Water', 'how_many': '3'}, T)
    assert f == {'started_on': '2026-11-11', 'method': 'Stem cuttings', 'medium': 'Water', 'how_many': 3, 'notes': ''}
    for bad in ({'method': 'Magic'}, {'method': 'Seed', 'medium': 'Air'}, {'method': 'Seed', 'how_many': 0},
                {'method': 'Seed', 'started_on': '2026-11-12'}, {'method': 'Seed', 'started_on': 'last week'}):
        with pytest.raises(HTTPException): S.cut_clean(bad, T)
    assert S.cut_clean({'stage': 'rooted'}, T, partial=True) == {'stage': 'rooted'}
    with pytest.raises(HTTPException): S.cut_clean({'stage': 'sold'}, T, partial=True)

def test_words_for_the_audit_log():
    assert S.cut_words({'how_many': 3, 'method': 'Stem cuttings', 'medium': 'Water'}) == '3 stem cuttings in water'
    assert S.cut_words({'how_many': 1, 'method': 'Division', 'medium': ''}) == '1 division'
    assert S.cut_kv({'stage': 'rooted', 'how_many': 2}) == 'stage: Has roots; how many: 2'
