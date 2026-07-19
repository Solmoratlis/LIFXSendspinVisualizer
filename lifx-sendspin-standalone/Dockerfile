FROM python:3.12-slim-bookworm

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application
COPY app/ /app/app/
COPY run.py /app/run.py
COPY config.example.yaml /app/config.example.yaml

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 8099

CMD ["python", "run.py"]