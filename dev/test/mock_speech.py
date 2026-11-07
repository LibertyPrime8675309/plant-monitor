"""A fake speech service (speech/service.py) for tests. It cannot hear: a test tells it what the next recording "says" with
POST /mock/say {"text": ...}, and can switch its state with POST /mock/state {"state": "ready" | "setting up" | "off"}.
GET /mock/last shows the last recording it got (size, type) and the prompt the app sent. mock_server.py starts it on
127.0.0.1:8094 (MOCK_SPEECH_PORT; 8093 is outside_check.py's own server)."""
from flask import Flask, jsonify, request
app = Flask(__name__)
STATE = {'state': 'ready', 'say': 'monstera', 'last': None}

@app.get('/status')
def status():
    st = STATE['state']
    return jsonify(state=st, model='small.en (test)', threads=8, error=None,
                   step={'ready': 'Ready', 'setting up': 'Getting the speech model (small.en, about 484 MB the first time)'}.get(st, 'Search by voice is turned off (test).'),
                   done=120 if st == 'setting up' else 0, total=484 if st == 'setting up' else 0)

@app.post('/transcribe')
def transcribe():
    if STATE['state'] != 'ready':
        return jsonify(error='The speech service is still getting ready: Getting the speech model (small.en).'), 503
    f = request.files.get('audio'); raw = f.read() if f else b''
    STATE['last'] = {'bytes': len(raw), 'type': f.mimetype if f else None, 'name': f.filename if f else None, 'prompt': request.form.get('prompt', '')}
    if not raw: return jsonify(error='No recording came with the request.'), 400
    return jsonify(text=STATE['say'], seconds=2.0, took=0.3, model='small.en (test)')

@app.post('/mock/say')
def mock_say():
    STATE['say'] = (request.get_json() or {}).get('text', ''); return jsonify(ok=True)

@app.post('/mock/state')
def mock_state():
    STATE['state'] = (request.get_json() or {}).get('state', 'ready'); return jsonify(ok=True)

@app.get('/mock/last')
def mock_last():
    return jsonify(STATE['last'] or {})
