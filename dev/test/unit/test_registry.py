"""1.46.0 (PLAN.md step 2): the module and script lists are generated, not kept by hand. These tests catch a module or a script
that was added without joining the list, and the server pages that carry the list."""
import glob, json, os, re
import server as S

APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'app')

def test_every_server_module_loads_core_first():
    names = [m.__name__.split('.')[-1] for m in S.MODULES]
    files = sorted(os.path.basename(f)[:-3] for f in glob.glob(os.path.join(APP, 'plantdb', '*.py')) if not f.endswith('__init__.py'))
    assert names[0] == 'core'
    assert sorted(names) == files, 'every .py in app/plantdb is a module and loads'

def test_every_script_is_in_the_manifest_and_exists():
    man = json.load(open(os.path.join(APP, 'static', 'js', 'manifest.json')))['scripts']
    files = sorted(os.path.basename(f)[:-3] for f in glob.glob(os.path.join(APP, 'static', 'js', '*.js')))
    assert man[0] == 'core' and man[1] == 'features' and man[-1] == 'main', 'core first, the registry next, main last'
    assert sorted(man) == files, 'every js file is in js/manifest.json and every name in it is a file'
    assert len(set(man)) == len(man)

def test_index_and_service_worker_carry_the_script_list():
    man = json.load(open(os.path.join(APP, 'static', 'js', 'manifest.json')))['scripts']
    with S.app.test_client() as c:
        page = c.get('/').get_data(as_text=True)
        tags = re.findall(r'<script src="/js/([a-z]+)\.js\?v=([0-9.]+)"></script>', page)
        assert [t[0] for t in tags] == man, 'index.html loads the scripts in manifest order'
        assert {t[1] for t in tags} == {S.APP_VERSION} and f'<meta name="app-version" content="{S.APP_VERSION}">' in page, '1.56.5: each names the version'
        assert '<!--scripts' not in page
        sw = c.get('/sw.js').get_data(as_text=True)
        assert '__SHELL_JS__' not in sw and '__VERSION__' not in sw
        assert all('/js/%s.js' % n in sw for n in man), 'the service worker saves every script'

def test_css_is_one_file_built_from_the_parts():
    parts = sorted(glob.glob(os.path.join(APP, 'static', 'css', '*.css')))
    assert os.path.basename(parts[0]) == '00-core.css'
    with S.app.test_client() as c:
        r = c.get('/style.css')
        assert r.status_code == 200 and r.mimetype == 'text/css'
        css = r.get_data(as_text=True)
        for p in parts: assert open(p, encoding='utf-8').read().strip()[:200] in css, os.path.basename(p) + ' is in /style.css'
        assert css.index(open(parts[0], encoding='utf-8').read().strip()[:200]) < css.index(open(parts[-1], encoding='utf-8').read().strip()[:200]), 'core comes first'
