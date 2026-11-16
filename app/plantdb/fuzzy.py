"""1.58.0 (the dyslexia audit): search that forgives spelling, on the server. The same rules as fzNorm/fzWord in static/js/core.js,
so the Search window and the Plants page agree; vision/service.py has a copy for the Library (it is its own container).

A name typed as it sounds ("filodendron", "dieffenbakia"), a letter or two out ("monstra", "calethea") or with its vowels muddled
("boganvilla") still finds the plant. Words under five letters must be as typed (or the start of a word), so "palm" never finds "pale"."""
import re, unicodedata

ORDER = 1          # plain helpers: loaded early so other modules can use them

def fz_norm(s):
    s = unicodedata.normalize('NFD', str(s or '').lower())
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    for a, b in (('ph', 'f'), ('ck', 'k'), ('ch', 'k'), ('qu', 'kw')): s = s.replace(a, b)
    s = re.sub(r'c(?=[eiy])', 's', s).replace('c', 'k').replace('y', 'i').replace('z', 's').replace('x', 'ks')
    s = re.sub(r'[^a-z0-9]', '', s)
    return re.sub(r'(.)\1+', r'\1', s)

def fz_skel(n): return n[0] + re.sub(r'[aeiou]', '', n[1:]) if n else ''

def fz_dist(a, b):
    m, n = len(a), len(b)
    d = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m + 1): d[i][0] = i
    for j in range(n + 1): d[0][j] = j
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] != b[j - 1]))
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]: d[i][j] = min(d[i][j], d[i - 2][j - 2] + 1)
    return d[m][n]

def fz_word(q, w):
    """0 the same (or its start), 1 or 2 a slip, 3 the same consonants, or None."""
    nq, nw = fz_norm(q), fz_norm(w)
    if not nq or not nw: return None
    if nw.startswith(nq): return 0
    if len(nq) < 5: return None
    lim = 2 if len(nq) >= 8 else 1
    d = min(fz_dist(nq, nw), fz_dist(nq, nw[:len(nq)]) + 1 if len(nw) > len(nq) else 99)
    if d <= lim: return d
    sq, sw = fz_skel(nq), fz_skel(nw)
    return 3 if len(sq) >= 5 and (sw == sq or (sw.startswith(sq) and len(sw) - len(sq) <= 1)) else None

def fz_words(s): return [w for w in re.split(r'[^a-z0-9À-ɏ]+', str(s or '').lower()) if w]

def fz_match(text, q):
    """'exact' when the text holds what was typed, 'close' when every typed word is a close spelling of a word in it, else False."""
    t, qq = str(text or '').lower(), str(q or '').strip().lower()
    if not qq or qq in t: return 'exact'
    qs, ws = fz_words(qq), fz_words(t)
    if not qs: return False
    return 'close' if all(x in t or any(fz_word(x, w) is not None for w in ws) for x in qs) else False

def fz_nearest(texts, q):
    """The word in the texts nearest to what was typed, for "Did you mean ...?"."""
    best, bd = None, 99
    for x in fz_words(q):
        for t in texts:
            for w in re.split(r"[\s,()/'\"]+", str(t or '')):
                w = re.sub(r'[^\wÀ-ɏ-]', '', w)
                d = fz_word(x, w)
                if d is not None and d < bd and w.lower() != x and not w.lower().startswith(x): best, bd = w, d
    return best
