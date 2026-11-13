"""For the layout previews (proto/first-screen): puts the test record's plants on spots, the way "Plants without a spot" does on
Ethan's PC, so pages that group by room and spot have something to group. The test record keeps where each plant is as words only.
python3 dev/test/preview_spots.py [URL]      (the mock server; never a real record)"""
import json, re, sys, urllib.request
L = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8080'
def call(method, u, body=None):
    req = urllib.request.Request(L + u, data=None if body is None else json.dumps(body).encode(), method=method, headers={'Content-Type': 'application/json', 'X-Editor': 'Shots'})
    with urllib.request.urlopen(req) as r: return json.loads(r.read() or b'{}')
# the first rule whose words are in the plant's "where exactly" names its spot; rules are per area name
RULES = {
    'Yard': [(r'black/yellow bench', 'Black and yellow bench'), (r'wire rack|wire fence|wire shelf|fence line|trellis/rack', 'Wire rack by the fence'), (r'front table', 'Front table'),
             (r'shade cloth', 'Under the shade cloth'), (r'crate|blue bucket|bucket', 'By the porch post'), (r'porch bench', 'Porch bench'),
             (r'black bench|dark pots on a bench', 'Black bench'), (r'grass|open ground|lumber|lava', 'Edge of the lawn'), (r'.', 'On the ground by the steps')],
    'Covered porch': [(r'bench', 'Porch bench'), (r'trellis', 'Wire trellis'), (r'top shelf', 'Pallet shelf, top'), (r'edge', 'Porch edge'), (r'.', 'Pallet shelf')],
    'Downstairs Living Room': [(r'grow light', 'Side Table'), (r'pumpkin', 'Large Brown Hutch'), (r'terracotta bowl', 'Tall Black Shelf'), (r'moss pole', 'Tall Brown Shelf'), (r'.', 'Short Brown Shelf')],
}
areas = {a['id']: a for h in call('GET', '/api/where')['homes'] for a in h['areas']}
items = []
for it in call('GET', '/api/where/sort')['items']:
    a = areas.get(it['area_id'])
    rules = RULES.get(a['name']) if a else None
    if not rules: continue
    name = next(n for pat, n in rules if re.search(pat, it['text'] or ' ', re.I))
    spot = next((s['id'] for s in a['spots'] if s['name'].lower() == name.lower()), None)
    items.append({'text': it['text'], 'from_area_id': it['area_id'], 'area_id': it['area_id'], **({'spot_id': spot} if spot else {'name': name})})
out = call('POST', '/api/where/sort', {'items': items})
print('moved', out.get('moved'), 'made', out.get('made'))
