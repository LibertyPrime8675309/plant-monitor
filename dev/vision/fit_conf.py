"""Fit the confidence for one model from leave-one-out matching on Ethan's photos: P(first is right) = logistic(w0 + w1*margin + w2*(score-0.85)).
Usage: python3 fit_conf.py <photos.npz>"""
import json, sys
import numpy as np
z = np.load(sys.argv[1]); E = z['E']; meta = json.loads(str(z['meta'])); codes = [m[1] for m in meta]
S = E @ E.T; np.fill_diagonal(S, -1)
cnt = {c: codes.count(c) for c in set(codes)}
X, y = [], []
for i, c in enumerate(codes):
    if cnt[c] < 2: continue
    best = {}
    for j in np.argsort(-S[i]):
        if codes[j] not in best: best[codes[j]] = S[i, j]
        if len(best) == 2: break
    (c1, s1), (c2, s2) = list(best.items())
    X.append([1, s1 - s2, s1 - 0.85]); y.append(c1 == c)
X, y = np.array(X), np.array(y, float)
w = np.zeros(3)
for _ in range(50):                                   # Newton steps, with a little ridge
    p = 1 / (1 + np.exp(-X @ w)); H = X.T @ (X * (p * (1 - p))[:, None]) + 0.01 * np.eye(3)
    w -= np.linalg.solve(H, X.T @ (p - y) + 0.01 * w)
p = 1 / (1 + np.exp(-X @ w))
print('weights', np.round(w, 2).tolist(), 'n', len(y), 'right first', round(y.mean(), 2))
for lo, hi in ((0.85, 1.01), (0.75, 0.85), (0.5, 0.75), (0.3, 0.5), (0, 0.3)):
    k = (p >= lo) & (p < hi)
    if k.any(): print(f'predicted {lo:.2f}-{hi:.2f}: {k.sum()} photos, right {y[k].mean():.0%}')
k = np.array([x[1] for x in X]); print('margin quartiles', np.round(np.percentile(k, [25, 50, 75]), 3))
