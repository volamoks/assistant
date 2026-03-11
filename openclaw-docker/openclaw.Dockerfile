FROM ghcr.io/openclaw/openclaw:2026.3.8

# Temporarily switch to root to install system dependencies
USER root

# Install docker CLI, sudo, python tools, jq, and column (bsdmainutils)
RUN apt-get update && apt-get install -y \
    docker.io \
    sudo \
    python3-pip \
    jq \
    bsdmainutils \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install actualpy and other dependencies globally
RUN pip3 install --break-system-packages actualpy python-dotenv telethon pandas pydub markitdown

# Install Gemini CLI and acpx for ACPX agent support
RUN npm install -g @google/gemini-cli acpx@0.1.15

# Install ClawVault (persistent agent memory) and qmd (BM25+vector search)
RUN npm install -g clawvault
RUN curl -fsSL https://bun.sh/install | bash \
    && export PATH=/root/.bun/bin:$PATH \
    && bun install -g github:tobi/qmd \
    && bun pm -g trust --all \
    && cd /root/.bun/install/global/node_modules/@tobilu/qmd \
    && bun install \
    && bun run build \
    && ln -sf /root/.bun/install/global/node_modules/@tobilu/qmd/dist/qmd.js /usr/local/bin/qmd \
    && chmod +x /usr/local/bin/qmd
RUN mkdir -p /root/.config/qmd /root/.cache/qmd \
    && mkdir -p /home/node/.config/qmd /home/node/.cache/qmd \
    && chown -R 501:20 /home/node/.config /home/node/.cache

# Gemini ACP wrapper: acpx expects "gemini" but needs --experimental-acp + flash model
# gemini-2.5-flash avoids gemini-3.1-pro-preview quota limits in ACP mode
RUN printf '#!/bin/bash\nexec /usr/local/bin/gemini --experimental-acp --model gemini-2.5-flash "$@"\n' \
    > /usr/local/bin/gemini-acp-wrapper \
    && chmod +x /usr/local/bin/gemini-acp-wrapper

# Create acpx state dir writable by container user (501:20)
# Configure gemini as default agent using --experimental-acp (OAuth via core/gemini-config volume)
RUN mkdir -p /home/node/.acpx/sessions \
    && printf '{"defaultAgent":"gemini","defaultPermissions":"approve-reads","nonInteractivePermissions":"deny","authPolicy":"skip","ttl":300,"agents":{"gemini":{"command":"gemini --experimental-acp --model gemini-3-flash-preview"}}}\n' \
       > /home/node/.acpx/config.json \
    && chown -R 501:20 /home/node/.acpx

# Add a mock host user mapping for the volume bounds and add to dialout
RUN groupadd -g 20 dialout_host 2>/dev/null || true; \
    useradd -u 501 -g 20 -m -s /bin/bash hostuser

# Add dialout group to sudoers and allow NOPASSWD
RUN echo "%dialout ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dialout \
    && chmod 0440 /etc/sudoers.d/dialout

# Revert back to the unprivileged host user mapping
USER 501:20
