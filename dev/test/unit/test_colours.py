"""1.58.0: every colour theme, contrast and colour-vision setting keeps text at 7 to 1, and the stylesheets keep to the reading rules.

The colour tokens (--ink, --moss, ...) are worked out for each combination the Display window offers, the way the browser would:
the rules on :root and html in 00-core.css and 01-reading.css, by specificity and then order. Then:
- text colours on the page and on cards, and the words of a notice on its soft tint, are 7 to 1 or better;
- the words on a filled Poor or Critical tag, and on a button, are 7 to 1 or better;
- with a colour-vision setting, good, fair and poor stay apart for that kind of colour blindness (simulated, Machado 2009).
And for reading with dyslexia: no justified text, no capitals made by the stylesheet, and italics only for Latin names."""
import itertools, os, re
import pytest

ROOT = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'app', 'static', 'css')
FILES = ['00-core.css', '01-reading.css']


def _rules():
    out, order = [], 0
    for f in FILES:
        css = open(os.path.join(ROOT, f), encoding='utf-8').read()
        css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
        css = re.sub(r'@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}', '', css)        # media blocks: the tests set the theme outright
        for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css):
            decl = dict(re.findall(r'(--[\w-]+)\s*:\s*([^;]+)', body))
            if not decl: continue
            for s in sel.split(','):
                s = s.strip()
                if re.fullmatch(r'(:root|html)((\[[\w-]+(=["\w-]+)?\])|(:not\(\[[\w-]+(=["\w-]+)?\]\)))*', s):
                    order += 1
                    out.append((s, decl, order))
    return out
RULES = _rules()


def _match(sel, attrs):
    for neg, a, v in re.findall(r'(:not\()?\[([\w-]+)(?:=["]?([\w-]+)["]?)?\]', sel):
        have = attrs.get(a)
        hit = have is not None and (v == '' or have == v)
        if hit == bool(neg): return False
    return True


def _spec(sel):
    return len(re.findall(r'\[', sel)) + 1


def tokens(attrs):
    got = {}
    for sel, decl, order in sorted((r for r in RULES if _match(r[0], attrs)), key=lambda r: (_spec(r[0]), r[2])):
        got.update(decl)
    def val(k, depth=0):
        v = got[k].strip()
        m = re.fullmatch(r'var\((--[\w-]+)\)', v)
        return val(m.group(1), depth + 1) if m and depth < 5 else v
    return {k: val(k) for k in got}


def _rgb(h):
    h = h.lstrip('#')
    if len(h) == 3: h = ''.join(c * 2 for c in h)
    return [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _lin(c): return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]


def ratio(a, b):
    la, lb = [0.2126 * l[0] + 0.7152 * l[1] + 0.0722 * l[2] for l in (_lin(_rgb(a)), _lin(_rgb(b)))]
    return (max(la, lb) + .05) / (min(la, lb) + .05)


SIM = {'deutan': [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
       'protan': [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
       'tritan': [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]]}


def _lab(c, kind):
    l = _lin(_rgb(c))
    if kind: l = [max(0, min(1, sum(m * x for m, x in zip(row, l)))) for row in SIM[kind]]
    X = [sum(m * x for m, x in zip(row, l)) for row in [[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]]
    X = [X[0] / 0.95047, X[1], X[2] / 1.08883]
    f = [x ** (1 / 3) if x > 0.008856 else 7.787 * x + 16 / 116 for x in X]
    return [116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])]


def apart(a, b, kind): return sum((x - y) ** 2 for x, y in zip(_lab(a, kind), _lab(b, kind))) ** .5


THEMES = {'light': {'data-theme': 'light', 'data-mode': 'light'}, 'cream': {'data-theme': 'light', 'data-tone': 'cream', 'data-mode': 'light'},
          'dark': {'data-theme': 'dark', 'data-mode': 'dark'}, 'softdark': {'data-theme': 'dark', 'data-tone': 'soft', 'data-mode': 'dark'},
          # the page tints (1.58.0, the dyslexia audit): light pages with a pale colour behind them
          'blue': {'data-theme': 'light', 'data-tint': 'blue', 'data-mode': 'light'}, 'green': {'data-theme': 'light', 'data-tint': 'green', 'data-mode': 'light'},
          'peach': {'data-theme': 'light', 'data-tint': 'peach', 'data-mode': 'light'}}
COMBOS = [(t, c, v) for t in THEMES for c in ('normal', 'high') for v in ('usual', 'rg', 'by')]


def _attrs(t, c, v):
    a = dict(THEMES[t]); a['data-contrast'] = c
    if v != 'usual': a['data-cvd'] = v
    return a


@pytest.mark.parametrize('t,c,v', COMBOS)
def test_text_is_seven_to_one(t, c, v):
    T, bad = tokens(_attrs(t, c, v)), []
    def need(fg, bg, at=6.95):
        r = ratio(T[fg], T[bg])
        if r < at: bad.append(f'{fg} {T[fg]} on {bg} {T[bg]}: {r:.2f}')
    for fg in ('ink', 'ink-2', 'cyan', 'moss', 'ochre', 'madder'):
        for bg in ('paper', 'sheet'): need('--' + fg, '--' + bg)
    for bg in ('cyan', 'moss', 'ochre', 'madder'):
        need('--ink', '--%s-soft' % bg)                  # a notice's words on its tint
    need('--ink-2', '--madder-soft')                       # a note in a danger box (Soft dark's was 6.85 to 1 at first)
    need('--cyan-ink', '--cyan')
    for bg in ('madder', 'critical'): need('--on-bad', '--' + bg)
    need('--top-ink', '--top-bg')
    assert not bad, f'{t}, {c} contrast, {v} colours: ' + '; '.join(bad)


@pytest.mark.parametrize('t,c,v', [x for x in COMBOS if x[2] != 'usual'])
def test_status_colours_stay_apart(t, c, v):
    T = tokens(_attrs(t, c, v))
    kinds = ['deutan', 'protan'] if v == 'rg' else ['tritan']
    cols = {'good': T['--moss'], 'fair': T['--ochre'], 'poor': T['--madder']}
    close = [f'{a}/{b} {k} {apart(cols[a], cols[b], k):.0f}' for k in kinds + [None] for a, b in itertools.combinations(cols, 2) if apart(cols[a], cols[b], k) < 20]
    assert not close, f'{t}, {c}, {v}: too alike: ' + ', '.join(close)


def test_new_themes_are_what_they_say():
    assert tokens(_attrs('cream', 'normal', 'usual'))['--paper'] != tokens(_attrs('light', 'normal', 'usual'))['--paper']
    assert tokens(_attrs('softdark', 'normal', 'usual'))['--paper'] == '#1b1c1e'
    assert tokens(_attrs('softdark', 'high', 'usual'))['--paper'] == '#000', 'Soft dark with high contrast is the high-contrast dark'


def _all_css():
    folder = os.path.join(ROOT)
    return {f: re.sub(r'/\*.*?\*/', '', open(os.path.join(folder, f), encoding='utf-8').read(), flags=re.S) for f in sorted(os.listdir(folder)) if f.endswith('.css')}


def test_reading_rules_in_the_stylesheets():
    """Justified text leaves rivers of space; capitals and slanted letters are harder to read with dyslexia. Italics are kept for
    Latin names only (.latin, and <i> around a name), and "One plain font" in Display makes even those upright."""
    found = []
    for f, css in _all_css().items():
        if re.search(r'text-align\s*:\s*justify', css): found.append(f'{f}: justified text')
        if re.search(r'text-transform\s*:\s*uppercase', css): found.append(f'{f}: capitals')
        css_no_faces = re.sub(r'@font-face\{[^}]*\}', '', css)
        for sel, body in re.findall(r'([^{}]+)\{([^{}]*)\}', css_no_faces):
            if re.search(r'font-style\s*:\s*(italic|oblique)', body) and sel.strip() != '.latin': found.append(f'{f}: italics on {sel.strip()[:40]}')
    assert not found, '; '.join(found)
