"""Batch B3 (1.28.0): a second home, Nevada City, California, where Ethan's girlfriend keeps her plants (Ethan, November 2026).
It gets its own weather; its plants are added later with Home set to it. Skipped if a place is already there.
Run: python3 dev/seed_src/build_batchB3.py"""
import json, os
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
b = {'id': 'B3', 'created': '2026-11-03', 'author': "Claude (Ethan's second home, Nov 2026)",
     'homes_add': [{'name': 'Nevada City, CA', 'lat': 39.2616, 'lon': -121.0161, 'tz': 'America/Los_Angeles'}]}
json.dump(b, open(os.path.join(REPO, 'app/seed/batches/batchB3.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('batch B3 written')
