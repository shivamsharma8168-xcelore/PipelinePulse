FROM nginx:1.27-alpine

COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY 10-runtime-config.sh /docker-entrypoint.d/10-runtime-config.sh
COPY index.html styles.css app.js /usr/share/nginx/html/

RUN chmod +x /docker-entrypoint.d/10-runtime-config.sh
