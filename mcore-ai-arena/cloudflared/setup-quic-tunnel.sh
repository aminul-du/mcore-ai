#!/usr/bin/env bash
set -Eeuo pipefail
PROJECT_DIR="/srv/mcore/mcore-ai-arena"
TUNNEL_NAME="${1:-mcore-arena-quic}"
HOSTNAME="${2:-arena.mcoreai.com}"

command -v cloudflared >/dev/null 2>&1 || { echo "[ERROR] cloudflared CLI not installed on host."; exit 1; }
[[ -f "${HOME}/.cloudflared/cert.pem" ]] || cloudflared tunnel login

cloudflared tunnel list | grep -qw "${TUNNEL_NAME}" || cloudflared tunnel create "${TUNNEL_NAME}"
cloudflared tunnel route dns "${TUNNEL_NAME}" "${HOSTNAME}"

TOKEN=$(cloudflared tunnel token "${TUNNEL_NAME}")
if grep -qE '^CLOUDFLARE_TUNNEL_TOKEN=' "${PROJECT_DIR}/.env"; then
  sed -i "s|^CLOUDFLARE_TUNNEL_TOKEN=.*|CLOUDFLARE_TUNNEL_TOKEN=${TOKEN}|" "${PROJECT_DIR}/.env"
else
  echo "CLOUDFLARE_TUNNEL_TOKEN=${TOKEN}" >> "${PROJECT_DIR}/.env"
fi

echo "[OK] DNS routed (${HOSTNAME} -> ${TUNNEL_NAME}) and token stored in ${PROJECT_DIR}/.env"
echo "Start QUIC tunnel container: cd ${PROJECT_DIR} && docker compose -f docker-compose.prod.yml --profile tunnel up -d"
