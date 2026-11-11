"""1.57.0 (review item 23): a name the server code uses must exist somewhere. The modules in app/plantdb share their names
(core.link() hands each module every other module's names), so pyflakes' "undefined name" is checked against the names all the
modules define between them. Also: no local variable assigned and never used, and no module importing something it never uses
(core.py excepted: its imports are shared with every module)."""
import ast, builtins, glob, os
import pytest

pyflakes = pytest.importorskip('pyflakes')
from pyflakes import checker, messages as M

APP = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'app')
MODS = sorted(glob.glob(os.path.join(APP, 'plantdb', '*.py')))
OTHERS = sorted(f for f in glob.glob(os.path.join(APP, '*.py')))

def module_names(path):
    """The names a module defines at its top level (functions, classes, assignments, imports)."""
    tree = ast.parse(open(path, encoding='utf-8').read())
    out = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)): out.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                for n in ast.walk(t):
                    if isinstance(n, ast.Name): out.add(n.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for a in node.names: out.add((a.asname or a.name).split('.')[0])
        elif isinstance(node, ast.For):
            for n in ast.walk(node):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store): out.add(n.id)
        elif isinstance(node, (ast.If, ast.Try, ast.With)):
            for n in ast.walk(node):
                if isinstance(n, (ast.FunctionDef, ast.ClassDef)): out.add(n.name)
                elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store): out.add(n.id)
                elif isinstance(n, (ast.Import, ast.ImportFrom)):
                    for a in n.names: out.add((a.asname or a.name).split('.')[0])
    return out

def findings(path, shared):
    path = os.path.abspath(path)
    src = open(path, encoding='utf-8').read()
    w = checker.Checker(ast.parse(src, filename=path), filename=path, builtins=set(dir(builtins)) | shared)
    return [m for m in w.messages]

def test_shared_names_all_exist_and_nothing_is_left_unused():
    shared = set().union(*(module_names(p) for p in MODS))
    bad = []
    for p in MODS:
        for m in findings(p, shared):
            if isinstance(m, (M.UndefinedName, M.UndefinedLocal, M.UnusedVariable, M.RedefinedWhileUnused, M.ImportShadowedByLoopVar)):
                bad.append(str(m))
            elif isinstance(m, M.UnusedImport) and not m.message_args[0].endswith('*') and not p.endswith(os.sep + 'core.py') and not p.endswith('__init__.py'):
                bad.append(str(m))
    for p in OTHERS:
        for m in findings(p, shared if os.path.basename(p) == 'server.py' else set()):
            if isinstance(m, (M.UndefinedName, M.UndefinedLocal, M.UnusedVariable, M.UnusedImport)) and not (m.message_args and str(m.message_args[0]).endswith('*')): bad.append(str(m))
    bad = [b.replace(os.path.abspath(APP) + os.sep, 'app/') for b in bad]
    assert not bad, '\n'.join(bad)

def test_the_lint_catches_a_typo():
    shared = set().union(*(module_names(p) for p in MODS))
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.py', delete=False) as f: f.write('def x():\n    return plant_by_codee(1)\n')
    try: assert any(isinstance(m, M.UndefinedName) for m in findings(f.name, shared))
    finally: os.remove(f.name)

def load_time_names(tree):
    """Names read while a module is being imported: top-level statements, decorators, default values and class bodies (not the
    bodies of functions, which run later, when every module's names have been linked)."""
    out = []
    def visit(node, top=True):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for d in node.decorator_list + node.args.defaults + [d for d in node.args.kw_defaults if d]: visit(d)
            return
        if isinstance(node, ast.Lambda):
            for d in node.args.defaults: visit(d)
            return
        if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            loop = {n.id for g in node.generators for n in ast.walk(g.target) if isinstance(n, ast.Name)}
            for n in ast.walk(node):
                if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id not in loop: out.append((n.id, n.lineno))
            return
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load): out.append((node.id, node.lineno))
        for ch in ast.iter_child_nodes(node): visit(ch)
    for node in tree.body: visit(node)
    return out

def test_module_level_code_uses_only_its_own_and_the_cores_names():
    """core.link() fills in other modules' names only after every module is imported, so code that runs at import time (a constant
    built from another constant, a default value, a decorator) may use only core's names and its own (ARCHITECTURE, 1.32.0).
    1.57.0: checked here, since splitting a module could break it without any test noticing until the app failed to start."""
    core = module_names(os.path.join(APP, 'plantdb', 'core.py'))
    bad = []
    for p in MODS:
        if p.endswith(os.sep + 'core.py') or p.endswith('__init__.py'): continue
        tree = ast.parse(open(p, encoding='utf-8').read())
        own = module_names(p)
        for node in tree.body:     # names imported from another module explicitly (facts.py from library.py, say) are its own too
            if isinstance(node, ast.ImportFrom):
                for a in node.names: own.add(a.asname or a.name)
        for n, line in load_time_names(tree):
            if n not in own and n not in core and not hasattr(builtins, n):
                bad.append(f'{os.path.basename(p)}:{line}: {n} is read at import time but is not core\'s or this module\'s own')
    assert not bad, '\n'.join(bad)
