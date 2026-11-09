"""Runs the browser checks and the smoke test the way a release is tested: a fresh mock server for each check (fake weather, no
internet), one summary line per check, logs in dev/tmp/logs/. Used by hand and by GitHub Actions (.github/workflows/checks.yml).

  python3 dev/test/run_checks.py                 every check, then the smoke test
  python3 dev/test/run_checks.py lights shops    only those
  python3 dev/test/run_checks.py --shard 2/4     a quarter of them (GitHub runs four in parallel)
  python3 dev/test/run_checks.py --list          the order they run in

Exit code: the number of checks that failed. A check that must see cold weather (frost, calendar) gets a 40°F base temperature;
the ones after 'care' share its server, as they always did."""
import os, subprocess, sys, time, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
LOGS = os.path.join(ROOT, 'dev', 'tmp', 'logs'); DATA = os.path.join(ROOT, 'dev', 'tmp', 'data')
# (name, server): 'fresh' = a new data folder; '40' = fresh, with cold nights; 'share' = the server the check before it used
ORDER = [('frost', '40'), ('frostdates', 'fresh'), ('care', 'fresh'), ('read', 'share'), ('timeline', 'share'), ('copy', 'share'), ('photocheck', 'share'), ('jumprow', 'share'),
         ('prep', 'fresh'), ('audit', 'fresh'), ('fertloc', 'fresh'), ('access', 'fresh'), ('lights', 'fresh'), ('details', 'fresh'), ('swipe', 'fresh'),
         ('calendar', '40'), ('outside', 'share'), ('groups', 'fresh'), ('newplant', 'fresh'), ('identify', 'fresh'), ('idmodes', 'fresh'), ('idloop', 'fresh'), ('factrows', 'fresh'), ('factreview', 'fresh'), ('header', 'fresh'), ('undo', 'fresh'),
         ('card', 'fresh'), ('sitter', 'fresh'), ('photos', 'fresh'), ('water', 'fresh'), ('library', 'fresh'), ('filters', 'fresh'), ('fungi', 'fresh'), ('wishlist', 'fresh'),
         ('know', 'fresh'), ('facts', 'fresh'), ('shops', 'fresh'), ('layout', 'fresh'), ('dialog', 'fresh'), ('offline', 'fresh'), ('sectionmenu', 'fresh'),
         ('homes', 'fresh'), ('sites', 'fresh'), ('places', 'fresh'), ('several', 'fresh'), ('where', 'fresh'), ('pots', 'fresh'), ('prefs', 'fresh'), ('shopping', 'fresh'),
         ('quickwins', 'fresh'), ('jobs', 'fresh'), ('reach', 'fresh'), ('pages', 'fresh'), ('sensors', 'fresh'), ('finish', 'fresh'), ('share', 'fresh'), ('phone', 'share'), ('turning', 'fresh'), ('repotting', 'fresh'), ('releases', 'fresh'), ('checkup', 'fresh'), ('voice', 'fresh'), ('units', 'fresh'), ('sitlink', 'fresh'), ('smoke', 'fresh')]
TIMEOUT = {'smoke': 600, 'reach': 600, 'shopping': 600, 'quickwins': 600, 'pages': 600, 'share': 600, 'phone': 900}
SERVER = None

def stop_server():
    global SERVER
    if SERVER and SERVER.poll() is None:
        SERVER.terminate()
        try: SERVER.wait(10)
        except subprocess.TimeoutExpired: SERVER.kill(); SERVER.wait(5)
    SERVER = None

def start_server(base):
    """A fresh data folder, the mock server, then one weather update so the forecast is filled in."""
    global SERVER
    stop_server()
    try:                                                   # a mock server left running by hand would answer instead of ours
        out = subprocess.run(['pgrep', '-f', 'dev/test/mock_server.py'], capture_output=True, text=True).stdout.split()
        for pid in out:
            if int(pid) != os.getpid():
                import signal; os.kill(int(pid), signal.SIGTERM)
        if out: time.sleep(2)
    except (OSError, ValueError, FileNotFoundError): pass
    import shutil; shutil.rmtree(DATA, ignore_errors=True); os.makedirs(DATA)
    env = dict(os.environ, MOCK_TS=os.environ.get('MOCK_TS', '1'), MOCK_BASE_F=base, DATA_DIR=DATA)
    env.pop('MOCK_VISION', None)
    for _ in range(20):                                    # wait for the port to be free, so the new server is the one that answers
        import socket
        with socket.socket() as sk:
            if sk.connect_ex(('127.0.0.1', 8080)) != 0: break
        time.sleep(1)
    else: raise SystemExit('port 8080 is still in use; stop whatever is on it')
    SERVER = subprocess.Popen([sys.executable, os.path.join(HERE, 'mock_server.py')], cwd=ROOT, env=env,
                              stdout=open(os.path.join(ROOT, 'dev', 'tmp', 'mock.log'), 'w'), stderr=subprocess.STDOUT)
    for _ in range(60):
        time.sleep(1)
        if SERVER.poll() is not None: raise SystemExit('the mock server stopped; see dev/tmp/mock.log')
        try: urllib.request.urlopen('http://127.0.0.1:8080/api/meta', timeout=2).read(); break
        except Exception: pass
    else: raise SystemExit('the mock server did not start; see dev/tmp/mock.log')
    req = urllib.request.Request('http://127.0.0.1:8080/api/weather/refresh', data=b'{}', headers={'X-Editor': 'Test', 'Content-Type': 'application/json'})
    try: urllib.request.urlopen(req, timeout=10).read()
    except Exception: pass
    for _ in range(40):
        time.sleep(3)
        try:
            if b'"running": false' in urllib.request.urlopen('http://127.0.0.1:8080/api/weather/job', timeout=5).read().replace(b'"running":false', b'"running": false'): break
        except Exception: pass

def run(name):
    script = os.path.join(HERE, 'smoke.py' if name == 'smoke' else f'{name}_check.py')
    log = os.path.join(LOGS, name + '.log')
    with open(log, 'w') as f:
        try: rc = subprocess.run([sys.executable, script], cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=TIMEOUT.get(name, 400)).returncode
        except subprocess.TimeoutExpired: rc = 124; f.write('\nTIMED OUT\n')
    text = open(log, errors='replace').read()
    ok = sum(1 for l in text.splitlines() if l.startswith('ok '))
    bad = [l for l in text.splitlines() if l.startswith('FAIL')]
    err = [l for l in text.splitlines() if 'Error' in l or 'TIMED OUT' in l][-1:] if rc and not bad else []
    print(f'== {name}: exit {rc}, {ok} ok, {len(bad)} FAIL' + (f'  {bad[0][:110]}' if bad else '') + (f'  {err[0][:110]}' if err else ''), flush=True)
    return rc == 0

def main(argv):
    os.makedirs(LOGS, exist_ok=True)
    names = [n for n, _ in ORDER]
    if '--list' in argv: print('\n'.join(names)); return 0
    picked = [a for a in argv if not a.startswith('--')]
    if '--shard' in argv:
        k, n = map(int, argv[argv.index('--shard') + 1].split('/'))
        picked = [nm for i, nm in enumerate(names) if i % n == k - 1]
    todo = [(n, s) for n, s in ORDER if not picked or n in picked]
    unknown = [p for p in picked if p not in names]
    if unknown: print('no such check:', ', '.join(unknown)); return 1
    failed = []
    try:
        last = None
        for name, srv in todo:
            if srv != 'share' or last is None or picked: start_server('40' if srv == '40' else '65')
            if not run(name): failed.append(name)
            last = name
    finally: stop_server()
    print(f'\n{len(todo) - len(failed)} of {len(todo)} passed' + (': failed ' + ', '.join(failed) if failed else ''))
    return len(failed)

if __name__ == '__main__': raise SystemExit(main(sys.argv[1:]))
