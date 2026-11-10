"""Batch C6 (PLAN.md step 10, 1.58.0): what the Compare lights table needs that the light records did not say plainly.

- Doubtful figures (a listing that contradicts itself), so the table never ranks them first without saying so: the 4-head
  gooseneck's figures are with all four heads aimed at one spot and look generous next to SANSI's own 10 W bulb figures; the
  30 W bulb's listing says 220 PPFD at 1 ft in one line and 336 in its chart and text.
- Whether a timer keeps its setting after a power cut (timer_keeps), where the listing says: the SANSI 80 W bulb's and the tripod's
  remote timers are lost. Left out where no listing says.
- The brand where a light had none.
Guarded: each is only set where the light holds nothing for it yet. No prices: Ethan has not said what he paid."""
import json, os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'app', 'seed', 'batches', 'batchC6.json')
U = [
    ('sansi-gooseneck', {'doubtful': [None, "the maker measured with all four heads aimed at one spot, and the figures look generous next to SANSI's own 10 W bulb"]}),
    ('sansi-30w', {'doubtful': [None, 'one line of the listing says 220 PPFD at 1 ft; its chart and text say 336']}),
    ('sansi-80w', {'timer_keeps': [None, False]}),
    ('sansi-tripod', {'timer_keeps': [None, False]}),
]
batch = {'id': 'C6', 'created': '2026-11-10', 'author': 'Claude (the listings in build_batchA3.py)',
         'lights_update': [{'key': k, 'set': s, 'note': 'for Compare lights (step 10)'} for k, s in U]}
json.dump(batch, open(OUT, 'w'), indent=1, ensure_ascii=False)
print('wrote', OUT)
