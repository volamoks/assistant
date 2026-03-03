#!/bin/bash
#
# Wrapper script to run Gemini CLI commands from other containers
# Usage: docker compose exec gemini-cli /usr/local/bin/gemini-wrapper.sh [args...]
#

# Default to gemini if no command specified
if [ "$#" -eq 0 ]; then
    set -- "gemini"
fi

# Execute the command in the gemini-cli container
cd /Users/abror_mac_mini/Projects/bot/openclaw-docker && \
docker compose exec gemini-cli "$@"
