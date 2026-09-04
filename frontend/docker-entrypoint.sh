#!/bin/sh
set -e
: "${VITE_API_URL:?VITE_API_URL doit être défini au docker run/compose}"
: "${VITE_BASE_URL:?VITE_BASE_URL doit être défini au docker run/compose}"

grep -rl "__RUNTIME_VITE_API_URL__\|__RUNTIME_VITE_BASE_URL__" /usr/share/nginx/html | while read -r f; do
  sed -i \
    -e "s|__RUNTIME_VITE_API_URL__|${VITE_API_URL}|g" \
    -e "s|__RUNTIME_VITE_BASE_URL__|${VITE_BASE_URL}|g" \
    "$f"
done
