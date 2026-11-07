"""Search by voice (prototype proto/voice-search): POST /api/voice passes a recording to the speech service and returns its words.
The fake speech service (dev/test/mock_speech.py) runs on a free port for these tests."""
import importlib.util, io, os, threading
import pytest
import server as S
import plantdb.voice as VM
from werkzeug.serving import make_server

HERE = os.path.dirname(os.path.abspath(__file__))

@pytest.fixture(scope='module')
def speech():
    spec = importlib.util.spec_from_file_location('mock_speech_unit', os.path.join(HERE, '..', 'mock_speech.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    srv = make_server('127.0.0.1', 0, m.app, threaded=True)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    old = VM.SPEECH_URL
    VM.SPEECH_URL = f'http://127.0.0.1:{srv.server_port}'
    yield m
    VM.SPEECH_URL = old
    srv.shutdown()

def post(data, **kw):
    return S.app.test_client().post('/api/voice', data=data, content_type='multipart/form-data', headers={'X-Editor': 'Unit'}, **kw)

def test_words_come_back_and_the_prompt_has_the_names(speech):
    speech.STATE.update(state='ready', say='open pink princess')
    r = post({'audio': (io.BytesIO(b'\x1aE\xdf\xa3 fake webm'), 'voice.webm', 'audio/webm')})
    assert r.status_code == 200 and r.get_json()['text'] == 'open pink princess'
    last = speech.STATE['last']
    assert last['bytes'] > 0 and last['name'] == 'voice.webm'
    p = last['prompt']
    assert p.startswith('Pages: Today') and 'Grow lights' in p and 'P-036' in p and p.endswith('F-002.')
    with S.app.test_request_context():
        names = [n for (n,) in S.db().execute("SELECT common_name FROM plants WHERE status='active' AND common_name<>'' ORDER BY id DESC LIMIT 3")]
    assert names and all(n.split(' (')[0] in p for n in names)          # the newest plants' names, without their brackets
    assert len(p) < 1100

def test_not_ready_and_not_running_say_so_in_plain_words(speech):
    speech.STATE['state'] = 'setting up'
    r = post({'audio': (io.BytesIO(b'abc'), 'voice.webm', 'audio/webm')})
    assert r.status_code == 503 and 'getting ready' in r.get_json()['error']
    speech.STATE['state'] = 'ready'
    keep = VM.SPEECH_URL
    VM.SPEECH_URL = 'http://127.0.0.1:9'
    try:
        r = post({'audio': (io.BytesIO(b'abc'), 'voice.webm', 'audio/webm')})
        assert r.status_code == 503 and 'not running' in r.get_json()['error']
        st = S.app.test_client().get('/api/voice/status').get_json()
        assert st['state'] == 'off' and 'not running' in st['step']
    finally:
        VM.SPEECH_URL = keep

def test_size_limits_and_missing_audio(speech):
    assert post({}).status_code == 400
    assert post({'audio': (io.BytesIO(b''), 'voice.webm', 'audio/webm')}).status_code == 400
    big = b'0' * (2 * 1024 * 1024 + 10)
    r = post({'audio': (io.BytesIO(big), 'voice.webm', 'audio/webm')})
    assert r.status_code == 413 and 'too long' in r.get_json()['error']

def test_viewers_may_use_it():
    assert '/api/voice' in S.VIEWER_POSTS
