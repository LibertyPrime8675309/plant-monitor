"""Search by voice (prototype proto/voice-search): the recording a voice button makes goes to the speech service (container
"plant-speech", speech/service.py) on Docker's private network, which turns it into words with Whisper on this computer.
The app adds a short prompt with your plant names, codes and page names, so they come out spelled the way the record has them.
Nothing is saved, and it changes nothing, so viewers may use it too (VIEWER_POSTS in core.py)."""
from .core import *   # noqa: F401,F403
SPEECH_URL = os.environ.get('PLANTDB_SPEECH_URL', 'http://speech:8093').rstrip('/')
VOICE_MAX = 2 * 1024 * 1024               # search stops at 15 seconds, a spoken note at a minute (32 kbit/s: about 240 KB)
VOICE_PAGES = ('Today, All plants, Groups, Add plants, Mushrooms, Rooms and spots, Photos, Labels, Year in review, Winter plan, '
               'Cold-night checklist, Coming inside, Back outside, Fertilizer, Grow lights, Pots and trays, Weather, Sensors, '
               'Homes and places, Identify, Library, Around home, Wishlist, Shopping, Settings, Offline use, Backups, Audit log')

def speech_call(path, data=None, ctype=None, timeout=60):
    req = urllib.request.Request(SPEECH_URL + path, data=data, headers={'Content-Type': ctype} if ctype else {}, method='POST' if data is not None else 'GET')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())
    except urllib.error.HTTPError as e:
        try: body = json.loads(e.read())
        except Exception: body = {}
        if e.code == 503: abort(503, body.get('error') or 'The speech service is still getting ready (downloading its model). Try again in a few minutes.')
        abort(e.code if e.code in (400, 413) else 502, body.get('error') or f'The speech service could not understand that recording ({e.code}).')
    except TimeoutError:
        abort(504, 'The speech service took too long. Try again with a few words.')
    except (urllib.error.URLError, OSError):
        abort(503, 'The speech service is not running. Start it with the updater, or see README, "Search by voice".')

def voice_prompt(c, note=False):
    """Words Whisper should expect, most important last (it keeps the end of a long prompt): pages, plant names, then codes.
    1.44.0: for a spoken note (the Speak buttons) only the plant names, written as sentences, so the note comes out punctuated."""
    names = []
    for (n,) in c.execute("SELECT common_name FROM plants WHERE status='active' AND common_name<>'' ORDER BY id DESC"):
        n = re.sub(r'\s*\([^)]*\)', '', n).strip()            # "Begonia (lobed, bright green)" -> "Begonia"
        if n and n.lower() not in (x.lower() for x in names): names.append(n)
    if note: return ('A note about my plants. The plants are ' + ', '.join(names))[:900] + '. Codes look like P-006 and P-036.'
    text = 'Pages: ' + VOICE_PAGES + '. Plants: ' + ', '.join(names)
    return text[:900] + '. Say "open" and a page or a plant. Codes look like P-006, P-036 and F-002.'

@app.route('/api/voice/status')
def voice_status():
    try: st = speech_call('/status', timeout=5)
    except Exception as e:
        st = {'state': 'off', 'step': getattr(e, 'description', 'The speech service is not running.')}
    return jsonify(st)

@app.route('/api/voice', methods=['POST'])
def voice():
    """A recording (field 'audio') in, {text} out. At most about 2 MB (20 seconds)."""
    if (request.content_length or 0) > VOICE_MAX + 64 * 1024: abort(413, 'That recording is too long. Say a few words at a time.')
    f = request.files.get('audio')
    if not f: abort(400, 'No recording came with the request.')
    raw = f.read(VOICE_MAX + 1)
    if not raw: abort(400, 'The recording was empty. Press the button and try again.')
    if len(raw) > VOICE_MAX: abort(413, 'That recording is too long. Say a few words at a time.')
    body, ctype = multipart({'prompt': voice_prompt(db(), note=request.form.get('mode') == 'note')}, [('audio', f.filename or 'voice.webm', raw, f.mimetype or 'application/octet-stream')])
    out = speech_call('/transcribe', body, ctype, timeout=40)
    return jsonify(text=(out.get('text') or '').strip(), seconds=out.get('seconds'), took=out.get('took'))
