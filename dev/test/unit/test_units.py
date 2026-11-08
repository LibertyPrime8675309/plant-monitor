"""1.47.0 (PLAN.md step 4a): units. Everything is kept in °F and inches; a person's 'units' setting decides what they read."""
import json
import server as S

C = {'temp': 'c', 'len': 'cm', 'rain': 'mm'}
F = {'temp': 'f', 'len': 'in', 'rain': 'in'}

def test_temperature_words():
    assert S.temp_text(72, F) == '72°F' and S.temp_text(72, C) == '22°C'
    assert S.temp_text(32, C) == '0°C' and S.temp_text(-40, C) == '-40°C'
    assert S.temp_text(72.5, C) == '22.5°C' and S.temp_text(72.5, F) == '72.5°F'
    assert S.temp_text(90, C, unit=False) == '32'
    assert S.temp_text(None, C) == '' and S.temp_text('', C) == ''
    assert S.temp_diff_text(3, F) == '3°F' and S.temp_diff_text(3, C) == '1.7°C' and S.temp_diff_text(9, C) == '5°C'

def test_length_and_rain_words():
    assert S.len_text(6, F) == '6 in' and S.len_text(6, C) == '15 cm' and S.len_text(1, C) == '2.5 cm'
    assert S.rain_text(0.5, F) == '0.5 in' and S.rain_text(0.5, C) == '13 mm' and S.rain_text(0.02, C) == '0.5 mm'

def test_sentences_written_for_fahrenheit_convert():
    t = 'Spray in the shade, between 50 and 90°F, until wet. Remove the cover above 35°F.'
    assert S.temps_in_text(t, F) == t
    assert S.temps_in_text(t, C) == 'Spray in the shade, between 10 and 32°C, until wet. Remove the cover above 2°C.'

def test_units_setting_follows_the_person_and_reaches_server_text():
    with S.app.test_client() as c:
        H = {'X-Editor': 'Unit'}
        r = c.put('/api/me/prefs', json={'units': json.dumps({'region': 'metric'})}, headers=H); assert r.status_code == 200, r.get_data(as_text=True)
        with S.app.app_context():
            assert S.units_for(S.db()) == C
        m = c.get('/api/prep').get_json()['methods']
        soap = next(x for x in m if x['key'] == 'soap')
        assert any('10 and 32°C' in st for st in soap['steps']), soap['steps']
        r = c.put('/api/me/prefs', json={'units': json.dumps({'region': 'metric', 'temp': 'f'})}, headers=H); assert r.status_code == 200
        with S.app.app_context():
            assert S.units_for(S.db()) == {'temp': 'f', 'len': 'cm', 'rain': 'mm'}, 'one unit changed by hand stands'
        c.put('/api/me/prefs', json={'units': None}, headers=H)
        with S.app.app_context():
            assert S.units_for(S.db()) == F
