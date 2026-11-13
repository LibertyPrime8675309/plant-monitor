"""1.58.0 (Ethan, November 13, 2026): Today asks once about care that was never logged (app/plantdb/asks.py), and rooms and spots
can be put in the order a round is walked (POST /api/where/order), which is the order Today lists the plants to water."""
import sqlite3
import pytest
import server as S

ED = {'X-Editor': 'Order Test'}

@pytest.fixture
def cl():
    c = sqlite3.connect(S.DB_PATH); c.execute("DELETE FROM settings WHERE key IN ('ask_feed', 'ask_flush')"); c.commit(); c.close()
    with S.app.test_client() as x: yield x
    c = sqlite3.connect(S.DB_PATH); c.execute("DELETE FROM settings WHERE key IN ('ask_feed', 'ask_flush')"); c.commit(); c.close()

def test_the_question_is_answered_once_and_can_be_asked_again(cl):
    assert cl.get('/api/asks').get_json() == {'feed': None, 'flush': None}
    a = cl.put('/api/asks', json={'kind': 'feed', 'answer': 'yes'}, headers=ED).get_json()
    assert a['feed']['answer'] == 'yes' and len(a['feed']['on']) == 10 and a['feed']['by'] == 'Order Test' and a['flush'] is None
    assert cl.put('/api/asks', json={'kind': 'flush', 'answer': 'no'}, headers=ED).get_json()['flush']['answer'] == 'no'
    assert cl.put('/api/asks', json={'kind': 'feed', 'answer': ''}, headers=ED).get_json()['feed'] is None, 'an empty answer: Today asks again'
    assert cl.put('/api/asks', json={'kind': 'water', 'answer': 'yes'}, headers=ED).status_code == 400
    assert cl.put('/api/asks', json={'kind': 'feed', 'answer': 'later'}, headers=ED).status_code == 400
    c = sqlite3.connect(S.DB_PATH)
    assert 'off' in c.execute("SELECT note FROM audit_log WHERE field='ask_flush' ORDER BY id DESC LIMIT 1").fetchone()[0]
    c.close()

def test_a_yes_counts_from_its_own_day(cl):
    from datetime import date
    import json
    c = sqlite3.connect(S.DB_PATH); c.row_factory = sqlite3.Row
    assert not S.ask_started(c, 'feed', 14, date(2026, 12, 1)), 'not asked'
    c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('ask_feed',?)", (json.dumps({'answer': 'yes', 'on': '2026-11-13', 'by': 'T'}),)); c.commit()
    assert not S.ask_started(c, 'feed', 14, date(2026, 11, 26)) and S.ask_started(c, 'feed', 14, date(2026, 11, 27))
    assert not S.ask_started(c, 'flush', 14, date(2027, 1, 1)), 'each kind has its own answer'
    c.close()

def names(cl, side='out'):
    home = cl.get('/api/where').get_json()['homes'][0]
    return [a['name'] for a in home['areas'] if a['side'] == side], home

def test_rooms_and_spots_move_one_place_at_a_time(cl):
    before, home = names(cl)
    assert len(before) >= 2, 'the test record has at least two areas outside'
    first = [a for a in home['areas'] if a['side'] == 'out'][0]
    r = cl.post('/api/where/order', json={'kind': 'area', 'id': first['id'], 'dir': 'down'}, headers=ED).get_json()
    after, _ = names(cl)
    assert r['moved'] and after[:2] == [before[1], before[0]] and after[2:] == before[2:]
    assert not cl.post('/api/where/order', json={'kind': 'area', 'id': [a for a in home['areas'] if a['side'] == 'out'][1]['id'], 'dir': 'up'}, headers=ED).get_json()['moved'], 'the first cannot go further up'
    assert cl.post('/api/where/order', json={'kind': 'area', 'id': first['id'], 'dir': 'up'}, headers=ED).get_json()['moved'] and names(cl)[0] == before, 'and back'
    inside_before = names(cl, 'in')[0]
    assert inside_before == [a['name'] for a in home['areas'] if a['side'] == 'in'], 'moving an area outside leaves the rooms inside as they were'
    # spots within one room
    made = []
    try:
        for n in ('Order test A', 'Order test B', 'Order test C'):
            h = cl.post('/api/where/spots', json={'area_id': first['id'], 'name': n}, headers=ED).get_json()
            made.append(next(s['id'] for x in h['homes'] for a in x['areas'] if a['id'] == first['id'] for s in a['spots'] if s['name'] == n))
        spots = lambda: [s['name'] for x in cl.get('/api/where').get_json()['homes'] for a in x['areas'] if a['id'] == first['id'] for s in a['spots'] if s['name'].startswith('Order test')]
        assert spots() == ['Order test A', 'Order test B', 'Order test C']
        assert cl.post('/api/where/order', json={'kind': 'spot', 'id': made[2], 'dir': 'up'}, headers=ED).get_json()['moved']
        assert cl.post('/api/where/order', json={'kind': 'spot', 'id': made[2], 'dir': 'up'}, headers=ED).get_json()['moved']
        assert spots() == ['Order test C', 'Order test A', 'Order test B']
        assert cl.post('/api/where/order', json={'kind': 'spot', 'id': 999999, 'dir': 'up'}, headers=ED).status_code == 404
        assert cl.post('/api/where/order', json={'kind': 'shelf', 'id': made[0], 'dir': 'up'}, headers=ED).status_code == 400
        assert cl.post('/api/where/order', json={'kind': 'spot', 'id': made[0], 'dir': 'sideways'}, headers=ED).status_code == 400
    finally:
        for i in made: cl.delete(f'/api/where/spots/{i}', headers=ED)
