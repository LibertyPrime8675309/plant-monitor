"""1.39.0: does the prior help? For each of Ethan's photos whose plant has a clear 'Genus species' name, rank the species
with and without the lifts the service applies (species and genera in the record, houseplant genera, Texas, look-alike photos
of the record's own named plants, leaving the photo's own plant out), and compare where the right name lands.
Usage: python3 prior_test.py <photos.npz from eval_photos.py> <names_dir with names.json + names.npy> [usda_states.json]
The npz meta rows are (file, code, name, sci, genus), as eval_photos.py writes them."""
import json, os, re, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'vision'))
os.environ['PLANTDB_VISION'] = '0'
import service as V                      # PRIOR, HOUSE and NOVEL as the service uses them

z = np.load(sys.argv[1]); E = z['E'].astype(np.float32); meta = json.loads(str(z['meta']))
rows = json.load(open(sys.argv[2] + '/names.json')); N = np.load(sys.argv[2] + '/names.npy').astype(np.float32)
usda = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else {}
sp = [r[0][5] + ' ' + r[0][6] for r in rows]; gen = [r[0][5] for r in rows]
by = {}
for i, s in enumerate(sp): by.setdefault(s, i)
has = np.abs(N).sum(1) > 0
common = np.array([bool(re.search(r'[A-Za-z]', r[1] or '')) for r in rows])
in_us = np.array([s in usda for s in sp]); in_tx = np.array([s in usda and 'Texas' in usda[s] for s in sp])
masks = {'common or US': has & (common | in_us), 'Texas': has & in_tx}
SCALE = 100.0
def sp_of(sci):
    m = re.match(r'^([A-Z][a-z]+) ([a-z][a-z\-]+)', sci or '')
    return by.get(m.group(1) + ' ' + m.group(2), -1) if m and m.group(2) not in ('sp', 'spp', 'x') else -1
photo_sp = np.array([sp_of(m[3]) for m in meta]); photo_code = [m[1] for m in meta]
own_sp = {i for i in photo_sp if i >= 0}
own_gen = {re.match(r'^([A-Z][a-z]+)', m[3]).group(1) for m in meta if re.match(r'^([A-Z][a-z]+)', m[3] or '')}
tests = [(k, photo_sp[k]) for k in range(len(meta)) if photo_sp[k] >= 0]
print(len(tests), 'photos with a known species;', len(own_sp), 'species and', len(own_gen), 'genera in the record')
for nm, mask in masks.items():
    idx = np.where(mask)[0]; S = E @ N[idx].T * SCALE
    state = 'state:Texas' if nm == 'Texas' else 'common'
    for prior in (False, True):
        s1 = s5 = s10 = g1 = n = 0
        for k, want in tests:
            if not mask[want]: continue
            n += 1
            top = np.argsort(-S[k])[:80]
            cand = {int(idx[t]): float(S[k][t]) for t in top}
            if prior:
                others = np.array([j for j in range(len(meta)) if photo_code[j] != photo_code[k]])   # the photo's own plant left out: a new pot
                sims = E[others] @ E[k]
                looks = {}
                for j in np.argsort(-sims)[:8]:
                    i, sim = photo_sp[others[j]], float(sims[j])
                    if i >= 0 and mask[i] and sim >= 0.65: looks[i] = max(looks.get(i, 0), sim)
                for i in looks:
                    if i not in cand: cand[i] = float(E[k] @ N[i]) * SCALE
                osp = own_sp - {want} if photo_code.count(photo_code[k]) == sum(1 for j in range(len(meta)) if photo_sp[j] == want) else own_sp
                for i in list(cand):
                    why = []
                    if i in osp: why.append('own_sp')
                    elif gen[i] in own_gen: why.append('own_gen')
                    if gen[i] in V.HOUSE: why.append('house')
                    if state.startswith('state:') and sp[i] in usda and 'Texas' in usda[sp[i]]: why.append('state')
                    b = sum(V.PRIOR[w] for w in why)
                    if i in looks: b += V.PRIOR['looks'] * (looks[i] - 0.65) / 0.35
                    cand[i] += b
            order = sorted(cand, key=lambda i: -cand[i])
            s1 += order[0] == want; s5 += want in order[:5]; s10 += want in order[:10]; g1 += gen[order[0]] == gen[want]
        print(f'{nm:13s} prior {"on " if prior else "off"} ({n} photos): species first {100*s1/n:.0f}%, top 5 {100*s5/n:.0f}%, top 10 {100*s10/n:.0f}%; genus first {100*g1/n:.0f}%')
