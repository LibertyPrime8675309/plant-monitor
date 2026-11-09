import pytest
import server as S

def test_site_of_and_back():
    for side, sh, site in (('out', 0, 'Outdoors'), ('out', 1, 'Covered porch'), ('in', 1, 'Indoors'), ('in', 0, 'Garage or shed')):
        assert S.site_of(side, sh) == site
        assert S.side_of_site(site) == (side, sh)

def test_version_tuple_orders_releases():
    assert S.version_tuple('1.31.0') > S.version_tuple('1.30.0') > S.version_tuple('1.9.9')
    assert S.version_tuple('garbage') == (0, 0, 0)

def test_same_value_reads_numbers_and_blanks_alike():
    assert S.same_value(None, '') and S.same_value(' 5 ', 5) and S.same_value(5.0, '5')
    assert not S.same_value('5', '6') and not S.same_value('a', None)

def test_cont_sqft_counts_a_circle_as_its_square():
    assert S.cont_sqft({'shape': 'circle', 'dia_in': 12, 'len_in': None, 'wid_in': None}) == 1.0
    assert S.cont_sqft({'shape': 'rectangle', 'dia_in': None, 'len_in': 24, 'wid_in': 12}) == 2.0
    assert S.cont_sqft({'shape': 'square', 'dia_in': None, 'len_in': 6, 'wid_in': None}) == 0.25
    assert S.cont_sqft({'shape': 'square', 'dia_in': None, 'len_in': None, 'wid_in': None}) is None

def test_miles():
    assert S.miles(30.5083, -97.6789, 30.5083, -97.6789) == 0
    assert 160 < S.miles(30.5083, -97.6789, 32.7767, -96.797) < 170      # Round Rock to Dallas, as the crow flies
    assert S.miles(None, 1, 2, 3) is None

def test_fert_calc_ppm():
    r = S.fert_calc('liquid', 2, 7, 7, 10, 'ml', 1, 'gal')          # 10 ml of a 2-7-7 in a gallon
    assert r['n_grams'] == 0.2
    assert abs(r['ppm_n'] - 0.2 * 1000 / 3.785) < 0.5
    assert S.fert_calc('granular', 2, 7, 7, None, 'g', 1, 'gal') == {'ppm_n': None, 'ppm_p2o5': None, 'ppm_k2o': None, 'n_grams': None}

def test_norm_ranges():
    assert S.norm('temp_ideal_low', '50') == 50
    assert S.norm('temp_ideal_low', '') is None
    with pytest.raises(Exception): S.norm('temp_ideal_low', 'warm')

def test_osm_address():
    assert S.osm_address({'house_number': '615', 'road': 'Maltman Drive', 'city': 'Grass Valley', 'state': 'California', 'postcode': '95945'}) == '615 Maltman Drive, Grass Valley, CA 95945'
    assert S.osm_address({}) == ''

# ---- 1.34.0: summer heat (AHS heat zones)
def test_ahs_heat_zone_bands():
    assert S.ahs_heat_zone(0) == 1 and S.ahs_heat_zone(0.9) == 1
    assert S.ahs_heat_zone(1) == 2 and S.ahs_heat_zone(7) == 2 and S.ahs_heat_zone(8) == 3
    assert S.ahs_heat_zone(116) == 8 and S.ahs_heat_zone(120) == 8 and S.ahs_heat_zone(121) == 9
    assert S.ahs_heat_zone(300) == 12 and S.ahs_heat_zone(None) is None

def test_place_heat_needs_three_whole_years():
    import json, math
    from datetime import date, timedelta
    c = S.sqlite3.connect(S.DB_PATH, timeout=30); c.row_factory = S.sqlite3.Row
    L = S.home_place(c); lid = L['id']
    c.execute('DELETE FROM weather_daily WHERE loc_id=?', (lid,))
    S.PLACE_HEAT.clear()
    this_year = S.local_today(c).year
    def fill(y):
        d = date(y, 1, 1)
        while d.year == y:
            doy = d.timetuple().tm_yday
            hi = 70 + 30 * math.sin((doy - 110) / 365 * 2 * math.pi)
            c.execute("INSERT OR REPLACE INTO weather_daily(loc_id,date,data,kind,updated_at) VALUES(?,?,?,?,?)", (lid, d.isoformat(), json.dumps({'temperature_2m_max': hi, 'temperature_2m_min': hi - 20}), 'observed', S.now()))
            d += timedelta(days=1)
    fill(this_year - 1); fill(this_year - 2); c.commit()
    h = S.place_heat(c, L)
    assert h['zone'] is None and h['years'] == 2 and h['over86'] is None          # two whole years: not enough yet
    S.PLACE_HEAT.clear(); fill(this_year - 3); c.commit()
    h = S.place_heat(c, L)
    assert h['years'] == 3 and h['over86'] > 100 and h['zone'] == S.ahs_heat_zone(h['over86']) and h['hottest'] == 100
    assert [m['month'] for m in h['months']][0] in ('May', 'Jun') and all(y['over86'] == h['over86'] for y in h['per_year'] if not y['partial'])
    c.execute('DELETE FROM weather_daily WHERE loc_id=?', (lid,)); c.commit(); S.PLACE_HEAT.clear()

# ---- 1.36.0: every page the router knows is listed in a section's row (or reached from a listed page by a link in the code)
def test_every_route_is_reachable():
    import os, re
    here = os.path.dirname(os.path.abspath(__file__)); js = os.path.join(here, '..', '..', '..', 'app', 'static', 'js')
    core = open(os.path.join(js, 'core.js'), encoding='utf-8').read()
    routes = set(re.findall(r"parts\[0\] === '([a-z]+)'", core)) - {'plant', 'group', 'species', 'store', 'fungi', 'today', 'audit'}   # pages of one thing, reached from lists; audit is the old name of history
    listed = set(re.findall(r"\['([a-z]+)', '[^']+', '#/[^']*'\]", core.split('const SECTIONS')[1].split('];')[0]))
    everything = ' '.join(open(os.path.join(js, f), encoding='utf-8').read() for f in os.listdir(js))
    missing = [r for r in routes if r not in listed and f'href="#/{r}' not in everything]
    assert not missing, f'pages nobody can find: {missing}'
    assert {'frost', 'inside', 'outside', 'around', 'decisions', 'sensors'} <= listed

# ---- prototype (proto/frost-dates): frost dates from the weather history
def test_frost_season_helpers():
    from datetime import date
    assert S.season_of(date(2025, 7, 1)) == 2025 and S.season_of(date(2026, 6, 30)) == 2025
    assert S.season_day(date(2025, 7, 1)) == 0 and S.season_label(S.season_day(date(2025, 12, 4))) == 'Dec 4'
    assert S.middle([3, 1, 2]) == 2 and S.middle([1, 2, 3, 4]) == 2.5 and S.middle([]) is None

def test_season_stats_first_last_and_none():
    from datetime import date
    w = {2021: [(date(2021, 11, 20), 31), (date(2022, 2, 10), 25), (date(2022, 3, 1), 33)],
         2022: [(date(2022, 12, 4), 32), (date(2023, 2, 22), 30)],
         2023: [(date(2023, 12, 20), 35)]}
    st = S.season_stats(w, 32)
    assert st['winters'] == 3 and st['had'] == 2 and st['none'] == 1 and not st['most_none']
    assert st['first']['earliest'] == 'Nov 20' and st['first']['latest'] == 'Dec 4' and st['last']['latest'] == 'Feb 22'
    assert S.season_stats(w, 32, strict=True)['first']['latest'] == 'Feb 22'       # strict: the 32°F night of Dec 4 is not below 32
    assert S.season_stats(w, 26)['most_none'] and S.season_stats(w, 26)['first']['usual'] == 'Feb 10'

def test_frost_dates_needs_three_whole_winters():
    import json, math
    from datetime import date, timedelta
    c = S.sqlite3.connect(S.DB_PATH, timeout=30); c.row_factory = S.sqlite3.Row
    L = S.home_place(c); lid = L['id']
    c.execute('DELETE FROM weather_daily WHERE loc_id=?', (lid,)); S.PLACE_LOWS.clear()
    start = S.season_of(S.datetime.now(S.tzinfo(L['tz'])).date())
    def fill(s):
        d = date(s, 7, 1)
        while d < date(s + 1, 7, 1):
            doy = d.timetuple().tm_yday
            lo = 50 + 25 * math.sin((doy - 110) / 365 * 2 * math.pi)        # coldest (25°F) in mid-January
            c.execute("INSERT OR REPLACE INTO weather_daily(loc_id,date,data,kind,updated_at) VALUES(?,?,?,?,?)", (lid, d.isoformat(), json.dumps({'temperature_2m_min': lo}), 'observed', S.now()))
            d += timedelta(days=1)
    fill(start - 1); fill(start - 2); c.commit()
    r = S.frost_dates(c, L)
    assert not r['ready'] and r['winters'] == 2 and 'freeze' not in r
    fill(start - 3); c.commit(); S.PLACE_LOWS.clear()
    r = S.frost_dates(c, L)
    assert r['ready'] and r['winters'] == 3 and r['freeze']['first']['usual'].startswith('Dec') and r['freeze']['last']['usual'].startswith(('Feb', 'Mar'))
    assert r['hard']['first']['usual_day'] > r['freeze']['first']['usual_day'] and r['frost_free_days'] > 250
    # Ethan's answers of November 6: frost possible at 36°F (sooner than a freeze, later in spring), and days to the usual last nights
    assert r['possible']['first']['usual_day'] < r['freeze']['first']['usual_day'] and r['possible']['last']['usual_day'] > r['freeze']['last']['usual_day']
    assert set(r['days_to_last']) == {'freeze', 'hard', 'possible'} and r['days_to_last']['possible'] > r['days_to_last']['freeze'] > r['days_to_last']['hard']
    assert all('first_possible' in w for w in r['per_winter']) and 1 <= r['month'] <= 12
    assert [w['winter'] for w in r['per_winter']][0] == f'{start - 1} to {start}'
    c.execute('DELETE FROM weather_daily WHERE loc_id=?', (lid,)); c.commit(); S.PLACE_LOWS.clear()

# ---- 1.51.1 (PLAN.md step 5d): the fields that check a mushroom lead, and the finds' export
def test_mushroom_find_fields_pick_lists_and_export():
    import server as S
    with S.app.test_client() as c:
        H = {'X-Editor': 'Fungi Test'}
        m = c.get('/api/fungi?status=none').get_json()
        names = [f['name'] for f in m['fields']]
        assert 'habitat' in names and 'stem' in names and {f['name']: f['kind'] for f in m['fields']}['spore_print'] == 'pick'
        assert 'Lawn or grass' in m['enums']['habitat'] and 'White' in m['picks']['spore_print'] and 'Not checked' in m['picks']['smell']
        r = c.post('/api/fungi', json={'fields': {'name': 'Little brown one', 'found_on': '2026-11-08', 'habitat': 'Lawn or grass', 'stem': 'Thin, hollow, 2 inches',
                                                   'spore_print': 'Lilac (my own word)', 'smell': 'Mushroomy or faint'}}, headers=H)
        assert r.status_code in (200, 201), r.get_data(as_text=True)
        code = r.get_json()['code']
        f = c.get('/api/fungi/' + code).get_json()
        assert f['habitat'] == 'Lawn or grass' and f['stem'] == 'Thin, hollow, 2 inches' and f['spore_print'] == 'Lilac (my own word)', 'a pick field takes any words'
        assert c.post('/api/fungi', json={'fields': {'name': 'x', 'found_on': '2026-11-08', 'habitat': 'The moon'}}, headers=H).status_code == 400, 'an enum still refuses other answers'
        csv_text = c.get('/api/fungi.csv').get_data(as_text=True)
        assert csv_text.splitlines()[0].startswith('code,status,') and ',habitat,' in csv_text.splitlines()[0] and 'Little brown one' in csv_text
        j = c.get('/api/export.json').get_json()
        assert any(x['code'] == code for x in j['mushroom_finds']) and 'mushroom_photos' in j
