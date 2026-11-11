"""Each species' uses, partners, deterrents, propagation and breeding (the species_facts blob, written by Claude on request),
and facts_keys(), the species key the facts table uses too. Split out of library.py in 1.57.0 (review item 25)."""
from .core import *   # noqa: F401,F403
# ---------- 1.27.0: uses, partners, deterrents, propagation and breeding, for each species ----------
FACTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS species_facts(
  key TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'plant', data TEXT NOT NULL,
  origin TEXT NOT NULL, written_by TEXT, written_at TEXT);
CREATE TABLE IF NOT EXISTS facts_link(code TEXT PRIMARY KEY, key TEXT NOT NULL);
"""
FACTS_EVIDENCE = ('Tested', 'Traditional', 'Same needs', 'Different needs')
FACTS_COMPOST = ('Good', 'Fine in small amounts', 'Poor', 'Keep it out')
# a fungus's uses never include eating it or taking it as medicine (the app never says a wild mushroom is edible or safe)
FACTS_FUNGUS_NO = re.compile(r'edib|\beat|eaten|cook|culinar|food|meal|tea\b|tincture|medicin|supplement|extract|psychoactiv|hallucin|consum|forag|recipe|flavou?r|tast', re.I)

def facts_keys(sci):
    """The keys a species' facts can be filed under, most exact first: 'Aloe vera (spotted form)' -> ['aloe vera', 'aloe'],
    'xGraptosedum 'Francesco Baldi'' -> ['graptosedum'], "Philodendron 'Birkin'" -> ['philodendron']."""
    s = re.sub(r'^\s*[x\u00d7]\s*(?=[A-Z])', '', (sci or '').strip())
    m = re.match(r'^([A-Z][a-z]+)(?:\s+([a-z][a-z\-]+))?', s)
    if not m: return []
    g, sp = m.group(1).lower(), m.group(2)
    return ([g + ' ' + sp] if sp and sp not in ('sp', 'spp', 'x', 'cultivar', 'type', 'hybrid', 'var', 'or', 'cf') else []) + [g]

def facts_clean(a, kind='plant'):
    """Keeps only the expected keys, at sensible lengths (for batches and for what Claude writes)."""
    a = a if isinstance(a, dict) else {}
    t = lambda v, n: re.sub(r'\s+', ' ', str(v or '')).strip()[:n]
    ev = lambda v: v if v in FACTS_EVIDENCE else 'Traditional'
    def lst(k, fields, n):
        out = []
        for x in (a.get(k) or [])[:n]:
            if isinstance(x, dict):
                y = {f: (ev(x.get(f)) if f == 'evidence' else t(x.get(f), m)) for f, m in fields}
                if any(v for f, v in y.items() if f != 'evidence'): out.append(y)
        return out
    d = {'summary': t(a.get('summary'), 400),
         'uses': lst('uses', (('kind', 40), ('text', 400), ('caution', 300)), 8),
         'partners_good': lst('partners_good', (('name', 80), ('sci', 80), ('why', 300), ('evidence', 0)), 8),
         'partners_bad': lst('partners_bad', (('name', 80), ('sci', 80), ('why', 300), ('evidence', 0)), 8),
         'deters': lst('deters', (('what', 80), ('how', 300), ('evidence', 0)), 6),
         'attracts': lst('attracts', (('what', 80), ('why', 300)), 6),
         'propagation': lst('propagation', (('method', 60), ('when', 160), ('how', 500)), 6)}
    cp = a.get('compost') if isinstance(a.get('compost'), dict) else {}
    d['compost'] = {'verdict': cp.get('verdict') if cp.get('verdict') in FACTS_COMPOST else '', 'why': t(cp.get('why'), 300)}
    br = a.get('breeding') if isinstance(a.get('breeding'), dict) else {}
    d['breeding'] = {'text': t(br.get('text'), 700), 'patent': t(br.get('patent'), 300), 'same_genus': br.get('same_genus') is not False,
                     'cross_genera': [t(g, 40) for g in (br.get('cross_genera') or [])[:6] if re.fullmatch(r'[A-Za-z\u00d7 ]{3,40}', str(g or ''))]}
    d['sources'] = [{'title': t(x.get('title'), 120), 'url': t(x.get('url'), 300)} for x in (a.get('sources') or [])[:6]
                    if isinstance(x, dict) and str(x.get('url', '')).startswith('https://')]
    if kind == 'fungus':
        d['uses'] = [u for u in d['uses'] if not FACTS_FUNGUS_NO.search(u['kind'] + ' ' + u['text'] + ' ' + u['caution'])]
        d['summary'] = '' if FACTS_FUNGUS_NO.search(d['summary']) else d['summary']
    return d

def facts_row(c, sci, code=None):
    if code:
        k = c.execute('SELECT key FROM facts_link WHERE code=?', (code,)).fetchone()
        if k:
            r = c.execute('SELECT * FROM species_facts WHERE key=?', (k[0],)).fetchone()
            if r: return r
    for k in facts_keys(sci):
        r = c.execute('SELECT * FROM species_facts WHERE key=?', (k,)).fetchone()
        if r: return r
    return None

def facts_links(c, d, sci, self_code=None):
    """Marks which partner plants you have, and which of your plants could be crossed with this one."""
    mine = []
    for code, name, s in c.execute("SELECT code, common_name, scientific_name FROM plants WHERE status='active' ORDER BY code"):
        lk = c.execute('SELECT key FROM facts_link WHERE code=?', (code,)).fetchone()
        mine.append((code, name, ([lk[0]] if lk else []) + facts_keys(s)))
    def have(target):
        t = (target or '').lower().strip()
        t = re.sub(r'^[x\u00d7]\s*', '', t)
        return [{'code': code, 'name': name} for code, name, ks in mine if code != self_code and t and (t in ks or any(k.startswith(t + ' ') for k in ks))]
    for p in d.get('partners_good', []) + d.get('partners_bad', []):
        p['yours'] = have(p['sci']) if p.get('sci') else []
    ks = facts_keys(sci)
    if self_code:
        lk = c.execute('SELECT key FROM facts_link WHERE code=?', (self_code,)).fetchone()
        if lk: ks = [lk[0]] + ks
    sp = next((k for k in ks if ' ' in k), None)
    br = d.get('breeding', {})
    genera = ({k for k in ks if ' ' not in k} if br.get('same_genus', True) else set()) | {g.lower().replace('\u00d7', '').strip() for g in br.get('cross_genera', [])}
    same, other = [], []
    for code, name, pks in mine:
        if code == self_code: continue
        if sp and sp in pks: same.append({'code': code, 'name': name})
        elif genera & {k for k in pks if ' ' not in k}: other.append({'code': code, 'name': name})
    d['cross_same'], d['cross_other'] = same, other
    return d

def facts_out(c, sci, code=None, kind='plant'):
    r = facts_row(c, sci, code)
    if not r: return None
    d = facts_links(c, json.loads(r['data']), sci, code)
    d.update(key=r['key'], name=r['name'], kind=r['kind'], origin=r['origin'], written_by=r['written_by'], written_at=r['written_at'])
    return d

@app.route('/api/facts', methods=['GET', 'POST'])
def species_facts():
    """GET ?name=<scientific name>[&code=P-001]: what is kept for that species (or its genus), with your plants linked.
    POST {name, common_name, kind}: Claude writes them with the owner's key, and they are kept."""
    c = db()
    if request.method == 'GET':
        a = request.args
        code = a.get('code') or None
        sci = a.get('name') or ''
        if code and not sci:
            r = c.execute('SELECT scientific_name FROM plants WHERE code=?', (code,)).fetchone()
            sci = r[0] if r else ''
        return jsonify(facts=facts_out(c, sci, code), keys=facts_keys(sci), can_write=bool(setting(c, 'claude_key', '')))
    b = request.get_json(silent=True) or {}
    name, kind = str(b.get('name') or '').strip()[:120], 'fungus' if b.get('kind') == 'fungus' else 'plant'
    ks = facts_keys(name)
    if not ks: abort(400, 'This needs a scientific name, such as "Aloe vera", to look up.')
    old = c.execute('SELECT origin FROM species_facts WHERE key=?', (ks[0],)).fetchone()
    if old and old['origin'] == 'researched': abort(409, 'These were researched for your plants and are kept as they are.')
    key = setting(c, 'claude_key', '')
    if not key: abort(400, 'These are written by Claude. The owner can save an Anthropic API key on the Identify page, under "Second opinions".')
    L = home_place(c)
    ask = FACTS_ASK.format(name=name, common=f' ({b["common_name"]})' if b.get('common_name') else '', place=L['name'],
                           zone=home_zone(c), extra=FACTS_ASK_FUNGUS if kind == 'fungus' else FACTS_ASK_PLANT)
    body = json.dumps({'model': CLAUDE_MODEL, 'max_tokens': 3000, 'messages': [{'role': 'user', 'content': ask}]}).encode()
    st, j = outside_call(CLAUDE_URL, body, {'Content-Type': 'application/json', 'x-api-key': key, 'anthropic-version': '2023-06-01'}, timeout=150)
    if st in (401, 403): abort(502, 'Anthropic refused the key. Check it at console.anthropic.com and save it again.')
    if st in (429, 529): abort(502, 'Claude is busy or the key has reached its limit. Try again in a minute.')
    if st != 200: abort(502, 'Could not reach Claude. Check the internet connection and try again.')
    text = ''.join(x.get('text', '') for x in j.get('content', []) if x.get('type') == 'text')
    m = re.search(r'\{.*\}', text, re.S)
    try: a = json.loads(m.group(0)) if m else {}
    except ValueError: a = {}
    d = facts_clean(a, kind)
    if not (d['uses'] or d['propagation'] or d['partners_good']): abort(502, 'Claude did not give an answer this could read. Try again.')
    c.execute('INSERT OR REPLACE INTO species_facts(key,name,kind,data,origin,written_by,written_at) VALUES(?,?,?,?,?,?,?)',
              (ks[0], name, kind, json.dumps(d), 'claude', editor(), now()))
    audit_only(c, 'library', 'uses and partners', None, name, editor(), f'Uses, partners and propagation for {name} written by Claude'); c.commit()
    return jsonify(facts=facts_out(c, name, None, kind))

FACTS_ASK = """For the species {name}{common}, grown by a home gardener in {place} (USDA zone {zone}), answer with ONE JSON object only, no other
text. Keys:
"summary": one sentence on what it is most useful for.
"uses": a list (0 to 6) of {{"kind": a short category such as "Skin and first aid", "Food for wildlife", "Dye", "Crafts", "Erosion control",
  "Cut flowers", "Ornamental", "Soil", "text": one or two sentences, "caution": safety notes, or ""}}. Traditional or folk uses must say so.
{extra}
"compost": {{"verdict": one of "Good", "Fine in small amounts", "Poor", "Keep it out", "why": one sentence}}.
"partners_good" and "partners_bad": lists (0 to 6) of {{"name": common name, "sci": its genus or "Genus species", "why": one sentence,
  "evidence": "Tested" (shown in trials), "Traditional" (gardeners' lore, not shown), "Same needs" (same light, water and soil, for pots
  and beds) or "Different needs" (for partners_bad: needs very different light, water or soil)}}.
"deters": a list (0 to 4) of {{"what": the pest or animal, "how": one sentence, "evidence": as above}}. Only real, specific claims.
"attracts": a list (0 to 4) of {{"what": pollinators, birds or beneficial insects, "why": one sentence}}.
"propagation": a list (1 to 4) of {{"method": such as "Stem cuttings", "Division", "Seed", "Spore print", "when": the best time in {place},
  "how": two or three practical sentences}}.
"breeding": {{"text": how to cross it with others and what to expect (or that it does not cross), "cross_genera": genera it is known to
  cross with besides its own (a list, often empty), "same_genus": false if it cannot practically be crossed with others of its genus at home,
  "patent": a note if named varieties are commonly patented, or ""}}.
"sources": a list (0 to 4) of {{"title", "url"}}: only well-known reference pages you are sure exist (extension services, botanic gardens).
Use plain words. If you do not know the species well, keep each list short and general, and say so in "summary"."""
FACTS_ASK_PLANT = "Medicinal or skin uses are folk or traditional information, never advice: put any toxicity to people or pets in \"caution\"."
FACTS_ASK_FUNGUS = """This is a FUNGUS. Do not say or suggest that it is edible, safe, tasty, medicinal or psychoactive, and do not list any use
that means eating it, drinking it or taking it in any form. Its uses are what it does: what it breaks down, which trees or plants it
partners with (mycorrhizal), what it tells you about the soil, compost, spore prints, dye from its color, and how it is cultivated."""
