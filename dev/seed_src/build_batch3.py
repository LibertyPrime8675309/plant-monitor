import os as _os
REPO = _os.path.abspath(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', '..'))  # repository root
import json
OUT = REPO + '/app/seed/batches'
b2 = json.load(open(OUT + '/batch2.json'))
old = [x for x in b2['plants'] if x['common_name'] == 'Water hyacinth'][0]
# batch 2 numbered the new plants P-041..P-066 in order, so the hyacinth is the 10th: P-050 (guards below protect against a shifted code)
code = 'P-%03d' % (40 + 1 + b2['plants'].index(old))
new = {
 'winter_plan': 'Move indoors',
 'winter_summary': "Frost-tender and normally lost to the first freeze. You've confirmed keeping it is fine, so bring it in before nights fall under 45 F if you want to try to overwinter it.",
 'winter_triggers': 'Move indoors before the first night under 45 F; frost kills it around 32 F.',
 'winter_steps': "Never pour the water or plants into a drain, ditch, creek or pond. Bag and bin dead plants, or let them dry out completely.\nMove it indoors before the first night under 45 F to a warm bright window (65-75 F) with a grow light.\nIf it dies back indoors, remove the dead stalks so the water does not turn foul.",
 'health_steps': "Remove brown stalks, change to fresh water and move it into full sun\nIf it has no roots, it is unlikely to recover",
 'notes': "Owner confirmed on Oct 19, 2026 that keeping it is fine. For reference, Texas Parks and Wildlife lists water hyacinth among harmful or potentially harmful exotic aquatic plants and regulates possessing and transporting it, so never release it or its water into a pond, creek or drain. Source: https://tpwd.texas.gov/regulations/outdoor-annual/fishing/general-rules-regulations/possession-and-transport-of-exotic-aquatic-species",
}
batch = {'id': 'batch3', 'created': '2026-10-19', 'author': 'Claude (batch 3, from owner reply)',
         'plants': [], 'existing_photos': [],
         'updates': [{'code': code, 'note': 'Owner confirmed keeping the water hyacinth is fine; winter plan updated',
                      'set': {f: [old[f], v] for f, v in new.items()}}],
         'to_photograph_done': [], 'to_photograph_add': []}
json.dump(batch, open(OUT + '/batch3.json', 'w'), indent=1, ensure_ascii=False)
print(code)
