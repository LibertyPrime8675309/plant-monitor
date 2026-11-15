"""1.58.0: watering many plants at once stays at one home. A home can be marked as cared for outside the app (Baraboo, batch D1),
and a care entry is dated by the day where the plant lives."""
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
import server as S
H = {'X-Editor': 'Unit'}

def conn():
    c = sqlite3.connect(S.DB_PATH, timeout=30); c.row_factory = sqlite3.Row
    return c

def baraboo(c):
    return next(h for h in S.homes(c) if h['name'].startswith('Baraboo'))

def test_batch_d1_marks_baraboo_as_cared_for_outside_the_app():
    c = conn()
    try:
        B = baraboo(c)
        assert B['tended'] is False and all(h['tended'] for h in S.homes(c) if h['id'] != B['id'])
        assert S.place_brief(B)['tended'] is False, 'the page gets it with the homes'
    finally: c.close()

def test_the_owner_can_change_it_on_homes_and_places():
    c = conn(); bid = baraboo(c)['id']; c.close()
    with S.app.test_client() as t:
        for v, want in (('1', True), ('0', False)):
            r = t.put(f'/api/places/{bid}', json={'tended': v}, headers=H)
            assert r.status_code == 200 and r.get_json()['place']['tended'] is want

def test_init_db_twice_keeps_the_setting():
    S.init_db(); S.init_db()
    c = conn()
    try: assert baraboo(c)['tended'] is False
    finally: c.close()

def test_a_watering_is_dated_where_the_plant_lives():
    c = conn()
    try:
        B = baraboo(c)
        code = c.execute('SELECT code FROM plants WHERE home_id=?', (B['id'],)).fetchone()[0]
        assert S.home_today(c, B['id']) == datetime.now(ZoneInfo(B['tz'])).date()
        nc = next((h for h in S.homes(c) if h['tz'] == 'America/Los_Angeles'), None)
        if nc: assert S.home_today(c, nc['id']) == datetime.now(ZoneInfo('America/Los_Angeles')).date()
        assert S.home_today(c, None) == datetime.now(ZoneInfo(S.home_place(c)['tz'])).date(), 'no home id: the main home'
    finally: c.close()
    with S.app.test_client() as t:
        r = t.post('/api/care', json={'plant': code, 'kind': 'note', 'note': 'unit: dated where it lives'}, headers=H)
        assert r.status_code == 201
    c = conn()
    try:
        row = c.execute("SELECT done_on FROM care_log WHERE plant_code=? AND note='unit: dated where it lives'", (code,)).fetchone()
        assert row[0] == datetime.now(ZoneInfo(B['tz'])).date().isoformat()
        c.execute("DELETE FROM care_log WHERE note='unit: dated where it lives'"); c.commit()
    finally: c.close()
