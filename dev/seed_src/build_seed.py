import os as _os
REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))  # repository root
import json, os, sys, glob
sys.path.insert(0, os.path.dirname(__file__))
from PIL import Image, ImageOps
from plants_a import A
from plants_b import B

RAW = REPO + '/dev/photos-raw/raw'
OUT = REPO + '/app/seed'
PH = OUT + '/photos'

def src_path(key):
    if key.startswith('heif'):
        return f'{RAW}/src_330ae945-4087-4f0c-a696-cbe01fd9cba9-1_all_{key[4:]}.heif.jpg'
    return f'{RAW}/src_{key}.jpg'

def out_name(key): return f'img_{key}.jpg'

used = set()
def convert(key):
    dst = f'{PH}/{out_name(key)}'
    if key in used: return
    im = ImageOps.exif_transpose(Image.open(src_path(key))).convert('RGB')   # re-encode: drops EXIF/GPS
    im.thumbnail((1400, 1400))
    im.save(dst, 'JPEG', quality=82, optimize=True)
    used.add(key)

plants = []
for r in A + B:
    d = {
        'code': r['code'], 'common_name': r['common'], 'scientific_name': r['sci'], 'aliases': r['aliases'],
        'plant_type': r['ptype'], 'location': r['loc'], 'container': r['cont'],
        'id_confidence': r['conf'], 'id_basis': r['basis'],
        'id_alternatives': '\n'.join(r['alts']), 'id_improve': '\n'.join(r['improve']),
        'temp_ideal_low': r['temp'][0], 'temp_ideal_high': r['temp'][1], 'temp_damage_below': r['temp'][2],
        'temp_lethal_below': r['temp'][3], 'temp_notes': r['temp'][4],
        'humidity_low': r['hum'][0], 'humidity_high': r['hum'][1], 'humidity_notes': r['hum'][2],
        'light_summary': r['light'][0], 'light_hours': r['light'][1], 'light_notes': r['light'][2],
        'winter_plan': r['winter'][0], 'winter_summary': r['winter'][1], 'winter_triggers': r['winter'][2],
        'winter_steps': '\n'.join(r['winter'][3]), 'indoor_setup': '\n'.join(r['winter'][4]),
        'health_rating': r['health'][0], 'health_summary': r['health'][1],
        'health_observations': '\n'.join(r['health'][2]), 'health_steps': '\n'.join(r['health'][3]),
        'notes': r['notes'],
        'photos': [{'file': out_name(k), 'caption': cap, 'primary': i == 0, 'source': k} for i, (k, cap) in enumerate(r['photos'])],
    }
    for k, _ in r['photos']: convert(k)
    plants.append(d)

other_photos = [
  ('1000021066', 'Pergola with string lights and shade cloth at night (garden overview)', 'area'),
  ('1000021067', 'Covered walkway and potted plants at night (garden overview)', 'area'),
  ('heif8617', 'Pallet shelf on the covered porch, daytime overview', 'area'),
  ('heif8618', 'Pergola with shade cloth, seen from the porch', 'area'),
  ('heif8619', 'Yard overview: potted plants, palms, fiddle-leaf fig, blue buckets', 'area'),
  ('1000021184', 'Black wasp-like insect on a pot, observation', 'other'),
  ('1000021185', 'Same insect, second photo', 'other'),
]
unassigned = []
for k, cap, kind in other_photos:
    convert(k)
    unassigned.append({'file': out_name(k), 'caption': cap, 'kind': kind, 'source': k})

to_photograph = [
 ('Money tree / Pachira or umbrella tree (palmate leaves)', 'Foreground of the porch shelf photo; also the big oblong leaves behind P-009.'),
 ('Monstera (large green leaves)', 'Left side of the yard overview.'),
 ('Purple heart (Tradescantia pallida)', 'Foreground of the adenium seedlings photo (P-021).'),
 ('Water hyacinth in the blue bucket', 'Yard overview, front blue bucket (LOWE\'S).'),
 ('Aeonium with dark rosettes (probably Zwartkop)', 'Dark pot behind P-012.'),
 ('Other palms in the yard (three more)', 'Yard overview; photograph each one with its tag.'),
 ('Strappy plants in black pots on the front table', 'Iris, agave, lily or similar (porch/yard overview).'),
 ('Second rose in the red pot', 'Behind P-022.'),
 ('Burpee-tagged pot (vegetable or herb)', 'Behind P-012 and P-010.'),
 ('Hanging planter on the teal shelf', 'Right side of the yard overview.'),
 ('Large green-leaf plant with a white clip', 'Bottom left of the Aglaonema photo (P-028).'),
 ('Any plants not yet photographed', 'Use the app: add a new plant and upload photos.'),
]

reference = {
  'climate': [
    {'month':'Oct','low':57,'high':82,'rh':68,'rh_pm':50,'sun_hours':7.5,'daylight':11.5,'freeze_nights':0.5},
    {'month':'Nov','low':47,'high':70,'rh':71,'rh_pm':53,'sun_hours':5.8,'daylight':10.7,'freeze_nights':1},
    {'month':'Dec','low':39,'high':62,'rh':72,'rh_pm':55,'sun_hours':4.5,'daylight':10.3,'freeze_nights':5},
    {'month':'Jan','low':38,'high':61,'rh':72,'rh_pm':55,'sun_hours':5.0,'daylight':10.4,'freeze_nights':8},
    {'month':'Feb','low':41,'high':65,'rh':72,'rh_pm':51,'sun_hours':5.7,'daylight':11.1,'freeze_nights':4},
    {'month':'Mar','low':48,'high':72,'rh':71,'rh_pm':48,'sun_hours':6.7,'daylight':12.0,'freeze_nights':1},
  ],
  'notes': [
    'Temperatures are 1991-2020 averages for Round Rock (PlantMaps). Humidity, sunshine and freezing-night counts are Austin-area climatology (NASA POWER via climate-zone.com; climates.com sunshine guide). Austin is about 20 miles south, so Round Rock can be a degree or two cooler on clear nights.',
    'Frost dates: Almanac (30% probability, 1991-2020) gives first fall frost ~Nov 13 and last spring frost ~Mar 19. PlantMaps gives average first frost Nov 21-30 and last frost Feb 21-Mar 10. Treat Nov 13 as the earliest risk and Mar 19 as the last.',
    'USDA zone 9a (20-25 F average annual minimum) on the 2023 map. Texas horticulturists recommend planning one zone colder: use 20 F as the design low. The January 2026 ice storm was forecast near 21 F in Austin.',
    'Outlook: NOAA CPC (Oct 8-15, 2026) expects a strong-to-very-strong El Nino through winter. For Central Texas that usually means cool, damp, cloudy stretches rather than a uniformly cold winter. A wet winter is not guaranteed.',
  ],
  'triggers': [
    {'temp':'~38 F, clear and calm', 'action':'Frost possible in low spots. Cover tender plants with frost cloth, or move them under the porch roof.'},
    {'temp':'32 F or below', 'action':'Move cold-sensitive pots under cover (garage or covered porch). Cover everything else with frost cloth to the ground.'},
    {'temp':'25 F or below, or a multi-day freeze', 'action':'Everything tender comes inside. Hardy plants get frost cloth and mulch.'},
  ],
  'playbook': [
    'Water the day before a freeze (moist soil holds heat) but do not water frozen soil.',
    'Use frost cloth or fabric, never plastic touching leaves. Drape to the ground over a frame, weigh down the edges, and remove when above 35 F.',
    'Container plants are the most at risk: group pots against the south/east wall under the roof, pile mulch around the pots, and wrap pots with burlap if needed.',
    'Do not fertilize with nitrogen in winter. Do not prune frost-browned growth until after the last frost (mid-March).',
    'Shut off drip lines and drain them before a hard freeze; cover spigots and unhook hoses.',
    'Remove dense shade cloth in winter so plants get full light, and reuse the pergola frame to hold frost cloth.',
    'Moving plants in: rinse leaves, inspect for pests, quarantine 2 weeks, put by the brightest window or grow light, expect some leaf drop, do not repot or fertilize.',
  ],
  'sources': [
    ['PlantMaps Round Rock climate','https://plantmaps.com/en/clim/f/us/texas/round-rock/climate-data'],
    ['Old Farmer\'s Almanac frost dates','https://cdn.almanac.com/gardening/frostdates/TX/Round+Rock'],
    ['NOAA CPC ENSO discussion','https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml'],
    ['Austin sunshine guide','https://www.climates.com/USA/PDF/TX003USA.pdf'],
    ['Neil Sperry on hardiness zones','https://neilsperry.com/2026/02/hardiness-zone-map-needs-revision-again/'],
    ['AgriLife: winterizing landscapes','https://agrilifetoday.tamu.edu/2012/12/12/winterizing-landscapes/'],
  ],
}

seed = {'created': '2026-10-19', 'author': 'Claude (initial analysis from photos)', 'plants': plants,
        'unassigned_photos': unassigned, 'to_photograph': [{'label': a, 'note': b} for a, b in to_photograph],
        'reference': reference}
json.dump(seed, open(OUT + '/seed.json', 'w'), indent=1, ensure_ascii=False)
print(len(plants), 'plants;', len(used), 'photos;', sum(os.path.getsize(f) for f in glob.glob(PH + '/*')) // 1024, 'KB')
