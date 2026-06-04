#!/bin/sh
set -eu

: "${BACKEND_UPSTREAM:?BACKEND_UPSTREAM is required}"

export API_BASE="${API_BASE:-/api}"
export NGINX_PORT="${NGINX_PORT:-80}"
export API_PROXY_PATH="${API_PROXY_PATH:-/api/}"
export PROXY_READ_TIMEOUT="${PROXY_READ_TIMEOUT:-60s}"
export STATIC_CACHE_CONTROL="${STATIC_CACHE_CONTROL:-no-store, no-cache, must-revalidate, max-age=0}"

cat > /usr/share/nginx/html/config.js <<EOF
window.PIPELINEPULSE_CONFIG = {
  API_BASE: "${API_BASE}"
};
EOF
