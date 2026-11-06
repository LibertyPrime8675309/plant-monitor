"""1.28.0: checking shops for the plants on the wishlist. No Flask here: server.py passes in fetch functions, so this is easy to test.
Each shop is read one of these ways:
  ebay / etsy   their official search services (keys saved by the owner)
  shopify       the store's public product list (/products.json): names, prices, in stock or not
  woo           a WooCommerce store's public Store API (/wp-json/wc/store/v1/products)
  page          for shops with no online store: the listed pages are read, and any line naming the plant is kept, with a price if
                one is on that line
'auto' tries shopify, then woo, then page, and remembers what worked."""
import base64, html as htmlmod, json, re, time, urllib.parse

DEFAULT_SHOPS = [   # key, name, kind ('api' or 'auto'), the shop's address, extra pages to read, local (a nursery near home)
    ('ebay', 'eBay', 'api', 'https://www.ebay.com/', [], False),
    ('etsy', 'Etsy', 'api', 'https://www.etsy.com/', [], False),
    ('stevesleaves', "Steve's Leaves", 'auto', 'https://stevesleaves.com/', [], False),
    ('gabriella', 'Gabriella Plants', 'auto', 'https://www.gabriellaplants.com/', [], False),
    ('logees', "Logee's", 'auto', 'https://www.logees.com/', [], False),
    ('costa', 'Costa Farms', 'auto', 'https://costafarms.com/', [], False),
    ('wildseed', 'Wildseed Farms', 'auto', 'https://www.wildseedfarms.com/', [], False),
    ('nativeseed', 'Native American Seed', 'auto', 'https://seedsource.com/', [], False),
    ('bakercreek', 'Baker Creek Heirloom Seeds', 'auto', 'https://www.rareseeds.com/', [], False),
    ('burpee', 'Burpee', 'auto', 'https://www.burpee.com/', [], False),
    ('northspore', 'North Spore', 'auto', 'https://northspore.com/', [], False),
    ('roundrockgc', 'Round Rock Garden Center', 'page', 'https://www.roundrockgardens.com/',
     ['https://www.roundrockgardens.com/newest-products'], True),
    ('snoopers', "Snooper's Nursery", 'page', 'https://snoopers-nursery.com/', [], True),
    ('cantu', 'Cantu Imports', 'page', 'https://cantuimports.com/nursery/',
     ['https://cantuimports.com/nursery/trees/', 'https://cantuimports.com/nursery/cacti/', 'https://cantuimports.com/nursery/perennials/',
      'https://cantuimports.com/nursery/shrubs/', 'https://cantuimports.com/nursery/palm-trees/'], True),
    ('mindseye', "Mind's Eye Plants", 'auto', 'https://minds-eye-plants.square.site/', [], True),
    ('barryhill', 'Barry Hill Garden Center', 'page', 'https://www.barryhillgc.com/plants',
     ['https://www.barryhillgc.com/plants/houseplants', 'https://www.barryhillgc.com/plants/tropicals', 'https://www.barryhillgc.com/plants/cacti-succulents',
      'https://www.barryhillgc.com/plants/perennials', 'https://www.barryhillgc.com/plants/annuals', 'https://www.barryhillgc.com/plants/trees-shrubs',
      'https://www.barryhillgc.com/specials'], True),
]
EBAY_API = 'https://api.ebay.com'
ETSY_API = 'https://openapi.etsy.com'
STOP = {'the', 'and', 'for', 'with', 'plant', 'plants', 'live', 'var', 'subsp', 'cultivar', 'sp', 'spp'}
PRICE_RE = re.compile(r'\$\s?(\d{1,4}(?:,\d{3})*(?:\.\d{2})?)')


class ShopError(Exception):
    """A shop could not be read; the message is shown to Ethan as it is."""


def words(s):
    return [w for w in re.findall(r"[a-z0-9]+", (s or '').lower().replace("'", '')) if len(w) >= 3 and w not in STOP]


def terms_for(item):
    """The searches for one wishlist entry: its own search words if set, else its common and scientific names."""
    own = [t.strip() for t in re.split(r'[\n;]', item.get('search_words') or '') if t.strip()]
    if own: return own
    out = []
    for t in (item.get('common_name'), item.get('name')):
        t = re.sub(r"\(.*?\)", '', t or '').strip()
        if t and words(t) and t.lower() not in [o.lower() for o in out]: out.append(t)
    return out


def matches(title, terms):
    """True when every word of one of the searches is in the title ("Texas bluebonnet" matches "Bluebonnet, Texas - 4 in. pot")."""
    tw = set(words(title))
    tw |= {w[:-1] for w in tw if w.endswith('s')}          # plural names in titles
    return any(words(t) and all(w in tw or (w.endswith('s') and w[:-1] in tw) for w in words(t)) for t in terms)


def root_of(url):
    p = urllib.parse.urlsplit(url)
    return f'{p.scheme}://{p.netloc}'


def _num(v):
    try: return round(float(str(v).replace(',', '')), 2)
    except (TypeError, ValueError): return None


# ---------- store catalogs (read once per check, then matched against every wishlist entry) ----------
def catalog_shopify(get_json, url, pages=8):
    root, out = root_of(url), []
    for n in range(1, pages + 1):
        j = get_json(f'{root}/products.json?limit=250&page={n}')
        if not isinstance(j, dict) or 'products' not in j:
            if n == 1: raise ShopError('not a Shopify store')
            break
        if not j['products']: break
        for p in j['products']:
            vs = p.get('variants') or []
            prices = [x for x in (_num(v.get('price')) for v in vs) if x is not None]
            cheap = min((v for v in vs if _num(v.get('price')) is not None), key=lambda v: (not v.get('available'), _num(v.get('price'))), default=None)
            out.append({'title': p.get('title', ''), 'url': f"{root}/products/{p.get('handle', '')}", 'price': min(prices) if prices else None,
                        'currency': 'USD', 'available': any(v.get('available') for v in vs) if vs else None,
                        'detail': ', '.join(sorted({v.get('title') for v in vs if v.get('title') and v.get('title') != 'Default Title'}))[:200],
                        # 1.30.0: the size of the cheapest variant, for the price per quart or pound
                        'size': (cheap.get('title') or '')[:80] if cheap and cheap.get('title') != 'Default Title' else ''})
        if len(j['products']) < 250: break
    return out


def catalog_woo(get_json, url, pages=10):
    root, out = root_of(url), []
    for n in range(1, pages + 1):
        j = get_json(f'{root}/wp-json/wc/store/v1/products?per_page=100&page={n}')
        if not isinstance(j, list):
            if n == 1: raise ShopError('not a WooCommerce store')
            break
        if not j: break
        for p in j:
            pr = p.get('prices') or {}
            unit = int(pr.get('currency_minor_unit', 2) or 0)
            price = _num(pr.get('price'))
            out.append({'title': htmlmod.unescape(p.get('name', '')), 'url': p.get('permalink', ''), 'price': round(price / 10 ** unit, 2) if price is not None else None,
                        'currency': pr.get('currency_code', 'USD'), 'available': bool(p.get('is_in_stock')), 'detail': ''})
        if len(j) < 100: break
    return out


def page_lines(get_text, urls):
    """For shops with no online store: each page's text, split into short lines (a product name and its price are usually on one)."""
    out = []
    for u in urls:
        t = get_text(u)
        t = re.sub(r'(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>', ' ', t)
        t = re.sub(r'(?i)<br\s*/?>|</(p|div|li|h[1-6]|tr|td|section|article|span|a)>', '\n', t)
        t = htmlmod.unescape(re.sub(r'<[^>]+>', ' ', t))
        for line in t.split('\n'):
            line = re.sub(r'\s+', ' ', line).strip()
            if 3 <= len(line) <= 300: out.append((u, line))
    if not out: raise ShopError('the page had no text to read')
    return out


def offers_from_lines(lines, terms):
    seen, out = set(), []
    for i, (u, line) in enumerate(lines):
        if not matches(line, terms): continue
        m = PRICE_RE.search(line) or (PRICE_RE.search(lines[i + 1][1]) if i + 1 < len(lines) and lines[i + 1][0] == u else None)
        k = (u, line.lower())
        if k in seen: continue
        seen.add(k)
        out.append({'title': line[:200], 'url': u, 'price': _num(m.group(1)) if m else None, 'currency': 'USD', 'available': True,
                    'detail': 'Named on the shop\'s page' + ('' if m else ' (no price on the page; call the shop)')})
    return out


# ---------- eBay and Etsy: a search for each wishlist entry ----------
def ebay_token(post_form, app_id, cert_id, api=EBAY_API):
    auth = base64.b64encode(f'{app_id}:{cert_id}'.encode()).decode()
    st, j = post_form(f'{api}/identity/v1/oauth2/token', {'grant_type': 'client_credentials', 'scope': 'https://api.ebay.com/oauth/api_scope'},
                      {'Authorization': 'Basic ' + auth})
    if st in (400, 401): raise ShopError('eBay refused the keys. Check the App ID and Cert ID (production keys, not sandbox).')
    if st != 200 or not j.get('access_token'): raise ShopError(f'eBay did not give a token (status {st}).')
    return j['access_token'], time.time() + int(j.get('expires_in', 7200)) - 120


def search_ebay(get_json_h, token, term, api=EBAY_API, limit=30):
    q = urllib.parse.urlencode({'q': term, 'limit': limit, 'filter': 'buyingOptions:{FIXED_PRICE},deliveryCountry:US'})
    j = get_json_h(f'{api}/buy/browse/v1/item_summary/search?{q}', {'Authorization': 'Bearer ' + token, 'X-EBAY-C-MARKETPLACE-ID': 'EBAY_US'})
    out = []
    for it in (j or {}).get('itemSummaries', []) or []:
        pr = it.get('price') or {}
        ship = ((it.get('shippingOptions') or [{}])[0].get('shippingCost') or {}).get('value')
        out.append({'title': it.get('title', ''), 'url': it.get('itemWebUrl', ''), 'price': _num(pr.get('value')), 'currency': pr.get('currency', 'USD'),
                    'available': True, 'detail': ', '.join(x for x in (it.get('condition'), f'shipping ${ship}' if ship not in (None, '0.00') else 'free shipping' if ship == '0.00' else '',
                                                                       (it.get('seller') or {}).get('username')) if x)[:200]})
    return out


def search_etsy(get_json_h, key, term, api=ETSY_API, limit=30):
    q = urllib.parse.urlencode({'keywords': term, 'limit': limit, 'sort_on': 'score'})
    j = get_json_h(f'{api}/v3/application/listings/active?{q}', {'x-api-key': key})
    out = []
    for it in (j or {}).get('results', []) or []:
        pr = it.get('price') or {}
        amt, div = _num(pr.get('amount')), pr.get('divisor') or 100
        out.append({'title': htmlmod.unescape(it.get('title', '')), 'url': it.get('url', ''), 'price': round(amt / div, 2) if amt is not None else None,
                    'currency': pr.get('currency_code', 'USD'), 'available': (it.get('quantity') or 0) > 0, 'detail': ''})
    return out


def detect(get_json, get_text, url, pages):
    """'shopify', 'woo' or 'page', and the first reading, for a shop set to 'auto'."""
    for kind, fn in (('shopify', catalog_shopify), ('woo', catalog_woo)):
        try: return kind, fn(get_json, url)
        except ShopError: pass
        except Exception: pass
    return 'page', page_lines(get_text, [url] + list(pages))


# ---------- 1.30.0: the price per quart, pound or square foot, read from a listing's name ----------
# Potting mixes and amendments come in quarts, gallons, cubic feet and litres; fertilizers in pounds and ounces (or, liquid, in
# fluid ounces and gallons); frost cloth by its sides in feet; pots and tools sometimes in packs. Dry quarts: 25.7 in a cubic foot.
KIND_UNIT = {'mix': 'quart', 'amend': 'quart', 'fert': 'pound', 'frost': 'square foot', 'pots': 'each', 'tools': 'each', 'pest': 'each', 'light': 'each'}
_N = r'(\d+(?:\.\d+)?(?:\s+\d/\d)?|\d/\d|\.\d+)'
def _val(t):
    t = t.strip()
    if ' ' in t: a, b = t.split(None, 1); return float(a) + _val(b)
    if '/' in t: a, b = t.split('/'); return float(a) / float(b) if float(b) else 0
    return float(t)
DRY = [(r'cu\.?\s*f(?:t|oot|eet)\.?|cubic\s*f(?:oo|ee)t|c\.?f\.?(?![a-z])', 25.71), (r'gal(?:lon)?s?\.?(?![a-z])', 4.0),
       (r'(?:dry\s*)?(?:quarts?|qts?\.?)(?![a-z])', 1.0), (r'(?:liters?|litres?|l)(?![a-z])', 0.908)]
WET = [(r'(?:fl\.?\s*oz|fluid\s*ounces?)\.?(?![a-z])', 1 / 32), (r'gal(?:lon)?s?\.?(?![a-z])', 4.0), (r'(?:quarts?|qts?\.?)(?![a-z])', 1.0),
       (r'pints?(?![a-z])', 0.5), (r'(?:liters?|litres?|l)(?![a-z])', 1.0567), (r'ml(?![a-z])', 0.0010567)]
WEIGHT = [(r'(?:lbs?|pounds?)\.?(?![a-z])', 1.0), (r'(?<!fl )(?<!fl\. )(?:oz|ounces?)\.?(?![a-z])', 1 / 16), (r'kgs?(?![a-z])', 2.2046), (r'(?:g|grams?)(?![a-z])', 1 / 453.6)]
def _first(text, table):
    best = None
    for pat, f in table:
        m = re.search(_N + r'\s*-?\s*(?:' + pat + ')', text, re.I)
        if m and (best is None or m.start() < best[0]):
            try: v = _val(m.group(1))
            except (ValueError, ZeroDivisionError): continue
            if v > 0: best = (m.start(), v * f, m.group(0).strip())
    return best

def unit_price(title, price, kind, size=''):
    """{'per': price per unit, 'unit': 'quart' | 'pound' | 'square foot' | 'each', 'size': the words it came from}, or None."""
    if price is None or kind not in KIND_UNIT: return None
    text = ' '.join(x for x in (size, title) if x).replace('\u00d7', 'x')
    if kind == 'frost':
        m = re.search(_N + r"\s*(?:ft|feet|foot|')?\.?\s*(?:x|by)\s*" + _N + r"\s*(?:ft|feet|foot|')", text, re.I)
        if m:
            area = _val(m.group(1)) * _val(m.group(2))
            if area > 0: return {'per': round(price / area, 3), 'unit': 'square foot', 'size': m.group(0).strip()}
        return None
    if kind in ('mix', 'amend', 'fert'):
        tables = [('pound', WEIGHT), ('quart', WET)] if kind == 'fert' else [('quart', DRY), ('pound', WEIGHT)]
        for unit, tab in tables:
            got = _first(text, tab)
            if got: return {'per': round(price / got[1], 3), 'unit': unit, 'size': got[2]}
        return None
    m = re.search(r'(?:pack|set|box|bag|case|lot)\s+of\s+(\d+)|(\d+)\s*-?\s*(?:pack|pk|count|ct|pcs|pieces|piece set)(?![a-z])', text, re.I)
    if m:
        n = int(m.group(1) or m.group(2))
        if n > 1: return {'per': round(price / n, 3), 'unit': 'each', 'size': m.group(0).strip()}
    return None
