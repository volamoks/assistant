# Gemini CLI Docker Service for OpenClaw
# Provides containerized access to Google Gemini CLI with MCP support

FROM node:20-alpine

# Install required packages
RUN apk add --no-cache \
    bash \
    curl \
    jq \
    git \
    ca-certificates \
    coreutils

# Create gemini user
RUN addgroup -g 1001 gemini && \
    adduser -u 1001 -G gemini -s /bin/bash -D gemini

# Set working directory
WORKDIR /home/gemini

# Install Gemini CLI globally
RUN npm install -g @google/gemini-cli

# Create config directory
RUN mkdir -p /home/gemini/.gemini && \
    chown -R gemini:gemini /home/gemini

# Copy entrypoint script
COPY --chown=gemini:gemini entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Switch to gemini user
USER gemini

# Environment variables
ENV HOME=/home/gemini \
    GEMINI_CONFIG_DIR=/home/gemini/.gemini \
    NODE_ENV=production \
    PATH="/home/gemini/.npm-global/bin:/usr/local/bin:${PATH}"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD gemini --version || exit 1

# Entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]
