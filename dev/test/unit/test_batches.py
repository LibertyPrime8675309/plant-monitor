"""The batch files themselves (1.58.0). A batch is applied once to every record there is: a new install, Ethan's own, the one a
second home will have. So what a file says has to mean the same thing in each of them, and two things do not:

- a plant's code. The files number plants as a new install does; a record where the owner has added a plant of their own gives
  the batches' later plants the next numbers. core.py batch_numbering() reads the old files so. From now on an entry that names
  a plant by its code also says the plant's name, or photos that are on its page, so nothing can land on a neighbour.
- a row number (home_id, area_id, spot_id, pot_id, tray_id). Batch C9 gave its new page `area_id: 7`, copied from another
  plant's row: a room of the main home for an orchid in Baraboo, and a different room in every record. `home_near` says the home.

dev/test/unit/test_upgrade.py found both, by upgrading old databases and comparing them with a new install."""
import sqlite3
import server as S

OLD_UP_TO = 'batchD1.json'      # the last file written while a code alone was believed. Files that sort after it follow the rule below.

def conn():
    c = sqlite3.connect(S.DB_PATH, timeout=30); c.row_factory = sqlite3.Row
    return c

def pointed(b):
    """Every entry of a batch that names a plant already in the record: (what it is, the entry)."""
    for u in b.get('updates', []): yield 'an update', u
    for a in b.get('archive', []): yield 'an archive entry', a
    for q in b.get('requests_add', []):
        if q.get('code'): yield 'a question', q
    for ph in b.get('existing_photos', []): yield 'a photo', ph
    for m in b.get('pot_mixes_add', []): yield 'a potting mix', m
    fl = b.get('facts_link') or []
    for e in ([{'code': k, 'key': v} for k, v in fl.items()] if isinstance(fl, dict) else fl): yield 'a facts link', e
    for p in b.get('plants', []):
        for mv in p.get('take_photos', []): yield 'a photo to move', {'code': mv.get('from'), 'name': mv.get('name')}

def test_the_files_are_read_in_the_order_they_apply():
    files = S.batch_files(); names = [fn for fn, _ in files]
    assert names == sorted(names) and len(names) >= 39 and len({b['id'] for _, b in files}) == len(files), 'one id per file'
    assert OLD_UP_TO in names

def test_no_batch_gives_a_row_number():
    for fn, b in S.batch_files():
        for p in b.get('plants', []):
            got = [k for k in S.BATCH_ROW_IDS if k in p]
            assert not got, f'{fn}: the new page "{p.get("common_name")}" carries {got}. Leave them out: `home_near` says the home, and the page gets the area that matches its `site`.'
        for u in b.get('updates', []):
            got = [k for k in S.BATCH_ROW_IDS if k in u.get('set', {})]
            assert not got, f'{fn}: an update for {u.get("code")} sets {got}, the number of a row in one record'

def test_a_new_batch_says_which_plant_it_means_by_more_than_its_code():
    for fn, b in S.batch_files():
        if fn <= OLD_UP_TO: continue
        for what, e in pointed(b):
            assert e.get('name') or e.get('photos'), (f'{fn}: {what} names {e.get("code")} by its code alone. Add "name" (the plant\'s common name) or "photos" (files on its page): '
                                                      'in a record where Ethan has added plants of his own, that code can be another plant.')

def test_in_a_record_without_plants_of_the_owners_own_a_code_is_the_plant_with_that_code():
    """Ethan's record in November 2026: 102 plants, all from the first list and the batches. For it the numbering changes nothing."""
    c = conn()
    meant, codes = S.batch_numbering(c)
    made = sum(len(b.get('plants', [])) for _, b in S.batch_files())
    assert len(meant) == 40 + made and sum(len(v) for v in codes.values()) == made, 'the first list has 40 plants; every new page of every batch has a number'
    for code, pid in meant.items():
        assert c.execute('SELECT code FROM plants WHERE id=?', (pid,)).fetchone()[0] == code
    assert S.find_plant(c, {'code': 'P-094'}, meant)['code'] == 'P-094' and S.find_plant(c, {'code': 'P-094'})['code'] == 'P-094'
    assert S.find_plant(c, {'code': 'P-001', 'name': 'not its name'}, meant) is None
    assert S.find_plant(c, {'code': 'P-999'}, meant) is None
    c.close()

def test_every_old_entry_still_finds_its_plant():
    """The 39 files up to D1 name 136 photos, 7 potting mixes, 10 updates and a facts link by a code alone. In a new install each is on the plant it was written for:
    nothing was left out, and the photos of one page are on that page."""
    c = conn()
    assert c.execute("SELECT COUNT(*) FROM audit_log WHERE note LIKE 'Batch % could not find %'").fetchone()[0] == 0
    meant, _ = S.batch_numbering(c)
    n = 0
    for fn, b in S.batch_files():
        for ph in b.get('existing_photos', []):
            rows = c.execute('SELECT plant_id FROM photos WHERE file=?', (ph['file'],)).fetchall()
            if not rows: continue                           # deleted by another unit test, or moved since
            assert meant[ph['code']] in {r[0] for r in rows}, f'{fn}: {ph["file"]} is not on {ph["code"]}'; n += 1
    assert n > 100
    c.close()
