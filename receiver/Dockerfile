FROM python:3.12-slim
WORKDIR /app
COPY receiver.py /app/receiver.py
VOLUME /received
EXPOSE 8089
CMD ["python", "/app/receiver.py"]
