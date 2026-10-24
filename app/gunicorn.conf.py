# How gunicorn runs Plant record inside its container (1.12.1; these were command-line options in the Dockerfile before).
# gunicorn ignores settings it does not know, so this file works with older and newer versions alike.

# 8080: this computer (http://localhost:8080). 8081: only the Tailscale container reaches it (never published).
# 8082: sensor readings only (closed unless opened in docker-compose.yml). See docker-compose.yml.
bind = ['0.0.0.0:8080', '0.0.0.0:8081', '0.0.0.0:8082']
# One worker: the app seeds its database on first start and SQLite is happiest with a single writer process.
workers = 1
threads = 4
timeout = 60
worker_tmp_dir = '/tmp'
# gunicorn 25.1 added a control socket for its gunicornc tool, made in a home folder. The app does not use it, and the
# container's own files are read-only, so it is turned off (it only printed "Control server error ... Read-only file system").
control_socket_disable = True
