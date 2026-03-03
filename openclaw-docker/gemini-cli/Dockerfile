# Gemini CLI Docker Service for OpenClaw
# Provides containerized access to Google Gemini CLI with MCP support

FROM node:20-alpine

# Install required packages including build tools for native modules
RUN apk add --no-cache \
    bash \
    curl \
    jq \
    git \
    openssh-client \
    ca-certificates \
    python3 \
    py3-pip \
    make \
    g++ \
    gcc \
    libc-dev \
    linux-headers \
    coreutils

# Create gemini user (use different uid/gid to avoid conflicts)
RUN addgroup -g 1001 gemini && \
    adduser -u 1001 -G gemini -s /bin/bash -D gemini

# Set working directory
WORKDIR /home/gemini

# Install Gemini CLI globally
RUN npm install -g @google/gemini-cli

# Install Composio MCP server (composio-core CLI + @composio/mcp for stdio MCP server)
RUN npm install -g composio-core @composio/mcp

# Create config directories
RUN mkdir -p /home/gemini/.gemini /home/gemini/.config/composio && \
    chown -R gemini:gemini /home/gemini

# Copy entrypoint script
COPY --chown=gemini:gemini entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Copy MCP configuration template
COPY --chown=gemini:gemini mcp-config.json /home/gemini/.gemini/settings.json.template

# Switch to gemini user
USER gemini

# Environment variables
ENV HOME=/home/gemini \
    GEMINI_CONFIG_DIR=/home/gemini/.gemini \
    COMPOSIO_API_KEY=${COMPOSIO_API_KEY} \
    NODE_ENV=production \
    PATH="/home/gemini/.npm-global/bin:/usr/local/bin:${PATH}"

# Expose port for potential future API usage
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD gemini --version || exit 1

# Entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["tail", "-f", "/dev/null"]
