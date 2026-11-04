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
