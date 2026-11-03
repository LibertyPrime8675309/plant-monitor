"""Builds app/seed/batches/batchA9.json (1.27.0): uses, partners, deterrents, propagation and breeding for the species in Ethan's
record, from facts_A9.py. Each entry is added once; a later batch or Claude never overwrites it.
python3 dev/seed_src/build_batchA9.py"""
import json, os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from facts_A9 import FACTS, LINKS
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
out = []
for f in FACTS:
    q = f['name'].split(' (')[0].replace('×', '')
    f['data']['sources'] = [{'title': 'NC State Extension Plant Toolbox', 'url': 'https://plants.ces.ncsu.edu/find_a_plant/?q=' + urllib.parse.quote_plus(q)},
                            {'title': 'Wikipedia', 'url': 'https://en.wikipedia.org/w/index.php?search=' + urllib.parse.quote_plus(q)}]
    out.append(f)
keys = [f['key'] for f in out]
assert len(keys) == len(set(keys)), 'duplicate keys'
b = {'id': 'A9', 'author': 'Claude (batch A9)', 'note': 'Uses, partners, deterrents, propagation and breeding (1.27.0)',
     'species_facts_add': out, 'facts_link': LINKS}
json.dump(b, open(os.path.join(ROOT, 'app', 'seed', 'batches', 'batchA9.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out), 'species')
