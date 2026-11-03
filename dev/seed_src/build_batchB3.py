"""Batch B3 (prototype proto/summer-heat): the American Horticultural Society heat zones each plant is listed for, with the
page they came from. Asked for by Ethan on pull request #33 (November 2, 2026).

The ranges were looked up by web search on November 3, 2026. Only ranges actually printed on a page are used, and each one keeps
that page's link. The only site that printed heat zones for these plants was Gardenia.net (a plant encyclopedia). Extension
services, botanic gardens and the big nurseries checked (NC State, Missouri Botanical Garden, Texas Tech, Proven Winners,
Monrovia) list USDA hardiness zones only. Plants with no published range are left empty, and so are these, on purpose:
- Bougainvillea: listed as 1 to 12, which looks like a placeholder for a frost-tender tropical.
- Celosia: listed as 2 to 9, which does not fit a heat-loving summer annual.
- Begonias, Alocasias, Agave: only other species had a range, and these plants' species are not certain.
Every field is only filled while still empty, so anything Ethan types himself stays.
Run against a copy of a database with batches up to B2 applied:  python3 dev/seed_src/build_batchB3.py <plants.db>"""
import json, os, sqlite3, sys
HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.abspath(os.path.join(HERE, '..', '..'))

G = 'Gardenia.net: '
# key: (hottest, coolest, source title, url, which level the range is for)
RANGES = {
    'aeonium':      (9, 4, G + "Aeonium arboreum 'Atropurpureum'", 'https://www.gardenia.net/plant/aeonium-arboreum-atropurpureum', 'the same range is given for Aeonium arboreum and Aeonium haworthii'),
    'opuntia':      (12, 9, G + 'Opuntia ficus-indica (Prickly Pear)', 'https://www.gardenia.net/plant/opuntia-ficus-indica-prickly-pear', 'for Opuntia ficus-indica'),
    'haworthiopsis': (12, 10, G + 'Zebra Haworthia (Haworthiopsis attenuata)', 'https://www.gardenia.net/plant/haworthiopsis-attenuata-zebra-haworthia', 'for the species'),
    'portulacaria': (12, 10, G + "Portulacaria afra 'Variegata' (Variegated Elephant Bush)", 'https://www.gardenia.net/plant/portulacaria-afra-variegata-elephant-bush-grow-care-guide', 'for this cultivar'),
    'ficus_lyrata': (12, 7, G + 'Fiddle-Leaf Fig', 'https://www.gardenia.net/plant/ficus-lyrata-fiddle-leaf-fig', 'for the species'),
    'cosmos':       (12, 1, G + "Cosmos 'Sensation Radiance'", 'https://www.gardenia.net/plant/cosmos-bipinnatus-sensation-radiance', "grown as an annual; Cosmos sulphureus 'Cosmic Orange' is listed the same"),
    'coleus':       (11, 1, G + "Solenostemon 'Black Prince' (Coleus)", 'https://www.gardenia.net/plant/solenostemon-black-prince', "for coleus cultivars ('Trusty Rusty' is listed the same), grown as an annual"),
    'euphorbia_milii': (11, 1, G + 'Crown of Thorns (Euphorbia milii)', 'https://www.gardenia.net/plant/Euphorbia-milii-Crown-of-Thorns', 'for the species'),
    'tradescantia_pallida': (12, 1, G + "Tradescantia pallida 'Purpurea' (Purple Heart)", 'https://www.gardenia.net/plant/tradescantia-pallida-purple-heart', 'for purple heart'),
    'gardenia':     (12, 7, G + 'Gardenia jasminoides', 'https://www.gardenia.net/plant/Gardenia-jasminoides', "for the species; the same site's care guide says 8 to 12"),
    'pennisetum':   (12, 8, G + "Pennisetum advena 'Rubrum' (Purple Fountain Grass)", 'https://www.gardenia.net/plant/pennisetum-setaceum-rubrum', 'for this cultivar and the species'),
    'petunia':      (12, 1, G + "Petunia 'Easy Wave Red'", 'https://www.gardenia.net/plant/petunia-easy-wave-red', "for Wave petunias, grown as an annual; no range was found for 'Ray Black' itself"),
    'artemisia':    (9, 1, G + 'Artemisia ludoviciana (White Sage)', 'https://www.gardenia.net/plant/artemisia-ludoviciana-white-sage', 'for the species'),
    'monarda':      (9, 1, G + 'Monarda fistulosa (Wild Bergamot)', 'https://www.gardenia.net/plant/monarda-fistulosa', 'for the species'),
    'iris':         (9, 1, G + 'Bearded Iris (Iris germanica)', 'https://www.gardenia.net/genus/iris-germanica-bearded-iris', 'for bearded irises'),
}
MAP = {'P-012': 'aeonium', 'P-045': 'aeonium', 'P-013': 'opuntia', 'P-016': 'haworthiopsis', 'P-043': 'haworthiopsis',
       'P-019': 'portulacaria', 'P-020': 'ficus_lyrata', 'P-023': 'cosmos', 'P-027': 'coleus', 'P-033': 'coleus',
       'P-040': 'euphorbia_milii', 'P-047': 'tradescantia_pallida', 'P-052': 'gardenia', 'P-054': 'pennisetum',
       'P-068': 'petunia', 'P-069': 'artemisia', 'P-070': 'monarda', 'P-064': 'iris'}

c = sqlite3.connect(sys.argv[1]); c.row_factory = sqlite3.Row
ups = []
for code, key in sorted(MAP.items()):
    r = c.execute('SELECT id, code, common_name FROM plants WHERE code=?', (code,)).fetchone()
    assert r, code
    hi, lo, title, url, level = RANGES[key]
    photos = [x[0] for x in c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY id LIMIT 1', (r['id'],))]
    ups.append({'code': code, 'name': r['common_name'], 'photos': photos,
                'note': f'AHS heat zones {hi} to {lo} added from Gardenia.net ({level}) (batch B3)',
                'set': {'heat_zone_high': ['', hi], 'heat_zone_low': ['', lo], 'heat_zone_source': ['', f'{title} | {url}']}})
batch = {'id': 'batchB3', 'created': '2026-11-03', 'author': 'Claude (AHS heat zones with sources, Nov 3, 2026)', 'updates': ups}
out = os.path.join(REPO, 'app', 'seed', 'batches', 'batchB3.json')
json.dump(batch, open(out, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print(f'{out}: {len(ups)} plants')
