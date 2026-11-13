"""Run the app with a fake Open-Meteo (no internet needed), on http://127.0.0.1:8080.
Usage: DATA_DIR=dev/tmp/data python3 dev/test/mock_server.py   (an empty DATA_DIR gets a fresh install with all plants)
Cold weather for testing frost features: MOCK_BASE_F=40 (nights around 22-34°F).
MOCK_TS=1 also answers on port 8081 (PLANTDB_TS_PORT) as if requests came through Tailscale; send Tailscale-User-Login yourself.
The forecast fills in after an update: POST /api/weather/refresh with an X-Editor header (or press Update now on the Weather page)."""
import math
import os, sys, time, urllib.parse
os.environ['PLANTDB_WEATHER']='0'
os.environ.setdefault('PLANTDB_UPDATES', '0')     # 1.55.0: no asking GitHub for the newest release from a test
# 1.18.0: the picture checker. Without MOCK_VISION=real, a fake one (dev/test/mock_vision.py) answers on 127.0.0.1:8090,
# started here, and stands in for Pl@ntNet and Claude too. With MOCK_VISION=real, run vision/service.py on 8090 yourself.
os.environ.setdefault('PLANTDB_VISION_URL', 'http://127.0.0.1:' + os.environ.get('MOCK_VISION_PORT', '8090'))
os.environ.setdefault('PLANTDB_SPEECH_URL', 'http://127.0.0.1:' + os.environ.get('MOCK_SPEECH_PORT', '8093'))   # search by voice
os.environ.setdefault('PLANTDB_PLANTNET_URL', os.environ['PLANTDB_VISION_URL'] + '/mock/plantnet')
os.environ.setdefault('PLANTDB_CLAUDE_URL', os.environ['PLANTDB_VISION_URL'] + '/mock/claude')
os.environ.setdefault('PLANTDB_EBAY_API', os.environ['PLANTDB_VISION_URL'] + '/mock/ebay')      # 1.27.0: wishlist shops
os.environ.setdefault('PLANTDB_ETSY_API', os.environ['PLANTDB_VISION_URL'] + '/mock/etsy')
os.environ.setdefault('PLANTDB_SHOP_GAP', '0')
os.environ.setdefault('PLANTDB_SHOPS', '0')            # no checks on a schedule in tests (the real shops are not reachable)
os.environ.setdefault('PLANTDB_OSM_URL', os.environ['PLANTDB_VISION_URL'] + '/mock/osm')                         # 1.30.0: store addresses
os.environ.setdefault('PLANTDB_INAT_URL', os.environ['PLANTDB_VISION_URL'] + '/mock/inat/v1')                 # 1.21.0: library photos
os.environ.setdefault('PLANTDB_INAT_IMG_OK', os.environ['PLANTDB_VISION_URL'] + '/mock/inat/img/')
os.environ.setdefault('PLANTDB_ASPCA_MIN', '3')
# 1.58.0: like an installed copy, the second-copy folder exists beside the data (docker-compose maps ./backups-copy there until
# PLANTDB_COPY_DIR names another drive), so the pages can say that it is the same drive
os.environ.setdefault('PLANTDB_COPY_MOUNT', os.path.join(os.path.dirname(os.path.abspath(os.environ.get('DATA_DIR', '/data'))), 'backups-copy-mock'))
os.makedirs(os.environ['PLANTDB_COPY_MOUNT'], exist_ok=True)
os.environ.setdefault('PLANTDB_ASPCA_URL', os.environ['PLANTDB_VISION_URL'] + '/mock/aspca')                       # 1.23.0: pet safety lists
sys.path.insert(0,os.environ.get('APPDIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'app')))
import server as S
from datetime import datetime, timedelta, timezone
def fake(url, tries=3):
    time.sleep(0.2)
    u=urllib.parse.urlparse(url); q=dict(urllib.parse.parse_qsl(u.query))
    if 'geocoding' in u.netloc:
        return {'results':[{'name':'Baraboo','admin1':'Wisconsin','admin1_code':'WI','country':'United States','country_code':'US','latitude':43.4711,'longitude':-89.7443,'timezone':'America/Chicago','elevation':262,'population':12000},
                           {'name':'Baraboo','admin1':'New South Wales','country':'Australia','country_code':'AU','latitude':-33.0,'longitude':150.0,'timezone':'Australia/Sydney','elevation':300,'population':100}]}
    api='archive' if 'archive' in u.netloc else 'forecast'; kind='hourly' if 'hourly' in q else 'daily'; names=q[kind].split(',')
    if api=='archive': a=datetime.strptime(q['start_date'],'%Y-%m-%d'); b=datetime.strptime(q['end_date'],'%Y-%m-%d')
    else:
        t=datetime.now(); a=(t-timedelta(days=int(q['past_days']))).replace(hour=0,minute=0,second=0,microsecond=0); b=a+timedelta(days=int(q['past_days'])+int(q['forecast_days'])-1)
    a=a.replace(tzinfo=timezone(timedelta(hours=-5))); ts=[]; d=a; step=timedelta(hours=1) if kind=='hourly' else timedelta(days=1)
    while d.date()<=b.date(): ts.append(int(d.timestamp())); d+=step
    # MOCK_BASE_F sets the average temperature for places south of 40°N (default 65); each day also drifts up or down a few degrees
    base = 30.0 if float(q['latitude'])>40 else float(os.environ.get('MOCK_BASE_F', '65'))
    return {kind:{'time':ts, **{n:[round(base + 12*math.sin((t/3600 % 24)/24*6.283) + 6*math.cos(t/86400*1.3),1) for t in ts] for n in names}}, kind+'_units':{n:('°F' if ('temp' in n or 'dew' in n) else 'inch' if ('precip' in n or 'rain' in n) else 'u') for n in names}}
S.patch('http_json', fake)
S.init_db()
# rain: dry, except about 0.6 in every fifth day, and never in the last 9 days, so some plants are always due for water
# whatever the date (watering reminders can be tested)
_fake_weather = S.http_json
import time as _time
def _with_rain(url, tries=3):
    d = _fake_weather(url, tries)
    for kind in ('hourly', 'daily'):
        if kind not in d: continue
        for n, vals in d[kind].items():
            if n == 'time' or 'probability' in n or not any(w in n for w in ('precip', 'rain', 'showers', 'snowfall')): continue
            d[kind][n] = [(0.6 if kind == 'daily' or int(t // 3600) % 24 == 15 else 0.0) if int(t // 86400) % 5 == 0 and t < _time.time() - 9 * 86400 else 0.0 for t in d[kind]['time']]
    return d
S.patch('http_json', _with_rain)
# 1.12.0: a second port that stands in for the Tailscale container (MOCK_TS=1). Requests to it are treated as coming through
# Tailscale Serve, so tests send Tailscale-User-Login / Tailscale-User-Name themselves, as Serve would.
if os.environ.get('MOCK_TS') == '1':
    import threading
    from werkzeug.serving import make_server
    _ts = make_server('127.0.0.1', int(S.TS_PORT), S.app, threaded=True)
    threading.Thread(target=_ts.serve_forever, daemon=True).start()
    _sensor = make_server('127.0.0.1', int(S.SENSOR_PORT), S.app, threaded=True)      # and the sensor-only port
    threading.Thread(target=_sensor.serve_forever, daemon=True).start()
if os.environ.get('MOCK_VISION', 'fake') == 'fake':
    import threading, importlib.util
    from werkzeug.serving import make_server
    _spec = importlib.util.spec_from_file_location('mock_vision', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mock_vision.py'))
    _mv = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_mv)
    import socket
    _port = int(os.environ.get('MOCK_VISION_PORT', '8090'))
    with socket.socket() as _s: _busy = _s.connect_ex(('127.0.0.1', _port)) == 0
    if _busy: print(f'mock vision not started: port {_port} is in use (a real vision service, probably)')
    else:
        _vs = make_server('127.0.0.1', _port, _mv.app, threaded=True)
        threading.Thread(target=_vs.serve_forever, daemon=True).start()
if os.environ.get('MOCK_SPEECH', 'fake') == 'fake':          # search by voice: a fake speech service (dev/test/mock_speech.py)
    import threading, importlib.util, socket
    from werkzeug.serving import make_server
    _sspec = importlib.util.spec_from_file_location('mock_speech', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mock_speech.py'))
    _ms = importlib.util.module_from_spec(_sspec); _sspec.loader.exec_module(_ms)
    _sport = int(os.environ.get('MOCK_SPEECH_PORT', '8093'))
    with socket.socket() as _s: _sbusy = _s.connect_ex(('127.0.0.1', _sport)) == 0
    if _sbusy: print(f'mock speech not started: port {_sport} is in use')
    else:
        _ss = make_server('127.0.0.1', _sport, _ms.app, threaded=True)
        threading.Thread(target=_ss.serve_forever, daemon=True).start()
@S.app.route('/mock/problem', methods=['POST'])
def mock_problem():                      # 1.31.0: lets a test record a background problem
    b = S.request.get_json(silent=True) or {}
    S.problem(b.get('area', 'weather'), b.get('text', 'Test problem'), b.get('detail', ''))
    return S.jsonify(ok=True)

PUSHED = []                               # 1.33.0: notifications the app tried to send, instead of a real push service
def fake_push(sub, payload):
    PUSHED.append({'login': sub['login'], 'device': sub['device'], 'endpoint': sub['endpoint'], **payload})
    return 410 if 'gone' in sub['endpoint'] else 201
S.PUSH_SEND['fn'] = fake_push
@S.app.route('/mock/pushed', methods=['GET', 'DELETE'])
def mock_pushed():
    if S.request.method == 'DELETE': PUSHED.clear()
    return S.jsonify(pushed=PUSHED)
@S.app.route('/mock/push/run', methods=['POST'])
def mock_push_run():                     # the clock-driven sends, now, as if it were the hour asked for
    b = S.request.get_json(silent=True) or {}
    c = S.sqlite3.connect(S.DB_PATH, timeout=30); c.row_factory = S.sqlite3.Row
    try:
        if b.get('what') == 'cold': S.push_cold(c)
        elif b.get('what') == 'sensors': S.push_sensors(c)
        elif b.get('what') == 'cover': S.push_cover(c, b.get('hour'))
        else: S.push_due(c)
    finally: c.close()
    return S.jsonify(ok=True)

@S.app.route('/mock/history', methods=['POST'])
def mock_history():                      # 1.34.0: whole years of daily highs and lows, so the winter and summer zones can be worked out
    b = S.request.get_json(silent=True) or {}
    years, lid = int(b.get('years', 4)), int(b.get('loc', 1))
    import math
    c = S.sqlite3.connect(S.DB_PATH, timeout=30)
    try:
        this_year = S.datetime.now(S.timezone.utc).year
        for y in range(this_year - years, this_year):
            d = S.date(y, 1, 1)
            while d.year == y:
                doy = d.timetuple().tm_yday
                hi = 71 + 27 * math.sin((doy - 110) / 365 * 2 * math.pi) + (3 if doy % 7 == 0 else 0)     # Round Rock-like: 44°F highs in January, 98 in July
                lo = hi - 22 - (6 if doy % 11 == 0 else 0)
                c.execute("INSERT INTO weather_daily(loc_id,date,data,kind,updated_at) VALUES(?,?,?,?,?) ON CONFLICT(loc_id,date) DO UPDATE SET data=excluded.data",
                          (lid, d.isoformat(), S.json.dumps({'temperature_2m_max': round(hi, 1), 'temperature_2m_min': round(lo, 1)}), 'observed', S.now()))
                d += S.timedelta(days=1)
        c.commit()
    finally: c.close()
    S.PLACE_HEAT.clear(); S.PLACE_CLIMATE.clear()
    return S.jsonify(ok=True, years=years)

S.app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '8080')), threaded=True)
