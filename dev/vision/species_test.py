"""Zero-shot species test: for each of Ethan's photos whose plant has a clear 'Genus species' name in the species list,
rank every species (worldwide, and narrowed lists) and see where the right one lands.
Usage: python3 species_test.py <photos.npz> <names_dir with names.json + names.npy> [usda_states.json]"""
import json, re, sys
import numpy as np
z = np.load(sys.argv[1]); E = z['E']; meta = json.loads(str(z['meta']))
rows = json.load(open(sys.argv[2] + '/names.json')); N = np.load(sys.argv[2] + '/names.npy').astype(np.float32)
usda = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
sp = [r[0][5] + ' ' + r[0][6] for r in rows]; gen = [r[0][5] for r in rows]
by = {}
for i, s in enumerate(sp): by.setdefault(s, i)
has = np.abs(N).sum(1) > 0
common = np.array([bool(re.search(r'[A-Za-z]', r[1] or '')) for r in rows])
in_us = np.array([s in usda for s in sp]); in_tx = np.array([s in usda and 'Texas' in usda[s] for s in sp])
masks = {'world': has, 'common or US': has & (common | in_us), 'US': has & in_us, 'Texas': has & in_tx}
tests = []
for k, (f, code, name, sci, genus) in enumerate(meta):
    m = re.match(r'^([A-Z][a-z]+) ([a-z][a-z\-]+)', sci or '')
    if m and m.group(1) + ' ' + m.group(2) in by: tests.append((k, m.group(1) + ' ' + m.group(2)))
print(len(tests), 'photos with a known species')
for nm, mask in masks.items():
    idx = np.where(mask)[0]; S = E @ N[idx].T
    s1 = s5 = g1 = g5 = n = 0
    for k, want in tests:
        if not mask[by[want]]: continue
        n += 1
        top = idx[np.argsort(-S[k])[:50]]
        names = [sp[i] for i in top]; gens = [gen[i] for i in top]
        s1 += names[0] == want; s5 += want in names[:5]; g1 += gens[0] == want.split()[0]
        g5 += want.split()[0] in list(dict.fromkeys(gens))[:5]
    if n: print(f'{nm:13s} ({mask.sum():6d} species, {n} photos): species first {100*s1/n:.0f}%, top 5 {100*s5/n:.0f}%; genus first {100*g1/n:.0f}%, top 5 genera {100*g5/n:.0f}%')
