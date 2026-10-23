"""Build a release zip from the repository: plant-database-v<VERSION>-<YYYYMMDD-HHMM>.zip (UTC), with everything inside a
plant-database/ folder, the way the updater expects. Leaves out dev/, docs/, data, backups, git files and caches.
  python3 tools/make-release.py              build from the current VERSION
  python3 tools/make-release.py 1.8.0        set VERSION and docker-compose.yml to 1.8.0 first, then build
Checks that VERSION, docker-compose.yml and the top CHANGELOG entry agree, and warns if the zip is over 30 MB
(the limit for saving a file to Ethan's computer from a Claude chat is 30 MB)."""
import os, re, sys, zipfile, datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SKIP_DIRS = {'.git', '.github', 'dev', 'docs', 'dist', '__pycache__'}
SKIP_TOP = {'CLAUDE.md'}
def rd(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()
ver = rd('VERSION').strip()
if len(sys.argv) > 1:
    new = sys.argv[1]
    assert re.fullmatch(r'\d+\.\d+\.\d+', new), 'version must look like 1.8.0'
    open(os.path.join(ROOT, 'VERSION'), 'w').write(new + '\n')
    c = rd('docker-compose.yml').replace(ver, new); open(os.path.join(ROOT, 'docker-compose.yml'), 'w', encoding='utf-8').write(c)
    ver = new
comp = rd('docker-compose.yml')
assert comp.count(ver) >= 3, f'docker-compose.yml does not carry version {ver} in all three places (build arg, image tag, label)'
top = re.search(r'^## (\d+\.\d+\.\d+)', rd('CHANGELOG.md'), re.M)
if not top or top.group(1) != ver: print(f'WARNING: the top CHANGELOG entry is {top.group(1) if top else "missing"}, not {ver}')
os.makedirs(os.path.join(ROOT, 'dist'), exist_ok=True)
name = f"plant-database-v{ver}-{datetime.datetime.now(datetime.timezone.utc):%Y%m%d-%H%M}.zip"
out = os.path.join(ROOT, 'dist', name)
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for d, dirs, files in os.walk(ROOT):
        rel = os.path.relpath(d, ROOT)
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not (rel == '.' and x in ('data', 'backups'))]
        for f in files:
            if rel == '.' and (f in SKIP_TOP or f.endswith('.zip')): continue
            if f.endswith('.pyc'): continue
            full = os.path.join(d, f); arc = os.path.join('plant-database', os.path.relpath(full, ROOT))
            z.write(full, arc)
    for keep in ('data/.gitkeep', 'backups/.gitkeep'):
        z.writestr('plant-database/' + keep, '')
mb = os.path.getsize(out) / 1e6
print(f'{out}  ({mb:.1f} MB)')
if mb > 30: print('WARNING: over 30 MB. It cannot be saved to Ethan\'s computer from a chat in one piece; shrink new photos or split the release.')
