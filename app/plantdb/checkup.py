"""Prototype proto/health-walk: the health walk-through. Go round the plants one at a time and say how each one looks today.
Rebuilt on the 1.32.0 module layout for 1.42.0; the names it uses from other modules are linked by server.py (see core.link())."""
from .core import *   # noqa: F401,F403

# A walk round the plants, one at a time, to say how each one looks now. "Looks the same" is logged as care kind 'looked';
# a new health rating (and the note, added to the Health summary) is saved on the plant page with its version check, and
# logged as 'looked' too. How often a plant is due is a setting: the usual number of days, a shorter one for plants in Poor
# or Critical health, and an optional number for each group (a plant in several groups takes the shortest). A group's own number
# decides for its plants even when they are in Poor or Critical health, so a group can be looked at less often (cacti once a
# month); the Poor or Critical number applies to plants in no group with a number of its own, when it is shorter. All three live
# in `settings` (checkup_days, checkup_days_poor, checkup_group_days as JSON {group id: days}), so the database needs no new columns.
from . import care as _care
_care.CARE_KINDS['looked'] = 'Looked over'
CHECKUP_DAYS, CHECKUP_DAYS_POOR = 14, 7

def ck_days(v, default=None):
    try: v = int(v)
    except (TypeError, ValueError): return default
    return v if 1 <= v <= 365 else default

def ck_settings(c):
    try: gd = json.loads(setting(c, 'checkup_group_days', '{}') or '{}')
    except ValueError: gd = {}
    groups = {int(k): ck_days(v) for k, v in (gd.items() if isinstance(gd, dict) else []) if str(k).isdigit() and ck_days(v)}
    return ck_days(setting(c, 'checkup_days'), CHECKUP_DAYS), ck_days(setting(c, 'checkup_days_poor'), CHECKUP_DAYS_POOR), groups

@app.route('/api/checkup')
def checkup():
    c = db()
    today = local_today(c)
    tz = tzinfo(location(c)['tz'])
    usual, poor, gdays = ck_settings(c)
    last = {k: d for k, d in c.execute("SELECT plant_code, MAX(done_on) FROM care_log WHERE kind='looked' GROUP BY plant_code")}
    # a health rating changed by a person on the edit page counts as a look too (upgrade batches, signed "Claude (...)", do not)
    for code, ts in c.execute("SELECT plant_code, MAX(changed_at) FROM audit_log WHERE field='health_rating' AND changed_by NOT LIKE 'Claude%' "
                              "AND plant_code IS NOT NULL GROUP BY plant_code"):
        try: d = datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).astimezone(tz).date().isoformat()
        except (TypeError, ValueError): continue
        if d > last.get(code, ''): last[code] = d
    at, at_args = plants_at(c, location(c))                                      # 1.48.0: only the plants at the home in use
    rows = c.execute("SELECT * FROM plants WHERE status='active'" + at + " ORDER BY code", at_args).fetchall()
    spots = plant_spots(c)
    groups, member = [], {}
    for g in c.execute('SELECT * FROM plant_groups ORDER BY name COLLATE NOCASE').fetchall():
        codes = group_codes(c, g, rows, spots)
        groups.append({'id': g['id'], 'name': g['name'], 'count': len(codes), 'days': gdays.get(g['id'])})
        for code in codes: member.setdefault(code, []).append(g['id'])
    gname = {g['id']: g['name'] for g in groups}
    out = []
    for r in rows:
        ph = c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC, id LIMIT 1', (r['id'],)).fetchone()
        pics = [x[0] for x in c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC, id DESC LIMIT 12', (r['id'],))]   # 1.47.0: all of them, newest first after the main one (Ethan, November 8)
        lk = last.get(r['code'])
        days = (today - date.fromisoformat(lk)).days if lk else None
        every, why = usual, 'the usual'
        set_by = sorted((gdays[i], gname[i]) for i in member.get(r['code'], []) if i in gdays)
        if set_by: every, why = set_by[0][0], 'the group ' + set_by[0][1]          # the group's own number decides, even for Poor or Critical
        elif (r['health_rating'] or '') in ('Poor', 'Critical') and poor < every: every, why = poor, 'its health is ' + r['health_rating']
        out.append({'code': r['code'], 'name': r['common_name'], 'site': r['site'] or 'Outdoors', 'location': r['location'] or '',
                    'health': r['health_rating'] or '', 'summary': (r['health_summary'] or '').strip(), 'photo': ph[0] if ph else None, 'photos': pics,
                    'version': r['version'], 'last_looked': lk, 'days': days, 'every': every, 'every_why': why,
                    'groups': member.get(r['code'], []), 'due': days is None or days >= every})
    return jsonify(today=today.isoformat(), due_days=usual, poor_days=poor, health=HEALTH, sites=SITES, groups=groups, plants=out)

@app.route('/api/checkup/settings', methods=['PUT'])
def checkup_settings():
    """The usual number of days, and the number for plants in Poor or Critical health."""
    c = db()
    b = request.get_json(silent=True) or {}
    old = ck_settings(c)
    new = (ck_days(b.get('days')), ck_days(b.get('poor_days')))
    if None in new: abort(400, 'The number of days must be a whole number from 1 to 365')
    for key, was, now_v, words in (('checkup_days', old[0], new[0], 'Health walk-through: look over plants every'),
                                    ('checkup_days_poor', old[1], new[1], 'Health walk-through: plants in Poor or Critical health every')):
        if was != now_v:
            set_setting(c, key, str(now_v))
            audit_only(c, 'setting', key, str(was), str(now_v), editor(), f'{words} {now_v} days (was {was})')
    c.commit()
    return checkup()

@app.route('/api/checkup/groups/<int:gid>', methods=['PUT'])
def checkup_group(gid):
    """How often the plants in one group are due. days: null (or empty) means the group has no number of its own."""
    c = db()
    g = c.execute('SELECT * FROM plant_groups WHERE id=?', (gid,)).fetchone()
    if not g: abort(404, 'No such group')
    b = request.get_json(silent=True) or {}
    raw_days = b.get('days')
    days = None if raw_days in (None, '') else ck_days(raw_days)
    if raw_days not in (None, '') and days is None: abort(400, 'The number of days must be a whole number from 1 to 365')
    gdays = ck_settings(c)[2]
    was = gdays.get(gid)
    if was != days:
        if days: gdays[gid] = days
        else: gdays.pop(gid, None)
        set_setting(c, 'checkup_group_days', json.dumps({str(k): v for k, v in sorted(gdays.items())}))
        audit_only(c, 'group', 'checkup_days', str(was or ''), str(days or ''), editor(),
                   f"Health walk-through for the group {g['name']}: " + (f'every {days} days' if days else 'the usual number of days')
                   + (f' (was every {was} days)' if was else ''))
    c.commit()
    return jsonify(id=gid, days=days)
