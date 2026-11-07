"""Prototype (proto/turn-pots): turn the pots. A plant by a window grows toward the light and leans; a quarter turn every week
or two keeps it straight and even. This lists the pots due for a turn, from the "Turned the pot" entries in the care log.

Which plants: active plants at the place in use that are Indoors or on the Covered porch (light from one side), except those in
a grow-light spot whose light shines from above. Each plant can be switched on or off by hand ("turn_choice" in settings, JSON
{code: 'on' | 'off'}; a choice that matches the usual rule is dropped). How often: "turn_every_days" in settings (default 14).
Nothing else is stored: a turn is a care_log row of kind 'turn', logged with the usual POST /api/care."""
from .core import *   # noqa: F401,F403
from .care import CARE_KINDS

CARE_KINDS['turn'] = 'Turned the pot'          # the same dict care.py checks, so POST /api/care accepts kind 'turn'
TURN_SITES = ('Indoors', 'Covered porch')     # light comes from one side here; out in the open the sun goes round the plant
TURN_EVERY_DEFAULT = 14
TURN_EVERY_CHOICES = (7, 10, 14, 21, 30)

def turn_every(c):
    try: n = int(setting(c, 'turn_every_days', TURN_EVERY_DEFAULT))
    except (TypeError, ValueError): n = TURN_EVERY_DEFAULT
    return n if n in TURN_EVERY_CHOICES else TURN_EVERY_DEFAULT

def turn_choices(c):
    try: d = json.loads(setting(c, 'turn_choice', '{}') or '{}')
    except ValueError: d = {}
    return {str(k): v for k, v in d.items() if v in ('on', 'off')} if isinstance(d, dict) else {}

def turn_overhead(c):
    """Plant codes in a grow-light spot whose light shines down from above, so they get even light and need no turning."""
    out = {}
    for code, data, spot in c.execute('SELECT a.plant_code, l.data, s.name FROM light_assign a JOIN light_spots s ON s.id=a.spot_id JOIN lights l ON l.id=s.light_id'):
        try: d = json.loads(data or '{}')
        except ValueError: d = {}
        if d.get('direction') == 'down': out[code] = spot
    return out

def turn_auto(r, overhead):
    """The usual rule: (included, reason words)."""
    site = r['site'] or 'Outdoors'
    if site not in TURN_SITES: return False, f'{site}: the light comes from all round'
    if r['code'] in overhead: return False, f'Under a grow light from above ({overhead[r["code"]]})'
    return True, ('By a window indoors' if site == 'Indoors' else 'On the covered porch: light from the open side')

def turn_report(c, code=None):
    """code: just that plant (its own page), so the page does not wait on the whole list."""
    today = local_today(c)
    every, choice, overhead = turn_every(c), turn_choices(c), turn_overhead(c)
    at, at_args = plants_at(c, location(c))
    if code: at, at_args = ' AND code=?', [code]
    rows = c.execute("SELECT * FROM plants WHERE status='active'" + at + ' ORDER BY code', at_args).fetchall()
    last = dict(c.execute("SELECT plant_code, MAX(done_on) FROM care_log WHERE kind='turn' GROUP BY plant_code"))
    areas = dict(c.execute('SELECT id, name FROM areas'))
    spots = dict(c.execute('SELECT id, name FROM spots'))
    photo = lambda pid: (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (pid,)).fetchone() or [None])[0]
    plants, left_out = [], []
    for r in rows:
        auto, why = turn_auto(r, overhead)
        ch = choice.get(r['code'])
        on = auto if ch is None else ch == 'on'
        where = ', '.join(x for x in (areas.get(r['area_id']), spots.get(r['spot_id'])) if x)
        p = {'code': r['code'], 'name': r['common_name'], 'photo': photo(r['id']), 'site': r['site'] or 'Outdoors', 'where': where,
             'auto': auto, 'why': why, 'choice': ch, 'last': last.get(r['code'])}
        if not on:
            p['why'] = 'Switched off by hand' if ch == 'off' else why
            if ch == 'off' or (r['site'] or 'Outdoors') in TURN_SITES: left_out.append(p)    # outdoor plants are not listed one by one
            continue
        if ch == 'on' and not auto: p['why'] = 'Switched on by hand'
        if not p['last']:
            p.update(state='never', due_on=None, days=None)
        else:
            due = date.fromisoformat(p['last']) + timedelta(days=every)
            p.update(due_on=due.isoformat(), days=(today - date.fromisoformat(p['last'])).days,
                     state='due' if due <= today else 'soon' if due <= today + timedelta(days=1) else 'ok')
        plants.append(p)
    plants.sort(key=lambda p: (p['due_on'] or '', p['code']))
    n = lambda s: sum(1 for p in plants if p['state'] == s)
    return {'today': today.isoformat(), 'every': every, 'choices': list(TURN_EVERY_CHOICES), 'plants': plants, 'left_out': left_out,
            'counts': {'due': n('due'), 'soon': n('soon'), 'never': n('never'), 'ok': n('ok'), 'left_out': len(left_out)}}

@app.route('/api/turning', methods=['GET', 'PUT'])
def turning():
    """GET: the pots to turn. PUT {every: 7|10|14|21|30} and/or {plant: CODE, on: true|false} changes the reminders (not for viewers)."""
    c = db()
    if request.method == 'GET': return jsonify(turn_report(c, request.args.get('plant') or None))
    b = request.get_json(silent=True) or {}
    who = editor()
    if 'every' in b:
        try: every = int(b['every'])
        except (TypeError, ValueError): abort(400, 'every must be a number of days')
        if every not in TURN_EVERY_CHOICES: abort(400, 'every must be one of: ' + ', '.join(map(str, TURN_EVERY_CHOICES)))
        old = turn_every(c)
        if every != old:
            set_setting(c, 'turn_every_days', str(every))
            audit_only(c, 'care', 'turn_every_days', str(old), str(every), who, f'Turn the pots: remind every {every} days (was {old})')
    if 'plant' in b:
        r = plant_row(c, str(b['plant']))
        on = bool(b.get('on'))
        auto, _ = turn_auto(r, turn_overhead(c))
        ch = turn_choices(c)
        was = ch.get(r['code'], 'on' if auto else 'off')
        if on == auto: ch.pop(r['code'], None)          # back to the usual rule
        else: ch[r['code']] = 'on' if on else 'off'
        set_setting(c, 'turn_choice', json.dumps(ch, sort_keys=True))
        now_ = 'on' if on else 'off'
        if was != now_:
            audit_only(c, 'care', 'turn_reminder', was, now_, who, 'Turn the pots: reminders ' + ('switched on' if on else 'switched off') + ' for this plant', r['id'], r['code'])
    c.commit()
    return jsonify(turn_report(c))
