FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
COPY a2ui.bundle.js /usr/share/nginx/html/a2ui.bundle.js
COPY nginx.conf /etc/nginx/conf.d/default.conf
