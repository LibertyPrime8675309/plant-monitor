"""The frost alert and the calendar file.
Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- frost alert (added in 1.8.0)
FROST_MARGIN = 3          # °F: forecasts often miss a clear, still night by a few degrees, so warn this far above a plant's damage point
FROST_LEVELS = {'danger': 3, 'damage': 2, 'watch': 1}

def frost_done(c):
    try: return json.loads(setting(c, 'frost_done', '{}') or '{}')
    except ValueError: return {}

def frost_report(c):
    """Nights in the home forecast that would hurt plants that are outside (Outdoors or Covered porch), plant by plant."""
    L = location(c)
    fc = loc_json(c, L['id'], 'forecast')
    today = local_today(c).isoformat()
    days = [d for d in (fc.get('days') or []) if d.get('date', '') >= today and d.get('low') is not None][:7]
    done = frost_done(c)
    at, at_args = plants_at(c, L)                  # 1.28.0: only the plants at this home
    plants = c.execute("SELECT * FROM plants WHERE status='active' AND temp_damage_below IS NOT NULL" + at + " ORDER BY code", at_args).fetchall()
    outdoor = [r for r in plants if (r['site'] or 'Outdoors') not in INSIDE_SITES]
    photo = lambda pid: (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (pid,)).fetchone() or [None])[0]
    nights, worst = [], None
    for d in days:
        low, at = d['low'], []
        for r in outdoor:
            dmg, leth = r['temp_damage_below'], r['temp_lethal_below']
            if leth is not None and low < leth: lv = 'danger'
            elif low < dmg: lv = 'damage'
            elif low < dmg + FROST_MARGIN: lv = 'watch'
            else: continue
            at.append({'code': r['code'], 'name': r['common_name'], 'photo': photo(r['id']), 'damage': dmg, 'lethal': leth,
                       'plan': r['winter_plan'], 'site': r['site'] or 'Outdoors', 'level': lv, 'done': done.get(d['date'], {}).get(r['code'])})
        at.sort(key=lambda x: (-FROST_LEVELS[x['level']], -(x['damage'] or 0), x['code']))
        lv = max((x['level'] for x in at), key=lambda v: FROST_LEVELS[v], default=None)
        n = {'date': d['date'], 'low': low, 'high': d.get('high'), 'hours': d.get('hours'), 'level': lv, 'plants': at,
             'counts': {k: sum(1 for x in at if x['level'] == k) for k in FROST_LEVELS}}
        nights.append(n)
        if lv and (worst is None or FROST_LEVELS[lv] > FROST_LEVELS[worst['level']]
                   or (lv == worst['level'] and low < worst['low'])):
            worst = n                                     # the most serious night; among equals, the coldest
    first = next((n for n in nights if n['level']), None)
    # the same, plant by plant: every cold night for each plant, the next one (what to act on) and the coldest
    by = {}
    for n in nights:
        for x in n['plants']:
            q = by.setdefault(x['code'], {k: x[k] for k in ('code', 'name', 'photo', 'damage', 'lethal', 'plan', 'site')} | {'nights': []})
            q['nights'].append({'date': n['date'], 'low': n['low'], 'level': x['level']})
    plants_out = []
    for q in by.values():
        q['next'] = q['nights'][0]
        q['worst'] = max(q['nights'], key=lambda z: (FROST_LEVELS[z['level']], -z['low']))
        q['level'] = q['worst']['level']
        q['done'] = done.get(q['next']['date'], {}).get(q['code'])
        plants_out.append(q)
    plants_out.sort(key=lambda q: (-FROST_LEVELS[q['level']], q['next']['date'], -(q['damage'] or 0), q['code']))
    return {'place': L['name'], 'fetched_at': fc.get('fetched_at'), 'margin': FROST_MARGIN, 'today': today, 'nights': nights, 'plants': plants_out,
            'outdoor': len(outdoor), 'level': worst['level'] if worst else None,
            'worst': {k: worst[k] for k in ('date', 'low', 'level', 'counts')} if worst else None,
            'first': {k: first[k] for k in ('date', 'low', 'level', 'counts')} if first else None}

@app.route('/api/frost')
def frost_api():
    return jsonify(frost_report(db()))

@app.route('/api/frost/done', methods=['POST'])
def frost_mark():
    """Tick a plant off the cold-night checklist ("covered") for one night, or untick it."""
    c = db()
    b = request.get_json(silent=True) or {}
    date, code, what = str(b.get('date', '')), str(b.get('code', '')), b.get('what')
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date): abort(400, 'date must look like 2026-11-03')
    r = plant_row(c, code)
    if what not in ('covered', None): abort(400, "what must be 'covered' or empty")
    done = frost_done(c)
    keep = local_today(c).isoformat()
    done = {k: v for k, v in done.items() if k >= keep}           # forget nights that have passed
    night = done.setdefault(date, {})
    if what: night[r['code']] = {'what': what, 'by': editor(), 'at': now()}
    else: night.pop(r['code'], None)
    if not night: done.pop(date, None)
    set_setting(c, 'frost_done', json.dumps(done))
    d = datetime.strptime(date, '%Y-%m-%d'); night_words = f'{d:%A}, {d:%b} {d.day}'      # "Sunday, Oct 25"
    audit_only(c, 'frost', 'frost', None, what or 'undone', editor(),
               ('Covered for the cold night of %s' % night_words) if what else ('Cold-night tick removed for %s' % night_words), r['id'], r['code'])
    c.commit()
    return jsonify(frost_report(c))

# ---------------------------------------------------------------- calendar file: feeding days and cold nights (prototype, proto/calendar-file)
# GET /api/calendar.ics makes an iCalendar file to import into a phone, Outlook or Google calendar.
# GET /cal/<token>.ics is the same calendar for subscribing: it needs no password, only the private token in the link, so a
# calendar service on the internet can fetch it (guard() lets /cal/ through; the token is checked here).
# GET /api/calendar gives the events as JSON, for the preview in the "Add to your calendar" window.
# The choices are kept in settings 'ics_options' (GET/PUT /api/calendar/settings), so the file and the subscribed
# calendar always match the window. Query arguments of the same names override them for one request (used by the tests).
ICS_NAME = 'Plant record'
ICS_DEFAULTS = {'feed': True, 'cold': True, 'close': True, 'months': 3, 'weekly': True, 'day': 5,      # day: 0 = Monday ... 5 = Saturday
                'feed_remind': True, 'feed_at': '08:00', 'cold_remind': True, 'cold_at': '16:00', 'public_base': ''}
ICS_DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

def ics_text(s):
    """Escape text for an iCalendar value (RFC 5545 section 3.3.11)."""
    return str(s).replace('\\', '\\\\').replace(';', '\\;').replace(',', '\\,').replace('\r\n', '\n').replace('\n', '\\n')

def ics_fold(line):
    """Fold a content line at 75 octets, as the standard asks; continuation lines start with one space."""
    b = line.encode('utf-8')
    if len(b) <= 75: return line
    out, cur = [], b''
    for ch in line:
        e = ch.encode('utf-8')
        if len(cur) + len(e) > (75 if not out else 74):
            out.append(cur.decode('utf-8')); cur = b''
        cur += e
    out.append(cur.decode('utf-8'))
    return '\r\n '.join(out)

def ics_season(r, m):
    a, b = r['fert_from_month'], r['fert_to_month']
    return a <= m <= b if a <= b else (m >= a or m <= b)

def ics_season_start(r, d):
    """The first day on or after d that falls in the plant's feeding season (d itself when it already does)."""
    for _ in range(14):
        if ics_season(r, d.month): return d
        d = (d.replace(day=1) + timedelta(days=32)).replace(day=1)
    return d

def ics_feed_days(c, today, end, weekday=None):
    """Projected feeding days per plant, the same way the Fertilizer page works out "Next feeding" (nextDue() in app.js),
    then every "Feed every (days)" after that, skipping the resting months. Later dates assume each feeding is done on time.
    With a weekday (0 = Monday), each feeding moves to the first feeding day of the week on or after the day it is due
    (never earlier: Ethan asked that a plant is never fed too early), and the next one is counted from that day, since that
    is when the plant will be fed."""
    last = dict(c.execute('SELECT plant_code, MAX(applied_on) FROM fertilizer_log GROUP BY plant_code').fetchall())
    rows = c.execute("""SELECT code, common_name, fert_from_month, fert_to_month, fert_every_days, site FROM plants WHERE status='active'
                        AND fert_from_month IS NOT NULL AND fert_to_month IS NOT NULL AND fert_every_days IS NOT NULL ORDER BY code""").fetchall()
    first = today + timedelta(days=(weekday - today.weekday()) % 7) if weekday is not None else today
    def snap(d):
        if weekday is None: return d
        return max(d + timedelta(days=(weekday - d.weekday()) % 7), first)    # the feeding day on or after d
    days = {}
    for r in rows:
        every = max(1, int(r['fert_every_days']))
        lf = last.get(r['code'])
        d = date.fromisoformat(lf) + timedelta(days=every) if lf else today
        if d < today: d = today
        for _ in range(400):
            d = snap(ics_season_start(r, d))
            while not ics_season(r, d.month): d += timedelta(days=7)          # snapped back across the start of the season
            if d > end: break
            days.setdefault(d.isoformat(), []).append({'code': r['code'], 'name': r['common_name'], 'every': every, 'last': lf})
            d = d + timedelta(days=every)
    return [{'date': k, 'plants': v} for k, v in sorted(days.items())]

def ics_clean(o):
    """Check and fill in a set of choices; anything missing or wrong falls back to the default."""
    out = dict(ICS_DEFAULTS)
    for k, v in (o or {}).items():
        if k not in ICS_DEFAULTS: continue
        d = ICS_DEFAULTS[k]
        if isinstance(d, bool): out[k] = v if isinstance(v, bool) else str(v).lower() not in ('0', 'false', 'no', '')
        elif k == 'months':
            try: out[k] = min(12, max(1, int(v)))
            except (TypeError, ValueError): abort(400, 'How far ahead must be a number of months from 1 to 12')
        elif k == 'day':
            try: out[k] = int(v) % 7
            except (TypeError, ValueError): abort(400, 'The feeding day must be a day of the week')
        elif k in ('feed_at', 'cold_at'):
            if not re.match(r'^([01]\d|2[0-3]):[0-5]\d$', str(v)): abort(400, 'Reminder times look like 08:00 or 16:30')
            out[k] = str(v)
        elif k == 'public_base':
            v = re.sub(r'/cal$', '', str(v or '').strip().rstrip('/'))          # a pasted link with /cal on the end still works
            if v and not re.match(r'^https?://[A-Za-z0-9.\-]+(:\d+)?(/[\w.\-/]*)?$', v): abort(400, 'The internet address should look like https://your-pc.tail1234.ts.net:8443')
            out[k] = v
    return out

def ics_saved(c):
    try: return ics_clean(json.loads(setting(c, 'ics_options', '{}') or '{}'))
    except ValueError: return dict(ICS_DEFAULTS)

def ics_options(c):
    """The saved choices, with any query arguments of the same names on top."""
    o = ics_saved(c)
    over = {k: request.args[k] for k in ICS_DEFAULTS if k in request.args and k != 'public_base'}
    if 'remind' in request.args: over['feed_remind'] = over['cold_remind'] = request.args['remind']     # older one-switch form
    return ics_clean({**o, **over}) if over else o

def ics_token(c):
    t = setting(c, 'ics_token')
    if not t:
        t = secrets.token_urlsafe(18); set_setting(c, 'ics_token', t); c.commit()
    return t

def ics_use_place():
    """?place=ID works like the X-Place header (see location()), for links that cannot send headers."""
    v = request.args.get('place', '').strip()
    if v.isdigit() and not request.headers.get('X-Place'):
        request.environ['HTTP_X_PLACE'] = v                  # Flask reads headers from the environ, so location() sees it

def ics_events(c, o):
    ics_use_place()
    L = location(c)
    tz = tzinfo(L['tz'])
    today = local_today(c)
    end = today + timedelta(days=round(30.5 * o['months']))
    ev = []
    if o['feed']:
        weekly = o['weekly']
        for f in ics_feed_days(c, today, end, o['day'] if weekly else None):
            ps = f['plants']; n = len(ps)
            names = ', '.join(p['name'] for p in ps[:3]) + (f' and {n - 3} more' if n > 3 else '')
            title = (f'Feeding day: {n} plant{"s" if n != 1 else ""} ({names})' if weekly
                     else f'Feed {n} plant{"s" if n != 1 else ""}: {names}')
            lines = [f'{p["name"]} ({p["code"]}), every {p["every"]} days.' + (f' Last fed {p["last"]}.' if p['last'] else ' No feeding logged yet.') for p in ps]
            desc = (('Your weekly feeding day. These plants are due by now' if weekly else 'Plants due for fertilizer on this day') + ', from Plant record.\n\n' + '\n'.join(lines) +
                    '\n\nOpen the Fertilizer page that morning before you feed: it says "Hold off" when a cold night is coming or a plant is unwell.'
                    ' Later dates assume each feeding is done on the day shown.')
            ev.append({'kind': 'feed', 'uid': f'feed-{f["date"]}', 'date': f['date'], 'title': title, 'desc': desc,
                       'plants': [p['code'] for p in ps], 'path': '#/fertilizer'})
    if o['cold']:
        F = frost_report(c)
        words = {'danger': 'Could die', 'damage': 'Damaged', 'watch': 'Close call'}
        for n in F['nights']:
            at = [x for x in n['plants'] if o['close'] or x['level'] != 'watch']
            if not at: continue
            serious = [x for x in at if x['level'] != 'watch']
            d = date.fromisoformat(n['date'])
            start = datetime.combine(d - timedelta(days=1), datetime.min.time(), tz).replace(hour=18)   # the evening before: lows come just before dawn
            stop = datetime.combine(d, datetime.min.time(), tz).replace(hour=8)
            if stop < datetime.now(tz): continue                 # that night is over
            k = len(at)
            title = (f'Cold night, low {round(n["low"])}°F: protect {len(serious)} plant{"s" if len(serious) != 1 else ""}' if serious
                     else f'Cold night, low {round(n["low"])}°F: {k} close call{"s" if k != 1 else ""}')
            lines = []
            for lv in ('danger', 'damage', 'watch'):
                g = [x for x in at if x['level'] == lv]
                if g: lines.append(words[lv] + ': ' + ', '.join(f'{x["name"]} ({x["code"]})' for x in g) + '.')
            desc = (f'Forecast low of {round(n["low"])}°F before dawn on {d:%A}, {d:%B} {d.day}, in {F["place"]}. These plants are outside:\n\n' + '\n'.join(lines) +
                    f'\n\nMove them in or cover them before dark, then tick them off on the cold-night checklist.'
                    f' "Close call" means within {F["margin"]}°F of the plant\'s damage point. This comes from the forecast of {datetime.now(tz):%B} {datetime.now(tz).day}; forecasts change, so a subscribed calendar is the way to keep this current.')
            ev.append({'kind': 'cold', 'uid': f'cold-{n["date"]}', 'date': n['date'], 'title': title, 'desc': desc, 'level': n['level'] if serious else 'watch',
                       'start': start.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ'), 'end': stop.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ'),
                       'plants': [x['code'] for x in at], 'path': '#/frost'})
    ev.sort(key=lambda e: (e['date'], e['kind']))
    return {'place': L['name'], 'place_id': L['id'], 'today': today.isoformat(), 'until': end.isoformat(), 'options': o, 'events': ev,
            'counts': {'feed': sum(1 for e in ev if e['kind'] == 'feed'), 'cold': sum(1 for e in ev if e['kind'] == 'cold')}}

def ics_body(c, o, E, base):
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    host = 'plant-record-' + str(E['place_id'])
    tz = tzinfo(location(c)['tz'])
    fh, fm = map(int, o['feed_at'].split(':')); ch, cm = map(int, o['cold_at'].split(':'))
    out = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Plant record//Calendar file ' + APP_VERSION + '//EN', 'CALSCALE:GREGORIAN', 'METHOD:PUBLISH',
           'X-WR-CALNAME:' + ics_text(ICS_NAME), 'X-WR-CALDESC:' + ics_text('Feeding days and cold nights for ' + E['place']),
           'REFRESH-INTERVAL;VALUE=DURATION:PT6H', 'X-PUBLISHED-TTL:PT6H']
    for e in E['events']:
        out += ['BEGIN:VEVENT', f'UID:{e["uid"]}@{host}', 'DTSTAMP:' + stamp]
        if e['kind'] == 'feed':
            d = date.fromisoformat(e['date'])
            out += ['DTSTART;VALUE=DATE:' + d.strftime('%Y%m%d'), 'DTEND;VALUE=DATE:' + (d + timedelta(days=1)).strftime('%Y%m%d'),
                    'TRANSP:TRANSPARENT', 'CATEGORIES:Plants,Feeding']
        else:
            out += ['DTSTART:' + e['start'], 'DTEND:' + e['end'], 'TRANSP:TRANSPARENT', 'CATEGORIES:Plants,Cold night']
        out += ['SUMMARY:' + ics_text(e['title']), 'DESCRIPTION:' + ics_text(e['desc'] + ('\n\n' + base + e['path'] if base else ''))] + (['URL:' + base + e['path']] if base else [])
        trig = None
        if e['kind'] == 'feed' and o['feed_remind']:
            trig = f'TRIGGER;RELATED=START:PT{fh}H{fm}M'                     # that time on the feeding day
        elif e['kind'] == 'cold' and o['cold_remind']:
            d = date.fromisoformat(e['date']) - timedelta(days=1)            # that time on the day before the cold morning
            at = datetime.combine(d, datetime.min.time(), tz).replace(hour=ch, minute=cm).astimezone(timezone.utc)
            trig = 'TRIGGER;VALUE=DATE-TIME:' + at.strftime('%Y%m%dT%H%M%SZ')
        if trig: out += ['BEGIN:VALARM', 'ACTION:DISPLAY', 'DESCRIPTION:' + ics_text(e['title']), trig, 'END:VALARM']
        out.append('END:VEVENT')
    out.append('END:VCALENDAR')
    return '\r\n'.join(ics_fold(x) for x in out) + '\r\n'

def ics_response(body, filename=None):
    resp = Response(body, mimetype='text/calendar')
    resp.headers['Content-Type'] = 'text/calendar; charset=utf-8'
    resp.headers['Cache-Control'] = 'no-store'
    if filename: resp.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp

def ics_links(c, o):
    tok = ics_token(c)
    local = setting(c, 'base_url', '') or request.host_url.rstrip('/')        # the address set for labels, when there is one
    return {'local': f'{local}/cal/{tok}.ics', 'public': f'{o["public_base"]}/cal/{tok}.ics' if o['public_base'] else None}

@app.route('/api/calendar')
def calendar_preview():
    c = db(); o = ics_options(c)
    return jsonify(ics_events(c, o) | {'links': ics_links(c, o)})

@app.route('/api/calendar/settings', methods=['GET', 'PUT'])
def calendar_settings():
    c = db()
    if request.method == 'PUT':
        old = ics_saved(c)
        new = ics_clean({**old, **(request.get_json(silent=True) or {})})
        if new != old:
            set_setting(c, 'ics_options', json.dumps(new))
            what = ', '.join(k for k in ICS_DEFAULTS if new[k] != old[k])
            audit_only(c, 'setting', 'ics_options', None, None, editor(), 'Calendar choices changed: ' + what)
            c.commit()
    o = ics_saved(c)
    return jsonify(options=o, links=ics_links(c, o), days=ICS_DAYS)

@app.route('/api/calendar/new-link', methods=['POST'])
def calendar_new_link():
    c = db()
    set_setting(c, 'ics_token', secrets.token_urlsafe(18))
    audit_only(c, 'setting', 'ics_token', None, None, editor(), 'New calendar link made; the old one stopped working')
    c.commit()
    o = ics_saved(c)
    return jsonify(options=o, links=ics_links(c, o))

@app.route('/api/calendar.ics')
def calendar_ics():
    c = db(); o = ics_options(c); E = ics_events(c, o)
    body = ics_body(c, o, E, request.host_url.rstrip('/') + '/')
    return ics_response(body, None if request.args.get('download') == '0' else f'plant-record-calendar-{E["today"]}.ics')

@app.route('/cal/<path:p>')
def calendar_subscribed(p):
    """The subscribed calendar. No password (guard() lets /cal/ through), so the private token is the only key.
    Only the last part of the path counts (<token>.ics), so it works the same behind a proxy that adds or keeps a
    /cal prefix, such as Tailscale Funnel with --set-path=/cal."""
    c = db()
    name = p.rsplit('/', 1)[-1]
    if not name.endswith('.ics') or not hmac.compare_digest(name[:-4].encode(), ics_token(c).encode()): abort(404)
    o = ics_saved(c)
    E = ics_events(c, o)
    # links in the events go to the app itself, which the public address does not open (it only shares /cal/):
    # use the address set for labels, or the one this request came in on unless that is the public one
    pub = urlparse(o['public_base']).hostname if o['public_base'] else None
    base = setting(c, 'base_url', '') or ('' if pub and request.host.split(':')[0] == pub else request.host_url.rstrip('/'))
    base = base + '/' if base else ''
    return ics_response(ics_body(c, o, E, base))
