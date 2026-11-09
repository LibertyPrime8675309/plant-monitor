"""Your own reminders (prototype proto/reminders): the pure parts and the API on a throwaway database."""
from datetime import date, timedelta
import pytest
import server as S

ED = {'X-Editor': 'Remind Test'}

def test_state_late_today_later():
    assert S.remind_state('2026-11-08', '2026-11-09') == 'late'
    assert S.remind_state('2026-11-09', '2026-11-09') == 'today'
    assert S.remind_state('2026-11-10', '2026-11-09') == 'later'

def test_clean_checks_the_fields():
    t = date(2026, 11, 9)
    with S.app.test_request_context():
        f = S.remind_clean({'text': '  Check   for roots ', 'due_on': '2026-11-16', 'repeat_days': 7}, t)
        assert f == {'text': 'Check for roots', 'due_on': '2026-11-16', 'repeat_days': 7}
        assert len(S.remind_clean({'text': 'x' * 500, 'due_on': '2026-11-16'}, t)['text']) == S.REMIND_TEXT_MAX
        for bad in ({'text': '', 'due_on': '2026-11-16'}, {'text': 'a', 'due_on': '16/11/2026'}, {'text': 'a', 'due_on': '2026-11-08'},
                    {'text': 'a', 'due_on': '2026-11-16', 'repeat_days': 5}, {'text': 'a', 'due_on': '2035-01-01'}):
            with pytest.raises(Exception): S.remind_clean(bad, t)
        assert S.remind_clean({'due_on': '2026-11-20'}, t, partial=True) == {'due_on': '2026-11-20'}

def test_add_done_repeat_and_take_back():
    with S.app.test_client() as c:
        plant = c.get('/api/plants').get_json()[0]['code']
        today = c.get('/api/reminders').get_json()['today']
        r = c.post('/api/reminders', json={'text': 'Spray again for mealybugs', 'due_on': today, 'repeat_days': 7, 'plant': plant}, headers=ED)
        assert r.status_code == 200, r.get_data(as_text=True)
        rid = r.get_json()['id']
        R = c.get('/api/reminders?plant=' + plant).get_json()
        one = next(x for x in R['open'] if x['id'] == rid)
        assert one['state'] == 'today' and one['repeat_word'] == 'Every week' and one['plant_code'] == plant
        assert c.post('/api/reminders', json={'text': 'Buy potting mix', 'due_on': today}, headers=ED).status_code == 200
        A = c.get('/api/reminders').get_json()
        assert A['counts']['due'] >= 2 and any(x['plant_code'] is None for x in A['open'])
        # done: a repeating one comes back a week later
        d = c.post(f'/api/reminders/{rid}/done', headers=ED).get_json()
        nxt = (date.fromisoformat(today) + timedelta(days=7)).isoformat()
        assert d['next'] == nxt
        R = c.get('/api/reminders?plant=' + plant).get_json()
        assert [x['due_on'] for x in R['open']] == [nxt] and R['done'][0]['id'] == rid and R['done'][0]['can_undo']
        # not done yet: the next one goes, this one is back
        assert c.delete(f'/api/reminders/{rid}/done', headers=ED).status_code == 200
        R = c.get('/api/reminders?plant=' + plant).get_json()
        assert [x['id'] for x in R['open']] == [rid] and not R['done']
        # a week later, then removed
        assert c.put(f'/api/reminders/{rid}', json={'due_on': nxt}, headers=ED).get_json()['changed'] == ['due_on']
        assert c.delete(f'/api/reminders/{rid}', headers=ED).status_code == 200
        assert not c.get('/api/reminders?plant=' + plant).get_json()['open']
        assert c.put(f'/api/reminders/{rid}', json={'due_on': nxt}, headers=ED).status_code == 404
        notes = [a.get('note') or '' for a in c.get('/api/audit?n=20').get_json()]
        assert any(n.startswith('Reminder set for') for n in notes) and any(n.startswith('Reminder removed') for n in notes)
        assert c.post('/api/reminders', json={'text': 'x', 'due_on': today, 'plant': 'P-9999'}, headers=ED).status_code == 404
