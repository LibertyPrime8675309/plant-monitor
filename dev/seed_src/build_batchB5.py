"""Builds app/seed/batches/batchB5.json (1.30.0): details for the stores near Round Rock (address, phone, hours, what they carry),
the stores near Nevada City, and two "Still to photograph" items Ethan ticked off. Store details were read from each store's own
website on November 4, 2026, except where details_src says otherwise. Run: python3 dev/seed_src/build_batchB5.py"""
import json, os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'app', 'seed', 'batches', 'batchB5.json')
AT = '2026-11-04T00:00:00Z'
OWN = "From the store's own website, checked November 4, 2026"
def upd(key, **f):
    return {'key': key, 'set': {k: [None, v] for k, v in f.items()} | {'details_src': [None, f.get('_src', OWN)], 'details_at': [None, AT]}}
U = [
    upd('roundrockgc', address='901 Sam Bass Rd., Round Rock, TX 78681', phone='512-255-3353',
        hours='Mon to Sat 9 am to 5 pm; Sun 10 am to 5 pm. Closed Thanksgiving, Christmas and New Year\'s Day.', email='onlinestore@roundrockgardens.com',
        website='https://www.roundrockgardens.com/', carries=['plant', 'mix', 'amend', 'fert', 'pest', 'tools']),
    upd('snoopers', address='3602 E Old Settlers Blvd, Round Rock, TX 78665', phone='512-310-2614', carries=['plant'],
        _src='From business listings (Yelp, Buzzfile), November 4, 2026: its own website did not open. Call to check'),
    upd('cantu', address='3223 S Interstate 35, Round Rock, TX', phone='512-990-2607', email='cantuimports@hotmail.com',
        website='https://cantuimports.com/', carries=['plant', 'pots']),
    upd('barryhill', address='690A N. Bagdad Rd, Leander, TX 78641', phone='512-923-9227',
        hours='Mon to Sat 9 am to 4 pm; Sun 10 am to 4 pm (can change with the season and holidays; call before going in bad weather).',
        website='https://www.barryhillgc.com/', carries=['plant', 'mix', 'amend', 'fert', 'pest', 'pots', 'tools']),
    upd('mindseye', address='100 E Main Street #202, Round Rock, TX 78664', email='mindseyeplants@gmail.com',
        hours='Wed to Sat noon to 6 pm; Sun noon to 4 pm; closed Mon and Tue (as best read from its website; check before going).',
        website='https://www.mindseyeplants.com/', carries=['plant']),
]
for u in U: u['set'].pop('_src', None)
for u in U:                      # the extra key used above for the source is not a field
    for k in list(u['set']):
        if k.startswith('_'): u['set'].pop(k)
NC = 'Nevada City, CA'
A = [
    {'key': 'peacefulvalley', 'name': 'Peaceful Valley Farm & Garden Supply', 'kind': 'auto', 'url': 'https://www.groworganic.com/', 'local': 1, 'online': 1, 'home': NC,
     'address': '125 Clydesdale Ct., Grass Valley, CA 95945', 'phone': '(530) 272-4769; toll-free (888) 784-1722',
     'hours': 'Mon to Sat 9 am to 5 pm. Closed Memorial Day, Independence Day and Labor Day.', 'website': 'https://www.groworganic.com/',
     'carries': ['plant', 'mix', 'amend', 'fert', 'pest', 'frost', 'tools'], 'details_src': OWN, 'details_at': AT},
    {'key': 'bcace', 'name': 'B&C Ace Home & Garden Center', 'kind': 'page', 'url': 'https://www.bandchomecenter.com/plant-nursery', 'local': 1, 'home': NC,
     'address': '2032 Nevada City Highway, Grass Valley, CA 95945', 'phone': '(530) 273-6105',
     'hours': 'Mon to Sat 7:30 am to 6 pm (its website also says 7 pm); Sun 8 am to 5 pm.', 'website': 'https://www.bandchomecenter.com/',
     'carries': ['plant', 'mix', 'amend', 'fert', 'pots', 'tools'], 'details_src': OWN, 'details_at': AT},
    {'key': 'weiss', 'name': 'Weiss Brothers Nursery', 'kind': 'page', 'url': 'http://www.weissbrothersnursery.com/', 'local': 1, 'home': NC,
     'address': '615 Maltman Drive, Grass Valley, CA 95945', 'phone': '(530) 273-5814', 'website': 'http://www.weissbrothersnursery.com/',
     'carries': ['plant'], 'details_src': 'From the Nevada City Chamber of Commerce listing, November 4, 2026. Call for hours', 'details_at': AT},
    {'key': 'prospectors', 'name': "Prospector's Nursery", 'kind': 'page', 'url': 'https://prospectorsnursery.com/', 'local': 1, 'home': NC,
     'address': '10003 Granholm Lane, Nevada City, CA 95959', 'phone': '530-470-0973', 'hours': 'Tue, Thu and Fri 9 am to 3 pm.',
     'website': 'https://prospectorsnursery.com/', 'carries': ['plant'], 'details_src': OWN, 'details_at': AT},
    {'key': 'ncblooms', 'name': 'Nevada City Blooms', 'kind': 'page', 'url': 'https://www.nevadacityblooms.com/', 'local': 1, 'home': NC,
     'address': '310 Drummond St., Nevada City, CA 95959', 'phone': '530-277-6885', 'hours': 'Open all day, every day, April to October (a self-serve flower bar).',
     'website': 'https://www.nevadacityblooms.com/', 'carries': ['plant'], 'details_src': OWN + ': a small nursery of native plants, with cut flowers', 'details_at': AT},
    {'key': 'doubledogwood', 'name': 'Double Dogwood Native Nursery', 'kind': 'page', 'url': 'https://www.doubledogwoodnursery.org/', 'local': 1, 'home': NC,
     'address': '', 'email': 'info@doubledogwoodnursery.com', 'hours': 'Visits by appointment only; email an order, and pick it up on a Thursday, 1:30 to 5 pm.',
     'website': 'https://www.doubledogwoodnursery.org/', 'carries': ['plant'], 'details_src': OWN + ': native trees, shrubs, perennials and grasses, in Nevada City', 'details_at': AT},
]
B = {'id': 'B5', 'created': '2026-11-04', 'author': 'Claude (store details for Shopping, Nov 2026)',
     'shops_update': U, 'shops_add': A,
     'to_photograph_done': ['Third extra palm', 'Any plants not yet photographed'], 'to_photograph_add': []}
json.dump(B, open(OUT, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('wrote', OUT, len(U), 'store updates,', len(A), 'stores added')
