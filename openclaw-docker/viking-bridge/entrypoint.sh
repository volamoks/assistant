#!/bin/bash
set -e

# Config is mounted via volume at /data/viking/ov.conf
export OPENVIKING_CONFIG_FILE=/data/viking/ov.conf

echo "Starting OpenViking server..."
exec openviking-server --host 0.0.0.0 --port 8100
