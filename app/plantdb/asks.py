"""1.58.0 (November 12 review, item 8; Ethan, November 13, 2026): care that has never been logged asks once.

A plant with no feeding ever logged has no rhythm to be late on, so Today cannot say when it is due. The first answer to that
(1.58.0, #122) was a folded part, "No feeding logged yet", that stayed for good. Ethan chose the other way: Today asks once
whether reminders are wanted, and then keeps quiet.

- No answer yet: Today shows the question, with the plants it is about.
- **yes**: the plants start counting from the day of the answer ('on'), so each comes up when its next feeding is due and they do
  not all show as due at once.
- **no**: Today says nothing about plants that have never been fed. A plant with a feeding logged keeps its reminders either way.

The same goes for flushes and root checks of semi-hydro and water-only plants ('flush'). The answer belongs to the record, not to
a person, and can be changed on the Fertilizer and Potting mixes pages. Setting: ask_<kind> = {"answer", "on", "by"}."""
from .core import *   # noqa: F401,F403

ASK_KINDS = ('feed', 'flush')

def ask_get(c, kind):
    """The answer for a kind, {'answer': 'yes' | 'no', 'on': 'YYYY-MM-DD', 'by': name}, or None when it has not been asked."""
    try: d = json.loads(setting(c, 'ask_' + kind, '') or 'null')
    except ValueError: d = None
    return d if isinstance(d, dict) and d.get('answer') in ('yes', 'no') and re.match(r'^\d{4}-\d\d-\d\d$', str(d.get('on') or '')) else None

def ask_started(c, kind, every, today):
    """Has a reminder that started with a "yes" come due: `every` days on from the day of the answer."""
    a = ask_get(c, kind)
    return bool(a and a['answer'] == 'yes' and (today - date.fromisoformat(a['on'])).days >= int(every))

@app.route('/api/asks', methods=['GET', 'PUT'])
def asks_api():
    """GET: {feed, flush}, each the answer or null. PUT {kind, answer: 'yes' | 'no' | ''}: answer, or '' to be asked again."""
    c = db()
    if request.method == 'PUT':
        b = request.get_json(silent=True) or {}; kind, ans = b.get('kind'), b.get('answer')
        if kind not in ASK_KINDS: abort(400, 'kind must be feed or flush')
        if ans not in ('yes', 'no', ''): abort(400, 'answer must be yes, no or empty')
        old = setting(c, 'ask_' + kind, ''); who = editor()
        new = json.dumps({'answer': ans, 'on': datetime.now(tzinfo(location(c)['tz'])).date().isoformat(), 'by': who}) if ans else ''
        set_setting(c, 'ask_' + kind, new)
        word = {'feed': 'feeding', 'flush': 'flushes and root checks'}[kind]
        audit_only(c, 'setting', 'ask_' + kind, old, new, who, f"Reminders for {word} never logged: {'on from today' if ans == 'yes' else 'off' if ans == 'no' else 'Today will ask again'}"); c.commit()
    return jsonify({k: ask_get(c, k) for k in ASK_KINDS})
