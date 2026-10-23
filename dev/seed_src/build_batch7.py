import os as _os
REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))  # repository root
"""Batch 7: what Claude needs from Ethan, as requests shown on each plant page (and the 'Needs something from you' filter)."""
import json
OUT = REPO + '/app/seed/batches/batch7.json'
R = []
def req(key, code, name, kind, text): R.append({'key': key, 'code': code, 'name': name, 'kind': kind, 'text': text})

req('p017-spear', 'P-017', 'Majesty palm (black pot)', 'check',
    "Check the centre leaf (the spear) for bud rot: tug it gently. Tell me whether it holds firm, or slides out and smells rotten (then follow the steps under Health).")
req('p055-two-pots', 'P-055', 'Philodendron (self-heading type, cultivar unconfirmed)', 'question',
    "Do the two photos on this page show two separate pots? If so, tell me, or use 'Move to another plant' on one photo to split them.")
req('p075-same-as-p022', 'P-075', 'Rose (black pot, sparse)', 'question',
    "Is this sparse rose a separate plant from P-022, the bushier rose in a black pot? If they are the same pot, I will merge the two pages.")
req('p022-same-as-p075', 'P-022', 'Rose (potted)', 'question',
    "Is this rose a separate plant from P-075, the sparse rose in a second black pot? If they are the same pot, I will merge the two pages.")
for code, name in [('P-029', "Philodendron 'Strawberry Shake'"), ('P-030', "Philodendron 'Pink Princess' (declining)"),
                   ('P-035', "Philodendron 'Pink Princess' (cutting, declining)"), ('P-039', 'Yellow-cream philodendron'),
                   ('P-055', 'Philodendron (self-heading type, cultivar unconfirmed)'), ('P-066', 'Velvet-leaf philodendron (young)')]:
    req(f'{code.lower()}-pot-tag', code, name, 'photo', "A photo of this pot with its plant tag (one photo per pot), to settle the cultivar name.")
for code, name in [('P-056', 'Alocasia (dark glossy leaf)'), ('P-061', 'Alocasia (lime-green, tagged)'),
                   ('P-048', 'Arrowhead plant (pink)'), ('P-060', 'Arrowhead plant (green, white-veined)')]:
    req(f'{code.lower()}-tag-closeup', code, name, 'photo', "A close-up of the plant tag, so the cultivar name can be filled in.")

batch = {'id': 'batch7', 'created': '2026-10-21', 'author': 'Claude (batch 7, requests)',
         'plants': [], 'existing_photos': [], 'updates': [], 'to_photograph_done': [], 'to_photograph_add': [], 'requests_add': R}
json.dump(batch, open(OUT, 'w'), indent=1, ensure_ascii=False)
print(len(R), 'requests')
