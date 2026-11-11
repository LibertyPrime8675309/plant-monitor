# Plant record speech service (search by voice): Whisper on the processor, through faster-whisper. Built on this computer by
# "docker compose up -d --build" (the updater runs it). The first build downloads about 200 MB of Python packages; the model
# itself downloads into data/speech on first start (small.en: about 465 MB). Nothing you say leaves this computer.
FROM python:3.15-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 PIP_PROGRESS_BAR=off PIP_DISABLE_PIP_VERSION_CHECK=1 SPEECH_CACHE=/cache HF_HOME=/cache/hf HOME=/tmp
WORKDIR /svc
COPY speech/requirements.txt /svc/requirements.txt
RUN pip install --no-compile -r /svc/requirements.txt
COPY speech/service.py /svc/service.py
COPY VERSION /svc/VERSION
EXPOSE 8093
# One worker (one model in memory); it transcribes one recording at a time with every core it is given.
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--timeout", "120", "--bind", "0.0.0.0:8093", "service:app"]
