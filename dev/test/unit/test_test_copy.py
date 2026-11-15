"""The test copy (1.58.0): tools/test-copy.ps1 and the banner it turns on."""
import os, re
import server as S

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..')
def read(*p): return open(os.path.join(ROOT, *p), encoding='utf-8').read()

def test_meta_says_whether_this_is_the_test_copy(monkeypatch):
    with S.app.test_client() as c:
        assert c.get('/api/meta').get_json()['test_copy'] is False
        monkeypatch.setenv('PLANTDB_TEST', '1')
        assert c.get('/api/meta').get_json()['test_copy'] is True

def test_the_script_turns_off_everything_that_reaches_outside():
    s = read('tools', 'test-copy.ps1')
    for name in ('PLANTDB_TEST: "1"', 'PLANTDB_PUSH: "0"', 'PLANTDB_BACKUPS: "0"', 'PLANTDB_UPDATES: "0"', 'PLANTDB_SHOPS: "0"', 'profiles: ["never"]', 'COMPOSE_PROJECT_NAME'):
        assert name in s, name
    # every container gets a name of its own, so the real ones are never replaced
    compose = read('docker-compose.yml')
    real = set(re.findall(r'container_name:\s*(\S+)', compose))
    test = set(re.findall(r'container_name:\s*(\S+)', s))
    assert len(test) == len(real) and not real & test
    # and the app reads each switch the script sets
    for env in ('PLANTDB_PUSH', 'PLANTDB_BACKUPS', 'PLANTDB_UPDATES', 'PLANTDB_SHOPS'):
        assert any(env in read('app', *p) for p in (('server.py',), ('plantdb', 'jobs.py'))), env

def test_the_script_is_plain_ascii_for_windows_powershell():
    for f in ('test-copy.ps1', 'Start Test Copy.cmd', 'Refresh Test Copy.cmd', 'Stop Test Copy.cmd'):
        open(os.path.join(ROOT, 'tools', f), encoding='ascii').read()
    assert all(f'{a} Test Copy.cmd' in read('tools', 'update-plant-database.ps1') for a in ('Start', 'Refresh', 'Stop'))
    assert 'TEST-COPY.txt' in read('tools', 'update-plant-database.ps1')
