FROM ghcr.io/home-assistant/amd64-base:3.21

# Install Python 3.12
RUN apk add --no-cache python3~3.12 py3-pip

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy application code
COPY app/ /app/app/

# Copy and prepare run.sh
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

ENTRYPOINT ["/app/run.sh"]
