#!/usr/bin/env python3
"""Checks a plant update file before it is saved on Ethan's computer (1.58.0): is it one the app will read, and what is in it?

  python3 tools/check-plant-updates.py plant-updates-20261114-0312.json      (or .zip)

It reads the file the way the app does (app/plantdb/updates.py: upd_parse) and prints what it holds, or what is wrong with it.
It cannot say whether each change still fits his record: only the app on his computer knows what his pages say now."""
import collections, os, sys, tempfile
if len(sys.argv) != 2: sys.exit(__doc__)
path = sys.argv[1]
os.environ.update(DATA_DIR=tempfile.mkdtemp(prefix='plantdb-check-'), PLANTDB_WEATHER='0', PLANTDB_SHOPS='0', PLANTDB_OSM='0', PLANTDB_UPDATES='0', PLANTDB_PUSH='0', PLANTDB_VISION_URL='http://127.0.0.1:9')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'app'))
import server as S   # noqa: E402
name = os.path.basename(path)
try:
    with open(path, 'rb') as f: u = S.upd_parse(f.read(), name)
except ValueError as e: sys.exit(f'NOT USABLE: {e}')
kinds = collections.Counter(x['kind'] for x in u['changes'])
WORDS = {'set': 'to set', 'archive': 'to archive', 'ask': 'to ask', 'photos': 'adding photos', 'new': 'new pages'}
count = lambda n, one, many: f'{n} {one if n == 1 else many}'
print(f"{name}: {count(len(u['changes']), 'change', 'changes')} ({', '.join(f'{n} {WORDS.get(k, k)}' for k, n in kinds.items()) or 'none'}), made {u['made'] or 'on no date given'}, {count(len(u['photos']), 'photo', 'photos')} in the file.")
for x in u['changes']:
    if x['kind'] == 'set' and (x['field'] not in S.FIELD_KIND or x['field'] in S.BATCH_ROW_IDS): print(f"  WARNING: {x['code']} {x['name']}: \"{x['field']}\" is not something an update file can change; the app will leave it out.")
    if x['kind'] == 'new':
        for k in x['fields']:
            if k not in S.FIELD_KIND or k in S.BATCH_ROW_IDS: print(f"  WARNING: the new page \"{x['fields'].get('common_name')}\" sets \"{k}\", which a new page cannot be given; the app will leave the page out.")
if not S.UPD_NAME.match(name): print('  WARNING: the app only picks up files in its folder whose name starts with "plant-updates" and ends in .json or .zip.')
if os.path.getsize(path) > 30 * 1024 * 1024: print('  WARNING: larger than 30 MB.')
print('The app will read it.')
