"""Finds the long sentences in the app's own words (1.58.0, the dyslexia audit).

Reads the text the front end writes (static/js/*.js) and lists every sentence of more than 25 words, file by file, with its line.
Text the record holds (plant notes, care profiles, batches) is not here: only the words written in the code.

    python3 dev/tools/wording.py                   every file
    python3 dev/tools/wording.py care.js lights.js some files
    python3 dev/tools/wording.py --count           the count per file only

dev/test/unit/test_wording.py keeps the count from growing: each file may have no more long sentences than its line in LIMITS."""
import os, re, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'app', 'static', 'js')
MAX_WORDS = 25


def _strip_expr(s):
    """${...} becomes X (a value), however deep the braces go."""
    out, i = [], 0
    while i < len(s):
        if s.startswith('${', i):
            depth, j = 1, i + 2
            while j < len(s) and depth:
                depth += {'{': 1, '}': -1}.get(s[j], 0); j += 1
            out.append('X'); i = j
        else:
            out.append(s[i]); i += 1
    return ''.join(out)


def prose(src):
    """(line, text) for each run of words the code shows to people: inside template literals and string literals."""
    found = []
    for m in re.finditer(r'`((?:[^`\\]|\\.)*)`|\'((?:[^\'\\\n]|\\.){30,})\'|"((?:[^"\\\n]|\\.){30,})"', src, re.S):
        body = next(g for g in m.groups() if g is not None)
        line = src.count('\n', 0, m.start()) + 1
        text = _strip_expr(body)
        text = re.sub(r'<[^>]*>', ' ', text)                   # tags out; their words stay
        for piece in re.split(r'\n\s*\n', text):
            piece = re.sub(r'\s+', ' ', piece).strip()
            if len(piece.split()) >= 8 and re.search(r'[a-z]{3,} [a-z]{3,} [a-z]{2,}', piece) and not re.search(r'=>|\bconst |\breturn |;\s*\w+\(|\bfunction\b|\);|\b(if|await|try|catch)\s*\(|\w\.\w+\(|//', piece):
                found.append((line, piece))
    return found


def sentences(t):
    return [s.strip() for s in re.split(r'(?<=[.!?:])\s+(?=[A-Z"(“])', t) if s.strip()]


def by_line(src):
    """(line, text) for prose on a single line, between quotes, backticks and tags: catches what the template scan splits wrongly."""
    for i, l in enumerate(src.split('\n'), 1):
        if re.match(r'\s*(//|/\*|\*)', l): continue                         # comments are for programmers
        l = re.sub(r'\s//\s.*$', '', l)
        t = re.sub(r'\$\{[^{}]*\}', 'X', l)
        for seg in re.split(r"[<>`]|'\s*[,)+:]|[(,:]\s*'", t):
            if not re.search(r'=>|\bconst\b|\breturn\b|===|&&|\|\||[{}]|\b(if|await|try|catch|toast|api|function)\s*\(|\w\.\w+\(|\);|//', seg): yield i, seg


def long_ones(fname):
    src = open(os.path.join(ROOT, fname), encoding='utf-8').read()
    src = re.sub(r'/\*.*?\*/', lambda m: '\n' * m.group(0).count('\n'), src, flags=re.S)
    out, seen = [], set()
    for line, t in list(prose(src)) + list(by_line(src)):
        for s in sentences(t):
            s = re.sub(r'\s+', ' ', s).strip()
            n = len(re.findall(r"[A-Za-z0-9X][\w'’-]*", s))
            key = re.sub(r'\W+', '', s)[:40]
            if n > MAX_WORDS and key not in seen: seen.add(key); out.append((line, n, s))
    return sorted(out)


def main(argv):
    files = [a for a in argv if a.endswith('.js')] or sorted(f for f in os.listdir(ROOT) if f.endswith('.js'))
    total = 0
    for f in files:
        L = long_ones(f); total += len(L)
        if '--count' in argv: print(f'{len(L):4d}  {f}'); continue
        for line, n, s in L: print(f'{f}:{line} ({n} words) {s[:200]}')
    print(f'{total} sentences over {MAX_WORDS} words')


if __name__ == '__main__':
    main(sys.argv[1:])
