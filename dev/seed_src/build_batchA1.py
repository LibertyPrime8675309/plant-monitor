"""Batch A1 (1.9.0): the leaf type of every plant, the pot size where the photos make it clear, for rating the ways to
keep pests out of the house; and the water hyacinth page archived (Ethan bagged and trashed it on October 23: it is a
prohibited aquatic plant in Texas). Leaf type and pot size are only set where still empty, so Ethan's own choices stay.
Run against a fresh install with batches up to 9d applied:  python3 dev/seed_src/build_batchA1.py <plants.db>"""
import json, os, sqlite3, sys
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
LARGE, SMALL, FUZZY, SUCC, FERN, PALM, WATER = ('Large leaves', 'Small or many leaves', 'Fuzzy or velvety leaves', 'Succulent or cactus',
                                               'Fern fronds', 'Palm fronds', 'Grows in water')
LEAF = {
    # big, smooth or firm leaves that are quick to wipe one by one
    LARGE: ['P-001', 'P-003', 'P-004', 'P-009', 'P-010', 'P-011', 'P-020', 'P-025', 'P-026', 'P-028', 'P-029', 'P-030', 'P-031', 'P-034',
            'P-035', 'P-039', 'P-046', 'P-048', 'P-049', 'P-052', 'P-053', 'P-055', 'P-056', 'P-060', 'P-061', 'P-062', 'P-064', 'P-065', 'P-081'],
    # many small leaves or leaflets: rinse rather than wipe
    SMALL: ['P-005', 'P-006', 'P-007', 'P-008', 'P-022', 'P-023', 'P-027', 'P-033', 'P-036', 'P-037', 'P-038', 'P-047', 'P-051', 'P-054',
            'P-057', 'P-058', 'P-059', 'P-063', 'P-067', 'P-070', 'P-071', 'P-072', 'P-073', 'P-074', 'P-075'],
    FUZZY: ['P-066', 'P-068', 'P-069'],          # velvet-leaf philodendron, petunia (sticky hairs), white sage (silvery hairs)
    SUCC: ['P-012', 'P-013', 'P-014', 'P-015', 'P-016', 'P-018', 'P-019', 'P-021', 'P-040', 'P-041', 'P-042', 'P-043', 'P-044', 'P-045',
           'P-078', 'P-079', 'P-080'],
    FERN: ['P-024'],
    PALM: ['P-017', 'P-076', 'P-077'],
    WATER: ['P-032', 'P-050'],
}
POT = {'Small: fits in a bucket': ['P-021', 'P-035', 'P-040', 'P-067', 'P-068', 'P-069', 'P-070', 'P-071', 'P-072'],   # cups, 8 in and 1 gal pots
       'Medium: fits in a big tub': ['P-046']}                                                                           # 5-gallon bucket
c = sqlite3.connect(sys.argv[1]); c.row_factory = sqlite3.Row
rows = {r['code']: r for r in c.execute("SELECT id, code, common_name FROM plants WHERE status='active' ORDER BY code")}
leaf = {code: t for t, codes in LEAF.items() for code in codes}
pot = {code: t for t, codes in POT.items() for code in codes}
missing = [k for k in rows if k not in leaf]
assert not missing, f'no leaf type for {missing}'
first = lambda r: [x[0] for x in c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY id LIMIT 1', (r['id'],))]
ups = []
for code, r in rows.items():
    if code == 'P-050': continue
    s = {'leaf_type': ['', leaf[code]]}
    if code in pot: s['pot_size'] = ['', pot[code]]
    ups.append({'code': code, 'name': r['common_name'], 'photos': first(r), 'note': 'Leaf type' + (' and pot size' if code in pot else '') +
                ' set, for choosing how to keep pests out of the house (batch A1)', 'set': s})
arch = [{'code': 'P-050', 'name': rows['P-050']['common_name'], 'photos': first(rows['P-050']),
         'note': 'Bagged and put in the trash on October 23, 2026. Water hyacinth is on the Texas list of prohibited aquatic plants.'}]
b = {'id': 'batchA1', 'created': '2026-10-23', 'author': 'Claude (batch A1, leaf types for pest prep)', 'plants': [], 'existing_photos': [],
     'updates': ups, 'archive': arch, 'to_photograph_done': [], 'to_photograph_add': []}
json.dump(b, open(os.path.join(REPO, 'app/seed/batches/batchA1.json'), 'w'), indent=1, ensure_ascii=False)
print(len(ups), 'plants updated,', len(arch), 'archived')
