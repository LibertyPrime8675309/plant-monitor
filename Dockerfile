FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 DATA_DIR=/data
WORKDIR /app
COPY requirements.txt .
# 1.12.0: the app runs as its own unprivileged user ("plants", 10001), not as root
RUN pip install --no-compile -r requirements.txt \
 && useradd --system --uid 10001 --gid 0 --no-create-home --shell /usr/sbin/nologin plants
COPY app/ /app/
# The release number: shown in the app header, at /api/version and on the image in Docker Desktop.
COPY VERSION /app/VERSION
ARG PLANTDB_VERSION=unknown
LABEL org.opencontainers.image.title="Plant database" org.opencontainers.image.version=$PLANTDB_VERSION
VOLUME /data
USER 10001
# 8080: this computer (http://localhost:8080). 8081: only the Tailscale container reaches it (never published).
# 8082: sensor readings only (closed unless opened in docker-compose.yml). See docker-compose.yml.
EXPOSE 8080 8081 8082
# One worker: the app seeds its database on first start and SQLite is happiest with a single writer process.
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:8080", "--bind", "0.0.0.0:8081", "--bind", "0.0.0.0:8082", "--timeout", "60", "--worker-tmp-dir", "/tmp", "server:app"]
