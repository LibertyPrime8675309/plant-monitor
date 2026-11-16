"""1.33.0: one search for everything: plants, groups, stores, mushroom finds, rooms and spots, and the species in the library,
for the search window in the top bar (the / key). Pages are matched on the device, from the list in js/core.js."""
from .core import *   # noqa: F401,F403
from .fuzzy import fz_match, fz_nearest

def _like(q): return '%' + q.replace('%', '').replace('_', '') + '%'

@app.route('/api/search')
def search_api():
    c = db(); q = request.args.get('q', '').strip()[:80]
    if len(q) < 2: return jsonify(q=q, groups=[])
    L, out = _like(q), []
    rows = c.execute("""SELECT code, common_name, scientific_name, aliases, location, status FROM plants WHERE code LIKE ? OR common_name LIKE ? OR scientific_name LIKE ?
                        OR aliases LIKE ? OR location LIKE ? OR notes LIKE ? ORDER BY status='archived', CASE WHEN code LIKE ? OR common_name LIKE ? THEN 0 ELSE 1 END, code LIMIT 12""",
                     (L, L, L, L, L, L, L, L)).fetchall()
    close_texts = []
    if not rows and len(q) >= 5:                   # 1.58.0: nothing spelt that way: close spellings of the names
        allp = c.execute("SELECT code, common_name, scientific_name, aliases, location, status FROM plants ORDER BY status='archived', code").fetchall()
        rows = [r for r in allp if fz_match(' '.join(x or '' for x in (r['common_name'], r['scientific_name'], r['aliases'])), q)][:12]
        close_texts += [' '.join(x or '' for x in (r['common_name'], r['scientific_name'], r['aliases'])) for r in rows]
    out.append({'kind': 'plants', 'word': 'Plants', 'items': [{'title': f"{r['code']} {r['common_name']}", 'sub': (r['scientific_name'] or '') + (f" · {r['location']}" if r['location'] else '') + (' · archived' if r['status'] == 'archived' else ''),
                                                             'href': '#/plant/' + r['code']} for r in rows]})
    rows = c.execute('SELECT id, name, kind FROM plant_groups WHERE name LIKE ? ORDER BY name LIMIT 6', (L,)).fetchall()
    if not rows and len(q) >= 5:
        rows = [r for r in c.execute('SELECT id, name, kind FROM plant_groups ORDER BY name').fetchall() if fz_match(r['name'], q)][:6]; close_texts += [r['name'] for r in rows]
    out.append({'kind': 'groups', 'word': 'Groups', 'items': [{'title': r['name'], 'sub': 'smart group' if r['kind'] == 'smart' else 'group', 'href': f'#/group/{r["id"]}'} for r in rows]})
    rows = c.execute("SELECT a.id, a.name, a.side, h.name home FROM areas a LEFT JOIN locations h ON h.id=a.home_id WHERE a.name LIKE ? ORDER BY a.name LIMIT 6", (L,)).fetchall()
    sp = c.execute("SELECT s.id, s.name, a.name area FROM spots s JOIN areas a ON a.id=s.area_id WHERE s.name LIKE ? ORDER BY s.name LIMIT 6", (L,)).fetchall()
    out.append({'kind': 'where', 'word': 'Rooms and spots', 'items': [{'title': r['name'], 'sub': ('room' if r['side'] == 'in' else 'outdoor area') + (f' at {r["home"]}' if r['home'] else ''), 'href': '#/where'} for r in rows]
                + [{'title': r['name'], 'sub': f'spot in {r["area"]}', 'href': '#/where'} for r in sp]})
    rows = c.execute('SELECT key, name, local, address FROM shops WHERE name LIKE ? OR address LIKE ? ORDER BY name LIMIT 6', (L, L)).fetchall()
    out.append({'kind': 'stores', 'word': 'Stores', 'items': [{'title': r['name'], 'sub': r['address'] or ('store you can visit' if r['local'] else 'online store'), 'href': '#/store/' + r['key']} for r in rows]})
    rows = c.execute("SELECT code, name, scientific_name FROM fungi_finds WHERE code LIKE ? OR name LIKE ? OR scientific_name LIKE ? ORDER BY code LIMIT 6", (L, L, L)).fetchall()
    if not rows and len(q) >= 5:
        rows = [r for r in c.execute('SELECT code, name, scientific_name FROM fungi_finds ORDER BY code').fetchall() if fz_match(f"{r['name']} {r['scientific_name'] or ''}", q)][:6]
        close_texts += [f"{r['name']} {r['scientific_name'] or ''}" for r in rows]
    out.append({'kind': 'finds', 'word': 'Mushroom finds', 'items': [{'title': f"{r['code']} {r['name']}", 'sub': r['scientific_name'] or '', 'href': '#/fungi/' + r['code']} for r in rows]})
    rows = c.execute("SELECT name, common_name, kind FROM wishlist WHERE name LIKE ? OR common_name LIKE ? LIMIT 6", (L, L)).fetchall()
    if not rows and len(q) >= 5:
        rows = [r for r in c.execute('SELECT name, common_name, kind FROM wishlist').fetchall() if fz_match(f"{r['name']} {r['common_name'] or ''}", q)][:6]
        close_texts += [f"{r['name']} {r['common_name'] or ''}" for r in rows]
    out.append({'kind': 'shopping', 'word': 'Shopping and wishlist', 'items': [{'title': r['common_name'] or r['name'], 'sub': 'wishlist plant' if r['kind'] == 'plant' else SHOP_KIND_WORD.get(r['kind'], r['kind']), 'href': '#/shopping'} for r in rows]})
    species = []
    if len(q) >= 3:
        try:
            got = vision_call('/names?' + urllib.parse.urlencode({'q': q, 'scope': 'common', 'limit': 8}), timeout=4)
            for n in (got.get('names') or got.get('results') or [])[:8]:
                sci = n.get('scientific_name') or n.get('name') or ''
                species.append({'title': n.get('common_name') or sci, 'sub': sci if n.get('common_name') else 'species', 'href': '#/species/' + urllib.parse.quote(sci)})
        except Exception: pass
    out.append({'kind': 'species', 'word': 'Library', 'items': species})
    # 1.58.0: when any part was found by a close spelling, the nearest word, for "Did you mean ...?"
    close = fz_nearest(close_texts + [it['title'] + ' ' + it['sub'] for it in species], q) if close_texts or species else None
    return jsonify(q=q, groups=[g for g in out if g['items']], close=close)
