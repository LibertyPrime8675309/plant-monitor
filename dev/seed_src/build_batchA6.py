"""Build app/seed/batches/batchA6.json (1.15.0): Ethan's answer of October 25, 2026 about what holds his E26 grow bulbs.
He has 3 clamp-on bendy lamps (120 V, own switches, removable shades), 1 bare E26 socket on a long cable (about 25 ft,
rated 150 W at 120 V, own switch) and 10 bare E26 sockets on 6 ft cables (rated 250 V at 4 A, own switches).
That is 14 sockets for his 9 bulbs (six 10 W, two 30 W, one 80 W), so all of them can be used and 5 bare sockets are spare.
Claude's suggestion goes in each bulb's "Where it is" (fixture), only where that is still empty, so Ethan can change it.
Run: python3 dev/seed_src/build_batchA6.py"""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
batch = {
    'id': 'batchA6', 'author': "Claude (Ethan's answers, Oct 25, 2026)",
    'lights_update': [
        {'key': 'sansi-80w', 'set': {
            'fixture': ['', 'Suggested: the bare socket on the long (about 25 ft) cable, rated 150 W. Hang it bare above the plants: the bulb is 17 in across with its wings open, too big for a clamp lamp shade.']},
         'note': 'what holds it'},
        {'key': 'sansi-30w', 'set': {
            'fixture': ['', 'Suggested: two of the three clamp-on bendy lamps. The shade can stay on to aim the light down; take it off if the bulb does not fit.']},
         'note': 'what holds them'},
        {'key': 'sansi-10w', 'set': {
            'fixture': ['', 'Suggested: the third clamp-on lamp and five of the ten bare sockets on 6 ft cables (each rated 4 A, far more than a 10 W bulb needs). Five bare sockets are left spare.']},
         'note': 'what holds them'},
    ],
    'requests_done': [
        {'key': 'lights-lamps', 'answer': '3 clamp-on bendy lamps (120 V, own switches, removable shades); 1 bare E26 socket on a long cable (about 25 ft, 150 W, own switch); '
                                          '10 bare E26 sockets on 6 ft cables (250 V, 4 A, own switches). 14 sockets for 9 bulbs, so there are enough.'},
    ],
}
p = os.path.join(ROOT, 'app', 'seed', 'batches', 'batchA6.json')
json.dump(batch, open(p, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('wrote', p)
