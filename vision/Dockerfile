# Plant record vision service (1.18.0): BioCLIP 2.5 on the processor, for camera identification and the plant library.
# Built on this computer by "docker compose up -d --build" (the updater runs it). The first build downloads about 1 GB of
# Python packages (PyTorch for processors, no graphics card needed); the model itself downloads into data/vision on first start.
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PIP_NO_CACHE_DIR=1 VISION_CACHE=/cache DATA_DIR=/data HF_HOME=/cache/hf HOME=/tmp
WORKDIR /svc
RUN pip install --no-compile torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-compile open_clip_torch==3.3.0 timm==1.0.30 huggingface_hub==2.3.0 safetensors==0.8.0 numpy==2.5.4 pillow==13.0.0 flask==3.1.3 gunicorn==26.2.0
COPY vision/service.py vision/gbif_country.py /svc/
COPY VERSION /svc/VERSION
EXPOSE 8090
# One worker (the model is large), a few threads. The first start can take several minutes while it downloads.
CMD ["gunicorn", "--workers", "1", "--threads", "4", "--timeout", "600", "--bind", "0.0.0.0:8090", "service:app"]
