"""1.56.5: fixes from the November 11 review: a change from a phone cut off part way is not refused for ever; a viewer's page
checks against the server's own list of what viewers may send."""
from datetime import datetime, timedelta, timezone
import server as S
H = {'X-Editor': 'Unit'}

def iso(dt): return dt.strftime('%Y-%m-%dT%H:%M:%SZ')

def test_a_change_cut_off_part_way_is_made_when_sent_again():
    op_old, op_new = 'unit-op-' + 'a' * 20, 'unit-op-' + 'b' * 20
    with S.app.app_context():
        c = S.db()
        c.execute('INSERT INTO sync_ops(op,method,path,status,received_at) VALUES(?,?,?,0,?)', (op_old, 'POST', '/api/care', iso(datetime.now(timezone.utc) - timedelta(minutes=10))))
        c.execute('INSERT INTO sync_ops(op,method,path,status,received_at) VALUES(?,?,?,0,?)', (op_new, 'POST', '/api/care', iso(datetime.now(timezone.utc))))
        c.commit()
    with S.app.test_client() as t:
        r = t.post('/api/care', json={'kind': 'water', 'plant': 'P-001'}, headers={**H, 'X-Offline-Op': op_old})
        assert r.status_code in (200, 201), 'claimed ten minutes ago and never finished: made now'
        again = t.post('/api/care', json={'kind': 'water', 'plant': 'P-001'}, headers={**H, 'X-Offline-Op': op_old})
        assert again.headers.get('X-Offline-Replayed') == '1', 'and sending it once more gives the kept answer'
        r = t.post('/api/care', json={'kind': 'water', 'plant': 'P-001'}, headers={**H, 'X-Offline-Op': op_new})
        assert r.status_code == 503, 'claimed a moment ago: still being made'

def test_the_page_gets_the_viewer_lists():
    with S.app.test_client() as t:
        me = t.get('/api/me').get_json()
        assert '/api/whatsnew/seen' in me['viewer_ok']['posts'] and '/api/push/' in me['viewer_ok']['prefixes']
