"""The plant record's server, in modules: core (the app, database, helpers, people, security), then one module per feature.
server.py (one level up) calls load() to import them all and core.link() to let them call across each other.

1.46.0 (PLAN.md step 2): the modules find themselves. Every .py file in this folder is a module; core comes first and the rest
follow in ORDER (a number a module may set at its top, usually left at 50) and then by name. A new feature on the server is one
new file here, with no list to edit. A module that must load after another (it imports from it, say) gives itself a higher ORDER."""
import importlib, pkgutil

def load():
    from . import core
    names = sorted(m.name for m in pkgutil.iter_modules(__path__) if m.name != 'core')
    others = [importlib.import_module('.' + n, __name__) for n in names]
    others.sort(key=lambda m: (getattr(m, 'ORDER', 50), m.__name__))
    return [core] + others
