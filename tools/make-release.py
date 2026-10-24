"""Build a release from the repository, the way the updater expects it (everything inside a plant-database/ folder):

  dist/plant-database-v<VERSION>-<YYYYMMDD-HHMM>.zip     the app, without plant photos (UTC time stamp)
  dist/plant-database-photos-<pack>.zip                  the plant photos, one zip per upgrade batch ("photo pack")

Photo packs never change once released, so only the packs for batches that are new in a release need sending to
Ethan; the updater finds them next to the release zip and adds any photos his folder is missing. Each zip stays under
the 30 MB limit for saving a file to his PC from a chat (a big batch is split into -part2, -part3 ...).

  python3 tools/make-release.py              build from the current VERSION
  python3 tools/make-release.py 1.8.0        set VERSION and docker-compose.yml to 1.8.0 first, then build
  python3 tools/make-release.py --full       one zip with everything, photos included (the pre-1.8.0 way)
Leaves out dev/, docs/, data, backups, git files and caches. Checks that VERSION, docker-compose.yml and the top
CHANGELOG entry agree."""
import os, re, sys, json, glob, zipfile, datetime
ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
SKIP_DIRS = {'.git', '.github', 'dev', 'docs', 'dist', '__pycache__'}
SKIP_TOP = {'CLAUDE.md', '.env'}         # .env may hold a Tailscale auth key
PACK_LIMIT = 28 * 1000 * 1000          # bytes of photos per pack zip (photos are already compressed)
PHOTOS = os.path.join(ROOT, 'app', 'seed', 'photos')
def rd(p): return open(os.path.join(ROOT, p), encoding='utf-8').read()
args = [a for a in sys.argv[1:] if not a.startswith('--')]
full = '--full' in sys.argv
ver = rd('VERSION').strip()
if args:
    new = args[0]
    assert re.fullmatch(r'\d+\.\d+\.\d+', new), 'version must look like 1.8.0'
    open(os.path.join(ROOT, 'VERSION'), 'w').write(new + '\n')
    c = rd('docker-compose.yml').replace(ver, new); open(os.path.join(ROOT, 'docker-compose.yml'), 'w', encoding='utf-8').write(c)
    ver = new
comp = rd('docker-compose.yml')
assert comp.count(ver) >= 3, f'docker-compose.yml does not carry version {ver} in all three places (build arg, image tag, label)'
top = re.search(r'^## (\d+\.\d+\.\d+)', rd('CHANGELOG.md'), re.M)
if not top or top.group(1) != ver: print(f'WARNING: the top CHANGELOG entry is {top.group(1) if top else "missing"}, not {ver}')

def photo_packs():
    """{pack name: [photo files]}: the initial seed, then each upgrade batch in the order they apply. A photo belongs to
    the first batch that uses it; photos no batch mentions go in a pack called 'extra'."""
    order, seen = [], set()
    def take(pack, f):
        if f and f not in seen and os.path.exists(os.path.join(PHOTOS, f)):
            seen.add(f); order.append((pack, f))
    seed = json.load(open(os.path.join(ROOT, 'app', 'seed', 'seed.json'), encoding='utf-8'))
    for p in seed.get('plants', []):
        for ph in p.get('photos', []): take('seed', ph['file'])
    for u in seed.get('unassigned_photos', []): take('seed', u['file'])
    for fn in sorted(glob.glob(os.path.join(ROOT, 'app', 'seed', 'batches', '*.json'))):
        b = json.load(open(fn, encoding='utf-8'))
        for p in b.get('plants', []):
            for ph in p.get('photos', []): take(b['id'], ph['file'])
        for ph in b.get('existing_photos', []): take(b['id'], ph['file'])
    for f in sorted(os.listdir(PHOTOS)): take('extra', f)
    packs = {}
    for pack, f in order: packs.setdefault(pack, []).append(f)
    out = {}
    for pack, files in packs.items():                     # split a pack that would be too big, in a fixed order
        part, size, n = [], 0, 1
        for f in files:
            sz = os.path.getsize(os.path.join(PHOTOS, f))
            if part and size + sz > PACK_LIMIT:
                out[pack if n == 1 else f'{pack}-part{n}'] = part; part, size, n = [], 0, n + 1
            part.append(f); size += sz
        if part: out[pack if n == 1 else f'{pack}-part{n}'] = part
    return out

os.makedirs(os.path.join(ROOT, 'dist'), exist_ok=True)
stamp = f"{datetime.datetime.now(datetime.timezone.utc):%Y%m%d-%H%M}"
name = f"plant-database-v{ver}-{stamp}.zip"
out = os.path.join(ROOT, 'dist', name)
packs = None if full else photo_packs()
manifest = None if full else {'version': ver, 'packs': {k: {'zip': f'plant-database-photos-{k}.zip', 'files': v} for k, v in packs.items()}}
with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
    for d, dirs, files in os.walk(ROOT):
        rel = os.path.relpath(d, ROOT)
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not (rel == '.' and x in ('data', 'backups')) and not (rel == 'tailscale' and x == 'state')]   # 1.12.0: the Tailscale sign-in
        if not full and os.path.abspath(d) == PHOTOS: continue          # photos travel in the packs
        for f in files:
            if rel == '.' and (f in SKIP_TOP or f.endswith('.zip')): continue
            if f.endswith('.pyc'): continue
            full_path = os.path.join(d, f); arc = os.path.join('plant-database', os.path.relpath(full_path, ROOT))
            z.write(full_path, arc)
    for keep in ('data/.gitkeep', 'backups/.gitkeep'):
        z.writestr('plant-database/' + keep, '')
    if manifest:
        z.writestr('plant-database/app/seed/photos/.keep', '')
        z.writestr('plant-database/app/seed/photo-packs.json', json.dumps(manifest, indent=1))
mb = os.path.getsize(out) / 1e6
print(f'{out}  ({mb:.1f} MB)')
if mb > 30: print("WARNING: over 30 MB. It cannot be saved to Ethan's computer from a chat in one piece.")
if packs:
    print('Photo packs (send Ethan the ones for batches that are new in this release):')
    for k, files in packs.items():
        pz = os.path.join(ROOT, 'dist', f'plant-database-photos-{k}.zip')
        with zipfile.ZipFile(pz, 'w', zipfile.ZIP_STORED) as z:              # JPEGs do not compress further
            for f in files: z.write(os.path.join(PHOTOS, f), 'plant-database/app/seed/photos/' + f)
        print(f'  {os.path.basename(pz)}  {len(files)} photos, {os.path.getsize(pz) / 1e6:.1f} MB')
