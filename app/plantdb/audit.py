"""The audit log.
Split out of server.py in 1.32.0; the names it uses from other modules are linked by server.py (see plantdb/core.py, link())."""
from .core import *   # noqa: F401,F403
# ---------------------------------------------------------------- audit log: every change to every record (filters added in 1.10.0)
AUDIT_KINDS = {                          # kind of change (the filter on the Audit log page) -> actions in audit_log
    'edits': ('Changes to plant pages', ('update', 'edit', 'restore')),
    'plants': ('Plants added, archived or brought back', ('create', 'archive', 'unarchive')),
    'photos': ('Photos', ('photo_add', 'photo_assign', 'photo_move', 'photo_remove', 'photo_caption', 'photo_primary')),
    'care': ('Feeding, watering and care', ('care', 'fertilizer', 'frost')),
    'requests': ('Requests and answers', ('request',)),
    'list': ('"Still to photograph" list', ('todo',)),
    'settings': ('Settings and backups', ('setting', 'backup')),
    'lights': ('Grow lights', ('light',)),
    'groups': ('Groups and changes to a whole group', ('group',)),
    'notes': ('Notes from updates', ('note',)),
    'fungi': ('Mushroom finds', ('fungi',)),
    'library': ('Library notes, tags and wishlist', ('library',)),
    'sync': ('Clashes between devices', ('sync',)),
}
ACTION_WORD = {'create': 'Page created', 'update': 'Edited', 'edit': 'Updated', 'restore': 'Restored', 'archive': 'Archived', 'unarchive': 'Brought back',
               'photo_add': 'Photo added', 'photo_assign': 'Photo assigned', 'photo_move': 'Photo moved', 'photo_remove': 'Photo removed',
               'photo_caption': 'Caption edited', 'photo_primary': 'Main photo changed', 'care': 'Care', 'fertilizer': 'Feeding', 'frost': 'Cold night',
               'request': 'Request', 'todo': 'Photo list', 'setting': 'Setting', 'backup': 'Backup', 'note': 'Note', 'light': 'Grow light', 'group': 'Group', 'fungi': 'Mushroom find', 'library': 'Library', 'sync': 'Clash between devices'}

def audit_query(c, a, count=False):
    """SQL and arguments for the audit log with the filters in `a` (request.args): q, plant, who, kind, field, from, to,
    after (id, for the live console) and order."""
    w, args = [], []
    q = (a.get('q') or '').strip()
    if q:
        like = '%' + q.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%'      # match the text itself, wildcards included
        fields = [n for n, l in FIELD_LABEL.items() if q.lower() in str(l).lower()]
        cols = ('a.note', 'a.old_value', 'a.new_value', 'a.changed_by', 'a.plant_code', 'a.action', 'a.field', 'p.common_name')
        w.append('(' + ' OR '.join(f"{col} LIKE ? ESCAPE '\\'" for col in cols)
                 + (' OR a.field IN (%s)' % ','.join('?' * len(fields)) if fields else '') + ')')
        args += [like] * len(cols) + fields
    plant = (a.get('plant') or '').strip()
    if plant == '-': w.append('a.plant_code IS NULL')
    elif plant: w.append('a.plant_code = ?'); args.append(plant)
    who = (a.get('who') or '').strip()
    if who == '~claude': w.append("a.changed_by LIKE 'Claude%'")
    elif who == '~people': w.append("a.changed_by NOT LIKE 'Claude%'")
    elif who: w.append('a.changed_by = ?'); args.append(who)
    kind = a.get('kind') or ''
    if kind in AUDIT_KINDS:
        acts = AUDIT_KINDS[kind][1]; w.append('a.action IN (%s)' % ','.join('?' * len(acts))); args += list(acts)
    field = a.get('field') or ''
    if field: w.append('a.field = ?'); args.append(field)
    tz = tzinfo(location(c)['tz'])
    for key, op, extra in (('from', '>=', 0), ('to', '<', 1)):
        v = a.get(key) or ''
        try: d = datetime.strptime(v, '%Y-%m-%d') + timedelta(days=extra)
        except ValueError: continue
        w.append(f'a.changed_at {op} ?'); args.append(d.replace(tzinfo=tz).astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    if a.get('after'):
        try: w.append('a.id > ?'); args.append(int(a['after']))
        except ValueError: abort(400, 'after must be a number')
    where = (' WHERE ' + ' AND '.join(w)) if w else ''
    base = ' FROM audit_log a LEFT JOIN plants p ON p.code = a.plant_code' + where
    if count: return 'SELECT COUNT(*)' + base, args
    order = 'ASC' if a.get('order') == 'asc' or a.get('after') else 'DESC'
    return 'SELECT a.*, p.common_name AS plant_name' + base + f' ORDER BY a.id {order}', args

AUDIT_FIELD_LABEL = {'status': 'Status', 'photo': 'Photo', 'photo caption': 'Photo caption', 'main photo': 'Main photo', 'care_log': 'Care log',
                     'frost': 'Cold night', 'request': 'Request', 'to_photograph': '"Still to photograph" list', 'base_url': 'Label web address',
                     'backup_settings': 'Automatic backups', 'weather_place': 'Weather place', 'ingest_token': 'Sensor token', 'backup': 'Backup',
                     'claude_copied_at': 'Copied for Claude', 'grow_light': 'Grow light spot', 'light_spot': 'Light spot', 'light': 'Grow light',
                     'indoor_place': 'Room or shelf'}

def audit_label(field):
    if not field: return None
    return FIELD_LABEL.get(field) or AUDIT_FIELD_LABEL.get(field) or str(field).replace('_', ' ').capitalize()

def audit_rows(c, sql, args):
    rows = [dict(x) for x in c.execute(sql, args)]
    for r in rows:
        r['label'] = audit_label(r['field'])
        r['action_word'] = ACTION_WORD.get(r['action'], r['action'])
    return rows

@app.route('/api/audit')
def audit():
    """The newest changes first (a list), with the same filters as /api/audit/search. ?after=<id> returns the changes
    since that one, oldest first: the live console asks for this every few seconds."""
    c = db()
    limit = max(1, min(int(request.args.get('limit', 200)), 2000))
    sql, args = audit_query(c, request.args)
    return jsonify(audit_rows(c, sql + ' LIMIT ?', args + [limit]))

@app.route('/api/audit/search')
def audit_search():
    """One page of the audit log with filters, plus how many changes match in all."""
    c = db()
    limit = max(1, min(int(request.args.get('limit', 100)), 500))
    offset = max(0, int(request.args.get('offset', 0) or 0))
    sql, args = audit_query(c, request.args)
    csql, cargs = audit_query(c, request.args, count=True)
    total = c.execute(csql, cargs).fetchone()[0]
    return jsonify(entries=audit_rows(c, sql + ' LIMIT ? OFFSET ?', args + [limit, offset]), total=total, offset=offset, limit=limit,
                   max_id=c.execute('SELECT MAX(id) FROM audit_log').fetchone()[0] or 0)

@app.route('/api/audit/facets')
def audit_facets():
    """What the filters on the Audit log page can choose from."""
    c = db()
    who = [{'name': r[0], 'count': r[1]} for r in c.execute('SELECT changed_by, COUNT(*) FROM audit_log GROUP BY changed_by ORDER BY changed_by LIKE ?, changed_by', ('Claude%',))]
    used = {r[0] for r in c.execute('SELECT DISTINCT field FROM audit_log WHERE field IS NOT NULL')}
    fields = [{'name': n, 'label': audit_label(n)} for n in used]
    plants = [{'code': r['code'], 'name': r['common_name'], 'status': r['status']} for r in c.execute('SELECT code, common_name, status FROM plants ORDER BY code')]
    first = c.execute('SELECT MIN(changed_at), COUNT(*) FROM audit_log').fetchone()
    return jsonify(who=who, fields=sorted(fields, key=lambda f: str(f['label']).lower()), plants=plants,
                   kinds=[{'key': k, 'label': v[0]} for k, v in AUDIT_KINDS.items()], first=first[0], total=first[1])
