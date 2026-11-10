"""Prototype (proto/repotting): the repotting plan. Potted plants fill their pots with roots and use up their soil; most want a
bigger pot or fresh soil every one to three years, best done in spring as they start to grow. This lists which plants are due
for repotting this spring (or next spring, out of season), from the "Repotted" entries already in the care log.

How often: from the plant's growth rate (About this plant): fast growers every year, moderate to fast every 18 months, moderate
every 2 years, slow growers every 3 years. Plants that grow in water are left out. Each plant can be given its own number of
months, or switched off, by hand ("repot_choice" in settings, JSON {code: months | 'off'}; a choice that matches the usual rule
is dropped). Nothing else is stored: a repot is a care_log row of kind 'repot' (or 'prep_repot' from the coming-inside checklist),
logged with the usual POST /api/care, which also takes an earlier date for "When was it last repotted?"."""
from .core import *   # noqa: F401,F403

REPOT_CHOICES = (12, 18, 24, 36)                # months
REPOT_KINDS = ('repot', 'prep_repot')
SPRING = ((3, 1), (5, 31))                       # Central Texas: growth starts in March; by June the heat makes a move hard on roots
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

def add_months(d, n):
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    last = [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(d.day, last))

def repot_auto(growth_rate, leaf_type):
    """The usual rule from the plant's growth rate: (months or None for left out, reason words)."""
    if leaf_type == 'Grows in water': return None, 'Grows in water: change the water instead'
    g = (growth_rate or '').strip().lower()
    if not g: return 24, 'Growth rate not filled in, so every 2 years'
    if g.startswith(('extremely fast', 'very fast', 'fast')): return 12, 'Grows fast, so every year'
    if g.startswith('moderate to fast'): return 18, 'Grows moderately fast, so every 18 months'
    if g.startswith('slow to moderate') or g.startswith('moderate'): return 24, 'Grows at a moderate pace, so every 2 years'
    if g.startswith('slow'): return 36, 'Grows slowly, so every 3 years'
    return 24, 'Every 2 years'

def next_spring(d):
    """The spring window d is in, or the next one after it."""
    y = d.year if (d.month, d.day) <= SPRING[1] else d.year + 1
    return date(y, *SPRING[0]), date(y, *SPRING[1])

def spring_of(d):
    """The spring a repot due on d is done in (the year): that year's spring if it is due by the end of August (a few months early
    beats a whole year late), else the next spring."""
    return d.year if (d.month, d.day) <= (8, 31) else d.year + 1

def repot_season(today):
    a, b = next_spring(today)
    now = a <= today <= b
    if now: words = f'It is repotting season: March to May, while plants start to grow and before the summer heat. The season ends {MONTHS[b.month - 1]} {b.day}.'
    else: words = (f'The best time to repot is spring, March to May {a.year}, as plants start to grow. Until then, repot only a plant that '
                   'shows it cannot wait (see the signs below).')
    return {'now': now, 'from': a.isoformat(), 'to': b.isoformat(), 'year': a.year, 'words': words}

def repot_choices(c):
    try: d = json.loads(setting(c, 'repot_choice', '{}') or '{}')
    except ValueError: d = {}
    if not isinstance(d, dict): return {}
    return {str(k): v for k, v in d.items() if v == 'off' or v in REPOT_CHOICES}

def repot_plan(today, rows, last, choice):
    """Pure: rows are dicts with code, name, photo, where, site, growth_rate, leaf_type, pot_size, health; last {code: date string};
    choice {code: months | 'off'}. Returns the plants on the plan and those left out."""
    season = repot_season(today)
    plants, left_out = [], []
    for r in rows:
        auto, why = repot_auto(r.get('growth_rate'), 'Grows in water' if r.get('grow_kind') == 'Water only' else r.get('leaf_type'))
        ch = choice.get(r['code'])
        p = {k: r.get(k) for k in ('code', 'name', 'photo', 'where', 'site', 'pot_size', 'health')}
        p['growth'] = r.get('growth_rate') or ''
        p.update(auto=auto, why=why, choice=ch, last=last.get(r['code']))
        months = auto if ch is None else (None if ch == 'off' else ch)
        if months is None:
            p.update(why='Switched off by hand' if ch == 'off' else why, months=None)
            left_out.append(p); continue
        if ch is not None: p['why'] = f'Every {months} months, chosen by hand'
        elif r.get('mix_months') and r['mix_months'] < months:      # 1.57.0 (PLAN.md step 9e): a mix that breaks down sooner brings it forward
            months = r['mix_months']; p['why'] = f'Its mix wants freshening in about {months} months (the {(r.get("mix_by") or "mix").lower()} breaks down)'
        p['months'] = months
        if not p['last']:
            p.update(state='never', due_on=None, spring=None)
        else:
            due = add_months(date.fromisoformat(p['last']), months)
            sp = spring_of(due)
            p.update(due_on=due.isoformat(), spring=sp, state='due' if sp <= season['year'] else 'later')
        plants.append(p)
    plants.sort(key=lambda p: (p['due_on'] or '9999', p['code']))
    n = lambda s: sum(1 for p in plants if p['state'] == s)
    return {'today': today.isoformat(), 'season': season, 'choices': list(REPOT_CHOICES), 'plants': plants, 'left_out': left_out,
            'counts': {'due': n('due'), 'never': n('never'), 'later': n('later'), 'left_out': len(left_out)}}

def repot_mix(c, code):
    """1.57.0: how long the plant's current mix lasts, for the plan: {mix_months, mix_by} (empty when not known)."""
    m = current_mix(c, code)
    if not m: return {}
    s = pot_dict(c, m)['summary']
    return {'mix_months': s.get('lasts_months'), 'mix_by': s.get('lasts_by')} if s.get('lasts_months') else {}

def repot_report(c, code=None):
    """code: just that plant (its own page)."""
    at, at_args = plants_at(c, location(c))
    if code: at, at_args = ' AND code=?', [code]
    rows = c.execute("SELECT * FROM plants WHERE status='active'" + at + ' ORDER BY code', at_args).fetchall()
    last = dict(c.execute('SELECT plant_code, MAX(done_on) FROM care_log WHERE kind IN (%s) GROUP BY plant_code' % ','.join('?' * len(REPOT_KINDS)), REPOT_KINDS))
    areas = dict(c.execute('SELECT id, name FROM areas'))
    spots = dict(c.execute('SELECT id, name FROM spots'))
    photo = lambda pid: (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (pid,)).fetchone() or [None])[0]
    rs = [{'code': r['code'], 'name': r['common_name'], 'photo': photo(r['id']), 'site': r['site'] or 'Outdoors',
           'where': ', '.join(x for x in (areas.get(r['area_id']), spots.get(r['spot_id'])) if x),
           'growth_rate': r['growth_rate'], 'leaf_type': r['leaf_type'], 'pot_size': r['pot_size'], 'health': r['health_rating'],
           'grow_kind': grow_kind(r), **repot_mix(c, r['code'])} for r in rows]
    return repot_plan(local_today(c), rs, last, repot_choices(c))

@app.route('/api/repotting', methods=['GET', 'PUT'])
def repotting():
    """GET: the repotting plan (?plant=CODE for one plant). PUT {plant: CODE, every: 12|18|24|36|'auto'|'off'} changes how often
    that plant is due (not for viewers)."""
    c = db()
    if request.method == 'GET': return jsonify(repot_report(c, request.args.get('plant') or None))
    b = request.get_json(silent=True) or {}
    if not b.get('plant'): abort(400, 'Choose a plant')
    r = plant_row(c, str(b['plant']))
    ev = b.get('every')
    if ev not in ('auto', 'off'):
        try: ev = int(ev)
        except (TypeError, ValueError): abort(400, "every must be 12, 18, 24, 36, 'auto' or 'off'")
        if ev not in REPOT_CHOICES: abort(400, 'every must be one of: ' + ', '.join(map(str, REPOT_CHOICES)) + ' months')
    auto, _ = repot_auto(r['growth_rate'], r['leaf_type'])
    ch = repot_choices(c)
    word = lambda v: 'no reminders' if v in ('off', None) else f'every {v} months'
    was = ch.get(r['code'], auto)
    if ev == 'auto' or ev == auto or (ev == 'off' and auto is None): ch.pop(r['code'], None)     # back to the usual rule
    else: ch[r['code']] = ev
    new = ch.get(r['code'], auto)
    set_setting(c, 'repot_choice', json.dumps(ch, sort_keys=True))
    if was != new:
        audit_only(c, 'care', 'repot_every', word(was), word(new), editor(), f'Repotting: {word(new)} for this plant (was {word(was)})', r['id'], r['code'])
    c.commit()
    return jsonify(repot_report(c))
