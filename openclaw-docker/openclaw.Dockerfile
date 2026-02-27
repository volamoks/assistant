FROM ghcr.io/openclaw/openclaw:main

# Temporarily switch to root to install system dependencies
USER root

# Install docker CLI and sudo
RUN apt-get update && apt-get install -y \
    docker.io \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Add a mock host user mapping for the volume bounds and add to dialout
RUN groupadd -g 20 dialout_host 2>/dev/null || true; \
    useradd -u 501 -g 20 -m -s /bin/bash hostuser

# Add dialout group to sudoers and allow NOPASSWD
RUN echo "%dialout ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/dialout \
    && chmod 0440 /etc/sudoers.d/dialout

# Revert back to the unprivileged host user mapping
USER 501:20
