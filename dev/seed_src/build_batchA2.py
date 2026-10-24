"""Batch A2 (1.11.0):
1. The fertilizer each plant needs, as an N-P-K ratio and a strength (new fields npk_ratio and fert_strength), taken from
   the plant's fertilizer note so the Fertilizer page can match it to the fertilizers Ethan has.
2. Ethan's answers of October 23, 2026 (Copy my answers for Claude) and what his new photos show:
   P-017 spear firm (no bud rot); P-025 tag blank; P-036 not sweet, so not stevia; P-042 yellow leaf firm, roots healthy;
   P-048 and P-066 tags not accurate or missing; P-053 most black specks are insects; P-055 specks are scorch marks;
   P-060 tag reads Syngonium 'Black Velvet'; P-081 tag reads Philodendron 'Ring of Fire'; P-006, P-031 and P-061 photos.
Every change states the value it replaces, so anything Ethan edited himself is left alone.
Run against a fresh install with batches up to A1 applied:  python3 dev/seed_src/build_batchA2.py <plants.db>"""
import json, os, sqlite3, sys
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
Q, QH, H, F, NONE = 'Quarter strength', 'Quarter to half strength', 'Half strength', 'Full strength', 'None needed'

# ---- 1. fertilizer ratio (N-P-K, as simple whole numbers) and strength, from each plant's fertilizer note
FERT = {
    # foliage aroids and other leafy tropicals: "such as 3-1-2 or 20-20-20, at half strength" -> the foliage ratio 3-1-2
    **{k: ('3-1-2', H) for k in ['P-001', 'P-009', 'P-010', 'P-020', 'P-029', 'P-030', 'P-035', 'P-039', 'P-048', 'P-049', 'P-055',
                                 'P-056', 'P-060', 'P-061', 'P-062', 'P-063', 'P-065', 'P-066', 'P-081']},
    # "balanced" feeds: equal parts
    **{k: ('1-1-1', H) for k in ['P-003', 'P-005', 'P-006', 'P-007', 'P-011', 'P-025', 'P-026', 'P-027', 'P-028', 'P-033', 'P-036',
                                 'P-037', 'P-038', 'P-046', 'P-047', 'P-051', 'P-053', 'P-054', 'P-059', 'P-072']},
    'P-004': ('1-1-1', Q),                   # "balanced slow-release, light feeding"
    'P-024': ('1-1-1', Q),                   # fern: easily burned
    'P-031': ('1-1-1', QH), 'P-034': ('1-1-1', QH),
    'P-032': ('1-1-1', Q),                   # orchid in water: a quarter of the label strength
    # succulents and cacti: low nitrogen, about 2-7-7
    **{k: ('2-7-7', H) for k in ['P-012', 'P-013', 'P-014', 'P-015', 'P-018', 'P-019', 'P-040', 'P-044', 'P-045', 'P-078', 'P-079', 'P-080']},
    **{k: ('2-7-7', QH) for k in ['P-016', 'P-042', 'P-043']},
    'P-041': ('2-7-7', Q),
    'P-008': ('1-1-2', H),                   # bougainvillea: low nitrogen, high potassium
    'P-021': ('1-5-5', H),                   # desert rose: high phosphorus, such as 6-30-30
    **{k: ('2-3-2', H) for k in ['P-022', 'P-073', 'P-074', 'P-075']},           # roses: such as 4-6-4
    **{k: ('4-1-6', H) for k in ['P-017', 'P-076', 'P-077']},                    # palms: such as 8-2-12, with magnesium
    'P-052': ('3-1-1', H),                   # gardenia: acid-loving food such as 30-10-10
    **{k: ('1-3-2', H) for k in ['P-057', 'P-058', 'P-067']},                    # celosia: low-nitrogen bloom food
    'P-064': ('1-2-2', H),                   # bearded iris: low nitrogen
    'P-068': ('2-1-2', H),                   # petunia: a petunia feed such as 20-9-20, with iron
    'P-023': ('', NONE),                     # cosmos: lean soil
    **{k: ('1-1-1', NONE) for k in ['P-069', 'P-070', 'P-071']},                 # natives: none, or a light feed in spring
}

# ---- 2. answers and photos
def lines(*xs): return '\n'.join(xs)
ANS = {
    'P-017': ({'health_rating': 'Fair',
               'health_summary': 'Only a few fronds, all pale yellow-green. The browning spear in the centre holds firm and does not smell, so it is tip damage, not bud rot.',
               'health_observations': lines('The new spear in the centre is brown and dry at the tip, but holds firm when tugged and has no rotten smell (checked October 23)',
                                            'A dead brown leaf stalk beside the spear', 'Remaining fronds pale yellow-green with dry tips',
                                            'Thick mat of spotted spurge weeds in and around the pot'),
               'health_steps': lines('Trim the dry brown tip of the spear if you like; leave the green part', 'Pull the spurge weeds out of the pot',
                                     'Move it out of hard afternoon sun', 'Feed palm fertilizer with magnesium once before winter, then stop until March',
                                     'Keep the mix evenly moist, not soggy'),
               'pests_current': 'Spotted spurge (a weed) covers the pot. The spear was checked on October 23: firm, no rot.'},
              'Spear checked: holds firm, no rotting smell, so no bud rot (batch A2)'),
    'P-025': ({'id_improve': lines('A flower (the tag in the pot is blank)', 'Whether it dies back to a tuber in winter (tuberous begonia) or stays leafy'),
               'notes': 'The tag in the pot is blank (Ethan, October 23).'},
              'Tag is blank (batch A2)'),
    'P-036': ({'common_name': 'Young shrub with toothed leaves (not stevia)', 'scientific_name': 'Not identified (not Stevia: the leaves are not sweet)',
               'aliases': '', 'id_confidence': 25,
               'id_basis': 'Thin, woody brown stems with opposite pairs of light-green leaves that narrow to the base and are coarsely toothed toward the tip. '
                           'It was taken for stevia, but the leaves have no sweetness at all (taste test, October 23), so it is not stevia. '
                           'A square stem would point to the mint family (salvia); a round one to a hydrangea cutting or a eupatorium.',
               'id_alternatives': lines('Hydrangea cutting', 'Salvia (mint family: square stems, scented leaves)', 'Eupatorium or Ageratina (boneset, snakeroot)',
                                        'Chrysanthemum cutting'),
               'id_improve': lines('Roll the stem between your fingers: square or round?', 'Crush a leaf: does it smell of sage, mint, or nothing?',
                                   'A flower', 'Where the cutting or seed came from')},
              'Not stevia: the leaves are not sweet (batch A2)'),
    'P-042': ({'health_rating': 'Good',
               'health_summary': 'Firm, with healthy white roots showing through the clear pot. The yellow lowest leaf is firm, so it is an old leaf dying back, not rot.',
               'health_observations': lines('Yellow-orange blotches on one leaf (sun scars)', 'Lowest leaf yellow but firm at the base (pressed, October 23): an old leaf dying back',
                                            'White, healthy roots visible through the clear pot', 'A small pink-flowered weed in the tub'),
               'health_steps': lines('Cut off the yellow lowest leaf when it has dried, close to the base.', 'Keep it dry; water only when the mix is dry through.',
                                     'Pull the weed.', 'Move it under cover before nights reach 25°F.')},
              'Yellow lowest leaf is firm: an old leaf, not rot (batch A2)'),
    'P-048': ({'id_improve': 'A mature leaf (pink usually fades to green with age)',
               'notes': 'The tag in the pot is not accurate, so it is not used for the name (Ethan, October 23).'},
              'Tag is not accurate, so the cultivar stays unconfirmed (batch A2)'),
    'P-053': ({'pests_current': 'October 23: most of the black specks under the leaves are tiny insects that move when nudged (some are just dots). '
                                'Most likely black aphids; thrips are possible. Insecticidal soap treats both.',
               'pests_found': 'Aphids',
               'health_observations': lines('Tiny black insects under several leaves (checked October 23)', 'Older leaves yellowing with brown spots',
                                            'Tendrils and new growth at the top'),
               'health_steps': lines('Hose the leaves, top and underside, with a strong spray.', 'Then spray insecticidal soap every 5-7 days, three times, covering the undersides.',
                                     'Keep it away from plants that are coming inside, so the insects do not spread to them.',
                                     'It is a frost-tender annual near the end of its season: when frost kills it, bag it and put it in the trash rather than compost.')},
              'Most black specks are insects, probably aphids (batch A2)'),
    'P-055': ({'health_summary': 'Struggling: many leaves are yellow-orange with dead brown tips and droop, and the green leaves have small white scorch marks from sun.',
               'health_observations': lines('Small white marks on the leaves that do not wipe off: sun scorch (checked October 23)', 'Yellow-orange leaves with dead tips',
                                            'Drooping leaves', 'Papery dead sheaths at the base'),
               'health_steps': lines('Move it to bright shade: no direct sun at all.', 'Cut off the dead and mostly yellow leaves.',
                                     'Water when the top inch is dry.', 'Bring it inside before nights reach 55°F.'),
               'pests_current': 'None. The white specks are scorch marks, not insects (checked October 23).'},
              'White specks are scorch marks, not pests (batch A2)'),
    'P-060': ({'common_name': "Arrowhead plant 'Black Velvet'", 'scientific_name': "Syngonium 'Black Velvet'", 'aliases': 'Exotic Angel Plants tag', 'id_confidence': 85,
               'id_basis': "The Exotic Angel Plants tag in the pot reads 'Syngonium Black Velvet'. Arrow-shaped leaves with a bright white midrib and veins fit it; "
                           "'Black Velvet' leaves are dark and velvety in shade and turn lighter green in strong light, as these have.",
               'id_alternatives': lines("Syngonium wendlandii (one of its parents)", 'Other green Syngonium podophyllum forms'),
               'id_improve': 'A newly opened leaf grown in shade (it should be dark and velvety)',
               'light_summary': 'Medium to bright indirect light (the tag says medium light)',
               'notes': 'The pot also has a few purple-pink wandering-dude (Tradescantia) shoots.'},
              "Tag reads Syngonium 'Black Velvet' (batch A2)"),
    'P-066': ({'id_improve': lines('A mature leaf photo', 'The whole vine and stem (there is no accurate tag)')},
              'No accurate tag in the pot (batch A2)'),
    'P-081': ({'common_name': "Philodendron 'Ring of Fire'", 'scientific_name': "Philodendron 'Ring of Fire' (sold as Philodendron serratum)",
               'aliases': 'HEB clearance, $1 (was $8), Sept 30 2026', 'id_confidence': 85,
               'id_basis': "The HEB tag in the pot reads 'Philodendron Ring of Fire, Philodendron serratum', and the clearance label 'HEB PHILO RNG OF FIRE 5IN'. "
                           "Its leaves are marbled lime and yellow over green, which is how 'Ring of Fire' looks; young leaves are smooth-edged and later ones become long and jagged.",
               'id_alternatives': lines("Philodendron 'Calypso' (lime-and-yellow marbled)", "Philodendron 'Painted Lady' (young leaf)"),
               'id_improve': 'A newly opened leaf (they become longer and more jagged as the plant matures)',
               'health_summary': 'One big leaf with yellow and brown sun-scorched edges, and dried papery sheaths at the base. Bought on clearance and recovering.',
               'health_observations': lines('Yellow and brown scorched edges on the big leaf', 'Dried papery sheaths (cataphylls) at the base, which is normal',
                                            'One green stalk and a new shoot at the base'),
               'health_steps': lines('Move it to bright shade: the tag says full sun, but the leaf is scorched.', 'Pull off the dried sheaths once they come away easily.',
                                     'Water when the top inch is dry.', 'Bring it inside before nights reach 55°F.'),
               'light_summary': 'Bright indirect light (the tag says full sun, but the leaf is scorched)',
               'notes': 'Split from P-055 on October 23, 2026. Identified from its HEB tag the same day.'},
              "Tag reads Philodendron 'Ring of Fire' (batch A2)"),
    'P-006': ({'health_observations': lines('Even colour', 'No pests seen', 'Strong climbing growth', 'Roots showing at the top of the mix (October 23 photo)', 'Spurge weeds in the pot'),
               'health_steps': lines('Cover the bare roots at the base with an inch of fresh mix.', 'Pull the spurge weeds.', 'Keep supported on the trellis', 'Water as the top inch dries')},
              'Photo: roots showing at the base (batch A2)'),
    'P-031': ({'health_observations': lines('Many brown crisped leaves', 'Several clean new leaves', 'New shoots and white roots at the base', 'Drip emitter in the pot',
                                            'Older leaves fading to yellow with brown tips (October 23 photo)')},
              'Photo: older leaves fading (batch A2)'),
    'P-061': ({'id_improve': lines('A newly opened leaf', 'Writing on the back of the white Alocasia tag, if any (the front only says Alocasia)')},
              'Photos of the whole plant; the tag only says Alocasia (batch A2)'),
}
DONE = [{'key': 'p017-spear', 'answer': 'Holds firm, no rotting smell'}, {'key': 'p025-tag-text', 'answer': 'Tag is blank'},
        {'key': 'p036-taste', 'answer': 'No sweetness or flavor of note'}, {'key': 'p042-base', 'answer': 'Firm'},
        {'key': 'p-048-tag-closeup', 'answer': 'Tag is not accurate, ignore it'}, {'key': 'p053-undersides', 'answer': 'Some are dots, most are insects'},
        {'key': 'p055-wipe', 'answer': 'No, the speckles seem to be scorch marks'}, {'key': 'p-060-tag-closeup', 'answer': 'Picture added'},
        {'key': 'p-066-pot-tag', 'answer': 'No accurate plant tag present'}, {'key': 'p081-whole-plant', 'answer': 'Photos added'}]
ADD = [{'key': 'p036-stem-smell', 'code': 'P-036', 'name': 'Young shrub with toothed leaves (not stevia)',
        'text': 'Roll the stem between your fingers: is it square or round? Then crush a leaf: does it smell of sage, of mint, or of nothing?'}]
PHOTO_DONE = ['Tag close-ups: both Alocasia pots', 'Each philodendron pot with its tag']

c = sqlite3.connect(sys.argv[1]); c.row_factory = sqlite3.Row
rows = {r['code']: r for r in c.execute("SELECT * FROM plants WHERE status='active' ORDER BY code")}
missing = [k for k in rows if k not in FERT]
assert not missing, f'no fertilizer ratio for {missing}'
first = lambda r: [x[0] for x in c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY id LIMIT 1', (r['id'],))]
cur = lambda r, f: '' if r[f] is None else r[f]
ups = []
for code, r in rows.items():
    ratio, strength = FERT[code]
    s = {}
    if ratio: s['npk_ratio'] = ['', ratio]
    s['fert_strength'] = ['', strength]
    note = 'Fertilizer ratio and strength set, for matching it to your fertilizers (batch A2)'
    if code in ANS:
        new, why = ANS[code]
        for f, v in new.items():
            if str(cur(r, f)) != str(v): s[f] = [cur(r, f), v]
        note = why.replace(' (batch A2)', '') + '. Also set the fertilizer ratio and strength (batch A2)'
    ups.append({'code': code, 'name': r['common_name'], 'photos': first(r), 'note': note, 'set': s})
b = {'id': 'batchA2', 'created': '2026-10-23', 'author': 'Claude (batch A2, fertilizer needs and your answers)', 'plants': [], 'existing_photos': [],
     'updates': ups, 'archive': [], 'requests_done': DONE, 'requests_add': ADD, 'to_photograph_done': PHOTO_DONE, 'to_photograph_add': []}
json.dump(b, open(os.path.join(REPO, 'app/seed/batches/batchA2.json'), 'w'), indent=1, ensure_ascii=False)
print(len(ups), 'plants updated,', sum(1 for u in ups if len(u['set']) > 2), 'with answers;', len(DONE), 'requests settled,', len(ADD), 'added')
