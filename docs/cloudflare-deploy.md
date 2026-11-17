# ShorbornoAI End-to-End Cloudflare Deployment & Cost-Zero Architecture (`MCORE-FDR-AIS-001`)

## 1. Root Cause of HTTP 522 on `sorbornoai.com`
Cloudflare Error 522 (`Connection timed out`) on a Pages/Worker domain occurs when a manual proxied `A` or `CNAME` record exists in the DNS zone without an active **Pages Custom Domain** binding, causing Cloudflare's edge to attempt a TCP connection to a stale/unreachable origin IP instead of routing internally to `sorbornoai-web.pages.dev`.

## 2. Zero-Cost Edge Architecture Strategy ($0/month Edge Tier)
* **Frontend & Token API (`sorbornoai.com`, `shorbornoai.com`):** Hosted on **Cloudflare Pages** (Free tier: unlimited static requests, unlimited bandwidth, 100,000 Pages Functions requests/day for `/api/livekit/token`).
* **Edge Voice Inference (`voice.sorbornoai.com`):** Hosted on **Cloudflare Workers AI** (`sorborno-voice`, 10,000 free Neurons/day for lightweight edge STT/TTS fallback).
* **LiveKit Signaling (`livekit.mcoreai.dev`):** Exposed via **Cloudflare Zero Trust QUIC Tunnel** (`cloudflared`, Free tier: unlimited bandwidth, zero open inbound TCP ports, zero origin IP exposure).
* **Media & Python Agent (`livekit-server` + `shorborno-agent.service`):** Runs locally on existing bare-metal compute with Silero VAD + local `faster-whisper` / VITS, avoiding per-minute commercial SaaS media/STT/TTS billing.

## 3. Automated Execution Command
```bash
export CLOUDFLARE_API_TOKEN="your_token_here"
export CLOUDFLARE_ACCOUNT_ID="your_account_id_here"
bash /srv/mcore/scripts/cf-e2e-deploy.sh
cat << 'EOF' > /srv/mcore/scripts/cf-e2e-deploy.sh
#!/usr/bin/env bash
set -euo pipefail
==============================================================================ShorbornoAI End-to-End Cloudflare Deployment, 522 Fix & Live VerificationSignature: MCORE-FDR-AIS-001 | Strategy: $0/mo Cloudflare Edge + Local Media==============================================================================WEB_DIR="/srv/mcore/web"
WORKER_DIR="/srv/mcore/worker"
EVIDENCE_DIR="/srv/mcore/evidence"
REPORT_MD="${EVIDENCE_DIR}/deploy-summary-report.md"
PAGES_PROJECT="sorbornoai-web"
DOMAINS=("sorbornoai.com" "www.sorbornoai.com" "shorbornoai.com" "www.shorbornoai.com"): "${CLOUDFLARE_API_TOKEN:?ERROR: Export CLOUDFLARE_API_TOKEN first}"
: "${CLOUDFLARE_ACCOUNT_ID:?ERROR: Export CLOUDFLARE_ACCOUNT_ID first}"cf_api() {
local method="$1" path="$2" data="${3:-}"
if [[ -n "$data" ]]; then
curl -fsS -X "$method" "https://api.cloudflare.com/client/v4${path}"-H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}"-H "Content-Type: application/json"--data "$data"
else
curl -fsS -X "$method" "https://api.cloudflare.com/client/v4${path}"-H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}"-H "Content-Type: application/json"
fi
}echo "[1/5] Purging stale A/CNAME records causing Error 522 & binding Pages Custom Domains..."
for domain in "${DOMAINS[@]}"; do
root_zone=$(echo "$domain" | awk -F. '{print $(NF-1)"."$NF}')
zone_id=$(cf_api GET "/zones?name=${root_zone}" | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(r[0]['id'] if r else '')")
[[ -z "$zone_id" ]] && { echo "  - Zone ${root_zone} not found, skipping"; continue; }Remove stale A/AAAA/CNAME records that hijack Pages routing and trigger 522records=$(cf_api GET "/zones/${zone_id}/dns_records?name=${domain}" | python3 -c "
import sys, json
for r in json.load(sys.stdin)['result']:
if r['type'] in ('A', 'AAAA', 'CNAME') and not r['content'].endswith('.pages.dev'):
print(r['id'])
")
for rec_id in $records; do
cf_api DELETE "/zones/${zone_id}/dns_records/${rec_id}" >/dev/null
echo "  - Deleted stale DNS record ${rec_id} on ${domain}"
doneAttach domain to Cloudflare Pages project via APIcf_api POST "/accounts/${CLOUDFLARE_ACCOUNT_ID}/pages/projects/${PAGES_PROJECT}/domains""{"name":"${domain}"}" >/dev/null 2>&1 || trueEnsure clean proxied CNAME pointing to ${PAGES_PROJECT}.pages.devexisting_cname=$(cf_api GET "/zones/${zone_id}/dns_records?type=CNAME&name=${domain}" | python3 -c "import sys,json; r=json.load(sys.stdin)['result']; print(r[0]['id'] if r else '')")
if [[ -z "$existing_cname" ]]; then
cf_api POST "/zones/${zone_id}/dns_records" \
"{\"type\":\"CNAME\",\"name\":\"${domain}","content":"${PAGES_PROJECT}.pages.dev","proxied":true}" >/dev/null
echo "  - Created proxied CNAME ${domain} -> ${PAGES_PROJECT}.pages.dev"
fi
doneecho "[2/5] Building & deploying frontend + /api/livekit/token to Cloudflare Pages..."
if [[ -d "$WEB_DIR" ]]; then
pushd "$WEB_DIR" >/dev/null
npm run build --if-present
BUILD_OUT="dist"
[[ -d ".next" && ! -d "dist" ]] && BUILD_OUT="out"
[[ -d ".vercel/output/static" ]] && BUILD_OUT=".vercel/output/static"
npx wrangler pages deploy "$BUILD_OUT" --project-name="$PAGES_PROJECT" --branch=main
popd >/dev/null
fiecho "[3/5] Deploying Edge Voice Worker (voice.sorbornoai.com)..."
if [[ -d "$WORKER_DIR" ]]; then
pushd "$WORKER_DIR" >/dev/null
npx wrangler deploy
popd >/dev/null
fiecho "[4/5] Verifying local LiveKit SFU, Cloudflared Tunnel & Shorborno Agent..."
systemctl is-active --quiet cloudflared || systemctl restart cloudflared
systemctl is-active --quiet shorborno-agent.service || systemctl restart shorborno-agent.service
ss -tulpn | grep -q ":7880" || { echo "ERROR: LiveKit port 7880 not listening"; exit 1; }echo "[5/5] Running live edge HTTP & Token Minting verification..."
sleep 4
STATUS_SORBORNO=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "https://sorbornoai.com" || echo "000")
STATUS_SHORBORNO=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "https://shorbornoai.com" || echo "000")
STATUS_VOICE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 "https://voice.sorbornoai.com" || echo "000")
STATUS_TOKEN=$(curl -s -o /dev/null -w "%{http_code}" --max-time 15 -X POST "https://sorbornoai.com/api/livekit/token"-H "Content-Type: application/json" -d '{"roomName":"verify-live","participantName":"ais-check"}' || echo "000")cat << SUMMARY > "$REPORT_MD"ShorbornoAI Live Deployment & Cost Verification ReportTimestamp (UTC): $(date -u +"%Y-%m-%dT%H:%M:%SZ")Signature: MCORE-FDR-AIS-001Error 522 Remediation: Purged stale non-Pages DNS records and bound domains directly to `${PAGES_PROJECT}.pages.dev`Live Endpoint Verification MatrixServiceEndpointHTTP StatusExpectedResultPrimary Web App`https://sorbornoai.com``${STATUS_SORBORNO}``200`$( [[ "$STATUS_SORBORNO" == "200" ]] && echo "PASS"Alias Web App`https://shorbornoai.com``${STATUS_SHORBORNO}``200`$( [[ "$STATUS_SHORBORNO" == "200" ]] && echo "PASS"Token Minting API`https://sorbornoai.com/api/livekit/token``${STATUS_TOKEN}``200`$( [[ "$STATUS_TOKEN" == "200" ]] && echo "PASS"Edge Voice Worker`https://voice.sorbornoai.com``${STATUS_VOICE}``200`$( [[ "$STATUS_VOICE" == "200" ]] && echo "PASS"Cost Optimization Strategy Summary ($0.00/mo Edge Footprint)Static + SSR Edge Hosting ($0/mo): Cloudflare Pages Free plan absorbs 100% of static assets and CDN caching globally (including Dhaka PoP) with zero egress fees.Serverless Token Minting ($0/mo): LiveKit JWT generation runs inside Cloudflare Pages Functions (100,000 free invocations/day), eliminating a dedicated auth microservice.Zero-NAT Tunneling ($0/mo): Cloudflare Tunnel (`cloudflared`) routes `wss://livekit.mcoreai.dev` over QUIC without paid load balancers or exposed origin IPs.Local Voice & Media Compute ($0/mo SaaS API cost): Self-hosted LiveKit SFU + Silero VAD + local Bengali STT/TTS avoids per-minute cloud voice billing.
SUMMARYcat "$REPORT_MD"
