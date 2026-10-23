import os as _os
REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))  # repository root
"""Batch 9: Ethan's October 21-22 photo round ("Plant Database New Pics", files named by plant code).
Old values for guarded updates come from a database with batches 1-8 applied (argv[1])."""
import json, os, sqlite3, sys, shutil
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import envdata as E

RAW = REPO + '/dev/photos-raw/raw9'; OUT = REPO + '/app/seed'; PH = OUT + '/photos'
DB = sys.argv[1] if len(sys.argv) > 1 else '/tmp/t18/plants.db'
c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
row = lambda code: c.execute('SELECT * FROM plants WHERE code=?', (code,)).fetchone()
first_photo = lambda code: c.execute('SELECT file FROM photos WHERE plant_id=(SELECT id FROM plants WHERE code=?) ORDER BY id LIMIT 1', (code,)).fetchone()[0]
L = lambda *x: '\n'.join(x)

used = set()
def pic(src, n):
    """raw9/<src>_<n>.jpg -> seed photos/img_b9_<src>_<n>.jpg"""
    key = f'{src}_{n}'; f = f"img_b9_{src.lower().replace('-', '')}_{n}.jpg"
    if key not in used:
        im = Image.open(f'{RAW}/{key}.jpg'); im.thumbnail((1280, 1280)); im.save(f'{PH}/{f}', 'JPEG', quality=80, optimize=True); used.add(key)
    return f

def prof(name, **over):
    d = {**E.PROFILES[name], **over}
    return {k: ('\n'.join(v) if isinstance(v, list) else v) for k, v in d.items()}

existing_photos, updates, new_plants = [], [], []
def photos_for(code, src, items):
    """items: [(n, caption, primary)]"""
    for n, cap, prim in items:
        existing_photos.append({'code': code, 'file': pic(src, n), 'caption': cap, 'primary': prim, 'source': f'{src} ({n})'})

def update(code, note, **new):
    r = row(code)
    s = {f: [r[f], v] for f, v in new.items() if r[f] != v}
    updates.append({'code': code, 'name': r['common_name'], 'photos': [first_photo(code)], 'note': note, 'set': s})

D = 'October 21'

# ---------------------------------------------------------------- P-004 grape
photos_for('P-004', 'P-004', [(3, f'{D}: leaf top', True), (4, f'{D}: pale, felted leaf undersides', False), (5, f'{D}: undersides and a leaf spot', False), (2, f'{D}: whole plant, autumn yellowing', False), (1, f'{D}: shredding bark at the base', False)])
update('P-004', 'Re-identified from new photos (batch 9)',
    scientific_name='Vitis mustangensis (probable)', aliases='Mustang grape (Texas native)', id_confidence=75,
    id_basis="The October photos show the leaf undersides: pale, almost white and felted with hairs, which is the mark of the native mustang grape. The leaves are heart-shaped to shallowly lobed with blunt teeth, the bark shreds at the base, and the plant is vigorous in Texas heat. Most cultivated grapes have green, nearly hairless undersides.",
    id_alternatives=L('Vitis vinifera hybrid (undersides would be greener and less hairy)', 'Vitis cinerea (graybark grape; also has hairy undersides)'),
    id_improve=L('Fruit next summer: mustang grapes are dark purple, thick-skinned and very tart', 'Where the cutting or seedling came from'),
    health_summary='Healthy and growing. Some older leaves are yellowing for autumn, and one leaf has a small brown spot.',
    health_observations=L('Leaf undersides pale and felted (normal for mustang grape)', 'A few yellowing older leaves (autumn)', 'One small brown leaf spot', 'Shredding bark at the base (normal)'))

# ---------------------------------------------------------------- P-005 morning glory
photos_for('P-005', 'P-005', [(4, f'{D}: three-lobed leaf and a hairy flower bud', True), (2, f'{D}: leaf with brown blotches', False), (3, f'{D}: bud with long, narrow, bristly sepals', False), (1, f'{D}: vine on the stake', False), (5, f'{D}: base, dead leaves and spurge weed', False)])
update('P-005', 'Re-identified from new photos (batch 9)',
    common_name='Ivy-leaf morning glory', scientific_name='Ipomoea hederacea (probable)', aliases='Ivyleaf morning glory', id_confidence=75,
    id_basis="The flower buds have very long, narrow, bristly-haired sepals that curl back at the tips, and the leaves are three-lobed and hairy on hairy reddish stems. That combination points to ivy-leaf morning glory. The native tievine has short, nearly hairless sepals.",
    id_alternatives=L('Ipomoea purpurea (common morning glory; heart-shaped leaves, usually unlobed)', 'Ipomoea cordatotriloba (tievine; short sepals)'),
    id_improve=L('An open flower: ivy-leaf morning glory is usually sky blue with a white throat, fading to pink'),
    health_summary='Flowering, but the leaves are pale lime-green with brown blotches, and spurge weed covers the pot.',
    health_observations=L('Pale lime-yellow leaves (hunger or too much sun)', 'Brown blotches on a few leaves', 'Spotted spurge growing in the pot', 'Dead leaves at the base'),
    health_steps=L('Pull the spurge weed (wear gloves; the sap irritates skin).', 'Feed once with a balanced liquid fertilizer at half strength.', 'Remove the dead leaves.', 'It is an annual: collect seed pods when they turn brown if you want it next year.'))

# ---------------------------------------------------------------- P-006 vine
photos_for('P-006', 'P-006', [(1, f'{D}: smooth heart- to arrow-shaped leaves', True), (2, f'{D}: leaf with angular basal lobes', False), (3, f'{D}: twining green stems', False)])
update('P-006', 'Re-identified from new photos (batch 9)',
    common_name='Sweet potato vine (green-leaf, probable)', scientific_name='Ipomoea batatas (probable)', id_confidence=55,
    id_basis="The close-ups show smooth, hairless leaves that are heart-shaped to arrow-shaped, with angular side lobes at the base, on smooth green stems. That fits a green-leaf sweet potato vine. No flower yet.",
    id_alternatives=L('Ipomoea alba (moonflower; leaves more rounded, stems often slightly prickly)', 'Another Ipomoea species', 'Dioscorea (yam vine; veins curve from the base to the tip)'),
    id_improve=L('A flower', 'Dig gently at the base: sweet potato forms a fat tuber'))

# ---------------------------------------------------------------- P-007 Mexican bird of paradise (tag)
photos_for('P-007', 'P-007', [(2, f'{D}: leaves and stems', True), (1, f"{D}: tag 'Mexican Bird of Paradise, Caesalpinia mexicana'", False), (4, f'{D}: Round Rock Garden Center label', False), (3, f'{D}: trunk base and weed seedlings', False)])
update('P-007', 'Identified from its tag (batch 9)',
    common_name='Mexican bird of paradise', scientific_name='Caesalpinia mexicana (Erythrostemon mexicanus)', aliases='Mexican holdback; Bird of paradise, Mexican (Round Rock Garden Center)', plant_type='Shrub / small tree (legume)',
    id_confidence=95, id_basis="Identified from its plant tag ('Mexican Bird of Paradise, Caesalpinia mexicana') and the Round Rock Garden Center label 'BIRD OF PARADISE MEXICAN NTN #1, $14.00'. The rounded leaflets in pairs on bipinnate leaves match. It is not a moringa.",
    id_alternatives=L('Caesalpinia pulcherrima (red bird of paradise; leaflets smaller, flowers red-orange)'), id_improve=L('Yellow flower clusters next spring or summer would settle it completely'),
    temp_ideal_low=60, temp_ideal_high=100, temp_damage_below=20, temp_lethal_below=10, temp_damage_above=115,
    temp_notes='Hardy in Central Texas. It may drop some leaves below about 25°F but recovers. In a pot the roots are more exposed than in the ground, so protect it below about 20°F.',
    humidity_low=20, humidity_high=70, humidity_notes='Not fussy. Dry air is fine.',
    light_summary='Full sun', light_hours='6+ hours of direct sun', light_notes='Flowers best in full sun. In shade it gets leggy and blooms little.',
    winter_plan='Hardy outside', winter_summary='Hardy outside in Round Rock. Leave it out; cover it or move it against the house on nights below about 20°F.',
    winter_triggers='Cover or move it against the house when a night below 20°F is forecast.', winter_steps=L('Stop feeding in September.', 'Water only when the mix is dry.', 'Cover or move it to shelter on nights below 20°F.'), indoor_setup='',
    health_rating='Good', health_summary='Healthy, clean leaves and a sturdy trunk. Small weed seedlings are coming up in the pot.',
    health_observations=L('Clean green leaflets', 'Sturdy trunk', 'Weed seedlings in the pot'), health_steps=L('Pull the weed seedlings.', 'Move it into the sunniest spot you have.', 'Pot up or plant in the ground in spring: it grows into a 6-10 ft shrub.'),
    par_low=1000, par_high=2000, dli_low=25, dli_high=45, vpd_low=0.8, vpd_high=2.5, soil_moisture_low=10, soil_moisture_high=35, soil_temp_low=55, soil_temp_high=95, soil_ph_low=6.0, soil_ph_high=8.0,
    water_notes='Drought-tolerant once established. In a pot, water deeply when the top 2 in (5 cm) are dry; in winter much less.',
    soil_medium='Fast-draining mix: potting soil with about a third grit, pumice or perlite. It tolerates alkaline Texas soil.',
    fertilizer='Balanced slow-release or 10-10-10', nutrients='Feed lightly in spring and early summer. Too much nitrogen gives leaves and fewer flowers.',
    fert_from_month=3, fert_to_month=8, fert_every_days=45)

# ---------------------------------------------------------------- P-009 Birkin (tag)
photos_for('P-009', 'P-009', [(3, f'{D}: pinstriped Birkin leaves', True), (2, f"{D}: tag 'Philodendron Birkin'", False), (4, f'{D}: new leaves with red sheaths', False), (1, f'{D}: base and an all-green leaf', False)])
update('P-009', 'Identified from its tag (batch 9)',
    common_name="Philodendron 'Birkin'", scientific_name="Philodendron 'Birkin'", aliases='', id_confidence=90,
    id_basis="A hand-written tag in the pot reads 'Philodendron Birkin', and the dark leaves with fine white pinstripes match. Birkin sometimes puts out plain green leaves; that is normal.",
    id_alternatives=L("Philodendron 'White Wave' or 'White Measure' (similar pinstriped types)"), id_improve=L('A mature leaf in good light'),
    health_rating='Fair', health_summary='Recovering. Several leaves droop or curl and some old ones are dead, but new leaves with red sheaths are coming.',
    health_observations=L('Drooping, curled leaves', 'Dead papery leaves at the base', 'New leaves emerging from red sheaths', 'One plain green leaf (normal for Birkin)'),
    health_steps=L('Remove the dead leaves.', 'Water when the top inch is dry; do not let it sit wet.', 'Bright indirect light, no direct afternoon sun.', 'Bring it inside before nights reach 55°F.'))

# ---------------------------------------------------------------- P-010 Dieffenbachia (tag)
photos_for('P-010', 'P-010', [(4, f'{D}: new leaves on the canes', True), (2, f"{D}: tag 'Dieffenbachia Seguine'", False), (3, f'{D}: Costa Farms label', False), (1, f'{D}: canes with dried tops', False), (5, f'{D}: side view', False)])
update('P-010', 'Identified from its tags (batch 9)',
    common_name='Dieffenbachia (dumb cane)', scientific_name='Dieffenbachia seguine', aliases='Dumb cane; Costa Farms Wick and Grow pot', id_confidence=90,
    id_basis="A hand-written tag reads 'Dieffenbachia Seguine', and the Costa Farms label reads '1.40-QT DIEFFENBACHIA WCK AND GRW' (a self-watering wick pot). The jointed green canes and broad leaves match.",
    id_alternatives=L('A named Dieffenbachia cultivar (the label gives none)'), id_improve=L('A mature leaf in good light, to see its pattern'),
    temp_notes='The label says to keep it above 50°F. Below that the leaves are damaged.',
    health_summary='Lots of healthy new leaves, but the tops of several canes have papery dead sheaths and leaves. Spurge weed in the pot.',
    health_observations=L('Healthy new leaves', 'Papery dead leaf bases on the cane tops', 'Spurge weed in the pot'),
    health_steps=L('Remove the dead leaves and sheaths (wear gloves: the sap irritates).', 'Pull the spurge.', 'Water weekly or when the top inch is dry, as the label says.', 'Bring it inside before nights reach 50°F.'))

# ---------------------------------------------------------------- P-011 peace lily (variegated)
photos_for('P-011', 'P-011', [(1, f'{D}: leaves with large cream and yellow sectors', True), (3, f'{D}: the clump from above', False), (2, f'{D}: roots showing at the soil surface', False)])
update('P-011', 'Re-identified from new photos (batch 9)',
    common_name='Variegated peace lily', scientific_name="Spathiphyllum, variegated cultivar ('Picasso' type)", aliases="Spathiphyllum 'Picasso'?", id_confidence=65,
    id_basis="The leaves come straight up from the soil in a clump, with sheathing stalks and papery old sheaths, so it is a peace lily rather than a Dieffenbachia (which grows on a cane). The variegation is in large cream-white and yellow sectors, not fine speckles, which fits 'Picasso' better than 'Domino'.",
    id_alternatives=L("Spathiphyllum 'Domino' (speckled and streaked)", "Spathiphyllum 'Sensation Variegated'"), id_improve=L('A flower', 'A tag or where it came from'),
    health_summary='Mostly clean, glossy leaves. Roots are showing at the soil surface, a few leaf edges are brown, and there are old dead leaves in the centre.',
    health_observations=L('Roots exposed at the surface', 'A few brown edges and one yellowing leaf', 'Dead strap-like old leaves in the centre'),
    health_steps=L('Cover the exposed roots with an inch of fresh mix, or pot up one size in spring.', 'Pull out the dead leaves.', 'Keep it out of direct sun: the white parts burn easily.', 'Bring it inside before nights reach 50°F.'))

# ---------------------------------------------------------------- P-012 aeonium
photos_for('P-012', 'P-012', [(3, f'{D}: rosette with fine-toothed edges', True), (2, f'{D}: the whole bowl', False), (1, f'{D}: stem with aerial roots', False), (4, f'{D}: branching stems', False), (5, f'{D}: side view', False)])
update('P-012', 'ID refined from new photos (batch 9)',
    scientific_name='Aeonium haworthii type (probable)', aliases="Haworth's aeonium; pinwheel aeonium", id_confidence=70,
    id_basis="A much-branched little shrub with many small rosettes, leaf edges fringed with fine teeth, and hair-like aerial roots on the stems. That fits Aeonium haworthii (pinwheel aeonium).",
    id_alternatives=L("Aeonium 'Kiwi' (similar habit, but yellow-and-red variegated)", 'Aeonium decorum'),
    health_summary='Leggy, with yellowing leaves and dark spots on some, after summer stress. New rosettes are forming now that it is cooler.',
    health_observations=L('Yellowing leaves with dark spots or tips', 'Long bare stems', 'Aerial roots on the stems (it wants water)', 'New small rosettes forming'),
    health_steps=L('Remove the spotted and yellow leaves.', 'It grows in the cool season: water when the mix is dry and give it morning sun.', 'Cut back very long stems in spring and root the tops in dry mix.', 'Move it under cover before nights reach 30°F.'))

# ---------------------------------------------------------------- P-014: three aloes
aloe_common = dict(scientific_name='Aloe vera (spotted young form) or a hybrid', aliases='', plant_type='Succulent',
    id_basis="Grey-green leaves with white speckles and pale teeth along the edges, in an upright rosette. Young Aloe vera is spotted like this; the spots fade as it matures. Ethan's photos show three separate pots, so each now has its own page.",
    id_alternatives=L('Aloe vera', 'Aloe maculata (soap aloe; flatter, more strongly banded)', "An Aloe hybrid such as 'Hercules' (young)"),
    id_improve=L('A flower spike: Aloe vera has yellow flowers', 'Any tag or receipt'))
photos_for('P-014', 'P-014', [(6, f'{D}: P-014, the biggest of the three aloes (black pot, gravel)', True), (3, f'{D}: P-014 from above', False), (4, f'{D}: P-014 base', False)])
update('P-014', 'Split into three pages: this one is the biggest aloe (batch 9)',
    common_name='Aloe vera (probable), largest of three', container='Black nursery pot with white gravel and bark', id_confidence=60, **{k: v for k, v in aloe_common.items() if k != 'aliases'},
    health_summary='Firm and upright. Leaves are tinged orange-tan from sun or cold stress, and some leaf tips are dry.',
    health_observations=L('Orange-tan stress colour', 'Dry leaf tips', 'Firm, upright leaves'),
    health_steps=L('Cut off fully dried leaf tips if you like (cosmetic).', 'Water only when the mix is dry through.', 'Move it under cover before nights reach 32°F.'))
for title, cont, nums, cap, health in [
    ('Aloe vera (probable), teal pot', 'Teal-green plastic pot, next to a terracotta pot', [(1, 'from above', True), (7, 'side view', False)], 'teal pot', 'Slimmer and upright; leaves tinged orange-tan.'),
    ('Aloe vera (probable), black pot by the prickly pear pad', 'Black nursery pot (behind the pot holding a prickly pear pad)', [(2, 'from above, curled dry leaf tips', True), (5, 'side view', False)], 'black pot', 'Several leaf tips are dry and curled; leaves tinged orange-tan.')]:
    r = row('P-014')
    d = {k: r[k] for k in ('temp_ideal_low', 'temp_ideal_high', 'temp_damage_below', 'temp_lethal_below', 'temp_notes', 'humidity_low', 'humidity_high', 'humidity_notes',
                           'light_summary', 'light_hours', 'light_notes', 'winter_plan', 'winter_summary', 'winter_triggers', 'winter_steps', 'indoor_setup', 'notes',
                           'temp_damage_above', 'vpd_low', 'vpd_high', 'par_low', 'par_high', 'dli_low', 'dli_high', 'water_notes', 'soil_medium', 'soil_ph_low', 'soil_ph_high',
                           'soil_moisture_low', 'soil_moisture_high', 'soil_temp_low', 'soil_temp_high', 'fertilizer', 'nutrients', 'fert_from_month', 'fert_to_month', 'fert_every_days',
                           'pests_watch', 'pest_steps', 'pests_current')}
    d.update(aloe_common, common_name=title, location=r['location'], container=cont, id_confidence=60, health_rating='Fair', health_summary=health,
             health_observations=L('Orange-tan stress colour', 'Dry leaf tips'), health_steps=L('Water only when the mix is dry through.', 'Move it under cover before nights reach 32°F.'),
             notes='Split from P-014 on ' + D + ' 2026: the old P-014 page covered three pots.', site='Outdoors')
    d['photos'] = [{'file': pic('P-014', n), 'caption': f'{D}: {c2}', 'primary': pr, 'source': f'P-014 ({n})'} for n, c2, pr in nums]
    new_plants.append(d)

# ---------------------------------------------------------------- P-015 hardy aloe (tag)
photos_for('P-015', 'P-015', [(1, f'{D}: rosettes', True), (2, f"{D}: tag 'Hardy Aloe Striatula'", False), (3, f'{D}: striped leaf bases on the stem', False), (4, f'{D}: offsets', False)])
update('P-015', 'Identified from its tag (batch 9)',
    common_name='Hardy aloe (Aloe striatula)', scientific_name='Aloiampelos striatula (syn. Aloe striatula)', aliases='Hardy aloe; Coral aloe', id_confidence=95,
    id_basis="A hand-written tag reads 'Hardy Aloe Striatula'. The narrow, toothed, bright-green leaves on sprawling stems, with green-striped leaf bases, match.",
    id_alternatives=L('Aloiampelos ciliaris (climbing aloe)'), id_improve=L('Orange-yellow flowers in late spring'),
    temp_ideal_low=50, temp_ideal_high=95, temp_damage_below=15, temp_lethal_below=5,
    temp_notes='One of the hardiest aloes: survives about 10-15°F if the roots are dry. Wet, cold soil is the danger, not the cold itself.',
    winter_plan='Hardy outside', winter_summary='Hardy outside in Round Rock. Keep it fairly dry in winter; cover it on nights below about 15°F.',
    winter_triggers='Cover it when a night below 15°F is forecast.', winter_steps=L('Water very little from November to February.', 'Cover with frost cloth on nights below 15°F.'), indoor_setup='',
    health_rating='Good', health_summary='Healthy, firm green leaves and new offsets.', health_observations=L('Firm green leaves', 'New offsets at the base'))

# ---------------------------------------------------------------- P-016: two different plants
photos_for('P-016', 'P-016', [(4, f'{D}: zebra haworthia from above', True), (7, f'{D}: zebra haworthia, offsets', False), (2, f'{D}: zebra haworthia, dry tips', False), (3, f'{D}: zebra haworthia side view', False)])
update('P-016', 'Split: the speckled rosette in the same pot has its own page now (batch 9)',
    common_name='Zebra haworthia', scientific_name='Haworthiopsis attenuata type', aliases='Zebra plant; zebra cactus', id_confidence=75,
    id_basis="Stiff, narrow, pointed green leaves with raised white bumps arranged in cross-bands, forming clumps of offsets. That is the zebra haworthia. The broader, dark, white-dotted rosette in the same pot is a different plant and has its own page.",
    id_alternatives=L('Haworthiopsis fasciata (bands only on the outer face)', 'Haworthiopsis coarctata'), id_improve=L('A side view of one leaf, showing whether the inner face is smooth'),
    container='Terracotta bowl with perlite and bark (shared with the speckled rosette)',
    health_summary='Healthy and offsetting. Many leaf tips have dried white, and a few outer leaves are dead.', health_observations=L('Dry white leaf tips (sun)', 'A few dead outer leaves', 'Offsets forming'))
r = row('P-016')
d = {**prof('aloe'), 'temp_ideal_low': 55, 'temp_ideal_high': 85, 'temp_damage_below': 32, 'temp_lethal_below': 25, 'temp_notes': 'Treat as frost-tender until identified.',
     'humidity_low': 10, 'humidity_high': 60, 'humidity_notes': 'Dry air is fine.', 'light_summary': 'Bright light, morning sun', 'light_hours': '4-6 hours', 'light_notes': 'Bronze colour means it is getting plenty of sun; shade it from hot afternoon sun.',
     'winter_plan': 'Move indoors', 'winter_summary': 'Small and frost-tender. Bring the pot under cover before nights reach 35°F.', 'winter_triggers': 'Move the pot when a night below 35°F is forecast.',
     'winter_steps': L('Water lightly in winter.', 'Bright window or porch.'), 'indoor_setup': '', 'notes': 'Split from P-016 on October 21, 2026: the two rosettes in that pot are different plants.',
     'common_name': 'Speckled dwarf aloe (in the zebra haworthia pot)', 'scientific_name': 'Dwarf Aloe hybrid or xGasteraloe (unconfirmed)', 'aliases': '', 'plant_type': 'Succulent',
     'location': r['location'], 'container': 'Terracotta bowl with perlite and bark (shared with P-016)', 'id_confidence': 40,
     'id_basis': 'Broad, flat, spiralling dark olive-brown leaves covered in small white dots, with fine white teeth along the edges and papery white tips. That fits one of the many dwarf Aloe hybrids or an Aloe x Gasteria cross. It is not the same plant as the zebra haworthia beside it.',
     'id_alternatives': L('Dwarf Aloe hybrid', 'xGasteraloe', 'Aristaloe aristata (lace aloe; has long hair-like tips)'),
     'id_improve': L('A flower spike', 'A side view of one leaf, and of the whole rosette', 'Where it came from'),
     'health_rating': 'Fair', 'health_summary': 'Firm, but sun-bronzed, and one outer leaf is dying back.', 'health_observations': L('Dark bronze colour (sun stress)', 'Papery white leaf tips', 'One outer leaf dying back'),
     'health_steps': L('Give it a little afternoon shade.', 'Water only when the mix is dry through.'), 'site': 'Outdoors',
     'fert_from_month': 4, 'fert_to_month': 8, 'fert_every_days': 42, 'pests_current': E.PESTS_NOW_DEFAULT}
d['photos'] = [{'file': pic('P-016', n), 'caption': f'{D}: {cap}', 'primary': pr, 'source': f'P-016 ({n})'} for n, cap, pr in [(5, 'speckled rosette from above', True), (6, 'side view', False), (1, 'a leaf dying back', False)]]
new_plants.append(d)

# ---------------------------------------------------------------- P-018
photos_for('P-018', 'P-018', [(2, f'{D}: plump pink leaves and small grey rosettes', True), (3, f'{D}: sprawling stems', False), (1, f'{D}: from above, with spurge weed', False)])
update('P-018', 'ID refined from new photos (batch 9)',
    common_name='Graptosedum (blush succulent)', scientific_name="xGraptosedum 'Francesco Baldi' type (probable)", aliases='', id_confidence=60,
    id_basis="Long, plump, round-tipped leaves in pastel pink and lavender, on stems that sprawl over the pot edge. That fits xGraptosedum 'Francesco Baldi'. The small grey-blue rosettes among them may be ghost plant (Graptopetalum paraguayense) offsets or a second plant.",
    id_alternatives=L('Graptopetalum paraguayense (ghost plant; flatter, more pointed leaves)', 'xPachyveria'),
    health_summary='Healthy blush colour and plump leaves. Spurge weed is growing through it.', health_observations=L('Plump, firm leaves', 'Spurge weed throughout the pot'),
    health_steps=L('Pull the spurge weed.', 'Water only when the mix is dry.', 'Move it under cover before nights reach 28°F.'))

# ---------------------------------------------------------------- P-022 rose (tag)
photos_for('P-022', 'P-022', [(2, f'{D}: the rose in its black pot', True), (1, f"{D}: Weeks Roses tag 'Queen of Elegance'", False), (3, f'{D}: back of the tag', False)])
update('P-022', 'Identified from its tag (batch 9)',
    common_name="Rose 'Queen of Elegance'", scientific_name="Rosa 'WEKjucstokol' (Queen of Elegance), floribunda", aliases='Weeks Roses, Pat. #32,810; hybridizer Tom Carruth (2020)', id_confidence=98,
    id_basis="The Weeks Roses tag reads 'Queen of Elegance, cv. WEKjucstokol, Floribunda'. It is medium pink, very double (40-90 petals, 3.5-4.5 in blooms) with a strong rose fragrance, medium-tall and upright; parents Life of the Party x Koko Loko.",
    id_alternatives='', id_improve=L('Nothing more needed'),
    light_summary='Full sun', light_hours='At least 6 hours of direct sun (from the tag)',
    health_summary='Leafy and growing, but many leaflets still have red-brown scorched edges.')

# ---------------------------------------------------------------- P-024 fern (tag)
photos_for('P-024', 'P-024', [(1, f'{D}: new green fronds and fiddleheads', True), (2, f"{D}: tag 'Nephrolepis Exaltata Emina'", False)])
update('P-024', 'Identified from its tag; recovering (batch 9)',
    common_name="Boston fern 'Emina'", scientific_name="Nephrolepis exaltata 'Emina'", aliases='Emina fern; curly Boston fern', id_confidence=95,
    id_basis="A hand-written tag reads \"Nephrolepis Exaltata 'Emina'\". 'Emina' is a compact, upright Boston fern with tightly crimped fronds, which matches the new growth.",
    id_alternatives='', id_improve=L('Nothing more needed'),
    health_rating='Poor', health_summary='Recovering. Several new green fronds and small fiddleheads are growing, though most old fronds are dead.',
    health_observations=L('New green fronds and fiddleheads', 'Old fronds brown and crisp'),
    health_steps=L('Cut the dead fronds off at the base so light reaches the new ones.', 'Keep the mix evenly moist, never dry.', 'Bright indirect light, no sun.', 'Bring it inside before nights reach 45°F.'))

# ---------------------------------------------------------------- P-025 begonia
photos_for('P-025', 'P-025', [(1, f'{D}: hairy, lobed leaves', True), (4, f'{D}: hairy leaf stalk', False), (2, f'{D}: whole plant and tag', False), (3, f'{D}: base and drip emitter', False)])
update('P-025', 'ID refined from new photos (batch 9)', id_confidence=75,
    id_basis="Hairy, lobed and toothed bright-green leaves with lopsided bases, on hairy reddish stalks: a Begonia for sure. The leaf shape fits a young tuberous begonia or a hairy shrub-type begonia; the tag in the pot would settle it.",
    id_improve=L('A photo of the hand-written tag in the pot (only part of it shows)', 'A flower'))

# ---------------------------------------------------------------- P-029 / P-030: same pot
photos_for('P-029', 'P-029', [(1, f'{D}: dark burgundy new leaf with pink streaks', True)])
photos_for('P-029', 'P-030', [(3, f'{D}: the whole pot (the offshoot P-030 is at the base)', False), (1, f"{D}: Costa Farms tag 'Pink Princess Philodendron'", False)])
update('P-029', 'Identified from the Costa Farms tag in its pot (batch 9)',
    common_name="Philodendron 'Pink Princess'", scientific_name="Philodendron erubescens 'Pink Princess'", aliases='Costa Farms', id_confidence=85,
    id_basis="A Costa Farms tag in the pot reads 'Pink Princess Philodendron'. The new leaf is dark burgundy with pink streaks and the stalks are red, which fits. Many older leaves are marbled cream-yellow rather than pink; that happens with bright light and with some plants sold as Pink Princess. P-030 is a small offshoot growing from the base of this plant, in the same pot.",
    id_alternatives=L("Philodendron 'Strawberry Shake' (cream-and-pink marbled)", "Philodendron 'Pink Congo' (treated, solid pink)"), id_improve=L('A mature leaf in shade, to see how much pink it keeps'))
photos_for('P-030', 'P-030', [(2, f'{D}: the pink offshoot at the base', True)])
update('P-030', 'Ethan: this is a baby shoot growing out of the Pink Princess, P-029 (batch 9)',
    common_name="Pink Princess offshoot (in P-029's pot)", container="Same black pot as P-029 (orange hand-written tag)", id_confidence=85,
    id_basis="Ethan says this is a baby shoot growing out of the Pink Princess (P-029), in the same pot, which has a Costa Farms 'Pink Princess Philodendron' tag.",
    id_alternatives='', id_improve='',
    health_rating='Poor', health_summary='A pale pink-and-white shoot at the base among dried leaves. It is alive, but leaves with little green make little food, so it depends on the mother plant.',
    health_observations=L('Pale pink-white new shoot', 'Dried leaves around it'),
    health_steps=L('Leave it attached to the mother plant.', 'Pull away the dried leaves around it.', 'Separate it only when it has 2-3 leaves with some green and its own roots.'))

# ---------------------------------------------------------------- P-031 calathea
photos_for('P-031', 'P-031', [(4, f'{D}: striped leaves', True), (3, f"{D}: tag '05.24.26 Brett b-day gift'", False), (2, f'{D}: red-purple leaf underside', False), (1, f'{D}: base with new shoots and roots', False)])
update('P-031', 'ID refined from new photos (batch 9)',
    common_name='Calathea (feather-striped)', scientific_name="Goeppertia sp. ('Freddie' / concinna type, unconfirmed)", aliases='Calathea', id_confidence=55,
    id_basis="Mid-green leaves with pale silvery-green feathered stripes along the side veins, on long stalks from a clump; one leaf shows a red-purple underside. That fits Goeppertia concinna ('Freddie') or G. leopardina.",
    id_alternatives=L('Goeppertia leopardina', 'Ctenanthe burle-marxii (fishbone prayer plant)', "Goeppertia 'Rattlesnake' (wavy edges, dark spots)"), id_improve=L('A clear photo of one healthy leaf, front and back'),
    notes="A hand-written tag reads '05.24.26 Brett b-day gift!' (a birthday gift, May 24, 2026).",
    health_summary='Still many brown, crisped leaves, but several clean striped leaves and new shoots are growing, with white roots at the base.',
    health_observations=L('Many brown crisped leaves', 'Several clean new leaves', 'New shoots and white roots at the base', 'Drip emitter in the pot'))

# ---------------------------------------------------------------- P-035
photos_for('P-035', 'P-035', [(3, f'{D}: new leaves and the hollow old stem with the stake in it', True), (1, f'{D}: pale marbled leaf', False), (2, f'{D}: dead leaves', False)])
update('P-035', 'New photos: new leaves forming (batch 9)',
    health_rating='Poor', health_summary='New leaves are forming, but the old cutting stem is hollow and the bamboo stake is pushed down into it.',
    health_observations=L('Two or three new pale-green, cream-marbled leaves', 'Old cutting stem hollow', 'Bamboo stake inside the hollow stem', 'Several dead papery leaves'),
    health_steps=L('Pull the stake out of the hollow stem; water collects there and rots it.', 'Remove the dead leaves.', 'Keep the mix barely moist and warm (above 65°F).', 'Bright indirect light.'))

# ---------------------------------------------------------------- P-036
photos_for('P-036', 'P-036', [(1, f'{D}: opposite, toothed leaves', True), (2, f'{D}: leaves tapering to the base', False), (3, f'{D}: woody stem', False), (4, f'{D}: base', False)])
update('P-036', 'Possible ID from new photos (batch 9)',
    common_name='Possible stevia (young, serrated leaves)', scientific_name='Stevia rebaudiana (possible)', aliases='Sweetleaf?', plant_type='Herb / perennial', id_confidence=50,
    id_basis="Thin, woody brown stems with opposite pairs of light-green leaves that narrow to the base and are coarsely toothed toward the tip. That fits stevia. A taste test settles it: stevia leaves are intensely sweet.",
    id_alternatives=L('Hydrangea cutting', 'Salvia', 'Eupatorium'), id_improve=L('Tear a leaf, touch it to your tongue and spit it out: stevia tastes very sweet', 'A flower (stevia has small white flowers in autumn)'))

# ---------------------------------------------------------------- P-039 Painted Lady (tag)
photos_for('P-039', 'P-039', [(1, f'{D}: yellow, green-speckled leaves', True), (3, f"{D}: tag 'Philodendron Painted Lady'", False), (2, f'{D}: roots growing out of the pot', False)])
update('P-039', 'Identified from its tag (batch 9)',
    common_name="Philodendron 'Painted Lady'", scientific_name="Philodendron 'Painted Lady'", aliases='', id_confidence=90,
    id_basis="A hand-written tag reads \"Philodendron 'Painted Lady'\". Bright yellow leaves speckled with green, on orange-pink stalks, match.",
    id_alternatives='', id_improve=L('Nothing more needed'), container='Clear plastic pot',
    health_summary='Colourful and growing, but root-bound: many roots grow out of the bottom of the pot. One leaf has a brown spot.',
    health_observations=L('Many roots growing out of the drainage holes', 'One brown leaf spot'),
    health_steps=L('Pot it up one size (1-2 in wider) into chunky aroid mix.', 'Bright indirect light.', 'Bring it inside before nights reach 55°F.'))

# ---------------------------------------------------------------- P-042 agave
photos_for('P-042', 'P-042', [(1, f'{D}: leaf with yellow-orange blotches', True), (2, f'{D}: yellowing lowest leaf base', False), (3, f'{D}: from above', False)])
update('P-042', 'New photos show leaf blotches (batch 9)',
    health_rating='Fair', health_summary='Firm overall, but one leaf has yellow-orange blotches, the lowest leaf base is yellow with a brown patch, and another leaf has a scar.',
    health_observations=L('Yellow-orange blotches on one leaf', 'Lowest leaf base yellow with a brown patch', 'A leaf with a yellow streak and scar', 'A small pink-flowered weed in the tub'),
    health_steps=L('Press the yellow lowest leaf near its base: firm means it is an old leaf dying back (cut it off); soft or smelly means rot (unpot and check the core).', 'Keep it dry; water only when the mix is dry through.', 'Pull the weed.', 'Move it under cover before nights reach 25°F.'))

# ---------------------------------------------------------------- P-044 = boobie cactus (P-002 before repotting)
p2 = row('P-002')
shutil.copy(f'{PH}/{first_photo("P-002")}', f'{PH}/img_b9_p002_before.jpg')
existing_photos.append({'code': 'P-044', 'file': 'img_b9_p002_before.jpg', 'caption': 'Before repotting, in the Costa Farms pot (was page P-002)', 'primary': False, 'source': 'P-002'})
photos_for('P-044', 'P-044', [(5, f'{D}: after repotting', True), (1, f'{D}: star shape from above', False), (2, f'{D}: next to a 16 oz can (about 5 in tall)', False), (4, f'{D}: side view', False), (7, f'{D}: from above', False)])
keep = ['common_name', 'scientific_name', 'aliases', 'plant_type', 'id_basis', 'id_alternatives', 'id_improve', 'temp_ideal_low', 'temp_ideal_high', 'temp_damage_below', 'temp_lethal_below', 'temp_notes',
        'humidity_low', 'humidity_high', 'humidity_notes', 'light_summary', 'light_hours', 'light_notes', 'winter_plan', 'winter_summary', 'winter_triggers', 'winter_steps', 'indoor_setup',
        'temp_damage_above', 'vpd_low', 'vpd_high', 'par_low', 'par_high', 'dli_low', 'dli_high', 'water_notes', 'soil_medium', 'soil_ph_low', 'soil_ph_high', 'soil_moisture_low', 'soil_moisture_high',
        'soil_temp_low', 'soil_temp_high', 'fertilizer', 'nutrients', 'fert_from_month', 'fert_to_month', 'fert_every_days', 'pests_watch', 'pest_steps']
update('P-044', 'Ethan: P-002 and P-044 are the same plant (P-002 was before repotting). This page is now the boobie cactus (batch 9)',
    **{k: p2[k] for k in keep}, id_confidence=95, container='Black nursery pot (repotted)',
    health_rating='Good', health_summary='Firm, plump and pale green after repotting. A small corky mark low on the stem.',
    health_observations=L('Firm, plump tubercles', 'Small corky mark low on the stem (old scar)'),
    health_steps=L('Water only when the mix is dry through; less in winter.', 'Full sun once acclimated.', 'Move it under cover before nights reach 35°F.'),
    pests_current='None seen.',
    notes="Same plant as P-002, which was the page from before repotting (P-002 is archived). An earlier version of this page described a 'fuzzy-leaved succulent'; that came from another pot visible beside the cactus in an October photo.")
archive = [{'code': 'P-002', 'name': p2['common_name'], 'photos': [first_photo('P-002')], 'note': 'Same plant as P-044 (this page is from before repotting); archived in favour of P-044 (batch 9)'}]

# ---------------------------------------------------------------- P-051
photos_for('P-051', 'P-051', [(1, f'{D}: striped leaves from above', True), (2, f'{D}: leaves clasping the stem', False), (3, f'{D}: creeping stem rooting at the nodes', False)])
update('P-051', 'Identified from new photos (batch 9)',
    common_name='Variegated tradescantia (lime, white-striped)', scientific_name="Tradescantia, variegated (T. fluminensis or T. albiflora 'Albovittata' type)", aliases='Inch plant; wandering dude', plant_type='Trailing perennial',
    id_confidence=65, container='Long white planter box with red lava-rock mix',
    id_basis="Jointed, creeping stems that root at the nodes, and lance-shaped leaves that clasp the stem with a short, slightly hairy sheath. The leaves are lime-green with fine white pinstripes. That is a variegated Tradescantia.",
    id_alternatives=L('Callisia (smaller leaves)', "Tradescantia 'Lemon Lime'"), id_improve=L('A flower: Tradescantia flowers have three petals (white for T. fluminensis)'),
    health_summary='Lots of new shoots. A few leaves have brown edges or spots.', health_observations=L('Many new shoots', 'A few brown leaf edges and spots'))

# ---------------------------------------------------------------- P-053
photos_for('P-053', 'P-053', [(2, f'{D}: vine with tendrils, an insect on a top leaf', True), (1, f'{D}: clusters of black specks on the leaves', False), (3, f'{D}: specks and yellowing', False)])
update('P-053', 'New photos show possible insects (batch 9)',
    pests_current='October 21: clusters of tiny black specks on several leaves (seen against the light) and a small insect on a top leaf. Possibly black aphids or their droppings, or thrips. Not confirmed.',
    health_observations=L('Clusters of tiny black specks on several leaves', 'A small insect on a top leaf', 'Older leaves yellowing with brown spots', 'Tendrils and new growth at the top'),
    health_steps=L('Look under the speckled leaves with a magnifier or phone zoom.', 'Hose the leaves (top and underside) with a strong spray.', 'Then spray insecticidal soap every 5-7 days, three times.', 'Feed with a balanced fertilizer: the perlite-heavy mix is hungry.', 'It is frost-tender; it will likely die back at the first frost.'))

# ---------------------------------------------------------------- P-055 Black Cardinal (label)
photos_for('P-055', 'P-055', [(1, f'{D}: leaves with white specks', True), (3, f"{D}: HEB label 'PHILO BLK CARDNL'", False), (2, f'{D}: drooping leaves', False), (4, f'{D}: base', False)])
update('P-055', 'Identified from its HEB label (batch 9)',
    common_name="Philodendron 'Black Cardinal'", scientific_name="Philodendron 'Black Cardinal'", aliases='HEB clearance, $1 (was $8), Sept 30 2026', id_confidence=85,
    id_basis="The HEB clearance label reads 'HEB PHILO BLK CARDNL 5in' (Philodendron Black Cardinal). It is a self-heading philodendron whose new leaves open copper-red and darken to near black; the reddish stalks fit.",
    id_alternatives=L("Philodendron 'Black Congo'", "Philodendron 'Rojo Congo'"), id_improve=L('A healthy new leaf as it opens'),
    health_rating='Poor', health_summary='Struggling: many leaves are yellow-orange with dead brown tips and droop, and the green leaves are covered in small white specks.',
    health_observations=L('Small white specks over the leaves', 'Yellow-orange leaves with dead tips', 'Drooping leaves', 'Papery dead sheaths at the base'),
    health_steps=L('Wipe one speckled leaf with a damp cloth: if the specks come off they are mineral spots from water; if not, look under the leaves for thrips or mites and treat with insecticidal soap.', 'Cut off the dead and mostly yellow leaves.', 'Bright indirect light, no direct sun.', 'Water when the top inch is dry.', 'Bring it inside before nights reach 55°F.'))

# ---------------------------------------------------------------- P-056 Alocasia (label)
photos_for('P-056', 'P-056', [(2, f'{D}: the big glossy leaf', True), (3, f'{D}: baby leaves at the base', False), (1, f"{D}: HEB label 'ALOCASIA NIGRA'", False)])
update('P-056', 'Label found (batch 9)',
    common_name="Alocasia (sold as 'Nigra')", aliases="HEB clearance label 'ALOCASIA NIGRA FOLIAGE' (faded), $1 (was $8), Sept 30 2026", id_confidence=60,
    id_basis="The HEB clearance label reads 'HEB ALOCASIA NIGRA FOLIA...' (faded). 'Nigra' is a store name rather than a registered cultivar. The large, glossy, dark, wavy-edged leaf fits Alocasia 'Regal Shields' type hybrids.",
    id_alternatives=L("Alocasia 'Regal Shields'", "Alocasia 'Yucatan Princess'", 'Alocasia odora (paler)'), id_improve=L('A photo of the leaf underside (purple or green?)'),
    health_summary='One large healthy leaf and three baby leaves at the base.')

# ---------------------------------------------------------------- P-061 Alocasia (tag)
photos_for('P-061', 'P-061', [(1, f'{D}: lime-green, wavy leaves', True), (4, f'{D}: mottled leaf stalks', False), (5, f'{D}: dead leaf base at the soil', False), (3, f"{D}: tag 'Alocasia'", False), (2, f'{D}: crumpled newer leaf', False)])
update('P-061', 'Tag found: it only says Alocasia (batch 9)',
    common_name='Alocasia (lime-green, mottled stalks)', scientific_name="Alocasia 'Sarian' or 'Portora' type (unconfirmed)", id_confidence=55,
    id_basis="The tag only says 'Alocasia' with care notes. The leaf stalks are mottled and striped brown, and the arrow-shaped leaves have wavy edges and stand upright, which fits Alocasia 'Sarian' or 'Portora'.",
    id_alternatives=L('Alocasia odora (plain green stalks)', 'Alocasia x Calidora'), id_improve=L('A photo of the whole plant from the side'),
    health_summary='Large leaves, but pale lime from strong sun. One newer leaf is crumpled and a dead leaf base is rotting at the soil.',
    health_observations=L('Pale lime leaves (too much sun)', 'One crumpled newer leaf', 'A dead leaf base at the soil'),
    health_steps=L('Pull out the dead leaf base.', 'Move it to bright shade.', 'Water when the top 2 in are dry (from the tag).', 'Bring it inside before nights reach 55°F.'))

# ---------------------------------------------------------------- P-066 micans runner
photos_for('P-066', 'P-066', [(3, f'{D}: velvety new leaves with red stalks', True), (4, f'{D}: the vine running from the clear pot above into the bucket', False), (2, f'{D}: new leaf', False), (1, f'{D}: the clear pot above: bare vines', False)])
update('P-066', 'New photos: it is a rooted runner of the plant above (batch 9)',
    id_confidence=65, container='Clear plastic pot on the rack; a vine from it has rooted in the blue 5-gallon bucket below',
    id_basis="Velvety, bronze-olive leaves with pink edges, red stalks and pink sheaths, which is how young micans leaves look. The photos show a long vine running from a clear pot on the rack down into the blue bucket, where it has rooted and put out these leaves.",
    health_rating='Fair', health_summary='The part in the bucket is growing well; the plant in the clear pot above is leggy with bare vines and several dried leaves.',
    health_observations=L('Healthy velvety new leaves in the bucket', 'Bare, leggy vines and dried leaves in the clear pot above'),
    health_steps=L('Pin more vine nodes onto the bucket mix so they root too.', 'Trim the bare vines in the clear pot and root the cuttings.', 'Bring both inside before nights reach 55°F.'))

# ---------------------------------------------------------------- requests
R = [
 ('p014-three-aloes', 'P-014', 'check', "P-014 is now the biggest aloe (black pot with white gravel). The other two have new pages: the one in the teal pot, and the one in the black pot behind the prickly pear pad. Print labels for the two new pages (Labels page) and put each on its pot."),
 ('p016-speckled', 'P-016', 'check', "The speckled rosette in this pot now has its own page. If you want to keep them apart, it can go in its own small pot with gritty mix."),
 ('p025-tag-text', 'P-025', 'photo', "A close photo of the hand-written tag in this pot (only part of it showed), to settle which begonia it is."),
 ('p036-taste', 'P-036', 'check', "Taste test: tear a leaf, touch it to your tongue and spit it out. Is it very sweet? (Stevia is.)"),
 ('p042-base', 'P-042', 'check', "Press the yellow lowest leaf near its base: is it firm, or soft and smelly?"),
 ('p053-undersides', 'P-053', 'check', "Look under a speckled leaf: are the black specks tiny insects (they move when nudged) or just dots?"),
 ('p055-wipe', 'P-055', 'check', "Wipe one white-speckled leaf with a damp cloth: do the specks come off?"),
]
requests_add = []
for key, code, kind, text in R:
    requests_add.append({'key': key, 'code': code, 'kind': kind, 'text': text, 'photos': [first_photo(code)]})
requests_done = ['p-029-pot-tag', 'p-030-pot-tag', 'p-039-pot-tag', 'p-055-pot-tag', 'p-056-tag-closeup', 'p-061-tag-closeup']

batch = {'id': 'batch9', 'created': '2026-10-22', 'author': "Claude (batch 9, Ethan's October 21 photos)",
         'plants': new_plants, 'existing_photos': existing_photos, 'updates': updates, 'archive': archive,
         'to_photograph_done': [], 'to_photograph_add': [{'label': 'Fuzzy pale-green-leaved plant', 'note': "Seen beside the boobie cactus (P-044) in an October photo: thick, hairy, pale-green leaves in a black pot. If you still have it, a photo would give it its own page."}],
         'requests_add': requests_add, 'requests_done': requests_done}
json.dump(batch, open(OUT + '/batches/batch9.json', 'w'), indent=1, ensure_ascii=False)
print(len(new_plants), 'new plants,', len(updates), 'updates,', len(existing_photos), 'photos,', len(requests_add), 'requests')
