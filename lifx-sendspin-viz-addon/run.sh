#!/usr/bin/env bash
# shellcheck shell=bash

set -e

echo "Starting LIFX SendSpin Music Visualizer Add-on..."

# Load config using bashio if available, otherwise use environment variables
if command -v bashio &> /dev/null; then
    SENDSPIN_URL=$(bashio::config 'sendspin_url' 2>/dev/null || echo "$SENDSPIN_URL")
    CLIENT_NAME=$(bashio::config 'client_name' 2>/dev/null || echo "$CLIENT_NAME")
    EFFECT=$(bashio::config 'effect' 2>/dev/null || echo "$EFFECT")
    SENSITIVITY=$(bashio::config 'sensitivity' 2>/dev/null || echo "$SENSITIVITY")
else
    SENDSPIN_URL=${SENDSPIN_URL:-"ws://localhost:8927/sendspin"}
    CLIENT_NAME=${CLIENT_NAME:-"LIFX Visualizer Dev"}
    EFFECT=${EFFECT:-"energy_pulse"}
    SENSITIVITY=${SENSITIVITY:-1.0}
fi

export SENDSPIN_URL CLIENT_NAME EFFECT SENSITIVITY

echo "SendSpin URL: $SENDSPIN_URL"
echo "Effect: $EFFECT | Sensitivity: $SENSITIVITY"

# Start the application
exec python3 -m app.main
