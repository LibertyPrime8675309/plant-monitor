"""Build app/seed/batches/batchA4.json (1.13.1): Ethan's answers of October 24, 2026 about his grow lights and where plants go inside.
- The rooms and shelves where plants will go this winter (he may add more).
- The disk light is new and still in its box, so it can go anywhere.
- All the bulbs (10 W, 30 W, 80 W) and the 4-head gooseneck's own bulbs use the E26 base; the gooseneck bulbs' model is not known yet.
Run: python3 dev/seed_src/build_batchA4.py"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PLACES = [('Downstairs Living Room', 'Tall Black Shelf'), ('Downstairs Living Room', 'Tall Brown Shelf'), ('Downstairs Living Room', 'Short Brown Shelf'),
          ('Downstairs Living Room', 'Large Brown Hutch'), ('Downstairs Living Room', 'Side Table'), ('My Bedroom', 'Shelves'),
          ('Garage', ''), ('Upstairs Living Room', '')]
batch = {
    'id': 'batchA4', 'author': "Claude (Ethan's answers, Oct 24, 2026)",
    'places_add': [{'room': r, 'name': n, 'sort': i} for i, (r, n) in enumerate(PLACES)],
    'lights_update': [
        {'key': 'disk-light', 'set': {'fixture': ['', 'New, still in its box: it can go anywhere']}, 'note': 'new and still in its box'},
        {'key': 'sansi-gooseneck', 'set': {'notes': ['', 'Its four heads take E26 bulbs. The model of the bulbs that came with it is not known yet.']}, 'note': 'E26 heads'},
    ],
    'requests_done': [
        {'key': 'lights-disk', 'answer': 'It is new and still in its box, so it can go anywhere.'},
        {'key': 'lights-spots', 'answer': 'Downstairs Living Room (Tall Black Shelf, Tall Brown Shelf, Short Brown Shelf, Large Brown Hutch, Side Table), My Bedroom (shelves, more to come), Garage, Upstairs Living Room. More may be added later.'},
        {'key': 'lights-sockets', 'answer': 'All of them use the E26 base, including the 4-head gooseneck\'s own bulbs.'},
    ],
    'requests_add': [
        {'key': 'lights-lamps', 'kind': 'question', 'text': 'Grow lights: what will hold the E26 bulbs (six 10 W, two 30 W and the 80 W)? For example clamp lamps, a lamp with a shade taken off, or a hanging socket cord. Do you have enough sockets, or should the layout leave some bulbs out for now? The 80 W bulb is 17 in across with its wings open, so it needs a hanging cord or a sturdy socket.'},
        {'key': 'lights-models', 'kind': 'question', 'text': 'Grow lights: the manufacturer model of each light, from its box or a label on the light, including the bulbs that came with the 4-head gooseneck. Type it under "Change this light" on the Grow lights page, or tell Claude.'},
    ],
}
p = os.path.join(ROOT, 'app', 'seed', 'batches', 'batchA4.json')
json.dump(batch, open(p, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('wrote', p)
