# Vision tests (1.18.0)

Scripts used to choose the model and fit the confidence in `vision/service.py`, on a copy of Ethan's data folder. They need a
Python with torch, open_clip_torch, numpy and pillow (any venv; not part of the app).

1. `eval_photos.py <data_dir> <out.npz> [model]`: fingerprints every photo and tests matching, leaving each photo out in turn.
2. `fit_conf.py <out.npz>`: fits `CONF[model]` (logistic on margin and score) and prints how often each confidence band was right.
3. `novel_test.py <out.npz> w0 w1 w2`: leaves each whole plant out, to set `NOVEL[model]` and see how often a plant that is not in the record would pop up.
4. `species_test.py <out.npz> <names_dir> [usda_states.json]`: zero-shot species naming for photos whose plant has a clear "Genus species" name, per scope. `names_dir` is the service's cache folder for that model.
5. `prior_test.py <out.npz> <names_dir> [usda_states.json]` (1.39.0): the same ranking with and without the service's prior (species and genera in the record, houseplant genera, Texas, look-alike photos of the record's own named plants, with the photo's own plant left out). Run on Ethan's PC on November 8, 2026 (inside the running vision container: the scripts copied into `data/vision/tests`, `docker exec -e PYTHONPATH=/svc plant-vision python3 /cache/tests/...`); the results are the baseline below.

Results on 213 photos (October 26, 2026):

| | BioCLIP 2 | BioCLIP 2.5 Huge |
|---|---|---|
| Right plant first / in top 3 | 65% / 85% | 70% / 80% |
| Said 80%+ (share of photos, right) | 25%, 87% | 33%, 92% |
| Species first / top 5 (common or US list) | 17% / 42% | 43% / 65% |
| Species first (all plants worldwide) | 10% | 33% |
| Species first (Texas list, Texas plants) | 62% | 74% |
| Seconds per photo (2 sandbox cores) | 1.3 | 2.2 |
| Download | 2.2 GB | 4.6 GB |

## Baseline on Ethan's photos (November 8, 2026; PLAN.md step 5a)

`prior_test.py` on 176 photos of plants with a known species (42 species, 52 genera in the record), BioCLIP 2.5 Huge, the prior as shipped in 1.39.0 to 1.48.0 (`PRIOR = {own_sp 1.5, own_gen 1.0, house 0.7, state 0.3, looks 3.0}`):

| List, prior | Photos | Species first | Top 5 | Top 10 | Genus first |
|---|---|---|---|---|---|
| Common or US, prior off | 153 | 33% | 54% | 61% | 44% |
| Common or US, prior on | 153 | **40%** | **61%** | **67%** | **52%** |
| Texas, prior off | 46 | 70% | 85% | 87% | 85% |
| Texas, prior on | 46 | **72%** | 85% | **93%** | **89%** |

The prior helps everywhere it was measured (seven points more species-first on the common-or-US list, six more in the top 10 on the Texas list) and hurts nowhere, so `PRIOR` stays as it is. These are the numbers every later change to the checker reports against: a change that lowers "species first" or "top 5" on the common-or-US list does not ship. The matching figures (the right plant first, 65 to 70%) are the October 26 table above; step 5b's "a new find" mode will add a row for species named with no lift for the record's own plants.

To repeat it (the app running; from the folder with `docker-compose.yml`, with the repository unzipped next to it as `plant-monitor`):

Windows (cmd.exe):
```
mkdir data\vision\tests
copy ..\plant-monitor\dev\vision\*.py data\vision\tests\
docker exec -e PYTHONPATH=/svc plant-vision python3 /cache/tests/eval_photos.py /data /cache/eval.npz bioclip-2.5-vith14
docker exec -e PYTHONPATH=/svc plant-vision python3 /cache/tests/prior_test.py /cache/eval.npz /cache/bioclip-2.5-vith14 /cache/usda_states.json
```

Windows (PowerShell):
```
New-Item -ItemType Directory -Force data\vision\tests | Out-Null
Copy-Item ..\plant-monitor\dev\vision\*.py data\vision\tests\
docker exec -e PYTHONPATH=/svc plant-vision python3 /cache/tests/eval_photos.py /data /cache/eval.npz bioclip-2.5-vith14
docker exec -e PYTHONPATH=/svc plant-vision python3 /cache/tests/prior_test.py /cache/eval.npz /cache/bioclip-2.5-vith14 /cache/usda_states.json
```

bash:
```
mkdir -p data/vision/tests
cp ../plant-monitor/dev/vision/*.py data/vision/tests/
docker exec -e PYTHONPATH=/svc plant-vision python3 /cache/tests/eval_photos.py /data /cache/eval.npz bioclip-2.5-vith14
docker exec -e PYTHONPATH=/svc plant-vision python3 /cache/tests/prior_test.py /cache/eval.npz /cache/bioclip-2.5-vith14 /cache/usda_states.json
```

The container's file system is read-only, so `docker cp` into it is refused; `data/vision` (mounted as `/cache`) is the writable place. `PYTHONPATH=/svc` lets the scripts import the service's own code. The first command takes 10 to 20 minutes.
