"""Can this process write everywhere the app needs to? (1.12.1)

Used twice: by start.py, which tests it as the app's own user before deciding whether to switch to that user, and by
server.py when it starts, which stops with a plain message (PLANTDB_NOT_WRITABLE) if a folder still cannot be written.
Nothing here changes a file that already exists: it only creates missing folders and a short-lived test file."""
import os

SQLITE_FILES = ('', '-wal', '-shm', '-journal')


def folders(data_dir, backup_dir):
    return (data_dir, os.path.join(data_dir, 'photos'), os.path.join(data_dir, 'photos_deleted'),
            os.path.join(data_dir, 'cache'), os.path.join(data_dir, 'cache', 'thumbs'), backup_dir)


def problem(data_dir, backup_dir):
    """None if every folder and the database can be written; otherwise (path, error text) for the first one that cannot."""
    for d in folders(data_dir, backup_dir):
        try:
            os.makedirs(d, exist_ok=True)
            probe = os.path.join(d, '.write-test-%d' % os.getpid())
            with open(probe, 'w') as fh:
                fh.write('ok')
            os.remove(probe)
        except OSError as e:
            return d, str(e)
    db = os.path.join(data_dir, 'plants.db')
    for f in (db + s for s in SQLITE_FILES):          # the database and SQLite's side files must be writable too
        if os.path.exists(f):
            try:
                os.close(os.open(f, os.O_RDWR))           # opening for writing changes nothing
            except OSError as e:
                return f, str(e)
    return None          # photos and thumbnails are only ever added or moved, never written over, so folder access is enough
