"""1.33.0: push notifications to phones and computers (Web Push, through the browser's own push service; app/webpush.py does the
signing and encryption). Each person chooses, for their own sign-in, which kinds reach them: cold nights, Shopping alerts, what is
due today, and requests from Claude. A person gets the messages for the home they start on (people.home_id; the main home
otherwise). Sending happens from the background jobs; push_loop() sends the ones that go by the clock."""
from .core import *   # noqa: F401,F403
import webpush as WP

PUSH_SCHEMA = """
CREATE TABLE IF NOT EXISTS push_subs(id INTEGER PRIMARY KEY AUTOINCREMENT, login TEXT NOT NULL, endpoint TEXT NOT NULL UNIQUE, p256dh TEXT NOT NULL,
  auth TEXT NOT NULL, device TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, last_ok TEXT, fails INTEGER NOT NULL DEFAULT 0);
"""
PUSH_KINDS = [('cold', 'Cold nights', 'When the forecast turns, and a reminder the afternoon before each cold night.'),
              ('shopping', 'Shopping alerts', 'A price at or under your limit, or something back in stock.'),
              ('due', 'Watering and feeding due', 'One message in the morning with what is due today.'),
              ('requests', 'Requests from Claude', 'When Claude adds a request in the app: a photo or an answer it needs.'),
              ('sensors', 'Sensor alerts', 'A dry pot, dangerous cold at a sensor, or a sensor that has gone quiet: once a day each.')]   # 1.35.0
PUSH_SUBJECT = 'mailto:plant-record@' + (os.environ.get('PLANTDB_PUSH_DOMAIN') or 'example.invalid')
PUSH_SEND = {'fn': None}             # a stand-in sender for tests: fn(sub, payload) -> status

def push_keys(c):
    """The VAPID key pair, made once and kept in settings (on this computer only)."""
    priv, pub = setting(c, 'push_vapid_private', ''), setting(c, 'push_vapid_public', '')
    if not (priv and pub):
        priv, pub = WP.make_vapid()
        set_setting(c, 'push_vapid_private', priv); set_setting(c, 'push_vapid_public', pub); c.commit()
    return priv, pub

def push_wants(c, login, kind):
    r = c.execute("SELECT value FROM user_prefs WHERE login=? AND key=?", (login, 'push.' + kind)).fetchone()
    return (r[0] if r else '1') != '0'

def push_home_of(c, login, main):
    r = c.execute('SELECT home_id FROM people WHERE login=?', (login,)).fetchone()
    return (r['home_id'] if r and r['home_id'] else None) or main

def push_send(c, kind, title, body, url='#/', home_id=None, logins=None, tag=None):
    """Sends one message to every device of every person who wants this kind (and, with home_id, lives at that home).
    Returns how many devices it reached. Devices the push service says are gone are dropped; others are kept after a failure."""
    priv, pub = push_keys(c)
    main = home_place(c)['id']
    subs = c.execute('SELECT * FROM push_subs ORDER BY id').fetchall()
    sent = 0
    for s in subs:
        if logins is not None and s['login'] not in logins: continue
        if not push_wants(c, s['login'], kind): continue
        if home_id is not None and push_home_of(c, s['login'], main) != home_id: continue
        t, b = (title(units_for(c, s['login'])) if callable(title) else (title, body))     # 1.47.0: a callable writes the words in that person's units
        payload = {'title': t[:120], 'body': b[:300], 'url': url, 'tag': tag or kind, 'kind': kind}
        try:
            if PUSH_SEND['fn']: st = PUSH_SEND['fn'](dict(s), payload)
            else: st, _ = WP.send(dict(s), payload, priv, pub, PUSH_SUBJECT, urgency='high' if kind == 'cold' else 'normal')
        except Exception as e:
            st = 0; problem('push', f'A notification could not be sent to {s["device"] or "a device"}', f'{type(e).__name__}: {e}', c)
        if st in (200, 201, 202): c.execute('UPDATE push_subs SET last_ok=?, fails=0 WHERE id=?', (now(), s['id'])); sent += 1
        elif st in (404, 410): c.execute('DELETE FROM push_subs WHERE id=?', (s['id'],))      # the browser dropped it
        else:
            c.execute('UPDATE push_subs SET fails=fails+1 WHERE id=?', (s['id'],))
            if st: problem('push', f'The push service refused a notification for {s["device"] or "a device"} (status {st})', '', c)
    c.commit()
    return sent

def push_once(c, key, days=2):
    """True the first time a key is seen (kept in settings for a few days), so a message goes once."""
    k = 'push_sent:' + key
    if setting(c, k, ''): return False
    set_setting(c, k, now())
    cut = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%dT%H:%M:%SZ')
    c.execute("DELETE FROM settings WHERE key LIKE 'push_sent:%' AND value<?", (cut,))
    c.commit(); return True

def push_cold(c):
    """A cold night that has just come into the forecast for a home, and the reminder the afternoon before it."""
    for H in homes(c):
        with place_for(H['id']):
            F = frost_report(c)
        nights = [n for n in F.get('nights', []) if n.get('plants')]
        tz = tzinfo(H['tz']); local = datetime.now(tz)
        for n in nights:
            d = n['date']; cnt = len(n['plants']); worst = n.get('worst') or 'watch'
            word = {'danger': 'could die', 'damage': 'would be damaged', 'watch': 'are close calls'}.get(worst, 'are at risk')
            when_ = 'tonight' if d == (local.date() + timedelta(days=1)).isoformat() else midday_word(d)
            if push_once(c, f'cold:{H["id"]}:{d}:new', 9):
                push_send(c, 'cold', lambda u, n=n, when_=when_, H=H, cnt=cnt, word=word: (f'Cold night {when_}: {temp_text(round(n["low"]), u)} at {H["name"].split(",")[0]}', f'{cnt} plant{"s" if cnt != 1 else ""} outside {word}. Open the cold-night checklist.'), None, '#/frost', H['id'], tag=f'cold-{d}')
            night_of = date.fromisoformat(d) - timedelta(days=1)       # the night of a date is the evening before it
            if local.date() == night_of and local.hour >= 15 and push_once(c, f'cold:{H["id"]}:{d}:eve', 3):
                push_send(c, 'cold', lambda u, n=n, H=H, cnt=cnt: (f'Tonight: down to {temp_text(round(n["low"]), u)} at {H["name"].split(",")[0]}', f'{cnt} plant{"s" if cnt != 1 else ""} to bring in or cover this evening.'), None, '#/frost', H['id'], tag=f'cold-{d}')

def midday_word(d):
    try: return date.fromisoformat(d).strftime('%A')
    except ValueError: return d

def push_due(c):
    """At 8 in the morning, local time, for each home: what is due today."""
    for H in homes(c):
        tz = tzinfo(H['tz']); local = datetime.now(tz)
        if local.hour < 8: continue
        if not push_once(c, f'due:{H["id"]}:{local.date().isoformat()}', 2): continue
        with place_for(H['id']):
            W = water_report(c)
            at, at_args = plants_at(c, H)
            codes = {r[0] for r in c.execute("SELECT code FROM plants WHERE status='active'" + at, at_args)}
            today = local.date()
            feed = [p for d in ics_feed_days(c, today, today) for p in d['plants'] if p['code'] in codes]
        water = [p for p in W['plants'] if p['state'] == 'due']
        if not water and not feed: continue
        parts = []
        if water: parts.append(f'{len(water)} to water')
        if feed: parts.append(f'{len(feed)} to feed')
        push_send(c, 'due', f'Today at {H["name"].split(",")[0]}: ' + ' and '.join(parts), ', '.join(p['code'] for p in (water + feed)[:8]) + ('…' if len(water) + len(feed) > 8 else ''), '#/today', H['id'], tag='due')

def push_shopping(c, alerts):
    """New Shopping alerts, just made by a store check: one message each, or one summary past three."""
    if not alerts: return
    if len(alerts) <= 3:
        for a in alerts: push_send(c, 'shopping', 'Shopping: ' + (a['wish'] or 'an alert'), a['text'], '#/shopping', tag=f'shop-{a["id"]}')
    else: push_send(c, 'shopping', f'Shopping: {len(alerts)} alerts', '; '.join(a['text'][:60] for a in alerts[:4]) + '…', '#/shopping', tag='shop')

def push_requests(c, items):
    """Requests Claude has just added (from an upgrade batch)."""
    if not items: return
    if len(items) == 1: push_send(c, 'requests', 'Claude asks: ' + (items[0].get('plant_code') or ''), str(items[0].get('text', ''))[:200], '#/today', tag='req')
    else: push_send(c, 'requests', f'Claude has {len(items)} requests', '; '.join(str(i.get('text', ''))[:50] for i in items[:4]) + '…', '#/today', tag='req')

def push_loop():
    time.sleep(120)
    while True:
        try:
            c = sqlite3.connect(DB_PATH, timeout=30); c.row_factory = sqlite3.Row
            try:
                if c.execute('SELECT 1 FROM push_subs LIMIT 1').fetchone():
                    push_cold(c); push_due(c); push_sensors(c)
            finally: c.close()
        except Exception as e: problem_exc('push', e, 'The notifications check failed')
        time.sleep(600)

@app.route('/api/push')
def push_info():
    """Your own devices, the public key the browser needs, and your choices."""
    c = db(); login = prefs_login(c)
    priv, pub = push_keys(c)
    subs = [dict(s) for s in c.execute('SELECT id, device, created_at, last_ok, fails FROM push_subs WHERE login=? ORDER BY id', (login,))]
    return jsonify(key=pub, devices=subs, kinds=[{'key': k, 'label': l, 'help': h, 'on': push_wants(c, login, k)} for k, l, h in PUSH_KINDS],
                   https=via_tailscale() or request.host.startswith(('localhost', '127.0.0.1')))

@app.route('/api/push/subscribe', methods=['POST', 'DELETE'])
def push_subscribe():
    """POST {endpoint, keys: {p256dh, auth}, device}: this browser wants notifications. DELETE {endpoint}: it stopped."""
    c = db(); login = prefs_login(c); b = request.get_json(silent=True) or {}
    ep = str(b.get('endpoint') or '')[:1000]
    if not ep.startswith('https://'): abort(400, 'That is not a push address')
    if request.method == 'DELETE':
        c.execute('DELETE FROM push_subs WHERE endpoint=? AND login=?', (ep, login)); c.commit()
        return jsonify(ok=True)
    keys = b.get('keys') or {}
    if not (keys.get('p256dh') and keys.get('auth')): abort(400, 'The browser did not give its keys')
    dev = re.sub(r'\s+', ' ', str(b.get('device') or ''))[:80]
    c.execute('INSERT INTO push_subs(login,endpoint,p256dh,auth,device,created_at) VALUES(?,?,?,?,?,?) ON CONFLICT(endpoint) DO UPDATE SET login=excluded.login, p256dh=excluded.p256dh, auth=excluded.auth, device=excluded.device, fails=0',
              (login, ep, str(keys['p256dh'])[:200], str(keys['auth'])[:100], dev, now()))
    audit_only(c, 'setting', 'push', None, dev, editor(), f'Notifications turned on for a device ({dev or "unnamed"})')
    c.commit()
    return jsonify(ok=True)

@app.route('/api/push/test', methods=['POST'])
def push_test():
    c = db(); login = prefs_login(c)
    n = push_send(c, 'test', 'Plant record', 'Notifications are working on this device.', '#/settings', logins={login}, tag='test')
    return jsonify(sent=n)

@app.route('/api/push/devices/<int:i>', methods=['DELETE'])
def push_device_rm(i):
    c = db(); login = prefs_login(c)
    c.execute('DELETE FROM push_subs WHERE id=? AND login=?', (i, login)); c.commit()
    return jsonify(ok=True)
