"""1.32.0: one list of the app's background jobs. Each worker (the weather update, a backup, the store check, library downloads,
map look-ups) reports here when it starts, how far it has got, and how it ended, so the Jobs window on Settings shows what is
running, what is waiting on a schedule, and what went wrong, in one place. The workers themselves are unchanged."""
from .core import *   # noqa: F401,F403

JOB_WORD = {'weather': 'Weather update', 'backup': 'Backup', 'shops': 'Store check', 'library': 'Library photos', 'know': 'Library lookups',
            'area': 'Library download', 'geo': 'Store map positions', 'restore': 'Restore', 'copy': 'Backup copy to the other computer'}
JOBS = {'lock': threading.Lock(), 'running': {}, 'done': [], 'next': 0}

def job_start(kind, label='', total=0):
    """Returns the job's id. One job of a kind at a time: starting another of the same kind replaces its line."""
    with JOBS['lock']:
        JOBS['next'] += 1; jid = JOBS['next']
        for k, j in list(JOBS['running'].items()):
            if j['kind'] == kind: JOBS['running'].pop(k)
        JOBS['running'][jid] = {'id': jid, 'kind': kind, 'word': JOB_WORD.get(kind, kind), 'label': label, 'done': 0, 'total': total, 'started': now(), 'beat': time.time()}
    return jid

def job_progress(jid, done=None, total=None, label=None):
    with JOBS['lock']:
        j = JOBS['running'].get(jid)
        if not j: return
        if done is not None: j['done'] = done
        if total is not None: j['total'] = total
        if label is not None: j['label'] = label
        j['beat'] = time.time()

def job_end(jid, ok=True, text=''):
    with JOBS['lock']:
        j = JOBS['running'].pop(jid, None)
        if not j: return
        j.update(ok=ok, text=str(text)[:300], finished=now(), seconds=round(time.time() - j['beat'] + (time.time() - j['beat']) * 0, 1))
        try: j['seconds'] = round((datetime.fromisoformat(j['finished'].replace('Z', '+00:00')) - datetime.fromisoformat(j['started'].replace('Z', '+00:00'))).total_seconds(), 1)
        except ValueError: pass
        JOBS['done'].insert(0, j); del JOBS['done'][30:]

def job_run(kind, label, fn, *args, **kw):
    """Runs fn in a thread of its own, reporting start and end (and any error as a problem). Returns the job id."""
    jid = job_start(kind, label)
    def work():
        try: r = fn(*args, **kw); job_end(jid, True, r if isinstance(r, str) else '')
        except Exception as e:
            job_end(jid, False, getattr(e, 'description', None) or f'{type(e).__name__}: {e}')
            problem_exc(kind if kind in PROBLEM_AREA else 'start', e, f'{JOB_WORD.get(kind, kind)} failed')
    threading.Thread(target=work, daemon=True).start()
    return jid

def jobs_schedule(c):
    """When each scheduled job is next due, in words the Jobs window shows."""
    out = []
    hours = float(setting(c, 'shops_hours', '12') or 0); last = setting(c, 'shops_checked_at', '')
    if hours > 0 and os.environ.get('PLANTDB_SHOPS', '1') == '1':
        due = (datetime.fromisoformat(last.replace('Z', '+00:00')) + timedelta(hours=hours)).strftime('%Y-%m-%dT%H:%M:%SZ') if last else 'soon'
        out.append({'kind': 'shops', 'word': JOB_WORD['shops'], 'every': f'every {hours:g} hours', 'next': due, 'last': last})
    else: out.append({'kind': 'shops', 'word': JOB_WORD['shops'], 'every': 'only when you ask', 'next': '', 'last': last})
    if os.environ.get('PLANTDB_WEATHER', '1') == '1':
        wl = setting(c, 'weather_last_auto', '') or ''
        out.append({'kind': 'weather', 'word': JOB_WORD['weather'], 'every': 'every hour', 'next': (datetime.fromisoformat(wl.replace('Z', '+00:00')) + timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ') if wl else 'within the hour', 'last': wl})
    S = bk_settings(c)
    if S['enabled']:
        last_b = setting(c, 'backup_last_auto', '') or ''
        out.append({'kind': 'backup', 'word': JOB_WORD['backup'], 'every': {6: 'every 6 hours', 12: 'every 12 hours', 24: 'once a day', 168: 'once a week'}.get(BK_FREQ.get(S['freq'], 24), S['freq']),
                    'next': 'when due' if backup_due(c) else (datetime.fromisoformat(last_b.replace('Z', '+00:00')) + timedelta(hours=BK_FREQ.get(S['freq'], 24))).strftime('%Y-%m-%dT%H:%M:%SZ') if last_b else 'soon', 'last': last_b})
    else: out.append({'kind': 'backup', 'word': JOB_WORD['backup'], 'every': 'turned off', 'next': '', 'last': setting(c, 'backup_last_auto', '') or ''})
    return out

@app.route('/api/jobs')
def jobs_api():
    c = db()
    with JOBS['lock']:
        running = sorted(JOBS['running'].values(), key=lambda j: j['id'])
        done = list(JOBS['done'])
    return jsonify(running=running, done=done, schedule=jobs_schedule(c), problems=c.execute('SELECT COUNT(*) FROM problems WHERE cleared_at IS NULL').fetchone()[0])

@app.route('/api/jobs/run', methods=['POST'])
def jobs_run_now():
    """Owner: start a scheduled job now: {kind: weather | shops | backup}."""
    kind = str((request.get_json(silent=True) or {}).get('kind') or '')
    c = db()
    if kind == 'weather':
        if not run_weather('manual'): abort(409, 'The weather is being updated already.')
    elif kind == 'shops':
        if not c.execute("SELECT 1 FROM wishlist WHERE status='want'").fetchone(): abort(400, 'Nothing is on Shopping to look for.')
        shops_check_soon()
    elif kind == 'backup':
        if not run_backup_job('manual', bk_settings(c)['photos'], 'From the Jobs window', editor()): abort(409, 'A backup is being made already.')
    else: abort(400, 'kind must be weather, shops or backup')
    audit_only(c, 'setting', 'jobs', None, kind, editor(), f'{JOB_WORD[kind]} started from the Jobs window'); c.commit()
    return jsonify(ok=True)
