FROM ghcr.io/home-assistant/amd64-base:3.12

# Install Python and pip
RUN apk add --no-cache python3 py3-pip

WORKDIR /app

# Copy and install Python dependencies first (better caching)
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy the application code
COPY app/ /app/app/

# Copy and prepare run.sh
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

ENTRYPOINT ["/app/run.sh"]
