"""1.57.0 (review item 24): fast tests for the parts that matter most when they go wrong quietly: backups and restore, when a plant
needs water, frost warnings, the weather sums and dates. Changes to the throwaway database are made in a transaction and rolled back,
so the tests do not depend on each other."""
import json, os, sqlite3, zipfile
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest
import server as S

def conn():
    c = sqlite3.connect(S.DB_PATH, timeout=30); c.row_factory = sqlite3.Row
    return c

# ---------------------------------------------------------------- backups
def test_a_backup_holds_the_database_and_restores_it():
    name = S.make_backup('manual', False, 'unit test', 'Unit')
    path = os.path.join(S.BACKUP_DIR, name)
    with zipfile.ZipFile(path) as z:
        assert set(z.namelist()) == {'plants.db', 'backup.json'}
        meta = json.loads(z.read('backup.json'))
    assert meta['version'] == S.APP_VERSION and meta['by'] == 'Unit' and meta['plants'] > 0
    assert any(b['file'] == name and b['kind'] == 'manual' and not b['broken'] for b in S.bk_list())
    c = conn(); before = c.execute('SELECT common_name FROM plants WHERE code=?', ('P-001',)).fetchone()[0]
    c.execute('UPDATE plants SET common_name=? WHERE code=?', ('Changed after the backup', 'P-001')); c.commit(); c.close()
    tested = conn().execute("SELECT value FROM settings WHERE key='restore_tested_at'").fetchone()
    out = S.restore_backup(name, 'Unit', before=True)
    c = conn()      # a restore counts as the quarterly restore test; put that back as it was, for the other tests
    if tested: c.execute("UPDATE settings SET value=? WHERE key='restore_tested_at'", (tested[0],))
    else: c.execute("DELETE FROM settings WHERE key='restore_tested_at'")
    c.commit(); c.close()
    assert out['ok'] and out['before'] and out['plants'] == meta['plants']
    c = conn()
    assert c.execute('SELECT common_name FROM plants WHERE code=?', ('P-001',)).fetchone()[0] == before, 'the restore put the old name back'
    note = c.execute("SELECT note FROM audit_log WHERE action='backup' AND field='restore' ORDER BY id DESC LIMIT 1").fetchone()[0]
    c.close()
    assert out['before'] in note and 'True' not in note

def test_a_backup_from_a_newer_version_or_a_damaged_zip_is_refused():
    newer = os.path.join(S.BACKUP_DIR, 'plantdb-backup-20990101-000000-manual.zip')
    with zipfile.ZipFile(newer, 'w') as z:
        z.writestr('plants.db', b'not a database'); z.writestr('backup.json', json.dumps({'version': '99.0.0'}))
    try:
        with pytest.raises(ValueError, match='newer than this one'): S.restore_backup(os.path.basename(newer), 'Unit')
        with zipfile.ZipFile(newer, 'w') as z: z.writestr('backup.json', '{}')
        with pytest.raises(ValueError, match='no plants.db'): S.restore_backup(os.path.basename(newer), 'Unit')
    finally: os.remove(newer)

def test_old_automatic_backups_are_pruned_and_manual_ones_kept():
    made = []
    for i in range(3):
        n = os.path.join(S.BACKUP_DIR, f'plantdb-backup-2001010{i + 1}-000000-auto.zip')
        with zipfile.ZipFile(n, 'w') as z: z.writestr('backup.json', '{}')
        made.append(n)
    keep_auto = sum(1 for b in S.bk_list() if b['kind'] == 'auto') - 2
    manual = [b['file'] for b in S.bk_list() if b['kind'] == 'manual']
    try:
        removed = S.prune_backups(keep_auto)
        assert sorted(removed) == sorted(os.path.basename(m) for m in made[:2]), 'the two oldest automatic backups go'
        assert [b['file'] for b in S.bk_list() if b['kind'] == 'manual'] == manual
    finally:
        for m in made:
            if os.path.exists(m): os.remove(m)

def test_backup_due_daily_waits_for_the_hour():
    c = conn()
    try:
        tz = ZoneInfo(S.location(c)['tz'])
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('backup_settings',?)", (json.dumps({'enabled': True, 'freq': 'daily', 'hour': 3}),))
        last = datetime(2026, 11, 10, 3, 5, tzinfo=tz).astimezone(timezone.utc)
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('backup_last_auto',?)", (last.strftime('%Y-%m-%dT%H:%M:%SZ'),))
        at = lambda d, h: datetime(2026, 11, d, h, 0, tzinfo=tz).astimezone(timezone.utc)
        assert not S.backup_due(c, at(10, 23)), 'the same day: not yet'
        assert not S.backup_due(c, at(11, 2)), 'the next day, before 3 am: not yet'
        assert S.backup_due(c, at(11, 3)), 'the next day at 3 am: due'
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES('backup_settings',?)", (json.dumps({'enabled': False}),))
        assert not S.backup_due(c, at(12, 3)), 'turned off: never due'
    finally: c.rollback(); c.close()

# ---------------------------------------------------------------- watering
def test_water_base_days_follow_the_soil_moisture_range():
    r = lambda every=None, lo=None: {'water_every_days': every, 'soil_moisture_low': lo}
    assert S.water_base_days(r(every=9)) == (9, 'set on this page')
    assert S.water_base_days(r())[0] == 7
    assert [S.water_base_days(r(lo=x))[0] for x in (5, 15, 25, 35, 60)] == [14, 10, 7, 5, 4]

def test_water_factor_by_weather_and_indoors():
    assert S.water_factor(100, True)[0] == 1.5, 'indoors wins over the weather'
    assert [S.water_factor(h, False)[0] for h in (None, 98, 88, 75, 60, 40)] == [1.0, .6, .8, 1.0, 1.3, 1.6]

def test_water_report_counts_from_the_last_watering_and_a_check():
    c = conn()
    try:
        today = S.local_today(c)
        code = c.execute("SELECT code FROM plants WHERE status='active' ORDER BY code LIMIT 1").fetchone()[0]
        c.execute("UPDATE plants SET site='Indoors', home_id=NULL WHERE code=?", (code,))
        r = c.execute('SELECT * FROM plants WHERE code=?', (code,)).fetchone()
        if S.grow_kind(r) != 'Soil mix': pytest.skip('the first plant does not grow in soil mix')
        c.execute('DELETE FROM care_log WHERE plant_code=?', (code,))
        st = next(p for p in S.water_report(c, [code])['plants'] if p['code'] == code)
        assert st['state'] == 'unknown' and st['next'] is None, 'never watered: nothing to count from'
        every = st['every']
        c.execute("INSERT INTO care_log(plant_code,kind,done_on,created_by,created_at) VALUES(?,?,?,'Unit','2026-01-01T00:00:00Z')", (code, 'water', (today - timedelta(days=every)).isoformat()))
        st = next(p for p in S.water_report(c, [code])['plants'] if p['code'] == code)
        assert st['state'] == 'due' and st['overdue'] == 0
        c.execute("INSERT INTO care_log(plant_code,kind,done_on,created_by,created_at) VALUES(?,?,?,'Unit','2026-01-01T00:00:00Z')", (code, 'check', today.isoformat()))
        st = next(p for p in S.water_report(c, [code])['plants'] if p['code'] == code)
        assert st['state'] == 'ok' and st['next'] > today.isoformat(), 'checked today and still moist: look again later'
    finally: c.rollback(); c.close()

# ---------------------------------------------------------------- frost
def test_frost_report_levels_a_plant_by_the_forecast_low():
    c = conn()
    try:
        L = S.location(c); today = S.local_today(c)
        c.execute("UPDATE plants SET temp_damage_below=NULL")
        code = c.execute("SELECT code FROM plants WHERE status='active' ORDER BY code LIMIT 1").fetchone()[0]
        c.execute("UPDATE plants SET temp_damage_below=40, temp_lethal_below=30, site='Outdoors', home_id=NULL WHERE code=?", (code,))
        days = [{'date': (today + timedelta(days=i)).isoformat(), 'low': low, 'high': 60} for i, low in enumerate((50, 42, 35, 25))]
        c.execute('UPDATE locations SET forecast=? WHERE id=?', (json.dumps({'days': days, 'fetched_at': 'now'}), L['id']))
        rep = S.frost_report(c)
        assert [n['level'] for n in rep['nights']] == [None, 'watch', 'damage', 'danger']
        assert rep['level'] == 'danger' and rep['worst']['low'] == 25 and rep['first']['low'] == 42
        p = rep['plants'][0]
        assert p['code'] == code and p['next']['level'] == 'watch' and p['worst']['level'] == 'danger'
        c.execute("UPDATE plants SET site='Indoors' WHERE code=?", (code,))
        assert S.frost_report(c)['level'] is None, 'indoors: no warning'
    finally: c.rollback(); c.close()

# ---------------------------------------------------------------- weather sums and dates
def test_vpd_and_timestamps():
    assert S.vpd_kpa(None, 50) is None
    assert S.vpd_kpa(77, 50) == pytest.approx(1.58, abs=.02)
    assert S.vpd_kpa(77, 100) == 0
    assert S.parse_ts('2026-11-11T06:00:00Z') == datetime(2026, 11, 11, 6, tzinfo=timezone.utc)
    assert S.parse_ts('2026-11-11T00:00:00-06:00') == datetime(2026, 11, 11, 6, tzinfo=timezone.utc)
    assert S.parse_ts('2026-11-11 06:00:00').tzinfo is not None, 'no zone means UTC'

def test_daily_light_adds_up_todays_readings_only():
    tz = ZoneInfo('America/Chicago')
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if (now - start).total_seconds() < 3 * 3600: pytest.skip('too close to midnight for three hours of readings')
    ts = lambda t: t.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    rows = [{'ts': ts(start - timedelta(hours=2)), 'par': 999}, {'ts': ts(start + timedelta(minutes=10)), 'par': 500},
            {'ts': ts(start + timedelta(minutes=40)), 'par': 500}, {'ts': ts(start + timedelta(hours=2)), 'par': None}]
    # 500 for 30 minutes, then 500 for an hour at most (the gap to the next reading is capped at one hour)
    assert S.integrate_dli(rows, tz) == round(500 * 1800 / 1e6 + 500 * 3600 / 1e6, 1)
    assert S.integrate_dli([], tz) is None

def test_today_is_the_places_day_not_utcs():
    c = conn()
    try:
        tz = ZoneInfo(S.location(c)['tz'])
        assert S.local_today(c) == datetime.now(tz).date()
    finally: c.close()

# ---------------------------------------------------------------- the saving mode
def test_wal_probe_leaves_nothing_behind():
    assert S.wal_works() in (True, False)
    folder = os.path.dirname(S.DB_PATH)
    assert not [f for f in os.listdir(folder) if f.startswith('.wal-probe')], 'the scratch database is removed'
    assert S.JOURNAL['probe']
