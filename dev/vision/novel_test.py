"""How a plant that is NOT in the record looks: remove all photos of the plant (leave one plant out) and compare the best
score and the fitted confidence with ordinary leave-one-out. Usage: python3 novel_test.py <photos.npz> w0 w1 w2"""
import json, sys
import numpy as np
z = np.load(sys.argv[1]); E = z['E']; meta = json.loads(str(z['meta'])); codes = np.array([m[1] for m in meta])
w = [float(x) for x in sys.argv[2:5]]
S = E @ E.T
def top2(i, mask):
    best = {}
    for j in np.argsort(-S[i]):
        if not mask[j]: continue
        if codes[j] not in best: best[codes[j]] = S[i, j]
        if len(best) == 2: break
    (c1, s1), (c2, s2) = list(best.items()); return c1, s1, s1 - s2
conf = lambda s, m: 1 / (1 + np.exp(-(w[0] + w[1] * m + w[2] * (s - 0.85))))
inrec, novel = [], []
for i in range(len(codes)):
    if (codes == codes[i]).sum() >= 2:
        m = np.ones(len(codes), bool); m[i] = False
        c1, s1, mg = top2(i, m); inrec.append((s1, conf(s1, mg), c1 == codes[i]))
    m = codes != codes[i]
    c1, s1, mg = top2(i, m); novel.append((s1, conf(s1, mg)))
inrec, novel = np.array(inrec), np.array(novel)
print('best score  in record: right', np.round(np.percentile(inrec[inrec[:, 2] == 1, 0], [5, 25, 50]), 3), ' wrong', np.round(np.percentile(inrec[inrec[:, 2] == 0, 0], [25, 50, 75]), 3))
print('best score  not in record', np.round(np.percentile(novel[:, 0], [50, 75, 90, 95]), 3))
for t in (0.6, 0.65, 0.7, 0.75, 0.8):
    print(f'score < {t}: not-in-record caught {np.mean(novel[:, 0] < t):.0%}; right in-record answers lost {np.mean(inrec[inrec[:, 2] == 1, 0] < t):.0%}')
for t in (0.75, 0.8, 0.85):
    print(f'conf >= {t}: not-in-record popups {np.mean(novel[:, 1] >= t):.0%}; in-record popups {np.mean(inrec[:, 1] >= t):.0%} (right {inrec[inrec[:, 1] >= t, 2].mean():.0%})')
