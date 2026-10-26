"""A fake picture checker (vision/service.py) for tests, with fake Pl@ntNet and Claude answers. It decides by the picture's
main colour: mostly red -> plant P-020, very sure; mostly green -> unsure between P-049, P-050 and P-051; mostly blue -> none
of yours, with species guesses. mock_server.py starts it on 127.0.0.1:8090 (MOCK_VISION_PORT)."""
import io
from flask import Flask, jsonify, request
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
