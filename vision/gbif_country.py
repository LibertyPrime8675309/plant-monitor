"""PLAN.md step 5b: which plant species are recorded in a country, from GBIF occurrence counts, for the "a new find" lift.
fetch_country(cc) gives {"Genus species": occurrences, ...} for one ISO country code; the vision service (service.py, country())
calls it the first time a request names a country and keeps the answer as gbif-<CC>.json in its cache folder.
By hand: python3 gbif_country.py <CC> [out_dir] [--probe]
--probe only prints the shape of GBIF's answer (used once from GitHub Actions to settle the request; the sandbox cannot reach GBIF)."""
import json, os, re, sys, time, urllib.parse, urllib.request

GBIF = 'https://api.gbif.org/v1/occurrence/search'
PLANTAE = 6                                        # GBIF backbone kingdom key
PAGE = 5000                                        # facet rows per request (GBIF caps facetLimit + facetOffset well above this)
MIN = 3                                            # a species with fewer records in the country is noise (a mislabelled garden plant, say)

def get(url, tries=4):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'plant-record/1.0 (vision; gbif country list)'}), timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:
            if i == tries - 1: raise
            time.sleep(3 * (i + 1))

def canon(name):
    """'Quercus virginiana Mill.' -> 'Quercus virginiana'; hybrids and names without an epithet are dropped."""
    m = re.match(r'^([A-Z][a-z]+) ([a-z][a-z\-]+)(?:\s|$)', name or '')
    return m.group(1) + ' ' + m.group(2) if m and m.group(2) not in ('sp', 'spp', 'x') else None

def fetch_country(cc, say=lambda *a: None):
    """{'Genus species': count} for the country: GBIF's scientificName facet over its plant occurrences, a page at a time."""
    out, off = {}, 0
    while True:
        q = urllib.parse.urlencode({'country': cc, 'kingdomKey': PLANTAE, 'facet': 'scientificName', 'facetLimit': PAGE, 'facetOffset': off,
                                    'facetMincount': MIN, 'limit': 0, 'hasCoordinate': 'true', 'occurrenceStatus': 'PRESENT'})
        d = get(GBIF + '?' + q)
        counts = (d.get('facets') or [{}])[0].get('counts') or []
        for x in counts:
            s = canon(x.get('name'))
            if s: out[s] = out.get(s, 0) + int(x.get('count', 0))
        say(f'GBIF {cc}: {len(out)} species so far', off + len(counts))
        if len(counts) < PAGE: break
        off += PAGE
        if off >= 400000: break                    # a safety stop; no country has this many plant names
    return out

if __name__ == '__main__':
    cc = (sys.argv[1] if len(sys.argv) > 1 else 'US').upper()
    out_dir = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else '.'
    if '--probe' in sys.argv:
        t0 = time.time()
        q = urllib.parse.urlencode({'country': cc, 'kingdomKey': PLANTAE, 'facet': 'scientificName', 'facetLimit': 20, 'facetMincount': MIN, 'limit': 0, 'hasCoordinate': 'true', 'occurrenceStatus': 'PRESENT'})
        d = get(GBIF + '?' + q)
        print('count', d.get('count'), 'seconds', round(time.time() - t0, 1))
        print(json.dumps(d.get('facets'), indent=1)[:3000])
        t0 = time.time()
        q = urllib.parse.urlencode({'country': cc, 'kingdomKey': PLANTAE, 'facet': 'scientificName', 'facetLimit': PAGE, 'facetOffset': PAGE, 'facetMincount': MIN, 'limit': 0, 'hasCoordinate': 'true', 'occurrenceStatus': 'PRESENT'})
        d = get(GBIF + '?' + q)
        c = (d.get('facets') or [{}])[0].get('counts') or []
        print('page 2 rows', len(c), 'seconds', round(time.time() - t0, 1), 'first', c[:2], 'last', c[-1:])
        sys.exit()
    t0 = time.time()
    sp = fetch_country(cc, lambda m, n: print(m, n, flush=True))
    os.makedirs(out_dir, exist_ok=True)
    p = os.path.join(out_dir, f'gbif-{cc}.json')
    json.dump(sp, open(p, 'w'))
    print(f'{p}: {len(sp)} species, {round(time.time() - t0)} s')
