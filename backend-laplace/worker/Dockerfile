FROM python:3.9-slim

WORKDIR /app

COPY worker.py .

RUN pip install --no-cache-dir pika

CMD ["python", "worker.py"]
