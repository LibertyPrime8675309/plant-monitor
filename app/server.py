"""Plant record: the entry point gunicorn and the tests load (server:app). The code is in the plantdb package: core (the app,
database, helpers, people, security), then one module per feature. Everything is re-exported here, so `import server as S`
still gives S.app, S.init_db, S.light_verdict and the rest, as before 1.32.0."""
import os, sys, threading
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from plantdb import core, where, weather, plants, care, fert, groups, lights, library, fungi, shopping, audit, offline, frost, backups, jobs, push, search, copies, heat, sensors, review, mirror, turning
MODULES = [core, where, weather, plants, care, fert, groups, lights, library, fungi, shopping, audit, offline, frost, backups, jobs, push, search, copies, heat, sensors, review, mirror, turning]
globals().update(core.link(MODULES))
def patch(name, value):
    """For tests: replace a function (http_json, say) in every module at once, since each holds its own link to it."""
    for m in MODULES: vars(m)[name] = value
    globals()[name] = value

init_db()
if os.environ.get('PLANTDB_BACKUPS', '1') == '1' and not MIRROR:
    threading.Thread(target=backup_loop, daemon=True).start()
if MIRROR:
    threading.Thread(target=mirror_loop, daemon=True).start()        # 1.37.0: the read-only mirror takes the newest backup every few minutes
if os.environ.get('PLANTDB_SHOPS', '1') == '1':
    threading.Thread(target=shops_loop, daemon=True).start()          # 1.27.0: the wishlist's shops, twice a day
if os.environ.get('PLANTDB_OSM', '1') == '1':
    threading.Thread(target=shops_geo, daemon=True).start()           # 1.30.0: map positions for the stores you can visit, once each
if os.environ.get('PLANTDB_WEATHER', '1') == '1':
    threading.Thread(target=weather_loop, daemon=True).start()
if os.environ.get('PLANTDB_PUSH', '1') == '1':
    threading.Thread(target=push_loop, daemon=True).start()           # 1.33.0: cold nights and what is due, as notifications

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
