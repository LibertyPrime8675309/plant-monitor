"""The fertilizer log, and the fertilizers you have.
Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- fertilizer log
FERT_FORMS = ['liquid', 'powder', 'granular', 'slow-release', 'spikes', 'organic liquid', 'organic solid', 'foliar spray', 'other']
FERT_METHODS = ['water in', 'foliar spray', 'top-dress', 'mixed into soil', 'spike', 'other']
AMOUNT_UNITS = ['g', 'oz', 'ml', 'fl oz', 'tsp', 'tbsp']
WATER_UNITS = ['L', 'gal', 'qt', 'cup']
WATER_L = {'L': 1.0, 'gal': 3.78541, 'qt': 0.946353, 'cup': 0.236588}

def fert_calc(form, n, p, k, amount, unit, water, wunit):
    """Estimate how much nutrient went in. Dry spoon measures are taken as 4 g per tsp and 12 g per tbsp,
    liquid measures as 1 g per ml (liquid fertilizers are about 1.0 to 1.2). Treat results as estimates."""
    out = {'ppm_n': None, 'ppm_p2o5': None, 'ppm_k2o': None, 'n_grams': None}
    if not amount or not unit: return out
    liquid = form in ('liquid', 'organic liquid', 'foliar spray')
    if unit == 'g': g = amount
    elif unit == 'oz': g = amount * 28.3495
    elif unit == 'ml': g = amount
    elif unit == 'fl oz': g = amount * 29.5735
    elif unit == 'tsp': g = amount * (4.92892 if liquid else 4.0)
    elif unit == 'tbsp': g = amount * (14.7868 if liquid else 12.0)
    else: return out
    if n is not None: out['n_grams'] = round(g * n / 100, 3)
    L = water * WATER_L[wunit] if water and wunit in WATER_L else None
    if L:
        for key, pct in (('ppm_n', n), ('ppm_p2o5', p), ('ppm_k2o', k)):
            if pct is not None: out[key] = round(g * pct / 100 * 1000 / L, 1)
    return out

def _num(b, key, lo, hi, label, required=False):
    v = b.get(key)
    if v in (None, ''):
        if required: abort(400, f'{label} is required')
        return None
    try: x = round(float(v), 3)
    except (TypeError, ValueError): abort(400, f'{label} must be a number')
    if not lo <= x <= hi: abort(400, f'{label} must be between {lo} and {hi}')
    return x

def local_today(c):
    return datetime.now(tzinfo(location(c)['tz'])).date()

def fert_fields(c, b):
    product = re.sub(r'\s+', ' ', str(b.get('product', ''))).strip()[:80]
    if not product: abort(400, 'Type the fertilizer name')
    day = str(b.get('applied_on', '')).strip()
    try: d = datetime.strptime(day, '%Y-%m-%d').date()
    except ValueError: abort(400, 'Date must look like 2026-10-20')
    if d < datetime(2000, 1, 1).date() or d > local_today(c) + timedelta(days=1): abort(400, 'Date cannot be in the future')
    form = str(b.get('form') or 'liquid')
    if form not in FERT_FORMS: abort(400, 'Form must be one of: ' + ', '.join(FERT_FORMS))
    method = str(b.get('method') or 'water in')
    if method not in FERT_METHODS: abort(400, 'Method must be one of: ' + ', '.join(FERT_METHODS))
    n, p, k = (_num(b, x, 0, 100, lab) for x, lab in (('n', 'Nitrogen (N) %'), ('p', 'Phosphate (P) %'), ('k', 'Potash (K) %')))
    amount = _num(b, 'amount', 0, 100000, 'Amount')
    unit = b.get('amount_unit') or None
    if amount is not None and unit not in AMOUNT_UNITS: abort(400, 'Amount unit must be one of: ' + ', '.join(AMOUNT_UNITS))
    if amount is None: unit = None
    water = _num(b, 'water_amount', 0, 100000, 'Water amount')
    wunit = b.get('water_unit') or None
    if water is not None and wunit not in WATER_UNITS: abort(400, 'Water unit must be one of: ' + ', '.join(WATER_UNITS))
    if water is None: wunit = None
    calc = fert_calc(form, n, p, k, amount, unit, water, wunit)
    return dict(applied_on=day, product=product, form=form, n=n, p=p, k=k, amount=amount, amount_unit=unit, water_amount=water,
                water_unit=wunit, method=method, note=str(b.get('note', '')).strip()[:500], **calc)

FERT_COLS = ['applied_on', 'product', 'form', 'n', 'p', 'k', 'amount', 'amount_unit', 'water_amount', 'water_unit', 'method',
             'ppm_n', 'ppm_p2o5', 'ppm_k2o', 'n_grams', 'note']

def fert_text(f):
    npk = '-'.join('?' if f[x] is None else ('%g' % f[x]) for x in 'npk')
    dose = ''
    if f['amount'] is not None: dose = ', %g %s' % (f['amount'], f['amount_unit']) + (' per %g %s water' % (f['water_amount'], f['water_unit']) if f['water_amount'] else '')
    ppm = ', about %g ppm N' % f['ppm_n'] if f['ppm_n'] is not None else ''
    return f"{f['product']} ({npk}) on {f['applied_on']}, {f['method']}{dose}{ppm}" + (f". {f['note']}" if f['note'] else '')

def fert_summary(f):
    npk = '-'.join('?' if f[x] is None else ('%g' % f[x]) for x in 'npk')
    return f"{f['product']} ({npk}) on {f['applied_on']}"

@app.route('/api/fertilizer', methods=['GET', 'POST'])
def fertilizer():
    c = db()
    if request.method == 'GET':
        q, a = 'SELECT * FROM fertilizer_log WHERE 1=1', []
        for key, col, op in (('plant', 'plant_code', '='), ('from', 'applied_on', '>='), ('to', 'applied_on', '<=')):
            if request.args.get(key): q += f' AND {col}{op}?'; a.append(request.args[key])
        rows = c.execute(q + ' ORDER BY applied_on DESC, id DESC LIMIT 5000', a).fetchall()
        return jsonify([dict(r) for r in rows])
    b = request.get_json(silent=True) or {}
    codes = b.get('plants') or ([b['plant']] if b.get('plant') else [])
    if not isinstance(codes, list) or not codes: abort(400, 'Choose at least one plant')
    codes = list(dict.fromkeys(str(x) for x in codes))[:200]
    for code in codes: plant_row(c, code)
    f = fert_fields(c, b)
    who, bid = editor(), secrets.token_hex(6)
    ids = []
    for code in codes:
        cur = c.execute(f'INSERT INTO fertilizer_log(plant_code,{",".join(FERT_COLS)},batch_id,created_by,created_at) VALUES(?,{",".join("?" * len(FERT_COLS))},?,?,?)',
                        [code] + [f[x] for x in FERT_COLS] + [bid, who, now()])
        ids.append(cur.lastrowid)
        r = plant_row(c, code)
        audit_only(c, 'fertilizer', 'fertilizer_log', None, fert_text(f), who, 'Fertilized: ' + fert_summary(f), r['id'], code)
    c.commit()
    return jsonify(ids=ids, **{x: f[x] for x in ('ppm_n', 'ppm_p2o5', 'ppm_k2o', 'n_grams')}), 201

@app.route('/api/fertilizer/<int:i>', methods=['PUT', 'DELETE'])
def fertilizer_one(i):
    c = db()
    old = c.execute('SELECT * FROM fertilizer_log WHERE id=?', (i,)).fetchone()
    if not old: abort(404, 'entry not found')
    r = plant_row(c, old['plant_code']) if c.execute('SELECT 1 FROM plants WHERE code=?', (old['plant_code'],)).fetchone() else None
    who = editor()
    oldj = fert_text(old)
    if request.method == 'DELETE':
        c.execute('DELETE FROM fertilizer_log WHERE id=?', (i,))
        audit_only(c, 'fertilizer', 'fertilizer_log', oldj, None, who, 'Removed fertilizer entry: ' + fert_summary(old), r['id'] if r else None, old['plant_code'])
        c.commit()
        return jsonify(ok=True)
    f = fert_fields(c, request.get_json(silent=True) or {})
    c.execute(f'UPDATE fertilizer_log SET {",".join(x + "=?" for x in FERT_COLS)},updated_by=?,updated_at=? WHERE id=?', [f[x] for x in FERT_COLS] + [who, now(), i])
    audit_only(c, 'fertilizer', 'fertilizer_log', oldj, fert_text(f), who, 'Changed fertilizer entry: ' + fert_summary(f), r['id'] if r else None, old['plant_code'])
    c.commit()
    return jsonify(ok=True, **{x: f[x] for x in ('ppm_n', 'ppm_p2o5', 'ppm_k2o', 'n_grams')})

# ---- 1.11.0: the fertilizers you have, and which one suits each plant
def parse_ratio(s):
    """'3-1-2', '3:1:2', '24 8 16' -> (3.0, 1.0, 2.0); None when it is not three numbers with at least one above 0."""
    parts = [x for x in re.split(r'[\s\-:/,]+', str(s or '').strip()) if x]
    if len(parts) != 3: return None
    try: v = tuple(float(x) for x in parts)
    except ValueError: return None
    if any(x < 0 or x > 100 for x in v) or not sum(v): return None
    return v

FERT_LIQUID = ('liquid', 'organic liquid', 'foliar spray')
FERT_SOIL = ('granular', 'slow-release', 'spikes', 'organic solid')        # go on or in the mix, not into water
STRENGTH_PPM = {'Quarter strength': 40, 'Quarter to half strength': 55, 'Half strength': 75, 'Full strength': 150}
STRENGTH_SHARE = {'Quarter strength': 'a quarter of', 'Quarter to half strength': 'a quarter to half of', 'Half strength': 'half', 'Full strength': 'all of'}
NUTRIENT = ('nitrogen (N)', 'phosphate (P)', 'potash (K)')
FRACTIONS = {0.125: '⅛', 0.25: '¼', 0.375: '⅜', 0.5: '½', 0.625: '⅝', 0.75: '¾', 0.875: '⅞'}

def nice_amount(x):
    """A spoon measure people can actually use: eighths under 1, quarters up to 3, halves above."""
    step = 0.125 if x < 1 else 0.25 if x < 3 else 0.5
    v = max(step, round(x / step) * step)
    whole, frac = int(v), round(v - int(v), 3)
    return v, (str(whole) if whole else '') + FRACTIONS.get(frac, '' if not frac else '%g' % frac)

def ratio_words(v):
    m = min(x for x in v if x > 0)
    return ' : '.join('%g' % round(x / m, 1) for x in v)

def fert_match(need, prod):
    """How well a fertilizer's N-P-K fits the ratio a plant needs, compared as shares of the total."""
    rs, fs = [x / sum(need) for x in need], [x / sum(prod) for x in prod]
    diff = max(abs(a - b) for a, b in zip(rs, fs))
    quality = 'Matches' if diff <= 0.05 else 'Close' if diff <= 0.12 else 'Usable' if diff <= 0.22 else 'Not a good match'
    more = [NUTRIENT[i] for i in range(3) if fs[i] - rs[i] > 0.08]
    less = [NUTRIENT[i] for i in range(3) if rs[i] - fs[i] > 0.08]
    j = lambda xs: ' and '.join(xs)
    why = ''
    if more or less:
        why = 'It has ' + ' and '.join(x for x in (('more ' + j(more)) if more else '', ('less ' + j(less)) if less else '') if x) + ' than this plant needs.'
    return {'quality': quality, 'diff': round(diff, 3), 'why': why}

def fert_dose(prod, strength):
    """How much of this fertilizer to use for a plant that wants it at this strength. Mixed into water, the strongest of
    N, P and K is aimed at about 150 ppm for full strength (75 for half, 40 for a quarter), close to typical label rates."""
    if strength == 'None needed': return {'kind': 'none', 'words': 'This plant needs little or no fertilizer.'}
    if strength not in STRENGTH_PPM: return None
    share = STRENGTH_SHARE[strength]
    if prod['form'] in FERT_SOIL:
        return {'kind': 'soil', 'words': f"This one goes on or into the mix, not into water. Use {share} the amount on its label for the pot size."}
    vals = [prod[x] for x in 'npk']
    if any(x is None for x in vals) or not max(vals): return None
    target, top = STRENGTH_PPM[strength], max(vals)
    liquid = prod['form'] in FERT_LIQUID
    per_tsp = 4.92892 if liquid else 4.0                 # grams per teaspoon, as in fert_calc
    g_gal = target * WATER_L['gal'] / (top * 10)
    water = 1
    for w in (1, 2, 5):                                   # less than ⅛ tsp is hard to measure: make a bigger batch
        water = w
        if g_gal * w / per_tsp >= 0.125: break
    amount, amt_txt = nice_amount(g_gal * water / per_tsp)
    unit = 'tsp'
    if amount >= 3: unit = 'tbsp'; amount, amt_txt = nice_amount(amount / 3)
    calc = fert_calc(prod['form'], prod['n'], prod['p'], prod['k'], amount, unit, water, 'gal')
    per_l = g_gal / WATER_L['gal']
    metric = ('%s ml' if liquid else '%s g') % ('%.1f' % per_l if per_l < 10 else '%.0f' % per_l) + ' per liter'
    return {'kind': 'water', 'amount': amount, 'unit': unit, 'amount_text': amt_txt + ' ' + unit, 'water': water, 'water_unit': 'gal', 'metric': metric, 'target_ppm': target,
            'ppm_n': calc['ppm_n'], 'ppm_p2o5': calc['ppm_p2o5'], 'ppm_k2o': calc['ppm_k2o'],
            'words': f"Mix {amt_txt} {unit} into {water} gallon{'s' if water > 1 else ''} of water ({metric})."}

def fert_products(c):
    """Fertilizers you have: the ones saved on the Fertilizer page, plus every one ever logged, newest first.
    A saved one's N-P-K and type win over what was logged; the last logged dose is kept either way."""
    out, by = [], {}
    for r in c.execute('SELECT * FROM fertilizers ORDER BY COALESCE(updated_at, created_at) DESC'):
        d = {'id': r['id'], 'product': r['product'], 'form': r['form'], 'n': r['n'], 'p': r['p'], 'k': r['k'], 'note': r['note'],
             'saved': True, 'uses': 0, 'last_used': None, 'amount': None, 'amount_unit': None, 'water_amount': None, 'water_unit': None, 'method': None}
        out.append(d); by[r['product'].lower()] = d
    for r in c.execute('SELECT * FROM fertilizer_log ORDER BY applied_on DESC, id DESC'):
        key = r['product'].lower()
        d = by.get(key)
        if d is None:
            d = {'id': None, 'product': r['product'], 'form': r['form'], 'n': r['n'], 'p': r['p'], 'k': r['k'], 'note': '', 'saved': False,
                 'uses': 0, 'last_used': None, 'amount': None, 'amount_unit': None, 'water_amount': None, 'water_unit': None, 'method': None}
            out.append(d); by[key] = d
        d['uses'] += 1
        if d['last_used'] is None:
            d.update(last_used=r['applied_on'], amount=r['amount'], amount_unit=r['amount_unit'], water_amount=r['water_amount'],
                     water_unit=r['water_unit'], method=r['method'])
    out.sort(key=lambda d: (d['last_used'] or '', d['saved']), reverse=True)
    return out

def fert_need(p, products):
    """What a plant needs, and the fertilizer you have that fits it best."""
    need = parse_ratio(p['npk_ratio'])
    strength = p['fert_strength'] or ''
    out = {'code': p['code'], 'ratio': list(need) if need else None, 'ratio_text': p['npk_ratio'] or '', 'ratio_words': ratio_words(need) if need else '',
           'strength': strength, 'match': None, 'note': ''}
    if strength == 'None needed' and not need:
        out['note'] = 'This plant needs little or no fertilizer.'
        return out
    if not need:
        out['note'] = 'No fertilizer ratio set yet. Add one on the Edit page, under Nutrients.'
        return out
    usable = [f for f in products if f['n'] is not None and f['p'] is not None and f['k'] is not None and (f['n'] + f['p'] + f['k']) > 0]
    if not usable:
        out['note'] = 'None of your fertilizers have their N-P-K numbers yet. Add the ones you have under "Your fertilizers".' if products else \
                      'No fertilizers yet. Add the ones you have under "Your fertilizers", or log a feeding, and the closest one shows here.'
        return out
    best = min(usable, key=lambda f: (fert_match(need, (f['n'], f['p'], f['k']))['diff'], f['form'] in FERT_SOIL, -(f['uses'] or 0)))
    m = fert_match(need, (best['n'], best['p'], best['k']))
    out['match'] = {'product': best['product'], 'form': best['form'], 'n': best['n'], 'p': best['p'], 'k': best['k'],
                    'npk_text': '-'.join('%g' % best[x] for x in 'npk'), 'ratio_words': ratio_words((best['n'], best['p'], best['k'])),
                    **m, 'dose': fert_dose(best, strength or 'Half strength'), 'strength_assumed': not strength,
                    'last': ({'amount': best['amount'], 'amount_unit': best['amount_unit'], 'water_amount': best['water_amount'], 'water_unit': best['water_unit'],
                              'on': best['last_used']} if best['amount'] is not None else None)}
    return out

@app.route('/api/fertilizer/products', methods=['GET', 'POST'])
def fertilizer_products():
    """GET: fertilizers you have (saved and logged), newest first, with the last dose so the form can be filled in.
    POST: save one you have, even before you use it: {product, form, n, p, k, note}."""
    c = db()
    if request.method == 'GET': return jsonify(fert_products(c))
    f = fert_product_fields(request.get_json(silent=True) or {})
    if c.execute('SELECT 1 FROM fertilizers WHERE product=?', (f['product'],)).fetchone(): abort(409, f'"{f["product"]}" is already in your fertilizers')
    who = editor()
    cur = c.execute('INSERT INTO fertilizers(product,form,n,p,k,note,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)',
                    (f['product'], f['form'], f['n'], f['p'], f['k'], f['note'], who, now()))
    audit_only(c, 'fertilizer', 'fertilizer_product', None, fert_product_text(f), who, 'Fertilizer added to your list: ' + fert_product_text(f))
    c.commit()
    return jsonify(id=cur.lastrowid), 201

def fert_product_fields(b):
    product = re.sub(r'\s+', ' ', str(b.get('product', ''))).strip()[:80]
    if not product: abort(400, 'Type the fertilizer name')
    form = str(b.get('form') or 'liquid')
    if form not in FERT_FORMS: abort(400, 'Type must be one of: ' + ', '.join(FERT_FORMS))
    n, p, k = (_num(b, x, 0, 100, lab, required=True) for x, lab in (('n', 'Nitrogen (N) %'), ('p', 'Phosphate (P) %'), ('k', 'Potash (K) %')))
    if not (n + p + k): abort(400, 'At least one of N, P and K must be above 0')
    return {'product': product, 'form': form, 'n': n, 'p': p, 'k': k, 'note': str(b.get('note', '')).strip()[:300]}

def fert_product_text(f):
    return f"{f['product']} ({'-'.join('%g' % f[x] for x in 'npk')}, {f['form']})"

@app.route('/api/fertilizer/products/<int:i>', methods=['PUT', 'DELETE'])
def fertilizer_product_one(i):
    c = db()
    old = c.execute('SELECT * FROM fertilizers WHERE id=?', (i,)).fetchone()
    if not old: abort(404, 'That fertilizer is not in your list')
    who = editor()
    if request.method == 'DELETE':
        c.execute('DELETE FROM fertilizers WHERE id=?', (i,))
        audit_only(c, 'fertilizer', 'fertilizer_product', fert_product_text(old), None, who, 'Fertilizer removed from your list: ' + fert_product_text(old))
        c.commit()
        return jsonify(ok=True)
    f = fert_product_fields(request.get_json(silent=True) or {})
    if c.execute('SELECT 1 FROM fertilizers WHERE product=? AND id<>?', (f['product'], i)).fetchone(): abort(409, f'"{f["product"]}" is already in your fertilizers')
    c.execute('UPDATE fertilizers SET product=?,form=?,n=?,p=?,k=?,note=?,updated_by=?,updated_at=? WHERE id=?',
              (f['product'], f['form'], f['n'], f['p'], f['k'], f['note'], who, now(), i))
    audit_only(c, 'fertilizer', 'fertilizer_product', fert_product_text(old), fert_product_text(f), who, 'Fertilizer changed: ' + fert_product_text(f))
    c.commit()
    return jsonify(ok=True)

@app.route('/api/fertilizer/needs')
def fertilizer_needs():
    """For every active plant (or ?plant=CODE): the N-P-K ratio and strength it needs, and the closest fertilizer you have."""
    c = db()
    products = fert_products(c)
    q, a = "SELECT * FROM plants WHERE status='active'", []
    if request.args.get('plant'): q += ' AND code=?'; a.append(request.args['plant'])
    return jsonify(needs=[fert_need(r, products) for r in c.execute(q + ' ORDER BY code', a)], products=len(products))
