"""A fake picture checker (vision/service.py) for tests, with fake Pl@ntNet and Claude answers. It decides by the picture's
main colour: mostly red -> plant P-020, very sure; mostly green -> unsure between P-049, P-050 and P-051; mostly blue -> none
of yours, with species guesses. mock_server.py starts it on 127.0.0.1:8090 (MOCK_VISION_PORT)."""
import io
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
                            'scopes': {k: {'label': k, 'count': n} for k, n in (('common', 32542), ('texas', 4606), ('us', 18168), ('world', 335884))}})

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
    return jsonify(model='bioclip-2.5-vith14 (test)', likely_new=c == 'blue', scope=request.args.get('scope', 'common'), seconds=0.1,
                   matches=[{'code': k, 'score': s, 'photo': None, 'confidence': cf} for k, s, cf in m],
                   species=[x | {'probability': p} for x, p in zip(sp, (.41, .22, .09))], genera=[{'genus': sp[0]['genus'], 'probability': .5}])

@app.get('/names')
def names():
    q = request.args.get('q', '').lower()
    res = [x for x in SP if q in (x['scientific_name'] + ' ' + x['common_name']).lower()]
    if request.args.get('scope') == 'texas': res = [x for x in res if x['in_texas']]
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
    return jsonify(content=[{'type': 'text', 'text': '{"plant": true, "guesses": [{"scientific_name": "Lupinus texensis", "common_name": "Texas bluebonnet", '
                                                     '"family": "Fabaceae", "probability": 0.8, "why": "Palmate leaves and blue pea flowers."}], "photo_tip": "A photo of the flowers."}'}])


# 1.21.0: the library's browse, facets and species pages, and a stand-in for iNaturalist (/mock/inat/v1/...)
MORE = [{'scientific_name': f'Testia species{i:02d}', 'common_name': f'Test plant {i:02d}' if i % 3 else '', 'genus': 'Testia', 'family': 'Testaceae',
         'order': 'Testales', 'in_texas': i % 2 == 0, 'us_states': ['Texas'] if i % 2 == 0 else [], 'usda_symbol': '', 'kind': 'fern' if i % 5 == 0 else 'dicot'}
        for i in range(1, 61)]
ALL = [x | {'kind': {'Lupinus': 'dicot', 'Monstera': 'monocot', 'Agave': 'monocot'}[x['genus']]} for x in SP] + MORE

@app.get('/browse')
def browse():
    a = request.args
    r = [x for x in ALL if a.get('scope') != 'texas' or x['in_texas']]
    if a.get('q'): r = [x for x in r if a['q'].lower() in (x['scientific_name'] + ' ' + x['common_name']).lower()]
    if a.get('kind'): r = [x for x in r if x['kind'] == a['kind']]
    if a.get('family'): r = [x for x in r if x['family'].lower() == a['family'].lower()]
    if a.get('genus'): r = [x for x in r if x['genus'].lower() == a['genus'].lower()]
    if a.get('common') == '1': r = [x for x in r if x['common_name']]
    if a.get('state') == 'us': r = [x for x in r if x['us_states']]
    elif a.get('state'): r = [x for x in r if a['state'] in x['us_states']]
    if a.get('mine'): own = set(a.get('own', '').lower().split('|')); r = [x for x in r if x['scientific_name'].lower() in own]
    if a.get('sort') == 'sci': r = sorted(r, key=lambda x: x['scientific_name'])
    off, lim = int(a.get('offset', 0)), int(a.get('limit', 48))
    return jsonify(total=len(r), offset=off, results=r[off:off + lim])

@app.get('/facets')
def facets():
    return jsonify(total=len(ALL), kinds=[{'key': 'dicot', 'label': 'Flowering plants: broadleaf (dicots)', 'count': 50}, {'key': 'monocot', 'label': 'Flowering plants: grasses, lilies, palms, orchids (monocots)', 'count': 2},
                                         {'key': 'fern', 'label': 'Ferns and horsetails', 'count': 12}],
                   families=[{'name': 'Araceae', 'count': 1}, {'name': 'Fabaceae', 'count': 1}, {'name': 'Testaceae', 'count': 60}], states=['Florida', 'Hawaii'])

@app.get('/taxon')
def taxon():
    x = next((y for y in ALL if y['scientific_name'] == request.args.get('name')), None)
    if not x: return jsonify(error='That species is not in the list'), 404
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
