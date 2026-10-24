"""Run the app with a fake Open-Meteo (no internet needed), on http://127.0.0.1:8080.
Usage: DATA_DIR=dev/tmp/data python3 dev/test/mock_server.py   (an empty DATA_DIR gets a fresh install with all plants)
Cold weather for testing frost features: MOCK_BASE_F=40 (nights around 22-34°F).
MOCK_TS=1 also answers on port 8081 (PLANTDB_TS_PORT) as if requests came through Tailscale; send Tailscale-User-Login yourself.
The forecast fills in after an update: POST /api/weather/refresh with an X-Editor header (or press Update now on the Weather page)."""
import math
import os, sys, time, urllib.parse
os.environ['PLANTDB_WEATHER']='0'
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
S.http_json=fake
S.init_db()
# rain: dry, except about 0.6 in every fifth day (so watering reminders can be tested)
_fake_weather = S.http_json
def _with_rain(url, tries=3):
    d = _fake_weather(url, tries)
    for kind in ('hourly', 'daily'):
        if kind not in d: continue
        for n, vals in d[kind].items():
            if n == 'time' or 'probability' in n or not any(w in n for w in ('precip', 'rain', 'showers', 'snowfall')): continue
            d[kind][n] = [(0.6 if kind == 'daily' or int(t // 3600) % 24 == 15 else 0.0) if int(t // 86400) % 5 == 0 else 0.0 for t in d[kind]['time']]
    return d
S.http_json = _with_rain
# 1.12.0: a second port that stands in for the Tailscale container (MOCK_TS=1). Requests to it are treated as coming through
# Tailscale Serve, so tests send Tailscale-User-Login / Tailscale-User-Name themselves, as Serve would.
if os.environ.get('MOCK_TS') == '1':
    import threading
    from werkzeug.serving import make_server
    _ts = make_server('127.0.0.1', int(S.TS_PORT), S.app, threaded=True)
    threading.Thread(target=_ts.serve_forever, daemon=True).start()
    _sensor = make_server('127.0.0.1', int(S.SENSOR_PORT), S.app, threaded=True)      # and the sensor-only port
    threading.Thread(target=_sensor.serve_forever, daemon=True).start()
S.app.run(host='127.0.0.1', port=int(os.environ.get('PORT', '8080')), threaded=True)
