# --- Build Stage ---
FROM node:20-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    python3 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Bun for qmd
RUN curl -fsSL https://bun.sh/install | bash

# --- Final Stage ---
FROM ghcr.io/openclaw/openclaw:2026.3.12

# Metadata
LABEL maintainer="Antigravity"
LABEL version="2026.3.13-optimized"

USER root

# Combine RUN commands to reduce layers
# Install docker CLI, sudo, python tools, jq, column, and ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    docker.io \
    sudo \
    python3-pip \
    jq \
    bsdmainutils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy Bun from builder
COPY --from=builder /root/.bun /root/.bun
ENV PATH="/root/.bun/bin:${PATH}"

# Install global tools in a single layer
RUN pip3 install --no-cache-dir --break-system-packages \
    actualpy \
    python-dotenv \
    telethon \
    pandas \
    pydub \
    markitdown \
    && npm install -g @google/gemini-cli acpx@0.1.15 clawvault \
    && bun install -g github:tobi/qmd \
    && bun pm -g trust --all \
    && printf '#!/bin/bash\nexec /root/.bun/bin/bun /root/.bun/install/global/node_modules/@tobilu/qmd/src/cli/qmd.ts "$@"\n' \
       > /usr/local/bin/qmd \
    && chmod +x /usr/local/bin/qmd

# Setup directories and permissions
RUN mkdir -p /root/.config/qmd /root/.cache/qmd \
    && mkdir -p /home/node/.config/qmd /home/node/.cache/qmd \
    && mkdir -p /home/node/.acpx/sessions \
    && chown -R 501:20 /home/node/.config /home/node/.cache /home/node/.acpx

# Gemini ACP wrapper
RUN printf '#!/bin/bash\nexec /usr/local/bin/gemini --experimental-acp --model gemini-2.5-flash "$@"\n' \
    > /usr/local/bin/gemini-acp-wrapper \
    && chmod +x /usr/local/bin/gemini-acp-wrapper

# ACPX configuration
RUN printf '{"defaultAgent":"gemini","defaultPermissions":"approve-reads","nonInteractivePermissions":"deny","authPolicy":"skip","ttl":300,"agents":{"gemini":{"command":"gemini --experimental-acp --model gemini-3-flash-preview"}}}\n' \
    > /home/node/.acpx/config.json \
    && chown 501:20 /home/node/.acpx/config.json

# User and sudo setup
RUN groupadd -g 20 dialout_host 2>/dev/null || true; \
    useradd -u 501 -g 20 -m -s /bin/bash hostuser 2>/dev/null || true; \
    echo "%dialout ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dialout \
    && chmod 0440 /etc/sudoers.d/dialout

# Revert to unprivileged user
USER 501:20
