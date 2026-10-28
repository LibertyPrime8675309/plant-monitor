"""Batch A8 (1.17.0): a "Safety for pets" value on every plant, for the new Pets filter, and Ethan's answers of October 26.
- pet_safety, from each plant's About profile (profiles_A5.py) and its "Dangers to pets" text:
  'Safe for pets (ASPCA)' only where the ASPCA lists the plant as non-toxic; 'Not known to be toxic' where no source lists it either way.
- The young Monstera (batch A7) started with at least five larger leaves without holes; an animal ate them all some months ago,
  and it had no tag. Its request is closed, and so is the fern-tag request (Ethan: it can be ignored).
Guarded: pet_safety is only set where it is still empty. The A7 pages are found by their photos, since their codes depend on the database.
Run: python3 dev/seed_src/build_batchA8.py <plants.db with batches up to A7>"""
import json, os, sqlite3, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from profiles_A5 import MAP
T, M, N, S = 'Toxic to pets', 'Mildly toxic to pets', 'Not known to be toxic', 'Safe for pets (ASPCA)'
PET = {
    'dieffenbachia': T, 'spathiphyllum': T, 'philo_erubescens': T, 'philo_hybrid': T, 'philo_micans': T, 'monstera': T, 'syngonium': T,
    'aglaonema': T, 'alocasia': T, 'zz': T, 'calathea': S, 'phalaenopsis': S, 'nephrolepis': S, 'begonia': T, 'coleus': T,
    'ficus_elastica': T, 'ficus_lyrata': T, 'ficus_carica': T, 'pachira': S, 'ravenea': N, 'adenium': T, 'euphorbia_milii': T,
    'aloe_vera': T, 'aloe_dwarf': T, 'aloiampelos': T, 'haworthiopsis': S, 'portulacaria': N, 'aeonium_arboreum': N, 'aeonium_haworthii': N,
    'graptosedum': N, 'opuntia': N, 'agave': M, 'myrtillocactus': N, 'moon_cactus': N, 'bougainvillea': M, 'grape': T,
    'ipomoea_hederacea': T, 'ipomoea_batatas': N, 'caesalpinia': M, 'rose_flori': S, 'rose_mini': S, 'cosmos': N,
    'tradescantia_pallida': M, 'tradescantia_zebrina': M, 'tradescantia_fluminensis': M, 'gardenia': M, 'fountain_grass': N,
    'celosia': S, 'iris': T, 'petunia': S, 'artemisia': N, 'monarda': N, 'zexmenia': N, 'hibiscus_coccineus': N, 'vanilla': N,
    'water_hyacinth': N, 'cucurbit': N, 'unknown': N}
NEW_A7 = {'img_a7_agla_1.jpg': 'aglaonema', 'img_a7_fern_1.jpg': 'nephrolepis', 'img_a7_mon_1.jpg': 'monstera'}
c = sqlite3.connect(sys.argv[1]); c.row_factory = sqlite3.Row
first = lambda pid: [x[0] for x in c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY id LIMIT 1', (pid,))]
ups = []
for r in c.execute('SELECT * FROM plants ORDER BY code'):
    files = first(r['id'])
    prof = MAP.get(r['code']) if not (files and files[0] in NEW_A7) else NEW_A7[files[0]]
    if files and files[0] in NEW_A7: prof = NEW_A7[files[0]]
    if not prof: continue
    ups.append({'code': r['code'], 'name': r['common_name'], 'photos': files, 'note': 'Safety for pets set, for the Pets filter (batch A8)',
                'set': {'pet_safety': ['', PET[prof]]}})
mon = c.execute("SELECT p.* FROM plants p JOIN photos ph ON ph.plant_id=p.id WHERE ph.file='img_a7_mon_1.jpg'").fetchone()
L = lambda *x: '\n'.join(x)
ups.append({'code': mon['code'], 'name': mon['common_name'], 'photos': ['img_a7_mon_1.jpg'], 'note': "Ethan's answer: how it started (batch A8)",
            'set': {'notes': [mon['notes'], mon['notes'] + ' It started with at least five larger leaves without holes; an animal ate them all some months '
                              'before October 2026, and these fenestrated leaves are the regrowth. It had no tag.'],
                    'id_basis': [mon['id_basis'], mon['id_basis'] + ' Ethan says it had at least five larger leaves without holes before an animal ate them, '
                                 'and the new leaves came up with holes. Monstera deliciosa can do that when it regrows from an established stem and roots.'],
                    'id_improve': [mon['id_improve'], L('A daylight photo once the next leaf opens')]}})
b = {'id': 'batchA8', 'created': '2026-10-26', 'author': "Claude (pet safety; Ethan's answers, Oct 26, 2026)", 'updates': ups,
     'requests_done': [{'key': 'a7-fern-tag', 'answer': 'Ethan: the tag can be ignored.'},
                       {'key': 'a7-monstera-start', 'answer': 'It started with at least five larger leaves without holes; an animal ate them all some months back. No tag.'}]}
json.dump(b, open(os.path.join(REPO, 'app/seed/batches/batchA8.json'), 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(len(ups), 'updates')
