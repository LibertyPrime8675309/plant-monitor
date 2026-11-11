"""Grow lights, and pots and catch trays.
Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- grow lights (1.13.0)
# Ethan's own lights (table lights, specs in a JSON column so a light can carry whatever its maker publishes), the spots
# they light (table light_spots: one kind of light, how many of it, how far above or beside the plants, hours a day and
# brightness) and which plants sit in which spot (table light_assign). From the maker's PPFD-at-distance figures the
# app works out the daily light (DLI) at the leaves and compares it with each plant's dli_low..dli_high.
def plant_foot(c, r):
    """1.29.0: the floor a plant takes under a light, in square feet: its catch tray if it has one, else its pot (both from Pots and
    trays, a circle counted as the square around it), else a guess from its Pot size."""
    for k in ('tray_id', 'pot_id'):
        cid = r[k] if k in r.keys() else None
        if cid:
            x = c.execute('SELECT * FROM containers WHERE id=?', (cid,)).fetchone()
            f = cont_sqft(x) if x else None
            if f: return f
    return LIGHT_FOOTPRINT.get((r['pot_size'] or '').split(':')[0], 1.0)

LIGHT_FOOTPRINT = {'Small': 0.75, 'Medium': 1.5, 'Large': 3.0}       # square feet of light a pot takes, by pot size (prep traits)
LIGHT_HOURS = (12, 14, 16, 10, 8)                                     # hours a day to try, in this order
LIGHT_VERDICT = {'too_dim': 'Too dim', 'dim': 'A bit dim', 'good': 'Good', 'bright': 'A bit bright', 'too_bright': 'Too bright', 'unknown': 'Needs not set'}

def light_specs(r):
    try: d = json.loads(r['data'] or '{}')
    except ValueError: d = {}
    return d

def light_points(d):
    """[(inches, ppfd, area_sqft or None)], nearest first. Points without a distance or PPFD are dropped."""
    out = []
    for p in d.get('ppfd') or []:
        try:
            x, y = float(p[0]), float(p[1])
            a = float(p[2]) if len(p) > 2 and p[2] not in (None, '') else None
        except (TypeError, ValueError, IndexError): continue
        if x > 0 and y > 0: out.append((x, y, a))
    return sorted(out)

def _loglog(pairs, d):
    """Value at distance d from (distance, value) pairs, straight lines on log-log axes (light falls off as a power of distance).
    Outside the measured range the nearest segment is extended; with one point, an exponent of 1.6 is assumed."""
    pairs = [(x, y) for x, y in pairs if x > 0 and y and y > 0]
    if not pairs: return None
    if len(pairs) == 1:
        x0, y0 = pairs[0]
        return y0 * (x0 / d) ** 1.6
    if d <= pairs[0][0]: (x1, y1), (x2, y2) = pairs[0], pairs[1]
    elif d >= pairs[-1][0]: (x1, y1), (x2, y2) = pairs[-2], pairs[-1]
    else:
        i = next(i for i in range(1, len(pairs)) if pairs[i][0] >= d)
        (x1, y1), (x2, y2) = pairs[i - 1], pairs[i]
    if x2 == x1: return y1
    k = math.log(y2 / y1) / math.log(x2 / x1)
    return y1 * (d / x1) ** k

def ppfd_at(pts, d): return _loglog([(x, y) for x, y, _ in pts], d)

def area_at(pts, d):
    ar = [(x, a) for x, _, a in pts if a]
    if not ar: return None
    if len(ar) == 1: return ar[0][1] * (d / ar[0][0]) ** 2
    return _loglog(ar, d)

def light_range(pts):
    """Practical distances for a light: a little closer than the nearest figure, a little past the farthest."""
    if not pts: return None, None
    return max(3.0, round(pts[0][0] * 0.75)), round(pts[-1][0] * 1.25)

def dli_of(ppfd, hours, dim=100): return round(ppfd * dim / 100 * hours * 3600 / 1e6, 1)

def light_verdict(dli, lo, hi):
    if dli is None or (lo is None and hi is None): return 'unknown'
    if lo is not None and dli < lo: return 'too_dim' if dli < lo * 0.8 else 'dim'
    if hi is not None and dli > hi: return 'too_bright' if dli > hi * 1.3 else 'bright'
    return 'good'

def plant_need(r):
    lo, hi = r['dli_low'], r['dli_high']
    if lo is None and hi is None: return None
    lo = lo if lo is not None else hi * 0.5
    hi = hi if hi is not None else lo * 2
    return {'lo': lo, 'hi': hi, 'target': round(lo + (hi - lo) * 0.4, 1)}

def light_timer_note(d, hours):
    hrs = d.get('timer_hours') or []
    if hours in hrs and d.get('timer_repeats'): return 'Set its own timer to %g hours.' % hours
    if hours in hrs: return "Its timer has a %g-hour setting, but it may not repeat every day; a plug-in outlet timer is surer." % hours
    return 'Use a plug-in outlet timer set to %g hours a day.' % hours

def light_setting(d, target, lo=None, hi=None, hours_first=None):
    """Distance, hours and brightness that give about `target` mol/day under one light. Returns a dict, with reach='ok',
    'weak' (cannot give that much, so the strongest setting) or 'strong' (too much even at the gentlest setting)."""
    pts = light_points(d)
    if not pts: return None
    dmin, dmax = light_range(pts)
    dims = sorted({int(x) for x in (d.get('dimming') or [100]) if 0 < int(x) <= 100} | {100}, reverse=True)
    order = ([hours_first] if hours_first else []) + [h for h in LIGHT_HOURS if h != hours_first]
    for h in order:
        for dim in dims:
            need = target * 1e6 / (h * 3600) / (dim / 100)
            if ppfd_at(pts, dmin) < need or ppfd_at(pts, dmax) > need: continue
            a, b = dmin, dmax                      # PPFD falls with distance: halve the interval until it gives `need`
            for _ in range(40):
                m = (a + b) / 2
                if ppfd_at(pts, m) > need: a = m
                else: b = m
            exact = (a + b) / 2
            for dist in dict.fromkeys(max(dmin, min(dmax, x)) for x in (round(exact), math.floor(exact), math.ceil(exact))):
                p = ppfd_at(pts, dist)                 # whole inches: the nearest, else the next one closer or farther that still suits
                dl = dli_of(p, h, dim)
                if lo is None or hi is None or lo <= dl <= hi: break
            else: continue
            return {'distance_in': dist, 'hours': h, 'dim_pct': dim, 'ppfd': round(p), 'dli': dl, 'reach': 'ok',
                    'area_sqft': round(area_at(pts, dist), 1) if area_at(pts, dist) else None}
    best = max(((dli_of(ppfd_at(pts, dmin), 16), 'weak', dmin, 16, 100), (dli_of(ppfd_at(pts, dmax), 8, dims[-1]), 'strong', dmax, 8, dims[-1])),
               key=lambda t: -abs(math.log(max(t[0], 0.01) / max(target, 0.01))))
    dl, reach, dist, h, dim = best
    return {'distance_in': dist, 'hours': h, 'dim_pct': dim, 'ppfd': round(ppfd_at(pts, dist)), 'dli': dl, 'reach': reach,
            'area_sqft': round(area_at(pts, dist), 1) if area_at(pts, dist) else None}

def light_dict(r, used=0):
    d = light_specs(r)
    pts = light_points(d)
    dmin, dmax = light_range(pts)
    return {'id': r['id'], 'key': r['lkey'], 'name': r['name'], 'count': r['count'], 'in_use': used, 'fixture': r['fixture'], 'notes': r['notes'],
            'specs': d, 'points': [{'distance_in': x, 'ppfd': y, 'area_sqft': a} for x, y, a in pts], 'min_in': dmin, 'max_in': dmax,
            'max_dli': dli_of(ppfd_at(pts, dmin), 16) if pts else None, 'reach': light_reach(d, pts),
            'room_light': 'room light' in (d.get('kind') or '').lower(),
            'photo': d.get('photo'), 'chart': d.get('chart'), 'updated_by': r['updated_by'] or r['created_by'], 'updated_at': r['updated_at'] or r['created_at'],
            'mount': d.get('mount'), 'mount_words': mount_words(d.get('mount')),      # 1.56.0 (PLAN.md step 8a): how it holds
            'status': r['status'] if 'status' in r.keys() else 'owned'}               # 1.56.0 (PLAN.md step 10b)

def light_reach(d, pts):
    """1.41.0: what one of this light can give, within the distances its maker (or Claude) measured: the most light (its
    nearest figure, full brightness) and the least (its farthest figure, its lowest brightness), and the daily light those
    give on 12 hours, and from 8 hours at the least to 16 at the most. Not extended past the measured distances."""
    if not pts: return None
    dims = sorted({int(x) for x in (d.get('dimming') or [100]) if 0 < int(x) <= 100} | {100})
    hi, lo = pts[0][1], pts[-1][1] * dims[0] / 100
    return {'near_in': pts[0][0], 'far_in': pts[-1][0], 'ppfd_max': round(hi), 'ppfd_min': round(lo, 1), 'dim_min': dims[0],
            'dli12': [dli_of(lo, 12), dli_of(hi, 12)], 'dli_any': [dli_of(lo, 8), dli_of(hi, 16)], 'one_point': len(pts) == 1}

def stack_factor(area, units, need):
    """1.56.1: how many lights' worth reach the plants when a spot has several of a light. Side by side over plants that need
    the room, each lights its own patch at the same strength; over plants that fit under fewer of them, their light adds up
    on the same leaves. So: all the area they light, spread over the larger of one light's area and the pots' room, between
    1 and the number of lights. With no area figures for the light, they are taken to shine on the same plants."""
    if units <= 1: return 1.0
    if not area: return float(units)
    return max(1.0, min(float(units), units * area / max(area, need or 0)))

def spot_eval(c, s, L, plants):
    d = light_specs(L) if L is not None else {}
    pts = light_points(d)
    p1 = ppfd_at(pts, s['distance_in']) if pts else None
    area = area_at(pts, s['distance_in']) if pts else None
    rows, need = [], 0.0
    for r in plants: need += plant_foot(c, r)
    f = stack_factor(area, s['units'], need)
    p = p1 * f if p1 else None
    dl = dli_of(p, s['hours'], s['dim_pct']) if p else None
    for r in plants:
        n = plant_need(r)
        v = light_verdict(dl, n and n['lo'], n and n['hi'])
        rows.append({'code': r['code'], 'name': r['common_name'], 'lo': n and n['lo'], 'hi': n and n['hi'], 'verdict': v, 'verdict_word': LIGHT_VERDICT[v],
                     'photo': plant_photo(c, r['id']), 'height_in': r['height_in'] if 'height_in' in r.keys() else None})
    cover = round(area * s['units'], 1) if area else None
    lit = round(area * s['units'] / f, 1) if area else None              # overlapping lights light less floor, more strongly
    return {'ppfd': round(p) if p else None, 'dli': dl, 'area_sqft': lit, 'plants': rows, 'room_needed_sqft': round(need, 1),
            'crowded': bool(cover and need > cover * LIGHT_ROOM * 1.1), 'timer_note': light_timer_note(d, s['hours']) if L is not None else '',
            'units': s['units'], 'stack': round(f, 2), 'area_known': bool(area)}

def plant_photo(c, pid):
    r = c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC, id LIMIT 1', (pid,)).fetchone()
    return r[0] if r else None

def light_candidates(c):
    """Plants that live inside or are going inside for the winter."""
    q = "SELECT * FROM plants WHERE status='active' AND (site IN (%s) OR winter_plan='Move indoors') ORDER BY code" % ','.join('?' * len(INSIDE_SITES))
    return c.execute(q, INSIDE_SITES).fetchall()

LIGHT_ROOM = 1.5     # a light lights usefully about this much more than the circle its maker measured (the edges get less, but enough)

def light_plan(c, lights, spots_used, assigned):
    """A suggested layout for plants that are not in a spot yet. Each free unit of a light can be one spot with one
    setting. Plants needing the most light are placed first. A plant joins a suggested spot when its light needs overlap
    with everyone already there and there is room under the light (area it lights at that distance, against each pot's
    size), adding another unit of the same light if one is free; otherwise it starts a new spot under the smallest of your
    lights that can give it enough."""
    free = {L['id']: max(0, L['count'] - spots_used.get(L['id'], 0)) for L in lights}
    specs = {L['id']: light_specs(L) for L in lights}
    todo = [r for r in light_candidates(c) if r['code'] not in assigned and plant_need(r)]
    todo.sort(key=lambda r: (-plant_need(r)['target'], r['code']))
    foot = lambda r: plant_foot(c, r)
    slots, unplaced = [], []

    def fit(L, lo, hi, used, units, maxu=None):
        """Setting for a spot under light L serving [lo, hi] with `used` square feet of pots, and how many units it then
        needs (None if it cannot). Aims near the middle of the range; when that needs more units than `maxu`, it aims
        lower, which raises the light so it covers more."""
        first = None
        for frac in (0.45, 0.3, 0.15, 0.05):
            st = light_setting(specs[L['id']], round(lo + (hi - lo) * frac, 1), lo, hi)
            if not st or st['reach'] != 'ok': continue
            need = max(units, math.ceil(used / ((st['area_sqft'] or 1.0) * LIGHT_ROOM) - 1e-9))
            if first is None: first = (st, need)
            if maxu is None or need <= maxu: return st, need
        return first if first else (None, None)

    for r in todo:
        n, f = plant_need(r), foot(r)
        best = None
        for sl in slots:
            lo, hi = max(sl['lo'], n['lo']), min(sl['hi'], n['hi'])
            if lo > hi: continue
            st, units = fit(sl['L'], lo, hi, sl['used'] + f, sl['units'], sl['units'] + free[sl['L']['id']])
            if st is None or units - sl['units'] > free[sl['L']['id']]: continue
            key = (units - sl['units'], specs[sl['L']['id']].get('watts') or 999)
            if best is None or key < best[0]: best = (key, sl, lo, hi, units)
        if best and best[0][0] == 0:
            pass                                     # joins a spot without needing another light
        else:
            new = None
            for L in lights:
                if not free[L['id']]: continue
                st, units = fit(L, n['lo'], n['hi'], f, 1, free[L['id']])
                if st is None or units > free[L['id']]: continue
                dmin = light_range(light_points(specs[L['id']]))[0]
                strain = (st['hours'] > 14) + (st['distance_in'] <= dmin + 1)       # only reaches it at its limits
                key = (strain, specs[L['id']].get('watts') or 999, L['id'])
                if new is None or key < new[2]: new = (L, units, key)
            if new and (best is None or (specs[new[0]['id']].get('watts') or 999) <= (specs[best[1]['L']['id']].get('watts') or 999)):
                L, units, _ = new
                free[L['id']] -= units
                slots.append({'L': L, 'lo': n['lo'], 'hi': n['hi'], 'used': f, 'units': units, 'members': [r]})
                continue
        if best:
            _, sl, lo, hi, units = best
            free[sl['L']['id']] -= units - sl['units']
            sl.update(lo=lo, hi=hi, used=sl['used'] + f, units=units); sl['members'].append(r)
            continue
        strongest = max((dli_of(ppfd_at(light_points(specs[L['id']]), light_range(light_points(specs[L['id']]))[0]), 16)
                         for L in lights if light_points(specs[L['id']])), default=0)
        why = ('None of your lights can give it %g mol/day: the strongest gives about %g at its closest, 16 hours a day.' % (n['lo'], strongest)
               if strongest < n['lo'] else 'The lights that suit it are full in this layout. Another light, a spot already set up with room, or a bright window would do.')
        unplaced.append({'code': r['code'], 'name': r['common_name'], 'lo': n['lo'], 'hi': n['hi'], 'why': why, 'photo': plant_photo(c, r['id'])})
    out = []
    for sl in slots:
        L, g = sl['L'], sl['members']
        st, _ = fit(L, sl['lo'], sl['hi'], sl['used'], sl['units'], sl['units'])
        st = st or light_setting(specs[L['id']], (sl['lo'] + sl['hi']) / 2)
        s = {'units': sl['units'], 'distance_in': st['distance_in'], 'hours': st['hours'], 'dim_pct': st['dim_pct']}
        ev = spot_eval(c, s, L, g)
        out.append({**s, 'light_id': L['id'], 'light': L['name'], 'band': spot_band(g), 'codes': [x['code'] for x in g], **ev})
    out.sort(key=lambda s: (-(s['dli'] or 0), s['light']))
    seen = {}
    for sp in out:                                   # "Bright light 1", "Medium light 2" ...: Ethan renames them to the room or shelf
        seen[sp['band']] = seen.get(sp['band'], 0) + 1
        sp['name'] = '%s light %d' % (sp['band'], seen[sp['band']])
    return out, unplaced

def spot_band(g):
    lo = min(plant_need(x)['lo'] for x in g)
    return 'Bright' if lo >= 12 else 'Medium' if lo >= 6 else 'Low'

def outdoor_dli(c):
    """Average daily light over the last 7 observed days at home, open sky (mol/m2/day), from the weather's solar radiation."""
    L = home_place(c)
    rows = c.execute("SELECT data FROM weather_daily WHERE loc_id=? AND kind='observed' ORDER BY date DESC LIMIT 7", (L['id'],)).fetchall()
    vals = []
    for (x,) in rows:
        try: v = (json.loads(x) or {}).get('shortwave_radiation_sum')
        except ValueError: v = None
        if v is not None: vals.append(v * PAR_PER_WM2)       # MJ/m2 of sunlight -> mol/m2 of PAR (same 2.1 factor as hourly)
    avg = sum(vals) / len(vals) if vals else None
    return round(avg, 1) if avg is not None and avg <= 75 else None      # above 75 mol/m2 a day is not possible outdoors: bad data

def step_down(L, s, plants, outdoor):
    """Easing plants from outdoor light into this spot: the first week as bright as the light allows without going over
    any plant's high, then halfway, then the spot's own setting."""
    d = light_specs(L)
    ns = [plant_need(r) for r in plants if plant_need(r)]
    if not ns: return []
    hi = min(n['hi'] for n in ns)
    pts = light_points(d)
    final = dli_of(ppfd_at(pts, s['distance_in']), s['hours'], s['dim_pct'])
    first = light_setting(d, hi * 0.95, None, hi, hours_first=16)
    if not first or first['dli'] < final * 1.2: return []
    mid = light_setting(d, round((first['dli'] + final) / 2, 1), None, hi, hours_first=14)
    steps = []
    if any(r['site'] == 'Outdoors' for r in plants) and outdoor and outdoor > hi * 1.5:
        steps.append({'when': 'Before moving in', 'text': 'Give the plants that are out in the open 5 to 7 days on the covered porch or in bright shade first, so the drop in light is smaller.'})
    for when, st in (('First week inside', first), ('Second week', mid)):
        if st: steps.append({'when': when, 'distance_in': st['distance_in'], 'hours': st['hours'], 'dim_pct': st['dim_pct'], 'dli': st['dli'],
                             'text': light_timer_note(d, st['hours'])})
    steps.append({'when': 'From the third week', 'distance_in': s['distance_in'], 'hours': s['hours'], 'dim_pct': s['dim_pct'], 'dli': final,
                  'text': "The spot's own setting."})
    return steps

def lights_state(c):
    lights = c.execute('SELECT * FROM lights ORDER BY sort, id').fetchall()
    byid = {L['id']: L for L in lights}
    spots = c.execute('SELECT * FROM light_spots ORDER BY id').fetchall()
    used = {}
    for s in spots: used[s['light_id']] = used.get(s['light_id'], 0) + s['units']
    assign = {}
    for code, sid in c.execute('SELECT plant_code, spot_id FROM light_assign'): assign.setdefault(sid, []).append(code)
    assigned = {code for codes in assign.values() for code in codes}
    outdoor = outdoor_dli(c)
    out_spots = []
    others = [(o['name'], light_mount(o)) for o in lights if o['count'] > 0]
    pphoto = place_photo_map(c)
    for s in spots:
        ps = [r for r in (c.execute('SELECT * FROM plants WHERE code=?', (code,)).fetchone() for code in assign.get(s['id'], [])) if r]
        L = byid.get(s['light_id'])
        ev = spot_eval(c, s, L, ps)
        out_spots.append({'id': s['id'], 'name': s['name'], 'light_id': s['light_id'], 'light': L['name'] if L else 'A light that was removed',
                          'place_id': s['place_id'], 'place': place_label(c, s['place_id']), 'place_photo': pphoto.get(s['place_id']),
                          'units': s['units'], 'distance_in': s['distance_in'], 'hours': s['hours'], 'dim_pct': s['dim_pct'], 'notes': s['notes'],
                          'level': s['level'] or '', 'holder': s['holder'] or '',
                          'fit': spot_fit(c, s, L, ps, [x for x in others if L is None or x[0] != L['name']]),     # 1.56.0 (PLAN.md step 8d): can it be put there
                          'checked': spot_checked(c, s),                                                        # 1.56.0 (8e): set up and checked
                          'steps': step_down(L, s, ps, outdoor) if L else [], **ev})
    plan, unplaced = light_plan(c, lights, used, assigned)
    for p in plan:
        p['steps'] = step_down(byid[p['light_id']], p, [c.execute('SELECT * FROM plants WHERE code=?', (x,)).fetchone() for x in p['codes']], outdoor)
    cands = [{'code': r['code'], 'name': r['common_name'], 'site': r['site'], 'winter_plan': r['winter_plan'], 'need': plant_need(r),
              'pot_size': r['pot_size'], 'photo': plant_photo(c, r['id']), 'foot': round(plant_foot(c, r), 2), 'inside': r['site'] in INSIDE_SITES}
             for r in light_candidates(c)]
    # 1.41.0: a plant that does not fit its spot is pointed at one of your other spots that would suit it
    for sp in out_spots:
        for p in sp['plants']: p['better'] = better_spot(out_spots, p, sp['id'])
    lights_out = [light_dict(L, used.get(L['id'], 0)) for L in lights if L['status'] == 'owned' or used.get(L['id'])]   # 1.56.0: others are on Compare lights
    for Ld in lights_out:      # how many of the plants that need a light this one could serve, at some setting within its range
        rg = Ld['reach']
        Ld['suits'] = sum(1 for x in cands if x['need'] and rg and x['need']['lo'] <= rg['dli_any'][1] and x['need']['hi'] >= rg['dli_any'][0]) if rg else 0
    def lv(pid):                                          # 1.56.0: how many levels, and each lower level's clear height, for the spot dialog
        sp, room = place_rows(c, pid); sh = {**(sheet_of(room) if room is not None else {}), **(sheet_of(sp) if sp is not None else {})}
        return {'levels': sh.get('levels'), 'gaps_in': sh.get('gaps_in') or ([sh['gap_in']] * (sh['levels'] - 1) if sh.get('gap_in') and sh.get('levels') else [])}
    places = [p | {'spots': [s['id'] for s in out_spots if s['place_id'] == p['id']], 'photo': pphoto.get(p['id']), 'words': place_words(c, p['id']), **lv(p['id'])} for p in light_places(c)]
    return {'lights': lights_out, 'spots': out_spots, 'plan': plan, 'unplaced': unplaced, 'places': places,
            'candidates': cands, 'assigned': {code: sid for sid, codes in assign.items() for code in codes}, 'outdoor_dli': outdoor,
            'verdicts': LIGHT_VERDICT, 'mount_kinds': MOUNT_KINDS, 'points': POINTS, 'holders': {k: v[0] for k, v in HOLDERS.items()}}

def better_spot(spots, p, here=None):
    """One of your other spots whose light would suit this plant (verdict Good), nearest its needs' middle, or None."""
    if p.get('verdict') in ('good', 'unknown', None) or p.get('lo') is None: return None
    mid = (p['lo'] + p['hi']) / 2
    def placeable(s):          # 1.56.0 (PLAN.md step 8d): not a spot whose light does not fit there, nor one whose level it is too tall for
        f = s.get('fit') or {}
        if f.get('status') == 'nofit' and any(x['kind'] == 'nofit' for x in f.get('lines') or []): return False
        return not (p.get('height_in') and f.get('clear_in') and p['height_in'] >= f['clear_in'])
    fits = [s for s in spots if s['id'] != here and s.get('dli') is not None and light_verdict(s['dli'], p['lo'], p['hi']) == 'good' and placeable(s)]
    if not fits: return None
    s = min(fits, key=lambda s: abs(s['dli'] - mid))
    return {'id': s['id'], 'name': s['name'], 'dli': s['dli']}

def best_setting(c, L, units, plants):
    """1.41.0: the distance, hours and brightness under light L that put the most of these plants in their range, then the
    fewest just outside it, then not crowded, then nearest the middle of their ranges; whole inches within the light's range."""
    d = light_specs(L); pts = light_points(d)
    if not pts: return None
    dmin, dmax = light_range(pts)
    dims = sorted({int(x) for x in (d.get('dimming') or [100]) if 0 < int(x) <= 100} | {100}, reverse=True)
    ns = [(r, plant_need(r)) for r in plants]
    known = [(r, n) for r, n in ns if n]
    foot = sum(plant_foot(c, r) for r in plants)
    best = None
    for dist in range(int(math.ceil(dmin)), int(math.floor(dmax)) + 1):
        area = area_at(pts, dist); p = ppfd_at(pts, dist) * stack_factor(area, units, foot)       # 1.56.1: several lights add up
        crowded = bool(area and foot > area * units * LIGHT_ROOM * 1.1)
        for h in LIGHT_HOURS:
            for dim in dims:
                dl = dli_of(p, h, dim)
                vs = [light_verdict(dl, n['lo'], n['hi']) for _, n in known]
                off = sum(abs(math.log(max(dl, 0.01) / max(n['target'], 0.01))) for _, n in known)
                key = (sum(v == 'good' for v in vs), sum(v in ('dim', 'bright') for v in vs), not crowded, h in (12, 14), dim == 100, -off)
                if best is None or key > best[0]: best = (key, dist, h, dim, dl, p)
    _, dist, h, dim, dl, p = best
    return {'distance_in': dist, 'hours': h, 'dim_pct': dim, 'dli': dl, 'ppfd': round(p), 'good': best[0][0], 'of': len(known)}

@app.route('/api/lights/best')
def lights_best():
    """Best setting for the ticked plants: ?light=ID&units=N&plants=P-001,P-002"""
    c = db()
    try: lid = int(request.args.get('light', 0)); units = max(1, min(50, int(request.args.get('units') or 1)))
    except ValueError: abort(400, 'light and units must be numbers')
    L = c.execute('SELECT * FROM lights WHERE id=?', (lid,)).fetchone()
    if not L: abort(404, 'That light is not in your list')
    codes = [x for x in (request.args.get('plants') or '').split(',') if x]
    ps = [r for r in (c.execute('SELECT * FROM plants WHERE code=?', (x,)).fetchone() for x in codes) if r]
    if not ps: abort(400, 'Tick the plants for this spot first')
    b = best_setting(c, L, units, ps)
    if not b: abort(400, 'This light has no light figures yet. Add them with "Change the light figures" under Your lights.')
    return jsonify(b)

@app.route('/api/lights')
def lights_get():
    """Everything the Grow lights page shows: your lights, your spots, a suggested layout for the rest, and the step-down plans.
    ?plant=CODE gives just that plant's spot (or suggestion), for its own page."""
    c = db()
    st = lights_state(c)
    code = request.args.get('plant')
    if not code: return jsonify(st)
    sid = st['assigned'].get(code)
    spot = next((s for s in st['spots'] if s['id'] == sid), None) if sid else None
    sug = next((s for s in st['plan'] if code in s['codes']), None)
    un = next((u for u in st['unplaced'] if u['code'] == code), None)
    cand = next((x for x in st['candidates'] if x['code'] == code), None)
    n = cand['need'] if cand else None
    spots = [{'id': s['id'], 'name': s['name'], 'place': s['place'], 'light': s['light'], 'dli': s['dli'], 'n': len(s['plants']),
              'verdict': light_verdict(s['dli'], n and n['lo'], n and n['hi']), 'verdict_word': LIGHT_VERDICT[light_verdict(s['dli'], n and n['lo'], n and n['hi'])]}
             for s in st['spots']]
    return jsonify(spot=spot, suggestion=sug, unplaced=un, candidate=cand is not None, lights=len(st['lights']), need=n, spots=spots)

@app.route('/api/lights/preview')
def lights_preview():
    """Light at the leaves for a spot that is being set up: ?light=ID&distance=IN&hours=H&dim=PCT&units=N&plants=P-001,P-002"""
    c = db()
    try: lid = int(request.args.get('light', 0))
    except ValueError: abort(400, 'light must be a number')
    L = c.execute('SELECT * FROM lights WHERE id=?', (lid,)).fetchone()
    if not L: abort(404, 'That light is not in your list')
    s = spot_fields(request.args, partial=True)
    codes = [x for x in (request.args.get('plants') or '').split(',') if x]
    ps = [r for r in (c.execute('SELECT * FROM plants WHERE code=?', (x,)).fetchone() for x in codes) if r]
    ev = spot_eval(c, s, L, ps)
    try: here = int(request.args.get('spot') or 0) or None
    except ValueError: here = None
    if any(p['verdict'] not in ('good', 'unknown') for p in ev['plants']):      # 1.41.0: where a plant that does not fit would
        others = []
        for o in c.execute('SELECT * FROM light_spots').fetchall():
            Lo = c.execute('SELECT * FROM lights WHERE id=?', (o['light_id'],)).fetchone()
            pts = light_points(light_specs(Lo)) if Lo else []
            pp = ppfd_at(pts, o['distance_in']) if pts else None
            ops = [r for r in (c.execute('SELECT * FROM plants WHERE code=?', (x,)).fetchone() for (x,) in c.execute('SELECT plant_code FROM light_assign WHERE spot_id=?', (o['id'],))) if r]
            others.append({'id': o['id'], 'name': o['name'], 'dli': dli_of(pp, o['hours'], o['dim_pct']) if pp else None, 'fit': spot_fit(c, o, Lo, ops) if Lo else None})
        for p in ev['plants']: p['better'] = better_spot(others, p, here)
    ev['fit'] = spot_fit(c, s, L, ps)          # 1.56.0 (PLAN.md step 8d)
    return jsonify(ev)

def spot_fields(b, partial=False):
    name = re.sub(r'\s+', ' ', str(b.get('name', ''))).strip()[:60]
    if not name and not partial: abort(400, 'Give the spot a name, for example "Living room shelf"')
    units = int(_num(b, 'units', 1, 50, 'How many of this light') or 1)
    dist = _num(b, 'distance', 1, 120, 'Distance from the leaves (inches)', required=True)
    hours = _num(b, 'hours', 1, 24, 'Hours a day', required=True)
    dim = int(_num(b, 'dim', 1, 100, 'Brightness (%)') or 100)
    place = b.get('place')
    try: place = int(place) if place not in (None, '', 'null') else None
    except (TypeError, ValueError): abort(400, 'Choose a room or shelf from the list')
    level = str(b.get('level') or '')
    if level not in ('', 'top', 'lower') and not re.fullmatch(r'L([1-9]|1[0-9])', level): abort(400, 'Choose which level: the top, or a level counted from the bottom')
    holder = str(b.get('holder') or '')
    if holder not in ('',) + tuple(HOLDERS): abort(400, 'Choose what the bulb screws into: a clamp lamp, a lamp with a base, or a socket on a cord')
    return {'name': name, 'units': units, 'distance_in': dist, 'hours': hours, 'dim_pct': dim, 'notes': str(b.get('notes', '')).strip()[:300], 'place_id': place,
            'level': level, 'holder': holder}      # 1.56.0 (PLAN.md step 8): which level of a shelf, and what a bulb screws into

def spot_text(s, light_name, c=None):
    where = place_label(c, s['place_id']) if c is not None and s['place_id'] else None
    return '%s%s: %s%s, %g in from the leaves, %g hours a day%s' % (s['name'], ' (%s)' % where if where else '', '%d x ' % s['units'] if s['units'] > 1 else '', light_name,
                                                                    s['distance_in'], s['hours'], '' if s['dim_pct'] == 100 else ', %d%% brightness' % s['dim_pct'])

def light_places(c):
    """1.29.0: where a light spot can be: an inside room (its id negative) or a spot in one (its id), from Rooms and spots."""
    out = []
    for a in c.execute("SELECT * FROM areas WHERE side='in' ORDER BY home_id IS NOT NULL, home_id, sort, id").fetchall():
        hn = ''
        if a['home_id']: r = c.execute('SELECT name FROM locations WHERE id=?', (a['home_id'],)).fetchone(); hn = f' ({r[0]})' if r else ''
        room = a['name'] + hn
        out.append({'id': -a['id'], 'room': room, 'name': '', 'label': room})
        out += [{'id': sp['id'], 'room': room, 'name': sp['name'], 'label': room + ', ' + sp['name']}
                for sp in c.execute('SELECT * FROM spots WHERE area_id=? ORDER BY sort, id', (a['id'],))]
    return out

def place_label(c, pid):
    if not pid: return None
    if pid < 0:
        r = c.execute('SELECT name FROM areas WHERE id=?', (-pid,)).fetchone(); return r[0] if r else None
    r = c.execute('SELECT a.name, s.name FROM spots s JOIN areas a ON a.id=s.area_id WHERE s.id=?', (pid,)).fetchone()
    return (r[0] + ', ' + r[1]) if r else None

def check_place(c, pid):
    if pid is not None and not place_label(c, pid): abort(400, 'That room or shelf is not in the list any more')

def set_spot_plants(c, sid, spot_name, codes, who):
    old = {x for (x,) in c.execute('SELECT plant_code FROM light_assign WHERE spot_id=?', (sid,))}
    new = set(codes)
    for code in sorted(new - old):
        r = c.execute('SELECT id, code FROM plants WHERE code=?', (code,)).fetchone()
        if not r: abort(400, f'There is no plant {code}')
        prev = c.execute('SELECT s.name FROM light_assign a JOIN light_spots s ON s.id=a.spot_id WHERE a.plant_code=?', (code,)).fetchone()
        c.execute('INSERT OR REPLACE INTO light_assign(plant_code,spot_id,assigned_by,assigned_at) VALUES(?,?,?,?)', (code, sid, who, now()))
        audit_only(c, 'light', 'grow_light', prev[0] if prev else None, spot_name, who, 'Grow light: now in the spot ' + spot_name, r['id'], code)
    for code in sorted(old - new):
        r = c.execute('SELECT id FROM plants WHERE code=?', (code,)).fetchone()
        c.execute('DELETE FROM light_assign WHERE plant_code=? AND spot_id=?', (code, sid))
        audit_only(c, 'light', 'grow_light', spot_name, None, who, 'Grow light: taken out of the spot ' + spot_name, r['id'] if r else None, code)

@app.route('/api/lights/spots', methods=['POST'])
def light_spot_add():
    """Set up a spot: {name, light, units, distance, hours, dim, notes, plants: [codes]}"""
    c = db()
    b = request.get_json(silent=True) or {}
    s = spot_fields(b)
    L = c.execute('SELECT * FROM lights WHERE id=?', (int(_num(b, 'light', 1, 1e9, 'Light', required=True)),)).fetchone()
    if not L: abort(400, 'Choose one of your lights')
    who = editor()
    check_place(c, s['place_id'])
    sid = make_spot(c, s, L, [str(x) for x in b.get('plants') or []], who)
    c.commit()
    return jsonify(id=sid), 201

def make_spot(c, s, L, codes, who):
    sid = c.execute('INSERT INTO light_spots(name,light_id,units,distance_in,hours,dim_pct,notes,place_id,level,holder,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                    (s['name'], L['id'], s['units'], s['distance_in'], s['hours'], s['dim_pct'], s['notes'], s['place_id'], s.get('level') or '', s.get('holder') or '', who, now())).lastrowid
    audit_only(c, 'light', 'light_spot', None, spot_text(s, L['name'], c), who, 'Grow light spot set up: ' + spot_text(s, L['name'], c))
    set_spot_plants(c, sid, s['name'], codes, who)
    return sid

@app.route('/api/lights/spots/plan', methods=['POST'])
def light_spot_plan_all():
    """1.41.0: set up every spot of the suggested layout at once, as it stands now. Each can be changed afterwards."""
    c = db()
    st = lights_state(c)
    if not st['plan']: abort(400, 'There is no suggested layout: every plant that needs a light is in a spot.')
    who = editor(); names = {s['name'] for s in st['spots']}; made = []
    for p in st['plan']:
        L = c.execute('SELECT * FROM lights WHERE id=?', (p['light_id'],)).fetchone()
        name, k = p['name'], 2
        while name in names: name = '%s (%d)' % (p['name'], k); k += 1
        names.add(name)
        s = {'name': name, 'units': p['units'], 'distance_in': p['distance_in'], 'hours': p['hours'], 'dim_pct': p['dim_pct'], 'notes': '', 'place_id': None}
        made.append(make_spot(c, s, L, p['codes'], who))
    c.commit()
    return jsonify(made=len(made), plants=sum(len(p['codes']) for p in st['plan'])), 201

@app.route('/api/lights/spots/<int:i>/plants', methods=['POST'])
def light_spot_add_plants(i):
    """1.41.0: add plants to a spot without changing anything else: {add: [codes]} (from a plant's own page)"""
    c = db()
    s = c.execute('SELECT * FROM light_spots WHERE id=?', (i,)).fetchone()
    if not s: abort(404, 'That spot is not set up any more')
    add = [str(x) for x in (request.get_json(silent=True) or {}).get('add') or []]
    if not add: abort(400, 'Choose a plant to add')
    old = [x for (x,) in c.execute('SELECT plant_code FROM light_assign WHERE spot_id=?', (i,))]
    set_spot_plants(c, i, s['name'], old + [x for x in add if x not in old], editor())
    c.commit()
    return jsonify(ok=True, name=s['name'])

@app.route('/api/lights/spots/<int:i>', methods=['PUT', 'DELETE'])
def light_spot_one(i):
    c = db()
    old = c.execute('SELECT * FROM light_spots WHERE id=?', (i,)).fetchone()
    if not old: abort(404, 'That spot is not set up any more')
    L0 = c.execute('SELECT name FROM lights WHERE id=?', (old['light_id'],)).fetchone()
    who = editor()
    if request.method == 'DELETE':
        set_spot_plants(c, i, old['name'], [], who)
        c.execute('DELETE FROM light_spots WHERE id=?', (i,))
        audit_only(c, 'light', 'light_spot', spot_text(old, L0[0] if L0 else 'light', c), None, who, 'Grow light spot removed: ' + old['name'])
        c.commit()
        return jsonify(ok=True)
    b = request.get_json(silent=True) or {}
    s = spot_fields(b)
    L = c.execute('SELECT * FROM lights WHERE id=?', (int(_num(b, 'light', 1, 1e9, 'Light', required=True)),)).fetchone()
    if not L: abort(400, 'Choose one of your lights')
    check_place(c, s['place_id'])
    c.execute('UPDATE light_spots SET name=?,light_id=?,units=?,distance_in=?,hours=?,dim_pct=?,notes=?,place_id=?,level=?,holder=?,updated_by=?,updated_at=? WHERE id=?',
              (s['name'], L['id'], s['units'], s['distance_in'], s['hours'], s['dim_pct'], s['notes'], s['place_id'], s['level'], s['holder'], who, now(), i))
    a, z = spot_text(old, L0[0] if L0 else 'light', c), spot_text(s, L['name'], c)
    if a != z: audit_only(c, 'light', 'light_spot', a, z, who, 'Grow light spot changed: ' + z)
    if 'plants' in b: set_spot_plants(c, i, s['name'], [str(x) for x in b.get('plants') or []], who)
    c.commit()
    return jsonify(ok=True)

def place_fields(b):
    room = re.sub(r'\s+', ' ', str(b.get('room', ''))).strip()[:60]
    if not room: abort(400, 'Type the room, for example "Downstairs Living Room"')
    return room, re.sub(r'\s+', ' ', str(b.get('name', ''))).strip()[:60]

@app.route('/api/lights/places', methods=['POST'])
def light_place_add():
    """A room, or a shelf or table in a room (1.29.0: an inside area or a spot in it, at the main home): {room, name}."""
    c = db()
    room, name = place_fields(request.get_json(silent=True) or {})
    who = editor()
    a = c.execute("SELECT id FROM areas WHERE side='in' AND home_id IS NULL AND name=?", (room,)).fetchone()
    if a and not name: abort(409, f'"{room}" is already in the list')
    aid = a[0] if a else c.execute("INSERT INTO areas(home_id,side,name,sheltered,sort,created_by,created_at) VALUES(NULL,'in',?,1,(SELECT COALESCE(MAX(sort),0)+1 FROM areas),?,?)", (room, who, now())).lastrowid
    pid = -aid
    if name:
        if c.execute('SELECT 1 FROM spots WHERE area_id=? AND name=?', (aid, name)).fetchone(): abort(409, f'"{room}, {name}" is already in the list')
        pid = c.execute('INSERT INTO spots(area_id,name,sort,created_by,created_at) VALUES(?,?,(SELECT COALESCE(MAX(sort),0)+1 FROM spots),?,?)', (aid, name, who, now())).lastrowid
    audit_only(c, 'light', 'indoor_place', None, place_label(c, pid), who, 'Room or shelf added: ' + place_label(c, pid))
    c.commit()
    return jsonify(id=pid), 201

@app.route('/api/lights/places/<int(signed=True):i>', methods=['PUT', 'DELETE'])     # 1.41.1: signed, a room itself is minus its id
def light_place_one(i):
    """i is a spot's id, or minus an area's id (the room itself). Changes go to Rooms and spots."""
    c = db()
    old = place_label(c, i)
    if not old: abort(404, 'That room or shelf is not in the list')
    who = editor()
    if request.method == 'DELETE':
        if i < 0: return where_area_delete(c, -i, who)
        return where_spot_delete(c, i, who)
    room, name = place_fields(request.get_json(silent=True) or {})
    if i < 0: c.execute('UPDATE areas SET name=? WHERE id=?', (room, -i))
    else:
        aid = c.execute('SELECT area_id FROM spots WHERE id=?', (i,)).fetchone()[0]
        c.execute('UPDATE areas SET name=? WHERE id=?', (room, aid)); c.execute('UPDATE spots SET name=? WHERE id=?', (name or old.split(', ', 1)[-1], i))
    audit_only(c, 'light', 'indoor_place', old, place_label(c, i), who, 'Room or shelf renamed: ' + place_label(c, i))
    c.commit()
    return jsonify(ok=True)

# ---------------------------------------------------------------- 1.29.0: pots and catch trays, kept as items
CONT_KIND = {'pot': 'Pot', 'tray': 'Catch tray'}
CONT_SHAPES = {'circle': 'Circle', 'square': 'Square', 'rectangle': 'Rectangle'}
CONT_MATERIALS = ['Terracotta', 'Thin plastic', 'Thick plastic']

def cont_sqft(x):
    """Square feet it covers, a circle counted as the square around it (Ethan's choice), or None when the sizes are missing."""
    sh = x['shape']
    a = (x['dia_in'] ** 2 if x['dia_in'] else None) if sh == 'circle' else (x['len_in'] ** 2 if x['len_in'] else None) if sh == 'square' else \
        (x['len_in'] * x['wid_in'] if x['len_in'] and x['wid_in'] else None)
    return round(a / 144, 2) if a else None

def cont_size_words(x):
    sh = x['shape']; f = lambda v: ('%g' % v) if v is not None else '?'
    s = f'{f(x["dia_in"])} in across' if sh == 'circle' else f'{f(x["len_in"])} in square' if sh == 'square' else f'{f(x["len_in"])} by {f(x["wid_in"])} in'
    return s + (f', {f(x["height_in"])} in tall' if x['height_in'] else '')

def cont_dict(c, x):
    col = 'pot_id' if x['kind'] == 'pot' else 'tray_id'
    users = [{'code': r[0], 'name': r[1]} for r in c.execute(f"SELECT code, common_name FROM plants WHERE status='active' AND {col}=? ORDER BY code", (x['id'],))]
    d = {k: x[k] for k in ('id', 'kind', 'name', 'shape', 'dia_in', 'len_in', 'wid_in', 'height_in', 'material', 'qty', 'notes', 'updated_at', 'updated_by')}
    d.update(drainage=None if x['drainage'] is None else bool(x['drainage']), sqft=cont_sqft(x), size=cont_size_words(x), in_use=len(users), free=x['qty'] - len(users), plants=users,
             photos=[{'id': p['id'], 'file': p['file'], 'is_primary': bool(p['is_primary'])} for p in c.execute('SELECT * FROM container_photos WHERE container_id=? ORDER BY is_primary DESC, id', (x['id'],))])
    return d

def cont_fields(b, old=None):
    o = dict(old or {}); out = {}
    def num(k, label):
        if k not in b: return o.get(k)
        v = b[k]
        if v in (None, ''): return None
        try: x = round(float(v), 2)
        except (TypeError, ValueError): abort(400, f'{label} must be a number of inches')
        if not 0 < x <= 240: abort(400, f'{label} must be between 0 and 240 inches')
        return x
    out['name'] = re.sub(r'\s+', ' ', str(b.get('name', o.get('name') or ''))).strip()[:80]
    if not out['name']: abort(400, 'Give it a name, for example "8 in black nursery pot"')
    out['shape'] = b.get('shape', o.get('shape') or 'circle')
    if out['shape'] not in CONT_SHAPES: abort(400, 'Shape must be circle, square or rectangle')
    out['dia_in'] = num('dia_in', 'Across'); out['len_in'] = num('len_in', 'Length'); out['wid_in'] = num('wid_in', 'Width'); out['height_in'] = num('height_in', 'Height')
    out['material'] = re.sub(r'\s+', ' ', str(b.get('material', o.get('material') or ''))).strip()[:60]
    q = b.get('qty', o.get('qty', 1))
    try: out['qty'] = int(q)
    except (TypeError, ValueError): abort(400, 'How many you have must be a whole number')
    if not 0 <= out['qty'] <= 9999: abort(400, 'How many you have must be between 0 and 9999')
    if 'drainage' in b: out['drainage'] = None if b['drainage'] in (None, '') else (1 if b['drainage'] in (True, 1, '1', 'yes', 'true') else 0)
    else: out['drainage'] = o.get('drainage')
    out['notes'] = str(b.get('notes', o.get('notes') or '')).strip()[:1000]
    return out

@app.route('/api/containers', methods=['GET', 'POST'])
def containers():
    c = db()
    if request.method == 'GET':
        return jsonify(items=[cont_dict(c, x) for x in c.execute('SELECT * FROM containers ORDER BY kind, name')], kinds=CONT_KIND, shapes=CONT_SHAPES, materials=CONT_MATERIALS)
    b = request.get_json(silent=True) or {}
    kind = b.get('kind')
    if kind not in CONT_KIND: abort(400, 'Choose a pot or a catch tray')
    f = cont_fields(b); who = editor()
    if kind == 'tray': f['drainage'] = None
    cid = c.execute('INSERT INTO containers(kind,name,shape,dia_in,len_in,wid_in,height_in,drainage,material,qty,notes,created_by,created_at,updated_by,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    (kind, f['name'], f['shape'], f['dia_in'], f['len_in'], f['wid_in'], f['height_in'], f['drainage'], f['material'], f['qty'], f['notes'], who, now(), who, now())).lastrowid
    audit_only(c, 'container', kind, None, f['name'], who, f'{CONT_KIND[kind]} added: {f["name"]} ({f["qty"]})'); c.commit()
    return jsonify(cont_dict(c, c.execute('SELECT * FROM containers WHERE id=?', (cid,)).fetchone())), 201

@app.route('/api/containers/<int:cid>', methods=['PUT', 'DELETE'])
def container_one(cid):
    c = db(); who = editor()
    x = c.execute('SELECT * FROM containers WHERE id=?', (cid,)).fetchone()
    if not x: abort(404, 'That item is not in the list any more')
    if request.method == 'DELETE':
        col = 'pot_id' if x['kind'] == 'pot' else 'tray_id'
        n = c.execute(f"SELECT COUNT(*) FROM plants WHERE {col}=? AND status='active'", (cid,)).fetchone()[0]
        if n: abort(409, f'{n} plant{"s use" if n != 1 else " uses"} it. Give {"them" if n != 1 else "it"} another one first.')
        c.execute(f'UPDATE plants SET {col}=NULL WHERE {col}=?', (cid,))
        for p in c.execute('SELECT file FROM container_photos WHERE container_id=?', (cid,)).fetchall():
            try: os.remove(os.path.join(PHOTO_DIR, p[0]))
            except OSError: pass
        c.execute('DELETE FROM container_photos WHERE container_id=?', (cid,)); c.execute('DELETE FROM containers WHERE id=?', (cid,))
        audit_only(c, 'container', x['kind'], x['name'], None, who, f'{CONT_KIND[x["kind"]]} removed: {x["name"]}'); c.commit()
        return jsonify(ok=True)
    b = request.get_json(silent=True) or {}
    f = cont_fields(b, dict(x))
    if x['kind'] == 'tray': f['drainage'] = None
    ch = [k for k in f if (x[k] if x[k] is not None else '') != (f[k] if f[k] is not None else '')]
    if ch:
        c.execute('UPDATE containers SET ' + ','.join(f'{k}=?' for k in ch) + ',updated_by=?,updated_at=? WHERE id=?', [f[k] for k in ch] + [who, now(), cid])
        audit_only(c, 'container', x['kind'], ', '.join(f'{k} {x[k]}' for k in ch), ', '.join(f'{k} {f[k]}' for k in ch), who, f'{CONT_KIND[x["kind"]]} changed: {f["name"]}')
        c.commit()
    return jsonify(cont_dict(c, c.execute('SELECT * FROM containers WHERE id=?', (cid,)).fetchone()))

@app.route('/api/containers/<int:cid>/photos', methods=['POST'])
def container_photos(cid):
    c = db(); who = editor()
    x = c.execute('SELECT * FROM containers WHERE id=?', (cid,)).fetchone()
    if not x: abort(404, 'That item is not in the list any more')
    files = request.files.getlist('files')
    if not files: abort(400, 'Choose a photo')
    has = c.execute('SELECT 1 FROM container_photos WHERE container_id=? AND is_primary=1', (cid,)).fetchone()
    for i, f in enumerate(files):
        name = save_image(f)
        c.execute('INSERT INTO container_photos(container_id,file,is_primary,added_by,added_at) VALUES(?,?,?,?,?)', (cid, name, 0 if has or i else 1, who, now()))
    audit_only(c, 'container', x['kind'], None, f'{len(files)} photo(s)', who, f'Photo added to {x["name"]}'); c.commit()
    return jsonify(cont_dict(c, x)), 201

@app.route('/api/containers/photos/<int:pid>', methods=['DELETE'])
def container_photo_del(pid):
    c = db(); who = editor()
    p = c.execute('SELECT * FROM container_photos WHERE id=?', (pid,)).fetchone()
    if not p: abort(404, 'That photo is not there any more')
    c.execute('DELETE FROM container_photos WHERE id=?', (pid,))
    try: os.remove(os.path.join(PHOTO_DIR, p['file']))
    except OSError: pass
    if p['is_primary']: c.execute('UPDATE container_photos SET is_primary=1 WHERE id=(SELECT MIN(id) FROM container_photos WHERE container_id=?)', (p['container_id'],))
    audit_only(c, 'container', 'photo', p['file'], None, who, 'Photo removed from a pot or tray'); c.commit()
    return jsonify(ok=True)
