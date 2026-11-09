"""1.39.0: the picture checker's naming with a stand-in model: the prior for the record's own species and genera, houseplants and
the place's state; the look-alike bonus from the record's own photos; several pictures of one plant; the views of one picture.
No torch here: the model is faked with a colour fingerprint, and the species list is tiny."""
import importlib.util, io, os, sqlite3, sys, types
import numpy as np
import pytest
from PIL import Image
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

def colour_vec(img):
    r, g, b = np.array(img.convert('RGB').resize((8, 8))).reshape(-1, 3).mean(0) / 255
    v = np.array([r, g, b, 1 - r, 1 - g, 1 - b, 0.5, 0.5], dtype=np.float32)
    return v / np.linalg.norm(v)

@pytest.fixture
def svc(tmp_path, monkeypatch):
    monkeypatch.setenv('PLANTDB_VISION', '0'); monkeypatch.setenv('VISION_CACHE', str(tmp_path)); monkeypatch.setenv('DATA_DIR', str(tmp_path))
    spec = importlib.util.spec_from_file_location('vision_service', os.path.join(ROOT, 'vision', 'service.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    # the stand-in model: the fingerprint is the picture's colour; a name's fingerprint is a colour too
    class T(list):
        def unsqueeze(self, _): return self
    class Vec:
        def __init__(self, v): self.v = v
        def float(self): return self
        def numpy(self): return self.v
    class Model:
        def encode_image(self, x): return [Vec(np.array(x[0]))]
    class Torch:
        def no_grad(self):
            class C:
                def __enter__(self): pass
                def __exit__(self, *a): pass
            return C()
    m.M.update(model=Model(), pre=lambda img: T([colour_vec(img)]), torch=Torch(), scale=100.0)
    def row(kingdom, family, genus, species, common): return [[kingdom, 'Tracheophyta', 'Magnoliopsida', 'Order', family, genus, species], common]
    rows = [row('Plantae', 'Araceae', 'Epipremnum', 'aureum', 'golden pothos'),      # 0 green, a houseplant genus
            row('Plantae', 'Araceae', 'Monstera', 'deliciosa', 'Swiss cheese plant'), # 1 green too
            row('Plantae', 'Fabaceae', 'Lupinus', 'texensis', 'Texas bluebonnet'),   # 2 blue
            row('Plantae', 'Rosaceae', 'Rosa', 'gallica', 'rose'),                   # 3 red
            row('Plantae', 'Asteraceae', 'Testia', 'rubra', ''),                      # 4 red too, no common name, not in the US
            row('Plantae', 'Poaceae', 'Bouteloua', 'gracilis', 'blue grama')]        # 5 grey, Texas
    def cv(rgb): return colour_vec(Image.new('RGB', (4, 4), rgb))
    emb = np.stack([cv((40, 200, 40)), cv((60, 190, 50)), cv((40, 40, 220)), cv((220, 30, 30)), cv((210, 40, 40)), cv((128, 128, 128))]).astype(np.float16)
    sp = [r[0][5] + ' ' + r[0][6] for r in rows]
    usda = {'Epipremnum aureum': {'Florida': ('golden pothos', 'EPAU', 'Araceae')}, 'Lupinus texensis': {'Texas': ('Texas bluebonnet', 'LUTE', 'Fabaceae')},
            'Rosa gallica': {'Texas': ('rose', 'ROGA', 'Rosaceae')}, 'Bouteloua gracilis': {'Texas': ('blue grama', 'BOGR', 'Poaceae')}}
    has = np.ones(6, bool)
    m.NAMES.update(rows=rows, sp=sp, emb=emb, usda=usda, hay=[x.lower() for x in sp], by_sp={s: i for i, s in enumerate(sp)}, n_plants=6,
                   masks={'world': has, 'us': np.array([s in usda for s in sp]), 'texas': np.array([s in usda and 'Texas' in usda[s] for s in sp]), 'common': has, 'fungi': ~has})
    m.S.update(state='ready', step='Ready')
    # the record: one named plant (a pothos) with one photo, and a plant named only to the genus
    db = sqlite3.connect(os.path.join(tmp_path, 'plants.db'))
    db.executescript("CREATE TABLE plants(id INTEGER PRIMARY KEY, code TEXT, scientific_name TEXT, status TEXT); CREATE TABLE photos(id INTEGER PRIMARY KEY, plant_id INTEGER, file TEXT);"
                     "INSERT INTO plants VALUES(1,'P-001','Epipremnum aureum','active'),(2,'P-002','Rosa sp.','active'),(3,'P-003','Lupinus texensis','archived');"
                     "INSERT INTO photos VALUES(1,1,'p1.jpg');")
    db.commit(); db.close()
    os.makedirs(os.path.join(tmp_path, 'photos')); Image.new('RGB', (64, 64), (45, 195, 45)).save(os.path.join(tmp_path, 'photos', 'p1.jpg'))
    m.index_photos()
    return m

def pic(rgb, size=(64, 64)):
    b = io.BytesIO(); Image.new('RGB', size, rgb).save(b, 'JPEG'); return b.getvalue()

def ask(m, data, **args):
    c = m.app.test_client()
    r = c.post('/identify?' + '&'.join(f'{k}={v}' for k, v in args.items()), data=data, content_type='multipart/form-data')
    assert r.status_code == 200, r.get_json()
    return r.get_json()

def test_photo_index_knows_the_species_of_each_photo(svc):
    assert svc.PHOTOS['files'] == ['p1.jpg'] and svc.PHOTOS['sp'] == [0]
    assert svc.PHOTOS['own_sp'] == {0} and svc.PHOTOS['own_gen'] == {'Epipremnum', 'Rosa'}     # the archived bluebonnet does not count
    assert svc.species_index('Epipremnum aureum') == 0 and svc.species_index('Rosa sp.') == -1 and svc.species_index('') == -1

def test_prior_and_look_alike_lift_the_record_s_own_species(svc):
    # a green picture: pothos and monstera look the same to the stand-in model; the pothos is in the record (and a houseplant) and its photo looks alike
    r = ask(svc, {'image': (io.BytesIO(pic((45, 195, 45))), 'g.jpg')}, views=0)
    names = [s['scientific_name'] for s in r['species']]
    assert names[0] == 'Epipremnum aureum' and set(r['species'][0]['basis']) == {'own_sp', 'house', 'looks'}
    assert r['species'][0]['probability'] > r['species'][1]['probability'] + 0.3
    assert r['matches'][0]['code'] == 'P-001' and len(r['species']) == 6 and r['prior'] is True
    assert r['genera'][0]['genus'] == 'Epipremnum'
    # without the prior the two greens are nearly level
    svc.PRIOR_ON = False
    r2 = ask(svc, {'image': (io.BytesIO(pic((45, 195, 45))), 'g.jpg')}, views=0)
    assert abs(r2['species'][0]['probability'] - r2['species'][1]['probability']) < 0.3 and all(s['basis'] == [] for s in r2['species'])
    svc.PRIOR_ON = True

def test_a_genus_in_the_record_and_the_state_count_too(svc):
    r = ask(svc, {'image': (io.BytesIO(pic((215, 35, 35))), 'r.jpg')}, views=0, scope='state:Texas')
    assert r['species'][0]['scientific_name'] == 'Rosa gallica' and set(r['species'][0]['basis']) == {'own_gen', 'state'}   # Rosa sp. is in the record; the rose grows in Texas
    assert [s['scientific_name'] for s in r['species']][:2] == ['Rosa gallica', 'Bouteloua gracilis'] or 'Testia rubra' not in [s['scientific_name'] for s in r['species']]   # the state list leaves Testia out

def test_several_pictures_are_averaged_and_views_are_made(svc):
    one = ask(svc, {'image': (io.BytesIO(pic((45, 195, 45))), 'g.jpg')})
    assert one['pictures'] == 1
    both = ask(svc, {'image': (io.BytesIO(pic((45, 195, 45))), 'g.jpg'), 'images': (io.BytesIO(pic((40, 40, 220))), 'b.jpg')})
    assert both['pictures'] == 2
    names = [s['scientific_name'] for s in both['species']]
    assert names[0] == 'Epipremnum aureum' and names.index('Lupinus texensis') < names.index('Rosa gallica')   # the blue shot pulls the bluebonnet up
    wide = Image.new('RGB', (300, 100), (45, 195, 45))
    views = svc.views_of(wide)
    assert len(views) == 3 and views[1].size == (300, 300) and views[2].size == (180, 60)     # the whole picture letterboxed, and the middle 60%
    assert len(svc.views_of(Image.new('RGB', (100, 100)))) == 2                              # a square picture needs no letterbox

# ---- PLAN.md step 5b (1.51.0): two modes, and the plants recorded in a country
def test_a_new_find_drops_the_record_s_lifts_and_lifts_the_country_s_plants(svc, tmp_path):
    import json
    # no country yet: in 'new' mode the two greens are level again (no own_sp, house or looks), and the answer says so
    r = ask(svc, {'image': (io.BytesIO(pic((45, 195, 45))), 'g.jpg')}, views=0, mode='new')
    assert r['mode'] == 'new' and r['country'] is None
    assert all('own_sp' not in s['basis'] and 'house' not in s['basis'] and 'looks' not in s['basis'] for s in r['species'])
    assert abs(r['species'][0]['probability'] - r['species'][1]['probability']) < 0.3
    assert r['matches'][0]['code'] == 'P-001', 'the match against the record\'s own photos still shows (it may be yours after all)'
    # a country list in the cache: Monstera is recorded in that country often, the pothos never
    json.dump({'Monstera deliciosa': 5000, 'Lupinus texensis': 12}, open(os.path.join(tmp_path, 'gbif-XX.json'), 'w'))
    r = ask(svc, {'image': (io.BytesIO(pic((45, 195, 45))), 'g.jpg')}, views=0, mode='new', country='xx')
    assert r['country'] == {'code': 'XX', 'state': 'ready', 'species': 2}
    assert r['species'][0]['scientific_name'] == 'Monstera deliciosa' and r['species'][0]['basis'] == ['country']
    assert r['species'][0]['probability'] > r['species'][1]['probability'] + 0.3
    assert float(svc.COUNTRY['XX']['weight'][1]) == 1.0 and 0.3 < float(svc.COUNTRY['XX']['weight'][2]) < 0.4, 'the lift grows with how often a species is recorded'
    # the same picture as one of my plants: the pothos wins as before
    r = ask(svc, {'image': (io.BytesIO(pic((45, 195, 45))), 'g.jpg')}, views=0, mode='mine', country='xx')
    assert r['species'][0]['scientific_name'] == 'Epipremnum aureum' and r['country'] is None
    # a country with no list yet starts a download (which fails here, offline) and says so; a bad code is ignored
    svc.country_fetch = lambda cc: svc.COUNTRY.__setitem__(cc, {'state': 'error', 'error': 'offline', 'mask': None, 'weight': None, 'species': 0})
    r = ask(svc, {'image': (io.BytesIO(pic((45, 195, 45))), 'g.jpg')}, views=0, mode='new', country='zz')
    assert r['country']['code'] == 'ZZ' and r['country']['state'] in ('fetching', 'error')
    assert ask(svc, {'image': (io.BytesIO(pic((45, 195, 45))), 'g.jpg')}, views=0, mode='new', country='usa')['country'] is None
    st = svc.app.test_client().get('/status?country=xx').get_json()
    assert st['country'] == {'code': 'XX', 'state': 'ready', 'species': 2}

def test_gbif_country_names_are_cut_to_genus_and_species():
    spec = importlib.util.spec_from_file_location('gbif_country', os.path.join(ROOT, 'vision', 'gbif_country.py'))
    g = importlib.util.module_from_spec(spec); spec.loader.exec_module(g)
    assert g.canon('Quercus virginiana Mill.') == 'Quercus virginiana'
    assert g.canon('Honckenya peploides subsp. diffusa (Hornem.) Hultén') == 'Honckenya peploides'
    assert g.canon('Quercus L.') is None and g.canon('Quercus sp.') is None and g.canon('Salix × fragilis') is None and g.canon('') is None
