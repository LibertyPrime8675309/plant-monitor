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
        # 1.57.0: one bundle, /app.js, in place of 26 script tags
        assert re.findall(r'<script src="([^"]+)"></script>', page) == ['/prefs.js?v=' + S.APP_VERSION, '/app.js?v=' + S.APP_VERSION] or \
            re.findall(r'<script src="(/app\.js[^"]*)"></script>', page) == ['/app.js?v=' + S.APP_VERSION], 'index.html loads the bundle'
        assert f'<meta name="app-version" content="{S.APP_VERSION}">' in page and '<!--scripts' not in page
        sw = c.get('/sw.js').get_data(as_text=True)
        assert '__SHELL_JS__' not in sw and '__VERSION__' not in sw
        assert '/app.js?v=' + S.APP_VERSION in sw, 'the service worker saves the bundle'
        r = c.get('/app.js')
        assert r.status_code == 200 and r.mimetype == 'application/javascript'
        js = r.get_data(as_text=True)
        at = [js.index('/* ==== js/%s.js ==== */' % n) for n in man]
        assert at == sorted(at), 'the bundle holds every script, in manifest order'
        for n in man:
            body = open(os.path.join(APP, 'static', 'js', n + '.js'), encoding='utf-8').read().strip()
            assert body[:300] in js and body[-300:] in js, n + '.js is whole in the bundle'
        assert c.get('/app.js', headers={'If-None-Match': r.headers['ETag']}).status_code == 304

def test_split_scripts_on_request(monkeypatch):
    man = json.load(open(os.path.join(APP, 'static', 'js', 'manifest.json')))['scripts']
    monkeypatch.setenv('PLANTDB_JS', 'split')
    with S.app.test_client() as c:
        page = c.get('/').get_data(as_text=True)
        tags = re.findall(r'<script src="/js/([a-z]+)\.js\?v=([0-9.]+)"></script>', page)
        assert [t[0] for t in tags] == man and {t[1] for t in tags} == {S.APP_VERSION}
        assert all('/js/%s.js' % n in c.get('/sw.js').get_data(as_text=True) for n in man)

def test_every_script_is_strict():
    """1.57.0: the bundle is strict from core.js's first line on, so every part must be written for strict mode."""
    for f in glob.glob(os.path.join(APP, 'static', 'js', '*.js')):
        assert re.search(r"^'use strict';$", open(f, encoding='utf-8').read(), re.M), os.path.basename(f) + ' says use strict'

def test_css_is_one_file_built_from_the_parts():
    parts = sorted(glob.glob(os.path.join(APP, 'static', 'css', '*.css')))
    assert os.path.basename(parts[0]) == '00-core.css'
    with S.app.test_client() as c:
        r = c.get('/style.css')
        assert r.status_code == 200 and r.mimetype == 'text/css'
        css = r.get_data(as_text=True)
        for p in parts: assert open(p, encoding='utf-8').read().strip()[:200] in css, os.path.basename(p) + ' is in /style.css'
        assert css.index(open(parts[0], encoding='utf-8').read().strip()[:200]) < css.index(open(parts[-1], encoding='utf-8').read().strip()[:200]), 'core comes first'
