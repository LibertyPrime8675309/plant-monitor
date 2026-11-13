"""1.58.0 (November 12 review, item 8): the messages say what a night would really do, and care that was never logged is not "due".
The pages' side of this is in dev/test/frost_check.py (made-up forecasts) and care_check.py."""
from datetime import date
import server as S

def test_a_night_is_described_by_its_own_numbers():
    assert S.cold_words({'danger': 3, 'damage': 8, 'watch': 14}) == '3 plants could die, 8 would be damaged and 14 are close calls'
    assert S.cold_words({'danger': 0, 'damage': 0, 'watch': 1}) == '1 plant is a close call'
    assert S.cold_words({'danger': 1, 'damage': 0, 'watch': 0}) == '1 plant could die'
    assert S.cold_words({'danger': 0, 'damage': 2, 'watch': 1}) == '2 plants would be damaged and 1 is a close call'

def test_the_evening_reminder_counts_what_is_left_and_says_when_nothing_would_be_damaged():
    P = lambda level, done=False: {'code': 'x', 'level': level, 'done': {'by': 'me'} if done else None}
    assert S.cold_evening([P('damage'), P('danger'), P('watch')]) == '2 plants to bring in or cover this evening. 1 more is a close call.'
    assert S.cold_evening([P('damage', True), P('damage')]) == '1 plant to bring in or cover this evening.'
    assert S.cold_evening([P('watch')]) == '1 close call: nothing is forecast to be damaged. Cover it to be safe.'
    assert S.cold_evening([P('watch'), P('watch')]) == '2 close calls: nothing is forecast to be damaged. Cover them to be safe.'
    assert S.cold_evening([P('damage', True), P('watch', True)]) is None, 'all ticked as covered: no reminder'

def test_a_new_cold_night_says_how_bad_it_is():
    """The message looked up n['worst'], which a night does not have, so a freeze that would kill plants read "are close calls"."""
    night = {'date': '2030-01-10', 'low': 22, 'level': 'danger', 'counts': {'danger': 60, 'damage': 8, 'watch': 4}, 'plants': [{'code': 'P-001', 'level': 'danger', 'done': None}]}
    sent = []
    keep = {k: getattr(S, k) for k in ('frost_report', 'push_once', 'push_send')}
    S.patch('frost_report', lambda c: {'nights': [night]})
    S.patch('push_once', lambda c, key, days: key.endswith(':new'))
    S.patch('push_send', lambda c, kind, title, body, url='#/', home_id=None, logins=None, tag=None: sent.append(title(S.UNIT_REGIONS['us']) if callable(title) else (title, body)))
    try:
        with S.app.app_context(): S.push_cold(S.db())
    finally:
        for k, v in keep.items(): S.patch(k, v)
    assert sent, 'a message was made'
    title, body = sent[0]
    assert title.startswith('Cold night ') and '22' in title
    assert body == 'Outside: 60 plants could die, 8 would be damaged and 4 are close calls. Open the cold-night checklist.'

def test_the_morning_message_leaves_out_plants_never_fed():
    keep = S.ics_feed_days
    S.patch('ics_feed_days', lambda c, a, b, weekday=None: [{'date': a.isoformat(), 'plants': [{'code': 'P-001', 'name': 'Fed before', 'every': 30, 'last': '2026-09-01'},
                                                                                             {'code': 'P-002', 'name': 'Never fed', 'every': 30, 'last': None},
                                                                                             {'code': 'P-900', 'name': 'At another home', 'every': 30, 'last': '2026-09-01'}]}])
    try: got = S.feed_due(None, {'P-001', 'P-002'}, date(2026, 11, 13))
    finally: S.patch('ics_feed_days', keep)
    assert [p['code'] for p in got] == ['P-001']
