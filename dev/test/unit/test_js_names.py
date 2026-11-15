"""1.57.0 (review item 22): the front-end scripts share one scope, so two files must never declare the same top-level name. A second
`function x` silently replaces the first, and a second `let x` stops the whole bundle from loading."""
import collections, glob, os, re

JS = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'app', 'static', 'js')
DECL = re.compile(r'^(?:async\s+)?(?:function\*?|let|const|var|class)\s+([A-Za-z_$][\w$]*)', re.M)
MULTI = re.compile(r'^(?:let|const|var)\s+(.+?);?\s*$', re.M)

def top_names(text):
    names = DECL.findall(text)
    # `let a = 1, b = 2;` on one line declares b too (only simple comma lists at the top level)
    for m in MULTI.finditer(text):
        line = m.group(1)
        depth, cur, parts = 0, '', []
        for ch in line:
            if ch in '([{': depth += 1
            elif ch in ')]}': depth -= 1
            if ch == ',' and depth == 0: parts.append(cur); cur = ''
            else: cur += ch
        parts.append(cur)
        for p in parts[1:]:
            n = re.match(r'\s*([A-Za-z_$][\w$]*)\s*(=|$)', p)
            if n: names.append(n.group(1))
    return names

def test_no_name_is_declared_twice():
    where = collections.defaultdict(list)
    for f in sorted(glob.glob(os.path.join(JS, '*.js'))):
        for n in top_names(open(f, encoding='utf-8').read()): where[n].append(os.path.basename(f))
    twice = {n: fs for n, fs in where.items() if len(fs) > 1}
    assert not twice, 'declared more than once: ' + ', '.join(f'{n} ({" and ".join(fs)})' for n, fs in sorted(twice.items()))
    assert len(where) > 500, 'the scan found the names'

def test_the_scan_sees_a_duplicate():
    assert top_names('function a() {}\nlet b = 1, c = [1, 2];\nconst d = f(1, 2);\n') == ['a', 'b', 'd', 'c']
