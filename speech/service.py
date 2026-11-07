"""Plant record speech service (search by voice): turns a short recording of what you said into words, on this computer.

It runs in its own container next to the app (docker-compose.yml, service "speech"), like the picture checker. Only the app talks
to it, on Docker's private network: it is never published to the computer, the home network or Tailscale.

What it does
- On first start it downloads OpenAI's Whisper model, converted for CTranslate2 (faster-whisper, MIT licence), into /cache
  (the data/speech folder). small.en is about 465 MB; SPEECH_MODEL can be tiny.en, base.en, small.en or medium.en. /status says
  how far the download has got.
- POST /transcribe with a recording (field 'audio': WebM/Opus from Chrome, Edge, Brave and Firefox, MP4/AAC from Safari; PyAV
  reads both) and an optional 'prompt' (the app's plant names, codes and page names, so "Pink Princess" and "P-036" come out
  right) returns {"text": ...}. English, a small beam, silence trimmed (VAD).
- The recording is read in memory and dropped: it is never written to disk, and nothing leaves the computer except the
  model download."""
import io, os, threading, time
from flask import Flask, request, jsonify

CACHE = os.environ.get('SPEECH_CACHE', '/cache')
MODEL = os.environ.get('SPEECH_MODEL', 'small.en')
THREADS = int(os.environ.get('SPEECH_THREADS') or 0) or (os.cpu_count() or 4)
MAX_BYTES = 3 * 1024 * 1024            # the app sends at most about 2 MB (20 seconds); a little room on top
MAX_SECONDS = 30
os.environ.setdefault('HF_HOME', os.path.join(CACHE, 'hf'))
os.environ.setdefault('HF_HUB_DISABLE_XET', '1')
SIZES = {'tiny.en': 75e6, 'base.en': 145e6, 'small.en': 484e6, 'medium.en': 1530e6}   # roughly, for the download progress

app = Flask(__name__)
S = {'state': 'starting', 'step': 'Starting', 'model': MODEL, 'threads': THREADS, 'done': 0, 'total': 0, 'error': None}
LOCK = threading.Lock()
M = {}

def say(step, state='setting up', done=0, total=0):
    S.update(step=step, state=state, done=done, total=total)
    print(f'[speech] {step}' + (f' {done}/{total} MB' if total else ''), flush=True)

def folder_mb(path):
    n = 0
    for root, _, files in os.walk(path):
        for f in files:
            try: n += os.path.getsize(os.path.join(root, f))
            except OSError: pass
    return n / 1e6

def load():
    try:
        from faster_whisper import WhisperModel
        root = os.path.join(CACHE, 'models'); os.makedirs(root, exist_ok=True)
        total = round(SIZES.get(MODEL, 0) / 1e6)
        stop = threading.Event()
        def watch():                     # the download's size so far, for /status
            while not stop.wait(1):
                if S['state'] == 'setting up': S.update(done=round(min(folder_mb(CACHE), total or 1e9)), total=total)
        threading.Thread(target=watch, daemon=True).start()
        say(f'Getting the speech model ({MODEL}, about {total} MB the first time)', total=total)
        m = WhisperModel(MODEL, device='cpu', compute_type='int8', cpu_threads=THREADS, download_root=root)
        stop.set()
        say('Warming up')
        import numpy as np
        list(m.transcribe(np.zeros(16000, dtype=np.float32), language='en', beam_size=1)[0])
        M['model'] = m
        say('Ready', state='ready')
    except Exception as e:                # shown on the Identify page and in Display, in the app's own words
        S.update(state='error', error=f'{type(e).__name__}: {e}', step='Could not start')
        print(f'[speech] could not start: {e}', flush=True)

@app.get('/status')
def status():
    return jsonify(S)

@app.get('/healthz')
def healthz():
    return jsonify(ok=True, state=S['state'])

@app.post('/transcribe')
def transcribe():
    if S['state'] == 'off': return jsonify(error=S['step'], status=S), 503
    if S['state'] != 'ready':
        return jsonify(error='The speech service is still getting ready: ' + S['step'] + '.', status=S), 503
    f = request.files.get('audio')
    raw = f.read() if f else request.get_data()
    if not raw: return jsonify(error='No recording came with the request.'), 400
    if len(raw) > MAX_BYTES: return jsonify(error='That recording is too long. Say a few words at a time.'), 413
    prompt = (request.form.get('prompt') or '')[:1200] or None
    from faster_whisper import decode_audio
    try: audio = decode_audio(io.BytesIO(raw), sampling_rate=16000)
    except Exception: return jsonify(error='The recording could not be read. Try again, or try another browser.'), 400
    if len(audio) > MAX_SECONDS * 16000: return jsonify(error='That recording is too long. Say a few words at a time.'), 413
    t0 = time.time()
    with LOCK:                            # one at a time: the model uses every core it is given
        segs, info = M['model'].transcribe(audio, language='en', beam_size=2, vad_filter=True, vad_parameters={'min_silence_duration_ms': 400},
                                           initial_prompt=prompt, condition_on_previous_text=False, without_timestamps=True, temperature=0)
        text = ' '.join(s.text.strip() for s in segs).strip()
    return jsonify(text=text, seconds=round(len(audio) / 16000, 1), took=round(time.time() - t0, 2), model=MODEL)

if os.environ.get('PLANTDB_SPEECH', '1') == '0':          # turned off in the .env file: answer, but load nothing
    S.update(state='off', step='Search by voice is turned off (PLANTDB_SPEECH=0 in the .env file). See README, "Search by voice".')
else:
    threading.Thread(target=load, daemon=True).start()
