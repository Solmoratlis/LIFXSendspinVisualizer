#!/usr/bin/with-contenv bashio
# shellcheck shell=bash

set -e

CONFIG_PATH=/data/options.json

# Read options (bashio or fallback)
if command -v bashio &> /dev/null; then
    SENDSPIN_URL=$(bashio::config 'sendspin_url')
    CLIENT_NAME=$(bashio::config 'client_name')
    DISCOVER_ALL=$(bashio::config 'lifx_discover_all')
    LIGHT_LABELS=$(bashio::config 'lifx_light_labels' | jq -c '.')
    EFFECT=$(bashio::config 'effect')
    SENSITIVITY=$(bashio::config 'sensitivity')
    UPDATE_RATE=$(bashio::config 'update_rate_hz')
    ENABLED=$(bashio::config 'enabled')
else
    # Fallback for local testing
    SENDSPIN_URL=${SENDSPIN_URL:-"ws://localhost:8927/sendspin"}
    CLIENT_NAME=${CLIENT_NAME:-"LIFX Visualizer Dev"}
    DISCOVER_ALL=${DISCOVER_ALL:-true}
    LIGHT_LABELS='[]'
    EFFECT=${EFFECT:-"energy_pulse"}
    SENSITIVITY=${SENSITIVITY:-1.0}
    UPDATE_RATE=${UPDATE_RATE:-12}
    ENABLED=${ENABLED:-true}
fi

export SENDSPIN_URL CLIENT_NAME DISCOVER_ALL LIGHT_LABELS EFFECT SENSITIVITY UPDATE_RATE ENABLED

echo "Starting LIFX SendSpin Music Visualizer Add-on..."
echo "SendSpin URL: $SENDSPIN_URL"
echo "Effect: $EFFECT | Rate: ${UPDATE_RATE}Hz | Sensitivity: $SENSITIVITY"

cd /app
exec python -m app.main