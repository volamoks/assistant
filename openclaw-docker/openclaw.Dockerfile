FROM ghcr.io/openclaw/openclaw:main

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
RUN pip3 install --break-system-packages actualpy python-dotenv telethon pandas pydub

# Add a mock host user mapping for the volume bounds and add to dialout
RUN groupadd -g 20 dialout_host 2>/dev/null || true; \
    useradd -u 501 -g 20 -m -s /bin/bash hostuser

# Add dialout group to sudoers and allow NOPASSWD
RUN echo "%dialout ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dialout \
    && chmod 0440 /etc/sudoers.d/dialout

# Revert back to the unprivileged host user mapping
USER 501:20
