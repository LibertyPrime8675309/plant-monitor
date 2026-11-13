"""1.58.0, from Ethan (November 13, 2026): the weather history has a backup of its own, in pieces (app/plantdb/wxbackup.py).
The first piece is everything; each later one holds only the days that are new or have changed; together they are the whole
history; combining them loses nothing; putting back only adds; and the other backups leave the weather out once it is covered,
without a restore ever losing it."""
import json, os, shutil, sqlite3, time, zipfile
from datetime import datetime, timedelta, timezone
import pytest
import server as S
import plantdb.wxbackup as WXM

ED = {'X-Editor': 'Weather Test'}

def conn():
    c = sqlite3.connect(S.DB_PATH, timeout=30); c.row_factory = sqlite3.Row
    return c

def put(key, value):
    c = conn()
    if value is None: c.execute('DELETE FROM settings WHERE key=?', (key,))
    else: c.execute('INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)', (key, value))
    c.commit(); c.close()

def day(c, dev, loc, d, temp=70.0):
    """One day of weather for a place: 24 hourly rows and its summary."""
    for h in range(24):
        c.execute("INSERT OR REPLACE INTO readings(ts,source,device,temp_f,humidity,par,extra) VALUES(?,?,?,?,?,?,?)",
                  (f'{d}T{h:02d}:00:00Z', 'weather', dev, temp + h, 50, 100.0, json.dumps({'rain': 0})))
    c.execute("INSERT OR REPLACE INTO weather_daily(loc_id,date,data,kind,updated_at) VALUES(?,?,?,?,?)", (loc, d, json.dumps({'high': temp + 23}), 'observed', S.now()))

def rows(c=None):
    own = c is None; c = c or conn()
    try: return (c.execute("SELECT COUNT(*) FROM readings WHERE source='weather'").fetchone()[0], c.execute('SELECT COUNT(*) FROM weather_daily').fetchone()[0])
    finally:
        if own: c.close()

@pytest.fixture
def wx():
    """Three days of weather for the home place, no pieces yet; everything is put back as it was afterwards."""
    c = conn()
    L = c.execute('SELECT id, device FROM locations ORDER BY is_home DESC, id LIMIT 1').fetchone()
    was = {k: (c.execute('SELECT value FROM settings WHERE key=?', (k,)).fetchone() or [None])[0] for k in ('wx_backup', 'wx_backup_last', 'wx_backup_result')}
    files = set(os.listdir(S.BACKUP_DIR))
    c.execute("DELETE FROM readings WHERE source='weather'"); c.execute('DELETE FROM weather_daily')
    for d in ('2026-11-01', '2026-11-02', '2026-11-03'): day(c, L['device'], L['id'], d)
    c.commit(); c.close()
    shutil.rmtree(S.WX_DIR, ignore_errors=True)
    for k in was: put(k, None)
    yield {'dev': L['device'], 'loc': L['id']}
    c = conn(); c.execute("DELETE FROM readings WHERE source='weather'"); c.execute('DELETE FROM weather_daily'); c.commit(); c.close()
    shutil.rmtree(S.WX_DIR, ignore_errors=True)
    for f in set(os.listdir(S.BACKUP_DIR)) - files:
        if os.path.isfile(os.path.join(S.BACKUP_DIR, f)): os.remove(os.path.join(S.BACKUP_DIR, f))
    for k, v in was.items(): put(k, v)

def piece_rows(name):
    with zipfile.ZipFile(os.path.join(S.WX_DIR, name)) as z:
        tmp = os.path.join(S.WX_DIR, 'look.db')
        with z.open('weather.db') as src, open(tmp, 'wb') as dst: shutil.copyfileobj(src, dst)
    try:
        p = sqlite3.connect(tmp)
        out = (sorted({r[0][:10] for r in p.execute('SELECT ts FROM readings')}), [r[0] for r in p.execute('SELECT date FROM weather_daily ORDER BY date')],
               p.execute('SELECT COUNT(*) FROM readings').fetchone()[0])
        p.close(); return out
    finally: os.remove(tmp)

def test_the_first_piece_is_everything_and_the_next_only_what_changed(wx):
    c = conn(); c.execute("INSERT INTO weather_daily(loc_id,date,data,kind,updated_at) VALUES(?,?,?,?,?)", (wx['loc'], '2026-11-09', '{"high": 60}', 'forecast', S.now())); c.commit(); c.close()
    a = S.wx_make('Test')
    assert a['file'].endswith('-full.zip') and (a['rows'], a['days'], a['first'], a['last']) == (72, 3, '2026-11-01', '2026-11-03'), 'a forecast is not history: it is left out'
    again = S.wx_make('Test')
    assert again['file'] is None and again['compared'] == 6 and again['changed'] == 0, 'nothing new, so no file'
    c = conn()
    c.execute("UPDATE readings SET temp_f=99 WHERE source='weather' AND ts='2026-11-02T05:00:00Z'")          # an hour is revised
    day(c, wx['dev'], wx['loc'], '2026-11-04')                                                               # and a day is new
    c.execute("UPDATE weather_daily SET updated_at=? WHERE date='2026-11-01'", ('2030-01-01T00:00:00Z',))    # a day written again with the same figures is no change
    c.commit(); c.close()
    b = S.wx_make('Test')
    assert b['file'].endswith('-part.zip') and b['changed'] == 3
    hourly, daily, n = piece_rows(b['file'])
    assert hourly == ['2026-11-02', '2026-11-04'] and n == 48, 'the whole of each changed day, and no other day'
    assert daily == ['2026-11-04']
    ps = S.wx_pieces()
    assert [p['kind'] for p in ps] == ['full', 'part'] and len(S.wx_have(ps)) == 8
    c = conn(); live = {k: v[0] for k, v in S.wx_scan(c).items()}; c.close()
    assert S.wx_have(ps) == live, 'the pieces together are the record'
    assert S.wx_make('Test')['file'] is None

def test_combining_keeps_every_day_and_only_then_removes_the_old_pieces(wx):
    S.wx_make('Test'); c = conn(); day(c, wx['dev'], wx['loc'], '2026-11-04'); c.execute("UPDATE readings SET temp_f=12 WHERE ts='2026-11-03T00:00:00Z' AND source='weather'"); c.commit(); c.close()
    S.wx_make('Test')
    assert [p['file'] for p in S.wx_pieces()] == sorted(p['file'] for p in S.wx_pieces()) and len({p['file'] for p in S.wx_pieces()}) == 2, 'two pieces in one second still sort in the order they were made'
    before = S.wx_have()
    r = S.wx_combine('Test')
    ps = S.wx_pieces()
    assert r['replaced'] == 2 and [p['file'] for p in ps] == [r['file']] and ps[0]['kind'] == 'full'
    assert (ps[0]['rows'], ps[0]['days']) == (96, 4) and S.wx_have(ps) == before
    hourly, daily, n = piece_rows(r['file'])
    assert n == 96 and daily == ['2026-11-01', '2026-11-02', '2026-11-03', '2026-11-04']
    assert S.wx_combine('Test') == {'file': None, 'replaced': 0}, 'one piece: nothing to combine'

def test_a_combine_that_does_not_match_removes_nothing(wx, monkeypatch):
    S.wx_make('Test'); c = conn(); day(c, wx['dev'], wx['loc'], '2026-11-04'); c.commit(); c.close(); S.wx_make('Test')
    names = [p['file'] for p in S.wx_pieces()]
    real = S.wx_have
    monkeypatch.setattr(WXM, 'wx_have', lambda pieces=None: {**real(pieces), 'h|gone|2020-01-01': 'x'})
    with pytest.raises(ValueError): S.wx_combine('Test')
    assert [p['file'] for p in S.wx_pieces()] == names, 'both pieces are still there, and the one that did not match is gone'

def test_putting_back_adds_what_is_missing_and_changes_nothing_else(wx):
    S.wx_make('Test')
    c = conn()
    c.execute("DELETE FROM readings WHERE source='weather' AND ts LIKE '2026-11-01%'"); c.execute("DELETE FROM weather_daily WHERE date='2026-11-01'")
    c.execute("UPDATE readings SET temp_f=-40 WHERE source='weather' AND ts='2026-11-03T12:00:00Z'"); c.commit(); c.close()
    r = S.wx_fill('Test')
    assert (r['hourly'], r['days'], r['pieces'], r['skipped_places']) == (24, 1, 1, 0)
    c = conn()
    assert rows(c) == (72, 3)
    assert c.execute("SELECT temp_f FROM readings WHERE source='weather' AND ts='2026-11-03T12:00:00Z'").fetchone()[0] == -40, 'a row the record has is left as it is'
    assert 'put back' in c.execute("SELECT note FROM audit_log WHERE field='weather' ORDER BY id DESC LIMIT 1").fetchone()[0]
    c.close()
    assert S.wx_fill('Test')['hourly'] == 0

def test_weather_of_a_place_the_record_no_longer_has_stays_in_the_pieces(wx):
    c = conn(); c.execute("INSERT INTO locations(name,lat,lon,tz,device,created_at) VALUES('Gone',10,10,'UTC','wx-gone',?)", (S.now(),)); lid = c.execute('SELECT last_insert_rowid()').fetchone()[0]
    day(c, 'wx-gone', lid, '2026-11-01'); c.commit(); c.close()
    try:
        S.wx_make('Test')
        c = conn(); c.execute("DELETE FROM readings WHERE source='weather'"); c.execute('DELETE FROM weather_daily'); c.execute('DELETE FROM locations WHERE id=?', (lid,)); c.commit(); c.close()
        r = S.wx_fill('Test')
        assert r['skipped_places'] == 1 and (r['hourly'], r['days']) == (72, 3) and rows() == (72, 3)
    finally:
        c = conn(); c.execute('DELETE FROM locations WHERE id=?', (lid,)); c.commit(); c.close()

def test_other_backups_leave_the_weather_out_once_it_is_covered(wx):
    assert not S.wx_covered(), 'no piece yet: the weather stays in the other backups'
    name = S.make_backup('manual', False, 'with weather', 'Test')
    with zipfile.ZipFile(os.path.join(S.BACKUP_DIR, name)) as z: assert json.loads(z.read('backup.json'))['weather'] is True
    S.wx_make('Test'); assert S.wx_covered()
    time.sleep(1.1)                             # a backup is named to the second
    name = S.make_backup('manual', False, 'without weather', 'Test')
    tmp = os.path.join(S.BACKUP_DIR, 'look.db')
    with zipfile.ZipFile(os.path.join(S.BACKUP_DIR, name)) as z:
        assert json.loads(z.read('backup.json'))['weather'] is False
        with z.open('plants.db') as src, open(tmp, 'wb') as dst: shutil.copyfileobj(src, dst)
    try:
        b = sqlite3.connect(tmp)
        assert rows(b) == (0, 0) and b.execute('SELECT COUNT(*) FROM plants').fetchone()[0] > 0
        idx = {r[0] for r in b.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='readings'")}
        assert {'readings_uq', 'readings_ts', 'readings_src_ts', 'readings_src_dev_ts'} <= idx, 'the indexes are back after the weather is taken out'
        assert b.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        b.close()
    finally: os.remove(tmp)
    assert rows() == (72, 3), 'the record itself still has its weather'
    assert [x for x in S.bk_list() if x['file'] == name][0]['weather'] is False
    assert S.wx_covered(t=datetime.now(timezone.utc) + timedelta(days=14)) and not S.wx_covered(t=datetime.now(timezone.utc) + timedelta(days=17)), \
        'a weekly weather backup that has not run for over two weeks no longer counts: the other backups carry the weather again'
    put('wx_backup', json.dumps({'enabled': False}))
    assert not S.wx_covered(), 'weather backup turned off: the other backups carry the weather again'

def test_restoring_a_backup_without_weather_keeps_the_weather(wx):
    S.wx_make('Test')
    name = S.make_backup('manual', False, 'without weather', 'Test')
    c = conn(); day(c, wx['dev'], wx['loc'], '2026-11-05'); c.commit(); c.close()             # weather that arrived after the backup
    time.sleep(1.1)
    r = S.restore_backup(name, 'Test')
    assert r['weather'].startswith('kept as it was (96') and rows() == (96, 4), 'nothing of the weather is lost, the newest day included'
    c = conn(); c.execute("DELETE FROM readings WHERE source='weather'"); c.execute('DELETE FROM weather_daily'); c.commit(); c.close()    # a new computer: no weather at all
    time.sleep(1.1)
    r = S.restore_backup(name, 'Test')
    assert r['weather'].startswith('put back from the weather backup (72') and rows() == (72, 3), 'what the pieces hold is put back'
    c = conn(); note = c.execute("SELECT note FROM audit_log WHERE field='restore' ORDER BY id DESC LIMIT 1").fetchone()[0]; c.close()
    assert 'Weather history: put back' in note

def test_its_own_schedule(wx):
    c = conn(); utc = timezone.utc
    assert S.wx_due(c), 'never run: due'
    put('wx_backup_last', '2026-11-01T10:00:00Z')
    assert not S.wx_due(c, datetime(2026, 11, 7, 23, 0, tzinfo=utc)), 'weekly: not yet on day 6'
    assert S.wx_due(c, datetime(2026, 11, 9, 12, 0, tzinfo=utc)), 'weekly: due after a week'
    put('wx_backup', json.dumps({'freq': 'daily', 'hour': 4}))
    assert S.wx_due(c, datetime(2026, 11, 3, 0, 0, tzinfo=utc))
    put('wx_backup', json.dumps({'enabled': False}))
    assert not S.wx_due(c, datetime(2027, 1, 1, tzinfo=utc)), 'turned off'
    c.close()

def test_the_page_can_read_and_set_it(wx):
    with S.app.test_client() as cl:
        d = cl.get('/api/backups/weather').get_json()
        assert d['pieces'] == [] and d['covered'] is False and d['settings'] == {'enabled': True, 'freq': 'weekly', 'hour': 4} and d['live']['rows'] == 72
        assert cl.put('/api/backups/weather/settings', json={'freq': 'hourly'}, headers=ED).status_code == 400
        assert cl.put('/api/backups/weather/settings', json={'hour': 24}, headers=ED).status_code == 400
        assert cl.put('/api/backups/weather/settings', json={'freq': 'monthly', 'hour': 6}, headers=ED).get_json()['settings'] == {'enabled': True, 'freq': 'monthly', 'hour': 6}
        assert cl.post('/api/backups/weather', json={'what': 'burn'}, headers=ED).status_code == 400
        S.wx_make('Test')
        d = cl.get('/api/backups/weather').get_json()
        assert len(d['pieces']) == 1 and 'sigs' not in d['pieces'][0] and d['covered'] is True and d['held_days'] == 6
        f = d['pieces'][0]['file']
        assert cl.get('/api/backups/weather/' + f).status_code == 200
        assert cl.get('/api/backups/weather/plantdb-weather-20200101-000000-full.zip').status_code == 404
        assert cl.get('/api/backups/weather/..%2Fplants.db').status_code == 404

def test_a_record_with_no_weather_gets_it_back_by_itself(wx):
    S.wx_make('Test')
    c = conn(); c.execute("DELETE FROM readings WHERE source='weather'"); c.execute('DELETE FROM weather_daily'); c.commit()
    WXM.WX_AUTOFILL['tried'] = False; WXM.WX_JOB.clear(); WXM.WX_JOB['running'] = False
    put('wx_backup_last', S.now())                       # not due: only the putting back can start
    S.wx_backup_tick(c)
    for _ in range(200):
        if not WXM.WX_JOB.get('running') and WXM.WX_JOB.get('finished'): break
        time.sleep(0.05)
    assert WXM.WX_JOB.get('what') == 'fill' and WXM.WX_JOB.get('ok') and rows() == (72, 3), 'a database put in place by hand gets its weather back from the pieces'
    WXM.WX_JOB.clear(); WXM.WX_JOB['running'] = False
    c.execute("DELETE FROM readings WHERE source='weather'"); c.commit()
    S.wx_backup_tick(c); c.close()
    assert not WXM.WX_JOB.get('what'), 'once per run of the app: weather removed on purpose is not put back again and again'

def test_a_day_that_lost_hours_is_replaced_whole(wx):
    S.wx_make('Test')
    c = conn(); c.execute("DELETE FROM readings WHERE source='weather' AND ts IN ('2026-11-02T03:00:00Z', '2026-11-02T04:00:00Z')"); c.commit(); c.close()
    b = S.wx_make('Test')
    assert b['rows'] == 22 and b['changed'] == 1
    r = S.wx_combine('Test')
    assert r['rows'] == 70, 'the later piece\'s day takes the place of the whole day: the two hours that went are not brought back'
    c = conn(); live = {k: v[0] for k, v in S.wx_scan(c).items()}; c.close()
    assert S.wx_have() == live
