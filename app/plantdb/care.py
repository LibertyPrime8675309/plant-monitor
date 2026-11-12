"""Care log and watering, back outside in spring, getting plants ready to come inside.
Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- care log and watering (added in 1.8.0)
CARE_KINDS = {'water': 'Watered', 'check': 'Checked: still moist', 'repot': 'Repotted', 'prune': 'Pruned', 'pests': 'Treated for pests', 'note': 'Note'}
# 1.9.0: the steps for getting a plant ready to come inside are logged as care too (see PREP_METHODS)
CARE_KINDS.update({'prep_inspect': 'Inspected for pests', 'prep_potclean': 'Cleaned the pot and saucer', 'prep_rinse': 'Rinsed with water',
                   'prep_wipe': 'Wiped the leaves', 'prep_soap': 'Sprayed insecticidal soap', 'prep_oil': 'Sprayed horticultural oil',
                   'prep_alcohol': 'Dabbed pests with rubbing alcohol', 'prep_soak': 'Soaked the pot', 'prep_topsoil': 'Refreshed the top of the soil',
                   'prep_repot': 'Repotted in fresh soil'})
CARE_KINDS['prep_start'] = 'Started the move-inside checklist'     # 1.40.1: the Start button, so a plant shows as in progress before any step is done
RAIN_COUNTS_IN = 0.25          # a day with at least this much rain counts as a watering for plants in the open

def water_base_days(r):
    """How often to check a plant for water in mild weather, from its own setting or its soil moisture range."""
    if r['water_every_days']: return int(r['water_every_days']), 'set on this page'
    lo = r['soil_moisture_low']
    if lo is None: return 7, 'a typical potted plant'
    for limit, days, why in ((10, 14, 'likes to dry out completely'), (20, 10, 'likes to dry out between waterings'), (30, 7, 'likes the top of the mix to dry'),
                             (40, 5, 'likes evenly moist mix'), (101, 4, 'likes constantly moist mix')):
        if lo <= limit: return days, why
    return 7, 'a typical potted plant'

def water_weather(c, today):
    """Recent highs and rain at the home place: (average high of the last 3 days or None, {date: inches of rain})."""
    L = location(c)
    rows = c.execute('SELECT date, data FROM weather_daily WHERE loc_id=? AND date>=? AND date<? ORDER BY date',
                     (L['id'], (today - timedelta(days=21)).isoformat(), today.isoformat())).fetchall()
    highs, rain = [], {}
    for d, data in rows:
        try: x = json.loads(data)
        except ValueError: continue
        if x.get('temperature_2m_max') is not None: highs.append((d, x['temperature_2m_max']))
        pr = x.get('precipitation_sum', x.get('rain_sum'))
        if pr is not None and pr >= RAIN_COUNTS_IN: rain[d] = round(pr, 2)
    hs = [h for _, h in highs[-3:]]
    return (round(sum(hs) / len(hs)) if hs else None), rain

def water_factor(avg_high, inside):
    if inside: return 1.5, 'indoors, where the mix dries more slowly'
    if avg_high is None: return 1.0, 'no recent weather'
    for limit, f, why in ((95, .6, 'very hot'), (85, .8, 'hot'), (70, 1.0, 'warm'), (55, 1.3, 'cool'), (-99, 1.6, 'cold')):
        if avg_high >= limit: return f, f'{why} lately (highs about {temp_text(avg_high)})'
    return 1.0, ''

def water_report(c, codes=None):
    today = local_today(c)
    avg_high, rain = water_weather(c, today)
    at, at_args = plants_at(c, location(c)) if not codes else ('', [])     # 1.28.0: the plants at the place in use
    q = "SELECT * FROM plants WHERE status='active'" + at + (' AND code IN (%s)' % ','.join('?' * len(codes)) if codes else '') + ' ORDER BY code'
    plants = c.execute(q, at_args + list(codes or [])).fetchall()
    last = {}
    for code, kind, d in c.execute("SELECT plant_code, CASE WHEN kind IN ('prep_soak','prep_repot') THEN 'water' ELSE kind END AS k, MAX(done_on) "
                                   "FROM care_log WHERE kind IN ('water','check','prep_soak','prep_repot','topup','flush','waterchange') GROUP BY plant_code, k"):     # a soak or a repot waters the plant
        last.setdefault(code, {})[kind] = d
    hydro = hydro_every(c)                     # 1.56.0 (PLAN.md step 9): semi-hydro plants are topped up, water-only plants get fresh water
    out = []
    for r in plants:
        gk = grow_kind(r)
        if gk != 'Soil mix':
            action = 'topup' if gk == 'Semi-hydro' else 'waterchange'
            lw = max((d for k, d in last.get(r['code'], {}).items() if k in (('topup', 'flush', 'water') if action == 'topup' else ('waterchange', 'water'))), default=None)
            every = int(r['water_every_days']) if r['water_every_days'] else hydro[action]
            st = {'code': r['code'], 'every': every, 'base': every, 'why': 'set on this page' if r['water_every_days'] else ('a semi-hydro pot: top up the reservoir' if action == 'topup' else 'grows in water: pour out the old and add fresh'),
                  'weather': '', 'site': r['site'] or 'Outdoors', 'last_water': lw, 'last_rain': None, 'rain_in': None, 'last_check': None,
                  'action': action, 'action_word': CARE_KINDS[action], 'grow_kind': gk}
            if not lw: st.update(state='unknown', next=None, overdue=None)
            else:
                nxt = date.fromisoformat(lw) + timedelta(days=every); od = (today - nxt).days
                st.update(next=nxt.isoformat(), overdue=od, state='due' if od >= 0 else 'soon' if od == -1 else 'ok')
            out.append(st); continue
        site = r['site'] or 'Outdoors'
        inside, open_sky = site in INSIDE_SITES, site == 'Outdoors'
        base, base_why = water_base_days(r)
        f, f_why = water_factor(avg_high, inside)
        every = max(1, round(base * f))
        lw, lc = last.get(r['code'], {}).get('water'), last.get(r['code'], {}).get('check')
        lr = max((d for d in rain if open_sky and (not lw or d > lw)), default=None)
        start = max(x for x in (lw, lr) if x) if (lw or lr) else None
        st = {'code': r['code'], 'every': every, 'base': base, 'why': base_why, 'weather': f_why, 'site': site,
              'last_water': lw, 'last_rain': lr, 'rain_in': rain.get(lr) if lr else None, 'last_check': lc, 'action': 'water', 'action_word': 'Watered', 'grow_kind': 'Soil mix'}
        if not start:
            st.update(state='unknown', next=None, overdue=None)
        else:
            nxt = date.fromisoformat(start) + timedelta(days=every)
            if lc and lc >= start:                                   # checked and still moist: look again in a third of the gap
                nxt = max(nxt, date.fromisoformat(lc) + timedelta(days=max(1, round(every / 3))))
            od = (today - nxt).days
            st.update(next=nxt.isoformat(), overdue=od, state='due' if od >= 0 else 'soon' if od == -1 else 'ok')
        out.append(st)
    return {'today': today.isoformat(), 'avg_high': avg_high, 'rain': rain, 'rain_counts_in': RAIN_COUNTS_IN, 'plants': out}

def home_today(c, home_id):
    """1.58.0: today's date at a plant's home (home_id empty = the main home)."""
    r = c.execute('SELECT tz FROM locations WHERE id=?', (home_id,)).fetchone() if home_id else None
    return datetime.now(tzinfo(r[0] if r and r[0] else home_place(c)['tz'])).date()

@app.route('/api/water')
def water_api():
    return jsonify(water_report(db()))

def day_words(d):
    """'2026-10-23' -> 'Friday, Oct 23', for the change log."""
    d = date.fromisoformat(d) if isinstance(d, str) else d
    return f'{d:%A}, {d:%b} {d.day}'

@app.route('/api/care', methods=['GET', 'POST'])
def care():
    c = db()
    if request.method == 'GET':
        q, a = 'SELECT * FROM care_log WHERE 1=1', []
        if request.args.get('plant'): q += ' AND plant_code=?'; a.append(request.args['plant'])
        n = max(1, min(int(request.args.get('n', 200)), 2000))
        return jsonify([dict(x) for x in c.execute(q + ' ORDER BY done_on DESC, id DESC LIMIT ?', a + [n])])
    b = request.get_json(silent=True) or {}
    kind = b.get('kind')
    if kind not in CARE_KINDS: abort(400, 'kind must be one of: ' + ', '.join(CARE_KINDS))
    codes = b.get('plants') or ([b['plant']] if b.get('plant') else [])
    if not isinstance(codes, list) or not codes: abort(400, 'Choose at least one plant')
    codes = list(dict.fromkeys(str(x) for x in codes))[:300]
    given = str(b.get('done_on') or '')
    if given:
        try: date.fromisoformat(given)
        except ValueError: abort(400, 'done_on must look like 2026-10-23')
        if given > local_today(c).isoformat(): abort(400, 'That date is in the future')
    note = str(b.get('note') or '').strip()[:500]
    if kind == 'note' and not note: abort(400, 'Write the note')
    who, ids, skipped = editor(), [], []
    tz_of = {}
    for code in codes:
        r = plant_row(c, code)
        # 1.58.0: "today" is the day where the plant lives (a Nevada City plant logged late on a Texas evening keeps its own date)
        hid = r['home_id'] if 'home_id' in r.keys() else None
        if hid not in tz_of: tz_of[hid] = home_today(c, hid).isoformat()
        day = given or tz_of[hid]
        # 1.21.0: a plant is watered at most once a day, so "Water all" and a second press skip it instead of logging it twice
        if kind == 'water' and c.execute("SELECT 1 FROM care_log WHERE plant_code=? AND kind='water' AND done_on=?", (r['code'], day)).fetchone():
            skipped.append(r['code']); continue
        ids.append(c.execute('INSERT INTO care_log(plant_code,kind,done_on,note,created_by,created_at) VALUES(?,?,?,?,?,?)',
                             (r['code'], kind, day, note, who, now())).lastrowid)
        audit_only(c, 'care', 'care_log', None, f'{CARE_KINDS[kind]} {day}' + (f': {note}' if note else ''), who,
                   CARE_KINDS[kind] + (f': {note}' if note else '') + ('' if day == tz_of[hid] else f' (for {day_words(day)})'), r['id'], r['code'])
    c.commit()
    return jsonify(ids=ids, skipped=skipped, water=water_report(c, codes)['plants']), 201

@app.route('/api/care/<int:i>', methods=['DELETE'])
def care_one(i):
    c = db()
    old = c.execute('SELECT * FROM care_log WHERE id=?', (i,)).fetchone()
    if not old: abort(404, 'entry not found')
    c.execute('DELETE FROM care_log WHERE id=?', (i,))
    r = c.execute('SELECT id FROM plants WHERE code=?', (old['plant_code'],)).fetchone()
    audit_only(c, 'care', 'care_log', f"{CARE_KINDS.get(old['kind'], old['kind'])} {old['done_on']}", None, editor(),
               ('Undone right after it was logged: ' if request.args.get('undo') == '1' else 'Removed from the care log: ')     # ?undo=1: the Undo button (prototype)
               + CARE_KINDS.get(old['kind'], old['kind']) + ', ' + day_words(old['done_on']), r['id'] if r else None, old['plant_code'])
    c.commit()
    return jsonify(ok=True)

def runs_as():
    """1.12.1: which user the app runs as inside its container (set by start.py), for the owner's Debug window."""
    if (getattr(g, 'user', None) or {}).get('role') != 'owner': return None
    v = os.environ.get('PLANTDB_RUNS_AS', '')
    if v == 'user': return {'root': False, 'text': 'Its own user, without special privileges'}
    if v.startswith('root:'): return {'root': True, 'text': 'Root inside its container, because ' + v[5:]}
    return None

@app.route('/api/version')
def version(): return jsonify(version=APP_VERSION)

# ---------------------------------------------------------------- back outside in spring (prototype: proto/move-outside)
# Plants that are inside now (Indoors, Garage or shed), and whether the nights in the 7-day forecast are warm enough for each
# to go back out. Levels, best first:
#   ready  every night at or above the plant's ideal low
#   safe   no night within FROST_MARGIN of its damage point, but some nights cooler than it likes
#   early  the forecast is safe, but the place's weather history says colder nights usually still come at this time of year
#   wait   a night in the forecast is below its damage point, or within FROST_MARGIN of it
# Reads only; moving a plant uses the existing /api/plants/<code>/site.
BO_LEVELS = ('ready', 'safe', 'early', 'wait')
BO_LOWS = {}                 # place id -> (time worked out, {date: low})

def bo_daily_lows(c, L):
    hit = BO_LOWS.get(L['id'])
    if hit and time.time() - hit[0] < 6 * 3600: return hit[1]
    try: rows = c.execute("SELECT date, json_extract(data, '$.temperature_2m_min') FROM weather_daily WHERE loc_id=? AND kind='observed'", (L['id'],)).fetchall()
    except sqlite3.OperationalError:            # an SQLite without JSON functions
        rows = [(d, (json.loads(x) if x else {}).get('temperature_2m_min')) for d, x in c.execute("SELECT date, data FROM weather_daily WHERE loc_id=? AND kind='observed'", (L['id'],))]
    lows = {d: t for d, t in rows if isinstance(t, (int, float))}
    BO_LOWS[L['id']] = (time.time(), lows)
    return lows

def bo_md(d):
    """A date as 'MM-DD' (Feb 29 counts as Feb 28), so days of different years compare."""
    return '02-28' if d[5:] == '02-29' else d[5:]

def bo_usual(lows, t):
    """From the daily history, for nights below t°F: the day after the last one each spring (January to June) and the first one
    each autumn (July to December). Medians over the years with enough days (150 in that half), and the latest spring date.
    None for a half with fewer than 3 such years. A spring with no night below t counts as '01-01'; autumn medians only count
    years that had one, and need at least half the years to have one."""
    halves = {}
    for d, v in lows.items():
        y, m = int(d[:4]), int(d[5:7])
        halves.setdefault((y, 'spring' if m <= 6 else 'autumn'), []).append((d, v))
    spring, autumn, years_a = [], [], 0
    for (y, h), vals in halves.items():
        if len(vals) < 150: continue
        cold = sorted(d for d, v in vals if v < t)
        if h == 'spring':
            if not cold: spring.append('01-01')
            else:
                nxt = (datetime.strptime(cold[-1], '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
                spring.append(bo_md(nxt) if nxt[5:7] <= '06' else '07-01')
        else:
            years_a += 1
            if cold: autumn.append(bo_md(cold[0]))
    med = lambda xs: sorted(xs)[(len(xs) - 1) // 2] if xs else None
    out = {}
    if len(spring) >= 3:
        out |= {'safe': med(spring), 'safe_latest': max(spring), 'spring_years': len(spring), 'spring_cold': sum(1 for x in spring if x != '01-01')}
    if years_a >= 3:
        out |= {'first': med(autumn) if len(autumn) * 2 >= years_a else None, 'autumn_years': years_a}
    return out or None

BO_PORCH_DAYS = 7           # a week on the porch, out of full sun, before the move to the summer spot

def bo_porch_state(c):
    try: return json.loads(setting(c, 'bo_porch', '{}') or '{}')
    except ValueError: return {}

def bo_porch_list(c, today, photo):
    """Plants moved to the porch with "Moved to the porch" that are still on it, and when each is due its move to the summer spot."""
    out = []
    for code, v in sorted(bo_porch_state(c).items()):
        r = c.execute("SELECT * FROM plants WHERE code=? AND status='active'", (code,)).fetchone()
        if not r or r['site'] != 'Covered porch': continue          # it has moved on: nothing to remind about
        try: on = datetime.strptime(v.get('on', ''), '%Y-%m-%d').date()
        except ValueError: continue
        due = on + timedelta(days=BO_PORCH_DAYS)
        out.append({'code': code, 'name': r['common_name'], 'photo': photo(r['id']), 'on': on.isoformat(), 'due': due.isoformat(),
                    'days': (today - on).days, 'is_due': today >= due, 'by': v.get('by')})
    out.sort(key=lambda p: (p['due'], p['code']))
    return out

def outside_report(c):
    L = location(c)
    fc = loc_json(c, L['id'], 'forecast')
    today = local_today(c)
    td, tmd = today.isoformat(), bo_md(today.isoformat())
    nights = [{'date': d['date'], 'low': d['low']} for d in (fc.get('days') or []) if d.get('date', '') >= td and d.get('low') is not None][:7]
    spring = today.month <= 6
    lows = bo_daily_lows(c, L)
    usual_at = {}
    photo = lambda pid: (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (pid,)).fetchone() or [None])[0]
    at, at_args = plants_at(c, L)                  # 1.28.0: only the plants at this home
    rows = c.execute("SELECT * FROM plants WHERE status='active'" + at + " ORDER BY code", at_args).fetchall()
    out = []
    for r in rows:
        if (r['site'] or 'Outdoors') not in INSIDE_SITES: continue
        dmg, ideal = r['temp_damage_below'], r['temp_ideal_low']
        p = {'code': r['code'], 'name': r['common_name'], 'photo': photo(r['id']), 'site': r['site'], 'plan': r['winter_plan'],
             'damage': dmg, 'lethal': r['temp_lethal_below'], 'ideal': ideal, 'level': None}
        if dmg is None and ideal is None: out.append(p); continue
        safe_at = dmg + FROST_MARGIN if dmg is not None else ideal
        like = ideal if ideal is not None and ideal > safe_at else safe_at
        if safe_at not in usual_at: usual_at[safe_at] = bo_usual(lows, safe_at)
        u = usual_at[safe_at]
        p |= {'safe_at': safe_at, 'like': like, 'usual': u}
        if not nights: out.append(p); continue
        cold = next((n for n in nights if n['low'] < safe_at), None)
        cool = [n for n in nights if n['low'] < like]
        p |= {'coldest': min(nights, key=lambda n: (n['low'], n['date'])), 'first_cold': cold, 'cool_nights': len(cool)}
        if cold: p['level'] = 'wait'
        else:
            p['level'] = 'safe' if cool else 'ready'
            if u and spring and u.get('safe') and tmd < u['safe']:
                p |= {'level': 'early', 'why': 'spring'}
            elif u and not spring and u.get('first') and tmd >= bo_md((datetime.strptime('2001-' + u['first'], '%Y-%m-%d') - timedelta(days=7)).strftime('%Y-%m-%d')):
                p |= {'level': 'early', 'why': 'autumn'}
        out.append(p)
    porch = bo_porch_list(c, today, photo)
    rank = {k: i for i, k in enumerate(BO_LEVELS)}
    out.sort(key=lambda p: (rank.get(p['level'], 9), (p['name'] or '').lower(), p['code']))
    return {'place': L['name'], 'fetched_at': fc.get('fetched_at'), 'today': td, 'season': 'spring' if spring else 'autumn', 'margin': FROST_MARGIN,
            'nights': nights, 'plants': out, 'porch': porch, 'history_days': len(lows),
            'counts': {k: sum(1 for p in out if p['level'] == k) for k in BO_LEVELS} | {'unknown': sum(1 for p in out if not p['level'])}}

@app.route('/api/outside')
def outside_api():
    return jsonify(outside_report(db()))

@app.route('/api/outside/porch', methods=['POST'])
def outside_porch():
    """'start': move a plant to the covered porch (out of full sun, so leaves that grew indoors do not scorch) and remind
    in a week; 'clear': leave it on the porch and stop the reminder. Leaving the porch needs nothing: the reminder follows the Location."""
    c = db()
    b = request.get_json(silent=True) or {}
    r = plant_row(c, str(b.get('code', '')))
    act = b.get('action')
    if act not in ('start', 'clear'): abort(400, "action must be 'start' or 'clear'")
    keep = {k: v for k, v in bo_porch_state(c).items() if k != r['code']}
    if act == 'start':
        apply_changes(c, r, {'site': 'Covered porch'}, editor(), 'update', 'Moved to covered porch (sun protection first)')
        keep[r['code']] = {'on': local_today(c).isoformat(), 'by': editor()}
    else:
        audit_only(c, 'care', 'porch', None, 'stay', editor(), 'Staying on the porch: reminder to move it to its summer spot turned off', r['id'], r['code'])
    set_setting(c, 'bo_porch', json.dumps(keep))
    c.commit()
    return jsonify(outside_report(c))

# ---------------------------------------------------------------- getting plants ready to come inside (added in 1.9.0)
# Ten ways to keep outdoor pests out of the house, rated for each plant from what is chosen on its page (leaf type,
# pot size, pests found) and what the app knows (health, how dry it likes its soil, the pests it often gets, the weather).
PREP_METHODS = [
    {'key': 'inspect', 'title': 'Inspect for pests', 'steps': [
        'Look at the undersides of the leaves, where the leaves join the stems, and the new growth.',
        'Run your fingers over the leaves. Sticky leaves mean aphids, scale or mealybugs are feeding.',
        'Mite check: hold a white sheet of paper under the leaves and tap the plant. Specks that crawl are mites.',
        'Lift the pot and look underneath it and in the saucer.',
        'Use your phone camera\'s zoom or a lighted magnifier, or send Claude close-up photos of the leaf undersides.',
        'Tick what you found under "Pests you found" on the plant\'s page. If you found nothing, tick nothing: the other methods still work as a precaution.']},
    {'key': 'potclean', 'title': 'Clean the pot and saucer', 'steps': [
        'Wear gloves: scorpions, spiders and other biters hide under pots.',
        'Lift the pot, look underneath, and knock off anything clinging to the bottom.',
        'Scrub the outside of the pot, the bottom and the drainage holes with soapy water and a brush.',
        'Empty and wash the saucer, and check under the rim of the pot.']},
    {'key': 'rinse', 'title': 'Rinse with water', 'steps': [
        'Do it outdoors in the morning, so the leaves dry by evening.',
        'Spray the plant hard with the hose: the undersides of the leaves first, then the tops and the stems.',
        'Hold delicate stems while you spray, and let the pot drain.']},
    {'key': 'wipe', 'title': 'Wipe the leaves', 'steps': [
        'Dip a soft cloth in lukewarm water with a drop of mild dish soap, and wring it out.',
        'Support each leaf with one hand and wipe the top, then the underside, from the stem to the tip.',
        'Rinse the cloth often, then wipe the leaves again with plain water.',
        'This also removes dust, so the leaves get more light indoors.']},
    {'key': 'soap', 'title': 'Spray insecticidal soap', 'repeat': True, 'steps': [
        'Use a ready-to-use insecticidal soap (potassium salts of fatty acids), or mix a concentrate as its label says.',
        'Test it on one leaf first and wait 2 days. If that leaf turns brown, use another method.',
        'Spray in the shade, between 50 and 90°F, until the tops and undersides of the leaves are wet. It only kills the pests it touches.',
        'Spray again every 5 to 7 days, 2 or 3 times in all, because it does not kill eggs.',
        'Press "Done today" after each round, and the Today page reminds you of the next one.']},
    {'key': 'oil', 'title': 'Spray horticultural or neem oil', 'repeat': True, 'steps': [
        'Use it outdoors only (neem oil smells), in the shade, between 50 and 90°F, and never on a plant that is dry or wilting.',
        'Test it on one leaf first and wait 2 days.',
        'Mix it as its label says and wet every surface, especially the stems and the undersides of the leaves, where scale and eggs sit.',
        'Spray again in 7 to 10 days if you still find live scale.']},
    {'key': 'alcohol', 'title': 'Dab with rubbing alcohol', 'steps': [
        'Dip a cotton swab in 70% rubbing alcohol.',
        'Touch each mealybug or scale insect with it. Scale may need a gentle scrape with a fingernail afterwards.',
        'On soft or thin leaves, test one spot first and wait a day.',
        'Check again every few days and dab any new ones.']},
    {'key': 'soak', 'title': 'Soak the pot', 'steps': [
        'Outdoors, choose a bucket or tub a little wider than the pot. Plain water works.',
        'Lower the pot in until the water just covers the soil.',
        'Leave it for 15 to 30 minutes. Ants, pill bugs and earwigs climb out or drown.',
        'If they are fire ants, wear gloves and stand back: they swarm up the pot.',
        'Lift it out and let it drain completely. This counts as a watering, so the watering reminder starts again from today.']},
    {'key': 'topsoil', 'title': 'Refresh the top of the soil', 'steps': [
        'Let the top of the soil dry a little first.',
        'Scrape off the top 1 to 2 inches of soil with a spoon, away from the stems, and bag it for the trash.',
        'Fill back up with fresh bagged potting mix, or with coarse sand or grit, which fungus gnats cannot lay eggs in.',
        'Water lightly.']},
    {'key': 'repot', 'title': 'Repot in fresh soil', 'steps': [
        'Water the plant the day before.',
        'Outdoors, slide the plant out of its pot and gently tease the old soil off the roots. Bag the old soil for the trash.',
        'Rinse the roots in a bucket of water. White cottony patches are root mealybugs. Trim mushy, dark roots with clean scissors.',
        'Use a new pot, or clean the old one without bleach: scrub it with hot soapy water and a brush, rinse it, and let it dry in the sun for a day. '
        'For extra cleaning, soak it for 10 minutes in 3% hydrogen peroxide from the pharmacy, straight from the bottle, then rinse. Never mix peroxide with vinegar or other cleaners.',
        'Repot in fresh bagged potting mix that suits the plant (see its Water and soil section), and water it in.',
        'Keep it out of strong light for a week while the roots recover.']},
]
PREP_KEYS = [m['key'] for m in PREP_METHODS]
PREP_TITLE = {m['key']: m['title'] for m in PREP_METHODS}
PREP_RANK = {'Best': 4, 'Good': 3, 'Use with care': 2, 'Not needed': 1, 'Not for this plant': 0}
PREP_WINDOW_DAYS = 75           # prep steps logged within this many days count towards this move inside
KEEP_APART_DAYS = 21            # keep plants that came in apart from long-term houseplants this long
KEEP_APART_AFTER_TREATMENT = 14
SOFT_PESTS = {'Spider mites', 'Mealybugs', 'Aphids', 'Whiteflies', 'Thrips'}
SOIL_PESTS = {'Ants', 'Pill bugs or earwigs', 'Slugs or snails'}

def prep_weather(c):
    """Today's forecast high and low at home, and what that means for spraying."""
    try:
        fc = loc_json(c, location(c)['id'], 'forecast')
        today = local_today(c).isoformat()
        d = next((x for x in (fc.get('days') or []) if x.get('date') == today), None)
    except Exception:
        d = None
    if not d or d.get('high') is None: return {'high': None, 'low': None, 'spray': None}
    hi, lo = round(d['high']), round(d['low']) if d.get('low') is not None else None
    T = temp_text          # 1.47.0: in the person's unit
    if hi >= 90: note = f'Today reaches {T(hi)}: spray early in the morning or in the evening, in the shade, or wait for a cooler day.'
    elif hi < 55: note = f'Today only reaches {T(hi)}: sprays work poorly in the cold, so wait for a day between {T(55, unit=False)} and {T(90)} if you can.'
    else: note = f'Today ({T(lo, unit=False)} to {T(hi)}) is fine for spraying in the shade.' if lo is not None else f'Today (up to {T(hi)}) is fine for spraying in the shade.'
    return {'high': hi, 'low': lo, 'spray': note}

def prep_rate(r, pests, wx):
    """Each method's rating and the reason, in plain words, for one plant."""
    lt, ps = r['leaf_type'] or '', r['pot_size'] or ''
    watch = ' '.join(x.lower() for x in (r['pests_watch'] or '').split('\n'))
    weak = r['health_rating'] in ('Poor', 'Critical')
    succ, fern, fuzzy, palm, water, big = (lt == 'Succulent or cactus', lt == 'Fern fronds', lt == 'Fuzzy or velvety leaves',
                                           lt == 'Palm fronds', lt == 'Grows in water', lt == 'Large leaves')
    dry = succ or (r['soil_moisture_high'] is not None and r['soil_moisture_high'] <= 35)
    soft, soil = sorted(pests & SOFT_PESTS, key=PESTS.index), sorted(pests & SOIL_PESTS, key=PESTS.index)
    words = lambda xs: ', '.join(xs[:-1]) + ' and ' + xs[-1] if len(xs) > 1 else (xs[0] if xs else '')
    lower = lambda xs: words([x.lower() for x in xs])
    mites_prone = 'spider mite' in watch or palm
    out = {}
    def put(k, rating, reason): out[k] = (rating, reason)

    put('inspect', 'Best', 'Do this first: what you find decides which of the other methods are needed.')
    put('potclean', 'Good' if water else 'Best', 'Wash the jar and give it fresh water.' if water else
        'Slugs, roaches, ants and scorpions hide under pots and in saucers.')

    if succ: put('rinse', 'Not for this plant', 'Water left in the rosettes or crowns can rot them. Use a soft dry brush, and rubbing alcohol for mealybugs.')
    elif fern: put('rinse', 'Best', 'Plain water is the safest treatment for ferns, which soaps and oils often damage.')
    elif fuzzy: put('rinse', 'Use with care', 'Rinse gently in the morning so the leaves dry fast; water can mark fuzzy leaves.')
    elif water: put('rinse', 'Good', 'Rinse the leaves and roots gently and give it fresh water.')
    elif soft: put('rinse', 'Best', f'A hard spray of water knocks off most of the {lower(soft)}.')
    elif mites_prone: put('rinse', 'Best', ('Palms' if palm else 'This plant') + ' often get spider mites, and rinsing the undersides of the leaves is the best prevention.')
    else: put('rinse', 'Good', 'Quick insurance against pests too small to see.')

    if big or water: put('wipe', 'Best' if big else 'Good', 'Big leaves are quick to wipe, and it removes dust so they get more light indoors.' if big else 'Wipe the leaves gently with a damp cloth.')
    elif palm: put('wipe', 'Good', 'Wipe the leaflets top and bottom if you have time; rinsing is quicker.')
    elif fuzzy: put('wipe', 'Use with care', 'Brush the leaves with a soft dry paintbrush instead of a wet cloth.')
    elif succ: put('wipe', 'Not for this plant', 'Wiping rubs off the powdery coating that protects the leaves. Use a soft dry brush.')
    elif fern: put('wipe', 'Not for this plant', 'The fronds break easily. Rinse instead.')
    elif lt == 'Small or many leaves': put('wipe', 'Not needed', 'Too many small leaves to wipe one by one; rinsing does the same job.')
    else: put('wipe', 'Good', 'Choose the leaf type above to rate this properly.')

    if soft or 'Scale' in pests:
        found = soft + (['Scale'] if 'Scale' in pests else [])
        if fern: put('soap', 'Use with care', f'It kills {lower(found)}, but ferns are often damaged by soap: test one frond and wait 2 days, or keep rinsing with water.')
        elif succ: put('soap', 'Use with care', f'It kills {lower(found)}; test one leaf first. For a few mealybugs, rubbing alcohol is gentler.')
        elif weak: put('soap', 'Use with care', f'It kills {lower(found)}, but this plant is already struggling: test one leaf and wait 2 days.')
        else: put('soap', 'Best', f'Kills {lower(found)} on contact. Spray 2 or 3 times, 5 to 7 days apart.')
    elif mites_prone or 'mealybug' in watch or 'aphid' in watch:
        put('soap', 'Not needed' if (fern or succ) else 'Good', 'Only if you find pests.' if (fern or succ) else
            'A precaution: this plant often gets ' + lower([p for p in ('Spider mites', 'Mealybugs', 'Aphids') if p.lower().rstrip('s') in watch or (p == 'Spider mites' and palm)]) + '.')
    else: put('soap', 'Not needed', 'Only if you find soft-bodied pests such as mites, aphids or mealybugs.')

    if succ or fuzzy or fern:
        put('oil', 'Not for this plant', 'Oil can burn ' + ('succulents' if succ else 'fuzzy leaves' if fuzzy else 'fern fronds') + '.')
    elif 'Scale' in pests: put('oil', 'Use with care' if weak else 'Best', 'Smothers scale and its eggs, which soap misses.' + (' This plant is struggling, so test one leaf first.' if weak else ''))
    elif {'Mealybugs', 'Spider mites'} & pests: put('oil', 'Use with care' if weak else 'Good', 'Also smothers eggs: use it if soap alone does not clear them.')
    else: put('oil', 'Not needed', 'Only for scale, or eggs that soap does not clear.')

    if {'Mealybugs', 'Scale'} & pests:
        what = lower(sorted({'Mealybugs', 'Scale'} & pests, key=PESTS.index))
        put('alcohol', 'Best' if succ else 'Use with care' if fern else 'Good',
            f'The gentlest way to clear {what} from succulents.' if succ else f'Quick for a few {what} you can reach; spray if there are many.')
    else: put('alcohol', 'Not needed', 'Only for mealybugs or scale.')

    if water: put('soak', 'Not needed', 'It already grows in water; change the water instead.')
    elif dry: put('soak', 'Not for this plant', 'A long soak keeps its roots wet for days. Refresh the top of the soil instead, or repot if there are pests in the soil.')
    elif ps.startswith('Large'): put('soak', 'Use with care', 'Too big for a bucket. Water it slowly and heavily instead, and watch what crawls out.')
    elif soil: put('soak', 'Best', f'Drives the {lower(soil)} out of the soil.' + ('' if ps else ' Choose the pot size above.'))
    else: put('soak', 'Good', 'Insurance against ants and other pests hiding in the soil, and it waters the plant.' + ('' if ps else ' Only if the pot fits in a bucket or tub.'))

    if water: put('topsoil', 'Not needed', 'It grows in water.')
    elif 'Fungus gnats' in pests or 'Ants' in pests:
        put('topsoil', 'Best', ('Fungus gnats lay their eggs' if 'Fungus gnats' in pests else 'Ants nest') + ' in the top inch or two of soil.')
    elif succ: put('topsoil', 'Good', 'Fresh grit on top keeps the base dry and fungus gnats away.')
    elif (r['soil_moisture_high'] or 0) >= 60: put('topsoil', 'Good', 'It likes damp soil, which draws fungus gnats indoors; a fresh top layer helps.')
    else: put('topsoil', 'Good', 'Quick, and removes eggs and debris from the surface.')

    if water: put('repot', 'Good', 'Rinse the roots and refill a clean jar with fresh water.')
    elif 'Root mealybugs' in pests: put('repot', 'Use with care' if weak else 'Best', 'Root mealybugs live on the roots; only fresh soil clears them.' + (' It is struggling already, so be gentle.' if weak else ''))
    elif soil or 'Fungus gnats' in pests: put('repot', 'Use with care' if weak else 'Good', 'Only if soaking or a fresh top layer did not clear them; repotting adds stress just as it loses light.')
    elif weak: put('repot', 'Not needed', 'It is already struggling, and repotting adds stress. Wait until spring.')
    else: put('repot', 'Not needed', 'Repotting now adds stress just as it loses light. Wait until spring unless you find pests in the soil.')

    if wx.get('spray'):
        for k in ('soap', 'oil'):
            rt, why = out[k]
            if PREP_RANK[rt] >= 2: out[k] = (rt, why + ' ' + wx['spray'])
    return out

def prep_moved_in(c, r):
    """The day the plant last moved to an inside Location, from its change log, or None."""
    a = c.execute("SELECT changed_at FROM audit_log WHERE plant_id=? AND field='site' AND new_value IN (%s) ORDER BY id DESC LIMIT 1"
                  % ','.join('?' * len(INSIDE_SITES)), [r['id']] + INSIDE_SITES).fetchone()
    if not a: return None
    tz = tzinfo(location(c)['tz'])
    return datetime.strptime(a[0], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(tz).date()

def prep_plan(c, r, wx, log=None, with_steps=False):
    """Everything about one plant's move inside: ratings, what has been done, its status and the next step."""
    today = local_today(c)
    since = (today - timedelta(days=PREP_WINDOW_DAYS)).isoformat()
    if log is None:
        log = [dict(x) for x in c.execute("SELECT * FROM care_log WHERE plant_code=? AND kind LIKE 'prep_%' AND done_on>=? ORDER BY done_on, id", (r['code'], since))]
    done = {k: sorted(x['done_on'] for x in log if x['kind'] == 'prep_' + k) for k in PREP_KEYS}
    pests = {x for x in (r['pests_found'] or '').split('\n') if x in PESTS}
    rates = prep_rate(r, pests, wx)
    methods = []
    for m in PREP_METHODS:
        rt, why = rates[m['key']]
        d = done[m['key']]
        rounds_needed = 2 if m.get('repeat') and rt == 'Best' else 1
        due = None
        if m.get('repeat') and d and len(d) < rounds_needed:
            due = (date.fromisoformat(d[-1]) + timedelta(days=5)).isoformat()
        x = {'key': m['key'], 'title': m['title'], 'rating': rt, 'rank': PREP_RANK[rt], 'reason': why, 'done': d,
             'rounds': rounds_needed, 'complete': len(d) >= rounds_needed, 'next_due': due}
        if with_steps: x['steps'] = m['steps']
        methods.append(x)
    site = r['site'] or 'Outdoors'
    inside = site in INSIDE_SITES
    moved = prep_moved_in(c, r) if inside else None
    started = [x['done_on'] for x in log if x['kind'] == 'prep_start']
    start = date.fromisoformat(max(started)) if started else None
    # 1.40.1: a plant already inside can go through the checklist too (a new plant from a store, or one brought in without a check)
    check_inside = inside and start is not None and (moved is None or start >= moved)
    treat = [x['done_on'] for x in log if x['kind'] in ('prep_soap', 'prep_oil', 'prep_alcohol', 'prep_repot')]
    keep = None
    if moved or check_inside:
        keep = max(d for d in (moved, start if check_inside else None) if d) + timedelta(days=KEEP_APART_DAYS)
        if pests and treat:
            keep = max(keep, date.fromisoformat(max(treat)) + timedelta(days=KEEP_APART_AFTER_TREATMENT))
    todo = [x for x in methods if x['rating'] == 'Best' and not x['complete']]
    nxt_key = None
    def next_step():
        """The next step to do, and the method to log for it when it can be done today (None when it is a later round)."""
        if not done['inspect']: return 'Inspect it for pests.', 'inspect'
        first = next((x for x in todo if not x['next_due']), None)
        if first: return f'Next: {first["title"].lower()}.', first['key']
        x = todo[0]; dd = date.fromisoformat(x['next_due'])
        return f'{x["title"]} again on or after {dd:%A}, {dd:%b} {dd.day} (round {len(x["done"]) + 1}).', (x['key'] if dd <= today else None)
    if inside and check_inside and (todo or not done['inspect']):
        status = 'doing'; nxt, nxt_key = next_step()
        if not any(done.values()): nxt = 'Started. Inspect it for pests first.'
    elif inside:
        if keep and today <= keep: status, nxt = 'apart', f'Keep it apart from your other houseplants until {keep:%A}, {keep:%b} {keep.day}, and check it at every watering.'
        else: status, nxt = 'settled', 'Inside and settled. Check it at every watering.'
    elif not any(done.values()):
        if start: status, nxt, nxt_key = 'doing', 'Started. Inspect it for pests first.', 'inspect'
        else: status, nxt, nxt_key = 'todo', 'Start by inspecting it for pests.', 'inspect'
    elif not done['inspect'] or todo:
        status = 'doing'; nxt, nxt_key = next_step()
    else: status, nxt = 'ready', 'Ready to come inside. Change its Location (or press Moved indoors) when you bring it in.'
    return {'code': r['code'], 'name': r['common_name'], 'site': site, 'winter_plan': r['winter_plan'], 'health': r['health_rating'],
            'leaf_type': r['leaf_type'] or '', 'pot_size': r['pot_size'] or '', 'pests_found': sorted(pests, key=PESTS.index),
            'watch': [x for x in (r['pests_watch'] or '').split('\n') if x.strip()],
            'methods': methods, 'best': [x['title'] for x in methods if x['rating'] == 'Best'],
            'status': status, 'next': nxt, 'next_key': nxt_key, 'next_word': CARE_KINDS['prep_' + nxt_key] if nxt_key else None,
            'started': start.isoformat() if start else None, 'inside': inside,
            'moved_in': moved.isoformat() if moved else None, 'keep_until': keep.isoformat() if keep else None,
            'done_count': sum(1 for x in methods if x['done']), 'log': log}

PREP_STATUS = {'todo': 'Not started', 'doing': 'In progress', 'ready': 'Ready to come inside', 'apart': 'Inside, kept apart', 'settled': 'Inside and settled'}

@app.route('/api/prep')
def prep_list():
    """Plants coming inside this winter (winter plan "Move indoors"), or every plant with ?all=1."""
    c = db()
    wx = prep_weather(c)
    since = (local_today(c) - timedelta(days=PREP_WINDOW_DAYS)).isoformat()
    logs = {}
    for x in c.execute("SELECT * FROM care_log WHERE kind LIKE 'prep_%' AND done_on>=? ORDER BY done_on, id", (since,)):
        logs.setdefault(x['plant_code'], []).append(dict(x))
    q = "SELECT * FROM plants WHERE status='active'" + ('' if request.args.get('all') == '1' else " AND (winter_plan='Move indoors' OR code IN (SELECT DISTINCT plant_code FROM care_log WHERE kind LIKE 'prep_%' AND done_on>=?))") + ' ORDER BY code'
    rows = c.execute(q, () if request.args.get('all') == '1' else (since,)).fetchall()
    photo = lambda pid: (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (pid,)).fetchone() or [None])[0]
    plants = []
    for r in rows:
        p = prep_plan(c, r, wx, logs.get(r['code'], []))
        p['photo'] = photo(r['id']); p['log'] = [{'id': x['id'], 'kind': x['kind'], 'done_on': x['done_on']} for x in p['log']]   # 1.40.1: for Undo on the Coming inside page
        plants.append(p)
    counts = {k: sum(1 for p in plants if p['status'] == k) for k in PREP_STATUS}
    return jsonify(weather=wx, status_words=PREP_STATUS, counts=counts, plants=plants,
                   methods=[{'key': m['key'], 'title': m['title'], 'steps': [temps_in_text(x) for x in m['steps']]} for m in PREP_METHODS],   # 1.47.0: the °F in the steps read in the person's unit
                   keep_apart_days=KEEP_APART_DAYS)

@app.route('/api/plants/<code>/prep')
def prep_one(code):
    c = db()
    p = prep_plan(c, plant_row(c, code), prep_weather(c), with_steps=True)
    p.update(status_word=PREP_STATUS[p['status']], options={'leaf_types': LEAF_TYPES, 'pot_sizes': POT_SIZES, 'pests': PESTS})
    return jsonify(p)

@app.route('/api/plants/<code>/prep-traits', methods=['POST'])
def prep_traits(code):
    """Saves the leaf type, pot size and pests found, as a new page version, and returns the new ratings."""
    c = db()
    r = plant_row(c, code)
    b = request.get_json(silent=True) or {}
    f = {}
    if 'leaf_type' in b: f['leaf_type'] = str(b['leaf_type'] or '')
    if 'pot_size' in b: f['pot_size'] = str(b['pot_size'] or '')
    if 'pests_found' in b:
        got = b['pests_found'] if isinstance(b['pests_found'], list) else []
        f['pests_found'] = '\n'.join(x for x in PESTS if x in got)
    if not f: abort(400, 'Nothing to save')
    note = None
    if 'pests_found' in f: note = 'Pests found: ' + (', '.join(f['pests_found'].split('\n')) if f['pests_found'] else 'none')
    apply_changes(c, r, f, editor(), 'update', note)
    c.commit()
    p = prep_plan(c, plant_row(c, code), prep_weather(c), with_steps=True)
    p.update(status_word=PREP_STATUS[p['status']], options={'leaf_types': LEAF_TYPES, 'pot_sizes': POT_SIZES, 'pests': PESTS},
             version=plant_row(c, code)['version'])
    return jsonify(p)
