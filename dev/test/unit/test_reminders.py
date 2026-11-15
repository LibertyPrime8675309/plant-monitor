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

# ---------------------------------------------------------------- November 15, 2026: the notification, the calendar file, the download, Done on an earlier day
OWN2 = {'X-Editor': 'Unit test'}

def test_the_morning_message_names_one_reminder_or_counts_several():
    one = [{'text': 'Look for roots', 'plant_name': 'Pothos', 'plant_code': 'P-001'}]
    assert S.remind_push_words(one, 'Round Rock') == ('Reminder for today at Round Rock', 'Look for roots (Pothos)')
    many = one + [{'text': 'Buy potting mix', 'plant_name': None, 'plant_code': None}] * 5
    title, body = S.remind_push_words(many, 'Round Rock')
    assert title == '6 reminders for today at Round Rock' and body.startswith('Look for roots (Pothos); Buy potting mix') and body.endswith('…')

def test_reminders_is_a_kind_of_notification_a_person_can_turn_off():
    assert ('remind', 'Your own reminders', 'On the morning a reminder of yours is due.') in S.PUSH_EXTRA_KINDS and S.remind_push in S.PUSH_CLOCK
    with S.app.test_client() as c:
        kinds = [k['key'] for k in c.get('/api/push').get_json()['kinds']]
        assert kinds[-1] == 'remind' and 'cold' in kinds, kinds

def test_a_reminder_is_in_the_calendar_file_on_its_day_and_in_the_download():
    with S.app.test_client() as c:
        with S.app.app_context(): today = S.local_today(S.db())
        soon = (today + timedelta(days=9)).isoformat()
        r = c.post('/api/reminders', json={'text': 'Repot the fig', 'due_on': soon}, headers=OWN2); assert r.status_code == 200
        rid = r.get_json()['id']
        ev = [e for e in c.get('/api/calendar').get_json()['events'] if e['kind'] == 'remind' and e['uid'] == f'remind-{rid}']
        assert len(ev) == 1 and ev[0]['date'] == soon and ev[0]['title'] == 'Reminder: Repot the fig'
        ics = c.get('/api/calendar.ics').get_data(as_text=True)
        assert f'UID:remind-{rid}@' in ics and 'SUMMARY:Reminder: Repot the fig' in ics and 'DTSTART;VALUE=DATE:' + soon.replace('-', '') in ics and 'CATEGORIES:Plants,Reminder' in ics
        rows = c.get('/api/export.json').get_json()['reminders']
        assert any(x['id'] == rid and x['text'] == 'Repot the fig' for x in rows)
        c.post(f'/api/reminders/{rid}/done', json={}, headers=OWN2)
        assert not [e for e in c.get('/api/calendar').get_json()['events'] if e.get('uid') == f'remind-{rid}'], 'a done one leaves the calendar'

def test_done_pressed_offline_keeps_the_day_it_was_pressed():
    with S.app.test_client() as c:
        with S.app.app_context(): today = S.local_today(S.db())
        was = (today - timedelta(days=2)).isoformat()
        rid = c.post('/api/reminders', json={'text': 'Water the seedlings', 'due_on': today.isoformat(), 'repeat_days': 7}, headers=OWN2).get_json()['id']
        with S.app.app_context(): d = S.db(); d.execute('UPDATE plant_reminders SET due_on=? WHERE id=?', (was, rid)); d.commit()      # it came due two days ago
        assert c.post(f'/api/reminders/{rid}/done', json={'done_on': (today + timedelta(days=1)).isoformat()}, headers=OWN2).status_code == 400
        assert c.post(f'/api/reminders/{rid}/done', json={'done_on': 'yesterday'}, headers=OWN2).status_code == 400
        r = c.post(f'/api/reminders/{rid}/done', json={'done_on': was}, headers=OWN2)
        assert r.status_code == 200 and r.get_json()['next'] == (today + timedelta(days=5)).isoformat(), 'the next one counts from the day it was done'
