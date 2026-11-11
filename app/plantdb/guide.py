"""Propagation and breeding guide (1.57.0). The guide's words (how each way of making new plants works, how breeding works, how to keep
a mother plant) are written in static/js/guide.js, so the page works offline like the rest of the app's pages. The one thing it needs
from the server is which of your plants each method suits, and that is already in the record: each plant's own "Propagation" lines
(plants.propagation, one method per line) and the methods in its species' uses-and-partners facts (species_facts). This lists them
for every active plant; the page matches the words to its sections. Nothing is stored and nothing here changes data."""
from .core import *   # noqa: F401,F403
from .speciesfacts import facts_row

ORDER = 60            # imports from speciesfacts (50), so after it

GUIDE_LINES_MAX = 12  # lines kept per plant
GUIDE_LINE_LEN = 300

def guide_lines(propagation, facts_json, kind='plant'):
    """The propagation notes for one plant, as short lines: its own field first, then its species' methods that are not already there.
    A fungus's facts are left out: the guide is about plants, and a fungus's growing notes are not its business."""
    out = [re.sub(r'\s+', ' ', x).strip()[:GUIDE_LINE_LEN] for x in str(propagation or '').splitlines() if x.strip()]
    if kind != 'fungus':
        try: d = json.loads(facts_json or '{}')
        except ValueError: d = {}
        for x in (d.get('propagation') or []) if isinstance(d, dict) else []:
            m = re.sub(r'\s+', ' ', str(x.get('method') or '') if isinstance(x, dict) else '').strip()[:GUIDE_LINE_LEN]
            if m and not any(m.lower() in l.lower() for l in out): out.append(m)
    return out[:GUIDE_LINES_MAX]

@app.route('/api/guide/plants')
def guide_plants():
    """[{code, name, lines}] for each active plant that has any propagation note (viewers may read it)."""
    c = db()
    out = []
    for r in c.execute("SELECT code, common_name, scientific_name, propagation FROM plants WHERE status='active' ORDER BY code").fetchall():
        f = facts_row(c, r['scientific_name'], r['code'])
        lines = guide_lines(r['propagation'], f['data'] if f else '', f['kind'] if f else 'plant')
        if lines: out.append({'code': r['code'], 'name': r['common_name'], 'lines': lines})
    return jsonify(plants=out)
