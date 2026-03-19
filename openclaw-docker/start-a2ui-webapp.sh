#!/bin/bash
# Start a2ui-webapp container with files copied directly (no volume mount conflict)

CONTAINER_NAME="a2ui-webapp"
A2UI_SOURCE="/data/bot/openclaw-docker/core/workspace-main/a2ui"
NGINX_CONF_SOURCE="/data/bot/openclaw-docker/core/workspace-main/a2ui/conf/default.conf"

# Stop and remove existing container
docker rm -f "$CONTAINER_NAME" 2>/dev/null

# Create container (not started)
docker create \
  --name "$CONTAINER_NAME" \
  --restart unless-stopped \
  -p 7090:80 \
  --network jarvis_net \
  nginx:alpine 2>&1

# Start container
docker start "$CONTAINER_NAME" 2>&1

# Wait for nginx to start
sleep 2

# Copy files into the container
docker cp "$A2UI_SOURCE/index.html" "$CONTAINER_NAME:/usr/share/nginx/html/index.html"
docker cp "$A2UI_SOURCE/a2ui.bundle.js" "$CONTAINER_NAME:/usr/share/nginx/html/a2ui.bundle.js"
docker cp "$NGINX_CONF_SOURCE" "$CONTAINER_NAME:/etc/nginx/conf.d/default.conf"

# Reload nginx config
docker exec "$CONTAINER_NAME" nginx -s reload 2>&1

echo "a2ui-webapp started on http://host.docker.internal:7090/"
