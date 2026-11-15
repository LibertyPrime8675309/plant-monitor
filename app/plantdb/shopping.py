"""Shopping: the stores, what they have, prices per unit, alerts, and each store's details and notes.
Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- 1.27.0: prices and stock for the wishlist (app/shops.py)
SHOPS_SCHEMA = """
CREATE TABLE IF NOT EXISTS shops(key TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, url TEXT NOT NULL, pages TEXT NOT NULL DEFAULT '[]',
  local INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 1, custom INTEGER NOT NULL DEFAULT 0, platform TEXT, status TEXT, error TEXT,
  checked_at TEXT, sort INTEGER NOT NULL DEFAULT 99);
CREATE TABLE IF NOT EXISTS offers(id INTEGER PRIMARY KEY AUTOINCREMENT, wish TEXT NOT NULL, shop TEXT NOT NULL, title TEXT NOT NULL, url TEXT NOT NULL,
  price REAL, currency TEXT, available INTEGER, detail TEXT, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, avail_since TEXT,
  gone INTEGER NOT NULL DEFAULT 0, UNIQUE(wish, shop, url, title));
CREATE TABLE IF NOT EXISTS offer_history(offer_id INTEGER NOT NULL, price REAL, available INTEGER, at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS offers_wish ON offers(wish, shop, gone);
CREATE INDEX IF NOT EXISTS offer_hist ON offer_history(offer_id, at);
CREATE TABLE IF NOT EXISTS wish_alert_marks(offer_id INTEGER NOT NULL, kind TEXT NOT NULL, price REAL, at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS wish_alerts(id INTEGER PRIMARY KEY AUTOINCREMENT, wish TEXT NOT NULL, offer_id INTEGER, kind TEXT NOT NULL, text TEXT NOT NULL,
  price REAL, url TEXT, shop TEXT, created_at TEXT NOT NULL, dismissed_by TEXT, dismissed_at TEXT);
CREATE TABLE IF NOT EXISTS shop_notes(id INTEGER PRIMARY KEY AUTOINCREMENT, shop TEXT NOT NULL, text TEXT NOT NULL, created_by TEXT NOT NULL, created_at TEXT NOT NULL);
"""
# 1.30.0: Shopping. Besides wishlist plants, the list holds garden supplies; each store can have its address, phone, hours and
# what it carries. home_id: the home a store you can visit is near (empty: the main home). online: it sells online, so it counts
# for every home.
SHOP_DETAIL_COLS = (('home_id', 'INTEGER'), ('online', 'INTEGER NOT NULL DEFAULT 0'), ('address', "TEXT NOT NULL DEFAULT ''"), ('phone', "TEXT NOT NULL DEFAULT ''"),
                    ('hours', "TEXT NOT NULL DEFAULT ''"), ('email', "TEXT NOT NULL DEFAULT ''"), ('website', "TEXT NOT NULL DEFAULT ''"),
                    ('carries', "TEXT NOT NULL DEFAULT '[]'"), ('lat', 'REAL'), ('lon', 'REAL'), ('details_src', "TEXT NOT NULL DEFAULT ''"),
                    ('details_at', 'TEXT'), ('geo_at', 'TEXT'))
SHOP_KINDS = [('plant', 'Wishlist plants'), ('pots', 'Pots and trays'), ('mix', 'Potting mixes'), ('amend', 'Amendments'), ('fert', 'Fertilizers'),
              ('pest', 'Pest control'), ('frost', 'Frost cloth and covers'), ('light', 'Grow lights and timers'), ('tools', 'Tools and labels')]
SHOP_KIND_WORD = dict(SHOP_KINDS)
SHOP_TEXT_MAX = {'address': 200, 'phone': 120, 'hours': 300, 'email': 120, 'website': 300, 'details_src': 200}
EBAY_API = os.environ.get('PLANTDB_EBAY_API', SH.EBAY_API).rstrip('/')
ETSY_API = os.environ.get('PLANTDB_ETSY_API', SH.ETSY_API).rstrip('/')
SHOP_UA = 'PlantRecord/1.27 (a home plant record checking its owner\'s wishlist, a few requests a day)'
SHOP_GAP = float(os.environ.get('PLANTDB_SHOP_GAP', '2'))          # seconds between requests to the same shop
SHOPQ = {'lock': threading.Lock(), 'thread': None, 'now': '', 'want': False, 'hosts': {}, 'ebay': None, 'done': 0, 'total': 0}

def shop_fetch(url, headers=None, data=None, timeout=25):
    host = urllib.parse.urlsplit(url).netloc
    wait = SHOPQ['hosts'].get(host, 0) + SHOP_GAP - time.time()
    if wait > 0: time.sleep(wait)
    SHOPQ['hosts'][host] = time.time()
    req = urllib.request.Request(url, data=data, headers={'User-Agent': SHOP_UA, 'Accept': 'application/json, text/html;q=0.9'} | (headers or {}),
                                 method='POST' if data is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return r.status, r.read(6_000_000)
    except urllib.error.HTTPError as e:
        return e.code, e.read(200_000) if e.fp else b''
    except (urllib.error.URLError, OSError, TimeoutError) as e:
        raise SH.ShopError('Could not reach the shop (' + str(getattr(e, 'reason', e))[:80] + ')')

def shop_json(url, headers=None):
    st, raw = shop_fetch(url, headers)
    if st in (401, 403) and headers: raise SH.ShopError('The shop refused the key. Check it and save it again.')
    if st == 429: raise SH.ShopError('The shop asked for fewer checks. It will be tried again next time.')
    if st >= 500: raise SH.ShopError(f'The shop had a problem (status {st}). It will be tried again next time.')
    try: return json.loads(raw) if st == 200 else None
    except ValueError: return None

def shop_text(url):
    st, raw = shop_fetch(url)
    if st != 200: raise SH.ShopError(f'The page did not open (status {st}). Check its address.')
    return raw.decode('utf-8', 'replace')

def shop_post_form(url, form, headers):
    st, raw = shop_fetch(url, headers | {'Content-Type': 'application/x-www-form-urlencoded'}, urllib.parse.urlencode(form).encode())
    try: return st, json.loads(raw)
    except ValueError: return st, {}

def offers_save(c, shop, wish, found):
    """Keeps what a shop has for one wishlist entry: new ones are added, changes go in the history, and ones that went are marked gone."""
    ts, keep = now(), set()
    found = sorted(found, key=lambda o: (not o['available'], o['price'] if o['price'] is not None else 1e9))[:20]
    for o in found:
        r = c.execute('SELECT * FROM offers WHERE wish=? AND shop=? AND url=? AND title=?', (wish, shop, o['url'], o['title'])).fetchone()
        av = None if o['available'] is None else int(bool(o['available']))
        if r:
            back = (r['gone'] or not r['available']) and av
            c.execute('UPDATE offers SET price=?, currency=?, available=?, detail=?, size=?, last_seen=?, gone=0, avail_since=? WHERE id=?',
                      (o['price'], o['currency'], av, o['detail'], o.get('size') or '', ts, ts if back else r['avail_since'], r['id']))
            if r['price'] != o['price'] or (r['available'] or 0) != (av or 0) or r['gone']:
                c.execute('INSERT INTO offer_history(offer_id,price,available,at) VALUES(?,?,?,?)', (r['id'], o['price'], av, ts))
            keep.add(r['id'])
        else:
            i = c.execute('INSERT INTO offers(wish,shop,title,url,price,currency,available,detail,size,first_seen,last_seen,avail_since) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                          (wish, shop, o['title'], o['url'], o['price'], o['currency'], av, o['detail'], o.get('size') or '', ts, ts, ts if av else None)).lastrowid
            c.execute('INSERT INTO offer_history(offer_id,price,available,at) VALUES(?,?,?,?)', (i, o['price'], av, ts))
            keep.add(i)
    for (i,) in c.execute('SELECT id FROM offers WHERE wish=? AND shop=? AND gone=0', (wish, shop)).fetchall():
        if i not in keep:
            c.execute('UPDATE offers SET gone=1 WHERE id=?', (i,))
            c.execute('INSERT INTO offer_history(offer_id,price,available,at) VALUES(?,?,?,?)', (i, None, 0, ts))

def wish_alerts_make(c):
    """One alert per wishlist entry per check, when something comes into stock or its price is at or under the one set (again only if it
    drops further). wish_alert_marks remembers what each listing has already been alerted for."""
    ts = now()
    money = lambda v: f'${v:,.2f}' if v is not None else 'price not shown'
    for w in c.execute("SELECT * FROM wishlist WHERE status='want' AND (alert_stock=1 OR max_price IS NOT NULL)").fetchall():
        nm, stock, cheap = w['common_name'] or w['name'], [], []
        for o in c.execute("SELECT o.*, s.name shop_name FROM offers o JOIN shops s ON s.key=o.shop WHERE o.wish=? AND o.gone=0 AND o.available=1 AND s.enabled=1 "
                           "ORDER BY o.price IS NULL, o.price", (w['name'],)).fetchall():
            if w['alert_stock'] and not c.execute("SELECT 1 FROM wish_alert_marks WHERE offer_id=? AND kind='stock' AND at>=?", (o['id'], o['avail_since'] or o['first_seen'])).fetchone():
                stock.append(o); c.execute('INSERT INTO wish_alert_marks(offer_id,kind,price,at) VALUES(?,?,?,?)', (o['id'], 'stock', o['price'], ts))
            # 1.30.0: a supply can be watched by its price per quart, pound or square foot
            u = offer_unit(o, w['kind']) if w['price_per'] == 'unit' else None
            val = (u['per'] if u and u['unit'] == SH.KIND_UNIT.get(w['kind']) else None) if w['price_per'] == 'unit' else o['price']
            if w['max_price'] is not None and val is not None and val <= w['max_price']:
                last = c.execute("SELECT MIN(price) FROM wish_alert_marks WHERE offer_id=? AND kind='price'", (o['id'],)).fetchone()[0]
                if last is None or val < last:
                    cheap.append((o, val)); c.execute('INSERT INTO wish_alert_marks(offer_id,kind,price,at) VALUES(?,?,?,?)', (o['id'], 'price', val, ts))
        if not (stock or cheap): continue
        cheap.sort(key=lambda x: x[1])
        per = f" a {SH.KIND_UNIT.get(w['kind'])}" if w['price_per'] == 'unit' else ''
        parts, top = [], (cheap[0][0] if cheap else stock[0])
        if cheap:
            parts.append(f"{money(cheap[0][1])}{per} at {cheap[0][0]['shop_name']}, at or under your {money(w['max_price'])}{per}" + (f" (and {len(cheap) - 1} more)" if len(cheap) > 1 else '') + '.')
        if stock:
            parts.append(f"In stock at {len(stock)} store{'s' if len(stock) > 1 else ''}: " + ', '.join(f"{o['shop_name']} {money(o['price'])}" for o in stock[:6]) + ('…' if len(stock) > 6 else '') + '.')
        c.execute('INSERT INTO wish_alerts(wish,offer_id,kind,text,price,url,shop,created_at) VALUES(?,?,?,?,?,?,?,?)',
                  (w['name'], top['id'], 'price' if cheap else 'stock', f"{nm}: " + ' '.join(parts), top['price'], top['url'], top['shop_name'], ts))

def wish_alerts_open(c):
    return [dict(r) for r in c.execute('SELECT * FROM wish_alerts WHERE dismissed_at IS NULL ORDER BY id DESC LIMIT 50')]

def shop_check_one(c, s, wants):
    """Reads one shop and keeps what it has for every wanted entry. Returns the status line shown on the Wishlist page."""
    if s['kind'] == 'api':
        if s['key'] == 'ebay':
            app_id, cert = setting(c, 'ebay_app_id', ''), setting(c, 'ebay_cert_id', '')
            if not (app_id and cert): return 'keys', 'Needs the owner\'s eBay keys (below).', None
            if not SHOPQ['ebay'] or SHOPQ['ebay'][1] < time.time() or SHOPQ['ebay'][2] != app_id:
                tok, exp = SH.ebay_token(shop_post_form, app_id, cert, EBAY_API); SHOPQ['ebay'] = (tok, exp, app_id)
            look = lambda t: SH.search_ebay(shop_json, SHOPQ['ebay'][0], t, EBAY_API)
        else:
            key = setting(c, 'etsy_key', '')
            if not key: return 'keys', 'Needs the owner\'s Etsy key (below).', None
            look = lambda t: SH.search_etsy(shop_json, key, t, ETSY_API)
        for w in wants:
            terms, found = SH.terms_for(w), []
            for t in terms[:2]:
                found += [o for o in look(t) if SH.matches(o['title'], terms) and not any(o['url'] == f['url'] for f in found)]
            offers_save(c, s['key'], w['name'], found)
        return 'ok', f'Searched for {len(wants)} wishlist {"entry" if len(wants) == 1 else "entries"}.', 'api'
    pages = json.loads(s['pages'] or '[]')
    kind = s['kind'] if s['kind'] != 'auto' else (s['platform'] or '')
    if kind == 'shopify': cat = SH.catalog_shopify(shop_json, s['url'])
    elif kind == 'woo': cat = SH.catalog_woo(shop_json, s['url'])
    elif kind == 'page': cat = SH.page_lines(shop_text, [s['url']] + pages)
    else: kind, cat = SH.detect(shop_json, shop_text, s['url'], pages)
    for w in wants:
        terms = SH.terms_for(w)
        found = SH.offers_from_lines(cat, terms) if kind == 'page' else [o for o in cat if SH.matches(o['title'], terms)]
        offers_save(c, s['key'], w['name'], found)
    if kind == 'page': return 'ok', f'Read {len(pages) + 1} page{"s" if pages else ""} for the names on your wishlist (this shop has no online store to read prices from).', kind
    return 'ok', f'Read its online store: {len(cat):,} products.', kind

def shops_worker():
    while True:
        with SHOPQ['lock']:
            if not SHOPQ['want']: SHOPQ['thread'] = None; SHOPQ['now'] = ''; return
            SHOPQ['want'] = False
        c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
        try:
            wants = [dict(r) for r in c.execute("SELECT * FROM wishlist WHERE status='want'")]
            todo = c.execute('SELECT * FROM shops WHERE enabled=1 ORDER BY sort, name').fetchall()
            SHOPQ['total'], SHOPQ['done'] = len(todo), 0
            jid = job_start('shops', f'{len(wants)} to look for', len(todo)); bad = []
            for s in todo:
                SHOPQ['now'] = s['name']; job_progress(jid, SHOPQ['done'], len(todo), s['name'])
                if not wants: break
                try: _, msg, kind = shop_check_one(c, s, wants); err = None
                except SH.ShopError as e: msg, kind, err = str(e), None, str(e); bad.append(s['name'])
                except Exception as e: msg, kind, err = 'Could not read it: ' + str(e)[:120], None, str(e)[:300]; bad.append(s['name'])
                c.execute('UPDATE shops SET status=?, error=?, checked_at=?, platform=COALESCE(?, platform) WHERE key=?', (msg, err, now(), kind, s['key']))
                c.commit(); SHOPQ['done'] += 1
            top = c.execute('SELECT COALESCE(MAX(id),0) FROM wish_alerts').fetchone()[0]
            wish_alerts_make(c)
            set_setting(c, 'shops_checked_at', now()); c.commit()
            try: push_shopping(c, [dict(r) for r in c.execute('SELECT * FROM wish_alerts WHERE id>? ORDER BY id', (top,))])   # 1.33.0
            except Exception as e: problem_exc('push', e, 'Shopping alerts could not be sent as notifications')
            job_end(jid, not bad, (f'{len(todo) - len(bad)} of {len(todo)} stores read; could not read ' + ', '.join(bad[:5])) if bad else f'{len(todo)} stores read')
        except Exception as e:
            job_end(jid, False, str(e)[:200])
            problem_exc('shops', e, 'The store check stopped part way')
        finally: c.close()

def shops_check_soon():
    with SHOPQ['lock']:
        SHOPQ['want'] = True
        if not SHOPQ['thread']:
            SHOPQ['thread'] = threading.Thread(target=shops_worker, daemon=True); SHOPQ['thread'].start()

def shops_loop():
    """Checks the shops on the schedule the owner set (every 12 hours unless changed). Off when set to 0."""
    time.sleep(90)
    while True:
        try:
            c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
            try:
                hours = float(setting(c, 'shops_hours', '12') or 0)
                last = setting(c, 'shops_checked_at', '')
                due = hours > 0 and (not last or (datetime.now(timezone.utc) - datetime.fromisoformat(last.replace('Z', '+00:00'))).total_seconds() >= hours * 3600)
                if due and c.execute("SELECT 1 FROM wishlist WHERE status='want'").fetchone(): shops_check_soon()
            finally: c.close()
        except Exception as e: problem_exc('shops', e, 'The store check could not be started')
        time.sleep(600)

def shop_row(r):
    d = dict(r); d['pages'] = json.loads(d['pages'] or '[]')
    try: d['carries'] = [k for k in json.loads(d.get('carries') or '[]') if k in SHOP_KIND_WORD]
    except ValueError: d['carries'] = []
    return d

OSM_URL = os.environ.get('PLANTDB_OSM_URL', 'https://nominatim.openstreetmap.org').rstrip('/')
OSM_UA = 'PlantRecord/1.30 (a home plant record finding its owner\'s local garden stores, a few requests a month)'
OSMQ = {'last': 0.0, 'lock': threading.Lock()}
def osm_search(params):
    """One OpenStreetMap (Nominatim) search, at most one a second as it asks. Returns its list of places, or []."""
    if os.environ.get('PLANTDB_OSM', '1') == '0': return []
    with OSMQ['lock']:
        wait = OSMQ['last'] + 1.1 - time.time()
        if wait > 0: time.sleep(wait)
        OSMQ['last'] = time.time()
    q = urllib.parse.urlencode({**params, 'format': 'jsonv2', 'limit': 5, 'addressdetails': 1, 'extratags': 1, 'countrycodes': 'us'})
    try:
        with urllib.request.urlopen(urllib.request.Request(f'{OSM_URL}/search?{q}', headers={'User-Agent': OSM_UA, 'Accept': 'application/json'}), timeout=20) as r:
            j = json.loads(r.read(2_000_000))
        return j if isinstance(j, list) else []
    except (urllib.error.URLError, OSError, ValueError, TimeoutError) as e:
        print('[stores] OpenStreetMap search failed:', e, flush=True); return []

def osm_address(a):
    a = a or {}
    street = ' '.join(x for x in (a.get('house_number'), a.get('road')) if x)
    town = a.get('city') or a.get('town') or a.get('village') or a.get('hamlet') or ''
    st = a.get('state', ''); st = US_STATE_ABBR.get(st, st)
    return ', '.join(x for x in (street, town, ' '.join(y for y in (st, a.get('postcode', '')) if y)) if x)

US_STATE_ABBR = {'Alabama': 'AL', 'Alaska': 'AK', 'Arizona': 'AZ', 'Arkansas': 'AR', 'California': 'CA', 'Colorado': 'CO', 'Connecticut': 'CT', 'Delaware': 'DE',
    'Florida': 'FL', 'Georgia': 'GA', 'Hawaii': 'HI', 'Idaho': 'ID', 'Illinois': 'IL', 'Indiana': 'IN', 'Iowa': 'IA', 'Kansas': 'KS', 'Kentucky': 'KY',
    'Louisiana': 'LA', 'Maine': 'ME', 'Maryland': 'MD', 'Massachusetts': 'MA', 'Michigan': 'MI', 'Minnesota': 'MN', 'Mississippi': 'MS', 'Missouri': 'MO',
    'Montana': 'MT', 'Nebraska': 'NE', 'Nevada': 'NV', 'New Hampshire': 'NH', 'New Jersey': 'NJ', 'New Mexico': 'NM', 'New York': 'NY',
    'North Carolina': 'NC', 'North Dakota': 'ND', 'Ohio': 'OH', 'Oklahoma': 'OK', 'Oregon': 'OR', 'Pennsylvania': 'PA', 'Rhode Island': 'RI',
    'South Carolina': 'SC', 'South Dakota': 'SD', 'Tennessee': 'TN', 'Texas': 'TX', 'Utah': 'UT', 'Vermont': 'VT', 'Virginia': 'VA', 'Washington': 'WA',
    'West Virginia': 'WV', 'Wisconsin': 'WI', 'Wyoming': 'WY'}

def shop_home(c, s):
    """The home a store you can visit is near (its home_id, else the main home)."""
    H = {h['id']: h for h in homes(c)}
    main = home_place(c)['id']
    return H.get(s['home_id'] if s['home_id'] is not None else main) or H.get(main)

def miles(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2): return None
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2
    return round(3958.8 * 2 * math.asin(math.sqrt(a)), 1)

def shop_full(c, r):
    d = shop_row(r)
    if d['local']:
        h = shop_home(c, r)
        d['home_name'] = h['name'] if h else ''; d['home_id_eff'] = h['id'] if h else None
        d['miles'] = miles(d['lat'], d['lon'], h.get('lat'), h.get('lon')) if h else None
    else: d['home_name'], d['home_id_eff'], d['miles'] = '', None, None
    d['maps'] = ('https://www.openstreetmap.org/search?query=' + urllib.parse.quote(d['name'] + ', ' + d['address'])) if d['address'] else ''
    d['notes_n'] = c.execute('SELECT COUNT(*) FROM shop_notes WHERE shop=?', (d['key'],)).fetchone()[0]
    return d

def shop_details_clean(b, r=None):
    """The details someone typed for a store: plain text, each to its own length; carries is a list of the Shopping kinds."""
    out = {}
    for k, n in SHOP_TEXT_MAX.items():
        if k in b: out[k] = re.sub(r'[ \t]+', ' ', str(b.get(k) or '')).strip()[:n]
    if 'website' in out and out['website'] and not re.match(r'^https?://\S+$', out['website']): out['website'] = 'https://' + out['website'].lstrip('/')
    if 'carries' in b:
        cs = b['carries'] if isinstance(b['carries'], list) else str(b['carries']).split(',')
        out['carries'] = json.dumps([k for k in SHOP_KIND_WORD if k in [str(x).strip() for x in cs]])
    return out

def shop_lookup(c, s, fill_all=False):
    """Looks a store up on OpenStreetMap by its name near its home (or by its address). Fills in what is still empty: the
    address, phone, hours, website and map position. Returns the names of what it filled."""
    h = shop_home(c, s) if s['local'] else None
    near = (h or {}).get('name', '')
    tries = []
    if s['address']: tries.append({'q': s['address']})
    tries.append({'q': f"{s['name']}, {near}" if near else s['name']})
    hit = None
    for p in tries:
        res = osm_search(p)
        if h and h.get('lat') is not None:
            res = [x for x in res if (miles(float(x.get('lat', 0)), float(x.get('lon', 0)), h['lat'], h['lon']) or 999) < 40]
        if res: hit = res[0]; break
    if not hit: return []
    t, got = hit.get('extratags') or {}, {}
    if not s['address'] or fill_all: got['address'] = osm_address(hit.get('address'))
    if not s['phone'] or fill_all: got['phone'] = t.get('phone') or t.get('contact:phone') or ''
    if not s['hours'] or fill_all: got['hours'] = (t.get('opening_hours') or '').replace(';', '; ')
    if not s['website'] or fill_all: got['website'] = t.get('website') or t.get('contact:website') or ''
    got = {k: v[:SHOP_TEXT_MAX[k]] for k, v in got.items() if v}
    sets = dict(got)
    try: sets['lat'], sets['lon'] = round(float(hit['lat']), 5), round(float(hit['lon']), 5)
    except (KeyError, TypeError, ValueError): pass
    sets['geo_at'] = now()
    if got: sets['details_src'] = 'OpenStreetMap'; sets['details_at'] = now()
    c.execute('UPDATE shops SET ' + ', '.join(f'{k}=?' for k in sets) + ' WHERE key=?', (*sets.values(), s['key']))
    return list(got)

def shops_geo():
    """Once, for each store you can visit that has an address but no map position: find it on the map, so its distance shows."""
    time.sleep(20)
    try:
        c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
        try:
            rows = c.execute("SELECT * FROM shops WHERE local=1 AND address<>'' AND lat IS NULL AND geo_at IS NULL").fetchall()
            if not rows: return
            jid = job_start('geo', f'{len(rows)} stores', len(rows))
            for i, s in enumerate(rows):
                job_progress(jid, i, len(rows), s['name'])
                res = osm_search({'q': s['address']})
                if res:
                    try: c.execute('UPDATE shops SET lat=?, lon=?, geo_at=? WHERE key=?', (round(float(res[0]['lat']), 5), round(float(res[0]['lon']), 5), now(), s['key']))
                    except (KeyError, TypeError, ValueError): c.execute('UPDATE shops SET geo_at=? WHERE key=?', (now(), s['key']))
                else: c.execute('UPDATE shops SET geo_at=? WHERE key=?', (now(), s['key']))
                c.commit()
            job_end(jid, True, f'{len(rows)} looked up')
        finally: c.close()
    except Exception as e:
        problem_exc('stores', e, 'Map positions for the stores could not be found')

@app.route('/api/shops/<key>')
def shop_page(key):
    """1.30.0: one store: its details, what you are watching that it has (with the price before, and the price per unit), and notes."""
    c = db()
    r = c.execute('SELECT * FROM shops WHERE key=?', (key,)).fetchone()
    if not r: abort(404, 'That store is not in the list')
    d = shop_full(c, r)
    items = []
    for o in c.execute("SELECT o.*, w.kind, w.common_name FROM offers o JOIN wishlist w ON w.name=o.wish WHERE o.shop=? AND o.gone=0 AND w.status='want' "
                       "ORDER BY o.available DESC, o.wish, o.price IS NULL, o.price", (key,)).fetchall():
        x = dict(o); x['unit'] = offer_unit(o, o['kind'])
        prev = c.execute('SELECT price, at FROM offer_history WHERE offer_id=? AND price IS NOT NULL AND (price<>? OR ? IS NULL) ORDER BY at DESC LIMIT 1',
                         (o['id'], o['price'], o['price'])).fetchone()
        x['before'] = dict(prev) if prev else None
        items.append(x)
    d['listings'] = items
    d['notes'] = [dict(n) for n in c.execute('SELECT * FROM shop_notes WHERE shop=? ORDER BY created_at DESC LIMIT 100', (key,))]
    return jsonify(d)

@app.route('/api/stores/<key>/details', methods=['PUT'])
def shop_details(key):
    """1.30.0: change a store's address, phone, hours, email, website, what it carries, or the home it is near. Anyone who can edit."""
    c = db()
    r = c.execute('SELECT * FROM shops WHERE key=?', (key,)).fetchone()
    if not r: abort(404, 'That store is not in the list')
    b = request.get_json(silent=True) or {}
    sets = shop_details_clean(b, r)
    if 'home_id' in b:
        hid = b['home_id']
        if hid in ('', None): sets['home_id'] = None
        else:
            try: hid = int(hid)
            except (TypeError, ValueError): abort(400, 'Choose one of your homes')
            if hid not in {h['id'] for h in homes(c)}: abort(400, 'Choose one of your homes')
            sets['home_id'] = None if hid == home_place(c)['id'] else hid
    if 'address' in sets and sets['address'] != r['address']: sets['lat'] = sets['lon'] = sets['geo_at'] = None
    if not sets: abort(400, 'Nothing to change')
    if any(k in sets for k in SHOP_TEXT_MAX): sets.setdefault('details_src', 'Typed in by ' + editor()); sets['details_at'] = now()
    c.execute('UPDATE shops SET ' + ', '.join(f'{k}=?' for k in sets) + ' WHERE key=?', (*sets.values(), key))
    audit_only(c, 'setting', 'shops', None, ', '.join(k for k in sets if k not in ('details_at', 'details_src', 'lat', 'lon', 'geo_at')), editor(), f'Store details changed: {r["name"]}')
    c.commit()
    if 'address' in sets and sets['address'] and os.environ.get('PLANTDB_OSM', '1') != '0':
        threading.Thread(target=shops_geo_one, args=(key,), daemon=True).start()
    return jsonify(shop_full(c, c.execute('SELECT * FROM shops WHERE key=?', (key,)).fetchone()))

def shops_geo_one(key):
    try:
        c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
        try:
            s = c.execute('SELECT * FROM shops WHERE key=?', (key,)).fetchone()
            res = osm_search({'q': s['address']}) if s and s['address'] else []
            if res: c.execute('UPDATE shops SET lat=?, lon=?, geo_at=? WHERE key=?', (round(float(res[0]['lat']), 5), round(float(res[0]['lon']), 5), now(), key))
            else: c.execute('UPDATE shops SET geo_at=? WHERE key=?', (now(), key))
            c.commit()
        finally: c.close()
    except Exception as e: problem_exc('stores', e, 'The store\'s map position could not be found')

@app.route('/api/stores/<key>/lookup', methods=['POST'])
def shop_lookup_api(key):
    c = db()
    r = c.execute('SELECT * FROM shops WHERE key=?', (key,)).fetchone()
    if not r: abort(404, 'That store is not in the list')
    got = shop_lookup(c, r)
    audit_only(c, 'setting', 'shops', None, ', '.join(got), editor(), f'Store looked up on OpenStreetMap: {r["name"]}' + (f' ({", ".join(got)} filled in)' if got else ' (nothing new)'))
    c.commit()
    return jsonify(shop_full(c, c.execute('SELECT * FROM shops WHERE key=?', (key,)).fetchone()) | {'filled': got})

@app.route('/api/stores/<key>/notes', methods=['POST'])
def shop_note_add(key):
    c = db()
    r = c.execute('SELECT * FROM shops WHERE key=?', (key,)).fetchone()
    if not r: abort(404, 'That store is not in the list')
    t = str((request.get_json(silent=True) or {}).get('text') or '').strip()[:1000]
    if not t: abort(400, 'Type the note first')
    i = c.execute('INSERT INTO shop_notes(shop,text,created_by,created_at) VALUES(?,?,?,?)', (key, t, editor(), now())).lastrowid
    audit_only(c, 'setting', 'shop_note', None, t[:200], editor(), f'Note about {r["name"]}')
    c.commit()
    return jsonify(id=i), 201

@app.route('/api/stores/notes/<int:i>', methods=['DELETE'])
def shop_note_rm(i):
    c = db()
    n = c.execute('SELECT * FROM shop_notes WHERE id=?', (i,)).fetchone()
    if not n: abort(404, 'That note is gone already')
    if n['created_by'] != editor() and me()['role'] != 'owner': abort(403, 'Only the person who wrote a note, or the owner, can remove it')
    c.execute('DELETE FROM shop_notes WHERE id=?', (i,))
    audit_only(c, 'setting', 'shop_note', n['text'][:200], None, editor(), 'Note about a store removed')
    c.commit()
    return jsonify(ok=True)

@app.route('/api/shopping')
def shopping_api():
    """1.30.0: everything on Shopping: wishlist plants and supplies, each with the cheapest listing at the stores that count for
    the home chosen (near=all or a home's id), the alerts, the kinds, the homes, and the stores you can visit for each kind."""
    c = db(); near = request.args.get('near', 'all')
    rows = [dict(r) for r in c.execute("SELECT * FROM wishlist ORDER BY status='got', added_at DESC")]
    for r in rows:
        r['terms'] = SH.terms_for(r)
        r['offers'] = offer_summary(c, r, near)
    extra, args = shop_near_sql(c, near)
    visit = [shop_full(c, s) for s in c.execute('SELECT s.* FROM shops s WHERE s.enabled=1 AND s.local=1' + extra + ' ORDER BY s.sort, s.name', args)]
    with SHOPQ['lock']: busy = bool(SHOPQ['thread'])
    return jsonify(items=rows, kinds=[{'key': k, 'label': v, 'unit': SH.KIND_UNIT.get(k, '') if SH.KIND_UNIT.get(k) != 'each' else ''} for k, v in SHOP_KINDS],
                   alerts=wish_alerts_open(c), checked=setting(c, 'shops_checked_at', ''), hours=setting(c, 'shops_hours', '12'), busy=busy,
                   homes=[{'id': h['id'], 'name': h['name']} for h in homes(c)],
                   visit=[{k: v[k] for k in ('key', 'name', 'phone', 'address', 'hours', 'carries', 'home_name', 'home_id_eff', 'miles', 'website', 'url', 'maps')} for v in visit],
                   stores=c.execute('SELECT COUNT(*) FROM shops WHERE enabled=1').fetchone()[0])

@app.route('/api/shops', methods=['GET', 'PUT', 'POST', 'DELETE'])
def shops_api():
    """GET: the shops, their last check and the settings. PUT {key, enabled, url, pages, name} changes one (owner). POST {name, url}
    adds a shop (owner). DELETE ?key= removes one the owner added."""
    c = db()
    if request.method != 'GET':
        b = request.get_json(silent=True) or {}
        if request.method == 'POST':
            name, url = str(b.get('name') or '').strip()[:80], str(b.get('url') or '').strip()[:300]
            if not name or not re.match(r'^https?://[^\s/]+(/\S*)?$', url): abort(400, 'Give the shop a name and its web address, starting with https://')
            key = 'custom-' + (re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')[:40] or 'shop')
            if c.execute('SELECT 1 FROM shops WHERE key=?', (key,)).fetchone(): abort(409, 'There is already a shop with that name.')
            local = 1 if b.get('local') else 0
            c.execute('INSERT INTO shops(key,name,kind,url,pages,local,online,custom,sort) VALUES(?,?,?,?,?,?,?,1,99)',
                      (key, name, 'auto', url, '[]', local, 1 if (b.get('online') or not local) else 0))
            sets = shop_details_clean(b)
            if local and b.get('home_id') not in (None, ''):
                try: hid = int(b['home_id'])
                except (TypeError, ValueError): hid = None
                if hid in {h['id'] for h in homes(c)} and hid != home_place(c)['id']: sets['home_id'] = hid
            if sets: c.execute('UPDATE shops SET ' + ', '.join(f'{k}=?' for k in sets) + ', details_src=?, details_at=? WHERE key=?', (*sets.values(), 'Typed in by ' + editor(), now(), key))
            audit_only(c, 'setting', 'shops', None, f'{name} ({url})', editor(), f'Shop added to the wishlist checks: {name}')
        elif request.method == 'DELETE':
            key = request.args.get('key', '')
            r = c.execute('SELECT * FROM shops WHERE key=? AND custom=1', (key,)).fetchone()
            if not r: abort(404, 'Only shops you added can be removed. Turn the others off instead.')
            c.execute('DELETE FROM shops WHERE key=?', (key,)); c.execute('DELETE FROM offers WHERE shop=?', (key,))
            audit_only(c, 'setting', 'shops', r['name'], None, editor(), f'Shop removed from the wishlist checks: {r["name"]}')
        else:
            if 'hours' in b:
                h = b.get('hours')
                if str(h) not in ('0', '6', '12', '24', '48'): abort(400, 'Choose how often: every 6, 12, 24 or 48 hours, or never')
                set_setting(c, 'shops_hours', str(h))
                audit_only(c, 'setting', 'shops_hours', None, str(h), editor(), 'Wishlist checks: how often changed')
            if b.get('key'):
                r = c.execute('SELECT * FROM shops WHERE key=?', (b['key'],)).fetchone()
                if not r: abort(404, 'No such shop')
                url = str(b.get('url', r['url']) or '').strip()[:300]
                if not re.match(r'^https?://[^\s/]+(/\S*)?$', url): abort(400, 'The address must start with https://')
                pages = b.get('pages', json.loads(r['pages']))
                pages = [p.strip()[:300] for p in (pages.split('\n') if isinstance(pages, str) else pages) if str(p).strip().startswith('http')][:12]
                en = 1 if b.get('enabled', r['enabled']) else 0
                c.execute('UPDATE shops SET enabled=?, url=?, pages=?, platform=CASE WHEN url<>? THEN NULL ELSE platform END WHERE key=?', (en, url, json.dumps(pages), url, r['key']))
                if not en: c.execute('UPDATE offers SET gone=1 WHERE shop=?', (r['key'],))
                audit_only(c, 'setting', 'shops', None, r['name'], editor(), f'Wishlist checks: {r["name"]} ' + ('changed' if en else 'turned off'))
        c.commit()
    rows = [shop_full(c, r) for r in c.execute('SELECT * FROM shops ORDER BY sort, name')]
    with SHOPQ['lock']: busy = bool(SHOPQ['thread'])
    return jsonify(shops=rows, kinds=[{'key': k, 'label': v} for k, v in SHOP_KINDS], homes=[{'id': h['id'], 'name': h['name']} for h in homes(c)],
                   hours=setting(c, 'shops_hours', '12'), checked=setting(c, 'shops_checked_at', ''), busy=busy, now=SHOPQ['now'],
                   done=SHOPQ['done'], total=SHOPQ['total'], have_ebay=bool(setting(c, 'ebay_app_id', '') and setting(c, 'ebay_cert_id', '')),
                   have_etsy=bool(setting(c, 'etsy_key', '')))

@app.route('/api/shops/keys', methods=['PUT', 'DELETE'])
def shops_keys():
    """The owner's eBay and Etsy keys. They are kept on this computer and never sent back to the browser."""
    c = db(); b = request.get_json(silent=True) or {}
    for k in (('ebay_app_id', 'ebay_cert_id') if b.get('shop') == 'ebay' else ('etsy_key',)):
        v = '' if request.method == 'DELETE' else str(b.get(k) or '').strip()[:200]
        if request.method == 'PUT' and not v: abort(400, 'Paste the key first.')
        set_setting(c, k, v)
    SHOPQ['ebay'] = None
    audit_only(c, 'setting', 'shop keys', None, b.get('shop'), editor(), f'Wishlist checks: {b.get("shop")} key ' + ('removed' if request.method == 'DELETE' else 'saved'))
    c.commit()
    return jsonify(ok=True)

@app.route('/api/wishlist/check', methods=['GET', 'POST'])
def shops_check():
    """POST: check every shop now (in the background). GET: how far it has got."""
    if request.method == 'POST':
        c = db()
        if not c.execute("SELECT 1 FROM wishlist WHERE status='want'").fetchone(): abort(400, 'Nothing is on Shopping to look for. Add something to watch first.')
        shops_check_soon()
        audit_only(c, 'library', 'shops', None, None, editor(), 'Wishlist: shops checked now'); c.commit()
    with SHOPQ['lock']: busy = bool(SHOPQ['thread'])
    return jsonify(busy=busy, now=SHOPQ['now'], done=SHOPQ['done'], total=SHOPQ['total'])

@app.route('/api/wishlist/offers')
def wishlist_offers():
    """Everything the shops have for one wishlist entry, cheapest first, with each one's price history."""
    c = db(); name = request.args.get('name', '')
    rows = [dict(r) for r in c.execute("SELECT o.*, s.name shop_name, s.local FROM offers o JOIN shops s ON s.key=o.shop WHERE o.wish=? "
                                       "ORDER BY o.gone, o.available DESC, o.price IS NULL, o.price", (name,))]
    w = c.execute('SELECT kind FROM wishlist WHERE name=?', (name,)).fetchone()
    for r in rows:
        r['history'] = [dict(h) for h in c.execute('SELECT price, available, at FROM offer_history WHERE offer_id=? ORDER BY at', (r['id'],))]
        r['unit'] = SH.unit_price(r['title'], r['price'], w['kind'] if w else 'plant', r.get('size') or '')   # 1.30.0
    return jsonify(offers=rows)

@app.route('/api/wishlist/alerts', methods=['GET', 'POST'])
def wishlist_alerts():
    """GET: the alerts not dismissed yet. POST {id} or {all: true}: dismiss."""
    c = db()
    if request.method == 'POST':
        b = request.get_json(silent=True) or {}
        if b.get('all'): c.execute('UPDATE wish_alerts SET dismissed_by=?, dismissed_at=? WHERE dismissed_at IS NULL', (editor(), now()))
        else: c.execute('UPDATE wish_alerts SET dismissed_by=?, dismissed_at=? WHERE id=? AND dismissed_at IS NULL', (editor(), now(), int(b.get('id') or 0)))
        c.commit()
    return jsonify(alerts=wish_alerts_open(c))

# ---------------------------------------------------------------- the wishlist (1.22.0; in library.py until 1.57.0)
@app.route('/api/wishlist', methods=['GET', 'PUT', 'DELETE'])
def wishlist_api():
    c = db()
    if request.method in ('PUT', 'DELETE'):
        b = request.get_json(silent=True) or {}
        name = str(b.get('name') or request.args.get('name') or '').strip()[:120]
        if not name: abort(400, 'Which species?')
        old = c.execute('SELECT * FROM wishlist WHERE name=?', (name,)).fetchone()
        if request.method == 'PUT' and old and str(b.get('rename') or '').strip() and str(b['rename']).strip()[:120] != name:   # 1.30.0: a supply's name can change
            new_name = str(b['rename']).strip()[:120]
            if old['kind'] == 'plant': abort(400, 'A wishlist plant keeps its species name. Change its common name instead.')
            if c.execute('SELECT 1 FROM wishlist WHERE name=?', (new_name,)).fetchone(): abort(409, f'"{new_name}" is already on the list.')
            c.execute('UPDATE wishlist SET name=? WHERE name=?', (new_name, name))
            c.execute('UPDATE offers SET wish=? WHERE wish=?', (new_name, name)); c.execute('UPDATE wish_alerts SET wish=? WHERE wish=?', (new_name, name))
            name = new_name; old = c.execute('SELECT * FROM wishlist WHERE name=?', (name,)).fetchone()
        if request.method == 'DELETE':
            c.execute('DELETE FROM wishlist WHERE name=?', (name,))
            c.execute('DELETE FROM offers WHERE wish=?', (name,))
            audit_only(c, 'library', 'wishlist', name, None, editor(), f'{name} taken off ' + ('Shopping' if old and old['kind'] != 'plant' else 'the wishlist'))
        else:
            st = b.get('status', old['status'] if old else 'want')
            if st not in ('want', 'got'): abort(400, 'status must be want or got')
            vals = (str(b.get('common_name', old['common_name'] if old else '') or '')[:120], str(b.get('notes', old['notes'] if old else '') or '').strip()[:2000],
                    str(b.get('where_seen', old['where_seen'] if old else '') or '').strip()[:300], st)
            mp = b.get('max_price', old['max_price'] if old else None)          # 1.27.0: price and stock alerts, and what to search the shops for
            if mp in ('', None): mp = None
            else:
                try: mp = round(float(mp), 2)
                except (TypeError, ValueError): abort(400, 'The price to watch for must be a number of dollars, such as 25')
                if not 0 < mp < 100000: abort(400, 'The price to watch for must be more than $0')
            more = (mp, 1 if b.get('alert_stock', old['alert_stock'] if old else 0) else 0,
                    re.sub(r'[ \t]+', ' ', str(b.get('search_words', old['search_words'] if old else '') or '')).strip()[:300])
            kind = str(b.get('kind', old['kind'] if old else 'plant') or 'plant')
            if kind not in SHOP_KIND_WORD: abort(400, 'Choose what kind of thing it is: ' + ', '.join(SHOP_KIND_WORD.values()))
            per = str(b.get('price_per', old['price_per'] if old else '') or '')
            if per not in ('', 'unit'): abort(400, 'price_per must be empty (the whole listing) or unit')
            if per == 'unit' and SH.KIND_UNIT.get(kind, 'each') == 'each': per = ''
            if old and old['kind'] == 'plant' and kind != 'plant': abort(400, 'A wishlist plant stays a plant.')
            more += (kind, per, str(b.get('source', old['source'] if old else '') or '')[:60])
            if old: c.execute('UPDATE wishlist SET common_name=?, notes=?, where_seen=?, status=?, max_price=?, alert_stock=?, search_words=?, kind=?, price_per=?, source=?, updated_by=?, updated_at=? WHERE name=?',
                              vals + more + (editor(), now(), name))
            else: c.execute('INSERT INTO wishlist(name,common_name,notes,where_seen,status,max_price,alert_stock,search_words,kind,price_per,source,added_by,added_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                            (name,) + vals + more + (editor(), now()))
            if old and (old['search_words'] or '') != more[2]: c.execute('DELETE FROM offers WHERE wish=?', (name,))   # new searches: start the list again
            where = 'the wishlist' if kind == 'plant' else 'Shopping'
            audit_only(c, 'library', 'wishlist', None, name, editor(), f'{name} ' + (f'updated on {where}' if old else f'added to {where}'))
        c.commit()
    rows = [dict(r) for r in c.execute("SELECT * FROM wishlist ORDER BY status='got', added_at DESC")]
    sp, _ = species_owned(c)
    for r in rows:
        r['yours'] = sp.get(r['name'].lower(), []) if r['kind'] == 'plant' else []
        r['terms'] = SH.terms_for(r)
        r['offers'] = offer_summary(c, r)
    return jsonify(wishlist=rows, alerts=wish_alerts_open(c), checked=setting(c, 'shops_checked_at', ''))

def shop_near_sql(c, near):
    """1.30.0: SQL (with its arguments) keeping the stores that count for a home: every online store, and the stores you can
    visit near that home. near: 'all', or a home's id."""
    if not near or near == 'all': return '', []
    try: hid = int(near)
    except (TypeError, ValueError): return '', []
    main = home_place(c)['id']
    return ' AND (s.online=1 OR s.local=0 OR COALESCE(s.home_id, ?)=?)', [main, hid]

def offer_unit(o, kind):
    return SH.unit_price(o['title'], o['price'], kind, o['size'] if 'size' in o.keys() else '')

def offer_summary(c, w, near='all'):
    """How many stores have it in stock, and the cheapest listing: by the price per quart, pound or square foot when the item is
    sold that way and the listing says its size, else by its price."""
    extra, args = shop_near_sql(c, near)
    rows = c.execute('SELECT o.*, s.name shop_name, s.local, s.online FROM offers o JOIN shops s ON s.key=o.shop WHERE o.wish=? AND o.gone=0 AND o.available=1 AND s.enabled=1' + extra,
                     [w['name']] + args).fetchall()
    kind = w['kind'] if 'kind' in w.keys() else 'plant'
    priced = []
    for o in rows:
        if o['price'] is None: continue
        d = dict(o); d['unit'] = offer_unit(o, kind); priced.append(d)
    want_unit = SH.KIND_UNIT.get(kind, 'each')
    by_unit = [d for d in priced if d['unit'] and d['unit']['unit'] == want_unit and want_unit != 'each']
    best = min(by_unit, key=lambda d: d['unit']['per']) if by_unit else (min(priced, key=lambda d: d['price']) if priced else None)
    return {'count': len(rows), 'shops': len({o['shop'] for o in rows}), 'best': best, 'unit': want_unit if want_unit != 'each' else ''}
