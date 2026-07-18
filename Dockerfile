FROM python:3.12-slim-bookworm

# Install system deps for lifxlan (if any) and build tools if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ /app/app/
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

# Data volume for options and state
VOLUME ["/data"]

# Expose ingress port
EXPOSE 8099

ENTRYPOINT ["/app/run.sh"]