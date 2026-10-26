"""Fingerprint every photo in a Plant record data folder with BioCLIP 2 and test matching: for each photo of a plant that has
2 or more photos, find the closest other photos and see whether they belong to the same plant (leave one out).
Usage: python3 eval_photos.py <data_dir> <out.npz>"""
import json, os, sqlite3, sys, time
import numpy as np, torch, open_clip
from PIL import Image, ImageOps
data, out = sys.argv[1], sys.argv[2]
MODEL = sys.argv[3] if len(sys.argv) > 3 else 'bioclip-2'
c = sqlite3.connect(os.path.join(data, 'plants.db'))
rows = c.execute("SELECT ph.file, p.code, p.common_name, p.scientific_name, p.genus FROM photos ph JOIN plants p ON p.id=ph.plant_id WHERE p.status='active' ORDER BY p.code, ph.id").fetchall()
torch.set_num_threads(os.cpu_count())
model, _, pre = open_clip.create_model_and_transforms('hf-hub:imageomics/' + MODEL, load_weights=False)
from huggingface_hub import hf_hub_download
from safetensors.torch import load_file
sd = load_file(hf_hub_download('imageomics/' + MODEL, 'open_clip_model.safetensors'))     # memory-mapped: low memory
model.load_state_dict(sd, assign=True); model.eval()
embs, keep, t0 = [], [], time.time()
with torch.no_grad():
    for f, code, name, sci, genus in rows:
        p = os.path.join(data, 'photos', f)
        if not os.path.exists(p): continue
        im = ImageOps.exif_transpose(Image.open(p)).convert('RGB')
        e = model.encode_image(pre(im).unsqueeze(0)); e = e / e.norm(dim=-1, keepdim=True)
        embs.append(e[0].numpy()); keep.append((f, code, name, sci, genus))
dt = (time.time() - t0) / max(1, len(keep))
E = np.stack(embs)
np.savez(out, E=E, meta=np.array(json.dumps(keep)))
codes = [k[1] for k in keep]; gen = [k[4] for k in keep]
S = E @ E.T; np.fill_diagonal(S, -1)
cnt = {x: codes.count(x) for x in set(codes)}
t1 = t3 = g1 = n = 0; confusions = []
for i, code in enumerate(codes):
    if cnt[code] < 2: continue
    order = np.argsort(-S[i])
    # rank plants by their best photo
    seen, ranked = set(), []
    for j in order:
        if codes[j] not in seen: seen.add(codes[j]); ranked.append((codes[j], float(S[i, j])))
        if len(ranked) == 5: break
    n += 1; t1 += ranked[0][0] == code; t3 += code in [r[0] for r in ranked[:3]]; g1 += gen[codes.index(ranked[0][0])] == gen[i]
    if ranked[0][0] != code: confusions.append((code, keep[i][2], ranked[0][0], next(k[2] for k in keep if k[1] == ranked[0][0]), round(ranked[0][1], 3)))
print(f'{len(keep)} photos, {dt:.2f} s per photo on {os.cpu_count()} CPU cores')
print(f'{n} photos of plants with 2+ photos: right plant first {t1}/{n} ({100*t1/n:.0f}%), in the top 3 {t3}/{n} ({100*t3/n:.0f}%), right genus first {g1}/{n} ({100*g1/n:.0f}%)')
for x in confusions: print('  mixed up:', x)
