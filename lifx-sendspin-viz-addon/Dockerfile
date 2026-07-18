FROM ghcr.io/home-assistant/amd64-base:3.12

# Install Python
RUN apk add --no-cache python3 py3-pip

WORKDIR /app

COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

ENTRYPOINT ["/app/run.sh"]
