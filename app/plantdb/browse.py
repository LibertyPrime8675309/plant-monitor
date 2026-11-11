"""Prototype (proto/browse-risk): which of the plants are likely to be eaten by rabbits, rats, mice, deer and other browsers.
Ethan's plants are being eaten (November 2026). This gives each plant a rough risk, with the reason in words, from the plant's
genus (and a few species), so it works for every plant and for plants added later. It stores nothing: the table below is
gardeners' and extension-service knowledge, not a test, and says so. Nothing here suggests harming an animal: a plant is called
"toxic" only to say animals usually leave it alone."""
from .core import *   # noqa: F401,F403

RISKS = ['Low', 'Moderate', 'High']
RISK_WORD = {'Low': 'Low risk: usually left alone', 'Moderate': 'Some risk: eaten when other food is short, or when young',
             'High': 'High risk: a favourite', 'Unknown': 'Not known yet'}

OX = 'Calcium oxalate crystals burn the mouth, so animals usually leave it alone.'
# key (lowercase genus, or "genus species") -> (risk, why). Longer keys are tried first.
BROWSE = {
    'dieffenbachia': ('Low', OX), 'alocasia': ('Low', OX), 'philodendron': ('Low', OX), 'monstera': ('Low', OX),
    'aglaonema': ('Low', OX), 'spathiphyllum': ('Low', OX), 'syngonium': ('Low', OX), 'rhaphidophora': ('Low', OX),
    'scindapsus': ('Low', OX), 'epipremnum': ('Low', OX),
    'zamioculcas': ('Low', 'Contains oxalates and has tough, glossy leaves; rarely eaten.'),
    'aloe': ('Low', 'Bitter latex under the skin; rarely eaten.'), 'aloiampelos': ('Low', 'Bitter latex, like aloe; rarely eaten.'),
    'haworthiopsis': ('Low', 'Tough, gritty leaves with little to eat; usually skipped, though mice may chew young ones.'),
    'haworthia': ('Low', 'Tough leaves with little to eat; usually skipped.'),
    'euphorbia': ('Low', 'Milky latex that irritates the mouth, and spines on crown of thorns; a strong deterrent.'),
    'adenium': ('Low', 'The sap is poisonous, so animals avoid it.'),
    'myrtillocactus': ('Low', 'Spiny. Rodents sometimes gnaw the base of a cactus, so keep it off the ground.'),
    'opuntia': ('Moderate', 'Spines put most animals off, but rabbits, rats and deer chew the pads in dry spells (chewed pads were seen).'),
    'bougainvillea': ('Low', 'Thorny stems. New soft shoots are sometimes nibbled.'),
    'ficus lyrata': ('Low', 'Milky sap irritates the mouth, so it is rarely eaten.'),
    'ficus carica': ('Moderate', 'The fruit and young leaves are eaten by birds, deer and rabbits, though the sap puts some off.'),
    'ravenea': ('Low', 'Tough fronds; seedlings are softer and can be nibbled.'), 'dypsis': ('Low', 'Tough fronds; seedlings are softer and can be nibbled.'),
    'nephrolepis': ('Low', 'Ferns are usually left alone by rabbits and deer.'),
    'rosa': ('Moderate', 'Thorns help, but rabbits eat young canes and buds, and deer eat the flowers.'),
    'vitis': ('High', 'Leaves, shoots and fruit are eaten by rabbits, deer, birds and raccoons.'),
    'ipomoea batatas': ('High', 'Sweet potato leaves are eaten by rabbits, rodents and deer.'),
    'ipomoea': ('Moderate', 'Morning glory leaves are mildly toxic, but seedlings are nibbled.'),
    'caesalpinia': ('Moderate', 'Soft feathery leaves on a legume; the seeds are poisonous, the leaves are sometimes browsed.'),
    'erythrostemon': ('Moderate', 'Soft feathery leaves on a legume; the seeds are poisonous, the leaves are sometimes browsed.'),
    'moringa': ('High', 'The leaves are food for people and livestock, so rabbits and deer will eat them.'),
    'senna': ('Moderate', 'Tender compound leaves on a legume; young plants are browsed.'),
    'begonia': ('High', 'Soft leaves with no defence; feeding holes were seen on yours.'),
    'plectranthus': ('High', 'Coleus is soft and tasty; rabbits and rodents go for it.'),
    'goeppertia': ('High', 'Soft tropical leaves, not toxic (ASPCA lists calatheas as pet-safe).'),
    'calathea': ('High', 'Soft tropical leaves, not toxic (ASPCA lists calatheas as pet-safe).'),
    'cosmos': ('Moderate', 'Rabbits eat young plants and deer nibble flowers; older plants are left more.'),
    'hibiscus': ('High', 'Tender leaves and buds; a well-known rabbit and deer favourite.'),
    'portulacaria': ('High', 'Elephant bush is edible and juicy; many animals eat it (elephants do).'),
    'tradescantia': ('Moderate', 'The sap can irritate skin, but the stems are soft and fast-growing, and are chewed.'),
    'graptopetalum': ('Moderate', 'Juicy leaves: rats and mice chew succulents, most in dry spells.'),
    'graptosedum': ('Moderate', 'Juicy leaves: rats and mice chew succulents, most in dry spells.'),
    'aeonium': ('Moderate', 'Juicy leaves: rats, mice and rabbits chew succulents, most in dry spells.'),
    'echeveria': ('Moderate', 'Juicy leaves: rats and mice chew succulents, most in dry spells.'),
    'kalanchoe': ('Low', 'Mildly toxic; usually left alone.'),
    'sedum': ('Moderate', 'Juicy leaves: rats and mice chew succulents, most in dry spells.'),
    'cucurbita': ('High', 'Squash and gourd leaves and fruit are eaten by rabbits, rodents and deer.'),
    'cucurbitaceae': ('High', 'Squash, melon and gourd leaves and fruit are eaten by rabbits, rodents and deer (bite holes seen).'),
    'cucumis': ('High', 'Melon leaves and fruit are eaten by rabbits, rodents and deer.'),
    'phalaenopsis': ('Moderate', 'Mice and rats chew flower spikes and root tips, and slugs eat the leaves.'),
    'pachira': ('Moderate', 'Not toxic, but the leaves are tough. Young plants can be nibbled.'),
}
COMMON = [('squash', 'cucurbita'), ('gourd', 'cucurbita'), ('melon', 'cucurbita'), ('coleus', 'plectranthus'), ('hibiscus', 'hibiscus'),
          ('elephant bush', 'portulacaria'), ('purple heart', 'tradescantia'), ('begonia', 'begonia'), ('philodendron', 'philodendron'),
          ('aloe', 'aloe'), ('prickly pear', 'opuntia'), ('crown of thorns', 'euphorbia'), ('calathea', 'calathea'), ('arrowhead', 'syngonium'),
          ('dieffenbachia', 'dieffenbachia'), ('alocasia', 'alocasia'), ('fiddle', 'ficus lyrata'), ('rose', 'rosa')]

def browse_for(scientific, common=''):
    """(risk, why) for a plant from its scientific name (genus or species), else its common name; ('Unknown', '') when not known."""
    words = re.sub(r"[^a-z ]", ' ', str(scientific or '').lower().replace('×', ' ').replace(' x ', ' ')).split()
    words = [w for w in words if w not in ('sp', 'spp', 'cv', 'cultivar', 'possibly', 'probable', 'unconfirmed', 'or')]
    words = [w[1:] if w.startswith('x') and w[1:] in BROWSE else w for w in words]       # xGraptosedum: a hybrid genus
    for n in (2, 1):                                  # genus + species first, then genus; a leading "x" (hybrid) is dropped
        for i in range(0, max(1, len(words) - n + 1)):
            key = ' '.join(words[i:i + n])
            if key in BROWSE: return BROWSE[key]
    low = str(common or '').lower()
    for word, key in COMMON:
        if word in low: return BROWSE[key]
    return ('Unknown', '')

def browse_row(r):
    risk, why = browse_for(r['scientific_name'], r['common_name'])
    return {'code': r['code'], 'name': r['common_name'], 'sci': r['scientific_name'] or '', 'risk': risk, 'word': RISK_WORD[risk], 'why': why,
            'site': r['site'] or 'Outdoors'}

def browse_report(c, code=None):
    at, at_args = plants_at(c, location(c))
    if code: at, at_args = ' AND code=?', [code]
    rows = c.execute("SELECT * FROM plants WHERE status='active'" + at + ' ORDER BY code', at_args).fetchall()
    ps = []
    for r in rows:
        x = browse_row(r)
        x['photo'] = (c.execute('SELECT file FROM photos WHERE plant_id=? ORDER BY is_primary DESC,id LIMIT 1', (r['id'],)).fetchone() or [None])[0]
        ps.append(x)
    counts = {k: sum(1 for p in ps if p['risk'] == k) for k in RISKS + ['Unknown']}
    return {'plants': ps, 'counts': counts, 'risks': RISKS, 'words': RISK_WORD}

@app.route('/api/browse')
def browse():
    """The browse risk of every active plant here (?plant=CODE for one). Read-only, so viewers may use it."""
    return jsonify(browse_report(db(), request.args.get('plant') or None))
