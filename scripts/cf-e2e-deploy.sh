#!/usr/bin/env bash
set -euo pipefail

WEB_DIR="/srv/mcore/apps/web"
WORKER_DIR="/srv/mcore/workers/sorborno-voice"
EVIDENCE_DIR="/srv/mcore/evidence"
REPORT_MD="${EVIDENCE_DIR}/deploy-summary-report.md"
PAGES_PROJECT="sorbornoai-web"
DOMAINS=("sorbornoai.com" "www.sorbornoai.com" "shorbornoai.com" "www.shorbornoai.com")

mkdir -p "${EVIDENCE_DIR}"

if [ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]; then
  CLOUDFLARE_ACCOUNT_ID="41903f4febb2c66dffd4ffcae558e692"
fi
export CLOUDFLARE_ACCOUNT_ID

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  if [ -f "${HOME}/.wrangler/config/default.toml" ]; then
    CLOUDFLARE_API_TOKEN=$(grep -E '^oauth_token' "${HOME}/.wrangler/config/default.toml" | awk -F'=' '{print $2}' | tr -d ' "' | tr -d ' ')
  fi
fi
: "${CLOUDFLARE_API_TOKEN:?ERROR: Export CLOUDFLARE_API_TOKEN first}"
export CLOUDFLARE_API_TOKEN

cf_api() {
  local method="$1" path="$2" data="${3:-}"
  if [ -n "$data" ]; then
    curl -fsS -X "$method" "https://api.cloudflare.com/client/v4${path}"       -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}"       -H "Content-Type: application/json"       --data "$data" || true
  else
    curl -fsS -X "$method" "https://api.cloudflare.com/client/v4${path}"       -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}"       -H "Content-Type: application/json" || true
  fi
}

echo "[1/5] Fixing Error 522: Attaching Pages & Edge Worker Routes for Domains..."
for domain in "${DOMAINS[@]}"; do
  root_zone=$(echo "$domain" | awk -F. '{print $(NF-1)"."$NF}')
  zone_id=$(cf_api GET "/zones?name=${root_zone}" | python3 -c "import sys,json
try:
    r=json.load(sys.stdin).get('result', [])
    print(r[0]['id'] if r else '')
except Exception:
    print('')
")
  if [ -z "$zone_id" ]; then
    continue
  fi

  cf_api POST "/accounts/${CLOUDFLARE_ACCOUNT_ID}/pages/projects/${PAGES_PROJECT}/domains"     "{"name":"${domain}"}" >/dev/null 2>&1 || true

  existing_route=$(cf_api GET "/zones/${zone_id}/workers/routes" | python3 -c "import sys,json
try:
    for r in json.load(sys.stdin).get('result', []):
        if r.get('pattern') == '${domain}/*':
            print(r.get('id', ''))
            break
except Exception:
    pass
")
  if [ -z "$existing_route" ]; then
    cf_api POST "/zones/${zone_id}/workers/routes"       "{"pattern":"${domain}/*","script":"sorborno-voice"}" >/dev/null 2>&1 || true
  fi
done

echo "[2/5] Deploying Frontend & /api/livekit/token to Cloudflare Pages..."
if [ -d "$WEB_DIR" ]; then
  pushd "$WEB_DIR" >/dev/null
  BUILD_OUT="dist"
  if [ -d ".next" ] && [ ! -d "dist" ]; then
    BUILD_OUT="out"
  fi
  if [ -d ".vercel/output/static" ]; then
    BUILD_OUT=".vercel/output/static"
  fi
  npx wrangler pages deploy "$BUILD_OUT" --project-name="$PAGES_PROJECT" --branch=main
  popd >/dev/null
fi

echo "[3/5] Deploying Edge Voice Worker (voice.sorbornoai.com)..."
if [ -d "$WORKER_DIR" ]; then
  pushd "$WORKER_DIR" >/dev/null
  npx wrangler deploy
  popd >/dev/null
fi

echo "[4/5] Verifying Local LiveKit SFU, Cloudflared Tunnel & Shorborno Agent..."
systemctl is-active --quiet cloudflared || sudo systemctl restart cloudflared
systemctl is-active --quiet shorborno-agent.service || sudo systemctl restart shorborno-agent.service
ss -tulpn | grep -q ":7880"

echo "[5/5] Verifying Live HTTP Status Codes..."
sleep 3
S1=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "https://sorbornoai.com" || echo "000")
S2=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "https://shorbornoai.com" || echo "000")
S3=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "https://voice.sorbornoai.com" || echo "000")
S4=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 -X POST "https://sorbornoai.com/api/livekit/token" -H "Content-Type: application/json" -d '{"roomName":"verify","participantName":"ais"}' || echo "000")

printf "| Endpoint | Status |\n|---|---|\n| sorbornoai.com | %s |\n| shorbornoai.com | %s |\n| voice.sorbornoai.com | %s |\n| /api/livekit/token | %s |\n" "$S1" "$S2" "$S3" "$S4" | tee "$REPORT_MD"
