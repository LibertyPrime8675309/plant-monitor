FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 DATA_DIR=/data
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/ /app/
# The release number: shown in the app header, at /api/version and on the image in Docker Desktop.
COPY VERSION /app/VERSION
ARG PLANTDB_VERSION=unknown
LABEL org.opencontainers.image.title="Plant database" org.opencontainers.image.version=$PLANTDB_VERSION
VOLUME /data
EXPOSE 8080
# One worker: the app seeds its database on first start and SQLite is happiest with a single writer process.
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--bind", "0.0.0.0:8080", "--timeout", "60", "server:app"]
