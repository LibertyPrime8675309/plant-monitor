import os as _os
REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))  # repository root
"""Batch 8: P-034 re-identified from Ethan's close-up photos (2026-10-21) as a peace lily recovering from near total leaf loss."""
import json, sqlite3, sys
from PIL import Image, ImageOps
RAW = REPO + '/dev/photos-raw/raw8'; OUT = REPO + '/app/seed'
DB = sys.argv[1] if len(sys.argv) > 1 else '/tmp/ui9/plants.db'
for k in ('b8_01', 'b8_02'):
    im = ImageOps.exif_transpose(Image.open(f'{RAW}/{k}.jpg')).convert('RGB'); im.thumbnail((1400, 1400))
    im.save(f'{OUT}/photos/img_{k}.jpg', 'JPEG', quality=82, optimize=True)

NEW = {
 'common_name': 'Peace lily (recovering, brown pot)',
 'scientific_name': 'Spathiphyllum sp. (probable)',
 'aliases': 'Spath; cultivar unknown',
 'plant_type': 'Tropical foliage (aroid)',
 'id_confidence': 70,
 'id_basis': "From the October 21 close-ups. The new leaf is glossy, lance-shaped with a pointed tip and a clear midrib, and has a small swollen joint (a geniculum) where the blade meets the stalk, which peace lilies have. The leaf stalks are sheathing and come straight up from the soil in a clump of several crowns, with papery brown sheaths around the new shoots. The dead leaves shrivelled lengthwise into narrow tan strips, which is how peace lily leaves dry out; that is why they looked strappy before. Several green shoots are coming up from the base, so the roots are alive.",
 'id_alternatives': 'Anthurium (also has a joint below the leaf and papery sheaths, but its leaves are usually heart-shaped)\nAglaonema (Chinese evergreen; leaves come from a short stem rather than a clump of crowns)',
 'id_improve': 'The next two or three leaves as they open (a peace lily leaf stays lance-shaped and glossy)\nA flower: a white hooded spathe around a cream spike confirms a peace lily\nThe pot tag, if there is one',
 'temp_ideal_low': 65, 'temp_ideal_high': 85, 'temp_damage_below': 50, 'temp_lethal_below': 35,
 'temp_notes': 'Peace lilies sulk below 55°F and leaves are damaged below about 45-50°F. Keep it above 60°F while it regrows. Heat above 90°F is fine in shade if it stays watered.',
 'humidity_low': 40, 'humidity_high': 70,
 'humidity_notes': 'Prefers 50% or more but grows well in normal indoor air of 40%. Very dry air gives brown leaf tips.',
 'light_summary': 'Bright indirect light; tolerates shade. No direct afternoon sun.',
 'light_hours': '8-12 hours of indirect light',
 'light_notes': 'An east window or a few feet back from a south or west window. Direct sun scorches the leaves; deep shade means few or no flowers.',
 'winter_summary': 'Bring it inside before nights reach 50°F. Indoors it can keep growing in a warm, bright room.',
 'health_rating': 'Poor',
 'health_summary': 'Recovering. Almost all the old leaves are dead, but one healthy new leaf has opened and several green shoots are coming up from the crowns.',
 'health_observations': 'One glossy, healthy new leaf\nSeveral green shoots emerging from the base (the crowns are alive)\nOld leaves dried to tan strips, some with dark streaks\nPapery brown sheaths around the new growth (normal)',
 'health_steps': 'Cut the dead leaves off near the soil with clean scissors. Leave the papery sheaths that wrap the new shoots.\nWater when the top inch of mix feels dry, then empty the saucer. Do not keep it soggy while it has so few leaves.\nKeep it warm (above 60°F) and in bright, indirect light.\nNo fertilizer until it has three or four new leaves, then half strength.\nDo not repot until it is growing well; then move it to fresh mix only one size up.',
 'water_notes': 'Water when the top inch (2-3 cm) of mix is dry. A peace lily droops clearly when thirsty and perks up within hours of watering, but do not wait for that every time. Empty the saucer. With few leaves it uses little water, so check before watering.',
 'soil_medium': 'Rich, moisture-holding but well-draining mix: about 60% potting soil, 20% perlite and 20% orchid bark or coir. Drainage holes are essential.',
 'fertilizer': 'Balanced liquid, such as 20-20-20, at quarter to half strength',
 'nutrients': 'Feed every 6 weeks from April to September at half strength, only once it is growing again. Peace lilies are light feeders; too much fertilizer burns the leaf tips.',
 'par_low': 50, 'par_high': 250, 'dli_low': 3, 'dli_high': 8, 'soil_moisture_low': 40, 'soil_moisture_high': 65,
 'fert_from_month': 4, 'fert_to_month': 9, 'fert_every_days': 42,
}
c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
r = c.execute("SELECT * FROM plants WHERE code='P-034'").fetchone()
assert r['common_name'].startswith('Unidentified: dying strappy')
s = {f: [r[f], v] for f, v in NEW.items() if r[f] != v}
batch = {'id': 'batch8', 'created': '2026-10-21', 'author': 'Claude (batch 8, P-034 close-ups)', 'plants': [],
 'existing_photos': [
  {'code': 'P-034', 'file': 'img_b8_01.jpg', 'caption': 'October 21: the new glossy leaf, with the joint below the blade', 'primary': True, 'source': 'b8_01'},
  {'code': 'P-034', 'file': 'img_b8_02.jpg', 'caption': 'October 21: the base, with new shoots coming up between the dead leaves', 'primary': False, 'source': 'b8_02'}],
 'updates': [{'code': 'P-034', 'name': r['common_name'], 'photos': ['img_1000021197.jpg'], 'note': 'Identified as a peace lily from close-up photos (batch 8)', 'set': s}],
 'to_photograph_done': [], 'to_photograph_add': []}
json.dump(batch, open(OUT + '/batches/batch8.json', 'w'), indent=1, ensure_ascii=False)
print(len(s), 'fields')
