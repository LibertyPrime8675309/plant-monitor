"""Start Plant record inside its container (1.12.1).

The container starts as root, with only the few privileges docker-compose.yml grants it, and this script decides which
user the app runs as:
  - its own unprivileged user ("plants", 10001) when that user can write to the data and backups folders. This is the
    safer way, and the usual one for a new install on Linux.
  - root inside the container otherwise. That is normal on Windows for folders an older version (which always ran as
    root) wrote to, because Docker Desktop does not let the new user write there and cannot hand those folders over.
    The app then runs as it did before 1.12.0, still read-only and with only those few privileges.
Either way it prints one plain line saying which, and the Debug window shows it to the owner.
It never changes a file that already exists: a brand-new, empty data or backups folder is handed to the app's own user,
and that is all.

Set PLANTDB_RUN_AS=root in docker-compose.yml (or .env) to skip the check and always run as root.
With arguments, it runs those instead of gunicorn (used by the tests)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import writable  # noqa: E402

APP_UID, APP_GID = 10001, 0
DATA_DIR = os.environ.get('DATA_DIR', '/data')
BACKUP_DIR = os.environ.get('PLANTDB_BACKUP_DIR') or ('/backups' if os.path.isdir('/backups') else os.path.join(DATA_DIR, 'backups'))
CMD = sys.argv[1:] or ['gunicorn', '--config', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gunicorn.conf.py'), 'server:app']


def say(text):
    print(text, flush=True)


def become_app_user():
    os.setgroups([])
    os.setgid(APP_GID)
    os.setuid(APP_UID)                 # from here on the process has no special privileges at all, and cannot get any back


def test_as_app_user():
    """Run the write check in a child process that has switched to the app's own user. None if it passed, else why not."""
    r, w = os.pipe()
    pid = os.fork()
    if pid == 0:                       # child
        os.close(r)
        try:
            become_app_user()
            bad = writable.problem(DATA_DIR, BACKUP_DIR)
            msg = '' if bad is None else 'it cannot write to %s (%s)' % bad
        except OSError as e:
            msg = 'it could not switch to that user (%s)' % e
        except Exception as e:         # never let the check itself stop the app from starting
            msg = 'the check failed (%s)' % e
        os.write(w, msg.encode('utf-8', 'replace'))
        os._exit(0)
    os.close(w)
    out = b''
    while True:
        chunk = os.read(r, 4096)
        if not chunk:
            break
        out += chunk
    os.close(r)
    os.waitpid(pid, 0)
    return out.decode('utf-8', 'replace') or None


def hand_over_new_folders():
    """A data or backups folder that is empty (a brand-new install) is given to the app's own user. Nothing else is."""
    for d in (DATA_DIR, BACKUP_DIR):
        try:
            if os.path.isdir(d) and not os.listdir(d) and os.stat(d).st_uid != APP_UID:
                os.chown(d, APP_UID, APP_GID)
        except OSError:
            pass                       # Windows folders cannot be handed over; the check below finds out


def main():
    os.environ['HOME'] = '/tmp'        # the container's own files are read-only; anything that wants a home folder gets /tmp
    if os.getuid() != 0:
        os.environ['PLANTDB_RUNS_AS'] = 'user'
        say('Plant record starts as user %d.' % os.getuid())
    elif os.environ.get('PLANTDB_RUN_AS', '').strip().lower() == 'root':
        os.environ['PLANTDB_RUNS_AS'] = 'root:PLANTDB_RUN_AS=root is set'
        say('PLANTDB_RUNNING_AS_ROOT: Plant record runs as root inside its container, because PLANTDB_RUN_AS=root is set.')
    else:
        hand_over_new_folders()
        why = test_as_app_user()
        if why is None:
            become_app_user()
            os.environ['PLANTDB_RUNS_AS'] = 'user'
            say('Plant record runs as its own user (plants, %d), without any special privileges.' % APP_UID)
        else:
            os.environ['PLANTDB_RUNS_AS'] = 'root:' + why
            say('PLANTDB_RUNNING_AS_ROOT: Plant record runs as root inside its container, as it did before version 1.12.0, '
                'because Docker does not let its own user use the data folders: %s. This is normal on Windows for folders '
                'an older version wrote to, and nothing needs doing. See README, "Which user the app runs as".' % why)
    os.execvp(CMD[0], CMD)


if __name__ == '__main__':
    main()
