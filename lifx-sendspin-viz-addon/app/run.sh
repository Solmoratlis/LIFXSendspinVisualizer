#!/usr/bin/with-contenv bashio
# shellcheck shell=bash

set -e

echo "Starting LIFX SendSpin Music Visualizer Add-on..."

if command -v bashio &> /dev/null; then
    SENDSPIN_URL=$(bashio::config 'sendspin_url')
    CLIENT_NAME=$(bashio::config 'client_name')
    EFFECT=$(bashio::config 'effect')
    SENSITIVITY=$(bashio::config 'sensitivity')
else
    SENDSPIN_URL=${SENDSPIN_URL:-"ws://localhost:8927/sendspin"}
    CLIENT_NAME=${CLIENT_NAME:-"LIFX Visualizer Dev"}
    EFFECT=${EFFECT:-"energy_pulse"}
    SENSITIVITY=${SENSITIVITY:-1.0}
fi

export SENDSPIN_URL CLIENT_NAME EFFECT SENSITIVITY

echo "SendSpin URL: $SENDSPIN_URL"
echo "Effect: $EFFECT | Sensitivity: $SENSITIVITY"

exec python3 -m app.main
