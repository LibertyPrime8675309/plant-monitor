"""A fake picture checker (vision/service.py) for tests, with fake Pl@ntNet and Claude answers. It decides by the picture's
main colour: mostly red -> plant P-020, very sure; mostly green -> unsure between P-049, P-050 and P-051; mostly blue -> none
of yours, with species guesses. mock_server.py starts it on 127.0.0.1:8090 (MOCK_VISION_PORT)."""
import io, json
from flask import Flask, jsonify, request, Response
from PIL import Image, ImageStat
app = Flask(__name__)
STATE = {'state': 'ready'}
SP = [{'scientific_name': 'Lupinus texensis', 'common_name': 'Texas bluebonnet', 'genus': 'Lupinus', 'family': 'Fabaceae', 'order': 'Fabales',
       'in_texas': True, 'us_states': ['Texas'], 'usda_symbol': 'LUTE'},
      {'scientific_name': 'Monstera deliciosa', 'common_name': 'Swiss cheese plant', 'genus': 'Monstera', 'family': 'Araceae', 'order': 'Alismatales',
       'in_texas': False, 'us_states': ['Florida', 'Hawaii'], 'usda_symbol': 'MODE3'},
      {'scientific_name': 'Agave americana', 'common_name': 'century plant', 'genus': 'Agave', 'family': 'Asparagaceae', 'order': 'Asparagales',
       'in_texas': True, 'us_states': ['Arizona', 'California', 'Texas'], 'usda_symbol': 'AGAM'}]

def colour():
    f = request.files.get('image') or request.files.get('images')
    r, g, b = ImageStat.Stat(Image.open(io.BytesIO(f.read())).convert('RGB')).mean
    return 'red' if r > g and r > b else 'green' if g >= b else 'blue'

@app.get('/status')
def status():
    return jsonify(STATE | {'step': 'Ready' if STATE['state'] == 'ready' else 'Downloading the species fingerprints', 'done': 3, 'total': 1024,
                            'photos': 215, 'species': 335884, 'model': 'bioclip-2.5-vith14 (test)',
                            'scopes': {k: {'label': k, 'count': n} for k, n in (('common', 32542), ('texas', 4606), ('us', 18168), ('world', 335884), ('fungi', 49210))}
                                      | ({request.args['state']: {'label': request.args['state'][6:], 'count': 6105 if 'California' in request.args['state'] else 4606}} if request.args.get('state') else {}), 'fungi': 49210})

@app.post('/mock/state')
def set_state():
    STATE['state'] = request.get_json()['state']; return jsonify(STATE)

@app.post('/identify')
def identify():
    if STATE['state'] != 'ready': return jsonify(error='The vision service is still setting up: Downloading'), 503
    c = colour()
    m = {'red': [('P-020', .95, .93), ('P-021', .80, None), ('P-022', .78, None)],
         'green': [('P-049', .90, .62), ('P-050', .89, None), ('P-051', .88, None)],
         'blue': [('P-030', .60, .52), ('P-031', .58, None), ('P-032', .57, None)]}[c]
    sp = SP if c == 'blue' else SP[1:] + SP[:1]
    if request.args.get('scope') == 'fungi': sp = FUNGI[:3]
    n_pics = len(request.files.getlist('images')) + (1 if 'image' in request.files else 0)      # 1.39.0: several pictures of one plant
    extra = [] if request.args.get('scope') == 'fungi' else [{'scientific_name': f'Testia species{i:02d}', 'common_name': f'Test plant {i:02d}' if i % 3 else '', 'genus': 'Testia', 'family': 'Testaceae', 'order': 'Testales',
                                                               'in_texas': False, 'us_states': [], 'usda_symbol': '', 'probability': round(.07 - i * .007, 3), 'basis': []} for i in range(1, 8)]
    basis = {'Monstera deliciosa': ['house', 'looks'], 'Lupinus texensis': ['state'], 'Agave americana': ['own_gen']}
    return jsonify(model='bioclip-2.5-vith14 (test)', likely_new=c == 'blue', scope=request.args.get('scope', 'common'), seconds=0.1, pictures=n_pics, prior=True,
                   matches=[{'code': k, 'score': s, 'photo': None, 'confidence': cf} for k, s, cf in m],
                   species=[x | {'probability': p, 'basis': basis.get(x['scientific_name'], [])} for x, p in zip(sp, (.41, .22, .09))] + extra,
                   genera=[{'genus': sp[0]['genus'], 'probability': .5}, {'genus': sp[1]['genus'], 'probability': .2}, {'genus': 'Testia', 'probability': .1}])

@app.get('/names')
def names():
    q = request.args.get('q', '').lower()
    res = [x for x in SP if q in (x['scientific_name'] + ' ' + x['common_name']).lower()]
    if request.args.get('scope') in ('texas', 'state:Texas'): res = [x for x in res if x['in_texas']]
    elif str(request.args.get('scope', '')).startswith('state:'): res = [x for x in res if request.args['scope'][6:] in x['us_states']]
    return jsonify(results=res, total=len(res))

@app.post('/mock/plantnet')
def plantnet():
    if request.args.get('api-key') == 'bad-key-0000': return jsonify(message='Unauthorized'), 401
    return jsonify(results=[{'score': 0.87, 'species': {'scientificNameWithoutAuthor': 'Lupinus texensis', 'scientificNameAuthorship': 'Hook.',
                                                        'genus': {'scientificNameWithoutAuthor': 'Lupinus'}, 'family': {'scientificNameWithoutAuthor': 'Fabaceae'},
                                                        'commonNames': ['Texas bluebonnet', 'Bluebonnet']}}], remainingIdentificationRequests=499)

@app.post('/mock/claude')
def claude():
    if not request.headers.get('x-api-key'): return jsonify(error='no key'), 401
    body = json.dumps(request.get_json(silent=True) or {})
    if 'CARE SHEET' in body:                                  # 1.23.0: a care sheet for any species
        sheet = {'summary': 'A tough annual wildflower for full sun.', 'light': 'Full sun, at least 6 hours.', 'water': 'Let the soil dry between waterings.',
                 'soil': 'Lean, fast-draining soil.', 'temperature': 'Takes frost once established.', 'min_temp_f': 10, 'zone_low': '7a', 'zone_high': '10b',
                 'humidity': 'Low is fine.', 'feeding': 'None needed.', 'pruning': 'Leave seed pods to ripen.', 'propagation': 'Scarified seed sown in fall.',
                 'pests': 'Pill bugs on seedlings.', 'outdoors_here': 'Sow outdoors in Round Rock in October or November.', 'containers': 'Deep pots only.'}
        return jsonify(content=[{'type': 'text', 'text': json.dumps(sheet)}])
    if '\\"uses\\": a list' in body:                         # 1.27.0: uses, partners and propagation for any species
        fungus = 'This is a FUNGUS' in body
        f = {'summary': 'Breaks down dead wood.' if fungus else 'A tough native wildflower.',
             'uses': [{'kind': 'Soil', 'text': 'Breaks down wood chips into rich soil.', 'caution': ''},
                      {'kind': 'Food', 'text': 'Edible when cooked.', 'caution': ''}] if fungus else
                     [{'kind': 'Cut flowers', 'text': 'Lasts a week in a vase.', 'caution': ''}, {'kind': 'Dye', 'text': 'Blue-green dye from the flowers.', 'caution': 'Wear gloves.'}],
             'compost': {'verdict': 'Good', 'why': 'Soft and quick to rot.'},
             'partners_good': [{'name': 'Agave', 'sci': 'Agave', 'why': 'Same dry ground.', 'evidence': 'Same needs'}],
             'partners_bad': [{'name': 'Thirsty plants', 'sci': '', 'why': 'Too much water.', 'evidence': 'Different needs'}],
             'deters': [], 'attracts': [{'what': 'Bees', 'why': 'Nectar in spring.'}],
             'propagation': [{'method': 'Seed', 'when': 'Autumn', 'how': 'Scratch the seed and sow it in October.'}],
             'breeding': {'text': 'Crosses with other lupines.', 'cross_genera': [], 'patent': ''},
             'sources': [{'title': 'Lady Bird Johnson Wildflower Center', 'url': 'https://www.wildflower.org/'}, {'title': 'Bad', 'url': 'javascript:alert(1)'}]}
        return jsonify(content=[{'type': 'text', 'text': 'Here it is: ' + json.dumps(f)}])
    return jsonify(content=[{'type': 'text', 'text': '{"plant": true, "guesses": [{"scientific_name": "Lupinus texensis", "common_name": "Texas bluebonnet", '
                                                     '"family": "Fabaceae", "probability": 0.8, "why": "Palmate leaves and blue pea flowers."}], "photo_tip": "A photo of the flowers."}'}])


# 1.21.0: the library's browse, facets and species pages, and a stand-in for iNaturalist (/mock/inat/v1/...)
MORE = [{'scientific_name': f'Testia species{i:02d}', 'common_name': f'Test plant {i:02d}' if i % 3 else '', 'genus': 'Testia', 'family': 'Testaceae',
         'order': 'Testales', 'in_texas': i % 2 == 0, 'us_states': ['Texas'] if i % 2 == 0 else [], 'usda_symbol': '', 'kind': 'fern' if i % 5 == 0 else 'dicot'}
        for i in range(1, 61)]
ALL = [x | {'kind': {'Lupinus': 'dicot', 'Monstera': 'monocot', 'Agave': 'monocot'}[x['genus']]} for x in SP] + MORE
ALL.append({'scientific_name': 'Melia azedarach', 'common_name': 'chinaberry', 'genus': 'Melia', 'family': 'Meliaceae', 'order': 'Sapindales',   # 1.23.0: on the Texas noxious list
            'in_texas': True, 'us_states': ['Texas'], 'usda_symbol': 'MEAZ', 'kind': 'dicot'})
for x in ALL: x['kingdom'] = 'Plantae'
# 1.22.0: a few fungi, for the "Fungi worldwide" list and the mushroom finds
FUNGI = [{'scientific_name': n, 'common_name': cn, 'genus': n.split()[0], 'family': fam, 'order': 'Agaricales', 'in_texas': False, 'us_states': [],
          'usda_symbol': '', 'kind': 'mushroom', 'kingdom': 'Fungi'}
         for n, cn, fam in (('Leucocoprinus birnbaumii', 'flowerpot parasol', 'Agaricaceae'), ('Chlorophyllum molybdites', 'green-spored parasol', 'Agaricaceae'),
                            ('Amanita phalloides', 'death cap', 'Amanitaceae'), ('Agaricus campestris', 'meadow mushroom', 'Agaricaceae'))]
FUNGI.append({'scientific_name': 'Peziza vesiculosa', 'common_name': 'blistered cup', 'genus': 'Peziza', 'family': 'Pezizaceae', 'order': 'Pezizales',
              'in_texas': False, 'us_states': [], 'usda_symbol': '', 'kind': 'cupfungus', 'kingdom': 'Fungi'})

@app.route('/browse', methods=['GET', 'POST'])
def browse():
    a = dict(request.args)
    if request.method == 'POST': a.update(request.get_json(silent=True) or {})
    r = FUNGI if a.get('scope') == 'fungi' else [x for x in ALL if not str(a.get('scope', '')).startswith(('texas', 'state:')) or (a['scope'] in ('texas', 'state:Texas') and x['in_texas']) or a['scope'][6:] in x['us_states']]
    if a.get('q'): r = [x for x in r if a['q'].lower() in (x['scientific_name'] + ' ' + x['common_name']).lower()]
    if a.get('kind'): r = [x for x in r if x['kind'] == a['kind']]
    if a.get('family'): r = [x for x in r if x['family'].lower() == a['family'].lower()]
    if a.get('genus'): r = [x for x in r if x['genus'].lower() == a['genus'].lower()]
    if a.get('common') == '1': r = [x for x in r if x['common_name']]
    if a.get('state') == 'us': r = [x for x in r if x['us_states']]
    elif a.get('state'): r = [x for x in r if a['state'] in x['us_states']]
    if a.get('mine'): own = set(a.get('own', '').lower().split('|')); r = [x for x in r if x['scientific_name'].lower() in own]
    if a.get('only') is not None or a.get('only_genera'):
        only, gen = {n.lower() for n in a.get('only') or []}, {g.lower() for g in a.get('only_genera') or []}
        r = [x for x in r if x['scientific_name'].lower() in only or x['genus'].lower() in gen]
    if a.get('sort') == 'sci': r = sorted(r, key=lambda x: x['scientific_name'])
    off, lim = int(a.get('offset', 0)), int(a.get('limit', 48))
    return jsonify(total=len(r), offset=off, results=r[off:off + lim])

@app.get('/scope_names')
def scope_names():
    sc = request.args.get('scope', 'world')
    return jsonify(names=[x['scientific_name'] for x in (FUNGI if sc == 'fungi' else ALL) if not sc.startswith(('texas', 'state:')) or (sc in ('texas', 'state:Texas') and x['in_texas']) or sc[6:] in x['us_states']])

@app.get('/facets')
def facets():
    if request.args.get('scope') == 'fungi':
        return jsonify(total=len(FUNGI), kinds=[{'key': 'mushroom', 'label': 'Mushrooms, brackets, puffballs and jelly fungi', 'count': 4}, {'key': 'cupfungus', 'label': 'Cup fungi, morels and truffles', 'count': 1}],
                       families=[{'name': 'Agaricaceae', 'count': 3}, {'name': 'Amanitaceae', 'count': 1}, {'name': 'Pezizaceae', 'count': 1}], states=[])
    return jsonify(total=len(ALL), kinds=[{'key': 'dicot', 'label': 'Flowering plants: broadleaf (dicots)', 'count': 50}, {'key': 'monocot', 'label': 'Flowering plants: grasses, lilies, palms, orchids (monocots)', 'count': 2},
                                         {'key': 'fern', 'label': 'Ferns and horsetails', 'count': 12}],
                   families=[{'name': 'Araceae', 'count': 1}, {'name': 'Fabaceae', 'count': 1}, {'name': 'Testaceae', 'count': 60}], states=['Florida', 'Hawaii'])

@app.get('/taxon')
def taxon():
    x = next((y for y in ALL + FUNGI if y['scientific_name'] == request.args.get('name')), None)
    if not x: return jsonify(error='That species is not in the list'), 404
    if x['kingdom'] == 'Fungi':
        return jsonify(x | {'classification': [{'rank': 'Kingdom', 'name': 'Fungi'}, {'rank': 'Family', 'name': x['family']}, {'rank': 'Genus', 'name': x['genus']}],
                            'common_names': [x['common_name']], 'kind': 'Mushrooms, brackets, puffballs and jelly fungi',
                            'similar': [y | {'similarity': .9} for y in FUNGI if y is not x][:4]})
    return jsonify(x | {'classification': [{'rank': 'Kingdom', 'name': 'Plantae'}, {'rank': 'Family', 'name': x['family']}, {'rank': 'Genus', 'name': x['genus']}],
                        'common_names': [x['common_name']] if x['common_name'] else [], 'kind': 'Flowering plants',
                        'similar': [y | {'similarity': .9} for y in ALL if y is not x][:4]})

INAT_CALLS = []
def _ph(i):
    base = request.host_url.rstrip('/')
    return {'id': 1000 + i, 'attribution': f'(c) Test Person {i}, some rights reserved (CC BY-NC)', 'license_code': 'cc-by-nc',
            'medium_url': f'{base}/mock/inat/img/{i}/medium.jpg', 'url': f'{base}/mock/inat/img/{i}/square.jpg'}

@app.get('/mock/inat/v1/taxa')
def inat_taxa():
    INAT_CALLS.append(request.args.get('q'))
    q = request.args.get('q', '')
    if q.startswith('Testia species0'): return jsonify(results=[])          # no photo for these
    i = sum(map(ord, q)) % 50
    return jsonify(results=[{'id': 500 + i, 'name': q, 'rank': 'species', 'preferred_common_name': 'Swiss cheese plant' if 'Monstera' in q else '',
                             'observations_count': 1234, 'wikipedia_url': 'https://en.wikipedia.org/wiki/' + q.replace(' ', '_'), 'default_photo': _ph(i)}])

@app.get('/mock/inat/v1/taxa/<int:tid>')
def inat_taxon(tid):
    return jsonify(results=[{'id': tid, 'preferred_common_name': 'Swiss cheese plant', 'observations_count': 1234, 'wikipedia_url': 'https://en.wikipedia.org/wiki/Test',
                             'wikipedia_summary': '<b>A test plant</b> &amp; its relatives grow in shady forests.', 'taxon_photos': [{'photo': _ph(k)} for k in range(3)]}])

@app.get('/mock/inat/img/<int:i>/<size>.jpg')
def inat_img(i, size):
    from PIL import Image
    b = io.BytesIO(); Image.new('RGB', (1024 if size == 'large' else 500, 375), ((i * 40) % 255, 120, 60)).save(b, 'JPEG')
    return Response(b.getvalue(), mimetype='image/jpeg')

@app.get('/mock/inat/calls')
def inat_calls():
    return jsonify(INAT_CALLS)


# 1.23.0: iNaturalist species counts (Texas native and introduced, near home, flowering and fungi this month), ASPCA's lists, care sheets
def _sc(names):
    return [{'count': n, 'taxon': {'id': 9000 + i, 'name': nm, 'rank': 'species', 'preferred_common_name': cm}} for i, (nm, cm, n) in enumerate(names)]
SC = {'native': [('Lupinus texensis', 'Texas bluebonnet', 900), ('Agave americana', 'century plant', 300)] + [(f'Testia species{i:02d}', '', 10 + i) for i in range(2, 31, 2)],
      'introduced': [('Melia azedarach', 'chinaberry', 500), ('Testia species03', '', 20), ('Testia species05', '', 12)],
      'near': [('Lupinus texensis', 'Texas bluebonnet', 120), ('Melia azedarach', 'chinaberry', 40), ('Testia species02', '', 15),
               ('Chlorophyllum molybdites', 'green-spored parasol', 25), ('Leucocoprinus birnbaumii', 'flowerpot parasol', 6)],
      'bloom': [('Lupinus texensis', 'Texas bluebonnet', 30), ('Testia species02', '', 4)],
      'fungi': [('Chlorophyllum molybdites', 'green-spored parasol', 10), ('Leucocoprinus birnbaumii', 'flowerpot parasol', 3)]}

@app.get('/mock/inat/v1/observations/species_counts')
def inat_species_counts():
    a = request.args
    INAT_CALLS.append('species_counts ' + '&'.join(f'{k}={v}' for k, v in sorted(a.items())))
    key = ('native' if a.get('native') == 'true' else 'introduced' if a.get('introduced') == 'true' else 'bloom' if a.get('term_value_id') == '13'
           else 'fungi' if a.get('iconic_taxa') == 'Fungi' else 'near')
    rows = _sc(SC[key]); per, page = int(a.get('per_page', 500)), int(a.get('page', 1))
    return jsonify(total_results=len(rows), page=page, per_page=per, results=rows[(page - 1) * per:page * per])

# 1.28.0: places. Around 30 N it is Texas; around 39 N it is California; anything else is a country only (Mexico).
MPLACES = {18: {'id': 18, 'name': 'Texas', 'display_name': 'Texas, US', 'admin_level': 10, 'place_type': 8},
           14: {'id': 14, 'name': 'California', 'display_name': 'California, US', 'admin_level': 10, 'place_type': 8},
           1: {'id': 1, 'name': 'United States', 'display_name': 'United States', 'admin_level': 0, 'place_type': 12},
           6793: {'id': 6793, 'name': 'Mexico', 'display_name': 'Mexico', 'admin_level': 0, 'place_type': 12},
           1214: {'id': 1214, 'name': 'Williamson', 'display_name': 'Williamson County, TX, US', 'admin_level': 20, 'place_type': 9}}

@app.get('/mock/inat/v1/places/nearby')
def inat_nearby():
    lat = float(request.args.get('nelat', 0)); INAT_CALLS.append('places/nearby')
    std = [MPLACES[18], MPLACES[1], MPLACES[1214]] if 25 < lat < 36.5 else [MPLACES[14], MPLACES[1]] if 36.5 <= lat < 42 else [MPLACES[6793]]
    return jsonify(results={'standard': std, 'community': []})

@app.get('/mock/inat/v1/places/autocomplete')
def inat_autocomplete():
    q = request.args.get('q', '').lower()
    return jsonify(results=[p for p in MPLACES.values() if q in p['display_name'].lower()])

@app.get('/mock/inat/v1/places/<int:pid>')
def inat_place(pid):
    return jsonify(results=[MPLACES[pid]] if pid in MPLACES else [])

ASPCA = {'toxic': [('Swiss Cheese Plant (Ceriman, Cut-leaf Philodendron)', 'Monstera deliciosa', 'Araceae'), ('Century Plant (Agave)', 'Agave americana', 'Agavaceae'),
                   ('Chinaberry Tree (Bead Tree)', 'Melia azedarach', 'Meliaceae'), ('Alocasia (Elephant\'s Ear)', 'Alocasia spp.', 'Araceae')],
         'non-toxic': [('Texas Bluebonnet ()', 'Lupinus texensis', 'Fabaceae'), ('Test Plant One', 'Testia species01', 'Testaceae')]}

@app.get('/mock/aspca/<animal>-plant-list')
def aspca(animal):
    title = {'dogs': 'Dogs', 'cats': 'Cats', 'horse': 'Horses'}[animal]
    def items(rows): return ''.join(f'<div class="views-row"><span><a href="/pet-care/x/{n.lower()}">{c}</a> | <b>Scientific Names:</b> <i>{n}</i> | <b>Family:</b> {f}</span></div>' for c, n, f in rows)
    tox = ASPCA['toxic'] if animal != 'horse' else ASPCA['toxic'] + [ASPCA['non-toxic'][0]]
    non = ASPCA['non-toxic'] if animal != 'horse' else ASPCA['non-toxic'][1:]
    return Response(f'<html><body><h1>Toxic and Non-Toxic Plant List \u2014 {title}</h1><h2>Plants Toxic to {title}</h2>{items(tox)}'
                    f'<h2>Plants Non-Toxic to {title}</h2>{items(non)}</body></html>', mimetype='text/html')


# 1.27.0: stand-in shops for the wishlist checks. A Shopify store answers on 127.0.0.1, a WooCommerce store on localhost (shops
# are told apart by their address), a nursery page, and eBay and Etsy's search services. /mock/shop/set changes the stock.
SHOP = {'bluebonnet_price': '4.95', 'bluebonnet_stock': True, 'pumice_price': '13.99', 'calls': []}

@app.get('/products.json')
def shop_shopify():
    SHOP['calls'].append('shopify ' + request.host)
    if not request.host.startswith('127.0.0.1'): return 'not found', 404
    if request.args.get('page', '1') != '1': return jsonify(products=[])
    return jsonify(products=[
        {'title': 'Texas Bluebonnet (Lupinus texensis) seed packet', 'handle': 'texas-bluebonnet', 'variants': [
            {'title': '1 oz', 'price': SHOP['bluebonnet_price'], 'available': SHOP['bluebonnet_stock']}, {'title': '1 lb', 'price': '39.00', 'available': False}]},
        {'title': 'Monstera deliciosa, 6 inch pot', 'handle': 'monstera-6', 'variants': [{'title': 'Default Title', 'price': '29.99', 'available': False}]},
        {'title': 'Pothos Golden', 'handle': 'pothos', 'variants': [{'title': 'Default Title', 'price': '12.00', 'available': True}]},
        # 1.30.0: garden supplies, for Shopping
        {'title': 'Pumice 1/4 in', 'handle': 'pumice', 'variants': [{'title': '0.5 cu ft', 'price': SHOP.get('pumice_price', '13.99'), 'available': True}, {'title': '2 cu ft', 'price': '39.99', 'available': True}]},
        {'title': 'Perlite, coarse 8 qt', 'handle': 'perlite', 'variants': [{'title': 'Default Title', 'price': '9.00', 'available': True}]},
        {'title': 'Frost protection blanket 10 x 12 ft', 'handle': 'frost-cloth', 'variants': [{'title': 'Default Title', 'price': '18.99', 'available': True}]}])

@app.get('/wp-json/wc/store/v1/products')
def shop_woo():
    SHOP['calls'].append('woo ' + request.host)
    if not request.host.startswith('localhost'): return 'not found', 404
    if request.args.get('page', '1') != '1': return jsonify([])
    return jsonify([{'name': 'Bluebonnets, Texas &amp; 4 inch', 'permalink': 'http://localhost:8090/shop/bluebonnet', 'prices': {'price': '799', 'currency_code': 'USD', 'currency_minor_unit': 2},
                     'is_in_stock': True}])

@app.get('/mock/shop/page')
def shop_page():
    return ('<html><body><h1>Fall sale</h1><ul><li>1 gallon Mexican Heather – $3.00</li><li>4 inch Texas bluebonnet &ndash; $2.50</li>'
            '<li>Agave americana, large</li></ul><script>var x="Texas bluebonnet $1"</script></body></html>')

@app.post('/mock/shop/set')
def shop_set():
    b = request.get_json(silent=True) or {}
    SHOP.update({k: v for k, v in b.items() if k in SHOP})
    return jsonify(ok=True)

@app.post('/mock/ebay/identity/v1/oauth2/token')
def ebay_token():
    if request.headers.get('Authorization') != 'Basic ' + __import__('base64').b64encode(b'app-1:cert-1').decode(): return jsonify(error='invalid_client'), 401
    return jsonify(access_token='tok-1', expires_in=7200)

@app.get('/mock/ebay/buy/browse/v1/item_summary/search')
def ebay_search():
    if request.headers.get('Authorization') != 'Bearer tok-1': return jsonify(errors=[{'message': 'bad token'}]), 401
    q = request.args.get('q', '').lower()
    items = [{'title': 'LIVE Texas Bluebonnet plant 4in pot', 'itemWebUrl': 'https://www.ebay.com/itm/1', 'price': {'value': '9.50', 'currency': 'USD'}, 'condition': 'New',
              'seller': {'username': 'txnative'}, 'shippingOptions': [{'shippingCost': {'value': '0.00'}}]},
             {'title': 'Bluebonnet print poster', 'itemWebUrl': 'https://www.ebay.com/itm/2', 'price': {'value': '5.00', 'currency': 'USD'}}] if 'bluebonnet' in q else []
    return jsonify(itemSummaries=items)

@app.get('/mock/etsy/v3/application/listings/active')
def etsy_search():
    if request.headers.get('x-api-key') != 'etsy-1': return jsonify(error='Invalid API key'), 403
    q = request.args.get('keywords', '').lower()
    res = [{'title': 'Texas bluebonnet seeds, 500 count', 'url': 'https://www.etsy.com/listing/9', 'price': {'amount': 650, 'divisor': 100, 'currency_code': 'USD'}, 'quantity': 3}] if 'bluebonnet' in q else []
    return jsonify(count=len(res), results=res)


# 1.30.0: a stand-in for OpenStreetMap's place search (Nominatim), for store addresses and map positions
OSM = {'calls': []}
@app.get('/mock/osm/search')
def osm_search():
    q = request.args.get('q', ''); OSM['calls'].append(q)
    if 'Weiss' in q or 'Maltman' in q:
        return jsonify([{'lat': '39.2290', 'lon': '-121.0580', 'display_name': 'Weiss Brothers Nursery, 615, Maltman Drive, Grass Valley',
                         'address': {'house_number': '615', 'road': 'Maltman Drive', 'city': 'Grass Valley', 'state': 'California', 'postcode': '95945'},
                         'extratags': {'opening_hours': 'Mo-Sa 08:00-17:00;Su 09:00-16:00', 'phone': '+1 530-273-5814', 'website': 'http://www.weissbrothersnursery.com/'}}])
    if 'Far Away' in q:
        return jsonify([{'lat': '47.6', 'lon': '-122.3', 'address': {'city': 'Seattle'}, 'extratags': {'phone': '1'}}])
    if 'Round Rock' in q or 'TX' in q:
        return jsonify([{'lat': '30.5100', 'lon': '-97.6800', 'address': {'city': 'Round Rock', 'state': 'Texas'}, 'extratags': {}}])
    if 'CA' in q or 'Nevada City' in q or 'Grass Valley' in q:
        return jsonify([{'lat': '39.2200', 'lon': '-121.0600', 'address': {'city': 'Grass Valley', 'state': 'California'}, 'extratags': {}}])
    return jsonify([])

@app.get('/mock/osm/calls')
def osm_calls():
    return jsonify(OSM)
