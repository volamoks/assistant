FROM nginx:alpine
COPY core/workspace-main/a2ui/index.html /usr/share/nginx/html/index.html
COPY core/workspace-main/a2ui/a2ui.bundle.js /usr/share/nginx/html/a2ui.bundle.js
COPY core/workspace-main/a2ui/nginx.conf /etc/nginx/conf.d/default.conf
