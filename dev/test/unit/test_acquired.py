"""Date acquired (1.58.0): a plant field that holds a day."""
import pytest
import server as S
from werkzeug.exceptions import HTTPException

def test_a_day_is_kept_as_written_and_empty_stays_empty():
    assert S.norm('acquired_on', '2024-05-17') == '2024-05-17'
    assert S.norm('acquired_on', ' 2024-05-17 ') == '2024-05-17'
    assert S.norm('acquired_on', '') == '' and S.norm('acquired_on', None) == ''

@pytest.mark.parametrize('bad', ['last spring', '2024-5-17', '20240517', '05/17/2024', '2024-13-01', '1850-01-01', '2999-01-01'])
def test_anything_that_is_not_a_past_day_is_refused(bad):
    with pytest.raises(HTTPException) as e: S.norm('acquired_on', bad)
    assert e.value.code == 400 and 'Date acquired' in e.value.description

def test_every_plant_has_the_field_and_an_edit_keeps_history():
    with S.app.test_client() as c:
        p = c.get('/api/plants').get_json()[0]; code = p['code']
        one = c.get(f'/api/plants/{code}').get_json()
        assert 'acquired_on' in one and not one['acquired_on']
        r = c.put(f'/api/plants/{code}', json={'base_version': one['version'], 'fields': {'acquired_on': '2023-03-04'}}, headers={'X-Editor': 'Unit test'})
        assert r.status_code == 200, r.get_data(as_text=True)
        two = c.get(f'/api/plants/{code}').get_json()
        assert two['acquired_on'] == '2023-03-04' and two['version'] == one['version'] + 1
        meta = c.get('/api/meta').get_json()
        assert {'name': 'acquired_on', 'kind': 'date', 'label': 'Date acquired'} in meta['fields']
        r = c.put(f'/api/plants/{code}', json={'base_version': two['version'], 'fields': {'acquired_on': ''}}, headers={'X-Editor': 'Unit test'})
        assert r.status_code == 200 and not c.get(f'/api/plants/{code}').get_json()['acquired_on']
