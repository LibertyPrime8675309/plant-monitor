"""1.58.0 (the dyslexia audit): search forgives spelling. The rules are in plantdb/fuzzy.py and again in static/js/core.js
(fzNorm, fzWord, fzMatch, fzNearest) and vision/service.py; these keep them finding the same names and making the same mistakes."""
import json, os, re, shutil, subprocess
import pytest
import server as S
from plantdb.fuzzy import fz_match, fz_nearest

NAMES = ['Philodendron Pink Princess', 'Monstera deliciosa', 'Dieffenbachia (dumb cane)', 'Calathea feather', 'Bougainvillea',
         'Begonia lobed', 'Pale palm', 'Aloe vera', 'Fig', 'Rosemary']
CASES = {   # typed: the names it finds, and the word offered in "such as ..."
    'filodendron': (['Philodendron Pink Princess'], 'Philodendron'), 'monstra': (['Monstera deliciosa'], 'Monstera'),
    'montsera': (['Monstera deliciosa'], 'Monstera'), 'dieffenbakia': (['Dieffenbachia (dumb cane)'], 'Dieffenbachia'),
    'calethea': (['Calathea feather'], 'Calathea'), 'boganvilla': (['Bougainvillea'], 'Bougainvillea'),
    'bagonia': (['Begonia lobed'], 'Begonia'), 'rosmary': (['Rosemary'], 'Rosemary'),
    'palm': (['Pale palm'], None), 'fog': ([], None), 'xyzzy': ([], None), 'pink princes': (['Philodendron Pink Princess'], None)}

@pytest.mark.parametrize('q', CASES)
def test_close_spellings_find_the_plant(q):
    want, near = CASES[q]
    assert [n for n in NAMES if fz_match(n, q)] == want
    assert fz_nearest(NAMES, q) == near

def test_short_words_must_be_as_typed():
    assert not fz_match('Pale palm', 'pals'), 'under five letters: only as typed or the start of a word'
    assert fz_match('Aloe vera', 'alo') == 'exact'

@pytest.mark.skipif(not shutil.which('node'), reason='node is not installed')
def test_the_page_uses_the_same_rules():
    src = open(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'app', 'static', 'js', 'core.js'), encoding='utf-8').read()
    part = src[src.index('function fzNorm'):src.index('// ---------- plant codes')]
    js = part + '\nconst N = %s, C = %s; const out = {}; for (const q of C) out[q] = [N.filter(n => fzMatch(n, q)), fzNearest(N, q)]; console.log(JSON.stringify(out));' % (json.dumps(NAMES), json.dumps(list(CASES)))
    got = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)
    for q, (want, near) in CASES.items():
        assert got[q] == [want, near], q

def test_search_finds_a_misspelt_plant_and_says_so():
    c = S.app.test_client()
    d = c.get('/api/search?q=' + 'filodendron').get_json()
    names = [it['title'] for g in d['groups'] if g['kind'] == 'plants' for it in g['items']]
    assert len(names) >= 5 and sum('hilodendron' in n for n in names) >= len(names) - 1, names
    assert d['close'] == 'Philodendron'
    d = c.get('/api/search?q=philodendron').get_json()
    assert d['close'] is None, 'spelt right: nothing to say'


@pytest.mark.skipif(not shutil.which('node'), reason='node is not installed')
def test_fzpick_shows_exact_first_then_close_spellings():
    """The lists with their own search box (Issue tracker, Compare lights, a light spot's plants, Add on a layout) use fzPick."""
    src = open(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'app', 'static', 'js', 'core.js'), encoding='utf-8').read()
    part = src[src.index('function fzNorm'):src.index('// ---------- plant codes')]
    js = part + '\nconst N = %s; console.log(JSON.stringify([fzPick(N, "monstra"), fzPick(N, "monstera"), fzPick(N, ""), fzPick(N, "xyzzy"), fzNote("monstra", "Monstera")]));' % json.dumps(NAMES)
    close, exact, empty, none, note = json.loads(subprocess.run(['node', '-e', js], capture_output=True, text=True, check=True).stdout)
    assert [n for n, on in zip(NAMES, close['on']) if on] == ['Monstera deliciosa'] and close['close'] == 'Monstera'
    assert exact['close'] is None and sum(exact['on']) == 1
    assert all(empty['on']) and empty['close'] is None
    assert not any(none['on']) and none['close'] is None
    assert note == ' Nothing is spelt "monstra", so these are close spellings, such as Monstera.'


def test_audit_log_search_forgives_spelling():
    c = S.app.test_client()
    name = c.get('/api/plants').get_json()[0]['common_name']
    word = max(re.findall(r'[A-Za-z]{6,}', name) or ['Philodendron'], key=len)
    typo = word[:2] + word[3:]                                 # one letter out
    d = c.get('/api/audit/search', query_string={'q': typo}).get_json()
    if d['close'] is None: assert d['total'] > 0, 'spelt that way somewhere, or a close spelling found'
    else: assert d['total'] > 0 and d['close'].lower().startswith(word[:2].lower())
    d = c.get('/api/audit/search', query_string={'q': word}).get_json()
    assert d['close'] is None
