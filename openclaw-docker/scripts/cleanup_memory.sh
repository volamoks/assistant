#!/bin/bash
# Script to clear Linux kernel caches inside OrbStack to free up memory
# Requires privileged container access

echo "🧼 Clearing OrbStack (Linux) caches..."
docker run --rm --privileged alpine sh -c 'sync; echo 3 > /proc/sys/vm/drop_caches'
echo "✅ Caches cleared."
