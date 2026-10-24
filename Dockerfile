FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 DATA_DIR=/data
WORKDIR /app
COPY requirements.txt .
# The app's own unprivileged user ("plants", 10001). Since 1.12.1 the container starts as root and app/start.py switches
# to this user when it can write to the data folders, or stays root (as before 1.12.0) when Docker does not allow that.
RUN pip install --no-compile -r requirements.txt \
 && useradd --system --uid 10001 --gid 0 --no-create-home --shell /usr/sbin/nologin plants
COPY app/ /app/
# The release number: shown in the app header, at /api/version and on the image in Docker Desktop.
COPY VERSION /app/VERSION
ARG PLANTDB_VERSION=unknown
LABEL org.opencontainers.image.title="Plant database" org.opencontainers.image.version=$PLANTDB_VERSION
VOLUME /data
# 8080: this computer (http://localhost:8080). 8081: only the Tailscale container reaches it (never published).
# 8082: sensor readings only (closed unless opened in docker-compose.yml). See docker-compose.yml.
EXPOSE 8080 8081 8082
# start.py picks the user, then runs gunicorn with app/gunicorn.conf.py (ports, one worker, no control socket).
CMD ["python", "/app/start.py"]
