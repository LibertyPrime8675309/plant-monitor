# Vision tests (1.18.0)

Scripts used to choose the model and fit the confidence in `vision/service.py`, on a copy of Ethan's data folder. They need a
Python with torch, open_clip_torch, numpy and pillow (any venv; not part of the app).

1. `eval_photos.py <data_dir> <out.npz> [model]`: fingerprints every photo and tests matching, leaving each photo out in turn.
2. `fit_conf.py <out.npz>`: fits `CONF[model]` (logistic on margin and score) and prints how often each confidence band was right.
3. `novel_test.py <out.npz> w0 w1 w2`: leaves each whole plant out, to set `NOVEL[model]` and see how often a plant that is not in the record would pop up.
4. `species_test.py <out.npz> <names_dir> [usda_states.json]`: zero-shot species naming for photos whose plant has a clear "Genus species" name, per scope. `names_dir` is the service's cache folder for that model.
5. `prior_test.py <out.npz> <names_dir> [usda_states.json]` (1.39.0): the same ranking with and without the service's prior (species and genera in the record, houseplant genera, Texas, look-alike photos of the record's own named plants, with the photo's own plant left out). Not yet run on Ethan's photos: the sandbox has no torch and the npz is on his PC. Run it there to set `PRIOR` in `vision/service.py` with numbers instead of judgment.

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
