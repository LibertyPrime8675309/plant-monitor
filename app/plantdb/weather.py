"""Weather, sensors and current conditions: Open-Meteo, the readings, the tables. 1.57.0: places, past days and problems moved to
places.py, pastdays.py and problems.py. Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- weather, sensors and current conditions
DEFAULT_LOC = {'name': 'Round Rock, TX', 'lat': 30.5083, 'lon': -97.6789, 'tz': 'America/Chicago'}
LUX_PER_PAR = 54.0          # sunlight: about 54 lux per umol/m2/s. A rough conversion; grow lights differ.
PAR_PER_WM2 = 2.1           # sunlight: global radiation (W/m2) to PAR (umol/m2/s), about 2.1
METRICS = ('temp_f', 'humidity', 'par', 'lux', 'soil_moisture', 'soil_temp_f', 'soil_ph', 'weight_g', 'soil_raw')     # 1.35.0: weight_g; 1.36.0: soil_raw (probe volts)
LIMITS = {'temp_f': (-60, 160), 'humidity': (0, 100), 'par': (0, 4000), 'lux': (0, 200000),
          'soil_moisture': (0, 100), 'soil_temp_f': (-40, 160), 'soil_ph': (0, 14), 'weight_g': (0, 200000), 'soil_raw': (0, 10)}

WX_CORE = ['temperature_2m', 'relative_humidity_2m', 'shortwave_radiation']
WX_HOURLY_GROUPS = [
    ('Air', ['temperature_2m', 'relative_humidity_2m', 'dew_point_2m', 'apparent_temperature', 'wet_bulb_temperature_2m', 'vapour_pressure_deficit',
             'temperature_80m', 'temperature_120m', 'temperature_180m']),
    ('Rain and snow', ['precipitation', 'rain', 'showers', 'snowfall', 'snow_depth', 'precipitation_probability']),
    ('Sky', ['weather_code', 'cloud_cover', 'cloud_cover_low', 'cloud_cover_mid', 'cloud_cover_high', 'visibility', 'is_day', 'sunshine_duration']),
    ('Sunlight', ['shortwave_radiation', 'direct_radiation', 'diffuse_radiation', 'direct_normal_irradiance', 'terrestrial_radiation', 'uv_index', 'uv_index_clear_sky']),
    ('Wind', ['wind_speed_10m', 'wind_speed_80m', 'wind_speed_120m', 'wind_speed_180m', 'wind_direction_10m', 'wind_direction_80m', 'wind_direction_120m',
              'wind_direction_180m', 'wind_gusts_10m']),
    ('Pressure and water loss', ['pressure_msl', 'surface_pressure', 'evapotranspiration', 'et0_fao_evapotranspiration']),
    ('Ground', ['soil_temperature_0cm', 'soil_temperature_6cm', 'soil_temperature_18cm', 'soil_temperature_54cm', 'soil_moisture_0_to_1cm',
                'soil_moisture_1_to_3cm', 'soil_moisture_3_to_9cm', 'soil_moisture_9_to_27cm', 'soil_moisture_27_to_81cm']),
    ('Upper atmosphere', ['total_column_integrated_water_vapour', 'freezing_level_height', 'cape', 'lifted_index', 'convective_inhibition', 'boundary_layer_height']),
]
WX_HOURLY = list(dict.fromkeys(v for _, vs in WX_HOURLY_GROUPS for v in vs))
WX_DAILY_GROUPS = [
    ('Temperature', ['temperature_2m_max', 'temperature_2m_min', 'temperature_2m_mean', 'apparent_temperature_max', 'apparent_temperature_min', 'apparent_temperature_mean',
                     'dew_point_2m_max', 'dew_point_2m_min', 'dew_point_2m_mean', 'wet_bulb_temperature_2m_max', 'wet_bulb_temperature_2m_min', 'wet_bulb_temperature_2m_mean']),
    ('Humidity', ['relative_humidity_2m_max', 'relative_humidity_2m_min', 'relative_humidity_2m_mean', 'vapour_pressure_deficit_max']),
    ('Sun', ['sunrise', 'sunset', 'daylight_duration', 'sunshine_duration', 'uv_index_max', 'uv_index_clear_sky_max', 'shortwave_radiation_sum',
             'cloud_cover_max', 'cloud_cover_min', 'cloud_cover_mean']),
    ('Rain and snow', ['weather_code', 'precipitation_sum', 'rain_sum', 'showers_sum', 'snowfall_sum', 'snowfall_water_equivalent_sum', 'precipitation_hours',
                       'precipitation_probability_max', 'precipitation_probability_min', 'precipitation_probability_mean']),
    ('Wind', ['wind_speed_10m_max', 'wind_speed_10m_min', 'wind_speed_10m_mean', 'wind_gusts_10m_max', 'wind_gusts_10m_min', 'wind_gusts_10m_mean', 'wind_direction_10m_dominant']),
    ('Pressure and water loss', ['pressure_msl_max', 'pressure_msl_min', 'pressure_msl_mean', 'surface_pressure_max', 'surface_pressure_min', 'surface_pressure_mean',
                                 'et0_fao_evapotranspiration', 'growing_degree_days_base_0_limit_50', 'leaf_wetness_probability_mean']),
    ('Other', ['visibility_max', 'visibility_min', 'visibility_mean', 'cape_max', 'cape_min', 'cape_mean']),
]
WX_DAILY = list(dict.fromkeys(v for _, vs in WX_DAILY_GROUPS for v in vs))
WX_GROUP_OF = {}
for _g, _vs in WX_HOURLY_GROUPS + WX_DAILY_GROUPS:
    for _v in _vs: WX_GROUP_OF.setdefault(_v, _g)
WX_LABELS = {'temperature_2m': 'Temperature', 'relative_humidity_2m': 'Humidity', 'shortwave_radiation': 'Solar radiation', 'dew_point_2m': 'Dew point',
             'apparent_temperature': 'Feels-like temperature', 'vapour_pressure_deficit': 'Air dryness (VPD)', 'precipitation': 'Precipitation',
             'precipitation_probability': 'Chance of precipitation', 'weather_code': 'Weather code', 'cloud_cover': 'Cloud cover',
             'sunshine_duration': 'Sunshine', 'uv_index': 'UV index', 'wind_speed_10m': 'Wind speed (10 m)', 'wind_gusts_10m': 'Wind gusts (10 m)',
             'wind_direction_10m': 'Wind direction (10 m)', 'pressure_msl': 'Pressure at sea level', 'surface_pressure': 'Pressure at the ground',
             'et0_fao_evapotranspiration': 'Water loss, reference crop (ET0)', 'evapotranspiration': 'Water loss, actual',
             'direct_normal_irradiance': 'Direct sun, facing the sun', 'cape': 'CAPE (storm energy)', 'snow_depth': 'Snow depth'}
WX_SUM = ('precipitation', 'rain', 'showers', 'snowfall', 'evapotranspiration', 'et0_fao_evapotranspiration', 'sunshine_duration')
WX_MAX = ('wind_gusts_10m', 'uv_index', 'precipitation_probability')
WX_SUFFIX = {'_max': 'highest', '_min': 'lowest', '_mean': 'average', '_sum': 'total', '_dominant': 'most common'}
def wx_label(v):
    if v in WX_LABELS: return WX_LABELS[v]
    for suf, word in WX_SUFFIX.items():
        if v.endswith(suf) and len(v) > len(suf) + 3:
            return f'{wx_label(v[:-len(suf)])}, {word}'
    s = v.replace('_', ' ').replace(' 2m', '').replace(' 10m', ' (10 m)').replace(' msl', ' at sea level')
    s = re.sub(r' (\d+)m$', r' at \1 m', s)
    s = re.sub(r' (\d+) to (\d+)cm$', r' \1 to \2 cm deep', s)
    s = re.sub(r' (\d+)cm$', r' at \1 cm deep', s)
    return s[:1].upper() + s[1:]
def wx_agg(v): return 'sum' if v in WX_SUM else 'max' if v in WX_MAX else 'avg'

WX_LOCK = threading.Lock()
WX_JOB = {'running': False}

def om_url(loc, kind, names, api, start=None, end=None, past_days=3, forecast_days=7):
    q = {'latitude': loc['lat'], 'longitude': loc['lon'], kind: ','.join(names), 'temperature_unit': 'fahrenheit', 'wind_speed_unit': 'mph',
         'precipitation_unit': 'inch', 'timeformat': 'unixtime', 'timezone': loc['tz']}
    if api == 'archive':
        q.update(start_date=start, end_date=end)
        return 'https://archive-api.open-meteo.com/v1/archive?' + urllib.parse.urlencode(q)
    q.update(past_days=past_days, forecast_days=forecast_days)
    return 'https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode(q)

def unsupported_get(c, api, kind):
    try: d = json.loads(setting(c, 'wx_unsupported', '{}') or '{}')
    except ValueError: d = {}
    if time.time() - d.get('_at', 0) > 14 * 86400: return set()        # try again every two weeks in case the service added them
    return set(d.get(f'{api}:{kind}', []))

def unsupported_add(c, api, kind, names):
    try: d = json.loads(setting(c, 'wx_unsupported', '{}') or '{}')
    except ValueError: d = {}
    if time.time() - d.get('_at', 0) > 14 * 86400: d = {'_at': int(time.time())}
    d.setdefault('_at', int(time.time()))
    d[f'{api}:{kind}'] = sorted(set(d.get(f'{api}:{kind}', [])) | set(names))
    set_setting(c, 'wx_unsupported', json.dumps(d))

def om_collect(c, loc, api, kind, names, **rng):
    """Ask for the variables in small groups. Returns ({unix: {variable: value}}, {variable: unit}, [variables not available])."""
    skip = unsupported_get(c, api, kind)
    want = [n for n in names if n not in skip]
    merged, units, missing = {}, {}, [n for n in names if n in skip]
    def take(data):
        blk = data.get(kind) or {}
        for i, t in enumerate(blk.get('time') or []):
            slot = merged.setdefault(int(t), {})
            for k, arr in blk.items():
                if k != 'time' and i < len(arr) and arr[i] is not None: slot[k] = arr[i]
        for k, u in (data.get(kind + '_units') or {}).items():
            if k != 'time': units[k] = u
    def ask(vs):
        WX_JOB['beat'] = time.time()                       # heartbeat for the progress display
        if WX_JOB.get('running'): WX_JOB['step'] = ('hourly' if kind == 'hourly' else 'daily') + ' values'
        try: return http_json(om_url(loc, kind, vs, api, **rng))
        except OMError as e:
            if e.code == 400: return e
            raise
    for i in range(0, len(want), 12):
        grp = want[i:i + 12]
        d = ask(grp)
        if not isinstance(d, OMError): take(d); time.sleep(0.2); continue
        for v in grp:                                   # something in this group is not offered: find out which
            d1 = ask([v])
            if isinstance(d1, OMError):
                if v not in d1.reason:                  # the complaint is not about this variable (bad dates, say): stop, do not blame it
                    raise d1
                missing.append(v); unsupported_add(c, api, kind, [v])
                if v in WX_CORE and kind == 'hourly': raise OMError(400, f'{v} is not available')
            else: take(d1)
            time.sleep(0.2)
    return merged, units, missing

def detail_years(c):
    try: return max(0, min(int(setting(c, 'wx_detail_years', '3')), 90))
    except (TypeError, ValueError): return 3
def rng_count(c, lo, hi, dev): return c.execute("SELECT COUNT(*) FROM readings WHERE source='weather' AND device=? AND ts>=? AND ts<=?", (dev, lo, hi)).fetchone()[0]
def wx_count(c, dev): return c.execute("SELECT COUNT(*) FROM readings WHERE source='weather' AND device=?", (dev,)).fetchone()[0]
def wxd_count(c, lid): return c.execute('SELECT COUNT(*) FROM weather_daily WHERE loc_id=?', (lid,)).fetchone()[0]

def store_hourly(c, merged, upto, dev='open-meteo'):
    n = 0
    for t in sorted(merged):
        if t > upto: continue
        d = merged[t]
        tmp, rh, sw = d.get('temperature_2m'), d.get('relative_humidity_2m'), d.get('shortwave_radiation')
        extra = {k: v for k, v in d.items() if k not in ('temperature_2m', 'relative_humidity_2m')}
        if tmp is None and rh is None and not extra: continue
        par = None if sw is None else round(sw * PAR_PER_WM2, 1)
        c.execute("""INSERT INTO readings(ts,source,device,temp_f,humidity,par,extra) VALUES(?,?,?,?,?,?,?)
                     ON CONFLICT(source,device,ts) DO UPDATE SET temp_f=COALESCE(excluded.temp_f,readings.temp_f), humidity=COALESCE(excluded.humidity,readings.humidity),
                       par=COALESCE(excluded.par,readings.par), extra=json_patch(COALESCE(readings.extra,'{}'),COALESCE(excluded.extra,'{}'))""",
                  (iso(t), 'weather', dev, tmp, rh, par, json.dumps(extra) if extra else None))
        n += 1
    return n

def store_daily(c, merged, tz, lid=1):
    n, today = 0, datetime.now(tz).date().isoformat()
    for t in sorted(merged):
        day = datetime.fromtimestamp(t, tz).date().isoformat()
        c.execute("""INSERT INTO weather_daily(loc_id,date,data,kind,updated_at) VALUES(?,?,?,?,?)
                     ON CONFLICT(loc_id,date) DO UPDATE SET data=json_patch(COALESCE(weather_daily.data,'{}'),excluded.data),
                       kind=excluded.kind, updated_at=excluded.updated_at""",
                  (lid, day, json.dumps(merged[t]), 'forecast' if day >= today else 'observed', now()))
        n += 1
    return n

def merge_units(c, units):
    if not units: return
    try: u = json.loads(setting(c, 'wx_units', '{}') or '{}')
    except ValueError: u = {}
    u.update(units); set_setting(c, 'wx_units', json.dumps(u))

def daily_forecast(rows, upto, tz):
    days = {}
    for t, tmp, rh, par in rows:
        if t <= upto or tmp is None: continue
        d = datetime.fromtimestamp(t, tz).date().isoformat()
        x = days.setdefault(d, {'date': d, 'temps': [], 'rh': [], 'par': 0.0})
        x['temps'].append(tmp)
        if rh is not None: x['rh'].append(rh)
        if par is not None: x['par'] += par * 3600 / 1e6
    out = []
    for d in sorted(days):
        x = days[d]
        out.append({'date': d, 'low': round(min(x['temps'])), 'high': round(max(x['temps'])),
                    'rh': round(sum(x['rh']) / len(x['rh'])) if x['rh'] else None, 'dli': round(x['par'], 1), 'hours': len(x['temps'])})
    return out

def log_run(c, trigger, kind, api, start, end, hourly_rows, hourly_new, daily_days, daily_new, vars_ok, vars_missing, ok, error, secs, note='', loc_id=1):
    c.execute('INSERT INTO weather_runs(ran_at,trigger,kind,api,range_start,range_end,hourly_rows,hourly_new,daily_days,daily_new,vars_ok,vars_missing,ok,error,seconds,note,loc_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (now(), trigger, kind, api, start, end, hourly_rows, hourly_new, daily_days, daily_new, vars_ok, json.dumps(vars_missing), 1 if ok else 0, error, round(secs, 1), note, loc_id))
    c.commit()

def year_chunks(start, end):
    a, out = datetime.strptime(start, '%Y-%m-%d').date(), []
    z = datetime.strptime(end, '%Y-%m-%d').date()
    while a <= z:
        b = min(datetime(a.year + 1, a.month, a.day).date() - timedelta(days=1) if not (a.month == 2 and a.day == 29) else datetime(a.year + 1, 2, 28).date(), z)
        out.append((a.isoformat(), b.isoformat())); a = b + timedelta(days=1)
    return out

def run_weather(trigger, backfill_start=None, progress=None, conn=None, loc_id=None):
    """One update. trigger: auto, auto-first, update-now or load-history. Logs what it fetched; never raises."""
    own = conn is None
    c = conn or sqlite3.connect(DB_PATH, timeout=30)
    c.row_factory = sqlite3.Row
    loc, ts_now = loc_get(c, loc_id) or location(c), int(time.time())
    tz, dev, lid = tzinfo(loc['tz']), loc['device'], loc['id']
    status = {'at': now(), 'ok': False, 'error': '', 'stored': 0}
    logged = {'history': False}
    prog = progress or (lambda *a, **k: None)
    try:
        with WX_LOCK:
            first = not c.execute("SELECT 1 FROM readings WHERE source='weather' AND device=? LIMIT 1", (dev,)).fetchone()
            total = 0
            if backfill_start:
                t0, end = time.time(), (datetime.now(timezone.utc) - timedelta(days=6)).date().isoformat()
                chunks = year_chunks(backfill_start, end) if backfill_start <= end else []
                h_rows = h_new = d_days = d_new = skipped = 0; ok_vars, miss, err = set(), set(), ''
                cutoff = (datetime.now(timezone.utc) - timedelta(days=365 * detail_years(c))).date().isoformat()
                for i, (a, b) in enumerate(chunks):
                    prog(i, len(chunks), f'{a} to {b}', hourly_saved=h_rows, daily_saved=d_days, skipped=skipped, phase='history')
                    detail = b >= cutoff                       # recent years keep every hourly measurement; older years keep the basics hourly and everything daily
                    days = (datetime.strptime(b, '%Y-%m-%d') - datetime.strptime(a, '%Y-%m-%d')).days + 1
                    lo, hi = iso(datetime.strptime(a, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() - 86400), iso(datetime.strptime(b, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() + 2 * 86400)
                    have = c.execute("SELECT COUNT(*) FROM readings WHERE source='weather' AND device=? AND ts>=? AND ts<=?" + (" AND extra IS NOT NULL" if detail else ""), (dev, lo, hi)).fetchone()[0]
                    dhave = c.execute('SELECT COUNT(*) FROM weather_daily WHERE loc_id=? AND date>=? AND date<=?', (lid, a, b)).fetchone()[0]
                    need_h, need_d = not (have > 0 and have >= days * 24 - 24), dhave < days - 1
                    if not need_h and not need_d:
                        skipped += 1; continue                    # this period already holds everything it should
                    try:
                        before, dbefore = rng_count(c, lo, hi, dev), wxd_count(c, lid)
                        if need_h:
                            m, u, ms = om_collect(c, loc, 'archive', 'hourly', WX_HOURLY if detail else WX_CORE, start=a, end=b)
                            merge_units(c, u); h_rows += store_hourly(c, m, ts_now, dev); ok_vars |= {k for d in m.values() for k in d}; miss |= set(ms)
                        if need_d:
                            m, u, ms = om_collect(c, loc, 'archive', 'daily', WX_DAILY, start=a, end=b)
                            merge_units(c, u); d_days += store_daily(c, m, tz, lid); miss |= {x + ' (daily)' for x in ms}
                        h_new += rng_count(c, lo, hi, dev) - before; d_new += wxd_count(c, lid) - dbefore
                        ds0 = loc_get(c, lid)['detail_since']
                        if detail and (not ds0 or a < ds0): loc_set(c, lid, detail_since=a)
                        c.commit()
                    except OMError as e:
                        err = f'Open-Meteo said no ({e}). ' + ('You have used up the free limit for now; press Load history again later and it carries on where it stopped.' if e.code == 429 else '')
                        break
                    except Exception as e:
                        err = (f'Could not reach Open-Meteo after 5 tries over about 3 minutes ({type(e).__name__}: {e}). '
                               'Everything fetched before this was saved; press Load history again to carry on from here.')[:400]; break
                prog(len(chunks), len(chunks), 'the last 3 months and the forecast', hourly_saved=h_rows, daily_saved=d_days, skipped=skipped, phase='recent')
                total += h_rows
                log_run(c, trigger, 'history', 'archive', backfill_start, end, h_rows, h_new, d_days, d_new, len(ok_vars), sorted(miss), not err, err, time.time() - t0,
                        f'{skipped} of {len(chunks)} year-long periods already held every measurement and were skipped.' if skipped else '', loc_id=lid)
                logged['history'] = bool(err)
                if err: raise RuntimeError(err)
            t0 = time.time()
            past = 92 if (first or backfill_start) else 3
            before, dbefore = wx_count(c, dev), wxd_count(c, lid)
            m, u, ms = om_collect(c, loc, 'forecast', 'hourly', WX_HOURLY, past_days=past, forecast_days=7)
            merge_units(c, u)
            rows = [(t, d.get('temperature_2m'), d.get('relative_humidity_2m'), None if d.get('shortwave_radiation') is None else round(d['shortwave_radiation'] * PAR_PER_WM2, 1)) for t, d in sorted(m.items())]
            n = store_hourly(c, m, ts_now, dev); total += n
            md, ud, msd = om_collect(c, loc, 'forecast', 'daily', WX_DAILY, past_days=past, forecast_days=7)
            merge_units(c, ud); dn = store_daily(c, md, tz, lid)
            loc_set(c, lid, forecast=json.dumps({'fetched_at': now(), 'days': daily_forecast(rows, ts_now, tz)}))
            ts_list = [t for t in m if t <= ts_now]
            if ts_list:
                d0 = datetime.fromtimestamp(min(ts_list), tz).date().isoformat()
                ds0 = loc_get(c, lid)['detail_since']
                if not ds0 or d0 < ds0: loc_set(c, lid, detail_since=d0)
            log_run(c, 'auto-first' if (first and trigger == 'auto') else trigger, 'recent', 'forecast',
                    datetime.fromtimestamp(min(ts_list), tz).date().isoformat() if ts_list else None, datetime.fromtimestamp(max(m), tz).date().isoformat() if m else None,
                    n, wx_count(c, dev) - before, dn, wxd_count(c, lid) - dbefore, len({k for d in m.values() for k in d}), sorted(set(ms) | {x + ' (daily)' for x in msd}), True, '', time.time() - t0, loc_id=lid)
            status.update(ok=True, stored=total)
    except Exception as e:                       # offline, blocked, API change: record it and carry on
        status['error'] = (str(e) if isinstance(e, RuntimeError) else f'{type(e).__name__}: {e}')[:400]
        if isinstance(e, (urllib.error.URLError, TimeoutError, OSError)) and not isinstance(e, OMError):
            status['error'] = ('Could not reach Open-Meteo after 5 tries over about 3 minutes. Check that this computer is online. Details: ' + status['error'])[:400]
        if not logged['history']:
            try: log_run(c, trigger, 'recent', 'forecast', None, None, 0, 0, 0, 0, 0, [], False, status['error'], 0, loc_id=lid)
            except Exception: pass
        problem('weather', f"The weather for {loc['name']} could not be updated", status['error'], c)
    status['place'] = loc['name']
    set_setting(c, 'weather_status', json.dumps(status))
    loc_set(c, lid, status=json.dumps(status))
    c.commit()
    WX_STATS.clear()
    if own: c.close()
    return status

def start_job(trigger, backfill_start=None, places=None):
    """places: list of (id, name). Several places are updated one after another."""
    if WX_JOB.get('running'): return False
    places = places or [(1, '')]
    WX_JOB.clear(); WX_JOB.update(running=True, trigger=trigger, started=now(), started_ts=time.time(), beat=time.time(), done=0, total=0, label='starting',
                                  start=backfill_start, hourly_saved=0, daily_saved=0, skipped=0, phase='history' if backfill_start else 'recent',
                                  place=places[0][1], place_id=places[0][0], places_total=len(places), place_no=1)
    def work():
        jid = job_start('weather', 'the weather history' if backfill_start else 'now', len(places))
        def prog(i, n, label, **kw): WX_JOB.update(done=i, total=n, label=label, beat=time.time(), **kw); job_progress(jid, label=f"{WX_JOB.get('place', '')}: {label}")
        errs = []
        for k, (pid, pname) in enumerate(places):
            WX_JOB.update(place=pname, place_id=pid, place_no=k + 1, done=0, total=0, hourly_saved=0, daily_saved=0, skipped=0)
            job_progress(jid, k, len(places), pname)
            st = run_weather(trigger, backfill_start, prog, loc_id=pid)
            if not st['ok']: errs.append((pname + ': ' if len(places) > 1 else '') + st['error'])
        WX_JOB.update(running=False, finished=now(), ok=not errs, error=' | '.join(errs)[:600])
        job_end(jid, not errs, ' | '.join(errs)[:300] if errs else f'{len(places)} place{"s" if len(places) != 1 else ""} updated')
    threading.Thread(target=work, daemon=True).start()
    return True

def weather_loop():
    time.sleep(8)
    while True:
        try:
            c = sqlite3.connect(DB_PATH, timeout=30)
            try:
                c.row_factory = sqlite3.Row
                rows = c.execute('SELECT id, name FROM locations WHERE enabled=1 ORDER BY is_home DESC, id').fetchall()
                jid = job_start('weather', 'hourly', len(rows)); bad = []
                for i, r in enumerate(rows):
                    if WX_JOB.get('running'): job_end(jid, True, 'skipped: an update was running'); jid = None; break   # a manual update or history load is busy; the next hour catches up
                    job_progress(jid, i, len(rows), r['name'])
                    st = run_weather('auto', conn=c, loc_id=r['id'])
                    if not st.get('ok'): bad.append(r['name'])
                if jid: job_end(jid, not bad, ('could not update ' + ', '.join(bad)) if bad else f'{len(rows)} place{"s" if len(rows) != 1 else ""} updated')
                set_setting(c, 'weather_last_auto', now()); c.commit()
            finally: c.close()
        except Exception as e: problem_exc('weather', e, 'The hourly weather update failed')
        time.sleep(3600)


def clean_reading(d, device_default='sensor'):
    """Validate one posted reading. Returns a dict ready to insert."""
    if not isinstance(d, dict): abort(400, 'each reading must be an object')
    out = {'device': re.sub(r'[^\w .\-@]', '', str(d.get('device') or device_default))[:40] or device_default}
    try: ts = parse_ts(d['ts']) if d.get('ts') else datetime.now(timezone.utc)
    except (ValueError, TypeError): abort(400, 'ts must look like 2026-10-19T18:30:00Z')
    if ts > datetime.now(timezone.utc) + timedelta(minutes=10): abort(400, 'ts is in the future')
    out['ts'] = ts.strftime('%Y-%m-%dT%H:%M:%SZ')
    conv = dict(d)
    if conv.get('temp_f') is None and conv.get('temp_c') is not None:
        try: conv['temp_f'] = float(conv['temp_c']) * 1.8 + 32
        except (TypeError, ValueError): abort(400, 'temp_c must be a number')
    if conv.get('soil_temp_f') is None and conv.get('soil_temp_c') is not None:
        try: conv['soil_temp_f'] = float(conv['soil_temp_c']) * 1.8 + 32
        except (TypeError, ValueError): abort(400, 'soil_temp_c must be a number')
    got = False
    for m in METRICS:
        v = conv.get(m)
        if v in (None, ''): out[m] = None; continue
        try: x = round(float(v), 2)
        except (TypeError, ValueError): abort(400, f'{m} must be a number')
        lo, hi = LIMITS[m]
        if not lo <= x <= hi: abort(400, f'{m} must be between {lo} and {hi}')
        out[m] = x; got = True
    if out['par'] is None and out['lux'] is not None: out['par'] = round(out['lux'] / LUX_PER_PAR, 1)
    if not got: abort(400, 'a reading needs at least one of: ' + ', '.join(METRICS))
    out['note'] = str(d.get('note') or '')[:200]
    return out

def insert_reading(c, source, r):
    c.execute('INSERT OR REPLACE INTO readings(ts,source,device,temp_f,humidity,par,lux,soil_moisture,soil_temp_f,soil_ph,weight_g,soil_raw,note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
              (r['ts'], source, r['device'], r['temp_f'], r['humidity'], r['par'], r['lux'], r['soil_moisture'], r['soil_temp_f'], r['soil_ph'], r.get('weight_g'), r.get('soil_raw'), r.get('note')))

@app.route('/api/readings', methods=['POST'])
def post_readings():
    """Sensor ingest. Auth is the X-Ingest-Token header (checked in guard())."""
    c = db()
    body = request.get_json(silent=True)
    items = body.get('readings') if isinstance(body, dict) and 'readings' in body else (body if isinstance(body, list) else [body])
    if not items or items == [None]: abort(400, 'send a JSON reading or a list of readings')
    if len(items) > 500: abort(400, 'at most 500 readings per request')
    rows = [clean_reading(d) for d in items]
    for r in rows: insert_reading(c, 'sensor', r)
    try: sensor_after_readings(c, rows)          # 1.35.0: a jump in soil moisture logs a watering
    except Exception as e: problem_exc('sensors', e, 'The sensor watering check failed')
    c.commit()
    return jsonify(stored=len(rows)), 201

@app.route('/api/ingest')
def ingest_info():
    c = db()
    return jsonify(token=setting(c, 'ingest_token'), url=request.host_url.rstrip('/') + '/api/readings')

@app.route('/api/ingest/regenerate', methods=['POST'])
def ingest_regen():
    c = db()
    set_setting(c, 'ingest_token', secrets.token_urlsafe(18))
    audit_only(c, 'setting', 'ingest_token', None, None, editor(), 'Sensor token regenerated')
    c.commit()
    return jsonify(token=setting(c, 'ingest_token'))

def ts_filter(days):
    return iso(time.time() - days * 86400)

SERIES_BUCKETS = ('hour', 'day', 'week', 'month')

@app.route('/api/readings/series')
def readings_series():
    """Chart data, worked out by the database. Either days=N (back from now) or from/to (local dates, YYYY-MM-DD).
    vars=a,b,c adds any of the extra Open-Meteo measurements. The time step grows with the period: hours up to 10 days,
    days up to 3 years, weeks up to 15 years, months beyond that (or bucket=... to choose)."""
    c = db()
    source = request.args.get('source', 'weather')
    if source not in ('weather', 'sensor', 'manual', 'all'): abort(400, 'unknown source')
    device = request.args.get('device')
    loc = req_loc(c) if source == 'weather' else location(c); tz = tzinfo(loc['tz'])
    if source == 'weather': device = loc['device']
    fr, to = request.args.get('from'), request.args.get('to')
    if fr or to:
        lo, hi = local_bounds(c, fr, to, loc['tz'])
        if not lo:
            r = c.execute('SELECT MIN(ts) FROM readings' + ('' if source == 'all' else ' WHERE source=?') + (' AND device=?' if device and source != 'all' else ''),
                          ([] if source == 'all' else [source]) + ([device] if device and source != 'all' else [])).fetchone()
            lo = r[0] or iso(time.time() - 86400)
        hi = min(hi or iso(time.time() + 60), iso(time.time() + 60))
    else:
        try: days = max(1, min(int(request.args.get('days', 7)), 40000))
        except ValueError: abort(400, 'days must be a whole number')
        lo, hi = ts_filter(days), iso(time.time() + 60)
    span = (parse_ts(hi) - parse_ts(lo)).total_seconds() / 86400
    bucket = request.args.get('bucket')
    if bucket not in SERIES_BUCKETS:
        bucket = 'hour' if span <= 10 else 'day' if span <= 3 * 366 else 'week' if span <= 15 * 366 else 'month'
    off_h = round(parse_ts(lo).astimezone(tz).utcoffset().total_seconds() / 3600 + parse_ts(hi).astimezone(tz).utcoffset().total_seconds() / 3600) / 2
    off = f"{off_h:+.1f} hours"                      # local day boundaries (an hour out at most around a daylight-saving change)
    key = {'hour': 'substr(ts,1,13)', 'day': f"date(ts,'{off}')", 'week': f"date(ts,'{off}','-6 days','weekday 1')", 'month': f"strftime('%Y-%m-01',ts,'{off}')"}[bucket]
    names = [v for v in (request.args.get('vars') or request.args.get('var') or '').split(',') if v]
    names = list(dict.fromkeys(names))[:400]
    for v in names:
        if not re.match(r'^[a-z0-9_]{2,60}$', v): abort(400, 'unknown measurement')
    inner = ['ts', 'temp_f', 'humidity', 'par', 'lux', 'soil_moisture', 'soil_temp_f', 'soil_ph', 'weight_g', 'soil_raw'] + [f"json_extract(extra,'$.{v}') AS x{i}" for i, v in enumerate(names)]
    sel = ['COUNT(*) AS n', 'AVG(temp_f) AS temp_f', 'MIN(temp_f) AS temp_min', 'MAX(temp_f) AS temp_max'] + \
          [f'AVG({m}) AS {m}' for m in METRICS if m != 'temp_f']
    for i, v in enumerate(names):
        fn = 'AVG' if bucket == 'hour' else {'sum': 'SUM', 'max': 'MAX'}.get(wx_agg(v), 'AVG')
        sel += [f'{fn}(x{i}) AS v{i}', f'COUNT(x{i}) AS n{i}']
    w, args = 'ts>=? AND ts<=?', [lo, hi]
    if source != 'all': w += ' AND source=?'; args.append(source)
    if device: w += ' AND device=?'; args.append(device)
    q = f"SELECT {key} AS k, {', '.join(sel)} FROM (SELECT {', '.join(inner)} FROM readings WHERE {w}) GROUP BY k ORDER BY k"
    rows = c.execute(q, args).fetchall()
    # Older years keep only daily summaries of the extra measurements: use them where there are no hourly values.
    daily = {}
    if names and bucket != 'hour' and source in ('weather', 'all'):
        dkey = {'day': 'date', 'week': "date(date,'-6 days','weekday 1')", 'month': "strftime('%Y-%m-01',date)"}[bucket]
        dlo, dhi = parse_ts(lo).astimezone(tz).date().isoformat(), parse_ts(hi).astimezone(tz).date().isoformat()
        exprs, which = [], []
        for v in names:
            agg = wx_agg(v)
            cand = [v] if v in WX_DAILY else [v + '_sum'] if agg == 'sum' else [v + '_max'] if agg == 'max' else [v + '_mean']
            dk = next((x for x in cand if x in WX_DAILY), None)
            if not dk: continue
            fn = {'sum': 'SUM', 'max': 'MAX'}.get(agg, 'AVG')
            if v in WX_DAILY: fn = 'SUM' if v.endswith('_sum') else 'MAX' if v.endswith('_max') else 'MIN' if v.endswith('_min') else 'AVG'
            exprs.append(f"{fn}(json_extract(data,'$.{dk}'))"); which.append(v)
        if exprs:                                        # one pass over the daily table for every measurement at once
            for r in c.execute(f"SELECT {dkey} AS k, {', '.join(exprs)} FROM weather_daily WHERE loc_id=? AND date>=? AND date<=? AND kind='observed' GROUP BY k", (loc['id'], dlo, dhi)):
                for v, val in zip(which, r[1:]):
                    if val is not None: daily.setdefault(r[0], {})[v] = val
    def t_of(k):
        if bucket == 'hour': return k + ':00:00Z'
        d = datetime.strptime(k, '%Y-%m-%d').replace(hour=12, tzinfo=tz)
        return d.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    pts, seen, used_daily = [], set(), set()
    for r in rows:
        seen.add(r['k'])
        p = {'t': t_of(r['k']), 'n': r['n']}
        for m in ('temp_f', 'temp_min', 'temp_max') + tuple(m for m in METRICS if m != 'temp_f'):
            p[m] = None if r[m] is None else round(r[m], 1)
        if names:
            p['x'] = {}
            for i, v in enumerate(names):
                val = r[f'v{i}'] if r[f'n{i}'] else None
                if val is None and v in daily.get(r['k'], {}): val = daily[r['k']][v]; used_daily.add(v)
                p['x'][v] = None if val is None else round(val, 2)
        pts.append(p)
    for k in sorted(set(daily) - seen):                 # days with daily summaries but no hourly rows at all
        pts.append({'t': t_of(k), 'n': 0, 'x': {v: (None if daily[k].get(v) is None else round(daily[k][v], 2)) for v in names}})
        used_daily |= set(daily[k])
    pts.sort(key=lambda p: p['t'])
    units = wx_units(c)
    meta = {v: {'label': wx_label(v), 'unit': units.get(v, ''), 'agg': wx_agg(v), 'group': WX_GROUP_OF.get(v, 'Other'), 'from_daily': v in used_daily} for v in names}
    devs = [r[0] for r in c.execute('SELECT DISTINCT device FROM readings WHERE source=? ORDER BY device', (source,))] if source not in ('all', 'weather') else []
    return jsonify(bucket=bucket, source=source, points=pts, devices=devs, tz=loc['tz'], vars=meta, start=lo, end=hi, place={'id': loc['id'], 'name': loc['name']} if source == 'weather' else None,
                   # old single-measurement form
                   **({'var': names[0], 'label': meta[names[0]]['label'], 'unit': meta[names[0]]['unit'], 'agg': meta[names[0]]['agg']} if len(names) == 1 else {}))

def integrate_dli(rows, tz):
    """mol/m2 so far today (local), from PAR readings. Each reading counts for the gap to the next one (max 1 hour)."""
    today = datetime.now(tz).date()
    pts = [(parse_ts(r['ts']), r['par']) for r in rows if r['par'] is not None]
    pts = [(t, p) for t, p in pts if t.astimezone(tz).date() == today]
    if not pts: return None
    tot = 0.0
    for i, (t, p) in enumerate(pts):
        nxt = pts[i + 1][0] if i + 1 < len(pts) else t + timedelta(hours=1)
        dt = min((nxt - t).total_seconds(), 3600)
        tot += p * dt / 1e6
    return round(tot, 1)

STALE_MIN = {'manual': 24 * 60, 'sensor': 90, 'weather': 180}
SOURCE_LABEL = {'manual': 'Typed in by you', 'sensor': 'Your sensor', 'weather': 'Online weather (Open-Meteo)'}

def resolve_current(c):
    mode = setting(c, 'current_mode', 'manual')
    if mode not in STALE_MIN: mode = 'manual'
    loc = location(c); tz = tzinfo(loc['tz'])
    out = {'mode': mode, 'label': SOURCE_LABEL[mode] + (f", {loc['name']}" if mode == 'weather' else ''), 'location': loc['name']}
    newest = None
    for m in ('temp_f', 'humidity', 'par', 'lux', 'soil_moisture', 'soil_temp_f', 'soil_ph'):
        if mode == 'weather' and m not in ('temp_f', 'humidity', 'par'):
            out[m] = None; continue                     # online weather never has these; searching for them would read every row
        if mode == 'weather':
            r = c.execute(f"SELECT ts,{m} FROM readings WHERE source='weather' AND device=? AND {m} IS NOT NULL AND ts<=? ORDER BY ts DESC LIMIT 1", (loc['device'], iso(time.time() + 300))).fetchone()
        else:
            r = c.execute(f'SELECT ts,{m} FROM readings WHERE source=? AND {m} IS NOT NULL AND ts<=? ORDER BY ts DESC LIMIT 1', (mode, iso(time.time() + 300))).fetchone()
        out[m] = r[1] if r else None
        if r and (newest is None or r[0] > newest): newest = r[0]
    out['as_of'] = newest
    out['age_minutes'] = int((time.time() - parse_ts(newest).timestamp()) / 60) if newest else None
    out['stale'] = newest is None or out['age_minutes'] > STALE_MIN[mode]
    out['vpd'] = vpd_kpa(out['temp_f'], out['humidity'])
    rows = c.execute('SELECT ts,par FROM readings WHERE source=? AND par IS NOT NULL AND ts>=?' + (' AND device=?' if mode == 'weather' else '') + ' ORDER BY ts',
                     (mode, iso(time.time() - 2 * 86400)) + ((loc['device'],) if mode == 'weather' else ())).fetchall()
    out['dli_today'] = integrate_dli(rows, tz) if mode != 'manual' else None
    return out

@app.route('/api/current', methods=['GET', 'PUT'])
def current():
    c = db()
    if request.method == 'PUT':
        b = request.get_json(silent=True) or {}
        mode = b.get('mode')
        if mode not in STALE_MIN: abort(400, 'mode must be manual, sensor or weather')
        set_setting(c, 'current_mode', mode)
        if mode == 'manual':
            vals = {k: b.get(k) for k in ('temp_f', 'humidity', 'par', 'lux')}
            if any(v not in (None, '') for v in vals.values()):
                r = clean_reading({**vals, 'device': 'typed in'})
                insert_reading(c, 'manual', r)
        c.commit()
    return jsonify(resolve_current(c))

WX_STATS = {}
def wx_stats(c, L=None):
    """Row counts over hundreds of thousands of rows: worked out once every couple of minutes per place, not on every page view."""
    L = L or location(c)
    key = L['device']
    hit = WX_STATS.get(key)
    if hit is None or time.time() - hit[0] > 120:
        hit = (time.time(), (tuple(c.execute("SELECT MIN(ts), MAX(ts), COUNT(*) FROM readings WHERE source='weather' AND device=?", (key,)).fetchone()),
                             tuple(c.execute("SELECT MIN(ts), MAX(ts), COUNT(*), COUNT(DISTINCT device) FROM readings WHERE source='sensor'").fetchone()),
                             tuple(c.execute('SELECT MIN(date), MAX(date), COUNT(*) FROM weather_daily WHERE loc_id=?', (L['id'],)).fetchone())))
        WX_STATS[key] = hit
    return hit[1]

def run_dict(r):
    d = dict(r)
    try: d['vars_missing'] = json.loads(d.get('vars_missing') or '[]')
    except ValueError: d['vars_missing'] = []
    d['ok'] = bool(d['ok'])
    return d

@app.route('/api/weather')
def weather_info():
    c = db()
    L = req_loc(c)
    fc, st = loc_json(c, L['id'], 'forecast'), loc_json(c, L['id'], 'status')
    first, sens, dd = wx_stats(c, L)
    q = lambda w: c.execute(f"SELECT * FROM weather_runs WHERE loc_id=? AND {w} ORDER BY id DESC LIMIT 1", (L['id'],)).fetchone()
    last_hist, last_ok_hist = q("kind='history'"), q("kind='history' AND ok=1 AND hourly_rows>0")
    last_auto, last_any = q("trigger IN ('auto','auto-first')"), q("kind!='earlier'")
    earlier = c.execute("SELECT * FROM weather_runs WHERE loc_id=? AND kind='earlier' ORDER BY id LIMIT 1", (L['id'],)).fetchone()
    return jsonify(location=L, places=places_list(c), forecast=fc, status=st, enabled=L['enabled'], home=home_place(c),
                   weather={'first': first[0], 'last': first[1], 'count': first[2], 'detail_since': L['detail_since'], 'detail_years': detail_years(c)},
                   daily={'first': dd[0], 'last': dd[1], 'count': dd[2]},
                   sensor={'first': sens[0], 'last': sens[1], 'count': sens[2], 'devices': sens[3]},
                   runs={'history': run_dict(last_hist) if last_hist else None, 'history_ok': run_dict(last_ok_hist) if last_ok_hist else None,
                         'auto': run_dict(last_auto) if last_auto else None, 'any': run_dict(last_any) if last_any else None,
                         'earlier': run_dict(earlier) if earlier else None},
                   db_mb=round(os.path.getsize(DB_PATH) / 1048576, 1), job={**WX_JOB, 'now_ts': time.time()}, background=os.environ.get('PLANTDB_WEATHER', '1') == '1')

@app.route('/api/weather/job')
def weather_job():
    return jsonify({**WX_JOB, 'now_ts': time.time()})

@app.route('/api/weather/runs')
def weather_runs():
    c = db()
    n = max(1, min(int(request.args.get('n', 100)), 1000))
    kind = request.args.get('kind')
    q, a = 'SELECT * FROM weather_runs WHERE loc_id=?', [req_loc(c)['id']]
    if kind in ('history', 'recent', 'earlier'): q += ' AND kind=?'; a.append(kind)
    rows = c.execute(q + ' ORDER BY id DESC LIMIT ?', a + [n]).fetchall()
    return jsonify([run_dict(r) for r in rows],)

@app.route('/api/weather/refresh', methods=['POST'])
def weather_refresh():
    """Starts an update in the background (a long history load takes minutes) and returns at once. Poll /api/weather/job."""
    b = request.get_json(silent=True) or {}
    start = b.get('backfill_start')
    if start:
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', str(start)): abort(400, 'Start date must look like 2025-10-01')
        try: datetime.strptime(start, '%Y-%m-%d')
        except ValueError: abort(400, 'That date does not exist')
        if start < '1940-01-01': abort(400, 'Open-Meteo history starts in 1940')
    c = db()
    which = b.get('loc')
    if which == 'all':
        pl = [(r['id'], r['name']) for r in c.execute('SELECT id,name FROM locations WHERE enabled=1 ORDER BY is_home DESC, name')] or [(location(c)['id'], location(c)['name'])]
    else:
        L = loc_get(c, which)
        if L is None: abort(404, 'That place does not exist')
        pl = [(L['id'], L['name'])]
    started = start_job('load-history' if start else 'update-now', start or None, pl)
    return jsonify(started=started, job={**WX_JOB, 'now_ts': time.time()}), (202 if started else 409)

# ---- the table of everything logged
SENSOR_COLS = [('temp_f', 'Temperature', '°F'), ('humidity', 'Humidity', '%'), ('par', 'PAR', 'µmol/m²/s'), ('lux', 'Light', 'lux'),
               ('soil_moisture', 'Soil moisture', '%'), ('soil_temp_f', 'Soil temperature', '°F'), ('soil_ph', 'Soil pH', ''), ('weight_g', 'Pot weight', 'g'), ('soil_raw', 'Probe volts', 'V'), ('note', 'Note', '')]   # 1.35.0: weight; 1.36.0: probe volts

def wx_units(c):
    try: u = json.loads(setting(c, 'wx_units', '{}') or '{}')
    except ValueError: u = {}
    return u

def table_columns(c, kind, source):
    if source == 'sensor':
        return [{'key': k, 'label': l, 'unit': u, 'group': 'Sensor'} for k, l, u in SENSOR_COLS]
    units = wx_units(c)
    names = WX_HOURLY if kind == 'hourly' else WX_DAILY
    have = set(units)                     # every measurement ever received has its unit recorded, so no table scan is needed
    cols = []
    if kind == 'hourly':
        cols += [{'key': 'temperature_2m', 'label': wx_label('temperature_2m'), 'unit': units.get('temperature_2m', '°F'), 'group': 'Air'},
                 {'key': 'relative_humidity_2m', 'label': wx_label('relative_humidity_2m'), 'unit': units.get('relative_humidity_2m', '%'), 'group': 'Air'},
                 {'key': 'par', 'label': 'PAR (plant light)', 'unit': 'µmol/m²/s', 'group': 'Sunlight'}]
    for n in names:
        if n in ('temperature_2m', 'relative_humidity_2m') and kind == 'hourly': continue
        if n in have or n in units:
            cols.append({'key': n, 'label': wx_label(n), 'unit': units.get(n, ''), 'group': WX_GROUP_OF.get(n, 'Other')})
    return cols

def local_bounds(c, a, b, tzname=None):
    tz = tzinfo(tzname or location(c)['tz'])
    lo = hi = None
    if a:
        try: lo = iso(datetime.strptime(a, '%Y-%m-%d').replace(tzinfo=tz).timestamp())
        except ValueError: abort(400, 'From date must look like 2026-10-01')
    if b:
        try: hi = iso(datetime.strptime(b, '%Y-%m-%d').replace(tzinfo=tz).timestamp() + 86400 - 1)
        except ValueError: abort(400, 'To date must look like 2026-10-31')
    return lo, hi

def table_query(c, args):
    kind = 'daily' if args.get('kind') == 'daily' else 'hourly'
    g.wx_place = loc_get(c, args.get('loc'))
    if g.wx_place is None: abort(404, 'That place does not exist')
    source = 'sensor' if args.get('source') == 'sensor' else 'weather'
    if source == 'sensor': kind = 'hourly'
    order = 'ASC' if args.get('order') == 'asc' else 'DESC'
    a, b = args.get('from'), args.get('to')
    return kind, source, order, a, b

def table_rows(c, kind, source, order, a, b, limit=None, offset=0):
    L = getattr(g, 'wx_place', None) or location(c)
    tz = tzinfo(L['tz'] if source == 'weather' else location(c)['tz'])
    if kind == 'daily':
        w, ar = ['loc_id=?'], [L['id']]
        if a: w.append('date>=?'); ar.append(a)
        if b: w.append('date<=?'); ar.append(b)
        wh = ' WHERE ' + ' AND '.join(w) if w else ''
        total = c.execute('SELECT COUNT(*) FROM weather_daily' + wh, ar).fetchone()[0]
        q = f'SELECT date,data,kind FROM weather_daily{wh} ORDER BY date {order}' + (' LIMIT ? OFFSET ?' if limit else '')
        rs = c.execute(q, ar + ([limit, offset] if limit else [])).fetchall()
        return total, ({'when': r['date'], 'kind': r['kind'], **json.loads(r['data'])} for r in rs)
    lo, hi = local_bounds(c, a, b, L['tz'] if source == 'weather' else None)
    w, ar = ['source=?', 'ts<=?'], [source, iso(time.time() + 7200)]
    if source == 'weather': w.append('device=?'); ar.append(L['device'])
    if lo: w.append('ts>=?'); ar.append(lo)
    if hi: w.append('ts<=?'); ar.append(hi)
    wh = ' WHERE ' + ' AND '.join(w)
    total = c.execute('SELECT COUNT(*) FROM readings' + wh, ar).fetchone()[0]
    q = f'SELECT * FROM readings{wh} ORDER BY ts {order}' + (', device' if source == 'sensor' else '') + (' LIMIT ? OFFSET ?' if limit else '')
    if limit and source == 'weather':        # walk the (source, ts) index for the page, then fetch only those rows
        q = f'SELECT * FROM readings WHERE id IN (SELECT id FROM readings INDEXED BY readings_uq{wh} ORDER BY ts {order} LIMIT ? OFFSET ?) ORDER BY ts {order}'
    rs = c.execute(q, ar + ([limit, offset] if limit else [])).fetchall()
    def conv(r):
        when = parse_ts(r['ts']).astimezone(tz).strftime('%Y-%m-%d %H:%M')
        if source == 'sensor':
            return {'when': when, 'device': r['device'], **{k: r[k] for k, _, _ in SENSOR_COLS}}
        d = json.loads(r['extra']) if r['extra'] else {}
        return {'when': when, 'temperature_2m': r['temp_f'], 'relative_humidity_2m': r['humidity'], 'par': r['par'], **d}
    return total, (conv(r) for r in rs)

@app.route('/api/weather/table')
def weather_table():
    c = db()
    kind, source, order, a, b = table_query(c, request.args)
    try: per, page = max(10, min(int(request.args.get('per', 50)), 1000)), max(1, int(request.args.get('page', 1)))
    except ValueError: abort(400, 'page and per must be whole numbers')
    total, rows = table_rows(c, kind, source, order, a, b, per, (page - 1) * per)
    if total and (page - 1) * per >= total:                  # past the end: show the last page instead of an empty one
        page = -(-total // per)
        total, rows = table_rows(c, kind, source, order, a, b, per, (page - 1) * per)
    return jsonify(kind=kind, source=source, columns=table_columns(c, kind, source), rows=list(rows), total=total, page=page, per=per,
                   pages=max(1, -(-total // per)), tz=(g.wx_place if source == 'weather' else location(c))['tz'], place=g.wx_place)

@app.route('/api/weather/table.csv')
def weather_table_csv():
    c = db()
    kind, source, order, a, b = table_query(c, request.args)
    cols = table_columns(c, kind, source)
    total, rows = table_rows(c, kind, source, order, a, b)
    head = ['date' if kind == 'daily' else 'local_time'] + (['device'] if source == 'sensor' else []) + (['kind'] if kind == 'daily' else []) + \
           [k['key'] + (f" ({k['unit']})" if k['unit'] else '') for k in cols]
    def gen():
        buf = io.StringIO(); w = csv.writer(buf)
        w.writerow(head); yield buf.getvalue(); buf.seek(0); buf.truncate()
        for i, r in enumerate(rows):
            w.writerow([r['when']] + ([r.get('device')] if source == 'sensor' else []) + ([r.get('kind')] if kind == 'daily' else []) + [r.get(k['key']) for k in cols])
            if i % 500 == 499: yield buf.getvalue(); buf.seek(0); buf.truncate()
        yield buf.getvalue()
    slug = re.sub(r'[^A-Za-z0-9]+', '-', g.wx_place['name']).strip('-').lower()[:30] or 'place'
    name = f"{'sensor' if source == 'sensor' else 'weather-' + slug + '-' + kind}-readings-{datetime.now().strftime('%Y%m%d')}.csv"
    return Response(gen(), mimetype='text/csv', headers={'Content-Disposition': f'attachment; filename={name}'})

@app.route('/api/weather/catalog')
def weather_catalog():
    """Every measurement we ask Open-Meteo for, its group and unit, and whether it has actually arrived."""
    c = db()
    units = wx_units(c)
    try: un = json.loads(setting(c, 'wx_unsupported', '{}') or '{}')
    except ValueError: un = {}
    out = []
    for kind, groups in (('hourly', WX_HOURLY_GROUPS), ('daily', WX_DAILY_GROUPS)):
        for g, vs in groups:
            for v in vs:
                out.append({'kind': kind, 'group': g, 'key': v, 'label': wx_label(v), 'unit': units.get(v, ''),
                            'history_missing': v in (un.get('archive:' + kind) or []), 'recent_missing': v in (un.get('forecast:' + kind) or [])})
    return jsonify(out)

@app.route('/api/weather/monthly')
def weather_monthly():
    """Observed monthly summary: average daily low/high, humidity, daily light, freezing nights."""
    c = db()
    source = request.args.get('source', 'weather')
    loc = req_loc(c) if source == 'weather' else location(c); tz = tzinfo(loc['tz'])
    since = request.args.get('from')                      # a month like 2025-09; the default is the last 14 months
    if not since or not re.match(r'^\d{4}-\d{2}$', since):
        d = datetime.now(tz).date().replace(day=1)
        for _ in range(14): d = (d - timedelta(days=1)).replace(day=1)
        since = d.strftime('%Y-%m')
    rows = c.execute('SELECT ts,temp_f,humidity,par FROM readings WHERE source=? AND ts>=?' + (' AND device=?' if source == 'weather' else '') + ' ORDER BY ts',
                     (source, since + '-01T00:00:00Z') + ((loc['device'],) if source == 'weather' else ())).fetchall()
    days = {}
    for r in rows:
        d = parse_ts(r['ts']).astimezone(tz).date().isoformat()
        x = days.setdefault(d, {'t': [], 'h': [], 'par': []})
        if r['temp_f'] is not None: x['t'].append(r['temp_f'])
        if r['humidity'] is not None: x['h'].append(r['humidity'])
        if r['par'] is not None: x['par'].append(r['par'])
    months = {}
    for d, x in days.items():
        if len(x['t']) < 12: continue                    # skip partial days
        m = months.setdefault(d[:7], {'lows': [], 'highs': [], 'rh': [], 'dli': [], 'freeze': 0, 'days': 0})
        m['lows'].append(min(x['t'])); m['highs'].append(max(x['t'])); m['days'] += 1
        if min(x['t']) <= 32: m['freeze'] += 1
        if x['h']: m['rh'].append(sum(x['h']) / len(x['h']))
        if len(x['par']) >= 12: m['dli'].append(sum(x['par']) * 3600 / len(x['par']) * 24 / 1e6)
    avg = lambda v: round(sum(v) / len(v), 1) if v else None
    return jsonify([{'month': k, 'days': m['days'], 'low': avg(m['lows']), 'high': avg(m['highs']), 'rh': avg(m['rh']),
                     'dli': avg(m['dli']), 'freeze_nights': m['freeze']} for k, m in sorted(months.items())])
